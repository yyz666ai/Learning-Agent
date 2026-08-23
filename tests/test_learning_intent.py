from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from backend.learning_intent import (
    IntentDecision,
    build_intent_prompt,
    parse_intent_response,
)


def clarification_payload(*, options: list[dict[str, str]] | None = None) -> dict[str, object]:
    return {
        "action": "clarify",
        "confidence": 0.82,
        "summary": "用户想学 LangGraph，但最终目标还不明确",
        "slots": {
            "intent_family": "structured_learning",
            "topic": "LangGraph",
            "goal": None,
            "desired_outcome": None,
            "target_context": None,
            "level_evidence": None,
            "deadline": None,
            "learning_scope": None,
            "constraints": [],
        },
        "question": {
            "prompt": "你希望用 LangGraph 先做到什么？",
            "slot": "desired_outcome",
            "options": options or [
                {"id": "a", "label": "看懂核心概念", "detail": "先建立图、状态与节点的直觉"},
                {"id": "b", "label": "做出一个 Agent", "detail": "围绕一个可运行项目边做边学"},
                {"id": "c", "label": "系统掌握", "detail": "从基础到工程设计和综合项目"},
            ],
        },
        "onboarding": None,
    }


def test_intent_prompt_includes_skill_recent_history_existing_slots_and_correction_rule() -> None:
    history = [
        {"role": "user", "content": f"旧消息 {index}"}
        for index in range(10)
    ]
    prompt = build_intent_prompt(
        message="不对，我其实只想看懂现有项目",
        history=history,
        slots={"topic": "LangGraph", "learning_scope": "systematic"},
        has_active_project=True,
        clarification_count=1,
    )

    assert ".codex/skills/learning-intent-router/SKILL.md" in prompt
    assert "不对，我其实只想看懂现有项目" in prompt
    assert '"topic": "LangGraph"' in prompt
    assert "最近对话" in prompt
    assert "新输入优先" in prompt
    assert "旧消息 1" not in prompt
    assert "旧消息 2" in prompt
    assert "信息仍不足时可以继续追问" in prompt
    assert "不得重复已填槽位" in prompt


def test_parse_clarification_accepts_two_or_three_specific_options() -> None:
    decision = parse_intent_response(json.dumps(clarification_payload(), ensure_ascii=False))

    assert isinstance(decision, IntentDecision)
    assert decision.action == "clarify"
    assert decision.question is not None
    assert 2 <= len(decision.question.options) <= 3
    assert decision.slots.topic == "LangGraph"


@pytest.mark.parametrize("label", ["其他", "都不符合", "我直接补充", "Other"])
def test_parse_clarification_rejects_catch_all_options(label: str) -> None:
    payload = clarification_payload(options=[
        {"id": "a", "label": "看懂核心概念", "detail": "先建立直觉"},
        {"id": "b", "label": label, "detail": "再输入需求"},
    ])

    with pytest.raises((ValueError, ValidationError), match="catch-all"):
        parse_intent_response(json.dumps(payload, ensure_ascii=False))


def test_ready_for_plan_requires_normalized_onboarding_fields() -> None:
    payload = clarification_payload()
    payload.update({"action": "ready_for_plan", "question": None})

    with pytest.raises((ValueError, ValidationError), match="onboarding"):
        parse_intent_response(json.dumps(payload, ensure_ascii=False))


def test_ready_for_plan_preserves_slot_filling_and_normalized_route() -> None:
    payload = clarification_payload()
    payload.update({
        "action": "ready_for_plan",
        "summary": "用户要系统掌握 LangGraph 并做一个完整 Agent",
        "question": None,
        "slots": {
            **payload["slots"],
            "goal": "系统学习",
            "desired_outcome": "独立设计并交付 LangGraph Agent",
            "learning_scope": "complete_mastery",
        },
        "onboarding": {
            "goal_route": "foundation_engineer",
            "learning_mode": "systematic",
            "level_claim": "zero",
            "session_minutes": 25,
            "concept_scope": "not_applicable",
        },
    })

    decision = parse_intent_response(f"```json\n{json.dumps(payload, ensure_ascii=False)}\n```")

    assert decision.action == "ready_for_plan"
    assert decision.onboarding is not None
    assert decision.onboarding.goal_route == "foundation_engineer"
    assert decision.slots.desired_outcome == "独立设计并交付 LangGraph Agent"


def test_non_clarification_actions_cannot_smuggle_choices() -> None:
    payload = clarification_payload()
    payload["action"] = "answer_in_context"

    with pytest.raises((ValueError, ValidationError), match="question"):
        parse_intent_response(json.dumps(payload, ensure_ascii=False))
