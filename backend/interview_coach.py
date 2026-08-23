"""Model-assisted explanations for persisted interview questions."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

try:
    from .interview_bank import InterviewBankStore
except ImportError:
    from interview_bank import InterviewBankStore


SYSTEM = """你是一名严格、循序渐进的中文面试教练。只返回 JSON 对象，不要代码围栏。
字段必须是 answer_markdown、rubric、prerequisites、related_questions。
讲解先给直觉和准确概念，再说明面试表达、常见误区和一个小例子；不要跳过前置知识。
related_questions 只给 1 到 4 道紧密相关的追问、变式或前置题。"""


def _rubric_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "；".join(filter(None, (_rubric_text(item) for item in value)))
    if isinstance(value, dict):
        return "；".join(f"{key}：{_rubric_text(item)}" for key, item in value.items())
    return str(value)


def _parse(payload: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", payload.strip(), flags=re.I)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError("模型没有返回可用的结构化讲解") from exc
    if not isinstance(value, dict) or not isinstance(value.get("answer_markdown"), str):
        raise ValueError("模型没有返回可用的结构化讲解")
    rubric = value.get("rubric")
    if isinstance(rubric, dict) and all(isinstance(key, str) for key in rubric):
        value["rubric"] = [f"{key}：{_rubric_text(item)}" for key, item in rubric.items()]
    for field in ("rubric", "prerequisites", "related_questions"):
        if not isinstance(value.get(field), list) or not all(isinstance(item, str) for item in value[field]):
            raise ValueError("模型没有返回可用的结构化讲解")
    if not value["answer_markdown"].strip():
        raise ValueError("模型没有返回可用的结构化讲解")
    value["related_questions"] = [item.strip() for item in value["related_questions"][:4] if item.strip()]
    return value


def expand_question(
    store: InterviewBankStore,
    user_id: str,
    identifier: str,
    model_chat: Callable[[str, str], str],
    *,
    mode: str = "systematic",
) -> dict[str, Any]:
    question = store.get_question(user_id, identifier)
    prompt = (
        f"学习方式：{mode}\n面试题：{question['normalized_text']}\n"
        "请生成能让学习者最终独立回答并应对追问的系统讲解。"
    )
    parsed = _parse(model_chat(prompt, SYSTEM))
    related_ids = store.add_expanded_questions(user_id, parsed["related_questions"])
    updated = dict(question)
    updated.update({
        "answer_status": "ready",
        "answer_markdown": parsed["answer_markdown"].strip(),
        "rubric": parsed["rubric"],
        "prerequisites": parsed["prerequisites"],
        "related_question_ids": list(dict.fromkeys(
            list(question.get("related_question_ids") or []) + related_ids
        )),
    })
    store.save_question(user_id, updated)
    return {"question": updated, "related_question_ids": related_ids}
