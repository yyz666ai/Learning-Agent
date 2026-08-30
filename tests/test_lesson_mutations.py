import json
from pathlib import Path

import pytest

from backend.lesson_generator import load_lesson_bundle, save_lesson_bundle
from backend.lesson_manifest import build_starter_lesson
from backend.lesson_context import lesson_revision
from backend.practice_bank import PracticeBankStore


def setup_lesson(tmp_path):
    root = tmp_path / 'userdir' / 'u_test'
    root.mkdir(parents=True)
    (root / 'learning-state.json').write_text(json.dumps({'revision': 1, 'active_topic': 'Python', 'active_plan': 'plans/python.md'}))
    (root / 'curriculum.json').write_text(json.dumps({'current_knowledge_point_id': 'starter'}))
    bundle = build_starter_lesson(topic='Python', language='python', session_minutes=25, goal_route='project_building')
    save_lesson_bundle(tmp_path, 'test', bundle)
    return root, load_lesson_bundle(tmp_path, 'test', 'starter')


def service(tmp_path):
    from backend.lesson_mutations import LessonMutationService
    return LessonMutationService(tmp_path, 'test')


def test_save_uses_immutable_pair_and_pointer(tmp_path):
    root, bundle = setup_lesson(tmp_path)
    pointer = root / 'lessons/.versions/starter/current.json'
    assert pointer.exists(), 'lesson writes need one paired-version commit pointer'
    old = pointer.read_bytes()
    save_lesson_bundle(tmp_path, 'test', bundle)
    assert pointer.read_bytes() == old, 'same bundle save must be idempotent'


def test_edit_validates_and_restore_preserves_attempts_and_code(tmp_path):
    root, bundle = setup_lesson(tmp_path)
    bank = PracticeBankStore(tmp_path)
    bank.register_lesson('test', bundle.manifest, answer_keys=bundle.answer_keys)
    bank.record_choice_attempt('test', lesson_id=bundle.manifest.lesson_id, page_id='check-label', selected_option_id='b', correct=True)
    code = root / 'projects/learner.py'
    code.parent.mkdir(parents=True)
    code.write_text('my own work')
    s = service(tmp_path)
    base = lesson_revision(bundle.manifest)
    edited = s.edit(base, 'concept', title='新标题', markdown='新讲解', code='')
    assert edited['revision'] != base
    assert s.state()['can_undo'] is True
    with pytest.raises(ValueError):
        s.edit(edited['revision'], 'check-label', title='quiz', markdown='', code='')
    restored = s.restore(edited['revision'], base)
    loaded = load_lesson_bundle(tmp_path, 'test', 'starter')
    assert loaded.manifest.pages[0].title == bundle.manifest.pages[0].title
    assert loaded.answer_keys == bundle.answer_keys
    assert restored['revision'] not in {base, edited['revision']}
    assert restored['lesson']['quiz_attempts'] == [{'page_id': 'check-label', 'correct': True}]
    assert code.read_text() == 'my own work'
    assert bank.list_items('test')[0]['attempts'] or any(r['attempts'] for r in bank.list_items('test'))
    assert len(service(tmp_path).state()['history']) == 3


def test_proposal_requires_confirmation_and_candidate_is_not_current(tmp_path):
    root, bundle = setup_lesson(tmp_path)
    s = service(tmp_path)
    base = lesson_revision(bundle.manifest)
    proposal = s.propose(base, '补充例子', page_id='concept')
    assert proposal['status'] == 'proposed'
    called = []
    def generate(prompt):
        called.append(prompt)
        return json.dumps({'pages': [{'id': 'concept', 'title': '更清楚', 'markdown': '新解释', 'code': ''}]})
    with pytest.raises(ValueError, match='confirm'):
        s.generate(proposal['proposal_id'], confirmed=False, model_call=generate)
    assert not called
    candidate = s.generate(proposal['proposal_id'], confirmed=True, model_call=generate)
    assert candidate['status'] == 'candidate'
    assert candidate['changes'][0]['before']['title'] == bundle.manifest.pages[0].title
    assert lesson_revision(load_lesson_bundle(tmp_path, 'test', 'starter').manifest) == base
    assert bundle.manifest.pages[1].title in called[0]
    with pytest.raises(ValueError, match='confirm'):
        s.apply(proposal['proposal_id'], confirmed=False)
    applied = s.apply(proposal['proposal_id'], confirmed=True)
    assert applied['lesson']['pages'][0]['title'] == '更清楚'
    assert s.apply(proposal['proposal_id'], confirmed=True) == applied
    assert service(tmp_path).proposal(proposal['proposal_id'])['status'] == 'applied'
    assert 'answer_keys' not in json.dumps(candidate)


def test_cancel_stale_and_cross_project_denial(tmp_path):
    root, bundle = setup_lesson(tmp_path)
    s = service(tmp_path)
    base = lesson_revision(bundle.manifest)
    p = s.propose(base, '改一下', page_id='concept')
    assert s.cancel(p['proposal_id'])['status'] == 'cancelled'
    with pytest.raises(ValueError):
        s.generate(p['proposal_id'], confirmed=True, model_call=lambda _: '')
    p = s.propose(base, '再改一下', page_id='concept')
    s.edit(base, 'concept', title='changed', markdown='', code='')
    with pytest.raises(RuntimeError, match='stale'):
        s.generate(p['proposal_id'], confirmed=True, model_call=lambda _: '')
    new_base = s.state()['lesson']['revision']
    p = s.propose(new_base, '改一下', page_id='concept')
    (root / 'learning-state.json').write_text(json.dumps({'revision': 2, 'active_topic': 'Go'}))
    with pytest.raises(RuntimeError):
        s.generate(p['proposal_id'], confirmed=True, model_call=lambda _: '')


def test_failed_pointer_commit_leaves_pair_and_bank_current(tmp_path, monkeypatch):
    root, bundle = setup_lesson(tmp_path)
    import backend.lesson_versions as versions
    base = lesson_revision(bundle.manifest)
    original = versions._atomic_json
    def fail_pointer(path, payload):
        if path.name == 'current.json':
            raise OSError('disk full')
        return original(path, payload)
    monkeypatch.setattr(versions, '_atomic_json', fail_pointer)
    with pytest.raises(OSError):
        service(tmp_path).edit(base, 'concept', title='cannot save', markdown='', code='')
    current = load_lesson_bundle(tmp_path, 'test', 'starter')
    assert lesson_revision(current.manifest) == base
    assert current.answer_keys == bundle.answer_keys


def test_export_and_legacy_import(tmp_path):
    root, bundle = setup_lesson(tmp_path)
    export = service(tmp_path).export()
    assert '# Python' in export
    assert 'answer_keys' not in export and 'correct_option_id' not in export
    assert bundle.manifest.pages[0].title in export
    legacy = root / 'lessons/legacy.json'
    legacy.write_text(bundle.manifest.model_copy(update={'knowledge_point_id': 'legacy'}).model_dump_json())
    legacy.with_name('legacy.answers.json').write_text(json.dumps(bundle.answer_keys))
    loaded = load_lesson_bundle(tmp_path, 'test', 'legacy')
    assert loaded.answer_keys == bundle.answer_keys
    assert (root / 'lessons/.versions/legacy/current.json').exists()


def test_supplemental_candidate_defers_files_and_restores_current_association(tmp_path):
    root, bundle = setup_lesson(tmp_path)
    s = service(tmp_path)
    base = lesson_revision(bundle.manifest)
    p = s.propose(base, '编程练习', kind='supplemental')
    question = {'kind': 'programming', 'title': '练循环', 'prompt': '循环处理输入', 'hints': ['先定义变量'], 'milestones': [], 'completion_criteria': '能够运行'}
    candidate = s.generate(p['proposal_id'], confirmed=True, model_call=lambda _: json.dumps({'questions': [question]}))
    assert not (root / 'projects').exists()
    assert not (root / 'practice-bank').exists()
    applied = s.apply(p['proposal_id'], confirmed=True)
    page = next(page for page in applied['lesson']['pages'] if page['id'].startswith('supplemental-'))
    readme = root / page['practice_path'] / 'README.md'
    assert readme.exists()
    own_code = readme.parent / 'main.py'
    own_code.write_text('user work')
    s.restore(applied['revision'], base)
    assert own_code.read_text() == 'user work'
    record = next(item for item in PracticeBankStore(tmp_path).list_items('test') if item['page_id'] == page['id'])
    assert record['current_lesson'] is False


def test_supplemental_private_explanations_survive_reload_without_preview_leak(tmp_path):
    root, bundle = setup_lesson(tmp_path)
    s = service(tmp_path)
    p = s.propose(lesson_revision(bundle.manifest), '加选择题', kind='supplemental')
    question = {'title': '新问题', 'prompt': '选择正确说法？', 'options': [{'id': 'a', 'label': '是'}, {'id': 'b', 'label': '否'}], 'correct_option_id': 'a', 'explanation': 'PRIVATE EXPLANATION'}
    preview = s.generate(p['proposal_id'], confirmed=True, model_call=lambda _: json.dumps({'questions': [question]}))
    assert 'PRIVATE EXPLANATION' not in json.dumps(preview)
    s.apply(p['proposal_id'], confirmed=True)
    record = next(r for r in PracticeBankStore(tmp_path).list_items('test') if r['page_id'].startswith('supplemental-'))
    assert record['explanation'] == 'PRIVATE EXPLANATION'
    reloaded = load_lesson_bundle(tmp_path, 'test', 'starter')
    assert reloaded.explanations[record['page_id']] == 'PRIVATE EXPLANATION'
    PracticeBankStore(tmp_path).register_lesson('test', reloaded.manifest, answer_keys=reloaded.answer_keys)
    assert next(r for r in PracticeBankStore(tmp_path).list_items('test') if r['id'] == record['id'])['explanation'] == 'PRIVATE EXPLANATION'


def test_duplicate_propose_and_generate_are_idempotent_and_stale_candidate_rejected(tmp_path):
    root, bundle = setup_lesson(tmp_path)
    s = service(tmp_path)
    base = lesson_revision(bundle.manifest)
    p = s.propose(base, '改标题', page_id='concept')
    assert s.propose(base, '改标题', page_id='concept')['proposal_id'] == p['proposal_id']
    def model(_):
        concurrent = s.generate(p['proposal_id'], confirmed=True, model_call=lambda _: pytest.fail('duplicate model call'))
        assert concurrent['status'] == 'generating'
        return json.dumps({'pages': [{'id': 'concept', 'title': 'new', 'markdown': '', 'code': ''}]})
    s.generate(p['proposal_id'], confirmed=True, model_call=model)
    s.edit(base, 'concept', title='other edit', markdown='', code='')
    with pytest.raises(RuntimeError, match='stale'):
        s.generate(p['proposal_id'], confirmed=True, model_call=lambda _: pytest.fail('stale model call'))


def test_interrupted_proposal_recovers_and_failure_does_not_replace_current(tmp_path):
    root, bundle = setup_lesson(tmp_path)
    s = service(tmp_path)
    base = lesson_revision(bundle.manifest)
    p = s.propose(base, '改标题', page_id='concept')
    path = root / 'lessons/.proposals' / (p['proposal_id'] + '.json')
    value = json.loads(path.read_text())
    value['status'] = 'generating'
    path.write_text(json.dumps(value))
    assert service(tmp_path).proposal(p['proposal_id'])['status'] == 'proposed'
    with pytest.raises(ValueError):
        s.generate(p['proposal_id'], confirmed=True, model_call=lambda _: 'invalid output')
    assert s.proposal(p['proposal_id'])['status'] == 'proposed'
    assert s.state()['lesson']['revision'] == base


def test_answer_only_snapshot_and_restore_keep_new_revision_and_answer_pair(tmp_path):
    root, bundle = setup_lesson(tmp_path)
    s = service(tmp_path)
    base = lesson_revision(bundle.manifest)
    from backend.lesson_manifest import LessonBundle
    changed = LessonBundle(bundle.manifest.model_copy(deep=True), {'check-label': 'a'})
    save_lesson_bundle(tmp_path, 'test', changed)
    new_base = lesson_revision(changed.manifest)
    assert new_base != base
    assert load_lesson_bundle(tmp_path, 'test', 'starter').answer_keys['check-label'] == 'a'
    s.restore(new_base, base)
    assert load_lesson_bundle(tmp_path, 'test', 'starter').answer_keys['check-label'] == 'b'
    assert next(item for item in PracticeBankStore(tmp_path).list_items('test') if item['page_id'] == 'check-label')['correct_option_id'] == 'b'


def revised_quiz_payload():
    return {'pages': [{'id': 'check-label', 'title': '新题目', 'markdown': '先判断再选择', 'code': '',
                       'question': '变量里保存了什么？', 'options': [{'id': 'a', 'label': '一个值'}, {'id': 'b', 'label': '不存在的数据'}]}],
            'answer_keys': {'check-label': 'a'}}


def test_ai_quiz_revision_pairs_answers_and_restores_original_evidence(tmp_path):
    root, original = setup_lesson(tmp_path)
    bank = PracticeBankStore(tmp_path)
    bank.register_lesson('test', original.manifest, answer_keys=original.answer_keys)
    bank.record_choice_attempt('test', lesson_id=original.manifest.lesson_id, page_id='check-label', selected_option_id='b', correct=True)
    s = service(tmp_path)
    base = lesson_revision(original.manifest)
    p = s.propose(base, '改写本题', page_id='check-label')
    preview = s.generate(p['proposal_id'], confirmed=True, model_call=lambda _: json.dumps(revised_quiz_payload()))
    assert preview['changes'][0]['after']['question'] == '变量里保存了什么？'
    assert 'answer_keys' not in json.dumps(preview) and 'correct_option_id' not in json.dumps(preview)
    assert load_lesson_bundle(tmp_path, 'test', 'starter').answer_keys['check-label'] == 'b'
    applied = s.apply(p['proposal_id'], confirmed=True)
    assert applied['lesson']['quiz_attempts'] == []
    updated = load_lesson_bundle(tmp_path, 'test', 'starter')
    assert updated.answer_keys['check-label'] == 'a'
    assert updated.manifest.pages[0] == original.manifest.pages[0]
    record = next(r for r in bank.list_items('test') if r['page_id'] == 'check-label')
    assert record['status'] == 'unattempted' and len(record['attempts']) == 1
    old_question_revision = record['attempts'][0]['question_revision']
    assert record['question_revision'] != old_question_revision
    bank.record_choice_attempt('test', lesson_id=original.manifest.lesson_id, page_id='check-label', selected_option_id='a', correct=True)
    restored = s.restore(applied['revision'], base)
    assert restored['lesson']['quiz_attempts'] == [{'page_id': 'check-label', 'correct': True}]
    record = next(r for r in bank.list_items('test') if r['page_id'] == 'check-label')
    assert record['question_revision'] == old_question_revision
    assert record['correct_option_id'] == 'b' and len(record['attempts']) == 2
    assert record['status'] == 'mastered'


@pytest.mark.parametrize('keys', [None, {}, {'check-label': 'wrong'}, {'other-page': 'a'}])
def test_ai_quiz_candidate_rejects_unpaired_or_invalid_answers(tmp_path, keys):
    root, bundle = setup_lesson(tmp_path)
    s = service(tmp_path)
    base = lesson_revision(bundle.manifest)
    p = s.propose(base, '改写本题', page_id='check-label')
    payload = revised_quiz_payload()
    payload['answer_keys'] = keys
    with pytest.raises(ValueError):
        s.generate(p['proposal_id'], confirmed=True, model_call=lambda _: json.dumps(payload))
    assert s.state()['lesson']['revision'] == base


def test_each_immutable_version_has_matching_private_safe_markdown_projection(tmp_path):
    root, bundle = setup_lesson(tmp_path)
    s = service(tmp_path)
    base = lesson_revision(bundle.manifest)
    initial = root / 'lessons/.versions/starter' / base / 'lesson.md'
    assert initial.is_file(), 'persist deterministic Markdown beside each version'
    text = initial.read_text()
    assert base in text and 'check-label' in text
    assert text == s.export()
    assert 'answer_keys' not in text and 'correct_option_id' not in text
    edited = s.edit(base, 'concept', title='新标题', markdown='新正文', code='')
    assert initial.read_text() == text
    next_file = initial.parent.parent / edited['revision'] / 'lesson.md'
    assert next_file.read_text() == s.export()
    assert edited['revision'] in s.export()


def test_failed_edit_does_not_erase_concurrent_answer(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    root, bundle = setup_lesson(tmp_path)
    bank = PracticeBankStore(tmp_path)
    bank.register_lesson('test', bundle.manifest, answer_keys=bundle.answer_keys)
    entered, release = Event(), Event()
    def failed_register(*args, **kwargs):
        entered.set()
        assert release.wait(3)
        raise OSError('disk failed')
    monkeypatch.setattr(PracticeBankStore, 'register_lesson', failed_register)
    def edit():
        with pytest.raises(OSError):
            service(tmp_path).edit(lesson_revision(bundle.manifest), 'concept', title='new', markdown='', code='')
    with ThreadPoolExecutor(max_workers=2) as pool:
        editing = pool.submit(edit)
        assert entered.wait(3)
        answer = pool.submit(bank.record_choice_attempt, 'test', lesson_id=bundle.manifest.lesson_id,
                             page_id='check-label', selected_option_id='b', correct=True)
        try:
            from concurrent.futures import TimeoutError
            with pytest.raises(TimeoutError):
                answer.result(timeout=0.1)
        finally:
            release.set()
        editing.result(timeout=3)
        answer.result(timeout=3)
    assert len(next(r for r in bank.list_items('test') if r['page_id'] == 'check-label')['attempts']) == 1


def test_legacy_import_preserves_raw_snapshot_before_compatibility_upgrade(tmp_path):
    root = tmp_path / 'userdir/u_test/lessons'
    root.mkdir(parents=True)
    bundle = build_starter_lesson(topic='Python', language='python', session_minutes=25, goal_route='foundation_engineer')
    payload = bundle.manifest.model_dump()
    payload['completion_mode'] = 'output'
    payload['pages'][1]['code'] = 'print("hello")'
    (root / 'starter.json').write_text(json.dumps(payload))
    (root / 'starter.answers.json').write_text(json.dumps(bundle.answer_keys))
    loaded = load_lesson_bundle(tmp_path, 'test', 'starter')
    from backend.lesson_versions import LessonVersionStore
    versions = LessonVersionStore(tmp_path, 'test', 'starter')
    history = versions.history()
    assert len(history) == 2
    original = versions.load(history[0]['revision'])
    assert original.manifest.completion_mode == 'output'
    assert original.manifest.pages[1].code == 'print("hello")'
    assert loaded.manifest.completion_mode == 'self_practice'
    assert loaded.manifest.pages[1].code != original.manifest.pages[1].code
    (root.parent / 'learning-state.json').write_text(json.dumps({'revision': 1, 'active_topic': 'Python'}))
    (root.parent / 'curriculum.json').write_text(json.dumps({'current_knowledge_point_id': 'starter'}))
    restored = service(tmp_path).restore(lesson_revision(loaded.manifest), history[0]['revision'])
    assert restored['lesson']['completion_mode'] == 'output'
    assert restored['lesson']['pages'][1]['code'] == 'print("hello")'


def test_revised_question_never_reuses_old_private_explanation(tmp_path):
    root, original = setup_lesson(tmp_path)
    from backend.lesson_manifest import LessonBundle
    pages = [page.model_copy(update={'completion_criteria': None}) if page.id == 'check-label' else page for page in original.manifest.pages]
    bundle = LessonBundle(original.manifest.model_copy(update={'pages': pages}), original.answer_keys,
                          {'check-label': 'OLD PRIVATE EXPLANATION'})
    save_lesson_bundle(tmp_path, 'test', bundle)
    bank = PracticeBankStore(tmp_path)
    bank.register_lesson('test', bundle.manifest, answer_keys=bundle.answer_keys)
    assert next(r for r in bank.list_items('test') if r['page_id'] == 'check-label')['explanation'] == 'OLD PRIVATE EXPLANATION'
    s = service(tmp_path)
    p = s.propose(lesson_revision(bundle.manifest), '改题', page_id='check-label')
    s.generate(p['proposal_id'], confirmed=True, model_call=lambda _: json.dumps(revised_quiz_payload()))
    s.apply(p['proposal_id'], confirmed=True)
    assert next(r for r in bank.list_items('test') if r['page_id'] == 'check-label')['explanation'] != 'OLD PRIVATE EXPLANATION'
