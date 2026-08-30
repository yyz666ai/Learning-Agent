import json

import pytest
from fastapi.testclient import TestClient

from backend import main
from backend.curriculum import curriculum_from_plan, load_curriculum, save_curriculum
from backend.lesson_generator import load_lesson_bundle, save_lesson_bundle
from backend.lesson_manifest import build_starter_lesson
from backend.lesson_mutations import LessonMutationService
from tests.test_curriculum import GO_PLAN
from tests.test_lesson_mutations import revised_quiz_payload


@pytest.fixture
def course(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'SERVER_ROOT', tmp_path)
    monkeypatch.setattr(main, 'latest_release', lambda: None)
    client = TestClient(main.app)
    client.post('/api/onboarding/confirm', json={'user_id': 'test', 'learning_mode': 'systematic',
                'goal_route': 'foundation_engineer', 'level_claim': 'zero', 'topic': {'type': 'go', 'value': 'Go'}, 'session_minutes': 25})
    curriculum = curriculum_from_plan(GO_PLAN, topic='Go', route='foundation_engineer', level='zero')
    save_curriculum(tmp_path, 'test', curriculum)
    bundle = build_starter_lesson(topic='Go', language='go', session_minutes=25, goal_route='foundation_engineer')
    bundle.manifest.knowledge_point_id = curriculum.current_knowledge_point_id
    bundle.manifest.chapter_id = curriculum.current_chapter().id
    bundle.manifest.covered_knowledge_point_ids = [p.id for p in curriculum.current_chapter_remaining_points()]
    save_lesson_bundle(tmp_path, 'test', bundle)
    return client, bundle, curriculum, tmp_path


def check(client, bundle, option='b'):
    result = client.post('/api/lesson/check', json={'user_id': 'test', 'lesson_id': bundle.manifest.lesson_id,
                         'page_id': 'check-label', 'selected_option_id': option, 'revision': bundle.public_manifest()['revision']})
    assert result.status_code == 200 and result.json()['correct'] is True


def complete(client, bundle, **extra):
    return client.post('/api/lesson/complete', json={'user_id': 'test', 'lesson_id': bundle.manifest.lesson_id,
                       'action': 'submit', 'quiz_attempts': [{'page_id': 'check-label', 'correct': True}], **extra})


def test_client_claimed_pass_cannot_advance_without_server_answer(course):
    client, bundle, curriculum, root = course
    response = complete(client, bundle)
    assert response.status_code == 200
    assert response.json()['verdict'] == 'practice'
    assert load_curriculum(root, 'test').current_knowledge_point_id == curriculum.current_knowledge_point_id


def test_old_question_pass_cannot_complete_revised_quiz(course):
    client, bundle, curriculum, root = course
    check(client, bundle)
    old_revision = bundle.public_manifest()['revision']
    service = LessonMutationService(root, 'test')
    proposal = service.propose(old_revision, '改题', page_id='check-label')
    service.generate(proposal['proposal_id'], confirmed=True, model_call=lambda _: json.dumps(revised_quiz_payload()))
    service.apply(proposal['proposal_id'], confirmed=True)
    response = complete(client, bundle)
    assert response.status_code == 200 and response.json()['verdict'] == 'practice'
    stale = complete(client, bundle, revision=old_revision)
    assert stale.status_code == 409
    current = load_lesson_bundle(root, 'test', curriculum.current_knowledge_point_id)
    check(client, current, 'a')
    completed = complete(client, current, revision=current.public_manifest()['revision'])
    assert completed.status_code == 200 and completed.json()['verdict'] == 'advance'


@pytest.mark.parametrize('change', ['project', 'lesson'])
def test_late_text_evaluation_cannot_commit_to_changed_project_or_lesson(course, monkeypatch, change):
    client, bundle, curriculum, root = course
    bundle.manifest.completion_mode = 'text'
    save_lesson_bundle(root, 'test', bundle)
    check(client, bundle)
    monkeypatch.setattr(main, 'latest_release', lambda: root)
    def evaluate(*args, **kwargs):
        assert kwargs['sandbox'] == 'read-only'
        if change == 'project':
            state_path = root / 'userdir/u_test/learning-state.json'
            state = json.loads(state_path.read_text())
            state.update(active_topic='another project', revision=state['revision'] + 1)
            state_path.write_text(json.dumps(state))
        else:
            current = load_lesson_bundle(root, 'test', curriculum.current_knowledge_point_id)
            current.manifest.pages[0].title = 'new lesson version'
            save_lesson_bundle(root, 'test', current)
        return json.dumps({'verdict': 'advance', 'feedback': '可以继续', 'mastery_score': 90})
    monkeypatch.setattr(main, 'chat', evaluate)
    response = complete(client, bundle)
    assert response.status_code == 409
    assert load_curriculum(root, 'test').current_knowledge_point_id == curriculum.current_knowledge_point_id
    assert not (root / 'userdir/u_test/attempts/lesson-completions.jsonl').exists()
