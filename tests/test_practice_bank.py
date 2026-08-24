from __future__ import annotations

import subprocess
import sys
import shutil
from datetime import date
from pathlib import Path

import pytest

from backend.lesson_manifest import InterviewPrompt, LessonManifest, build_starter_lesson
from backend import practice_bank
from backend.practice_bank import PracticeBankStore


def lesson_bundle():
    return build_starter_lesson(
        topic="Go 语言", language="go", session_minutes=25, goal_route="project_delivery",
    )


def test_register_lesson_collects_choices_and_homework_without_duplicates(tmp_path) -> None:
    store = PracticeBankStore(tmp_path)
    bundle = lesson_bundle()

    first = store.register_lesson("learner", bundle.manifest)
    second = store.register_lesson("learner", bundle.manifest)

    assert len(first) == 2
    assert len(second) == 2
    assert {item["source"] for item in second} == {"classroom", "homework"}
    choice = next(item for item in second if item["kind"] == "choice")
    homework = next(item for item in second if item["kind"] == "homework")
    assert choice["status"] == "unattempted"
    assert choice["prompt"]
    assert len(choice["options"]) == 3
    assert homework["practice_path"]
    assert homework["status"] == "pending"


def test_register_lesson_rolls_back_every_item_after_a_partial_write(
    tmp_path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = PracticeBankStore(tmp_path)
    bundle = lesson_bundle()
    original_save = store._save
    calls = 0

    def fail_after_first(user_id: str, record: dict[str, object]):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("disk full")
        return original_save(user_id, record)

    monkeypatch.setattr(store, "_save", fail_after_first)
    with pytest.raises(OSError, match="disk full"):
        store.register_lesson("learner", bundle.manifest, answer_keys=bundle.answer_keys)

    assert store.list_items("learner") == []


def test_register_lesson_preserves_backup_when_rollback_copy_fails(
    tmp_path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = PracticeBankStore(tmp_path)
    bundle = lesson_bundle()
    store.register_lesson("learner", bundle.manifest, answer_keys=bundle.answer_keys)
    original_copytree = shutil.copytree
    calls = 0

    def fail_restore(source, target, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("restore failed")
        return original_copytree(source, target, *args, **kwargs)

    monkeypatch.setattr(practice_bank.shutil, "copytree", fail_restore)
    monkeypatch.setattr(store, "_save", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("write failed")))
    with pytest.raises(RuntimeError, match="recovery backup preserved") as failure:
        store.register_lesson("learner", bundle.manifest, answer_keys=bundle.answer_keys)

    backup = str(failure.value).split(" at ", 1)[1]
    assert Path(backup).is_dir()
    shutil.rmtree(Path(backup).parent)


def test_choice_attempts_preserve_wrong_history_after_correct_retry(tmp_path) -> None:
    store = PracticeBankStore(tmp_path)
    bundle = lesson_bundle()
    store.register_lesson("learner", bundle.manifest)

    wrong = store.record_choice_attempt(
        "learner", lesson_id=bundle.manifest.lesson_id, page_id="check-label",
        selected_option_id="a", correct=False,
    )
    correct = store.record_choice_attempt(
        "learner", lesson_id=bundle.manifest.lesson_id, page_id="check-label",
        selected_option_id="b", correct=True,
    )

    assert wrong["status"] == "incorrect"
    assert wrong["needs_review"] is True
    assert correct["status"] == "mastered"
    assert correct["attempt_count"] == 2
    assert correct["wrong_count"] == 1
    assert correct["needs_review"] is False
    assert len(correct["attempts"]) == 2


def test_bank_summary_counts_all_registered_items_and_mastery(tmp_path) -> None:
    store = PracticeBankStore(tmp_path)
    bundle = lesson_bundle()
    store.register_lesson("learner", bundle.manifest)
    store.record_choice_attempt(
        "learner", lesson_id=bundle.manifest.lesson_id, page_id="check-label",
        selected_option_id="b", correct=True,
    )

    bank = store.read_bank("learner")

    assert bank["coverage"] == {"mastered": 1, "total": 2, "percent": 50}
    assert len(bank["questions"]) == 2


def test_practice_bank_can_load_when_server_runs_main_as_a_script() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import sys; sys.path.insert(0, 'backend'); import practice_bank"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr


def test_review_session_prioritizes_due_wrong_questions_and_hides_answer(tmp_path) -> None:
    store = PracticeBankStore(tmp_path)
    bundle = lesson_bundle()
    store.register_lesson("learner", bundle.manifest, answer_keys=bundle.answer_keys)
    store.record_choice_attempt(
        "learner", lesson_id=bundle.manifest.lesson_id, page_id="check-label",
        selected_option_id="a", correct=False,
    )

    session = store.review_session("learner", today=date(2026, 8, 24), limit=5)

    assert session["total"] == 1
    card = session["cards"][0]
    assert card["needs_review"] is True
    assert card["prompt"]
    assert "answer" not in card
    assert "correct_option_id" not in card


def test_reveal_and_rate_review_item_persist_answer_and_interval(tmp_path) -> None:
    store = PracticeBankStore(tmp_path)
    bundle = lesson_bundle()
    store.register_lesson("learner", bundle.manifest, answer_keys=bundle.answer_keys)
    item_id = f"lesson:{bundle.manifest.lesson_id}:check-label"

    revealed = store.reveal_review_item("learner", item_id)
    rated = store.rate_review_item(
        "learner", item_id=item_id, rating="hard", today=date(2026, 8, 24),
    )

    assert revealed["answer"] == "name"
    assert revealed["correct_option_id"] == "b"
    assert rated["last_reviewed"] == "2026-08-24"
    assert rated["next_review"] == "2026-08-27"
    assert rated["review_count"] == 1
    assert rated["review_history"][0]["rating"] == "hard"


def test_supplemental_questions_are_deduplicated_and_reviewable(tmp_path) -> None:
    store = PracticeBankStore(tmp_path)
    questions = [{
        "title": "变量赋值判断",
        "prompt": "执行 x := 1 后，x 保存什么？",
        "options": [{"id": "a", "label": "整数 1"}, {"id": "b", "label": "字符串 1"}],
        "correct_option_id": "a",
        "explanation": ":= 会根据右侧值推断为整数。",
    }]

    first = store.add_supplemental_questions("learner", topic="Go", questions=questions)
    second = store.add_supplemental_questions("learner", topic="Go", questions=questions)
    bank = store.read_bank("learner")

    assert first["added_count"] == 1
    assert second["duplicate_count"] == 1
    item = bank["questions"][0]
    assert item["source"] == "supplemental"
    assert item["answer"] == "整数 1"
    assert store.review_session("learner")["total"] == 1


def test_generated_interview_prompts_are_saved_with_answers(tmp_path) -> None:
    store = PracticeBankStore(tmp_path)
    bundle = lesson_bundle()
    prompt = InterviewPrompt(
        id="goroutine-leak", question="什么是 goroutine 泄漏？",
        reference_answer="goroutine 因永久等待而无法退出，并持续占用资源。",
        answer_structure=["定义", "常见原因", "排查方式"],
        common_omissions=["只说内存，不说生命周期"], follow_ups=[],
    )
    manifest = LessonManifest.model_validate({
        **bundle.manifest.model_dump(), "route": "interview_sprint", "interview_prompts": [prompt.model_dump()],
    })

    store.register_lesson("learner", manifest, answer_keys=bundle.answer_keys)
    interview = next(item for item in store.list_items("learner") if item["source"] == "interview")

    assert interview["kind"] == "short_answer"
    assert interview["answer"].startswith("goroutine")
    assert "常见原因" in interview["explanation"]
    assert store.review_session("learner")["total"] == 2
