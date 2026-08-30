import json
import threading
import time

import pytest

from backend.diagnosis_jobs import DiagnosisJobs, StaleDiagnosis
from backend.user_memory import _atomic_json
from backend.diagnostics import start_diagnosis, answer_diagnosis


INTENT={'session_id':'intent','revision':1,'action':'ready_for_plan','slots':{'topic':'Go'},
    'onboarding':{'goal_route':'gap_upgrade','level_claim':'some','learning_mode':'practice','session_minutes':25,
                  'topic_type':'custom','concept_scope':'not_applicable','teaching_preference':'balanced','deadline_days':None}}


@pytest.fixture
def prepared(tmp_path):
    root=tmp_path
    user=root/'userdir/u_test'
    _atomic_json(user/'onboarding/intent-state.json', INTENT)
    _atomic_json(user/'learning-state.json', {'revision':1})
    jobs=DiagnosisJobs(root, max_workers=1)
    yield root,user,jobs
    jobs.shutdown()


def start(jobs, work, rid='r1', topic='Go'):
    return jobs.start('test',rid,'intent',1,{'user_id':'test','topic':{'type':'custom','value':topic},'level_claim':'some','learning_mode':'practice','goal_route':'gap_upgrade','session_minutes':25},work)


def finish(jobs,rid='r1'):
    deadline=time.monotonic()+2
    while time.monotonic()<deadline:
        job=jobs.get('test',rid)
        if job['status'] not in {'queued','running'}: return job
        time.sleep(.005)
    raise AssertionError('job did not finish')


def generated(_phase): return start_diagnosis('Go','some')


def test_returns_before_model_and_deduplicates_lost_response(prepared):
    _,_,jobs=prepared; gate=threading.Event(); calls=[]
    def work(phase):
        calls.append(1);gate.wait(1);return generated(phase)
    t=time.monotonic()
    first=start(jobs,work); second=start(jobs,work)
    assert time.monotonic()-t < .2
    assert first['request_id']==second['request_id']
    gate.set();assert finish(jobs)['status']=='completed';assert len(calls)==1


@pytest.mark.parametrize('change',['cancel','intent','project','new_job'])
def test_stale_worker_cannot_commit(prepared,change):
    root,user,jobs=prepared;entered=threading.Event();gate=threading.Event()
    def work(phase): entered.set();gate.wait(1);return generated(phase)
    start(jobs,work);assert entered.wait(1)
    if change=='cancel':jobs.cancel('test','r1')
    elif change=='intent':_atomic_json(user/'onboarding/intent-state.json',{'session_id':'intent','revision':2})
    elif change=='project':_atomic_json(user/'learning-state.json',{'revision':2})
    else:start(jobs,generated,'r2')
    gate.set();assert finish(jobs)['status']=='cancelled'
    if change!='new_job':assert not (user/'onboarding/diagnostic.json').exists()


def test_completed_refresh_reads_answered_state_without_reset(prepared):
    _,user,jobs=prepared;start(jobs,generated);result=finish(jobs)
    session=json.loads((user/'onboarding/diagnostic.json').read_text())
    question=result['result']['question'];option=question['options'][0]['id']
    updated=answer_diagnosis(session,option,question_id=question['id'])
    _atomic_json(user/'onboarding/diagnostic.json',updated)
    assert jobs.current('test')['result']['answered_count']==1
    again=start(jobs,lambda _:pytest.fail('must not regenerate'))
    assert again['result']['answered_count']==1


def test_restart_marks_orphan_interrupted_and_preserves_completed(prepared):
    root,_,jobs=prepared;start(jobs,generated);assert finish(jobs)['status']=='completed'
    fresh=DiagnosisJobs(root)
    try:assert fresh.get('test','r1')['status']=='completed'
    finally:fresh.shutdown()
    path=root/'userdir/u_test/.diagnosis-jobs/r2.json'
    stored=json.loads((path.with_name('r1.json')).read_text())
    stored.update(request_id='r2',status='running',phase='generating')
    _atomic_json(path,stored)
    fresh=DiagnosisJobs(root)
    try:assert fresh.get('test','r2')['status']=='interrupted'
    finally:fresh.shutdown()


def test_reusing_request_id_with_different_payload_is_rejected(prepared):
    _,_,jobs=prepared;start(jobs,generated);finish(jobs)
    with pytest.raises(StaleDiagnosis):start(jobs,generated,topic='Python')


def test_failure_sanitized_and_new_id_retry_works(prepared):
    _,_,jobs=prepared
    def broken(_):raise RuntimeError('secret-test-key-do-not-return')
    start(jobs,broken);failed=finish(jobs)
    assert failed['status']=='failed' and failed['retryable']
    assert 'secret-test-key' not in json.dumps(failed)
    start(jobs,generated,'r2');assert finish(jobs,'r2')['status']=='completed'


def test_cancel_before_delayed_start_is_a_tombstone(prepared):
    _,_,jobs=prepared;jobs.cancel('test','late')
    assert start(jobs,lambda _:pytest.fail('cancelled'),'late')['status']=='cancelled'


def test_session_binding_must_match_before_start(prepared):
    _,_,jobs=prepared
    with pytest.raises(StaleDiagnosis):jobs.start('test','r1','wrong',1,{},generated)


def test_new_request_id_cannot_change_authoritative_topic(prepared):
    _,_,jobs=prepared
    with pytest.raises(StaleDiagnosis):start(jobs,generated,'changed','Python')


def test_old_answer_and_confirmation_cannot_write_after_new_intent(monkeypatch, prepared):
    from fastapi.testclient import TestClient
    from backend import main
    root,user,jobs=prepared
    monkeypatch.setattr(main,'SERVER_ROOT',root)
    monkeypatch.setattr(main,'diagnosis_registry',lambda:jobs)
    start(jobs,generated);job=finish(jobs);session=job['result']
    path=user/'onboarding/diagnostic.json';before=path.read_bytes()
    _atomic_json(user/'onboarding/intent-state.json',{**INTENT,'revision':2})
    client=TestClient(main.app)
    response=client.post('/api/diagnostics/answer',json={'user_id':'test','session_id':session['session_id'],
        'question_id':session['question']['id'],'selected_option_id':session['question']['options'][0]['id']})
    assert response.status_code==409 and path.read_bytes()==before
    response=client.post('/api/onboarding/confirm',json={**job['submission'],'diagnostic_session_id':session['session_id']})
    assert response.status_code==409


def test_http_start_is_202_while_model_blocked_and_guarded(monkeypatch, prepared):
    from fastapi.testclient import TestClient
    from backend import main
    root,_,jobs=prepared
    monkeypatch.setattr(main,'SERVER_ROOT',root)
    monkeypatch.setattr(main,'diagnosis_registry',lambda:jobs)
    monkeypatch.setattr(main,'latest_release',lambda:root)
    gate=threading.Event();entered=threading.Event();calls=[]
    def model(*args,**kwargs):
        calls.append(kwargs);entered.set();gate.wait(2)
        return json.dumps({'topic':'Go','questions':[{'id':f'q{i}','prompt':f'Go变量赋值情境{i}', 'dimension':'Go',
            'options':[{'id':'a','label':'编译报错'},{'id':'b','label':'正确执行'}], 'correct_option_id':'a'} for i in range(3)]})
    monkeypatch.setattr(main,'chat',model)
    payload={'user_id':'test','request_id':'r1','intent_session_id':'intent','intent_revision':1,
        'topic':{'type':'custom','value':'Go'},'level_claim':'some','learning_mode':'practice','goal_route':'gap_upgrade','session_minutes':25}
    client=TestClient(main.app)
    started=time.monotonic();response=client.post('/api/onboarding/diagnosis/start',json=payload)
    assert response.status_code==202 and time.monotonic()-started<.5
    assert entered.wait(1)
    assert client.post('/api/onboarding/diagnosis/start',json=payload).status_code==202
    assert client.get('/api/onboarding/diagnosis/status',params={'user_id':'test','request_id':'r1'}).json()['status']=='running'
    gate.set();assert finish(jobs)['status']=='completed'
    assert len(calls)==1 and calls[0]['sandbox']=='read-only' and calls[0]['timeout']==120


@pytest.fixture
def confirmed_diagnosis(monkeypatch, prepared):
    from fastapi.testclient import TestClient
    from backend import main
    root,user,jobs=prepared
    monkeypatch.setattr(main,'SERVER_ROOT',root)
    monkeypatch.setattr(main,'diagnosis_registry',lambda:jobs)
    def completed(phase):
        session=generated(phase)
        while not session['complete']:
            session=answer_diagnosis(session,session['question']['correct_option_id'],question_id=session['question']['id'])
        return session
    start(jobs,completed);job=finish(jobs)
    payload={**job['submission'],'diagnostic_session_id':job['result']['session_id']}
    client=TestClient(main.app)
    response=client.post('/api/onboarding/confirm',json=payload)
    assert response.status_code==200
    return root,user,jobs,client,payload,response.json()


def test_confirmation_retry_replays_durable_receipt_without_overwriting_plan(monkeypatch, confirmed_diagnosis):
    from backend import main
    root,user,jobs,client,payload,first=confirmed_diagnosis
    before=(user/'learning-state.json').read_bytes()
    plan=user/first['active_plan']
    plan.write_text('Synthetic preserved draft',encoding='utf-8')
    fresh=DiagnosisJobs(root)
    monkeypatch.setattr(main,'diagnosis_registry',lambda:fresh)
    try:
        retry=client.post('/api/onboarding/confirm',json=payload)
        assert retry.status_code==200 and retry.json()==first
        assert (user/'learning-state.json').read_bytes()==before
        assert plan.read_text()=='Synthetic preserved draft'
        assert fresh.current('test')['result']['complete']
    finally:fresh.shutdown()


def test_plan_failure_can_retry_confirmation_without_repeating_questions(confirmed_diagnosis):
    from backend.generation_transaction import cancel_generation
    root,user,jobs,client,payload,first=confirmed_diagnosis
    assert cancel_generation(root,'test',first['generation_id'])
    retry=client.post('/api/onboarding/confirm',json=payload)
    assert retry.status_code==200
    assert retry.json()['generation_id']!=first['generation_id']
    again=client.post('/api/onboarding/confirm',json=payload)
    assert again.json()==retry.json()
    assert jobs.current('test')['result']['complete']


@pytest.mark.parametrize('change',['intent','project','payload'])
def test_confirmation_receipt_never_authorizes_changed_context(confirmed_diagnosis,change):
    _,user,_,client,payload,_=confirmed_diagnosis
    if change=='intent':
        _atomic_json(user/'onboarding/intent-state.json',{**INTENT,'revision':2})
    elif change=='project':
        state=json.loads((user/'learning-state.json').read_text())
        _atomic_json(user/'learning-state.json',{**state,'revision':state['revision']+1,'active_topic':'Python'})
    else:payload={**payload,'session_minutes':40}
    before=(user/'learning-state.json').read_bytes()
    response=client.post('/api/onboarding/confirm',json=payload)
    assert response.status_code==409
    assert (user/'learning-state.json').read_bytes()==before
