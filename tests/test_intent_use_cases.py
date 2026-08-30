"""Behavioral contracts from UC02/14/15/18/20; no live model required."""
import pytest

from backend.learning_intent import IntentDecision, IntentQuestion, validate_intent_against_message


def ready(message, *, route="gap_upgrade", level="some", scope="not_applicable"):
    return IntentDecision.model_validate({
        "action": "ready_for_plan", "confidence": .9, "summary": "目标已明确",
        "slots": {"topic": "Go", "desired_outcome": "补齐并发能力", "level_evidence": message},
        "onboarding": {"goal_route": route, "level_claim": level,
                       "learning_mode": "systematic", "concept_scope": scope},
    })


def test_greeting_allows_open_topic_question():
    q = IntentQuestion(prompt="你想学什么？", slot="topic", options=[], interaction="text")
    assert q.interaction == "text"


def test_material_questions_reject_choices():
    with pytest.raises(ValueError, match="open text"):
        IntentQuestion(prompt="请发仓库", slot="target_context", interaction="material", options=[
            {"id": "a", "label": "有", "detail": "有仓库"},
            {"id": "b", "label": "无", "detail": "无仓库"}])


def test_stack_question_cannot_also_request_interview_material():
    result = IntentDecision(action="clarify", confidence=.9, summary="确认方向",
        slots={"topic": "AI产品经理"}, question={"prompt": "主要侧重什么方向？另外有面经可以直接粘贴。", "slot": "tech_stack", "options": []})
    with pytest.raises(ValueError, match="one slot"):
        validate_intent_against_message(result, "想面试AI产品经理")


def test_concept_and_code_is_not_downgraded():
    text = "我是初学者，解释一下 RAG 是什么，还要用 Python 最小代码演示它怎么实现。"
    result = ready(text, route="concept_clarity", level="zero", scope="code_walkthrough")
    assert validate_intent_against_message(result, text) is result


def test_concept_explicitly_without_code_stays_meaning_only():
    text = "解释一下RAG是什么，不需要代码"
    assert validate_intent_against_message(ready(text, route="concept_clarity", scope="meaning_only"), text)


def test_years_alone_do_not_prove_expert_mastery():
    text = "我写了三年Python，想学FastAPI"
    with pytest.raises(ValueError, match="experienced"):
        validate_intent_against_message(ready(text, level="experienced"), text)


def test_contextual_definition_may_answer_without_new_plan():
    result = IntentDecision(action="answer_in_context", confidence=.9, summary="解释本页state", slots={})
    assert validate_intent_against_message(result, "这里的 state 是什么意思？") is result


@pytest.mark.parametrize("text", [
    "我不是零基础，我写了三年 Go，想进阶并发与性能优化。",
    "我写了三年 Python，做过两个线上项目，想用 FastAPI 开发服务端 API。",
])
def test_real_experience_is_valid_evidence(text):
    result = ready(text)
    assert validate_intent_against_message(result, text) is result


def test_negation_does_not_allow_zero_claim():
    text = "我不是零基础，我写了三年 Go，想进阶并发与性能优化。"
    with pytest.raises(ValueError, match="level"):
        validate_intent_against_message(ready(text, level="zero"), text)


def test_fabricated_experience_rejected():
    with pytest.raises(ValueError, match="evidence"):
        validate_intent_against_message(ready("我写了三年Go"), "我想学Go")


def test_typographic_quotes_are_not_fabricated_experience():
    result = ready("I've shipped React apps for three years")
    assert validate_intent_against_message(result, "I’ve shipped React apps for three years; help me learn streaming")


def test_already_filled_outcome_not_asked_again():
    result = IntentDecision(action="clarify", confidence=.9, summary="还需问目标",
        slots={"topic": "Python", "desired_outcome": "独立开发项目", "level_evidence": "零基础"},
        question={"prompt": "想学到什么程度？", "slot": "desired_outcome", "options": []})
    with pytest.raises(ValueError, match="already filled"):
        validate_intent_against_message(result, "我零基础，想系统学Python，直到能独立开发项目")


def test_multiple_known_goals_can_ask_unknown_priority():
    result = IntentDecision(action="clarify", confidence=.9, summary="确认先后",
        slots={"topic": "操作系统", "goal": "小项目与考试"},
        question={"prompt": "这次先做哪个？", "slot": "priority", "options": []})
    assert validate_intent_against_message(result, "想写个操作系统小项目，也想准备考试，没想好先做哪个")
    assert hasattr(result.slots, "priority")


def test_ready_may_reuse_explicit_goal_as_outcome_without_more_questions():
    payload = ready("有基础").model_dump()
    payload["slots"].update(goal="补泛型和并发", desired_outcome=None)
    result = IntentDecision.model_validate(payload)
    assert result.slots.desired_outcome == "补泛型和并发"


def test_domain_specific_foundation_is_real_evidence():
    result = ready("有C基础", route="academic_course")
    result.slots.course_scope = "通用操作系统范围"
    assert validate_intent_against_message(result, "本科操作系统跟课，有C基础") is result


def test_course_without_scope_must_ask_for_chapters():
    with pytest.raises(ValueError, match="course_scope"):
        validate_intent_against_message(ready("有C基础", route="academic_course"), "操作系统跟课，有C基础，每周学习")


def test_existing_repo_reading_cannot_evade_material_check_by_changing_route():
    with pytest.raises(ValueError, match="repository"):
        validate_intent_against_message(ready("初学", route="syntax_reading", level="zero"), "我是初学，只想看懂现有项目")


def test_specific_repo_requires_material_or_explicit_generic_opt_out():
    result = ready("有基础", route="urgent_codebase")
    with pytest.raises(ValueError, match="repository"):
        validate_intent_against_message(result, "有基础，两天看懂同事的项目")


@pytest.mark.parametrize("route", ["academic_course", "exam_review"])
def test_academic_routes_share_onboarding_contract(route):
    from backend.onboarding import OnboardingSubmission, ROUTE_STRATEGIES, ROUTE_PHASES
    decision = ready("有基础", route=route)
    submission = OnboardingSubmission(user_id="test", topic={"type": "custom", "value": "数据结构"},
                                      **decision.onboarding.model_dump(exclude={"topic_type"}))
    assert submission.goal_route in ROUTE_STRATEGIES
    assert ROUTE_PHASES[submission.goal_route]
