"""Regression for the 20260830-200459 model response's knowledge-list wrapper."""
import pytest

from backend.curriculum import curriculum_from_plan
from backend.learning_plan_personalizer import normalize_and_validate_plan


def plan(*, points=2, stages=12, position="start"):
    header = """# Go 工程学习计划
## 当前任务
建立目录，检查工具版本，运行第一个程序。
## 学习成果
独立实现、调试和测试服务，解释数据与错误如何流动。
## 教学策略
从小程序开始独立练习，保留每次运行证据，再迁移到陌生需求。
## 知识覆盖地图
语言基础、数据结构、资源、并发、网络、测试与项目交付。
## 最终达成标准
独立设计并交付可测试的 Go 服务，说明边界和工程取舍。
## 毕业项目
交付包含持久化、并发、HTTP 接口、测试和运行说明的服务。
"""
    sections = []
    for i in range(1, stages + 1):
        knowledge = "- #### 知识点\n" + "".join(
            f"  - Go 原子能力 {i}.{j}：说明输入输出和错误边界。\n"
            for j in range(1, points + 1)
        )
        fields = [
            "- 本阶段要学：掌握本阶段能力并应用到真实的小型程序中。\n",
            "- 练习：独立实现、测试并调试正常与错误路径。\n",
            "- 完成证据：运行结果匹配预期，能够解释边界并修改行为。\n",
            "- 预计课次：2\n",
        ]
        fields.insert({"start": 0, "middle": 1, "before_budget": 3, "end": 4}[position], knowledge)
        sections.append(
            f"### 阶段 {i}：{'毕业项目交付' if i == stages else '工程能力练习'}\n"
            + "".join(fields)
        )
    return header + "\n".join(sections)


def test_exact_model_knowledge_list_wrapper_normalizes_without_losing_points():
    normalized = normalize_and_validate_plan(plan(), "Go", "foundation_engineer")
    assert normalized is not None
    assert "- #### 知识点" not in normalized
    assert normalized.count("\n#### 知识点\n") == 12
    curriculum = curriculum_from_plan(normalized, topic="Go", route="foundation_engineer", level="zero")
    assert len(curriculum.chapters) == 12
    assert all(len(chapter.knowledge_points) == 2 for chapter in curriculum.chapters)
    assert "Go 原子能力 1.1" in curriculum.chapters[0].knowledge_points[0].title


def test_plain_learning_plan_title_can_be_promoted_without_inventing_content():
    source = plan().replace("# Go 工程学习计划", "学习计划：Go 工程学习计划", 1)
    normalized = normalize_and_validate_plan(source, "Go")
    assert normalized is not None and normalized.startswith("# 学习计划：Go 工程学习计划")


def test_unknown_plain_preamble_is_not_accepted_as_a_plan_title():
    assert normalize_and_validate_plan(plan().replace("# Go 工程学习计划", "Go 随便学学"), "Go") is None


def test_template_metadata_after_knowledge_does_not_become_knowledge():
    source = plan().replace("- 预计课次：2", "- 预计课次：2")
    source = source.replace("- 本阶段要学：", "- 为什么现在学：这是先修\n- 必要知识点：章节说明\n- 真实产出：练习\n- 验收方式：运行\n- 本阶段要学：")
    normalized = normalize_and_validate_plan(source, "Go")
    assert normalized is not None
    curriculum = curriculum_from_plan(normalized, topic="Go", route="foundation_engineer", level="zero")
    assert all(len(chapter.knowledge_points) == 2 for chapter in curriculum.chapters)


@pytest.mark.parametrize("invalid", [
    plan(points=1),
    plan(stages=11),
    plan().replace("## 知识覆盖地图", "## 普通说明"),
    plan().replace("- #### 知识点", "- #### 可选说明"),
])
def test_list_wrapper_does_not_relax_required_coverage_or_structure(invalid):
    assert normalize_and_validate_plan(invalid, "Go", "foundation_engineer") is None


@pytest.mark.parametrize("position", ["middle", "before_budget", "end"])
@pytest.mark.parametrize("trailing_newline", [True, False])
def test_knowledge_wrapper_is_position_independent(position, trailing_newline):
    source = plan(position=position)
    if not trailing_newline:
        source = source.rstrip("\n")
    normalized = normalize_and_validate_plan(source, "Go", "foundation_engineer")
    assert normalized is not None
    expected = source.replace("- #### 知识点", "#### 知识点").replace("  - Go 原子能力", "- Go 原子能力")
    assert normalized == expected.rstrip("\n") + "\n"
    curriculum = curriculum_from_plan(normalized, topic="Go", route="foundation_engineer", level="zero")
    assert all(len(chapter.knowledge_points) == 2 for chapter in curriculum.chapters)
    assert all(point.title.startswith("Go 原子能力") for chapter in curriculum.chapters for point in chapter.knowledge_points)


@pytest.mark.parametrize("position", ["start", "middle", "before_budget", "end"])
@pytest.mark.parametrize("points", [0, 1])
def test_stage_fields_never_substitute_for_missing_knowledge(position, points):
    assert normalize_and_validate_plan(plan(position=position, points=points), "Go", "foundation_engineer") is None


@pytest.mark.parametrize("replacement", [
    "- #### 知识点补充",
    "- #### 知识点\n  这里是说明，不是知识点列表。",
])
def test_only_exact_heading_with_immediate_indented_bullets_is_unwrapped(replacement):
    source = plan(position="end").replace("- #### 知识点", replacement)
    assert normalize_and_validate_plan(source, "Go", "foundation_engineer") is None


def test_normalization_preserves_prose_after_knowledge():
    source = plan(position="end").replace("\n\n###", "\n  保留这段说明及其缩进。\n\n###")
    normalized = normalize_and_validate_plan(source, "Go", "foundation_engineer")
    assert normalized is not None
    assert normalized.count("\n  保留这段说明及其缩进。\n") == 11


def test_prose_and_its_list_do_not_supply_missing_knowledge():
    source = plan(points=1, position="end").replace(
        "说明输入输出和错误边界。\n",
        "说明输入输出和错误边界。\n说明文字。\n- 这是说明的列表项。\n",
    )
    assert normalize_and_validate_plan(source, "Go", "foundation_engineer") is None


def test_knowledge_wrapper_inside_mermaid_is_unchanged():
    diagram = "```mermaid\n- #### 知识点\n  - 图中说明一\n  - 图中说明二\n- 本阶段要学：图中内容\n```\n"
    source = plan().replace("## 当前任务\n", "## 当前任务\n" + diagram)
    normalized = normalize_and_validate_plan(source, "Go", "foundation_engineer")
    assert normalized is not None
    assert diagram in normalized


def test_non_mermaid_code_fences_remain_rejected():
    source = plan() + "\n```text\n- #### 知识点\n  - 一\n  - 二\n```\n"
    assert normalize_and_validate_plan(source, "Go", "foundation_engineer") is None
