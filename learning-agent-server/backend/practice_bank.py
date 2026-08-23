"""Persistent unified classroom-choice and homework practice records."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from .lesson_manifest import LessonManifest
except ImportError:  # Support `python backend/main.py`.
    from backend.lesson_manifest import LessonManifest

USER_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as temporary:
            json.dump(payload, temporary, ensure_ascii=False, indent=2)
            temporary.write("\n")
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


class PracticeBankStore:
    def __init__(self, server_root: Path) -> None:
        self.server_root = Path(server_root)

    def _root(self, user_id: str) -> Path:
        if not USER_ID.fullmatch(user_id):
            raise ValueError("invalid user_id")
        return self.server_root / "userdir" / f"u_{user_id}" / "practice-bank" / "items"

    def _path(self, user_id: str, item_id: str) -> Path:
        digest = hashlib.sha256(item_id.encode("utf-8")).hexdigest()[:24]
        return self._root(user_id) / f"{digest}.json"

    def _read(self, path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}

    def _save(self, user_id: str, record: dict[str, Any]) -> dict[str, Any]:
        record["updated_at"] = _now()
        _atomic_json(self._path(user_id, str(record["id"])), record)
        return record

    def register_lesson(self, user_id: str, manifest: LessonManifest) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for page in manifest.pages:
            if page.question and page.options:
                item_id = f"lesson:{manifest.lesson_id}:{page.id}"
                previous = self._read(self._path(user_id, item_id))
                record = {
                    **previous,
                    "id": item_id,
                    "source": "classroom",
                    "kind": "choice",
                    "title": page.title,
                    "normalized_text": page.question,
                    "prompt": page.question,
                    "lesson_id": manifest.lesson_id,
                    "page_id": page.id,
                    "options": [option.model_dump() for option in page.options],
                    "practice_path": page.practice_path or manifest.practice_path,
                    "status": previous.get("status", "unattempted"),
                    "attempt_count": int(previous.get("attempt_count") or 0),
                    "wrong_count": int(previous.get("wrong_count") or 0),
                    "needs_review": bool(previous.get("needs_review", False)),
                    "attempts": list(previous.get("attempts") or []),
                    "created_at": previous.get("created_at") or _now(),
                }
                records.append(self._save(user_id, record))
            if page.practice_kind == "homework" or page.type == "practice":
                item_id = f"homework:{manifest.lesson_id}:{page.id}"
                previous = self._read(self._path(user_id, item_id))
                record = {
                    **previous,
                    "id": item_id,
                    "source": "homework",
                    "kind": "homework",
                    "title": page.title,
                    "normalized_text": page.markdown or page.title,
                    "prompt": page.markdown or manifest.completion_prompt,
                    "lesson_id": manifest.lesson_id,
                    "page_id": page.id,
                    "options": [],
                    "practice_path": page.practice_path or manifest.practice_path,
                    "status": previous.get("status", "pending"),
                    "attempt_count": int(previous.get("attempt_count") or 0),
                    "wrong_count": int(previous.get("wrong_count") or 0),
                    "needs_review": bool(previous.get("needs_review", False)),
                    "attempts": list(previous.get("attempts") or []),
                    "created_at": previous.get("created_at") or _now(),
                }
                records.append(self._save(user_id, record))
        return records

    def record_choice_attempt(
        self,
        user_id: str,
        *,
        lesson_id: str,
        page_id: str,
        selected_option_id: str,
        correct: bool,
    ) -> dict[str, Any]:
        item_id = f"lesson:{lesson_id}:{page_id}"
        path = self._path(user_id, item_id)
        record = self._read(path)
        if not record:
            raise KeyError(item_id)
        attempts = list(record.get("attempts") or [])
        attempts.append({"selected_option_id": selected_option_id, "correct": bool(correct), "at": _now()})
        record.update({
            "attempts": attempts,
            "attempt_count": len(attempts),
            "wrong_count": int(record.get("wrong_count") or 0) + (0 if correct else 1),
            "last_result": "correct" if correct else "incorrect",
            "status": "mastered" if correct else "incorrect",
            "needs_review": not correct,
        })
        return self._save(user_id, record)

    def list_items(self, user_id: str) -> list[dict[str, Any]]:
        root = self._root(user_id)
        if not root.exists():
            return []
        records = [self._read(path) for path in sorted(root.glob("*.json"))]
        return sorted((item for item in records if item), key=lambda item: str(item.get("created_at") or ""))

    def read_bank(self, user_id: str) -> dict[str, Any]:
        questions = self.list_items(user_id)
        mastered = sum(item.get("status") == "mastered" for item in questions)
        total = len(questions)
        return {
            "questions": questions,
            "coverage": {"mastered": mastered, "total": total, "percent": round(mastered * 100 / total) if total else 0},
        }
