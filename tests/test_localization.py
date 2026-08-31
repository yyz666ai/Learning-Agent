import json
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from backend import localization as loc


def test_preferences_default_and_atomic_update(tmp_path):
    assert loc.read_preferences(tmp_path, 'alice')['locale'] == 'zh-CN'
    folder = tmp_path / 'userdir/u_alice'
    folder.mkdir(parents=True)
    (folder / 'preferences.json').write_text('{"theme":"light"}')
    assert loc.save_preferences(tmp_path, 'alice', 'en') == {'theme': 'light', 'locale': 'en'}
    assert loc.read_preferences(tmp_path, 'alice')['locale'] == 'en'
    assert loc.read_preferences(tmp_path, 'bob')['locale'] == 'zh-CN'
    with pytest.raises(ValueError):
        loc.save_preferences(tmp_path, '../alice', 'en')
    with pytest.raises(ValueError):
        loc.save_preferences(tmp_path, 'alice', 'fr')


def test_locale_scope_and_worker_snapshot():
    assert loc.current_locale() == 'zh-CN'
    with ThreadPoolExecutor(max_workers=1) as pool:
        with loc.locale_context('en'):
            future = loc.submit_localized(pool, loc.current_locale)
            assert 'English' in loc.language_instruction()
        assert future.result() == 'en'
    assert loc.current_locale() == 'zh-CN'


def test_english_comments_are_valid_but_missing_comments_still_fail():
    from backend.lesson_generator import _validate_commented_progressive_code
    from backend.lesson_manifest import LessonPage
    page = LessonPage(id='example', type='example', title='Example', code='x = 1 # Store a starting value\nprint(x)')
    with loc.locale_context('en'):
        _validate_commented_progressive_code([page])
        with pytest.raises(ValueError):
            _validate_commented_progressive_code([page.model_copy(update={'code': 'print(1)'})])


def test_generation_registry_keeps_locale():
    from backend.generation_jobs import GenerationJobRegistry
    jobs = GenerationJobRegistry()
    try:
        with loc.locale_context('en'):
            jobs.start('alice', 'example', lambda: {'locale': loc.current_locale()})
        for _ in range(100):
            result = jobs.get('alice', 'example')
            if result['status'] == 'completed':
                break
            time.sleep(.01)
        assert result['result']['locale'] == 'en'
        assert result['locale'] == 'en'
    finally:
        jobs._executor.shutdown()


def test_preferences_api(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from backend import main
    monkeypatch.setattr(main, 'SERVER_ROOT', tmp_path)
    with TestClient(main.app) as client:
        assert client.get('/api/preferences?user_id=alice').json()['locale'] == 'zh-CN'
        assert client.put('/api/preferences', json={'user_id':'alice','locale':'en'}).json()['locale'] == 'en'
        assert client.get('/api/preferences?user_id=alice').json()['locale'] == 'en'
        assert client.put('/api/preferences', json={'user_id':'alice','locale':'bad'}).status_code == 422


ENGLISH_PLAN = '''# Python learning plan
## Current task
Run a small Python program and explain its output.
## Learning outcomes
Independently write and debug a small command line program.
## Teaching strategy
Build intuition, then practice and check understanding with concrete examples.
### Stage 1: Variables
- What to learn: Variables and values
- Practice: Write a greeting program and change its input twice.
- Completion evidence: Explain and run the modified program independently.
- Estimated sessions: 2
- Session minutes: 25
- Homework minutes: 20
#### Knowledge points
- Variables
- Printing
- Strings
- Input
- Formatting
'''


def test_english_plan_stays_english_and_builds_curriculum():
    from backend.learning_plan_personalizer import normalize_and_validate_plan
    from backend.curriculum import curriculum_from_plan
    from backend.learning_content import parse_markdown_plan
    with loc.locale_context('en'):
        plan = normalize_and_validate_plan(ENGLISH_PLAN, 'Python', 'gap_upgrade')
        assert plan and '## Current task' in plan and '本阶段' not in plan
        curriculum = curriculum_from_plan(plan, topic='Python', route='gap_upgrade', level='zero')
        assert len(curriculum.chapters) == 1
        assert curriculum.chapters[0].title == 'Variables'
        assert len(curriculum.chapters[0].knowledge_points) == 5
        assert parse_markdown_plan(plan)['stages']
        from backend.curriculum import render_curriculum_plan
        assert '详细' not in render_curriculum_plan(curriculum)


def test_old_lesson_validation_uses_content_not_interface_language():
    from tests.test_lesson_semantic_review import payload
    from backend.lesson_generator import parse_lesson_response
    from backend.lesson_mutations import validate_bundle
    value = payload()
    value['pages'][0]['code'] = 'print(1) # 打印当前值'
    bundle = parse_lesson_response(json.dumps(value), topic='Vue', route='concept_clarity',knowledge_point_id='terminal',session_minutes=25)
    with loc.locale_context('en'):
        assert validate_bundle(bundle).manifest.locale == 'zh-CN'


def test_english_experience_is_explicit():
    from backend.learning_intent import _level_from_text
    assert _level_from_text('I have some experience with Python') == 'some'
    assert _level_from_text('I have no coding experience') == 'zero'


def test_english_plan_bold_title_is_a_recoverable_display_format():
    from backend.learning_plan_personalizer import normalize_and_validate_plan
    plan = ENGLISH_PLAN.replace('# Python learning plan', '**Learning plan: Python variables**')
    with loc.locale_context('en'):
        assert normalize_and_validate_plan(plan, 'Python', 'gap_upgrade').startswith('# Learning plan: Python variables')


def test_missing_english_plan_title_and_cached_deck_remain_english():
    from backend.learning_plan_personalizer import normalize_and_validate_plan
    from backend.curriculum import curriculum_from_plan
    from backend.lesson_generator import parse_lesson_response
    from backend.knowledge_library import _render_atom, _render_deck
    from tests.test_lesson_semantic_review import payload
    with loc.locale_context('en'):
        plan = normalize_and_validate_plan(ENGLISH_PLAN.split('\n', 1)[1].strip(), 'Python', 'gap_upgrade')
        assert plan.startswith('# Python learning plan')
        course = curriculum_from_plan(plan, topic='Python', route='gap_upgrade', level='zero')
        bundle = parse_lesson_response(json.dumps(payload()), topic='Vue', route='concept_clarity', knowledge_point_id='terminal', session_minutes=25)
    assert '<html lang="en">' in _render_deck(bundle)
    assert '## Lesson content' in _render_atom(course, bundle)


def test_fenced_english_plan_preserves_language():
    from backend.learning_plan_personalizer import normalize_and_validate_plan
    assert normalize_and_validate_plan('```markdown\n' + ENGLISH_PLAN + '\n```', 'Python', 'gap_upgrade') == normalize_and_validate_plan(ENGLISH_PLAN, 'Python', 'gap_upgrade')


def test_manual_code_edit_preserves_original_comment_language(tmp_path):
    from tests.test_lesson_mutations import setup_lesson, service
    from backend.lesson_context import lesson_revision
    _, bundle = setup_lesson(tmp_path)
    page = next(p for p in bundle.manifest.pages if p.code and not p.question)
    with loc.locale_context('en'):
        result = service(tmp_path).edit(lesson_revision(bundle.manifest), page.id, title=page.title, markdown=page.markdown, code=page.code + '\n')
    assert result['revision'] != lesson_revision(bundle.manifest)


def test_pre_locale_snapshot_hash_can_edit_and_restore(tmp_path):
    from tests.test_lesson_mutations import setup_lesson, service
    from backend.lesson_context import _digest
    root, bundle = setup_lesson(tmp_path)
    legacy = bundle.manifest.model_dump()
    legacy.pop('locale')
    for page in legacy['pages']:
        page.pop('locale')
    identity = dict(legacy)
    identity.pop('progress')
    for key in ('planned_sessions', 'session_minutes', 'homework_minutes'):
        if identity.get(key) is None:
            identity.pop(key, None)
    old_hash = _digest(identity)
    folder = root / 'lessons/.versions/starter'
    meta = {'revision':old_hash, 'created_at':'2026-08-30T00:00:00Z', 'reason':'generated'}
    (folder / f'{old_hash}.json').write_text(json.dumps({**meta, 'manifest':legacy, 'answer_keys':bundle.answer_keys}))
    (folder / 'current.json').write_text(json.dumps({**meta, 'history':[meta]}))
    s = service(tmp_path)
    assert s.state()['lesson']['revision'] == old_hash
    edited = s.edit(old_hash, 'concept', title='Changed', markdown='Updated explanation', code='')
    restored = s.restore(edited['revision'], old_hash)
    assert restored['lesson']['pages'][0]['title'] == bundle.manifest.pages[0].title


def test_proposal_keeps_creation_locale_after_interface_switch(tmp_path):
    from tests.test_lesson_mutations import setup_lesson, service
    from backend.lesson_context import lesson_revision
    _, bundle = setup_lesson(tmp_path)
    s = service(tmp_path)
    with loc.locale_context('en'):
        proposal = s.propose(lesson_revision(bundle.manifest), 'Add a short explanation', page_id='concept')
    assert proposal['locale'] == 'en'
    def model(prompt):
        assert loc.current_locale() == 'en'
        return json.dumps({'pages':[{'id':'concept','title':'Example','markdown':'English explanation','code':''}],'answer_keys':{}})
    with loc.locale_context('zh-CN'):
        assert s.generate(proposal['proposal_id'], confirmed=True, model_call=model)['status'] == 'candidate'


def test_english_supplemental_page_framework_is_english():
    from backend.lesson_generator import parse_lesson_response
    from backend.supplemental_practice import parse_supplemental_response, append_supplemental_questions
    from tests.test_lesson_semantic_review import payload
    bundle = parse_lesson_response(json.dumps(payload()),topic='Vue',route='concept_clarity',knowledge_point_id='terminal',session_minutes=25)
    questions = parse_supplemental_response(json.dumps({'questions':[{'kind':'project','title':'Build a greeting','prompt':'Create a greeting program.','milestones':['Create a variable','Print it'],'hints':['Start with one line'],'completion_criteria':'Run and explain the program.'}]}),expected_count=1)
    with loc.locale_context('en'):
        added = append_supplemental_questions(bundle,questions).manifest.pages[-2]
    assert added.locale == 'en'
    assert 'Milestones' in added.markdown and '里程碑' not in added.markdown


def test_omitted_english_completion_prompt_has_english_default():
    from backend.lesson_generator import parse_lesson_response
    from tests.test_lesson_semantic_review import payload
    with loc.locale_context('en'):
        bundle = parse_lesson_response(json.dumps(payload()),topic='Vue',route='concept_clarity',knowledge_point_id='terminal',session_minutes=25)
    assert bundle.manifest.completion_prompt.startswith('Complete')
