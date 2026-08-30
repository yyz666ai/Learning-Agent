from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend import main
from backend.lesson_context import lesson_revision
from backend.lesson_manifest import build_starter_lesson
from backend.user_memory import read_conversation_events


@pytest.fixture
def lesson_api(tmp_path, monkeypatch):
    bundle = build_starter_lesson(topic="Go", language="go", session_minutes=20, goal_route="foundation_engineer")
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    monkeypatch.setattr(main, "latest_release", lambda: Path("/fixture"))
    monkeypatch.setattr(main, "read_learning_context", lambda *_: {"profile_status":"confirmed", "topic":"Go"})
    monkeypatch.setattr(main, "read_state", lambda *_: {"state":{"profile_status":"confirmed"}})
    monkeypatch.setattr(main, "load_curriculum", lambda *_: SimpleNamespace(current_knowledge_point_id="starter"))
    monkeypatch.setattr(main, "load_lesson_bundle", lambda *_: bundle)
    return TestClient(main.app), bundle, tmp_path


def test_quote_validates_before_model_and_survives_reload(lesson_api, monkeypatch):
    client, bundle, root = lesson_api
    prompts = []
    def stream(*args, **kwargs):
        prompts.append(args[1])
        yield {"event":"message.delta","data":{"text":"这是程序包声明。"}}
        yield {"event":"done","data":{}}
    monkeypatch.setattr(main, "stream_chat", stream)
    ref = {"lesson_id":bundle.manifest.lesson_id,"page_id":"example","revision":lesson_revision(bundle.manifest),"quote":"package main"}
    response = client.post("/api/chat/stream", json={"user_id":"test", "message":"这是什么意思", "lesson_id":bundle.manifest.lesson_id,"reference":ref})
    assert response.status_code == 200
    assert "package main" in prompts[0]
    history = client.get("/api/chat/history?user_id=test").json()["messages"]
    assert [event["role"] for event in history] == ["user", "assistant"]
    assert history[0]["reference"]["quote"] == "package main"
    ref["revision"] = "0" * 64
    response = client.post("/api/chat/stream", json={"user_id":"test", "message":"这是什么意思", "lesson_id":bundle.manifest.lesson_id,"reference":ref})
    assert response.status_code == 409
    assert len(prompts) == 1


def test_stream_failure_does_not_save_partial_answer_as_completed(lesson_api, monkeypatch):
    client, bundle, root = lesson_api
    def stream(*args, **kwargs):
        yield {"event":"message.delta","data":{"text":"半句回答"}}
        yield {"event":"error","data":{"message":"断开"}}
    monkeypatch.setattr(main, "stream_chat", stream)
    client.post("/api/chat/stream", json={"user_id":"test","message":"开始模拟面试","lesson_id":bundle.manifest.lesson_id})
    events = read_conversation_events(root, "test")
    assert len(events) == 1
    assert events[0]["role"] == "user"
    assert events[0]["chat_mode"] == "interview"
