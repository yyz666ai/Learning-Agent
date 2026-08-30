"""Validate model-generated supplemental practice before persistence."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import PurePosixPath
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


def _required_text(value: Any, name: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{name} must be non-empty text of at most {limit} characters")
    return value.strip()


def _text_list(value: Any, name: str, minimum: int) -> list[str]:
    if not isinstance(value, list) or not minimum <= len(value) <= 8:
        raise ValueError(f"{name} must contain {minimum} to 8 text entries")
    return [_required_text(item, name, 1_000) for item in value]


def parse_supplemental_response(raw: str, *, expected_count: int | None) -> list[dict[str, Any]]:
    if expected_count is not None and (type(expected_count) is not int or not 1 <= expected_count <= 5):
        raise ValueError("supplemental practice count must be 1 to 5")
    payload = _extract_json_object(raw)
    questions = payload.get("questions") if isinstance(payload, dict) else None
    if not isinstance(questions, list) or not 1 <= len(questions) <= 5 or (expected_count is not None and len(questions) != expected_count):
        raise ValueError("supplemental practice must contain the requested 1 to 5 questions")
    normalized: list[dict[str, Any]] = []
    seen_prompts: set[str] = set()
    for index, question in enumerate(questions, start=1):
        if not isinstance(question, dict):
            raise ValueError(f"question {index} must be an object")
        title = _required_text(question.get("title"), f"question {index} title", 240)
        prompt = _required_text(question.get("prompt"), f"question {index} prompt", 2_000)
        kind = question.get("kind", "choice")
        if not isinstance(kind, str) or kind not in {"choice", "programming", "project"}:
            raise ValueError(f"question {index} has an invalid kind")
        if any(key in question for key in ("practice_path", "path", "filename", "directory")):
            raise ValueError(f"question {index} must not supply a practice path")
        canonical = " ".join(prompt.casefold().split())
        if canonical in seen_prompts:
            raise ValueError("duplicate supplemental question prompt")
        seen_prompts.add(canonical)
        if kind != "choice":
            if any(key in question for key in ("options", "correct_option_id", "answer", "code", "solution", "reference_answer")):
                raise ValueError(f"question {index} programming practice must not supply options or answers")
            criteria = _required_text(question.get("completion_criteria"), f"question {index} completion_criteria", 1_000)
            milestones = _text_list(question.get("milestones", []), f"question {index} milestones", 2 if kind == "project" else 0)
            hints = _text_list(question.get("hints"), f"question {index} hints", 1)
            normalized.append({
                "kind": kind, "title": title, "prompt": prompt,
                "milestones": milestones, "hints": hints, "completion_criteria": criteria,
                "options": [], "correct_option_id": "", "explanation": criteria,
            })
            continue
        explanation = _required_text(question.get("explanation"), f"question {index} explanation", 4_000)
        options = question.get("options")
        answer = _required_text(question.get("correct_option_id"), f"question {index} answer", 32).casefold()
        if not isinstance(options, list) or not 2 <= len(options) <= 4:
            raise ValueError(f"question {index} must have 2 to 4 options")
        normalized_options = []
        option_ids: set[str] = set()
        for option in options:
            if not isinstance(option, dict):
                raise ValueError(f"question {index} option must be an object")
            option_id = _required_text(option.get("id"), f"question {index} option id", 32).casefold()
            label = _required_text(option.get("label") or option.get("text"), f"question {index} option label", 240)
            if not option_id or not label or option_id in option_ids:
                raise ValueError(f"question {index} contains an invalid option")
            option_ids.add(option_id)
            normalized_options.append({"id": option_id, "label": label})
        if answer not in option_ids:
            raise ValueError(f"question {index} answer is not present in options")
        normalized.append({
            "kind": kind,
            "title": title,
            "prompt": prompt,
            "options": normalized_options,
            "correct_option_id": answer,
            "explanation": explanation,
        })
    return normalized


def append_supplemental_questions(
    bundle: LessonBundle,
    questions: list[dict[str, Any]],
) -> LessonBundle:
    """Append validated choice/homework questions before the closing page."""
    existing_ids = {page.id for page in bundle.manifest.pages}
    existing_paths = {page.practice_path for page in bundle.manifest.pages if page.practice_path}
    existing_prompts = {
        " ".join(text.casefold().split())
        for page in bundle.manifest.pages
        for text in [page.question, page.markdown if page.type == "practice" else None]
        if text
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
        is_programming = question.get("kind", "choice") in {"programming", "project"}
        practice_base = PurePosixPath(bundle.manifest.practice_path)
        if is_programming and (
            practice_base.is_absolute() or ".." in practice_base.parts or not practice_base.parts
            or "\\" in bundle.manifest.practice_path
            or any(ord(char) < 32 for char in bundle.manifest.practice_path)
        ):
            raise ValueError("practice path must stay inside the learner directory")
        while page_id in existing_ids or (is_programming and str(practice_base / page_id) in existing_paths):
            page_id = f"{base_id}-{suffix}"
            suffix += 1
        existing_ids.add(page_id)
        if is_programming:
            practice_path = str(practice_base / page_id)
            if len(practice_path) > 240:
                raise ValueError("supplemental practice path is too long")
            existing_paths.add(practice_path)
            sections = [str(question["prompt"])]
            if question["milestones"]:
                sections.append("### 里程碑\n\n" + "\n".join(f"{index}. {step}" for index, step in enumerate(question["milestones"], 1)))
            sections.append("<details>\n<summary>需要时查看提示</summary>\n\n" + "\n".join(f"- {hint}" for hint in question["hints"]) + "\n\n</details>")
            sections.append("### 完成标准\n\n" + str(question["completion_criteria"]))
            added_pages.append(LessonPage(
                id=page_id, type="practice", practice_kind="homework",
                eyebrow="追加项目练习" if question["kind"] == "project" else "追加编程练习",
                title=str(question["title"]), markdown="\n\n".join(sections),
                question=str(question["prompt"]), language=bundle.manifest.language,
                practice_path=practice_path, completion_criteria=str(question["completion_criteria"]),
            ))
            continue
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
