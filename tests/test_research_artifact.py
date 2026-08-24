from __future__ import annotations

import json

import pytest

from backend.research_artifact import load_valid_research, render_research_evidence, research_path


def test_common_agent_aliases_are_canonicalized_without_losing_sources(tmp_path) -> None:
    path = research_path(tmp_path, "learner", "LangGraph")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "topic": "LangGraph",
        "researched_at": "2026-08-21",
        "version": "1.2.11",
        "sources": [{"id": "official", "title": "官方文档", "url": "https://docs.langchain.com/oss/python/langgraph/overview"}],
        "teaching_facts": [{"fact": "LangGraph 用图组织有状态 Agent。", "source": ["official"]}],
    }, ensure_ascii=False), encoding="utf-8")

    artifact = load_valid_research(tmp_path, "learner", "LangGraph")
    saved = json.loads(path.read_text(encoding="utf-8"))

    assert artifact.sources[0].kind == "official_docs"
    assert saved["teaching_facts"][0]["statement"] == "LangGraph 用图组织有状态 Agent。"
    assert saved["teaching_facts"][0]["source_ids"] == ["official"]


def test_deep_research_keeps_coverage_prerequisites_and_graduation_project(tmp_path) -> None:
    path = research_path(tmp_path, "learner", "Go")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "topic": "Go",
        "researched_at": "2026-08-21",
        "version": "1.25",
        "sources": [{"id": "spec", "title": "Go Specification", "url": "https://go.dev/ref/spec", "kind": "official_docs"}],
        "teaching_facts": [{"statement": "Go 规范定义语言语法与类型系统。", "source_ids": ["spec"]}],
        "coverage_areas": ["语言基础", "并发", "测试", "性能", "工程交付"],
        "prerequisites": ["命令行基础"],
        "graduation_project": "实现并交付一个带并发任务、测试和可观测性的 Go 服务",
    }, ensure_ascii=False), encoding="utf-8")

    artifact = load_valid_research(tmp_path, "learner", "Go")

    assert "并发" in artifact.coverage_areas
    assert artifact.prerequisites == ["命令行基础"]
    assert "Go 服务" in artifact.graduation_project


def test_deep_research_accepts_structured_graduation_project_from_agent(tmp_path) -> None:
    path = research_path(tmp_path, "learner", "Go")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "topic": "Go",
        "researched_at": "2026-08-21",
        "version": "1.27",
        "sources": [{"id": "docs", "title": "Go Documentation", "url": "https://go.dev/doc/"}],
        "teaching_facts": [{"statement": "Go 官方文档给出完整工具链入口。", "source_ids": ["docs"]}],
        "coverage_areas": ["语言基础", "并发", "测试", "性能", "工程交付"],
        "prerequisites": ["可以使用命令行"],
        "graduation_project": {
            "name": "Go 记账工作台",
            "goal": "交付 CLI 和 HTTP 接口",
            "evidence": ["测试全绿", "完成安全扫描"],
        },
    }, ensure_ascii=False), encoding="utf-8")

    artifact = load_valid_research(tmp_path, "learner", "Go", require_deep=True)
    rendered = render_research_evidence(artifact)

    assert artifact.graduation_project.name == "Go 记账工作台"
    assert "测试全绿" in rendered


def test_deep_research_normalizes_common_agent_string_lists(tmp_path) -> None:
    path = research_path(tmp_path, "learner", "Go")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "topic": "Go",
        "researched_at": "2026-08-22",
        "version": "1.27",
        "sources": [{"id": "docs", "title": "Go Documentation", "url": "https://go.dev/doc/"}],
        "teaching_facts": [{"statement": "Go 官方资料覆盖语言与工具链。", "source_ids": ["docs"]}],
        "coverage_areas": ["语言", "并发", "测试", "性能", "工程"],
        "prerequisites": "会使用终端；能够安装 Go",
        "graduation_project": {
            "name": "Go 学习服务",
            "goal": "交付一个可运行的服务",
            "evidence": "测试通过；安全扫描通过",
        },
    }, ensure_ascii=False), encoding="utf-8")

    artifact = load_valid_research(tmp_path, "learner", "Go", require_deep=True)

    assert artifact.prerequisites == ["会使用终端", "能够安装 Go"]
    assert artifact.graduation_project.evidence == ["测试通过", "安全扫描通过"]


def test_research_topic_accepts_only_display_qualifiers_and_is_canonicalized(tmp_path) -> None:
    path = research_path(tmp_path, "learner", "AI前端")
    path.parent.mkdir(parents=True)
    payload = {
        "topic": "AI前端工程师（面试冲刺 · 零基础 · meaning_only）",
        "researched_at": "2026-08-24",
        "version": "current",
        "sources": [{"id": "docs", "title": "AI SDK", "url": "https://ai-sdk.dev/docs/introduction", "kind": "official_docs"}],
        "teaching_facts": [{"statement": "AI SDK 支持流式 AI 界面。", "source_ids": ["docs"]}],
        "coverage_areas": ["前端基础", "模型 API", "流式交互", "安全", "面试表达"],
        "prerequisites": ["JavaScript"],
        "graduation_project": "完成 AI 前端模拟面试",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    artifact = load_valid_research(tmp_path, "learner", "AI前端", require_deep=True)

    assert artifact.topic == "AI前端"
    assert json.loads(path.read_text(encoding="utf-8"))["topic"] == "AI前端"

    payload["topic"] = "AI后端工程师（面试冲刺）"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        load_valid_research(tmp_path, "learner", "AI前端", require_deep=True)
