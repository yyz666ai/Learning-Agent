"""Run fixed learner routes and score teaching-start quality."""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATTERNS = {
    "prior_experience": ("学过", "基础", "写过代码", "会不会编程"),
    "goal": ("想学什么", "学习目标", "主要想做什么"),
    "time": ("多少时间", "每周", "单次时长"),
}
VIVID_MARKERS = (
    "比如", "比方", "想成", "想象", "类比", "像", "好比", "菜谱", "盒子", "快递", "插座", "地图",
    "服务员", "点菜", "订单", "收货", "打电话", "发邮件", "邮筒",
    "拍照", "取景框", "画",
)
TEACHING_MARKERS = (
    "第一课", "核心", "概念", "程序", "请求流", "理解", "例如", "比如", "想成", "想象", "先看", "最小示例",
    "先讲", "取舍", "易错点", "一句话记",
    "坑", "规则", "原理",
)
INTERNAL_PROCESS_MARKERS = (
    "我先读取",
    "读取学习状态",
    "路由 concept",
    "检查 Schema",
    "核对教学",
    "教学策略和",
    "课程覆盖情况",
)
ANSWER_KEYS = {
    "go-variables": "a",
    "go-function": "b",
    "go-error": "b",
    "go-channel": "a",
    "py-variable": "a",
    "py-list": "a",
    "py-traceback": "a",
    "py-generator": "a",
    "project-entry": "a",
    "api-contract": "a",
    "debug-evidence": "a",
    "transfer": "a",
}

ROUTE_MARKERS = {
    "foundation_engineer": ("第一", "变量", "程序", "概念"),
    "urgent_codebase": ("入口", "调用链", "请求"),
    "syntax_reading": ("语法", "代码", "输出"),
    "project_delivery": ("文件", "运行", "API", "接口"),
    "gap_upgrade": ("易错", "薄弱", "迁移", "快进"),
    "senior_engineer": ("架构", "取舍", "可靠", "设计"),
    "interview_sprint": ("简答", "面试", "回答", "评价标准"),
}


def _assistant_texts(run: dict[str, Any]) -> list[str]:
    return [
        str(event.get("text") or "")
        for event in run.get("events", [])
        if event.get("role") in {"assistant", "agent"}
    ]


def _profile_categories(text: str) -> list[str]:
    question_clauses = re.findall(r"[^。！？!?\n]*[？?]", text)
    return [
        category
        for clause in question_clauses
        for category, markers in PROFILE_PATTERNS.items()
        if any(marker in clause for marker in markers)
    ]


def score_run(run: dict[str, Any]) -> dict[str, Any]:
    texts = _assistant_texts(run)
    categories = [category for text in texts for category in _profile_categories(text)]
    profile_question_count = len(categories)
    duplicate_count = sum(max(0, categories.count(category) - 1) for category in set(categories))
    combined = "\n".join(texts)
    batch_questions = re.search(
        r"(?:两|二|三|四|五|六|七|八|九|[2-9])\s*(?:道题|个(?:问题|练习|题))",
        combined,
    )
    separate_exercise_blocks = (
        ("**判断**" in combined and "**练习**" in combined)
        or "两个答案" in combined
        or "然后做这道" in combined
    )
    has_question = "题" in combined or "？" in combined or "?" in combined
    question_count = 2 if batch_questions or separate_exercise_blocks else 1 if has_question else 0
    diagnostic_count = int(run.get("diagnostic_question_count") or 0)
    turns = int(run.get("turns_to_first_teaching") or 99)
    has_teaching = any(marker in combined for marker in TEACHING_MARKERS)
    has_vivid_example = any(marker in combined for marker in VIVID_MARKERS)
    internal_process_leak = any(marker in combined for marker in INTERNAL_PROCESS_MARKERS)
    goal_route = str(run.get("goal_route") or "")
    route_markers = ROUTE_MARKERS.get(goal_route, ())
    route_fit = not route_markers or any(marker in combined for marker in route_markers)
    interview_avoids_choices = goal_route != "interview_sprint" or not re.search(
        r"(?:^|\n)\s*[A-D][.、：:]", combined
    )
    unsafe_install_instruction = "pip install" in combined and not any(
        marker in combined for marker in ("虚拟环境", "项目环境", "先检查", "已经使用")
    )
    passed = all(
        (
            profile_question_count == 0,
            duplicate_count == 0,
            diagnostic_count <= 10,
            turns <= 2,
            has_teaching,
            has_vivid_example,
            not internal_process_leak,
            question_count <= 1,
            route_fit,
            interview_avoids_choices,
            not unsafe_install_instruction,
        )
    )
    return {
        "passed": passed,
        "profile_question_count": profile_question_count,
        "duplicate_question_count": duplicate_count,
        "diagnostic_question_count": diagnostic_count,
        "turns_to_first_teaching": turns,
        "has_teaching": has_teaching,
        "has_vivid_example": has_vivid_example,
        "internal_process_leak": internal_process_leak,
        "visible_question_count": question_count,
        "small_step": question_count <= 1,
        "goal_route": goal_route,
        "route_fit": route_fit,
        "interview_avoids_choices": interview_avoids_choices,
        "response_characters": len(combined),
        "unsafe_install_instruction": unsafe_install_instruction,
    }


def score_state(user_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    active_plan = state.get("active_plan")
    resolves = False
    resolved_path = ""
    if isinstance(active_plan, str) and active_plan.strip():
        root = user_dir.resolve()
        candidate = (root / active_plan).resolve()
        if (candidate == root or root in candidate.parents) and candidate.is_file():
            resolves = True
            resolved_path = str(candidate)
    return {
        "active_plan": active_plan,
        "active_plan_resolves": resolves,
        "resolved_plan_path": resolved_path,
        "profile_confirmed": state.get("profile_status") == "confirmed",
    }


def _parse_sse(text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for block in re.split(r"\r?\n\r?\n", text):
        event_name = "message"
        data_lines: list[str] = []
        for line in block.splitlines():
            if line.startswith("event:"):
                event_name = line.removeprefix("event:").strip()
            elif line.startswith("data:"):
                data_lines.append(line.removeprefix("data:").strip())
        if not data_lines:
            continue
        try:
            data = json.loads("\n".join(data_lines))
        except json.JSONDecodeError:
            data = {"raw": "\n".join(data_lines)}
        events.append({"event": event_name, "data": data})
    return events


def _choose_option(question: dict[str, Any], correct: bool) -> str:
    correct_id = ANSWER_KEYS.get(str(question.get("id")))
    option_ids = [str(option["id"]) for option in question.get("options", [])]
    if correct and correct_id in option_ids:
        return str(correct_id)
    return next((option for option in option_ids if option != correct_id), option_ids[0])


def run_persona(client: httpx.Client, persona: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "user_id": persona["user_id"],
        "learning_mode": persona["learning_mode"],
        "goal_route": persona.get("goal_route", "foundation_engineer"),
        "level_claim": persona["level_claim"],
        "topic": persona["topic"],
        "session_minutes": int(persona.get("session_minutes") or 25),
        "teaching_preference": "balanced",
    }
    raw_calls: list[dict[str, Any]] = []
    diagnostic_count = 0
    session_id = None
    started_at = time.monotonic()

    if persona["level_claim"] != "zero":
        response = client.post("/api/onboarding/start", json=payload)
        response.raise_for_status()
        current = response.json()
        raw_calls.append({"path": "/api/onboarding/start", "response": current})
        session_id = current["session_id"]
        pattern = list(persona.get("diagnostic_pattern") or [True, True, True])
        while not current.get("complete"):
            desired = pattern[min(diagnostic_count, len(pattern) - 1)]
            answer = {
                "user_id": persona["user_id"],
                "session_id": session_id,
                "question_id": current["question"]["id"],
                "selected_option_id": _choose_option(current["question"], desired),
            }
            response = client.post("/api/diagnostics/answer", json=answer)
            response.raise_for_status()
            current = response.json()
            diagnostic_count += 1
            raw_calls.append({"path": "/api/diagnostics/answer", "response": current})

    confirm_payload = dict(payload)
    if session_id:
        confirm_payload["diagnostic_session_id"] = session_id
    response = client.post("/api/onboarding/confirm", json=confirm_payload)
    response.raise_for_status()
    raw_calls.append({"path": "/api/onboarding/confirm", "response": response.json()})

    response = client.post(
        "/api/chat/stream",
        json={
            "user_id": persona["user_id"],
            "message": persona["first_prompt"],
            "history": [],
        },
        timeout=660,
    )
    response.raise_for_status()
    sse_events = _parse_sse(response.text)
    assistant_text = "".join(
        str(event["data"].get("text") or "")
        for event in sse_events
        if event["event"] == "message.delta"
    )
    raw_calls.append({"path": "/api/chat/stream", "events": sse_events})
    duration = time.monotonic() - started_at
    return {
        "persona_id": persona["id"],
        "goal_route": persona.get("goal_route", "foundation_engineer"),
        "user_id": persona["user_id"],
        "events": [{"role": "assistant", "text": assistant_text}],
        "diagnostic_question_count": diagnostic_count,
        "turns_to_first_teaching": 1 if persona["level_claim"] == "zero" else 2,
        "duration_seconds": round(duration, 2),
        "raw_calls": raw_calls,
    }


def _write_report(output: Path, results: list[dict[str, Any]]) -> None:
    lines = [
        "# Phase C 七路线教学质量评测",
        "",
        f"生成时间：{datetime.now(timezone.utc).isoformat()}",
        "",
        "| 画像 | 路线匹配 | 诊断题 | 开课步数 | 重复摸底 | 生动类比 | 计划可读 | 用时 | 结果 |",
        "| --- | --- | ---: | ---: | ---: | --- | --- | ---: | --- |",
    ]
    for result in results:
        quality = result["quality"]
        state = result["state_quality"]
        passed = quality["passed"] and state["active_plan_resolves"] and state["profile_confirmed"]
        lines.append(
            f"| {result['persona_id']} | {'是' if quality['route_fit'] else '否'} | {quality['diagnostic_question_count']} | "
            f"{quality['turns_to_first_teaching']} | {quality['duplicate_question_count']} | "
            f"{'是' if quality['has_vivid_example'] else '否'} | "
            f"{'是' if state['active_plan_resolves'] else '否'} | "
            f"{result['duration_seconds']}s | {'通过' if passed else '未通过'} |"
        )
    (output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8791")
    parser.add_argument("--personas", type=Path, default=ROOT / "evals/personas.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--only", action="append", default=[], help="Only run matching persona ids")
    args = parser.parse_args()
    config = json.loads(args.personas.read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    with httpx.Client(base_url=args.base_url, timeout=30) as client:
        personas = [persona for persona in config["personas"] if not args.only or persona["id"] in args.only]
        for persona in personas:
            run = run_persona(client, persona)
            state_response = client.get("/api/state", params={"user_id": persona["user_id"]})
            state_response.raise_for_status()
            state = state_response.json()["state"]
            state_quality = score_state(ROOT / "userdir" / f"u_{persona['user_id']}", state)
            run["quality"] = score_run(run)
            run["state_quality"] = state_quality
            (args.output / f"{persona['id']}.json").write_text(
                json.dumps(run, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            results.append(run)
    _write_report(args.output, results)
    all_passed = all(
        result["quality"]["passed"]
        and result["state_quality"]["active_plan_resolves"]
        and result["state_quality"]["profile_confirmed"]
        for result in results
    )
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
