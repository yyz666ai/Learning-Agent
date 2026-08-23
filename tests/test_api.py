from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from backend import main
from backend.curriculum import curriculum_from_plan
from backend.lesson_generator import parse_lesson_response
from backend.practice_bank import PracticeBankStore
from backend import review_material
from backend.review_material import append_learning_question
from backend import project_snapshot
from tests.test_curriculum import GO_PLAN
from tests.test_lesson_generator import model_lesson_json


@pytest.fixture
def client() -> TestClient:
    return TestClient(main.app)


def deep_mastery_plan(topic: str = "Go") -> str:
    stages = []
    for index in range(1, 13):
        title = "毕业项目交付" if index == 12 else f"具体能力 {index}"
        stages.append(
            f"### 阶段 {index}：{title}\n"
            "#### 知识点\n"
            f"- {topic} 原子知识 {index}.1\n"
            f"- {topic} 原子知识 {index}.2\n"
            f"- 本阶段要学：围绕 {topic} 能力 {index} 建立可迁移理解\n"
            f"- 练习：完成 {topic} 阶段任务 {index}\n"
            f"- 完成证据：留下 {topic} 独立产出 {index}\n"
            "- 预计课次：2"
        )
    return (
        f"# {topic} 从零到工程师学习计划\n\n"
        "## 当前任务\n先建立运行直觉。\n\n"
        "## 学习成果\n能够独立设计、实现、测试、调试和交付。\n\n"
        "## 教学策略\n由浅入深，课堂、课后、项目和延迟复习结合。\n\n"
        "## 知识覆盖地图\n- 基础与运行时\n- 数据与控制流\n- 调试与测试\n- 工程、性能和安全\n\n"
        "## 最终达成标准\n- 能在陌生需求下独立完成并解释取舍。\n\n"
        f"## 毕业项目\n独立交付一个包含测试、可观测性和复盘的 {topic} 大型项目。\n\n"
        + "\n\n".join(stages)
    )


def test_health(client: TestClient) -> None:
    payload = client.get("/api/health").json()

    assert payload["ok"] is True
    assert payload["backend"] == "fastapi"


def test_current_lesson_registers_practice_and_check_attempt_updates_unified_bank(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    curriculum = curriculum_from_plan(
        GO_PLAN, topic="Go", route="foundation_engineer", level="zero",
    )
    bundle = parse_lesson_response(
        model_lesson_json(curriculum.current_knowledge_point_id),
        topic="Go", route="foundation_engineer",
        knowledge_point_id=curriculum.current_knowledge_point_id,
        session_minutes=25, chapter=curriculum.current_chapter(),
    )
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    monkeypatch.setattr(main, "read_learning_context", lambda *_: {
        "profile_status": "confirmed", "plan_status": "confirmed",
    })
    monkeypatch.setattr(main, "load_curriculum", lambda *_: curriculum)
    monkeypatch.setattr(main, "load_lesson_bundle", lambda *_: bundle)
    monkeypatch.setattr(main, "ensure_practice_workspace", lambda *_: tmp_path)

    current = client.get("/api/lesson/current?user_id=learner")
    page_id, correct_option_id = next(iter(bundle.answer_keys.items()))
    checked = client.post("/api/lesson/check", json={
        "user_id": "learner", "lesson_id": bundle.manifest.lesson_id,
        "page_id": page_id, "selected_option_id": correct_option_id,
    })
    bank = client.get("/api/practice/bank?user_id=learner")

    assert current.status_code == 200
    assert checked.status_code == 200
    assert bank.status_code == 200
    payload = bank.json()
    assert payload["coverage"]["total"] >= 2
    classroom = next(item for item in payload["questions"] if item["source"] == "classroom")
    assert classroom["status"] == "mastered"
    assert classroom["attempt_count"] == 1
    assert any(item["source"] == "homework" for item in payload["questions"])


def test_cached_lesson_is_reloaded_through_current_teaching_contract_before_use(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    curriculum = curriculum_from_plan(
        GO_PLAN, topic="Go", route="foundation_engineer", level="zero",
    )
    chapter = curriculum.current_chapter()
    cached = parse_lesson_response(
        model_lesson_json(curriculum.current_knowledge_point_id),
        topic="Go",
        route="foundation_engineer",
        knowledge_point_id=curriculum.current_knowledge_point_id,
        session_minutes=25,
        chapter=chapter,
    )
    generated = cached
    load_calls = 0
    generated_calls = 0

    def fake_load(*_args: object, **_kwargs: object):
        nonlocal load_calls
        load_calls += 1
        if load_calls == 1:
            raise OSError("no personal lesson")
        raise ValueError("cached lesson violates current teaching contract")

    def fake_generate(*_args: object, **_kwargs: object):
        nonlocal generated_calls
        generated_calls += 1
        return generated

    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    monkeypatch.setattr(main, "read_learning_context", lambda *_: {
        "profile_status": "confirmed", "recent_evidence": [], "session_minutes": 25,
    })
    monkeypatch.setattr(main, "load_curriculum", lambda *_: curriculum)
    monkeypatch.setattr(main, "load_lesson_bundle", fake_load)
    monkeypatch.setattr(main, "load_completed_chapter", lambda *_: cached)
    monkeypatch.setattr(main, "save_lesson_bundle", lambda *_: None)
    monkeypatch.setattr(main, "latest_release", lambda: tmp_path / "release")
    monkeypatch.setattr(main, "read_state", lambda *_: {})
    monkeypatch.setattr(main, "load_valid_research", lambda *_: (_ for _ in ()).throw(OSError()))
    monkeypatch.setattr(main, "generate_and_save_lesson", fake_generate)
    monkeypatch.setattr(main, "ensure_practice_workspace", lambda *_: tmp_path)

    response = client.post("/api/lesson/generate", json={"user_id": "learner"})

    assert response.status_code == 200
    assert load_calls == 2
    assert generated_calls == 1


def test_nonzero_onboarding_uses_codex_generated_click_diagnosis(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    monkeypatch.setattr(main, "latest_release", lambda: Path("/tmp/release"))
    monkeypatch.setattr(main, "chat", lambda *_: json.dumps({"questions": [
        {"id": "java-list", "prompt": "List 的作用？", "dimension": "syntax", "options": [{"id": "a", "label": "保存多个值"}, {"id": "b", "label": "启动服务"}], "correct_option_id": "a"},
        {"id": "java-http", "prompt": "200 的意思？", "dimension": "api", "options": [{"id": "a", "label": "成功"}, {"id": "b", "label": "未找到"}], "correct_option_id": "a"},
        {"id": "java-error", "prompt": "异常出现时？", "dimension": "debugging", "options": [{"id": "a", "label": "处理它"}, {"id": "b", "label": "忽略项目"}], "correct_option_id": "a"},
    ]}, ensure_ascii=False))

    response = client.post("/api/onboarding/start", json={
        "user_id": "learner", "topic": {"type": "custom", "value": "Java API"},
        "learning_mode": "systematic", "goal_route": "foundation_engineer",
        "level_claim": "some", "session_minutes": 25,
    })

    assert response.status_code == 200
    assert response.json()["question"]["id"] == "java-list"
    assert response.json()["diagnostic_source"] == "skill_generated"


def test_onboarding_intent_uses_fast_skill_prompt_with_recent_history_and_slots(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    captured: dict[str, str] = {}
    decision = {
        "action": "clarify",
        "confidence": 0.88,
        "summary": "用户想学 LangGraph，还需要确定最终结果",
        "slots": {
            "intent_family": "structured_learning", "topic": "LangGraph",
            "goal": None, "desired_outcome": None, "target_context": None,
            "level_evidence": None, "deadline": None, "learning_scope": None,
            "constraints": [],
        },
        "question": {
            "prompt": "你想用 LangGraph 先做到什么？", "slot": "desired_outcome",
            "options": [
                {"id": "a", "label": "看懂核心概念", "detail": "理解图、状态与节点"},
                {"id": "b", "label": "做出一个 Agent", "detail": "围绕可运行项目学习"},
            ],
        },
        "onboarding": None,
    }

    def fake_intent_chat(prompt: str, skill_text: str) -> str:
        captured["prompt"] = prompt
        captured["skill"] = skill_text
        return json.dumps(decision, ensure_ascii=False)

    monkeypatch.setattr(main, "latest_release", lambda: tmp_path / "release")
    monkeypatch.setattr(main, "intent_chat", fake_intent_chat)

    response = client.post("/api/onboarding/intent", json={
        "user_id": "learner", "message": "其实我想做一个客服 Agent",
        "history": [{"role": "user", "content": "我想学 LangGraph"}],
        "slots": {"topic": "LangGraph"}, "has_active_project": True,
        "clarification_count": 0,
    })

    assert response.status_code == 200
    assert response.json()["action"] == "clarify"
    assert len(response.json()["question"]["options"]) == 2
    assert "客服 Agent" in captured["prompt"]
    assert '"topic": "LangGraph"' in captured["prompt"]
    assert "slot filling" in captured["skill"]


def test_onboarding_intent_rejects_malformed_model_output_without_fixed_fallback(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "latest_release", lambda: tmp_path / "release")
    monkeypatch.setattr(main, "intent_chat", lambda *_: '{"action":"clarify","question":null}')

    response = client.post("/api/onboarding/intent", json={
        "user_id": "learner", "message": "我想学 LangGraph",
    })

    assert response.status_code == 502
    assert response.json()["detail"]["retryable"] is True
    assert response.json()["detail"]["recovery"] == "retry_intent"
    assert "固定选项" not in response.text


def test_ready_intent_does_not_persist_or_confirm_project(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    ready = {
        "action": "ready_for_plan", "confidence": 0.95,
        "summary": "用户要从零学会 LangGraph 并交付 Agent 项目",
        "slots": {
            "intent_family": "structured_learning", "topic": "LangGraph",
            "goal": "从零系统学会", "desired_outcome": "独立交付一个 LangGraph Agent",
            "target_context": "客服 Agent", "level_evidence": "零基础",
            "deadline": None, "learning_scope": "complete_mastery", "constraints": [],
        },
        "question": None,
        "onboarding": {
            "goal_route": "foundation_engineer", "learning_mode": "systematic",
            "level_claim": "zero", "session_minutes": 25,
            "concept_scope": "not_applicable", "topic_type": "custom",
            "deadline_days": None, "teaching_preference": "balanced",
        },
    }
    monkeypatch.setattr(main, "latest_release", lambda: tmp_path / "release")
    monkeypatch.setattr(main, "intent_chat", lambda *_: json.dumps(ready, ensure_ascii=False))
    monkeypatch.setattr(
        main, "confirm_onboarding",
        lambda *_: (_ for _ in ()).throw(AssertionError("intent endpoint must not persist")),
    )

    response = client.post("/api/onboarding/intent", json={
        "user_id": "learner", "message": "我从零学 LangGraph，最后想做客服 Agent",
    })

    assert response.status_code == 200
    assert response.json()["action"] == "ready_for_plan"
    assert not (tmp_path / "userdir/u_learner/learning-state.json").exists()


def test_project_archive_can_keep_old_project_and_switch_back(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    user_dir = tmp_path / "userdir/u_learner"
    (user_dir / "plans").mkdir(parents=True)
    (user_dir / "profile.md").write_text("# Go 学习画像\n", encoding="utf-8")
    (user_dir / "learning-state.json").write_text(json.dumps({"active_plan": "plans/go.md", "active_topic": "Go"}), encoding="utf-8")
    (user_dir / "plans/go.md").write_text("# Go 计划\n", encoding="utf-8")

    snapshot = client.post("/api/projects/snapshot", json={"user_id": "learner"}).json()["snapshot_id"]
    archived = client.post("/api/projects/snapshot/archive", json={"user_id": "learner", "snapshot_id": snapshot})
    listing = client.get("/api/projects?user_id=learner")
    (user_dir / "profile.md").write_text("# Java 学习画像\n", encoding="utf-8")
    switched = client.post("/api/projects/switch", json={"user_id": "learner", "project_id": archived.json()["project"]["id"]})

    assert archived.status_code == listing.status_code == switched.status_code == 200
    assert listing.json()["projects"][0]["topic"] == "Go"
    assert "Go" in (user_dir / "profile.md").read_text(encoding="utf-8")


def test_project_list_includes_active_project_progress_and_archives(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    user_dir = tmp_path / "userdir/u_learner"
    (user_dir / "plans").mkdir(parents=True)
    (user_dir / "profile.md").write_text("# LangGraph 学习画像\n", encoding="utf-8")
    (user_dir / "plans/langgraph.md").write_text("# LangGraph 计划\n", encoding="utf-8")
    (user_dir / "learning-state.json").write_text(json.dumps({
        "active_plan": "plans/langgraph.md", "active_topic": "LangGraph",
        "updated_at": "2026-08-22T09:30:00+00:00",
    }), encoding="utf-8")
    (user_dir / "curriculum.json").write_text(json.dumps({
        "schema_version": 1, "topic": "LangGraph", "route": "foundation_engineer",
        "level": "zero", "current_knowledge_point_id": "state",
        "chapters": [{"id": "chapter-1", "title": "基础", "knowledge_points": [
            {"id": "graph", "title": "图", "outcome": "理解图", "practice": "画图", "mastery_criteria": "能解释", "status": "completed"},
            {"id": "state", "title": "状态", "outcome": "理解状态", "practice": "写状态", "mastery_criteria": "能应用", "status": "active", "prerequisites": ["graph"]},
        ]}],
    }), encoding="utf-8")
    snapshot = client.post("/api/projects/snapshot", json={"user_id": "learner"}).json()["snapshot_id"]
    client.post("/api/projects/snapshot/archive", json={"user_id": "learner", "snapshot_id": snapshot})

    response = client.get("/api/projects?user_id=learner")

    assert response.status_code == 200
    projects = response.json()["projects"]
    assert projects[0] == {
        "id": "current", "topic": "LangGraph", "current": True,
        "progress": 50, "updated_at": "2026-08-22T09:30:00+00:00",
    }
    assert projects[1]["current"] is False
    assert projects[1]["id"] == snapshot


def test_topic_key_treats_case_spacing_and_common_punctuation_as_the_same_project() -> None:
    normalize = project_snapshot.normalize_project_topic
    assert normalize("LangGraph") == normalize("langgraph")
    assert normalize("Lang Graph") == normalize("Lang-Graph")
    assert normalize("LangGraph") != normalize("LangChain")


def test_project_match_returns_existing_same_topic_before_a_new_plan(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    user_dir = tmp_path / "userdir/u_learner"
    user_dir.mkdir(parents=True)
    (user_dir / "learning-state.json").write_text(json.dumps({
        "active_topic": "LangGraph", "updated_at": "2026-08-22T08:00:00+00:00",
    }), encoding="utf-8")

    response = client.get("/api/projects/match", params={"user_id": "learner", "topic": "lang graph"})
    unrelated = client.get("/api/projects/match", params={"user_id": "learner", "topic": "LangChain"})

    assert response.status_code == 200
    assert response.json()["project"]["id"] == "current"
    assert response.json()["project"]["topic"] == "LangGraph"
    assert unrelated.status_code == 200
    assert unrelated.json()["project"] is None


def test_delete_archived_project_only_removes_that_private_archive(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    user_dir = tmp_path / "userdir/u_learner"
    user_dir.mkdir(parents=True)
    (user_dir / "learning-state.json").write_text(json.dumps({"active_topic": "Go"}), encoding="utf-8")
    snapshot_id = client.post("/api/projects/snapshot", json={"user_id": "learner"}).json()["snapshot_id"]
    client.post("/api/projects/snapshot/archive", json={"user_id": "learner", "snapshot_id": snapshot_id})
    sentinel = tmp_path / "workspace/dev/curriculum/generated/keep.lesson.json"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_text("shared lesson", encoding="utf-8")

    response = client.delete(f"/api/projects/{snapshot_id}", params={"user_id": "learner"})

    assert response.status_code == 200
    assert response.json()["deleted_project_id"] == snapshot_id
    assert not (user_dir / ".project-archives" / snapshot_id).exists()
    assert (user_dir / "learning-state.json").is_file()
    assert sentinel.read_text(encoding="utf-8") == "shared lesson"


def test_delete_current_project_keeps_archives_and_shared_knowledge(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    user_dir = tmp_path / "userdir/u_learner"
    (user_dir / "plans").mkdir(parents=True)
    (user_dir / "learning-state.json").write_text(json.dumps({"active_topic": "Go"}), encoding="utf-8")
    (user_dir / "plans/go.md").write_text("# plan", encoding="utf-8")
    snapshot_id = client.post("/api/projects/snapshot", json={"user_id": "learner"}).json()["snapshot_id"]
    client.post("/api/projects/snapshot/archive", json={"user_id": "learner", "snapshot_id": snapshot_id})
    sentinel = tmp_path / "workspace/dev/curriculum/generated/keep.deck.html"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_text("shared deck", encoding="utf-8")

    response = client.delete("/api/projects/current", params={"user_id": "learner"})

    assert response.status_code == 200
    assert not (user_dir / "learning-state.json").exists()
    assert not (user_dir / "plans").exists()
    assert (user_dir / ".project-archives" / snapshot_id).is_dir()
    assert sentinel.read_text(encoding="utf-8") == "shared deck"


def test_delete_project_rejects_invalid_or_cross_user_archive_id(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    other = tmp_path / "userdir/u_other"
    other.mkdir(parents=True)
    (other / "learning-state.json").write_text(json.dumps({"active_topic": "Rust"}), encoding="utf-8")
    snapshot_id = client.post("/api/projects/snapshot", json={"user_id": "other"}).json()["snapshot_id"]
    client.post("/api/projects/snapshot/archive", json={"user_id": "other", "snapshot_id": snapshot_id})

    invalid = client.delete("/api/projects/not-safe", params={"user_id": "learner"})
    cross_user = client.delete(f"/api/projects/{snapshot_id}", params={"user_id": "learner"})

    assert invalid.status_code == 422
    assert cross_user.status_code == 404
    assert (other / ".project-archives" / snapshot_id).is_dir()


def test_backend_main_supports_documented_module_mode_import() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import backend.main as main; print(main.app.title)"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Learning Agent" in result.stdout


def test_learning_context(client: TestClient) -> None:
    response = client.get("/api/learning-context?user_id=yang")

    assert response.status_code == 200
    assert "plan" in response.json()
    assert "exercise" in response.json()


def test_home_serves_workbench(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Learning Agent" in response.text


def test_frontend_assets_do_not_keep_a_stale_learning_flow_in_browser_cache(client: TestClient) -> None:
    response = client.get("/js/app.js")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"


def test_learning_questions_are_saved_separately_from_run_output(tmp_path: Path) -> None:
    document = append_learning_question(
        tmp_path, "learner", question="为什么 go build 后还能直接运行？", topic="Go",
    )

    stored = (tmp_path / "userdir/u_learner/memory/questions.jsonl").read_text(encoding="utf-8")
    assert "go build" in stored
    assert "# 我遇到的问题" in document.read_text(encoding="utf-8")


def test_empty_stream_message_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/chat/stream",
        json={"user_id": "yang", "message": ""},
    )

    assert response.status_code == 422


def test_stream_is_event_stream(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main, "latest_release", lambda: Path("/tmp/release"))
    monkeypatch.setattr(
        main,
        "stream_chat",
        lambda *args, **kwargs: iter(
            [
                {"event": "message.delta", "data": {"text": "你好"}},
                {"event": "message.completed", "data": {}},
            ]
        ),
    )

    response = client.post(
        "/api/chat/stream",
        json={"user_id": "yang", "message": "Go", "history": []},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: message.delta" in response.text
    assert 'data: {"text": "你好"}' in response.text


def test_stream_persists_lesson_note_summary_reward_and_emits_refresh_event(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    monkeypatch.setattr(main, "latest_release", lambda: Path("/tmp/release"))
    monkeypatch.setattr(main, "read_learning_context", lambda *_: {"topic": "Go", "profile_status": "confirmed"})
    monkeypatch.setattr(
        main,
        "stream_chat",
        lambda *args, **kwargs: iter([
            {"event": "message.delta", "data": {"text": "重点是 main 函数是程序入口。"}},
            {"event": "message.completed", "data": {}},
        ]),
    )
    client = TestClient(main.app)

    response = client.post("/api/chat/stream", json={
        "user_id": "note-user", "message": "为什么 Go 必须有 main 函数？",
        "lesson_id": "go-entry-lesson", "history": [],
    })

    assert response.status_code == 200
    assert "event: notes.updated" in response.text
    notes = client.get("/api/lesson/notes?user_id=note-user&lesson_id=go-entry-lesson").json()
    assert notes["notes"][0]["question"] == "为什么 Go 必须有 main 函数？"
    assert "main 函数" in notes["notes"][0]["summary"]
    assert notes["notes"][0]["reward"]
    assert notes["notes"][0]["important"] is True


def test_course_chat_answers_the_question_without_adding_a_text_only_quiz(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    user_dir = tmp_path / "userdir/u_chat-user"
    user_dir.mkdir(parents=True)
    (user_dir / "learning-state.json").write_text(
        json.dumps({"profile_status": "confirmed"}), encoding="utf-8",
    )

    prompt = main.build_prompt("chat-user", [], "为什么 main 是入口？")

    assert "回答完不要再追加一道要求用户作答的文字题" in prompt
    assert "代码必须有详细中文注释" in prompt
    assert "立即讲一个核心概念并给一道当前题" not in prompt


def test_important_lesson_note_creates_review_card_and_knowledge_candidate(tmp_path: Path) -> None:
    note = review_material.append_lesson_note(
        tmp_path, "learner", lesson_id="go-entry-lesson", topic="Go",
        question="为什么 main 是程序入口？", summary="main 是可执行程序的入口。",
    )

    assert note["important"] is True
    assert (tmp_path / "userdir/u_learner/memory/review-cards.json").is_file()
    candidates = tmp_path / "workspace/dev/curriculum/curation/pending/important-questions.jsonl"
    assert candidates.is_file()
    assert "main 是程序入口" in candidates.read_text(encoding="utf-8")


def test_stream_requires_release(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main, "latest_release", lambda: None)

    response = client.post(
        "/api/chat/stream",
        json={"user_id": "yang", "message": "Go"},
    )

    assert response.status_code == 503


def test_grade_returns_coach_feedback(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        main,
        "llm_chat",
        lambda prompt, system: "部分正确：思路清楚；请补上完整输出。",
    )

    response = client.post(
        "/api/grade",
        json={
            "question": "程序会输出什么？",
            "answer": "你好",
            "kind": "prediction",
        },
    )

    assert response.status_code == 200
    assert response.json()["feedback"].startswith("部分正确")


def test_grade_persists_review_document(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    monkeypatch.setattr(main, "llm_chat", lambda prompt, system: "正确：输出完整。")

    response = client.post(
        "/api/grade",
        json={
            "user_id": "learner",
            "question": "程序会输出什么？",
            "answer": "你好, Go!",
            "kind": "prediction",
        },
    )
    review = client.get("/api/review-document?user_id=learner")

    assert response.status_code == 200
    assert review.status_code == 200
    assert "你好, Go!" in review.json()["content"]


def test_interview_intake_returns_questions_and_inline_study_choices(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)

    response = client.post(
        "/api/interview/intake",
        json={"user_id": "learner", "raw_text": "1. 什么是闭包？\n2. HTTP 缓存怎么工作？"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intake"]["new_count"] == 2
    assert [choice["value"] for choice in payload["study_choices"]] == [
        "from_scratch", "systematic", "assess_first",
    ]
    assert payload["coverage"]["total"] == 2


def test_interview_bank_question_and_mastery_endpoints(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    intake = client.post(
        "/api/interview/intake",
        json={"user_id": "learner", "raw_text": "什么是闭包？"},
    ).json()
    question_id = intake["intake"]["question_ids"][0]

    bank = client.get("/api/interview/bank?user_id=learner")
    question = client.get(f"/api/interview/questions/{question_id}?user_id=learner")
    rated = client.post(
        f"/api/interview/questions/{question_id}/mastery",
        json={"user_id": "learner", "mastery": "smooth"},
    )
    mode = client.post(
        "/api/interview/study-mode",
        json={"user_id": "learner", "mode": "systematic"},
    )

    assert bank.status_code == question.status_code == rated.status_code == mode.status_code == 200
    assert bank.json()["questions"][0]["answer_status"] == "missing"
    assert rated.json()["question"]["mastery"] == "smooth"
    assert mode.json()["study_mode"] == "systematic"


def test_unknown_interview_question_returns_404(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)

    response = client.get("/api/interview/questions/iq_0000000000000000?user_id=learner")

    assert response.status_code == 404


def test_interview_expand_uses_model_and_returns_structured_answer(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    captured: dict[str, object] = {}

    def fake_interview_model(prompt: str, system: str, **kwargs: object) -> str:
        captured.update(kwargs)
        return json.dumps({
            "answer_markdown": "HTTP 缓存通过新鲜度与再验证工作。",
            "rubric": ["Cache-Control", "ETag"],
            "prerequisites": ["HTTP header"],
            "related_questions": ["强缓存与协商缓存有什么区别？"],
        }, ensure_ascii=False)

    monkeypatch.setattr(main, "llm_chat", fake_interview_model)
    intake = client.post(
        "/api/interview/intake",
        json={"user_id": "learner", "raw_text": "HTTP 缓存怎么工作？"},
    ).json()

    response = client.post(
        f"/api/interview/questions/{intake['intake']['question_ids'][0]}/expand",
        json={"user_id": "learner", "mode": "systematic"},
    )

    assert response.status_code == 200
    assert response.json()["question"]["answer_status"] == "ready"
    assert len(response.json()["related_question_ids"]) == 1
    assert captured["max_tokens"] >= 1800


def test_generate_module_exercise(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        main,
        "llm_chat",
        lambda prompt, system: '{"kind":"prediction","title":"再预测一次","prompt":"会输出什么？","instructions":"写完整输出。","completion_criteria":"输出一致。"}',
    )

    response = client.post(
        "/api/exercises/generate",
        json={"user_id": "yang", "module": "Go 第一个程序", "level": "beginner"},
    )

    assert response.status_code == 200
    assert response.json()["exercise"]["title"] == "再预测一次"


def onboarding_payload(user_id: str, level: str = "zero") -> dict:
    return {
        "user_id": user_id,
        "learning_mode": "systematic",
        "level_claim": level,
        "topic": {"type": "go", "value": "go"},
    }


def test_zero_beginner_confirm_starts_lesson(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    response = client.post(
        "/api/onboarding/confirm",
        json=onboarding_payload("zero-go"),
    )

    assert response.status_code == 200
    assert response.json()["first_lesson"]["start_immediately"] is False
    state = json.loads(
        (tmp_path / "userdir/u_zero-go/learning-state.json").read_text(encoding="utf-8")
    )
    assert (tmp_path / "userdir/u_zero-go" / state["active_plan"]).is_file()


def test_plan_personalization_uses_codex_and_persists_valid_markdown(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    payload = onboarding_payload("plan-codex")
    payload["topic"] = {"type": "custom", "value": "FastAPI 发 API"}
    payload["goal_route"] = "project_delivery"
    client.post("/api/onboarding/confirm", json=payload)
    monkeypatch.setattr(main, "latest_release", lambda: Path("/tmp/codex-release"))
    captured: dict[str, str] = {}

    def fake_chat(user_id, prompt, release):
        research_dir = tmp_path / "userdir/u_plan-codex/research/fastapi-api"
        research_dir.mkdir(parents=True, exist_ok=True)
        (research_dir / "sources.json").write_text(json.dumps({
            "topic": "FastAPI 发 API",
            "researched_at": "2026-08-21T00:00:00+00:00",
            "version": "current",
            "sources": [{"id": "official-docs", "title": "FastAPI 官方文档", "url": "https://fastapi.tiangolo.com/", "kind": "official_docs"}],
            "teaching_facts": [{"statement": "最小应用通过路径操作装饰器声明接口。", "source_ids": ["official-docs"]}],
        }, ensure_ascii=False), encoding="utf-8")
        captured["prompt"] = prompt
        stages = "\n\n".join(
            f"### 阶段 {index}：具体步骤 {index}\n- 本阶段要学：FastAPI 发 API 知识 {index}\n- 练习：完成接口任务 {index}\n- 完成证据：提交运行结果 {index}"
            for index in range(1, 6)
        )
        return (
            "我已经读取了资料，下面开始写计划。\n"
            "# FastAPI 发 API 学习计划\n\n## 当前任务\n完成第一个 GET API。"
            "\n\n## 学习成果\n能独立设计、运行和测试 API。\n\n## 教学策略\n边做边学。\n\n"
            + stages
        )

    monkeypatch.setattr(main, "chat", fake_chat)

    response = client.post("/api/plans/personalize", json=payload)

    assert response.status_code == 200
    assert response.json()["personalized"] is True
    assert "learning-plan" in captured["prompt"]
    assert "new-topic-research" in captured["prompt"]
    assert "tools/web_search.py" in captured["prompt"]
    assert response.json()["plan_status"] == "awaiting_confirmation"
    assert "plan_markdown" in response.json()
    state = json.loads((tmp_path / "userdir/u_plan-codex/learning-state.json").read_text(encoding="utf-8"))
    assert state["plan_status"] == "awaiting_confirmation"
    plan = (tmp_path / "userdir/u_plan-codex" / state["active_plan"]).read_text(encoding="utf-8")
    assert plan.startswith("# FastAPI 发 API 学习计划")
    curriculum = json.loads((tmp_path / "userdir/u_plan-codex/curriculum.json").read_text(encoding="utf-8"))
    assert curriculum["topic"] == "FastAPI 发 API"
    assert curriculum["current_knowledge_point_id"]
    assert "## 教学策略" in plan
    assert "### 阶段 1" in plan


def test_concept_clarity_personalization_accepts_a_short_plan_without_daily_time(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    payload = onboarding_payload("rag-concept")
    payload.update({
        "topic": {"type": "custom", "value": "RAG 是什么"},
        "goal_route": "concept_clarity",
        "concept_scope": "meaning_only",
    })
    client.post("/api/onboarding/confirm", json=payload)
    monkeypatch.setattr(main, "latest_release", lambda: Path("/tmp/codex-release"))
    captured: dict[str, str] = {}

    def fake_chat(user_id, prompt, release):
        captured["prompt"] = prompt
        research_dir = tmp_path / "userdir/u_rag-concept/research/rag"
        research_dir.mkdir(parents=True, exist_ok=True)
        (research_dir / "sources.json").write_text(json.dumps({
            "topic": "RAG 是什么",
            "researched_at": "2026-08-21T00:00:00+00:00",
            "version": "current",
            "sources": [{"id": "official", "title": "官方资料", "url": "https://example.com/rag", "kind": "official_docs"}],
            "teaching_facts": [{"statement": "RAG 在生成前检索外部资料。", "source_ids": ["official"]}],
        }, ensure_ascii=False), encoding="utf-8")
        return """# RAG 是什么 概念速学

## 当前任务
先用一个比喻理解 RAG。

## 学习成果
能判断哪些场景需要 RAG。

## 教学策略
少术语、多例子、点击验收。

### 阶段 1：建立直觉
- 本阶段要学：RAG 为什么要先找资料再回答
- 练习：点击判断一个场景是否属于 RAG
- 完成证据：能选对并看懂反馈
"""

    monkeypatch.setattr(main, "chat", fake_chat)
    response = client.post("/api/plans/personalize", json=payload)

    assert response.status_code == 200
    assert response.json()["personalized"] is True
    assert "不询问每日学习时长" in captured["prompt"]
    assert "1–3 个" in captured["prompt"]
    curriculum = json.loads((tmp_path / "userdir/u_rag-concept/curriculum.json").read_text(encoding="utf-8"))
    assert len(curriculum["chapters"]) == 1


def test_plan_must_be_confirmed_before_current_lesson_opens(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    payload = onboarding_payload("plan-review")
    client.post("/api/onboarding/confirm", json=payload)

    blocked = client.get("/api/lesson/current?user_id=plan-review")
    confirmed = client.post("/api/plans/confirm", json={"user_id": "plan-review"})

    assert blocked.status_code == 409
    assert blocked.json()["detail"]["recovery"] == "confirm_plan"
    assert confirmed.status_code == 200
    assert confirmed.json()["plan_status"] == "confirmed"
    state = json.loads((tmp_path / "userdir/u_plan-review/learning-state.json").read_text(encoding="utf-8"))
    assert state["plan_status"] == "confirmed"


def test_plan_revision_reads_plan_revision_skill_and_preserves_confirmation_gate(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    payload = onboarding_payload("plan-revise")
    client.post("/api/onboarding/confirm", json=payload)
    monkeypatch.setattr(main, "latest_release", lambda: Path("/tmp/codex-release"))
    captured: dict[str, str] = {}

    def fake_chat(user_id, prompt, release):
        captured["prompt"] = prompt
        return deep_mastery_plan("Go")

    monkeypatch.setattr(main, "chat", fake_chat)
    response = client.post("/api/plans/revise", json={**payload, "feedback": "项目实战再多一点"})

    assert response.status_code == 200
    assert response.json()["revised"] is True
    assert response.json()["plan_status"] == "awaiting_confirmation"
    assert "plan-revision" in captured["prompt"]
    assert "项目实战再多一点" in captured["prompt"]


def test_invalid_codex_plan_keeps_detailed_fallback(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    payload = onboarding_payload("plan-fallback")
    payload["topic"] = {"type": "custom", "value": "FastAPI 发 API"}
    client.post("/api/onboarding/confirm", json=payload)
    plan_path = tmp_path / "userdir/u_plan-fallback/plans/fastapi-api-plan.md"
    fallback = plan_path.read_text(encoding="utf-8")
    monkeypatch.setattr(main, "latest_release", lambda: Path("/tmp/codex-release"))
    monkeypatch.setattr(main, "chat", lambda *_: "太宽泛了，随便学学。")

    response = client.post("/api/plans/personalize", json=payload)

    assert response.status_code == 200
    assert response.json()["personalized"] is False
    assert response.json()["user_message"]
    assert plan_path.read_text(encoding="utf-8") == fallback


def test_codex_timeout_is_reported_as_generation_failure_not_plan_validation(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    payload = onboarding_payload("plan-timeout")
    client.post("/api/onboarding/confirm", json=payload)
    monkeypatch.setattr(main, "latest_release", lambda: Path("/tmp/codex-release"))
    monkeypatch.setattr(main, "chat", lambda *_: "[超时] Codex 在限定时间内没有完成")

    response = client.post("/api/plans/personalize", json=payload)

    assert response.status_code == 200
    assert response.json()["reason"] == "model_generation_failed"
    assert "超时" in response.json()["user_message"]


def test_existing_confirmed_user_can_generate_structured_curriculum(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    payload = onboarding_payload("legacy-go")
    payload["goal_route"] = "foundation_engineer"
    client.post("/api/onboarding/confirm", json=payload)
    monkeypatch.setattr(main, "latest_release", lambda: Path("/tmp/codex-release"))

    def fake_chat(user_id, prompt, release):
        research_dir = tmp_path / "userdir/u_legacy-go/research/go"
        research_dir.mkdir(parents=True, exist_ok=True)
        (research_dir / "sources.json").write_text(json.dumps({
            "topic": "go",
            "researched_at": "2026-08-21T00:00:00+00:00",
            "version": "current",
            "sources": [{"id": "official", "title": "Go 官方文档", "url": "https://go.dev/doc/", "kind": "official_docs"}],
            "teaching_facts": [{"statement": "Go 官方文档覆盖语言、工具链和工程实践。", "source_ids": ["official"]}],
            "coverage_areas": ["语言基础", "运行时", "并发", "测试", "工程交付"],
            "prerequisites": ["命令行基础"],
            "graduation_project": "交付一个带测试和可观测性的 Go 服务",
        }, ensure_ascii=False), encoding="utf-8")
        return deep_mastery_plan("Go")

    monkeypatch.setattr(main, "chat", fake_chat)

    response = client.post("/api/curriculum/generate", json={"user_id": "legacy-go"})

    assert response.status_code == 200
    assert response.json()["generated"] is True
    assert (tmp_path / "userdir/u_legacy-go/curriculum.json").is_file()
    assert response.json()["current_knowledge_point_id"]


def test_model_plan_with_a_detailed_learning_line_still_builds_a_curriculum() -> None:
    from backend.curriculum import curriculum_from_plan

    long_concept = "；".join(["StateGraph 状态、节点和边的职责以及它们在一次 invoke 中如何传递数据" * 5])
    plan = (
        "# LangGraph 学习计划\n\n## 当前任务\n先读图。\n\n## 学习成果\n能完成项目。\n\n## 教学策略\n边做边学。\n\n"
        + "\n\n".join(
            f"### 阶段 {index}：步骤 {index}\n- 本阶段要学：{long_concept if index == 1 else f'LangGraph 知识 {index}'}\n- 练习：运行示例\n- 完成证据：留下输出"
            for index in range(1, 6)
        )
    )

    curriculum = curriculum_from_plan(plan, topic="LangGraph", route="foundation_engineer", level="zero")

    assert len(curriculum.knowledge_points()) == 5
    assert max(len(point.title) for point in curriculum.knowledge_points()) <= 220


def test_some_experience_returns_click_question(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    response = client.post(
        "/api/onboarding/start",
        json=onboarding_payload("some-go", "some"),
    )

    assert response.status_code == 200
    assert response.json()["next"] == "diagnosis"
    assert response.json()["question"]["options"]
    assert "correct_option_id" not in response.text


def test_diagnostic_answer_never_exposes_correct_id(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    started = client.post(
        "/api/onboarding/start",
        json=onboarding_payload("private-answer", "some"),
    ).json()
    response = client.post(
        "/api/diagnostics/answer",
        json={
            "user_id": "private-answer",
            "session_id": started["session_id"],
            "question_id": started["question"]["id"],
            "selected_option_id": started["question"]["options"][0]["id"],
        },
    )

    assert response.status_code == 200
    assert "correct_option_id" not in response.text


def test_expired_diagnostic_session_returns_recoverable_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    response = client.post(
        "/api/diagnostics/answer",
        json={
            "user_id": "expired",
            "session_id": "missing",
            "question_id": "go-1",
            "selected_option_id": "a",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["recovery"] == "restart_diagnosis"


def test_confirmed_profile_prompt_forbids_more_onboarding(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    client.post("/api/onboarding/confirm", json=onboarding_payload("confirmed"))
    monkeypatch.setattr(main, "latest_release", lambda: Path("/tmp/release"))
    captured = {}

    def fake_stream(user_id, prompt, release):
        captured["prompt"] = prompt
        return iter([{"event": "message.completed", "data": {}}])

    monkeypatch.setattr(main, "stream_chat", fake_stream)
    response = client.post(
        "/api/chat/stream",
        json={"user_id": "confirmed", "message": "开始吧"},
    )

    assert response.status_code == 200
    assert "禁止继续摸底" in captured["prompt"]
    assert "立即讲一个核心概念" in captured["prompt"]
    assert "不要播报读取状态" in captured["prompt"]
    assert "选择题和动手题不能同轮" in captured["prompt"]


def test_grade_response_has_machine_readable_verdict(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    monkeypatch.setattr(
        main,
        "grade_answer",
        lambda **_: {
            "feedback": "正确：判断与运行结果一致。",
            "correct": True,
            "verified": True,
        },
    )
    response = client.post(
        "/api/grade",
        json={
            "user_id": "motion-test",
            "question": "2 + 2 = ?",
            "answer": "4",
        },
    )

    assert response.status_code == 200
    assert response.json()["correct"] is True
    assert response.json()["verified"] is True


def test_unstructured_grade_never_claims_verified_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main, "llm_chat", lambda prompt, system: "看起来不错，继续加油。")

    result = main.grade_answer(question="题目", answer="答案", kind="text")

    assert result["correct"] is None
    assert result["verified"] is False


def test_lesson_remediation_forces_a_regenerated_lesson(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    def fake_generate(request):
        captured["request"] = request
        return {"lesson_id": "remediated"}

    monkeypatch.setattr(main, "generate_lesson", fake_generate)

    response = client.post(
        "/api/lesson/remediate",
        json={"user_id": "learner", "remediation": "换一个生活类比"},
    )

    assert response.status_code == 200
    assert response.json()["lesson_id"] == "remediated"
    assert captured["request"].force is True
    assert captured["request"].remediation == "换一个生活类比"


def test_project_snapshot_restores_backend_course_after_failed_switch(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    old_payload = onboarding_payload("archive-user")
    client.post("/api/onboarding/confirm", json=old_payload)
    old_state = (tmp_path / "userdir/u_archive-user/learning-state.json").read_text(encoding="utf-8")
    old_profile = (tmp_path / "userdir/u_archive-user/profile.md").read_text(encoding="utf-8")

    snapshot = client.post("/api/projects/snapshot", json={"user_id": "archive-user"})
    assert snapshot.status_code == 200
    snapshot_id = snapshot.json()["snapshot_id"]

    new_payload = onboarding_payload("archive-user")
    new_payload["topic"] = {"type": "custom", "value": "Rust 面试"}
    client.post("/api/onboarding/confirm", json=new_payload)
    assert "Rust 面试" in (tmp_path / "userdir/u_archive-user/profile.md").read_text(encoding="utf-8")

    restored = client.post(
        "/api/projects/restore",
        json={"user_id": "archive-user", "snapshot_id": snapshot_id},
    )
    assert restored.status_code == 200
    assert (tmp_path / "userdir/u_archive-user/learning-state.json").read_text(encoding="utf-8") == old_state
    assert (tmp_path / "userdir/u_archive-user/profile.md").read_text(encoding="utf-8") == old_profile
