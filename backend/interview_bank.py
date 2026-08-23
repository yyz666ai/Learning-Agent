"""Persistent, deterministic interview-question ingestion and mastery records."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

USER_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
STUDY_MODES = {"from_scratch", "systematic", "assess_first"}
MASTERY_VALUES = {"unrated", "forgot", "hard", "smooth"}


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


def _read_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def split_questions(raw_text: str) -> list[str]:
    """Split common pasted/voice-transcribed lists without rewriting their meaning."""
    text = raw_text.replace("\r\n", "\n").strip()
    if not text:
        return []
    numbered = re.split(r"(?:^|\n)\s*(?:\d{1,3}[.)、]|[-*•])\s*", text)
    parts = [part.strip() for part in numbered if part.strip()]
    if len(parts) <= 1:
        parts = [part.strip() for part in text.splitlines() if part.strip()]
    if len(parts) <= 1 and text.count("？") + text.count("?") > 1:
        parts = [part.strip() + mark for part, mark in re.findall(r"([^？?]+)([？?])", text)]
    return [part for part in parts if len(part) >= 2]


def normalize_question(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.strip())
    normalized = re.sub(r"^[\d\s.)、*•-]+", "", normalized)
    normalized = re.sub(r"[？?。.!！]+$", "", normalized)
    return normalized.strip()


def question_id(text: str) -> str:
    canonical = normalize_question(text).casefold()
    return "iq_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _concepts(text: str) -> list[str]:
    vocabulary = {
        "闭包": "closure", "goroutine": "goroutine", "线程": "threading",
        "react": "react", "vue": "vue", "http": "http", "api": "api",
        "数据库": "database", "索引": "database-index", "缓存": "cache",
        "算法": "algorithm", "网络": "network", "并发": "concurrency",
    }
    lowered = text.casefold()
    found = [concept for token, concept in vocabulary.items() if token.casefold() in lowered]
    return found or ["interview-general"]


class InterviewBankStore:
    def __init__(self, server_root: Path) -> None:
        self.server_root = Path(server_root)

    def _root(self, user_id: str) -> Path:
        if not USER_ID.fullmatch(user_id):
            raise ValueError("invalid user_id")
        return self.server_root / "userdir" / f"u_{user_id}" / "interview-bank"

    def _bank_path(self, user_id: str) -> Path:
        return self._root(user_id) / "bank.json"

    def read_bank(self, user_id: str) -> dict[str, Any]:
        value = _read_json(
            self._bank_path(user_id),
            {"schema_version": 1, "study_mode": None, "question_ids": [], "updated_at": None},
        )
        return value if isinstance(value, dict) else {"schema_version": 1, "study_mode": None, "question_ids": []}

    def intake(
        self,
        user_id: str,
        raw_text: str,
        *,
        source: str = "chat",
        split_input: bool = True,
    ) -> dict[str, Any]:
        questions = split_questions(raw_text) if split_input else [raw_text.strip()]
        if not questions:
            raise ValueError("没有识别到可入库的面试题")
        root = self._root(user_id)
        bank = self.read_bank(user_id)
        known = set(bank.get("question_ids") or [])
        new_count = 0
        ids: list[str] = []
        batch_id = "batch_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "_" + uuid4().hex[:8]
        received_at = _now()
        for raw_question in questions:
            normalized = normalize_question(raw_question)
            identifier = question_id(normalized)
            ids.append(identifier)
            path = root / "questions" / f"{identifier}.json"
            record = _read_json(path, {})
            if not isinstance(record, dict) or not record:
                new_count += 1
                record = {
                    "id": identifier,
                    "normalized_text": normalized,
                    "raw_variants": [],
                    "role": "unspecified",
                    "domains": [],
                    "concept_ids": _concepts(normalized),
                    "difficulty": "unknown",
                    "origin": "collected",
                    "answer_status": "missing",
                    "answer_markdown": "",
                    "rubric": [],
                    "related_question_ids": [],
                    "mastery": "unrated",
                    "evidence": [],
                    "next_review": None,
                    "plan_node_id": None,
                    "created_at": received_at,
                }
            variants = record.setdefault("raw_variants", [])
            if raw_question not in variants:
                variants.append(raw_question)
            record["updated_at"] = received_at
            _atomic_json(path, record)
            if identifier not in known:
                bank.setdefault("question_ids", []).append(identifier)
                known.add(identifier)
        _atomic_json(root / "sources" / f"{batch_id}.json", {
            "batch_id": batch_id, "source": source, "received_at": received_at,
            "raw_text": raw_text, "question_ids": ids,
        })
        bank.update({"schema_version": 1, "updated_at": received_at})
        _atomic_json(self._bank_path(user_id), bank)
        return {
            "batch_id": batch_id, "source_count": len(questions), "new_count": new_count,
            "duplicate_count": len(questions) - new_count, "question_ids": ids,
        }

    def list_questions(self, user_id: str) -> list[dict[str, Any]]:
        root = self._root(user_id)
        return [
            record for identifier in self.read_bank(user_id).get("question_ids", [])
            if isinstance((record := _read_json(root / "questions" / f"{identifier}.json", None)), dict)
        ]

    def list_sources(self, user_id: str) -> list[dict[str, Any]]:
        root = self._root(user_id) / "sources"
        if not root.exists():
            return []
        return [value for path in sorted(root.glob("*.json")) if isinstance((value := _read_json(path, None)), dict)]

    def get_question(self, user_id: str, identifier: str) -> dict[str, Any]:
        if not re.fullmatch(r"iq_[a-f0-9]{16}", identifier):
            raise KeyError(identifier)
        value = _read_json(self._root(user_id) / "questions" / f"{identifier}.json", None)
        if not isinstance(value, dict):
            raise KeyError(identifier)
        return value

    def save_question(self, user_id: str, question: dict[str, Any]) -> dict[str, Any]:
        identifier = str(question.get("id") or "")
        self.get_question(user_id, identifier)
        question["updated_at"] = _now()
        _atomic_json(self._root(user_id) / "questions" / f"{identifier}.json", question)
        return question

    def set_study_mode(self, user_id: str, mode: str) -> dict[str, Any]:
        if mode not in STUDY_MODES:
            raise ValueError("invalid study mode")
        bank = self.read_bank(user_id)
        bank.update({"study_mode": mode, "updated_at": _now()})
        _atomic_json(self._bank_path(user_id), bank)
        return bank

    def record_mastery(self, user_id: str, identifier: str, mastery: str) -> dict[str, Any]:
        if mastery not in MASTERY_VALUES - {"unrated"}:
            raise ValueError("invalid mastery")
        question = self.get_question(user_id, identifier)
        interval = {"forgot": 1, "hard": 3, "smooth": 7}[mastery]
        question["mastery"] = mastery
        question["next_review"] = (datetime.now(UTC) + timedelta(days=interval)).date().isoformat()
        question.setdefault("evidence", []).append({"kind": "self_rating", "value": mastery, "at": _now()})
        return self.save_question(user_id, question)

    def add_expanded_questions(self, user_id: str, questions: list[str]) -> list[str]:
        identifiers: list[str] = []
        for text in questions:
            result = self.intake(user_id, text, source="model_expansion", split_input=False)
            identifier = result["question_ids"][0]
            record = self.get_question(user_id, identifier)
            if record.get("origin") != "collected":
                record["origin"] = "expanded"
            elif result["new_count"]:
                record["origin"] = "expanded"
            if result["new_count"]:
                record["answer_status"] = "draft"
            self.save_question(user_id, record)
            identifiers.append(identifier)
        return identifiers
