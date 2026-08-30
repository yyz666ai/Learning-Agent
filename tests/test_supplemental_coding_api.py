import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from backend import main
from backend.lesson_manifest import build_starter_lesson
from backend.lesson_generator import save_lesson_bundle, load_lesson_bundle
from backend.practice_bank import PracticeBankStore
from backend.lesson_context import lesson_revision


def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    monkeypatch.setattr(main, "latest_release", lambda: Path("/fixture"))
    bundle = build_starter_lesson(topic="Go", language="go", session_minutes=20, goal_route="gap_upgrade")
    save_lesson_bundle(tmp_path, "test", bundle)
    user_root = tmp_path / 'userdir/u_test'
    (user_root / 'learning-state.json').write_text(json.dumps({'revision': 1, 'active_topic': 'Go'}))
    (user_root / 'curriculum.json').write_text(json.dumps({'current_knowledge_point_id': 'starter'}))
    return TestClient(main.app), bundle


def confirmed_supplemental(client, bundle, instruction='追加项目练习'):
    proposal = client.post('/api/lesson/proposals', json={'user_id': 'test', 'base_revision': lesson_revision(bundle.manifest), 'instruction': instruction, 'kind': 'supplemental'})
    assert proposal.status_code == 200, proposal.text
    path = '/api/lesson/proposals/' + proposal.json()['proposal_id']
    candidate = client.post(path + '/generate', json={'user_id': 'test', 'confirmed': True})
    assert candidate.status_code == 200, candidate.text
    return client.post(path + '/apply', json={'user_id': 'test', 'confirmed': True})


def project():
    return {"kind":"project","title":"并发下载器","prompt":"实现可取消的并发下载器并排查泄漏。","milestones":["实现单请求与错误处理","加入并发取消并补泄漏测试"],"hints":["先追踪 context 的传播"],"completion_criteria":"取消后所有 worker 退出，测试可重复运行。"}


def test_full_instruction_becomes_project_in_lesson_and_bank(tmp_path, monkeypatch):
    client, bundle = setup(tmp_path, monkeypatch)
    prompts = []
    monkeypatch.setattr(main, "chat", lambda *args, **kwargs: (prompts.append(args[1]) or json.dumps({"questions":[project()]},ensure_ascii=False)))
    response = confirmed_supplemental(client, bundle, '再给一个更难的并发项目，要分步引导')
    assert response.status_code == 200, response.text
    assert "再给一个更难的并发项目，要分步引导" in prompts[0]
    assert "project-practice/SKILL.md" in prompts[0]
    assert len(response.json()['lesson']['pages']) == len(bundle.manifest.pages) + 1
    page = next(page for page in response.json()["lesson"]["pages"] if page["id"].startswith("supplemental-"))
    assert page["type"] == "practice" and page["options"] == []
    assert (tmp_path / "userdir/u_test" / page["practice_path"] / "README.md").is_file()
    records = PracticeBankStore(tmp_path).list_items("test")
    assert any(item["page_id"] == page["id"] and item["kind"] == "homework" for item in records)
    assert len(load_lesson_bundle(tmp_path,"test","starter").manifest.pages) == 6


def test_bank_failure_rolls_back_lesson_and_owned_exercise_document(tmp_path, monkeypatch):
    client, bundle = setup(tmp_path, monkeypatch)
    monkeypatch.setattr(main,"chat",lambda *_, **kwargs:json.dumps({"questions":[project()]},ensure_ascii=False))
    def fail(*args, **kwargs):
        raise OSError("disk full")
    monkeypatch.setattr(PracticeBankStore,"register_lesson",fail)
    response = confirmed_supplemental(client, bundle)
    assert response.status_code == 502
    assert len(load_lesson_bundle(tmp_path,"test","starter").manifest.pages) == 5
    assert not list((tmp_path/"userdir/u_test/projects").glob("**/supplemental-*/README.md"))
