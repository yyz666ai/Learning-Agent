"""Equivalent explicit knowledge formats must not degrade to learning goals."""

from pathlib import Path

import pytest

from backend.curriculum import curriculum_from_plan
from backend.learning_plan_personalizer import normalize_and_validate_plan
from tests.test_plan_list_wrapper import plan


def short_plan(knowledge):
    return (
        "# Go 学习计划\n## 学习成果\n独立启动并等待任务结束。\n"
        "## 教学策略\n观察、预测、编写并验证正常与错误路径。\n"
        "## 当前任务\n编写并运行一个并发任务。\n"
        "### 阶段 1：并发等待\n"
        + knowledge
        + "- 本阶段要学：能启动并等待多个任务，解释谁负责结束。\n"
        "- 练习：编写任务并观察输出，故意去掉等待再检查变化。\n"
        "- 完成证据：输出完整并能够解释任务启动及结束的顺序。\n"
        "- 预计课次：1\n"
    )


@pytest.mark.parametrize("knowledge", [
    "- 必要知识点：goroutine 启动、sync.WaitGroup、主函数等待、goroutine 泄漏入口。\n",
    "- 必要知识点：\n  - goroutine 启动\n  - sync.WaitGroup\n  - 主函数等待\n  - goroutine 泄漏入口\n",
])
def test_explicit_required_knowledge_is_preferred_to_goal_fallback(knowledge):
    source = short_plan(knowledge)
    expected = ["goroutine 启动", "sync.WaitGroup", "主函数等待", "goroutine 泄漏入口"]
    for content in [source, normalize_and_validate_plan(source, "Go", "concept_clarity")]:
        assert content is not None
        curriculum = curriculum_from_plan(content, topic="Go", route="concept_clarity", level="experienced")
        assert [point.title for point in curriculum.chapters[0].knowledge_points] == expected


def test_inline_enumeration_preserves_compounds_parentheses_and_inline_code():
    source = short_plan("- 必要知识点：发送与接收阻塞；调用（位置、关键字参数）；`fmt.Print(a; b)`、关闭职责。\n")
    normalized = normalize_and_validate_plan(source, "Go", "concept_clarity")
    assert normalized is not None
    curriculum = curriculum_from_plan(normalized, topic="Go", route="concept_clarity", level="experienced")
    assert [p.title for p in curriculum.chapters[0].knowledge_points] == [
        "发送与接收阻塞", "调用（位置、关键字参数）", "`fmt.Print(a; b)`", "关闭职责",
    ]


def test_complete_plan_missing_only_display_title_is_recovered():
    source = plan(position="end").split("\n", 1)[1].replace("### 阶段", "## 阶段").replace("- #### 知识点", "- 必要知识点：")
    normalized = normalize_and_validate_plan(source, "Go")
    assert normalized is not None and normalized.startswith("# Go 学习计划\n")
    curriculum = curriculum_from_plan(normalized, topic="Go", route="foundation_engineer", level="zero")
    assert len(curriculum.chapters) == 12
    assert all(len(c.knowledge_points) == 2 for c in curriculum.chapters)


@pytest.mark.parametrize("mutation", [
    lambda text: text.replace("Go", "Python"),
    lambda text: text.replace("## 当前任务", "## 其他内容"),
    lambda text: text.replace("- 完成证据：", "- 其他字段："),
    lambda text: text.replace("## 知识覆盖地图", "## 普通说明"),
])
def test_display_title_recovery_does_not_fill_missing_plan_content(mutation):
    source = plan().split("\n", 1)[1]
    assert normalize_and_validate_plan(mutation(source), "Go") is None


def test_necessary_knowledge_format_keeps_comprehensive_minimum():
    assert normalize_and_validate_plan(plan(points=1).replace("- #### 知识点", "- 必要知识点："), "Go") is None


def test_necessary_knowledge_normalization_preserves_fences_prose_and_fields():
    diagram = "```mermaid\n- 必要知识点：图中一、图中二\n```\n"
    source = short_plan("- 必要知识点：甲、乙\n  保留说明。\n").replace("## 当前任务\n", "## 当前任务\n" + diagram)
    normalized = normalize_and_validate_plan(source, "Go", "concept_clarity")
    assert normalized is not None
    assert diagram in normalized
    assert "\n  保留说明。\n- 本阶段要学：" in normalized
    assert "#### 知识点\n- 甲\n- 乙\n" in normalized


def test_runtime_template_exposes_explicit_atomic_knowledge_to_curriculum():
    template = Path("workspace/dev/.codex/skills/learning-plan/assets/learning-plan-template.md").read_text()
    filled = template.replace("{目标名称}", "Go").replace("{原子知识点一}", "goroutine 启动").replace("{原子知识点二}", "sync.WaitGroup")
    curriculum = curriculum_from_plan(filled, topic="Go", route="concept_clarity", level="experienced")
    assert [p.title for p in curriculum.chapters[0].knowledge_points] == ["goroutine 启动", "sync.WaitGroup"]
