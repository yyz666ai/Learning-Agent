"""Opt-in, allowlisted local diagnostics. Never export learner content or keys."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import platform
from pathlib import Path

from .generation_transaction import project_lock
from .lesson_review import LessonCoverageError, LessonReviewUnavailable
from .user_memory import _atomic_json, _user_dir

logger = logging.getLogger(__name__)
_RULES = {
    "at least two relevant pages": "scope_relevant_pages",
    "drifted away from a covered": "scope_missing_terms",
    "scope evidence": "scope_citations",
}
_CATEGORIES = {"none", "validation", "provider", "content_review", "review_unavailable"}
_RULE_CODES = {"none", "structure", "provider", "semantic_coverage", "semantic_review_unavailable", *_RULES.values()}


def _read_records(path: Path) -> dict:
    try:
        if path.stat().st_size > 16_384:
            return {}
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return {}
    except (OSError, ValueError):
        return {}
    records = {}
    for operation in ("lesson", "plan"):
        item = raw.get(operation)
        if not isinstance(item, dict):
            continue
        # Project directories are editable by their owner. Re-allowlist on
        # download rather than assuming previously written records are safe.
        if (not isinstance(item.get("status"), str) or item["status"] not in {"succeeded", "failed"}
                or not isinstance(item.get("category"), str) or item["category"] not in _CATEGORIES
                or not isinstance(item.get("rule"), str) or item["rule"] not in _RULE_CODES):
            continue
        try:
            at = datetime.fromisoformat(item["at"]).astimezone(timezone.utc).isoformat()
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        records[operation] = {"status": item["status"], "category": item["category"], "rule": item["rule"], "at": at}
    return records


def record_generation(root: Path, user_id: str, operation: str, *, error: Exception | None = None) -> None:
    """Best-effort metadata; diagnostics must not turn success into a failure."""
    if operation not in {"lesson", "plan"}:
        raise ValueError("invalid diagnostic operation")
    path = _user_dir(root, user_id) / "diagnostics/generation.json"
    category = "none" if error is None else "validation" if isinstance(error, (ValueError, TypeError)) else "provider"
    rule = "none" if error is None else "structure" if category == "validation" else "provider"
    if category == "validation":
        rule = next((code for pattern, code in _RULES.items() if pattern in str(error)), rule)
    if isinstance(error, LessonCoverageError):
        category, rule = "content_review", "semantic_coverage"
    elif isinstance(error, LessonReviewUnavailable):
        category, rule = "review_unavailable", "semantic_review_unavailable"
    try:
        with project_lock(root, user_id):
            records = _read_records(path)
            records[operation] = {"status": "succeeded" if error is None else "failed", "category": category,
                                  "rule": rule, "at": datetime.now(timezone.utc).isoformat()}
            _atomic_json(path, records)
    except OSError:
        logger.warning("Could not persist optional generation diagnostics")


def build_report(root: Path, user_id: str) -> dict:
    path = _user_dir(root, user_id) / "diagnostics/generation.json"
    return {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "runtime": {"os": platform.system(), "python": platform.python_version()},
        "generation": _read_records(path),
        "privacy": {"includes_conversation": False, "includes_credentials": False, "includes_paths": False},
        "scope": "Latest recorded plan/lesson outcomes since diagnostics were enabled; not a full log archive.",
    }
