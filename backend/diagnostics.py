"""Server-owned, click-only adaptive learner diagnosis."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any
from uuid import uuid4

from .onboarding import DiagnosisSummary


QUESTION_BANKS: dict[str, list[dict[str, Any]]] = {
    "go": [
        {
            "id": "go-variables",
            "prompt": "下面哪一行会创建一个值为 3 的 Go 变量 n？",
            "dimension": "syntax",
            "options": [
                {"id": "a", "label": "n := 3"},
                {"id": "b", "label": "let n = 3"},
                {"id": "c", "label": "n <- 3"},
            ],
            "correct_option_id": "a",
        },
        {
            "id": "go-function",
            "prompt": "调用函数 add(2, 3) 时，最贴近“参数”的是哪一项？",
            "dimension": "concept",
            "options": [
                {"id": "a", "label": "add"},
                {"id": "b", "label": "2 和 3"},
                {"id": "c", "label": "函数返回后的结果"},
            ],
            "correct_option_id": "b",
        },
        {
            "id": "go-error",
            "prompt": "Go 函数返回 err 后，最稳妥的下一步通常是什么？",
            "dimension": "debugging",
            "options": [
                {"id": "a", "label": "忽略 err，继续运行"},
                {"id": "b", "label": "先判断 err 是否为 nil"},
                {"id": "c", "label": "把 err 改成字符串"},
            ],
            "correct_option_id": "b",
        },
        {
            "id": "go-channel",
            "prompt": "无缓冲 channel 没有接收者时，发送操作通常会怎样？",
            "dimension": "mental_model",
            "options": [
                {"id": "a", "label": "等待接收者"},
                {"id": "b", "label": "自动丢弃数据"},
                {"id": "c", "label": "自动写入文件"},
            ],
            "correct_option_id": "a",
        },
    ],
    "python": [
        {
            "id": "py-variable",
            "prompt": "哪一行会让变量 count 保存数字 3？",
            "dimension": "syntax",
            "options": [
                {"id": "a", "label": "count = 3"},
                {"id": "b", "label": "count := int 3"},
                {"id": "c", "label": "3 -> count"},
            ],
            "correct_option_id": "a",
        },
        {
            "id": "py-list",
            "prompt": "items.append(x) 主要会做什么？",
            "dimension": "concept",
            "options": [
                {"id": "a", "label": "把 x 加到列表末尾"},
                {"id": "b", "label": "删除列表"},
                {"id": "c", "label": "复制整个程序"},
            ],
            "correct_option_id": "a",
        },
        {
            "id": "py-traceback",
            "prompt": "排查异常时，Traceback 最先帮你定位什么？",
            "dimension": "debugging",
            "options": [
                {"id": "a", "label": "出错调用路径和代码位置"},
                {"id": "b", "label": "电脑剩余电量"},
                {"id": "c", "label": "网页配色"},
            ],
            "correct_option_id": "a",
        },
        {
            "id": "py-generator",
            "prompt": "生成器相对一次性列表，常见优势是什么？",
            "dimension": "mental_model",
            "options": [
                {"id": "a", "label": "按需产生值，减少内存占用"},
                {"id": "b", "label": "总能运行得无限快"},
                {"id": "c", "label": "不需要任何代码"},
            ],
            "correct_option_id": "a",
        },
    ],
}

GENERIC_BANK = [
    {
        "id": "project-entry",
        "prompt": "接手陌生项目时，哪一步更适合先建立全局认识？",
        "dimension": "project_reading",
        "options": [
            {"id": "a", "label": "先看入口、README 和主要目录"},
            {"id": "b", "label": "立刻重写所有文件"},
            {"id": "c", "label": "只看文件名最长的文件"},
        ],
        "correct_option_id": "a",
    },
    {
        "id": "api-contract",
        "prompt": "理解一个 API 时，哪组信息最关键？",
        "dimension": "concept",
        "options": [
            {"id": "a", "label": "输入、输出和失败方式"},
            {"id": "b", "label": "作者头像和屏幕亮度"},
            {"id": "c", "label": "文件创建日期"},
        ],
        "correct_option_id": "a",
    },
    {
        "id": "debug-evidence",
        "prompt": "定位故障时，哪一种做法留下的证据最好？",
        "dimension": "debugging",
        "options": [
            {"id": "a", "label": "记录最小复现、输入和实际输出"},
            {"id": "b", "label": "连续随机修改"},
            {"id": "c", "label": "只说“它坏了”"},
        ],
        "correct_option_id": "a",
    },
    {
        "id": "transfer",
        "prompt": "验证自己真正理解一个概念，哪种方式更可靠？",
        "dimension": "transfer",
        "options": [
            {"id": "a", "label": "换一个小场景重新应用"},
            {"id": "b", "label": "只把定义读十遍"},
            {"id": "c", "label": "跳过所有练习"},
        ],
        "correct_option_id": "a",
    },
]


def _bank_for(topic: str) -> list[dict[str, Any]]:
    lowered = topic.casefold()
    if lowered == "go" or "golang" in lowered:
        return QUESTION_BANKS["go"]
    if "python" in lowered:
        return QUESTION_BANKS["python"]
    return GENERIC_BANK


def has_curated_bank(topic: str, goal_route: str | None = None) -> bool:
    if goal_route == "interview_sprint":
        return False
    lowered = topic.casefold()
    return lowered == "go" or "golang" in lowered or "python" in lowered


def build_diagnosis_prompt(topic: str, level_claim: str, goal_route: str) -> str:
    return f"""你在 Learning Agent workspace 中工作。先读取 `adaptive-onboarding` Skill，再根据主题、目标和水平生成点击式诊断题。

主题：{topic}
用户自述水平：{level_claim}
学习目标路线：{goal_route}

只输出 JSON：{{"topic":"{topic}","questions":[...]}}。顶层 topic 必须原样保留为“{topic}”。questions 必须有 3 或 4 道题；每题含 id、prompt、dimension、options、correct_option_id。
options 为 2–4 个 {{"id":"a","label":"..."}}，correct_option_id 必须引用本题 option。题目应针对主题与路线；不要要求用户写代码、输入文本或解释。每一道 prompt 或 dimension 都必须原样包含完整主题“{topic}”，方便服务端校验没有串岗；只写 AI、Go、前端等局部通用词不算通过。
先确定该目标岗位的岗位核心能力，再从中选择能区分起点的判断题。不得复用通用题库，不得输出与“{topic}”无关的技术或岗位问题。
"""


def parse_generated_diagnosis(response: str, *, expected_topic: str | None = None) -> list[dict[str, Any]]:
    start, end = response.find("{"), response.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("diagnosis response is not JSON")
    payload = json.loads(response[start:end + 1])
    if expected_topic is not None:
        actual_topic = str(payload.get("topic") or "") if isinstance(payload, dict) else ""
        topic_key = lambda value: re.sub(r"[\s\W_]+", "", value.casefold())
        if topic_key(actual_topic) != topic_key(expected_topic):
            raise ValueError("diagnosis topic does not match the target role")
        required_topic_anchor = topic_key(expected_topic)
    else:
        required_topic_anchor = ""
    questions = payload.get("questions") if isinstance(payload, dict) else None
    if not isinstance(questions, list) or not 3 <= len(questions) <= 4:
        raise ValueError("diagnosis requires three or four questions")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in questions:
        if not isinstance(raw, dict):
            raise ValueError("diagnosis question must be an object")
        identifier = str(raw.get("id") or "")
        prompt = str(raw.get("prompt") or "")
        dimension = str(raw.get("dimension") or "")
        options = raw.get("options")
        answer = str(raw.get("correct_option_id") or "")
        if not re.fullmatch(r"[a-z0-9-]{1,96}", identifier) or identifier in seen or not prompt.strip() or not dimension.strip():
            raise ValueError("diagnosis question metadata is invalid")
        searchable = re.sub(r"[\s\W_]+", "", f"{prompt} {dimension}".casefold())
        if required_topic_anchor and required_topic_anchor not in searchable:
            raise ValueError("diagnosis question is not anchored to the target role")
        if not isinstance(options, list) or not 2 <= len(options) <= 4:
            raise ValueError("diagnosis options must contain two to four choices")
        clean_options = []
        for option in options:
            if not isinstance(option, dict) or not isinstance(option.get("id"), str) or not isinstance(option.get("label"), str):
                raise ValueError("diagnosis option is invalid")
            clean_options.append({"id": option["id"], "label": option["label"]})
        if answer not in {option["id"] for option in clean_options}:
            raise ValueError("diagnosis answer must reference an option")
        seen.add(identifier)
        result.append({"id": identifier, "prompt": prompt, "dimension": dimension, "options": clean_options, "correct_option_id": answer})
    return result


def start_diagnosis(topic: str, level_claim: str, *, questions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    bank = deepcopy(questions if questions is not None else _bank_for(topic))
    return {
        "session_id": uuid4().hex,
        "topic": topic,
        "level_claim": level_claim,
        "question_index": 0,
        "question": bank[0],
        "bank": bank,
        "answers": [],
        "answered_count": 0,
        "complete": False,
    }


def answer_diagnosis(
    session: dict[str, Any],
    selected_option_id: str,
    *,
    question_id: str | None = None,
) -> dict[str, Any]:
    if session.get("complete"):
        raise ValueError("diagnosis is already complete")
    current = session["question"]
    if question_id is not None and question_id != current["id"]:
        raise ValueError("question does not match current session")
    valid_options = {option["id"] for option in current["options"]}
    if selected_option_id not in valid_options:
        raise ValueError("selected option is invalid")

    updated = deepcopy(session)
    is_correct = selected_option_id == current["correct_option_id"]
    updated["answers"].append(
        {
            "question_id": current["id"],
            "dimension": current["dimension"],
            "selected_option_id": selected_option_id,
            "correct": is_correct,
        }
    )
    updated["answered_count"] += 1
    count = updated["answered_count"]
    recent = [answer["correct"] for answer in updated["answers"][-3:]]
    stable_after_three = count >= 3 and len(set(recent)) == 1
    updated["complete"] = stable_after_three or count >= 4 or count >= 10
    if not updated["complete"]:
        updated["question_index"] = count % len(updated["bank"])
        updated["question"] = updated["bank"][updated["question_index"]]
    return updated


def public_session(session: dict[str, Any]) -> dict[str, Any]:
    result = {
        key: deepcopy(value)
        for key, value in session.items()
        if key not in {"bank", "answers"}
    }
    question = result.get("question")
    if isinstance(question, dict):
        question.pop("correct_option_id", None)
        question.pop("dimension", None)
    return result


def summarize_diagnosis(session: dict[str, Any]) -> DiagnosisSummary:
    answers = list(session.get("answers") or [])
    if not session.get("complete") or not answers:
        raise ValueError("diagnosis is not complete")
    score = sum(bool(answer["correct"]) for answer in answers) / len(answers)
    if score >= 0.75:
        level = "experienced"
    elif score >= 0.4:
        level = "foundation"
    else:
        level = "beginner"
    strengths = [answer["dimension"] for answer in answers if answer["correct"]]
    gaps = [answer["dimension"] for answer in answers if not answer["correct"]]
    return DiagnosisSummary(
        estimated_level=level,
        score=score,
        answered_count=len(answers),
        strengths=list(dict.fromkeys(strengths)),
        gaps=list(dict.fromkeys(gaps)),
        evidence=[
            {
                "question_id": str(answer["question_id"]),
                "dimension": str(answer["dimension"]),
                "correct": bool(answer["correct"]),
            }
            for answer in answers
        ],
    )
