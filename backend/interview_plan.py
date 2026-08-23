"""Reconcile a growing interview bank without erasing earned progress."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def reconcile_interview_plan(plan: dict[str, Any], questions: list[dict[str, Any]]) -> dict[str, Any]:
    result = deepcopy(plan)
    floor = max(int(result.get("progress_floor") or 0), int(result.get("display_progress") or 0))
    result["progress_floor"] = floor
    result["display_progress"] = max(floor, int(result.get("display_progress") or 0))
    existing = {
        item.get("question_id") for item in result.get("interview_backlog", []) if isinstance(item, dict)
    }
    backlog = list(result.get("interview_backlog", []))
    for question in questions:
        identifier = question.get("id")
        if identifier and identifier not in existing:
            backlog.append({
                "question_id": identifier,
                "concept_ids": list(question.get("concept_ids") or []),
                "status": "mastered" if question.get("mastery") == "smooth" else "pending",
            })
            existing.add(identifier)
    mastered = sum(question.get("mastery") == "smooth" for question in questions)
    total = len(questions)
    result["interview_backlog"] = backlog
    result["bank_coverage"] = {
        "mastered": mastered,
        "total": total,
        "percent": round(mastered / total * 100) if total else 0,
    }
    return result
