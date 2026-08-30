"""Regression for the 20260830-200459 model response's knowledge-list wrapper."""
import pytest

from backend.curriculum import curriculum_from_plan
from backend.learning_plan_personalizer import normalize_and_validate_plan


def plan(*, points=2, stages=12):
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
    return header + "\n".join(
        f"### 阶段 {i}：{'毕业项目交付' if i == stages else '工程能力练习'}\n"
        "- #### 知识点\n"
        + "".join(f"  - Go 原子能力 {i}.{j}：说明输入输出和错误边界。\n" for j in range(1, points + 1))
        + "- 本阶段要学：掌握本阶段能力并应用到真实的小型程序中。\n"
        "- 练习：独立实现、测试并调试正常与错误路径。\n"
        "- 完成证据：运行结果匹配预期，能够解释边界并修改行为。\n"
        "- 预计课次：2\n"
        for i in range(1, stages + 1)
    )


def test_exact_model_knowledge_list_wrapper_normalizes_without_losing_points():
    normalized = normalize_and_validate_plan(plan(), "Go", "foundation_engineer")
    assert normalized is not None
    assert "- #### 知识点" not in normalized
    assert normalized.count("\n#### 知识点\n") == 12
    curriculum = curriculum_from_plan(normalized, topic="Go", route="foundation_engineer", level="zero")
    assert len(curriculum.chapters) == 12
    assert all(len(chapter.knowledge_points) == 2 for chapter in curriculum.chapters)
    assert "Go 原子能力 1.1" in curriculum.chapters[0].knowledge_points[0].title


@pytest.mark.parametrize("invalid", [
    plan(points=1),
    plan(stages=11),
    plan().replace("## 知识覆盖地图", "## 普通说明"),
    plan().replace("- #### 知识点", "- #### 可选说明"),
])
def test_list_wrapper_does_not_relax_required_coverage_or_structure(invalid):
    assert normalize_and_validate_plan(invalid, "Go", "foundation_engineer") is None
