"""Versioned lesson references and server-owned classroom recovery."""

import hashlib
import json
import re

from pydantic import BaseModel, Field

from .lesson_manifest import LessonBundle, LessonManifest


class LessonReference(BaseModel):
    lesson_id: str = Field(min_length=1, max_length=96, pattern=r"^[A-Za-z0-9_-]+$")
    page_id: str = Field(min_length=1, max_length=96)
    revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    quote: str = Field(min_length=1, max_length=2000)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def lesson_revision(manifest: LessonManifest) -> str:
    payload = manifest.model_dump()
    payload.pop("progress", None)
    # Preserve hashes of immutable snapshots created before locale fields existed.
    if payload.get('locale') == 'zh-CN':
        payload.pop('locale', None)
    for page in payload.get('pages', []):
        if page.get('locale') is None:
            page.pop('locale', None)
    # Additive optional scheduling fields must not invalidate old snapshots.
    for key in ("planned_sessions", "session_minutes", "homework_minutes"):
        if payload.get(key) is None:
            payload.pop(key, None)
    return _digest(payload)


def question_revision(question: str, options: list[dict], answer: str, *, code: str = "", markdown: str = "") -> str:
    return _digest([question, options, answer, code, markdown])


def restored_checks(bundle: LessonBundle, records: list[dict]) -> list[dict]:
    records_by_id = {record["id"]: record for record in records}
    passed = []
    for page in bundle.manifest.pages:
        if not page.question or not page.options:
            continue
        revision = question_revision(page.question, [option.model_dump() for option in page.options], bundle.answer_keys.get(page.id, ""), code=page.code, markdown=page.markdown)
        record = records_by_id.get(f"lesson:{bundle.manifest.lesson_id}:{page.id}", {})
        if any(attempt.get("correct") is True and attempt.get("question_revision") == revision for attempt in record.get("attempts", [])):
            passed.append({"page_id": page.id, "correct": True})
    return passed


def _visible_text(value: str) -> str:
    # Mirror the intentionally small MarkdownRenderer, not generic Markdown:
    # inline/fenced code and escaped literal HTML keep their original symbols.
    def inline(text: str) -> str:
        code = []
        def protect(match):
            code.append(match.group(1))
            return f"\ue000{len(code)-1}\ue000"
        text = re.sub(r"`([^`]+)`", protect, text.replace("\ue000", ""))
        text = re.sub(r"<u>(.*?)</u>", r"\1", text)
        text = re.sub(r"==([^=]+)==", r"\1", text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"\*([^*]+)\*", r"\1", text)
        return re.sub(r"\ue000(\d+)\ue000", lambda m: code[int(m.group(1))], text)

    visible = []
    fenced = False
    for line in value.replace("\r\n", "\n").split("\n"):
        if (not fenced and re.fullmatch(r"```[\w+-]*\s*", line)) or (fenced and re.fullmatch(r"```\s*", line)):
            fenced = not fenced
            continue
        if fenced:
            visible.append(line)
        else:
            line = re.sub(r"^(?:#{1,6}\s+|\s*[-*]\s+|\s*\d+[.)]\s+|>\s?)", "", line)
            visible.append(inline(line))
    return re.sub(r"\s+", "", "\n".join(visible))


def validate_reference(bundle: LessonBundle, reference: LessonReference) -> dict:
    if reference.lesson_id != bundle.manifest.lesson_id:
        raise ValueError("reference lesson is not active")
    if reference.revision != lesson_revision(bundle.manifest):
        raise ValueError("reference version is stale; select again")
    page = next((page for page in bundle.manifest.pages if page.id == reference.page_id), None)
    if page is None:
        raise ValueError("reference page is not active")
    quote = reference.quote.strip()
    # Browser selection is already rendered text. Never strip code operators
    # from it, or a fabricated `**` could match the actual `*` expression.
    normalized = re.sub(r"\s+", "", quote)
    code_match = bool(normalized) and normalized in re.sub(r"\s+", "", page.code)
    plain_match = any(normalized in re.sub(r"\s+", "", part) for part in [page.title, page.question or ""])
    if not normalized or not (code_match or plain_match or normalized in _visible_text(page.markdown)):
        raise ValueError("reference quote is not present on this page")
    return {**reference.model_dump(), "quote": quote, "page_title": page.title}
