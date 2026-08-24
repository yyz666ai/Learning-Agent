import json

import pytest

from backend.supplemental_practice import parse_supplemental_response


def payload() -> str:
    return json.dumps({"questions": [
        {"title": f"练习 {index}", "prompt": f"问题 {index}？", "options": [
            {"id": "a", "label": "正确"}, {"id": "b", "label": "错误"},
        ], "correct_option_id": "a", "explanation": f"解析 {index}"}
        for index in range(1, 4)
    ]}, ensure_ascii=False)


def test_parser_accepts_three_valid_answered_choice_questions() -> None:
    questions = parse_supplemental_response(payload(), expected_count=3)

    assert len(questions) == 3
    assert questions[0]["correct_option_id"] == "a"


def test_parser_rejects_answer_not_present_in_options() -> None:
    value = json.loads(payload())
    value["questions"][0]["correct_option_id"] = "c"

    with pytest.raises(ValueError, match="answer"):
        parse_supplemental_response(json.dumps(value, ensure_ascii=False), expected_count=3)


def test_parser_rejects_duplicate_prompts() -> None:
    value = json.loads(payload())
    value["questions"][1]["prompt"] = value["questions"][0]["prompt"]

    with pytest.raises(ValueError, match="duplicate"):
        parse_supplemental_response(json.dumps(value, ensure_ascii=False), expected_count=3)
