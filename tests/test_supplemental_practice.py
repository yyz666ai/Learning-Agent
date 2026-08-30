import json
from pathlib import PurePosixPath

import pytest

from backend.lesson_manifest import build_starter_lesson
from backend.supplemental_practice import append_supplemental_questions, parse_supplemental_response


def programming_question(kind: str = "programming") -> dict:
    return {
        "kind": kind, "title": "实现猜数字", "prompt": "编写程序读取输入并提示猜测是否正确。",
        "milestones": ["先实现固定目标数字。", "再处理无效输入。"],
        "hints": ["先考虑输入的类型。"], "completion_criteria": "提交可运行程序，正确处理正确、错误和无效输入。",
    }


@pytest.mark.parametrize("count", [1, 2, 3, 4, 5])
def test_parser_supports_explicit_or_automatic_one_to_five_questions(count: int) -> None:
    question = json.loads(payload())["questions"][0]
    raw = json.dumps({"questions": [{**question, "prompt": f"new prompt {index}"} for index in range(count)]})

    assert len(parse_supplemental_response(raw, expected_count=count)) == count
    assert len(parse_supplemental_response(raw, expected_count=None)) == count


@pytest.mark.parametrize("count", [0, 6])
def test_parser_rejects_out_of_range_automatic_counts(count: int) -> None:
    raw = json.dumps({"questions": [{**programming_question(), "prompt": f"new {index}"} for index in range(count)]})
    with pytest.raises(ValueError, match="1 to 5"):
        parse_supplemental_response(raw, expected_count=None)


@pytest.mark.parametrize("kind", ["programming", "project"])
def test_parser_preserves_typed_programming_practice_without_answers(kind: str) -> None:
    question = programming_question(kind)
    parsed = parse_supplemental_response(json.dumps({"questions": [question]}), expected_count=1)[0]

    assert parsed == {**question, "options": [], "correct_option_id": "", "explanation": question["completion_criteria"]}


@pytest.mark.parametrize("field,value", [
    ("title", 5), ("prompt", []), ("kind", "unknown"), ("hints", []), ("hints", "hint"),
    ("hints", [1]), ("completion_criteria", ""), ("completion_criteria", {}),
    ("milestones", "step"), ("milestones", [False]), ("milestones", ["only one"]),
    ("title", "x" * 241), ("prompt", "x" * 2001), ("completion_criteria", "x" * 1001),
    ("hints", ["x" * 1001]), ("milestones", ["x" * 1001, "step 2"]),
    ("practice_path", "../../escape"), ("path", "/tmp/escape"),
    ("options", [{"id": "a", "label": "answer"}]), ("correct_option_id", "a"),
    ("answer", "complete solution"), ("code", "print('solution')"),
])
def test_parser_rejects_invalid_programming_records(field: str, value: object) -> None:
    question = {**programming_question("project"), field: value}
    with pytest.raises(ValueError):
        parse_supplemental_response(json.dumps({"questions": [question]}), expected_count=None)


@pytest.mark.parametrize("field", ["title", "prompt", "hints", "completion_criteria", "milestones"])
def test_parser_rejects_missing_required_project_fields(field: str) -> None:
    question = programming_question("project")
    question.pop(field)
    with pytest.raises(ValueError):
        parse_supplemental_response(json.dumps({"questions": [question]}), expected_count=None)


def test_parser_default_kind_remains_choice() -> None:
    assert parse_supplemental_response(payload(), expected_count=3)[0]["kind"] == "choice"


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


@pytest.mark.parametrize("kind", ["programming", "project"])
def test_append_programming_practice_preserves_homework_and_has_safe_separate_path(kind: str) -> None:
    bundle = build_starter_lesson(topic="Go", language="go", session_minutes=25, goal_route="foundation_engineer")
    question = programming_question(kind)
    questions = parse_supplemental_response(json.dumps({"questions": [question]}), expected_count=1)

    updated = append_supplemental_questions(bundle, questions)

    added = next(page for page in updated.manifest.pages if page.id.startswith("supplemental-"))
    assert added.type == "practice"
    assert added.practice_kind == "homework"
    assert added.options == [] and added.code == ""
    assert added.question == question["prompt"]
    assert added.practice_path.startswith(bundle.manifest.practice_path + "/supplemental-")
    assert ".." not in PurePosixPath(added.practice_path).parts
    assert added.completion_criteria == question["completion_criteria"]
    assert all(value in added.markdown for value in [question["prompt"], *question["milestones"], *question["hints"], question["completion_criteria"]])
    assert "<details>" in added.markdown
    assert updated.answer_keys == bundle.answer_keys
    assert next(page for page in updated.manifest.pages if page.id == "practice") == next(page for page in bundle.manifest.pages if page.id == "practice")
    assert updated.manifest.pages.index(added) < next(index for index, page in enumerate(updated.manifest.pages) if page.type == "mastery")
    assert len(append_supplemental_questions(updated, questions).manifest.pages) == len(updated.manifest.pages)


@pytest.mark.parametrize("unsafe_path", ["../escape", "/tmp/escape", "projects/../../escape", "projects\\..\\escape"])
def test_append_programming_rejects_unsafe_manifest_path(unsafe_path: str) -> None:
    bundle = build_starter_lesson(topic="Go", language="go", session_minutes=25, goal_route="foundation_engineer")
    bundle.manifest.practice_path = unsafe_path
    questions = parse_supplemental_response(json.dumps({"questions": [programming_question()]}), expected_count=1)
    with pytest.raises(ValueError, match="path"):
        append_supplemental_questions(bundle, questions)


def test_append_avoids_existing_homework_directory_even_with_different_page_id() -> None:
    bundle = build_starter_lesson(topic="Go", language="go", session_minutes=25, goal_route="foundation_engineer")
    questions = parse_supplemental_response(json.dumps({"questions": [programming_question()]}), expected_count=1)
    first = append_supplemental_questions(bundle, questions)
    added = next(page for page in first.manifest.pages if page.id.startswith("supplemental-"))
    existing = next(page for page in bundle.manifest.pages if page.id == "practice")
    existing.practice_path = added.practice_path

    updated = append_supplemental_questions(bundle, questions)

    new_page = next(page for page in updated.manifest.pages if page.id.startswith("supplemental-"))
    assert new_page.practice_path != existing.practice_path


def test_append_rejects_more_than_24_pages_without_changing_original_bundle() -> None:
    bundle = build_starter_lesson(topic="Go", language="go", session_minutes=25, goal_route="foundation_engineer")
    bundle.manifest.pages += [bundle.manifest.pages[0].model_copy(update={"id": f"extra-{index}"}) for index in range(19)]
    original = bundle.manifest.model_dump()
    questions = parse_supplemental_response(payload(), expected_count=3)
    with pytest.raises(ValueError, match="room"):
        append_supplemental_questions(bundle, questions)
    assert bundle.manifest.model_dump() == original


def test_programming_practice_round_trips_and_registers_as_homework(tmp_path) -> None:
    from backend.lesson_generator import load_lesson_bundle, save_lesson_bundle
    from backend.practice_bank import PracticeBankStore

    bundle = build_starter_lesson(topic="Go", language="go", session_minutes=25, goal_route="foundation_engineer")
    questions = parse_supplemental_response(json.dumps({"questions": [programming_question("project")]}), expected_count=1)
    updated = append_supplemental_questions(bundle, questions)

    save_lesson_bundle(tmp_path, "test-user", updated)
    restored = load_lesson_bundle(tmp_path, "test-user", updated.manifest.knowledge_point_id)
    records = PracticeBankStore(tmp_path).register_lesson("test-user", restored.manifest, answer_keys=restored.answer_keys)

    page = next(page for page in restored.manifest.pages if page.id.startswith("supplemental-"))
    record = next(record for record in records if record["page_id"] == page.id)
    assert page.type == "practice" and page.practice_kind == "homework"
    assert page.markdown == next(page for page in updated.manifest.pages if page.id.startswith("supplemental-")).markdown
    assert record["source"] == "homework" and record["kind"] == "homework"
    assert record["options"] == [] and not record.get("answer")
    assert record["practice_path"] == page.practice_path
    assert restored.answer_keys == bundle.answer_keys


def test_parser_rejects_duplicate_prompts_across_kinds() -> None:
    choice = json.loads(payload())["questions"][0]
    programming = {**programming_question(), "prompt": choice["prompt"]}
    with pytest.raises(ValueError, match="duplicate"):
        parse_supplemental_response(json.dumps({"questions": [choice, programming]}), expected_count=None)


@pytest.mark.parametrize("count", [True, 0, 6, "3", 1.5])
def test_parser_rejects_invalid_expected_count(count) -> None:
    with pytest.raises(ValueError, match="count"):
        parse_supplemental_response(payload(), expected_count=count)


def test_parser_rejects_explicit_count_mismatch() -> None:
    with pytest.raises(ValueError, match="requested"):
        parse_supplemental_response(payload(), expected_count=2)
