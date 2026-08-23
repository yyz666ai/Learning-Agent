"""Persist exercise evidence and render a learner-owned review handout."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .learning_content import resolve_user_dir
    from .review_cards import add_question_card
except ImportError:
    from learning_content import resolve_user_dir
    from review_cards import add_question_card


IMPORTANT_QUESTION = re.compile(
    r"为什么|原理|区别|边界|什么时候|怎么选择|报错|错误|异常|性能|安全|并发|底层|架构|复杂度|坑|注意",
    re.IGNORECASE,
)


def _safe_lesson_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-")[:96]
    return cleaned or "current-lesson"


def _lesson_notes_path(server_root: Path, user_id: str, lesson_id: str) -> Path:
    user_dir = resolve_user_dir(user_id, server_root)
    return user_dir / "lessons" / f"{_safe_lesson_id(lesson_id)}.notes.json"


def read_lesson_notes(server_root: Path, user_id: str, lesson_id: str) -> dict[str, Any]:
    path = _lesson_notes_path(server_root, user_id, lesson_id)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"lesson_id": _safe_lesson_id(lesson_id), "notes": []}
    notes = payload.get("notes") if isinstance(payload, dict) else None
    return {"lesson_id": _safe_lesson_id(lesson_id), "notes": notes if isinstance(notes, list) else []}


def append_lesson_note(
    server_root: Path,
    user_id: str,
    *,
    lesson_id: str,
    topic: str,
    question: str,
    summary: str,
) -> dict[str, Any]:
    """Persist a learner-owned PPT note and queue reusable important questions."""
    payload = read_lesson_notes(server_root, user_id, lesson_id)
    notes = payload["notes"]
    clean_question = question.strip()[:2_000]
    clean_summary = summary.strip()[:4_000]
    important = bool(IMPORTANT_QUESTION.search(clean_question))
    sequence = len(notes) + 1
    excerpt = re.sub(r"\s+", " ", clean_question).strip("。！？?!")[:48]
    reward = (
        f"你的专属奖励：第 {sequence} 次主动追问把“{excerpt}”变成了可复习的知识点。"
        if important
        else f"你的专属奖励：你在本课留下了第 {sequence} 条自己的学习痕迹，而不只是看完代码。"
    )
    note = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "topic": topic[:240],
        "question": clean_question,
        "summary": clean_summary,
        "important": important,
        "reward": reward,
    }
    notes.append(note)
    path = _lesson_notes_path(server_root, user_id, lesson_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)

    markdown = path.with_suffix(".notes.md")
    lines = ["# 我的课堂笔记", "", f"> 课程：{topic or lesson_id}", ""]
    for index, item in enumerate(notes, start=1):
        lines.extend((
            f"## 笔记 {index}", "", f"**我的问题**：{item.get('question', '')}", "",
            f"**教练总结**：{item.get('summary', '')}", "", f"> {item.get('reward', '')}", "",
        ))
    markdown.write_text("\n".join(lines), encoding="utf-8")

    if important:
        add_question_card(server_root, user_id, topic=topic, question=clean_question, summary=clean_summary)
        candidate = server_root / "workspace/dev/curriculum/curation/pending/important-questions.jsonl"
        candidate.parent.mkdir(parents=True, exist_ok=True)
        with candidate.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "created_at": note["created_at"], "topic": topic[:240],
                "question": clean_question, "summary": clean_summary,
                "status": "pending_review",
            }, ensure_ascii=False) + "\n")
    return note


def append_attempt(
    server_root: Path,
    user_id: str,
    *,
    question: str,
    answer: str,
    feedback: str,
    kind: str,
) -> Path:
    user_dir = resolve_user_dir(user_id, server_root)
    review_dir = user_dir / "reviews"
    review_dir.mkdir(parents=True, exist_ok=True)
    attempt = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "question": question,
        "answer": answer,
        "feedback": feedback,
    }
    attempts_file = review_dir / "exercise-attempts.jsonl"
    with attempts_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(attempt, ensure_ascii=False) + "\n")
    document = review_dir / "review-notes.md"
    document.write_text(render_review_document(attempts_file), encoding="utf-8")
    return document


def append_learning_question(
    server_root: Path,
    user_id: str,
    *,
    question: str,
    topic: str = "",
) -> Path:
    """Keep learner-initiated questions apart from deterministic run-output checks."""
    user_dir = resolve_user_dir(user_id, server_root)
    memory_dir = user_dir / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    item = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "topic": topic,
        "question": question.strip(),
    }
    questions_file = memory_dir / "questions.jsonl"
    with questions_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    questions = [entry for entry in read_attempts(questions_file) if entry.get("question")]
    document = memory_dir / "questions.md"
    lines = ["# 我遇到的问题", "", "> 这些是学习时主动提出的问题，之后可以用来复习薄弱点。", ""]
    for index, entry in enumerate(questions[-80:], start=max(1, len(questions) - 79)):
        topic_label = f" · {entry['topic']}" if entry.get("topic") else ""
        lines.extend((f"## 问题 {index}{topic_label}", "", str(entry["question"]), ""))
    document.write_text("\n".join(lines), encoding="utf-8")
    return document


def read_attempts(attempts_file: Path) -> list[dict[str, Any]]:
    if not attempts_file.is_file():
        return []
    attempts: list[dict[str, Any]] = []
    for line in attempts_file.read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            attempts.append(value)
    return attempts


def render_review_document(attempts_file: Path) -> str:
    attempts = read_attempts(attempts_file)
    lines = [
        "# 我的学习讲义与练习复盘",
        "",
        "> 这份文档由你真实做过的题与教练评价组成，会随着学习持续更新。",
        "",
    ]
    if not attempts:
        lines.extend(("还没有已提交的练习。完成第一道题后，这里会形成你的复习材料。", ""))
        return "\n".join(lines)
    for index, item in enumerate(attempts, start=1):
        lines.extend(
            (
                f"## 练习 {index}",
                "",
                f"**题目**：{item.get('question', '')}",
                "",
                f"**我的作答**：{item.get('answer', '')}",
                "",
                f"**教练评价**：{item.get('feedback', '')}",
                "",
            )
        )
    lines.extend(("## 下一次复习怎么用", "", "先遮住教练评价重新作答，再比较这次和上次的差异。", ""))
    return "\n".join(lines)


def read_review_document(server_root: Path, user_id: str) -> dict[str, Any]:
    user_dir = resolve_user_dir(user_id, server_root)
    attempts_file = user_dir / "reviews" / "exercise-attempts.jsonl"
    content = render_review_document(attempts_file)
    return {"content": content, "attempt_count": len(read_attempts(attempts_file))}
