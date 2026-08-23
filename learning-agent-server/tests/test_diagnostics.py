import pytest

from backend.diagnostics import (
    answer_diagnosis,
    parse_generated_diagnosis,
    public_session,
    start_diagnosis,
    summarize_diagnosis,
)
import json


def choose_correct(session):
    return session["question"]["correct_option_id"]


def choose_incorrect(session):
    correct = choose_correct(session)
    return next(
        option["id"] for option in session["question"]["options"]
        if option["id"] != correct
    )


def test_questions_are_real_click_options():
    session = start_diagnosis(topic="go", level_claim="some")
    question = public_session(session)["question"]

    assert 2 <= len(question["options"]) <= 5
    assert all(set(option) == {"id", "label"} for option in question["options"])
    assert "correct_option_id" not in question


def test_three_consistent_answers_finish_diagnosis():
    session = start_diagnosis(topic="go", level_claim="some")
    for _ in range(3):
        session = answer_diagnosis(session, choose_correct(session))

    assert session["complete"] is True
    assert session["answered_count"] == 3
    assert summarize_diagnosis(session).answered_count == 3


def test_mixed_boundary_answers_get_one_fourth_question():
    session = start_diagnosis(topic="go", level_claim="some")
    for selected in (choose_correct, choose_incorrect, choose_correct):
        session = answer_diagnosis(session, selected(session))

    assert session["complete"] is False
    session = answer_diagnosis(session, choose_correct(session))
    assert session["complete"] is True
    assert session["answered_count"] == 4


def test_diagnosis_never_exceeds_ten():
    session = start_diagnosis(topic="unknown subject", level_claim="experienced")
    while not session["complete"]:
        selected = choose_correct(session) if session["answered_count"] % 2 == 0 else choose_incorrect(session)
        session = answer_diagnosis(session, selected)
    assert session["answered_count"] <= 10


def test_invalid_click_does_not_advance():
    session = start_diagnosis(topic="go", level_claim="some")
    with pytest.raises(ValueError, match="option"):
        answer_diagnosis(session, "typed free-form answer")
    assert session["answered_count"] == 0


def test_answered_question_cannot_be_replayed():
    session = start_diagnosis(topic="go", level_claim="some")
    old_question_id = session["question"]["id"]
    session = answer_diagnosis(session, choose_correct(session))
    with pytest.raises(ValueError, match="question"):
        answer_diagnosis(session, choose_correct(session), question_id=old_question_id)


def test_skill_generated_diagnosis_is_a_small_clickable_topic_specific_question_set():
    questions = parse_generated_diagnosis(json.dumps({"questions": [
        {"id": "java-generics", "prompt": "List<String> 的主要好处？", "dimension": "syntax", "options": [
            {"id": "a", "label": "限制元素类型"}, {"id": "b", "label": "自动联网"}], "correct_option_id": "a"},
        {"id": "java-exception", "prompt": "捕获异常后应做什么？", "dimension": "debugging", "options": [
            {"id": "a", "label": "记录或处理"}, {"id": "b", "label": "删除项目"}], "correct_option_id": "a"},
        {"id": "java-api", "prompt": "HTTP 201 表示什么？", "dimension": "api", "options": [
            {"id": "a", "label": "资源已创建"}, {"id": "b", "label": "服务关闭"}], "correct_option_id": "a"},
    ]}, ensure_ascii=False))

    session = start_diagnosis(topic="Java API", level_claim="some", questions=questions)

    assert len(session["bank"]) == 3
    assert all(2 <= len(question["options"]) <= 4 for question in session["bank"])
    assert session["bank"][0]["id"] == "java-generics"
