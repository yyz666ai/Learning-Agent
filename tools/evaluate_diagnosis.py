#!/usr/bin/env python3
"""Opt-in paid Vue diagnosis regression: HTTP start/poll/answer, isolated data.

Starts from a saved intent fixture; does not claim to evaluate intent extraction,
Plan, or lessons. Real prompts/results stay in ignored evals/runs.
"""
import json
import logging
import os
from pathlib import Path
import shutil
import sys
import time
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient
from backend import main as api, codex_driver as driver
from backend.diagnosis_jobs import DiagnosisJobs
from backend.user_memory import _atomic_json


def main():
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger('backend.codex_driver').setLevel(logging.INFO)
    logging.getLogger('backend.deepseek_transport').setLevel(logging.INFO)
    run = ROOT / 'evals/runs' / (datetime.now().strftime('%Y%m%d-%H%M%S') + '-diagnosis')
    root = run / 'isolated'
    shutil.copytree(ROOT / 'templates', root / 'templates')
    for key, value in driver.load_secrets(ROOT / '.secrets.env').items():
        if key.startswith('DEEPSEEK_'):
            os.environ[key] = value
    user = root / 'userdir/u_diagnosis_eval'
    onboarding = dict(goal_route='interview_sprint', level_claim='some', learning_mode='practice',
        session_minutes=25, topic_type='custom', concept_scope='not_applicable',
        teaching_preference='balanced', deadline_days=None)
    slots = dict(topic='前端', target_role='前端岗', tech_stack=['Vue'],
                 level_evidence='学过一些', interview_question_source='none')
    _atomic_json(user / 'onboarding/intent-state.json', dict(session_id='vue', revision=1,
        action='ready_for_plan', slots=slots, onboarding=onboarding))
    calls = []
    def model(uid, prompt, release, **kwargs):
        started = time.monotonic()
        result = driver.chat(uid, prompt, release, **kwargs)
        calls.append(dict(seconds=round(time.monotonic()-started, 2), prompt=prompt, output=result))
        _atomic_json(run / 'calls.json', calls)
        return result
    api.SERVER_ROOT = root
    api.latest_release = lambda: ROOT / 'workspace/dev'
    api.chat = model
    jobs = DiagnosisJobs(root)
    api.diagnosis_registry = lambda: jobs
    client = TestClient(api.app)
    payload = {k:v for k,v in onboarding.items() if k != 'topic_type'}
    payload.update(user_id='diagnosis_eval', topic=dict(type='custom', value='前端'),
        request_id='vue-diagnosis', intent_session_id='vue', intent_revision=1)
    report = {'scope': 'saved Vue intent -> real model -> HTTP polling -> answer all questions'}
    started = time.monotonic()
    try:
        response = client.post('/api/onboarding/diagnosis/start', json=payload)
        report['start_seconds'] = round(time.monotonic()-started, 3)
        assert response.status_code == 202, response.text
        while time.monotonic()-started < 260:
            result = client.get('/api/onboarding/diagnosis/status', params={
                'user_id':'diagnosis_eval', 'request_id':'vue-diagnosis'}).json()
            if result['status'] not in {'queued', 'running'}:
                break
            time.sleep(.5)
        report.update(job=result, seconds=round(time.monotonic()-started, 2))
        assert result['status'] == 'completed', result
        session = json.loads((user / 'onboarding/diagnostic.json').read_text())
        report['generated_session'] = session
        assert 'vue' in json.dumps(session, ensure_ascii=False).lower()
        public = result['result']
        report['answers'] = []
        while not public['complete']:
            question = public['question']
            assert 'correct_option_id' not in question
            # Exercise answer handling, not the simulated learner's ability.
            response = client.post('/api/diagnostics/answer', json=dict(user_id='diagnosis_eval',
                session_id=public['session_id'], question_id=question['id'], selected_option_id=question['options'][0]['id']))
            assert response.status_code == 200, response.text
            public = response.json()
            report['answers'].append(public)
        assert public['next'] == 'confirm'
        report['ok'] = True
    except Exception as exc:
        report.update(ok=False, error=str(exc))
    finally:
        jobs.shutdown()
        client.close()
        _atomic_json(run / 'report.json', report)
    print(json.dumps({k: report.get(k) for k in ['ok', 'start_seconds', 'seconds', 'error']}, ensure_ascii=False))
    print(run)
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
