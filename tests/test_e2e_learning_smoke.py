from __future__ import annotations

from tools import e2e_learning_smoke as smoke


def ready(level: str = "zero") -> dict:
    return {
        "action": "ready_for_plan",
        "slots": {"topic": "前端", "level_evidence": "初学"},
        "onboarding": {
            "learning_mode": "practice", "goal_route": "interview_sprint",
            "level_claim": level, "topic_type": "custom", "session_minutes": 25,
            "concept_scope": "not_applicable", "teaching_preference": "balanced",
        },
    }


def test_missing_level_is_clarified_before_plan(monkeypatch) -> None:
    calls = []
    responses = iter([
        {"action": "clarify", "slots": {"topic": "前端"}, "question": {"options": []}},
        ready(),
    ])

    def fake_post(base_url, path, payload, timeout=600):
        calls.append((path, payload))
        return next(responses)

    monkeypatch.setattr(smoke, "post", fake_post)
    result = smoke.run_case("http://test", smoke.CASES["frontend-interview-missing-level"], through="intent")

    assert result["ok"] is True
    assert [stage["stage"] for stage in result["stages"]] == ["intent", "clarification"]
    assert calls[1][1]["message"] == "初学"
    assert calls[1][1]["slots"]["topic"] == "前端"


def test_non_beginner_journey_completes_diagnosis_plan_and_lesson(monkeypatch) -> None:
    paths = []
    diagnostic = {
        "session_id": "session-1", "complete": False, "answered_count": 0,
        "question": {"id": "q1", "options": [{"id": "a", "label": "answer"}]},
    }

    def fake_post(base_url, path, payload, timeout=600):
        paths.append(path)
        if path == "/api/onboarding/intent":
            value = ready("some")
            value["slots"]["topic"] = "Java 后端"
            value["slots"]["level_evidence"] = "有一点基础"
            return value
        if path == "/api/onboarding/start":
            return diagnostic
        if path == "/api/diagnostics/answer":
            return {**diagnostic, "complete": True, "answered_count": 1, "question": None}
        if path == "/api/onboarding/confirm":
            return {"active_plan": "plans/java.md", "generation_id": "a" * 32}
        if path == "/api/plans/personalize":
            assert payload["generation_id"] == "a" * 32
            return {"personalized": True, "current_knowledge_point_id": "java-1"}
        if path == "/api/plans/confirm":
            return {"plan_status": "confirmed"}
        if path == "/api/lesson/generate":
            return {
                "lesson_id": "java-1-lesson", "chapter_id": "chapter-1",
                "covered_knowledge_point_ids": ["java-1"],
                "pages": [{"type": "explain"}, {"type": "check"}],
            }
        raise AssertionError(path)

    monkeypatch.setattr(smoke, "post", fake_post)
    result = smoke.run_case("http://test", smoke.CASES["java-backend-interview-some"])

    assert result["ok"] is True
    assert paths == [
        "/api/onboarding/intent", "/api/onboarding/start", "/api/diagnostics/answer",
        "/api/onboarding/confirm", "/api/plans/personalize", "/api/plans/confirm",
        "/api/lesson/generate",
    ]
    assert result["stages"][-1]["checks"] == 1


def test_post_turns_socket_timeout_into_stage_error(monkeypatch) -> None:
    monkeypatch.setattr(smoke.DIRECT_OPENER, "open", lambda *_args, **_kwargs: (_ for _ in ()).throw(TimeoutError("timed out")))

    try:
        smoke.post("http://test", "/api/plans/personalize", {})
    except smoke.JourneyError as exc:
        assert exc.stage == "/api/plans/personalize"
        assert exc.payload["error_type"] == "TimeoutError"
    else:
        raise AssertionError("timeout must become JourneyError")
