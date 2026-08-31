"""Read learner-facing plan and progress content from a user's state folder."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SAFE_USER_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def safe_user_id(user_id: str) -> str:
    value = (user_id or "").strip()
    return value if SAFE_USER_ID.fullmatch(value) else "yang"


def resolve_user_dir(user_id: str, server_root: Path) -> Path:
    return (server_root.resolve() / "userdir" / f"u_{safe_user_id(user_id)}").resolve()


def resolve_plan_path(user_dir: Path, active_plan: object) -> Path | None:
    if not isinstance(active_plan, str) or not active_plan.strip():
        return None
    resolved_user_dir = user_dir.resolve()
    target = (resolved_user_dir / active_plan.strip()).resolve()
    if target != resolved_user_dir and resolved_user_dir not in target.parents:
        return None
    return target if target.is_file() else None


def _section_first_line(markdown: str, heading: str) -> str:
    from .plan_locale import plan_labels
    markdown = plan_labels(markdown)
    active = False
    for raw in markdown.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            active = line.removeprefix("## ").strip() == heading
            continue
        if not active or not line or line.startswith("#"):
            continue
        value = re.sub(r"^[-*]\s+", "", line)
        value = re.sub(r"^(任务|当前任务)[：:]\s*", "", value)
        return value.strip()
    return ""


def parse_markdown_plan(markdown: str, source: str = "") -> dict[str, Any]:
    title = "我的学习路线"
    stages: list[dict[str, str]] = []
    current_stage_index: int | None = None
    marked_active_index: int | None = None
    for raw in markdown.splitlines():
        line = raw.strip()
        if line.startswith("# ") and title == "我的学习路线":
            title = line.removeprefix("# ").strip()
            title = re.sub(r"^学习计划[：:]\s*", "", title)
        elif line.startswith("### "):
            stage_title = line.removeprefix("### ").strip()
            if stage_title.startswith("阶段") or re.match(r"^第\s*\d+\s*章|^(?:Stage|Chapter|Phase)\s+\d+", stage_title, re.I):
                stages.append(
                    {
                        "title": stage_title,
                        "status": "active" if not stages else "upcoming",
                    }
                )
                current_stage_index = len(stages) - 1
        elif "（当前）" in line and current_stage_index is not None:
            marked_active_index = current_stage_index
    if marked_active_index is not None:
        for index, stage in enumerate(stages):
            stage["status"] = (
                "completed" if index < marked_active_index
                else "active" if index == marked_active_index
                else "upcoming"
            )
    return {
        "title": title,
        "source": source,
        "content": markdown,
        "stages": stages,
    }


def default_exercise(language: str) -> dict[str, Any]:
    if language == "go":
        return {
            "exercise_id": "go.first-program.predict-output",
            "kind": "prediction",
            "title": "预测一下输出",
            "prompt": '运行 fmt.Println("你好, Go!") 后，终端会显示什么？',
            "instructions": "在下面写出你预测的完整一行输出，然后提交。",
            "completion_criteria": "输出文字和标点与程序一致。",
        }
    if language == "python":
        return {
            "exercise_id": "python.first-program.predict-output",
            "kind": "prediction",
            "title": "预测一下输出",
            "prompt": '运行 print("你好, Python!") 后，终端会显示什么？',
            "instructions": "在下面写出你预测的完整一行输出，然后提交。",
            "completion_criteria": "输出文字和标点与程序一致。",
        }
    return {
        "exercise_id": "custom.first-concept.explain",
        "kind": "explanation",
        "title": "用自己的话讲一遍",
        "prompt": "刚刚这个核心概念解决了什么问题？",
        "instructions": "先写一个生活化例子，再说明它在真实场景中的作用。",
        "completion_criteria": "包含一个具体例子和一个可观察的作用。",
    }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _session_minutes(profile: str) -> int:
    match = re.search(r"单次时长[^\n]*?(\d+)\s*分钟", profile)
    return int(match.group(1)) if match else 25


def _learner_visible_plan(markdown: str) -> str:
    return re.sub(
        r"`?\$USER_DIR(?:/[^\s`)），。]+)+`?",
        "已核对的资料来源",
        markdown,
    )


def read_learning_context(
    user_id: str,
    server_root: Path,
) -> dict[str, Any]:
    selected_user = safe_user_id(user_id)
    user_dir = resolve_user_dir(selected_user, server_root)
    state = _read_json(user_dir / "learning-state.json")
    profile = _read_text(user_dir / "profile.md")
    plan_path = resolve_plan_path(user_dir, state.get("active_plan"))
    plan_text = _learner_visible_plan(_read_text(plan_path)) if plan_path else ""
    source = str(plan_path.relative_to(user_dir)) if plan_path else ""
    plan = parse_markdown_plan(plan_text, source)
    curriculum = _read_json(user_dir / "curriculum.json")
    points = [
        point
        for chapter in curriculum.get("chapters", []) if isinstance(chapter, dict)
        for point in chapter.get("knowledge_points", []) if isinstance(point, dict)
    ]
    completed_points = sum(point.get("status") == "completed" for point in points)
    current_task = _section_first_line(plan_text, "当前任务")
    language = state.get("active_language")
    topic = str(state.get("active_topic") or "").strip()
    if language not in {"python", "go"}:
        language = "custom" if topic else "go"
    return {
        "user_id": selected_user,
        "profile_status": state.get("profile_status", "uninitialized"),
        "plan_status": state.get("plan_status", "confirmed" if state.get("profile_status") == "confirmed" else "draft"),
        "knowledge_source": state.get("knowledge_source", "skill_guided"),
        "goal_route": state.get("goal_route", "foundation_engineer"),
        "concept_scope": state.get("concept_scope", "not_applicable"),
        "language": language,
        "topic": topic,
        "plan": plan,
        "current_task": current_task or "完成第一小步",
        "active_task": state.get("active_task") or "",
        "due_review_count": int(state.get("due_review_count") or 0),
        "session_minutes": (
            state.get("session_minutes")
            if isinstance(state.get("session_minutes"), int) and 10 <= state["session_minutes"] <= 120
            else _session_minutes(profile)
        ),
        "recent_evidence": list(state.get("recent_evidence") or [])[-3:],
        "knowledge_progress": {"completed": completed_points, "total": len(points)},
        "exercise": default_exercise(language),
    }
