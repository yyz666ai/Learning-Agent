from pathlib import Path

import pytest

from backend.lesson_manifest import build_starter_lesson
from backend.practice_bank import PracticeBankStore


def test_changed_question_does_not_restore_old_pass(tmp_path: Path):
    from backend.lesson_context import restored_checks
    bundle = build_starter_lesson(topic="Go", language="go", session_minutes=20, goal_route="foundation_engineer")
    store = PracticeBankStore(tmp_path)
    store.register_lesson("test", bundle.manifest, answer_keys=bundle.answer_keys)
    store.record_choice_attempt("test", lesson_id=bundle.manifest.lesson_id, page_id="check-label", selected_option_id="b", correct=True)
    assert restored_checks(bundle, store.list_items("test")) == [{"page_id": "check-label", "correct": True}]
    bundle.manifest.pages[2].question = "全新的题目，哪项正确？"
    store.register_lesson("test", bundle.manifest, answer_keys=bundle.answer_keys)
    assert restored_checks(bundle, store.list_items("test")) == []


def test_quote_is_grounded_and_versioned():
    from backend.lesson_context import LessonReference, lesson_revision, validate_reference
    bundle = build_starter_lesson(topic="Go", language="go", session_minutes=20, goal_route="foundation_engineer")
    reference = LessonReference(lesson_id=bundle.manifest.lesson_id, page_id="example", revision=lesson_revision(bundle.manifest), quote="package main")
    assert validate_reference(bundle, reference)["page_title"] == bundle.manifest.pages[1].title
    with pytest.raises(ValueError, match="quote"):
        validate_reference(bundle, reference.model_copy(update={"quote": "not in this page"}))
    with pytest.raises(ValueError, match="version"):
        validate_reference(bundle, reference.model_copy(update={"revision": "0" * 64}))
    with pytest.raises(ValueError, match="lesson"):
        validate_reference(bundle, reference.model_copy(update={"lesson_id": "someone-else"}))


def test_markdown_rendered_selection_matches_without_exposing_answers():
    from backend.lesson_context import LessonReference, lesson_revision, validate_reference
    bundle = build_starter_lesson(topic="Go", language="go", session_minutes=20, goal_route="foundation_engineer")
    bundle.manifest.pages[0].markdown = "**变量** 保存 `值`。"
    ref = LessonReference(lesson_id=bundle.manifest.lesson_id, page_id="concept", revision=lesson_revision(bundle.manifest), quote="变量 保存 值。")
    result = validate_reference(bundle, ref)
    assert result["quote"] == "变量 保存 值。"
    assert "answer_keys" not in result


def test_code_selection_preserves_operators_and_generic_syntax():
    from backend.lesson_context import LessonReference, lesson_revision, validate_reference
    bundle = build_starter_lesson(topic="Go", language="go", session_minutes=20, goal_route="foundation_engineer")
    bundle.manifest.pages[1].code = "result := left * right\nvar items []Box<T>"
    ref = LessonReference(lesson_id=bundle.manifest.lesson_id, page_id="example", revision=lesson_revision(bundle.manifest), quote="*")
    assert validate_reference(bundle, ref)["quote"] == "*"
    assert validate_reference(bundle, ref.model_copy(update={"quote": "<T>"}))["quote"] == "<T>"
    with pytest.raises(ValueError, match="quote"):
        validate_reference(bundle, ref.model_copy(update={"quote": "result := left ** right"}))


@pytest.mark.parametrize("field", ["code", "markdown"])
def test_changed_question_material_does_not_restore_pass(tmp_path: Path, field: str):
    from backend.lesson_context import restored_checks
    bundle = build_starter_lesson(topic="Go", language="go", session_minutes=20, goal_route="foundation_engineer")
    store = PracticeBankStore(tmp_path)
    store.register_lesson("test", bundle.manifest, answer_keys=bundle.answer_keys)
    store.record_choice_attempt("test", lesson_id=bundle.manifest.lesson_id, page_id="check-label", selected_option_id="b", correct=True)
    setattr(bundle.manifest.pages[2], field, "changed question material")
    store.register_lesson("test", bundle.manifest, answer_keys=bundle.answer_keys)
    assert restored_checks(bundle, store.list_items("test")) == []


@pytest.mark.parametrize("markdown,quote", [
    ("变量 `user_id`", "user_id"), ("计算 `left * right`", "left * right"),
    ("泛型 `Box<T>`", "Box<T>"), ("```go\nleft * right\n```", "left * right"),
    ("==重要==：**变量** 保存 `值`。", "重要：变量 保存 值。"),
    ("字面 HTML <b>hello</b>", "<b>hello</b>"),
    ("**调用 `main` 函数**，<u>先运行</u>", "调用 main 函数，先运行"),
])
def test_rendered_markdown_quote_keeps_code_and_literal_characters(markdown, quote):
    from backend.lesson_context import LessonReference, lesson_revision, validate_reference
    bundle = build_starter_lesson(topic="Go", language="go", session_minutes=20, goal_route="foundation_engineer")
    bundle.manifest.pages[0].markdown = markdown
    ref = LessonReference(lesson_id=bundle.manifest.lesson_id,page_id="concept",revision=lesson_revision(bundle.manifest),quote=quote)
    assert validate_reference(bundle,ref)["quote"] == quote


def test_fabricated_markdown_quote_cannot_drop_operator():
    from backend.lesson_context import LessonReference, lesson_revision, validate_reference
    bundle = build_starter_lesson(topic="Go", language="go", session_minutes=20, goal_route="foundation_engineer")
    bundle.manifest.pages[0].markdown = "计算 `left * right`"
    ref = LessonReference(lesson_id=bundle.manifest.lesson_id,page_id="concept",revision=lesson_revision(bundle.manifest),quote="left right")
    with pytest.raises(ValueError,match="quote"):
        validate_reference(bundle,ref)
