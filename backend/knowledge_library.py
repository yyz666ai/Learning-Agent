"""Reusable, verified chapter assets for the shared curriculum library."""

from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path

try:
    from .curriculum import Curriculum
    from .lesson_manifest import LessonBundle, LessonManifest
except ImportError:
    from curriculum import Curriculum
    from lesson_manifest import LessonBundle, LessonManifest


def _topic_key(topic: str) -> str:
    readable = re.sub(r"[^a-z0-9]+", "-", topic.casefold()).strip("-")[:48] or "learning-topic"
    return f"{readable}-{hashlib.sha256(topic.encode('utf-8')).hexdigest()[:10]}"


def _chapter_root(server_root: Path, curriculum: Curriculum) -> Path:
    chapter = curriculum.current_chapter()
    return server_root / "workspace" / "dev" / "curriculum" / "generated" / _topic_key(curriculum.topic) / "chapters" / chapter.id


def _cache_paths(server_root: Path, curriculum: Curriculum) -> dict[str, Path]:
    root = _chapter_root(server_root, curriculum)
    variant = f"{curriculum.route}--{curriculum.level}"
    return {
        "root": root,
        "manifest": root / f"{variant}.lesson.json",
        "answers": root / f"{variant}.answers.json",
        "atom": root / f"{variant}.md",
        "deck": root / f"{variant}.deck.html",
    }


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def _render_atom(curriculum: Curriculum, bundle: LessonBundle) -> str:
    manifest = bundle.manifest
    lines = [
        f"# {curriculum.topic} · {manifest.chapter_title or manifest.title}",
        "",
        "> 来源：模型生成、学习者完成本章课堂选择题后自动沉淀；课后练习不作为保存门禁。",
        "",
        "## 覆盖知识点",
        "",
        *(f"- {point_id}" for point_id in manifest.covered_knowledge_point_ids),
        "",
        "## 讲义内容",
        "",
    ]
    for index, page in enumerate(manifest.pages, start=1):
        lines.extend((f"### {index}. {page.title}", "", page.markdown or ""))
        if page.code:
            lines.extend(("", f"```{page.language or ''}", page.code, "```"))
        if page.question:
            lines.extend(("", f"练习题：{page.question}", *(f"- {option.label}" for option in page.options)))
        lines.append("")
    homework = next((page for page in manifest.pages if page.practice_kind == "homework"), None)
    if homework is not None:
        lines.extend(("## 课后练习", "", homework.markdown or homework.title, ""))
    return "\n".join(lines)


def _render_deck(bundle: LessonBundle) -> str:
    sections = []
    for page in bundle.manifest.pages:
        body = html.escape(page.markdown or "")
        code = f"<pre><code>{html.escape(page.code)}</code></pre>" if page.code else ""
        sections.append(f"<section><p>{html.escape(page.eyebrow)}</p><h2>{html.escape(page.title)}</h2><p>{body}</p>{code}</section>")
    return "<!doctype html><html lang=\"zh-CN\"><meta charset=\"utf-8\"><title>学习讲义</title><body>" + "\n".join(sections) + "</body></html>\n"


def save_completed_chapter(server_root: Path, curriculum: Curriculum, bundle: LessonBundle) -> dict[str, Path]:
    """Persist only a chapter that has passed learner-visible completion checks."""
    paths = _cache_paths(server_root, curriculum)
    _atomic_write(paths["manifest"], bundle.manifest.model_dump_json(indent=2) + "\n")
    _atomic_write(paths["answers"], json.dumps(bundle.answer_keys, ensure_ascii=False, indent=2) + "\n")
    _atomic_write(paths["atom"], _render_atom(curriculum, bundle))
    _atomic_write(paths["deck"], _render_deck(bundle))
    return paths


def load_completed_chapter(server_root: Path, curriculum: Curriculum) -> LessonBundle | None:
    paths = _cache_paths(server_root, curriculum)
    if not paths["manifest"].is_file() or not paths["answers"].is_file():
        return None
    try:
        manifest = LessonManifest.model_validate_json(paths["manifest"].read_text(encoding="utf-8"))
        answers = json.loads(paths["answers"].read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(answers, dict):
        return None
    expected = [point.id for point in curriculum.current_chapter_remaining_points()]
    if manifest.topic != curriculum.topic or manifest.route != curriculum.route or manifest.covered_knowledge_point_ids != expected:
        return None
    return LessonBundle(manifest=manifest, answer_keys={str(key): str(value) for key, value in answers.items()})
