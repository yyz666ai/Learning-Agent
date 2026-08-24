"""Validate model-generated supplemental choice questions before persistence."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .lesson_manifest import LessonBundle, LessonOption, LessonPage


def _clean_json(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return cleaned


def _extract_json_object(raw: str) -> dict[str, Any]:
    cleaned = _clean_json(raw)
    try:
        payload = json.loads(cleaned)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", cleaned):
        try:
            candidate, _ = decoder.raw_decode(cleaned, match.start())
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict) and "questions" in candidate:
            return candidate
    raise ValueError("supplemental practice must be valid JSON")


def parse_supplemental_response(raw: str, *, expected_count: int) -> list[dict[str, Any]]:
    payload = _extract_json_object(raw)
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
            label = str(option.get("label") or option.get("text") or "").strip()
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


def append_supplemental_questions(
    bundle: LessonBundle,
    questions: list[dict[str, Any]],
) -> LessonBundle:
    """Append validated clickable questions before the lesson's closing page."""
    existing_ids = {page.id for page in bundle.manifest.pages}
    existing_prompts = {
        " ".join((page.question or "").casefold().split())
        for page in bundle.manifest.pages if page.question
    }
    added_pages: list[LessonPage] = []
    added_answers: dict[str, str] = {}
    for question in questions:
        canonical = " ".join(str(question["prompt"]).casefold().split())
        if canonical in existing_prompts:
            continue
        existing_prompts.add(canonical)
        digest = hashlib.sha256(str(question["prompt"]).encode("utf-8")).hexdigest()[:16]
        base_id = f"supplemental-{digest}"
        page_id = base_id
        suffix = 2
        while page_id in existing_ids:
            page_id = f"{base_id}-{suffix}"
            suffix += 1
        existing_ids.add(page_id)
        added_pages.append(LessonPage(
            id=page_id,
            type="check",
            eyebrow="追加练习",
            title=str(question["title"]),
            markdown="先自己判断，再点击最合适的答案。答完后可以在右侧对话框继续追问。",
            question=str(question["prompt"]),
            options=[LessonOption.model_validate(option) for option in question["options"]],
            completion_criteria="完成后可在题库查看解析，并按掌握情况安排复习。",
        ))
        added_answers[page_id] = str(question["correct_option_id"])

    pages = list(bundle.manifest.pages)
    insert_at = next((index for index, page in enumerate(pages) if page.type == "mastery"), len(pages))
    pages[insert_at:insert_at] = added_pages
    if len(pages) > 24:
        raise ValueError("current lesson does not have room for more practice pages")
    progress = bundle.manifest.progress.model_copy(update={
        "total_pages": len(pages),
        "remaining_minutes": min(240, bundle.manifest.progress.remaining_minutes + len(added_pages)),
    })
    manifest = bundle.manifest.model_copy(update={"pages": pages, "progress": progress})
    return LessonBundle(manifest=manifest, answer_keys={**bundle.answer_keys, **added_answers})
