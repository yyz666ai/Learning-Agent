"""Validated research evidence for version-sensitive learning plans."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel, Field, model_validator

from .learning_content import SAFE_USER_ID


class ResearchSource(BaseModel):
    id: str = Field(min_length=1, max_length=96, pattern=r"^[A-Za-z0-9_.:-]+$")
    title: str = Field(min_length=1, max_length=300)
    url: str = Field(min_length=8, max_length=2_000)
    kind: str = Field(min_length=1, max_length=64)


class TeachingFact(BaseModel):
    statement: str = Field(min_length=5, max_length=2_000)
    source_ids: list[str] = Field(min_length=1, max_length=12)


class GraduationProject(BaseModel):
    name: str = Field(min_length=2, max_length=300)
    goal: str = Field(min_length=5, max_length=2_000)
    evidence: list[str] = Field(min_length=1, max_length=20)


class ResearchArtifact(BaseModel):
    topic: str = Field(min_length=1, max_length=240)
    researched_at: str = Field(min_length=10, max_length=64)
    version: str = Field(min_length=1, max_length=120)
    sources: list[ResearchSource] = Field(min_length=1, max_length=30)
    teaching_facts: list[TeachingFact] = Field(min_length=1, max_length=60)
    coverage_areas: list[str] = Field(default_factory=list, max_length=60)
    prerequisites: list[str] = Field(default_factory=list, max_length=30)
    graduation_project: str | GraduationProject = ""

    @model_validator(mode="after")
    def validate_references(self) -> "ResearchArtifact":
        source_ids = [source.id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("research source ids must be unique")
        if any(urlparse(source.url).scheme not in {"http", "https"} for source in self.sources):
            raise ValueError("research sources must use http or https")
        known = set(source_ids)
        if any(source_id not in known for fact in self.teaching_facts for source_id in fact.source_ids):
            raise ValueError("teaching facts must reference known sources")
        return self


def research_slug(topic: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", topic.casefold()).strip("-")
    return (slug or "learning-topic")[:64]


def research_path(server_root: Path, user_id: str, topic: str) -> Path:
    if not SAFE_USER_ID.fullmatch(user_id):
        raise ValueError("invalid user_id")
    return server_root / "userdir" / f"u_{user_id}" / "research" / research_slug(topic) / "sources.json"


def load_valid_research(
    server_root: Path,
    user_id: str,
    topic: str,
    *,
    require_deep: bool = False,
) -> ResearchArtifact:
    path = research_path(server_root, user_id, topic)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("research artifact must be an object")
    normalized_sources = []
    for source in raw.get("sources") or []:
        if not isinstance(source, dict):
            continue
        item = dict(source)
        if not item.get("kind"):
            url = str(item.get("url") or "")
            item["kind"] = "official_repo" if "github.com" in url else "official_docs"
        normalized_sources.append(item)
    normalized_facts = []
    for fact in raw.get("teaching_facts") or []:
        if not isinstance(fact, dict):
            continue
        source_ids = fact.get("source_ids", fact.get("source", []))
        if isinstance(source_ids, str):
            source_ids = [source_ids]
        normalized_facts.append({
            "statement": fact.get("statement", fact.get("fact", "")),
            "source_ids": source_ids,
        })
    def string_list(value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in re.split(r"[；;\n]+", value) if item.strip()]
        return []

    graduation = raw.get("graduation_project") or ""
    if isinstance(graduation, dict):
        graduation = {**graduation, "evidence": string_list(graduation.get("evidence"))}
    normalized = {
        **raw,
        "sources": normalized_sources,
        "teaching_facts": normalized_facts,
        "coverage_areas": string_list(raw.get("coverage_areas")),
        "prerequisites": string_list(raw.get("prerequisites")),
        "graduation_project": graduation,
    }
    artifact = ResearchArtifact.model_validate(normalized)
    def topic_key(value: str) -> str:
        # 研究产物可以有展示用的路线标签，但不能悄悄换成另一个主题。
        without_qualifiers = re.sub(r"[（(][^）)]*[）)]", "", value.casefold())
        key = re.sub(r"[\s\W_]+", "", without_qualifiers)
        return re.sub(r"(?:工程师|开发者|语言|课程|学习|是什么)$", "", key)
    if topic_key(artifact.topic) != topic_key(topic):
        raise ValueError("research topic does not match the learning plan")
    artifact = artifact.model_copy(update={"topic": topic})
    if require_deep:
        if len(artifact.coverage_areas) < 5:
            raise ValueError("deep research must cover at least five capability areas")
        if isinstance(artifact.graduation_project, str):
            has_project = bool(artifact.graduation_project.strip())
        else:
            has_project = bool(artifact.graduation_project.name.strip() and artifact.graduation_project.evidence)
        if not has_project:
            raise ValueError("deep research must recommend a graduation project")
    canonical = path.with_suffix(".json.tmp")
    canonical.write_text(artifact.model_dump_json(indent=2) + "\n", encoding="utf-8")
    canonical.replace(path)
    return artifact


def render_research_evidence(artifact: ResearchArtifact) -> str:
    """Render bounded, source-linked facts for a lesson-generation prompt."""
    source_titles = {source.id: source.title for source in artifact.sources}
    lines = [
        f"研究版本：{artifact.version}",
        f"覆盖领域：{'、'.join(artifact.coverage_areas) or '按本章知识点'}",
        f"必要先修：{'、'.join(artifact.prerequisites) or '无额外先修'}",
    ]
    if artifact.graduation_project:
        if isinstance(artifact.graduation_project, str):
            lines.append(f"毕业项目建议：{artifact.graduation_project}")
        else:
            project = artifact.graduation_project
            lines.append(f"毕业项目建议：{project.name}；目标：{project.goal}")
            lines.append(f"毕业项目证据：{'、'.join(project.evidence)}")
    for fact in artifact.teaching_facts[:30]:
        sources = "、".join(
            f"{source_id}:{source_titles.get(source_id, source_id)}"
            for source_id in fact.source_ids
        )
        lines.append(f"- {fact.statement}（来源 {sources}）")
    return "\n".join(lines)
