"""Structured, learner-owned curriculum derived from a model-authored plan."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

try:
    from .learning_content import SAFE_USER_ID
except ImportError:
    from learning_content import SAFE_USER_ID


class KnowledgePoint(BaseModel):
    id: str = Field(min_length=1, max_length=96, pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=1, max_length=240)
    outcome: str = Field(min_length=1, max_length=1000)
    practice: str = Field(min_length=1, max_length=2000)
    mastery_criteria: str = Field(min_length=1, max_length=2000)
    prerequisites: list[str] = Field(default_factory=list, max_length=12)
    estimated_sessions: int = Field(default=1, ge=1, le=20)
    status: Literal["active", "upcoming", "completed"] = "upcoming"


class Chapter(BaseModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=1, max_length=240)
    knowledge_points: list[KnowledgePoint] = Field(min_length=1, max_length=30)


class Curriculum(BaseModel):
    schema_version: int = 1
    topic: str = Field(min_length=1, max_length=240)
    route: str = Field(min_length=1, max_length=64)
    level: str = Field(min_length=1, max_length=64)
    chapters: list[Chapter] = Field(min_length=1, max_length=60)
    current_knowledge_point_id: str = Field(min_length=1, max_length=96)

    def knowledge_points(self) -> list[KnowledgePoint]:
        return [point for chapter in self.chapters for point in chapter.knowledge_points]

    def current_chapter(self) -> Chapter:
        for chapter in self.chapters:
            if any(point.id == self.current_knowledge_point_id for point in chapter.knowledge_points):
                return chapter
        raise ValueError("current knowledge point chapter is missing")

    def current_chapter_remaining_points(self) -> list[KnowledgePoint]:
        chapter = self.current_chapter()
        current_index = next(
            index for index, point in enumerate(chapter.knowledge_points)
            if point.id == self.current_knowledge_point_id
        )
        return [point for point in chapter.knowledge_points[current_index:] if point.status != "completed"]

    @model_validator(mode="after")
    def validate_graph(self) -> "Curriculum":
        points = self.knowledge_points()
        ids = [point.id for point in points]
        minimum_points = 1 if self.route == "concept_clarity" else 5
        if len(points) < minimum_points:
            raise ValueError(f"curriculum must contain at least {minimum_points} knowledge points")
        if len(ids) != len(set(ids)):
            raise ValueError("knowledge point ids must be unique")
        known = set(ids)
        if self.current_knowledge_point_id not in known:
            raise ValueError("current knowledge point must exist")
        if any(prerequisite not in known for point in points for prerequisite in point.prerequisites):
            raise ValueError("prerequisite must reference an existing knowledge point")
        return self


def _slug(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return (slug or fallback)[:80]


def _field(section: str, label: str, fallback: str) -> str:
    match = re.search(rf"(?m)^- {re.escape(label)}[：:]\s*(.+)$", section)
    return match.group(1).strip() if match else fallback


def _knowledge_items(section: str, fallback: str) -> list[str]:
    """Prefer readable nested knowledge bullets; retain legacy semicolon Plans."""
    block = re.search(
        r"(?ms)^#### 知识点\s*$\n(?P<body>.*?)(?=^- 本阶段要学[：:]|^#### |\Z)",
        section,
    )
    if block is not None:
        items = [
            item.strip(" 。")
            for item in re.findall(r"(?m)^-\s+(.+)$", block.group("body"))
            if item.strip(" 。")
        ]
        if items:
            return items
    return [item.strip(" 。") for item in fallback.split("；") if item.strip(" 。")] or [fallback]


def _estimated_sessions(section: str, item_count: int) -> int:
    match = re.search(r"(?m)^- 预计课次[：:]\s*(\d+)\s*$", section)
    total = int(match.group(1)) if match else item_count
    return max(1, min(20, (total + max(1, item_count) - 1) // max(1, item_count)))


def curriculum_from_plan(markdown: str, *, topic: str, route: str, level: str) -> Curriculum:
    """Turn a detailed model-authored Markdown plan into a navigable curriculum."""
    headings = list(re.finditer(r"(?m)^###\s+(?:阶段\s*\d+|第\s*\d+\s*章)[：:\s]*(.+)$", markdown))
    chapters: list[Chapter] = []
    previous_id: str | None = None
    used_ids: set[str] = set()
    for chapter_index, heading in enumerate(headings, start=1):
        end = headings[chapter_index].start() if chapter_index < len(headings) else len(markdown)
        section = markdown[heading.start():end]
        chapter_title = heading.group(1).strip()
        learn = _field(section, "本阶段要学", chapter_title)
        practice = _field(section, "练习", f"围绕 {chapter_title} 完成一次可验证练习")
        evidence = _field(section, "完成证据", f"能独立解释并应用 {chapter_title}")
        concepts = _knowledge_items(section, learn)
        estimated_sessions = _estimated_sessions(section, len(concepts))
        points: list[KnowledgePoint] = []
        for point_index, concept in enumerate(concepts, start=1):
            concept_title = concept if len(concept) <= 220 else concept[:217].rstrip(" ，。；:：") + "…"
            concept_outcome = concept if len(concept) <= 900 else concept[:897].rstrip(" ，。；:：") + "…"
            base_id = _slug(concept_title, f"chapter-{chapter_index}-point-{point_index}")
            point_id = base_id
            suffix = 2
            while point_id in used_ids:
                point_id = f"{base_id}-{suffix}"
                suffix += 1
            used_ids.add(point_id)
            points.append(
                KnowledgePoint(
                    id=point_id,
                    title=concept_title,
                    outcome=f"理解并能解释：{concept_outcome}",
                    practice=practice,
                    mastery_criteria=evidence,
                    prerequisites=[previous_id] if previous_id else [],
                    estimated_sessions=estimated_sessions,
                    status="active" if previous_id is None else "upcoming",
                )
            )
            previous_id = point_id
        chapters.append(
            Chapter(
                id=f"chapter-{chapter_index}",
                title=chapter_title,
                knowledge_points=points,
            )
        )
    if not chapters:
        raise ValueError("plan does not contain concrete chapters")
    first_id = chapters[0].knowledge_points[0].id
    return Curriculum(
        topic=topic,
        route=route,
        level=level,
        chapters=chapters,
        current_knowledge_point_id=first_id,
    )


def render_curriculum_plan(curriculum: Curriculum) -> str:
    lines = [
        f"# {curriculum.topic} 详细学习大纲",
        "",
        f"> 路线：{curriculum.route} · 当前能力：{curriculum.level}",
        "",
        "## 课程地图",
        "",
    ]
    for chapter_index, chapter in enumerate(curriculum.chapters, start=1):
        lines.extend((f"### 第 {chapter_index} 章：{chapter.title}", ""))
        for point_index, point in enumerate(chapter.knowledge_points, start=1):
            marker = "（当前）" if point.id == curriculum.current_knowledge_point_id else ""
            lines.extend(
                (
                    f"#### {chapter_index}.{point_index} {point.title}{marker}",
                    f"- 学习结果：{point.outcome}",
                    f"- 练习：{point.practice}",
                    f"- 完成标准：{point.mastery_criteria}",
                    "",
                )
            )
    current = next(point for point in curriculum.knowledge_points() if point.id == curriculum.current_knowledge_point_id)
    lines.extend(("## 当前任务", "", f"学习并完成：{current.title}", ""))
    return "\n".join(lines)


def curriculum_path(server_root: Path, user_id: str) -> Path:
    if not SAFE_USER_ID.fullmatch(user_id):
        raise ValueError("invalid user_id")
    return server_root / "userdir" / f"u_{user_id}" / "curriculum.json"


def save_curriculum(server_root: Path, user_id: str, curriculum: Curriculum) -> Path:
    path = curriculum_path(server_root, user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(curriculum.model_dump_json(indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def load_curriculum(server_root: Path, user_id: str) -> Curriculum:
    return Curriculum.model_validate_json(curriculum_path(server_root, user_id).read_text(encoding="utf-8"))
