import inspect
import json

import pytest
from fastapi.testclient import TestClient

from backend import main
from tests.test_lesson_mutations import setup_lesson


@pytest.fixture
def client(tmp_path, monkeypatch):
    setup_lesson(tmp_path)
    monkeypatch.setattr(main, 'SERVER_ROOT', tmp_path)
    return TestClient(main.app)


def test_mutation_api_contract_and_confirmation(client, monkeypatch, tmp_path):
    state = client.get('/api/lesson/edit-state', params={'user_id': 'test'})
    assert state.status_code == 200
    data = state.json()
    assert data['can_undo'] is False
    base = data['lesson']['revision']
    calls = []
    def model(*args, **kwargs):
        calls.append(kwargs)
        return json.dumps({'pages': [{'id': 'concept', 'title': '更新', 'markdown': '解释', 'code': ''}]})
    monkeypatch.setattr(main, 'chat', model)
    monkeypatch.setattr(main, 'latest_release', lambda: tmp_path)
    proposed = client.post('/api/lesson/proposals', json={'user_id': 'test', 'base_revision': base, 'instruction': '改讲解', 'page_id': 'concept'})
    assert proposed.status_code == 200
    assert not calls
    path = '/api/lesson/proposals/' + proposed.json()['proposal_id']
    assert client.post(path + '/generate', json={'user_id': 'test'}).status_code in {422, 409}
    candidate = client.post(path + '/generate', json={'user_id': 'test', 'confirmed': True})
    assert candidate.status_code == 200
    assert calls[0]['sandbox'] == 'read-only'
    assert client.get(path, params={'user_id': 'test'}).json()['status'] == 'candidate'
    assert client.post(path + '/apply', json={'user_id': 'test'}).status_code in {422, 409}
    applied = client.post(path + '/apply', json={'user_id': 'test', 'confirmed': True})
    assert applied.status_code == 200
    assert applied.json()['revision'] != base
    assert 'answer_keys' not in applied.text
    exported = client.get('/api/lesson/export', params={'user_id': 'test'})
    assert exported.status_code == 200
    assert exported.headers['content-type'].startswith('text/markdown')
    assert '更新' in exported.text
    assert 'answer_keys' not in exported.text


def test_old_manual_endpoints_do_not_bypass_proposals(client, monkeypatch):
    calls = []
    monkeypatch.setattr(main, 'chat', lambda *a, **kw: calls.append(a))
    for path, data in [
        ('/api/lesson/remediate', {'user_id': 'test'}),
        ('/api/practice/supplemental/generate', {'user_id': 'test', 'module': 'Python', 'level': 'beginner', 'count': 1, 'append_to_lesson': True, 'lesson_id': 'python-lesson-01'}),
    ]:
        response = client.post(path, json=data)
        assert response.status_code == 409
        assert response.json()['detail']['recovery'] == 'confirmation_required'
    assert not calls


def test_chat_entrypoints_enforce_readonly_model_calls():
    assert 'sandbox="read-only"' in inspect.getsource(main.chat_once)
    assert 'sandbox="read-only"' in inspect.getsource(main.chat_stream)
