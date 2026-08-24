from __future__ import annotations

import json
from pathlib import Path

from backend.user_memory import (
    append_conversation_event,
    persist_intent_decision,
    read_intent_state,
    write_profile_json,
)


def test_intent_state_keeps_current_fact_and_jsonl_keeps_every_change(tmp_path: Path) -> None:
    persist_intent_decision(
        tmp_path,
        "learner",
        message="我要面试 AI 前端，初学",
        decision={
            "action": "clarify",
            "summary": "还缺技术栈",
            "slots": {"target_role": "AI 前端", "level_evidence": "初学"},
        },
    )
    persist_intent_decision(
        tmp_path,
        "learner",
        message="React 和 TypeScript",
        decision={
            "action": "clarify",
            "summary": "还缺题目来源",
            "slots": {
                "target_role": "AI 前端",
                "level_evidence": "初学",
                "tech_stack": ["React", "TypeScript"],
            },
        },
    )

    state = read_intent_state(tmp_path, "learner")
    events = [
        json.loads(line)
        for line in (tmp_path / "userdir/u_learner/onboarding/intent-events.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]

    assert state["slots"]["tech_stack"] == ["React", "TypeScript"]
    assert state["last_message"] == "React 和 TypeScript"
    assert [event["message"] for event in events] == [
        "我要面试 AI 前端，初学",
        "React 和 TypeScript",
    ]


def test_profile_json_combines_normalized_profile_and_persisted_slots(tmp_path: Path) -> None:
    persist_intent_decision(
        tmp_path,
        "learner",
        message="没有现成题",
        decision={
            "action": "ready_for_plan",
            "summary": "可以生成面试计划",
            "slots": {
                "target_role": "AI 前端",
                "tech_stack": ["React", "TypeScript"],
                "interview_question_source": "none",
            },
        },
    )

    path = write_profile_json(
        tmp_path,
        "learner",
        {"topic": "AI 前端", "goal_route": "interview_sprint", "level_claim": "zero"},
    )
    profile = json.loads(path.read_text(encoding="utf-8"))

    assert profile["topic"] == "AI 前端"
    assert profile["intent_slots"]["tech_stack"] == ["React", "TypeScript"]
    assert profile["intent_slots"]["interview_question_source"] == "none"


def test_conversation_events_are_append_only_and_role_scoped(tmp_path: Path) -> None:
    append_conversation_event(tmp_path, "learner", role="user", content="闭包为什么会捕获变量？")
    append_conversation_event(tmp_path, "learner", role="assistant", content="先看变量的生命周期。")

    path = tmp_path / "userdir/u_learner/memory/conversation-events.jsonl"
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    assert [event["role"] for event in events] == ["user", "assistant"]
    assert events[0]["content"] == "闭包为什么会捕获变量？"
