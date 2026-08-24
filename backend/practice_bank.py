"""Persistent unified classroom-choice and homework practice records."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

try:
    from .lesson_manifest import LessonManifest
except ImportError:  # Support `python backend/main.py`.
    from backend.lesson_manifest import LessonManifest

USER_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
REVIEW_INTERVAL_DAYS = {"forgot": 1, "hard": 3, "easy": 7}


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

    def register_lesson(
        self,
        user_id: str,
        manifest: LessonManifest,
        *,
        answer_keys: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        keys = answer_keys or {}
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
                    "correct_option_id": keys.get(page.id) or previous.get("correct_option_id"),
                    "answer": next(
                        (option.label for option in page.options if option.id.casefold() == str(keys.get(page.id) or "").casefold()),
                        previous.get("answer", ""),
                    ),
                    "explanation": page.completion_criteria or previous.get("explanation", ""),
                    "practice_path": page.practice_path or manifest.practice_path,
                    "status": previous.get("status", "unattempted"),
                    "attempt_count": int(previous.get("attempt_count") or 0),
                    "wrong_count": int(previous.get("wrong_count") or 0),
                    "needs_review": bool(previous.get("needs_review", False)),
                    "attempts": list(previous.get("attempts") or []),
                    "review_history": list(previous.get("review_history") or []),
                    "review_count": int(previous.get("review_count") or 0),
                    "last_reviewed": previous.get("last_reviewed"),
                    "next_review": previous.get("next_review"),
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
        for prompt in manifest.interview_prompts:
            item_id = f"generated-interview:{manifest.lesson_id}:{prompt.id}"
            previous = self._read(self._path(user_id, item_id))
            explanation_parts = ["回答结构：" + "；".join(prompt.answer_structure)]
            if prompt.common_omissions:
                explanation_parts.append("常见遗漏：" + "；".join(prompt.common_omissions))
            if prompt.follow_ups:
                explanation_parts.append("常见追问：" + "；".join(
                    f"{item.prompt}（{'、'.join(item.answer_points)}）" for item in prompt.follow_ups
                ))
            record = {
                **previous,
                "id": item_id,
                "source": "interview",
                "kind": "short_answer",
                "title": prompt.question[:240],
                "normalized_text": prompt.question,
                "prompt": prompt.question,
                "lesson_id": manifest.lesson_id,
                "page_id": "interview-prompts",
                "options": [],
                "answer": prompt.reference_answer,
                "explanation": "\n\n".join(explanation_parts),
                "status": previous.get("status", "unattempted"),
                "attempt_count": int(previous.get("attempt_count") or 0),
                "wrong_count": int(previous.get("wrong_count") or 0),
                "needs_review": bool(previous.get("needs_review", False)),
                "attempts": list(previous.get("attempts") or []),
                "review_history": list(previous.get("review_history") or []),
                "review_count": int(previous.get("review_count") or 0),
                "last_reviewed": previous.get("last_reviewed"),
                "next_review": previous.get("next_review"),
                "created_at": previous.get("created_at") or _now(),
            }
            records.append(self._save(user_id, record))
        return records

    def review_session(
        self,
        user_id: str,
        *,
        today: date | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        selected_today = today or date.today()
        candidates = []
        for item in self.list_items(user_id):
            if not item.get("answer") or item.get("kind") == "homework":
                continue
            next_review = str(item.get("next_review") or "")
            if next_review and next_review > selected_today.isoformat():
                continue
            candidates.append(item)
        candidates.sort(key=lambda item: (
            0 if item.get("needs_review") else 1,
            str(item.get("next_review") or "0000-00-00"),
            -int(item.get("wrong_count") or 0),
            str(item.get("created_at") or ""),
        ))
        cards = []
        for item in candidates[:max(1, min(limit, 20))]:
            cards.append({
                key: value for key, value in item.items()
                if key not in {"answer", "correct_option_id", "explanation", "review_history"}
            })
        return {"cards": cards, "total": len(cards), "due_count": len(candidates)}

    def reveal_review_item(self, user_id: str, item_id: str) -> dict[str, Any]:
        item = self._read(self._path(user_id, item_id))
        if not item or not item.get("answer"):
            raise KeyError(item_id)
        attempts = list(item.get("attempts") or [])
        last_wrong = next((attempt for attempt in reversed(attempts) if not attempt.get("correct")), None)
        return {
            "id": item_id,
            "answer": item.get("answer"),
            "correct_option_id": item.get("correct_option_id"),
            "explanation": item.get("explanation") or "",
            "last_wrong": last_wrong,
        }

    def rate_review_item(
        self,
        user_id: str,
        *,
        item_id: str,
        rating: str,
        today: date | None = None,
    ) -> dict[str, Any]:
        if rating not in REVIEW_INTERVAL_DAYS:
            raise ValueError("invalid rating")
        item = self._read(self._path(user_id, item_id))
        if not item or not item.get("answer"):
            raise KeyError(item_id)
        selected_today = today or date.today()
        interval = REVIEW_INTERVAL_DAYS[rating]
        history = list(item.get("review_history") or [])
        next_review = (selected_today + timedelta(days=interval)).isoformat()
        history.append({
            "rating": rating,
            "reviewed_at": selected_today.isoformat(),
            "interval_days": interval,
            "next_review": next_review,
        })
        item.update({
            "review_history": history,
            "review_count": len(history),
            "last_reviewed": selected_today.isoformat(),
            "next_review": next_review,
            "last_review_rating": rating,
            "needs_review": rating != "easy",
        })
        return self._save(user_id, item)

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

    def add_supplemental_questions(
        self,
        user_id: str,
        *,
        topic: str,
        questions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        added_ids: list[str] = []
        duplicate_ids: list[str] = []
        for question in questions:
            canonical = " ".join(str(question["prompt"]).casefold().split())
            item_id = "supplemental:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]
            path = self._path(user_id, item_id)
            if self._read(path):
                duplicate_ids.append(item_id)
                continue
            options = list(question["options"])
            correct_option_id = str(question["correct_option_id"])
            answer = next(
                option["label"] for option in options if option["id"] == correct_option_id
            )
            record = {
                "id": item_id,
                "source": "supplemental",
                "kind": "choice",
                "topic": topic[:240],
                "title": str(question["title"])[:240],
                "normalized_text": str(question["prompt"])[:2_000],
                "prompt": str(question["prompt"])[:2_000],
                "options": options,
                "correct_option_id": correct_option_id,
                "answer": answer,
                "explanation": str(question["explanation"])[:4_000],
                "status": "unattempted",
                "attempt_count": 0,
                "wrong_count": 0,
                "needs_review": False,
                "attempts": [],
                "review_history": [],
                "review_count": 0,
                "last_reviewed": None,
                "next_review": None,
                "created_at": _now(),
            }
            self._save(user_id, record)
            added_ids.append(item_id)
        return {
            "added_count": len(added_ids),
            "duplicate_count": len(duplicate_ids),
            "item_ids": added_ids,
        }

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
