from __future__ import annotations

import subprocess
import sys

from backend.lesson_manifest import build_starter_lesson
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
