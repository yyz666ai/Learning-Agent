"""Validate model-generated supplemental choice questions before persistence."""

from __future__ import annotations

import json
from typing import Any


def _clean_json(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return cleaned


def parse_supplemental_response(raw: str, *, expected_count: int) -> list[dict[str, Any]]:
    try:
        payload = json.loads(_clean_json(raw))
    except json.JSONDecodeError as exc:
        raise ValueError("supplemental practice must be valid JSON") from exc
    questions = payload.get("questions") if isinstance(payload, dict) else None
    if not isinstance(questions, list) or len(questions) != expected_count or not 3 <= len(questions) <= 5:
        raise ValueError("supplemental practice must contain the requested 3 to 5 questions")
    normalized: list[dict[str, Any]] = []
    seen_prompts: set[str] = set()
    for index, question in enumerate(questions, start=1):
        if not isinstance(question, dict):
            raise ValueError(f"question {index} must be an object")
        title = str(question.get("title") or "").strip()
        prompt = str(question.get("prompt") or "").strip()
        explanation = str(question.get("explanation") or "").strip()
        options = question.get("options")
        answer = str(question.get("correct_option_id") or "").strip().casefold()
        if not title or not prompt or not explanation:
            raise ValueError(f"question {index} is missing title, prompt, or explanation")
        canonical = " ".join(prompt.casefold().split())
        if canonical in seen_prompts:
            raise ValueError("duplicate supplemental question prompt")
        seen_prompts.add(canonical)
        if not isinstance(options, list) or not 2 <= len(options) <= 4:
            raise ValueError(f"question {index} must have 2 to 4 options")
        normalized_options = []
        option_ids: set[str] = set()
        for option in options:
            if not isinstance(option, dict):
                raise ValueError(f"question {index} option must be an object")
            option_id = str(option.get("id") or "").strip().casefold()
            label = str(option.get("label") or "").strip()
            if not option_id or not label or option_id in option_ids:
                raise ValueError(f"question {index} contains an invalid option")
            option_ids.add(option_id)
            normalized_options.append({"id": option_id, "label": label[:240]})
        if answer not in option_ids:
            raise ValueError(f"question {index} answer is not present in options")
        normalized.append({
            "title": title[:240],
            "prompt": prompt[:2_000],
            "options": normalized_options,
            "correct_option_id": answer,
            "explanation": explanation[:4_000],
        })
    return normalized
