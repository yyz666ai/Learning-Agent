from __future__ import annotations

import time

from backend.generation_jobs import GenerationJobRegistry


def test_background_job_returns_immediately_and_keeps_result() -> None:
    registry = GenerationJobRegistry(max_workers=1)

    started = time.monotonic()
    accepted = registry.start("learner", "a" * 32, lambda: {"personalized": True})
    elapsed = time.monotonic() - started

    assert accepted["status"] in {"queued", "running", "completed"}
    assert elapsed < 0.2

    deadline = time.monotonic() + 2
    status = registry.get("learner", "a" * 32)
    while status["status"] not in {"completed", "failed"} and time.monotonic() < deadline:
        time.sleep(0.01)
        status = registry.get("learner", "a" * 32)

    assert status == {
        "user_id": "learner",
        "generation_id": "a" * 32,
        "status": "completed",
        "result": {"personalized": True},
    }


def test_background_job_preserves_retryable_failure_result() -> None:
    registry = GenerationJobRegistry(max_workers=1)
    registry.start(
        "learner",
        "b" * 32,
        lambda: {"personalized": False, "reason": "validation_failed"},
    )

    deadline = time.monotonic() + 2
    status = registry.get("learner", "b" * 32)
    while status["status"] not in {"completed", "failed"} and time.monotonic() < deadline:
        time.sleep(0.01)
        status = registry.get("learner", "b" * 32)

    assert status["status"] == "failed"
    assert status["result"]["reason"] == "validation_failed"


def test_background_job_supports_lesson_result_envelopes() -> None:
    registry = GenerationJobRegistry(max_workers=1)
    registry.start("learner", "c" * 32, lambda: {"ok": True, "lesson": {"pages": [1]}})
    registry.start("learner", "d" * 32, lambda: {"ok": False, "detail": {"message": "retry"}})

    deadline = time.monotonic() + 2
    completed = registry.get("learner", "c" * 32)
    failed = registry.get("learner", "d" * 32)
    while (
        (completed["status"] not in {"completed", "failed"} or failed["status"] not in {"completed", "failed"})
        and time.monotonic() < deadline
    ):
        time.sleep(0.01)
        completed = registry.get("learner", "c" * 32)
        failed = registry.get("learner", "d" * 32)

    assert completed["status"] == "completed"
    assert completed["result"]["lesson"]["pages"] == [1]
    assert failed["status"] == "failed"
    assert failed["result"]["detail"]["message"] == "retry"
