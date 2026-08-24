import json

import pytest

from backend.lesson_manifest import build_starter_lesson
from backend.supplemental_practice import append_supplemental_questions, parse_supplemental_response


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


def test_parser_extracts_one_valid_json_object_after_codex_progress_text() -> None:
    raw = "已读取出题 Skills，正在对齐学习者难度。\n```json\n" + payload() + "\n```"

    questions = parse_supplemental_response(raw, expected_count=3)

    assert len(questions) == 3


def test_parser_normalizes_codex_text_option_alias_to_label() -> None:
    value = json.loads(payload())
    for question in value["questions"]:
        for option in question["options"]:
            option["text"] = option.pop("label")

    questions = parse_supplemental_response(json.dumps(value, ensure_ascii=False), expected_count=3)

    assert questions[0]["options"][0] == {"id": "a", "label": "正确"}


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


def test_append_questions_adds_clickable_pages_before_mastery_and_answer_keys() -> None:
    bundle = build_starter_lesson(
        topic="Go", language="go", session_minutes=25, goal_route="foundation_engineer",
    )
    questions = parse_supplemental_response(payload(), expected_count=3)

    updated = append_supplemental_questions(bundle, questions)

    added = [page for page in updated.manifest.pages if page.id.startswith("supplemental-")]
    mastery_index = next(index for index, page in enumerate(updated.manifest.pages) if page.type == "mastery")
    assert len(added) == 3
    assert all(page.type == "check" and page.options for page in added)
    assert all(updated.manifest.pages.index(page) < mastery_index for page in added)
    assert all(updated.answer_keys[page.id] == "a" for page in added)
    assert updated.manifest.progress.total_pages == len(updated.manifest.pages)
    assert bundle.manifest.progress.total_pages + 3 == updated.manifest.progress.total_pages


def test_append_questions_does_not_duplicate_existing_question_prompts() -> None:
    bundle = build_starter_lesson(
        topic="Go", language="go", session_minutes=25, goal_route="foundation_engineer",
    )
    questions = parse_supplemental_response(payload(), expected_count=3)

    first = append_supplemental_questions(bundle, questions)
    second = append_supplemental_questions(first, questions)

    assert len(second.manifest.pages) == len(first.manifest.pages)
    assert second.answer_keys == first.answer_keys
