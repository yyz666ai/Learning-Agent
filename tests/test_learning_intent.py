from __future__ import annotations

import json

import pytest
from pydantic import ValidationError
from backend import learning_intent

from backend.learning_intent import (
    IntentDecision,
    IntentSlots,
    build_intent_prompt,
    parse_intent_response,
    recover_explicit_interview_intent,
    validate_intent_against_message,
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
        for index in range(45)
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
    assert '"content": "旧消息 1"' not in prompt
    assert '"content": "旧消息 44"' in prompt
    assert "信息仍不足时可以继续追问" in prompt
    assert "不得重复已填槽位" in prompt


def test_explicit_beginner_interview_goal_does_not_route_to_concept_depth_choices() -> None:
    prompt = build_intent_prompt(
        message="我想面试 AI 前端，初学",
        history=[], slots={}, has_active_project=False, clarification_count=0,
    )

    assert "完整 target_role" in prompt
    assert "interview_sprint" in prompt
    assert "tech_stack" in prompt
    assert "interview_question_source" in prompt
    assert "interview_bank_intake" in prompt


def test_parse_clarification_accepts_two_or_three_specific_options() -> None:
    decision = parse_intent_response(json.dumps(clarification_payload(), ensure_ascii=False))

    assert isinstance(decision, IntentDecision)
    assert decision.action == "clarify"
    assert decision.question is not None
    assert 2 <= len(decision.question.options) <= 3
    assert decision.slots.topic == "LangGraph"


def test_interview_material_request_is_open_text_without_choice_options() -> None:
    payload = clarification_payload(options=[])
    payload["question"] = {
        "prompt": "如果你有收集的真实面试题，直接粘贴；暂时没有就回复‘没有’。",
        "slot": "interview_question_source",
        "options": [],
    }

    decision = parse_intent_response(json.dumps(payload, ensure_ascii=False))

    assert decision.question is not None
    assert decision.question.slot == "interview_question_source"
    assert decision.question.options == []


def test_interview_material_request_rejects_an_extra_choice_step() -> None:
    payload = clarification_payload(options=[])
    payload["question"] = {
        "prompt": "你有没有面试题？",
        "slot": "interview_question_source",
        "options": [
            {"id": "has", "label": "有", "detail": "下一步再粘贴"},
            {"id": "none", "label": "没有", "detail": "直接生成计划"},
        ],
    }

    with pytest.raises((ValueError, ValidationError), match="open text"):
        parse_intent_response(json.dumps(payload, ensure_ascii=False))


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
            "level_evidence": "用户说自己是零基础",
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


def test_ready_for_plan_rejects_invented_level_without_user_evidence() -> None:
    payload = clarification_payload()
    payload.update({
        "action": "ready_for_plan",
        "summary": "用户要面试前端岗",
        "question": None,
        "slots": {
            **payload["slots"], "topic": "前端", "goal": "面试前端岗",
            "desired_outcome": "完成前端岗模拟面试", "level_evidence": None,
        },
        "onboarding": {
            "goal_route": "interview_sprint", "learning_mode": "practice",
            "level_claim": "some", "session_minutes": 25,
            "concept_scope": "not_applicable",
        },
    })

    with pytest.raises((ValueError, ValidationError), match="level evidence"):
        parse_intent_response(json.dumps(payload, ensure_ascii=False))


def test_concept_ready_does_not_require_level_evidence() -> None:
    payload = clarification_payload()
    payload.update({
        "action": "ready_for_plan", "summary": "用户只想理解 RAG", "question": None,
        "slots": {**payload["slots"], "topic": "RAG", "goal": "理解 RAG", "desired_outcome": "能解释 RAG"},
        "onboarding": {
            "goal_route": "concept_clarity", "learning_mode": "systematic",
            "level_claim": "zero", "session_minutes": 25, "concept_scope": "meaning_only",
        },
    })

    assert parse_intent_response(json.dumps(payload, ensure_ascii=False)).action == "ready_for_plan"


def test_explicit_definition_request_rejects_generic_route_choices() -> None:
    decision = parse_intent_response(json.dumps(clarification_payload(), ensure_ascii=False))

    with pytest.raises(ValueError, match="concept-definition"):
        validate_intent_against_message(decision, "我想弄懂大模型的 RAG 是什么意思")


def test_explicit_definition_request_accepts_concept_plan_without_level_question() -> None:
    payload = clarification_payload()
    payload.update({
        "action": "ready_for_plan", "summary": "解释 RAG", "question": None,
        "slots": {**payload["slots"], "topic": "RAG", "goal": "理解 RAG", "desired_outcome": "能解释 RAG"},
        "onboarding": {
            "goal_route": "concept_clarity", "learning_mode": "systematic",
            "level_claim": "zero", "session_minutes": 25, "concept_scope": "meaning_only",
        },
    })
    decision = parse_intent_response(json.dumps(payload, ensure_ascii=False))

    assert validate_intent_against_message(decision, "RAG 是什么？") is decision


def test_explicit_level_rejects_repeated_level_question() -> None:
    payload = clarification_payload()
    payload["slots"]["topic"] = "Java 后端"
    payload["question"] = {
        "prompt": "你目前基础如何？", "slot": "level_evidence",
        "options": [
            {"id": "beginner", "label": "初学", "detail": "从零开始"},
            {"id": "some", "label": "有基础", "detail": "学过一些"},
            {"id": "experienced", "label": "熟练", "detail": "有工程经验"},
        ],
    }
    decision = parse_intent_response(json.dumps(payload, ensure_ascii=False))

    with pytest.raises(ValueError, match="explicit learner level"):
        validate_intent_against_message(decision, "我要面试 Java 后端岗，有一点基础")


def test_ready_intent_rejects_model_authored_level_evidence_not_found_in_learner_context() -> None:
    payload = clarification_payload()
    payload.update({
        "action": "ready_for_plan", "summary": "前端面试", "question": None,
        "slots": {
            **payload["slots"], "topic": "前端", "goal": "准备前端面试",
            "desired_outcome": "完成模拟面试", "level_evidence": "有基础",
            "target_role": "前端", "tech_stack": ["React"], "interview_question_source": "none",
        },
        "onboarding": {
            "goal_route": "interview_sprint", "learning_mode": "practice",
            "level_claim": "some", "session_minutes": 25,
            "concept_scope": "not_applicable",
        },
    })
    decision = parse_intent_response(json.dumps(payload, ensure_ascii=False))

    with pytest.raises(ValueError, match="learner context"):
        validate_intent_against_message(decision, "我要面试前端岗")


def test_ready_intent_rejects_verbatim_text_that_is_not_level_evidence() -> None:
    payload = clarification_payload()
    payload.update({
        "action": "ready_for_plan", "summary": "前端面试", "question": None,
        "slots": {
            **payload["slots"], "topic": "前端", "goal": "准备前端面试",
            "desired_outcome": "完成模拟面试", "level_evidence": "面试",
            "target_role": "前端", "tech_stack": ["React"], "interview_question_source": "none",
        },
        "onboarding": {
            "goal_route": "interview_sprint", "learning_mode": "practice",
            "level_claim": "some", "session_minutes": 25,
            "concept_scope": "not_applicable",
        },
    })
    decision = parse_intent_response(json.dumps(payload, ensure_ascii=False))

    with pytest.raises(ValueError, match="learner context"):
        validate_intent_against_message(decision, "我要面试前端岗")


def test_level_only_reply_cannot_replace_confirmed_topic_or_outcome() -> None:
    payload = clarification_payload()
    payload.update({
        "action": "ready_for_plan", "summary": "开始 Django", "question": None,
        "slots": {
            **payload["slots"], "topic": "Django", "goal": "学 Django",
            "desired_outcome": "做 Django 项目", "level_evidence": "初学",
        },
        "onboarding": {
            "goal_route": "project_delivery", "learning_mode": "project",
            "level_claim": "zero", "session_minutes": 25,
            "concept_scope": "not_applicable",
        },
    })
    decision = parse_intent_response(json.dumps(payload, ensure_ascii=False))

    with pytest.raises(ValueError, match="preserve confirmed topic"):
        validate_intent_against_message(
            decision, "初学",
            existing_slots={
                "topic": "LangGraph", "goal": "学习 LangGraph",
                "desired_outcome": "做客服 Agent", "target_context": "客服",
            },
        )


def test_model_authored_prior_level_slot_is_not_treated_as_learner_evidence() -> None:
    payload = clarification_payload()
    payload.update({
        "action": "ready_for_plan", "summary": "前端面试", "question": None,
        "slots": {
            **payload["slots"], "topic": "前端", "goal": "前端面试",
            "desired_outcome": "完成模拟面试", "level_evidence": "有基础",
            "target_role": "前端", "tech_stack": ["React"], "interview_question_source": "none",
        },
        "onboarding": {
            "goal_route": "interview_sprint", "learning_mode": "practice",
            "level_claim": "some", "session_minutes": 25,
            "concept_scope": "not_applicable",
        },
    })
    decision = parse_intent_response(json.dumps(payload, ensure_ascii=False))

    with pytest.raises(ValueError, match="learner context"):
        validate_intent_against_message(
            decision, "继续",
            history=[{"role": "user", "content": "我要面试前端岗"}],
            existing_slots={"topic": "前端", "level_evidence": "有基础"},
        )


def test_latest_user_level_correction_wins_over_older_history() -> None:
    payload = clarification_payload()
    payload.update({
        "action": "ready_for_plan", "summary": "按熟练水平准备", "question": None,
        "slots": {
            **payload["slots"], "topic": "前端", "goal": "前端面试",
            "desired_outcome": "完成模拟面试", "level_evidence": "已经熟练",
            "target_role": "前端", "tech_stack": ["React"], "interview_question_source": "none",
        },
        "onboarding": {
            "goal_route": "interview_sprint", "learning_mode": "practice",
            "level_claim": "experienced", "session_minutes": 25,
            "concept_scope": "not_applicable",
        },
    })
    decision = parse_intent_response(json.dumps(payload, ensure_ascii=False))

    assert validate_intent_against_message(
        decision, "其实我已经熟练",
        history=[{"role": "user", "content": "我是初学者"}],
    ) is decision


def test_correction_prompt_requires_one_level_question_without_rewriting_known_slots() -> None:
    original = build_intent_prompt(
        message="我要面试前端岗", history=[], slots={},
        has_active_project=False, clarification_count=0,
    )
    correction = learning_intent.build_intent_correction_prompt(original, "ready_for_plan requires level evidence")

    assert "不得猜测水平" in correction
    assert "只修复上述具体错误" in correction
    assert "选项必须是" not in correction
    assert "前端" in correction


def test_explicit_interview_recovery_asks_only_for_missing_level() -> None:
    decision = recover_explicit_interview_intent("我要面试前端岗")

    assert decision is not None
    assert decision.action == "clarify"
    assert decision.slots.topic == "前端"
    assert decision.question is not None
    assert decision.question.slot == "level_evidence"
    assert [option.label for option in decision.question.options] == ["初学", "有基础", "熟练"]


def test_explicit_interview_recovery_uses_stated_level_and_role() -> None:
    decision = recover_explicit_interview_intent("我是一名熟练的产品经理，想准备 AI 产品经理面试")

    assert decision is not None
    assert decision.action == "clarify"
    assert decision.slots.topic == "AI 产品经理"
    assert decision.slots.level_evidence == "熟练"
    assert decision.slots.target_role == "AI 产品经理"
    assert decision.question is not None
    assert decision.question.slot == "tech_stack"


def test_interview_recovery_preserves_prior_level_when_user_only_adds_stack() -> None:
    prior = {
        "intent_family": "面试准备", "topic": "AI 前端", "target_role": "AI 前端",
        "goal": "准备 AI 前端面试", "desired_outcome": "完成岗位模拟面试",
        "level_evidence": "初学",
    }

    decision = recover_explicit_interview_intent("React 和 TypeScript", prior)

    assert decision is not None
    assert decision.action == "clarify"
    assert decision.slots.level_evidence == "初学"
    assert decision.slots.tech_stack == ["React", "TypeScript"]
    assert decision.question is not None
    assert decision.question.slot == "interview_question_source"
    assert decision.question.options == []


def test_stack_only_reply_cannot_replace_confirmed_interview_role() -> None:
    payload = clarification_payload()
    payload["slots"].update({
        "topic": "Java 后端", "target_role": "Java 后端", "tech_stack": ["React"],
        "goal": "准备 Java 后端面试", "desired_outcome": "完成岗位模拟面试",
        "level_evidence": "初学",
    })
    decision = parse_intent_response(json.dumps(payload, ensure_ascii=False))

    with pytest.raises(ValueError, match="preserve confirmed topic"):
        validate_intent_against_message(
            decision, "React 和 TypeScript",
            existing_slots={
                "topic": "AI 前端", "target_role": "AI 前端",
                "goal": "准备 AI 前端面试", "desired_outcome": "完成岗位模拟面试",
                "level_evidence": "初学",
            },
        )


def test_interview_plan_requires_role_tech_stack_and_question_source() -> None:
    payload = clarification_payload()
    payload.update({
        "action": "ready_for_plan", "summary": "AI 前端面试", "question": None,
        "slots": {
            **payload["slots"], "topic": "AI 前端", "target_role": "AI 前端",
            "goal": "准备 AI 前端面试", "desired_outcome": "完成模拟面试",
            "level_evidence": "初学", "tech_stack": [],
            "interview_question_source": "unknown",
        },
        "onboarding": {
            "goal_route": "interview_sprint", "learning_mode": "practice",
            "level_claim": "zero", "session_minutes": 25,
            "concept_scope": "not_applicable",
        },
    })

    with pytest.raises((ValueError, ValidationError), match="tech stack"):
        parse_intent_response(json.dumps(payload, ensure_ascii=False))

    payload["slots"]["tech_stack"] = ["React", "TypeScript"]
    with pytest.raises((ValueError, ValidationError), match="question source"):
        parse_intent_response(json.dumps(payload, ensure_ascii=False))

    payload["slots"]["interview_question_source"] = "none"
    decision = parse_intent_response(json.dumps(payload, ensure_ascii=False))
    assert decision.action == "ready_for_plan"
    assert decision.slots.tech_stack == ["React", "TypeScript"]


def test_interview_question_source_has_questions_routes_to_intake_before_plan() -> None:
    payload = clarification_payload()
    payload.update({
        "action": "interview_bank_intake", "summary": "等待粘贴面试题", "question": None,
        "slots": {
            **payload["slots"], "topic": "AI 前端", "target_role": "AI 前端",
            "goal": "准备 AI 前端面试", "desired_outcome": "完成模拟面试",
            "level_evidence": "初学", "tech_stack": ["React", "TypeScript"],
            "interview_question_source": "has_questions",
        },
        "onboarding": None,
    })

    decision = parse_intent_response(json.dumps(payload, ensure_ascii=False))
    assert decision.action == "interview_bank_intake"
    assert decision.slots.interview_question_source == "has_questions"


def test_confirmed_interview_question_source_cannot_change_without_user_correction() -> None:
    payload = clarification_payload()
    payload.update({
        "action": "ready_for_plan", "summary": "准备开始", "question": None,
        "slots": {
            **payload["slots"], "topic": "AI 前端", "target_role": "AI 前端",
            "goal": "准备面试", "desired_outcome": "完成模拟面试",
            "level_evidence": "初学", "tech_stack": ["React"],
            "interview_question_source": "none",
        },
        "onboarding": {
            "goal_route": "interview_sprint", "learning_mode": "practice", "level_claim": "zero",
            "session_minutes": 25, "concept_scope": "not_applicable", "topic_type": "custom",
            "deadline_days": None, "teaching_preference": "balanced",
        },
    })
    decision = parse_intent_response(json.dumps(payload, ensure_ascii=False))
    prior = IntentSlots.model_validate({
        **payload["slots"], "interview_question_source": "has_questions", "interview_question_count": 0,
    })

    with pytest.raises(ValueError, match="interview_question_source"):
        validate_intent_against_message(
            decision, "其实这些题比较难，但继续", existing_slots=prior,
            history=[{"role": "user", "content": "我是初学，有现成面试题"}],
        )


def test_interview_question_source_understands_double_negation() -> None:
    assert learning_intent._interview_source_from_text("不是没有题，我有收集的面试题") == "has_questions"
    assert learning_intent._interview_source_from_text("我并非有现成面试题") == "none"
    assert learning_intent._interview_source_from_text("没有") == "none"


def test_explicit_interview_recovery_does_not_guess_for_unrelated_learning_request() -> None:
    assert recover_explicit_interview_intent("我想系统学习 LangGraph") is None


def test_non_clarification_actions_cannot_smuggle_choices() -> None:
    payload = clarification_payload()
    payload["action"] = "answer_in_context"

    with pytest.raises((ValueError, ValidationError), match="question"):
        parse_intent_response(json.dumps(payload, ensure_ascii=False))
