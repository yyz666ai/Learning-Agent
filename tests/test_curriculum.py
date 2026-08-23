from __future__ import annotations

from pathlib import Path

import pytest

from backend.curriculum import (
    Curriculum,
    curriculum_from_plan,
    load_curriculum,
    render_curriculum_plan,
    save_curriculum,
)


GO_PLAN = """# Go 学习计划

### 阶段 1：程序结构与运行
- 本阶段要学：package main；func main；go run 与 go build
- 练习：运行 hello.go
- 完成证据：能解释编译和运行

### 阶段 2：变量与类型
- 本阶段要学：var 与 :=；string、int 和 bool；fmt.Printf
- 练习：完成个人资料程序
- 完成证据：预测输出正确

### 阶段 3：控制流
- 本阶段要学：if 判断；for 循环；break 与 continue
- 练习：完成猜数字
- 完成证据：能解释循环终止条件

### 阶段 4：函数与错误
- 本阶段要学：参数与返回值；error 惯例
- 练习：拆分函数并处理错误
- 完成证据：错误输入不会崩溃

### 阶段 5：结构体与项目
- 本阶段要学：slice；map；struct；go test
- 练习：完成命令行待办项目
- 完成证据：测试通过
"""


JAVA_PLAN = GO_PLAN.replace("Go 学习计划", "Java 学习计划").replace(
    "package main；func main；go run 与 go build",
    "JDK 与 JVM；class 与 main；javac 与 java",
).replace("hello.go", "Hello.java").replace("var 与 :=", "变量声明与基本类型").replace(
    "slice；map；struct；go test", "List；Map；class；JUnit"
)


def test_model_plan_becomes_topic_specific_chapters_and_knowledge_points() -> None:
    go = curriculum_from_plan(GO_PLAN, topic="Go", route="foundation_engineer", level="zero")
    java = curriculum_from_plan(JAVA_PLAN, topic="Java", route="foundation_engineer", level="experienced")

    assert len(go.chapters) == 5
    assert len(go.knowledge_points()) >= 12
    assert go.current_knowledge_point_id == go.knowledge_points()[0].id
    assert any("go-run" in item.id or "go-build" in item.id for item in go.knowledge_points())
    assert any("jdk" in item.id or "jvm" in item.id for item in java.knowledge_points())
    assert {item.title for item in go.knowledge_points()} != {item.title for item in java.knowledge_points()}
    assert java.level == "experienced"


def test_curriculum_renders_a_detailed_readable_plan() -> None:
    curriculum = curriculum_from_plan(GO_PLAN, topic="Go", route="foundation_engineer", level="zero")

    rendered = render_curriculum_plan(curriculum)

    assert "## 课程地图" in rendered
    assert rendered.count("### 第") == 5
    assert rendered.count("#### ") >= 12
    assert "完成标准" in rendered


def test_curriculum_round_trip_is_confined_to_learner_folder(tmp_path: Path) -> None:
    curriculum = curriculum_from_plan(GO_PLAN, topic="Go", route="foundation_engineer", level="zero")

    path = save_curriculum(tmp_path, "learner", curriculum)

    assert path == tmp_path / "userdir/u_learner/curriculum.json"
    assert load_curriculum(tmp_path, "learner") == curriculum
    with pytest.raises(ValueError):
        save_curriculum(tmp_path, "../outside", curriculum)


def test_curriculum_rejects_a_plan_without_enough_concrete_content() -> None:
    with pytest.raises(ValueError, match="knowledge points"):
        curriculum_from_plan(
            "# Java 学习计划\n\n### 阶段 1：基础\n- 本阶段要学：基础\n",
            topic="Java",
            route="foundation_engineer",
            level="zero",
        )


def test_concept_clarity_accepts_a_short_single_concept_curriculum() -> None:
    plan = """# RAG 是什么 概念速学

### 阶段 1：建立直觉
- 本阶段要学：RAG 如何先检索资料再组织回答
- 练习：用一道点击题区分 RAG 与纯模型回答
- 完成证据：能判断一个例子是否用了 RAG
"""

    curriculum = curriculum_from_plan(
        plan, topic="RAG 是什么", route="concept_clarity", level="zero",
    )

    assert len(curriculum.chapters) == 1
    assert len(curriculum.knowledge_points()) == 1


def test_curriculum_keeps_semicolons_inside_code_as_one_knowledge_point() -> None:
    plan = GO_PLAN.replace(
        "if 判断；for 循环；break 与 continue",
        "`if` 判断；`for i := 0; i < n; i++` 计数循环；`for range` 遍历",
    )

    curriculum = curriculum_from_plan(
        plan, topic="Go", route="foundation_engineer", level="zero",
    )

    titles = [point.title for point in curriculum.knowledge_points()]
    assert "`for i := 0; i < n; i++` 计数循环" in titles
    assert not any(title in {"i < n", "i++` 计数循环"} for title in titles)
    assert "`if` 判断" in titles
