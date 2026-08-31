"""Short HTTP handles for long-running model generation work."""

from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from .localization import current_locale, submit_localized


class GenerationJobRegistry:
    """Keep long model calls alive while clients poll with short requests."""

    def __init__(self, *, max_workers: int = 2) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="learning-generation",
        )
        self._lock = threading.Lock()
        self._jobs: dict[tuple[str, str], dict[str, Any]] = {}

    def start(
        self,
        user_id: str,
        generation_id: str,
        work: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]:
        key = (user_id, generation_id)
        with self._lock:
            existing = self._jobs.get(key)
            if existing is not None:
                return dict(existing)
            job = {
                "user_id": user_id,
                "generation_id": generation_id,
                "status": "queued",
                "locale": current_locale(),
                "result": None,
            }
            self._jobs[key] = job
        submit_localized(self._executor, self._run, key, work)
        return self.get(user_id, generation_id)

    def _run(self, key: tuple[str, str], work: Callable[[], dict[str, Any]]) -> None:
        with self._lock:
            self._jobs[key]["status"] = "running"
        try:
            result = work()
        except Exception as exc:  # the polling API must remain available
            result = {
                "personalized": False,
                "reason": "background_generation_failed",
                "error_type": type(exc).__name__,
                "user_message": "课程生成暂时中断，你的目标和选择都已保留，请直接重试。",
            }
        with self._lock:
            job = self._jobs[key]
            job["result"] = result
            failed = result.get("personalized") is False or result.get("ok") is False
            job["status"] = "failed" if failed else "completed"

    def get(self, user_id: str, generation_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get((user_id, generation_id))
            if job is None:
                raise KeyError(generation_id)
            return dict(job)
