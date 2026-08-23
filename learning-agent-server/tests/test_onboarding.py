import json
from pathlib import Path

import pytest
from jsonschema import validate

from backend.onboarding import (
    DiagnosisSummary,
    OnboardingSubmission,
    confirm_onboarding,
    needs_diagnosis,
    render_plan,
)
from backend.learning_plan_personalizer import build_plan_prompt, normalize_and_validate_plan


def submission(
    user_id: str = "learner",
    level: str = "some",
    topic: str = "go",
    goal_route: str = "foundation_engineer",
):
    return OnboardingSubmission(
        user_id=user_id,
        learning_mode="systematic",
        goal_route=goal_route,
        level_claim=level,
        topic={"type": "go" if topic == "go" else "custom", "value": topic},
    )


@pytest.mark.parametrize(
    ("route", "marker"),
    [
        ("concept_clarity", "先建立准确直觉，再决定是否查看代码实现"),
        ("foundation_engineer", "完整学习、复习、实战与阶段验收"),
        ("urgent_codebase", "优先入口、调用链和关键文件"),
        ("syntax_reading", "优先语法辨析和代码阅读"),
        ("project_delivery", "真实文件、运行结果和测试"),
        ("gap_upgrade", "已掌握内容快进"),
        ("senior_engineer", "架构取舍、可靠性和重构"),
        ("interview_sprint", "简答、追问和代码推演"),
    ],
)
def test_plan_contains_route_strategy(route, marker):
    plan = render_plan(
        submission(level="zero", goal_route=route),
        diagnosis=None,
        knowledge_source="knowledge_base",
    )

    assert marker in plan


def test_plan_records_daily_time_and_deadline():
    selected = submission(level="zero", goal_route="urgent_codebase")
    selected.session_minutes = 45
    selected.deadline_days = 2

    plan = render_plan(selected, diagnosis=None, knowledge_source="knowledge_base")

    assert "每天 45 分钟" in plan
    assert "截止：2 天" in plan


def test_concept_clarity_plan_is_short_and_does_not_claim_a_daily_schedule():
    selected = submission(level="zero", topic="RAG 是什么", goal_route="concept_clarity")
    selected.concept_scope = "meaning_only"

    plan = render_plan(selected, diagnosis=None, knowledge_source="skill_guided")

    assert "每天" not in plan
    assert 1 <= plan.count("### 阶段") <= 3
    assert "先讲懂它是什么" in plan


def test_concept_clarity_skips_diagnosis_regardless_of_claimed_level():
    selected = submission(level="experienced", topic="RAG 是什么", goal_route="concept_clarity")
    selected.concept_scope = "code_walkthrough"

    assert needs_diagnosis(selected) is False


@pytest.mark.parametrize(
    "route",
    [
        "concept_clarity",
        "foundation_engineer", "urgent_codebase", "syntax_reading",
        "project_delivery", "gap_upgrade", "senior_engineer", "interview_sprint",
    ],
)
def test_fallback_plan_is_specific_and_actionable_for_every_route(route):
    selected = submission(level="zero", topic="FastAPI 发 API", goal_route=route)
    plan = render_plan(selected, diagnosis=None, knowledge_source="skill_guided")

    assert "# FastAPI 发 API 学习计划" in plan
    assert "## 学习成果" in plan
    minimum = 1 if route == "concept_clarity" else 5
    assert plan.count("### 阶段") >= minimum
    assert plan.count("- 本阶段要学：") >= minimum
    assert plan.count("- 练习：") >= minimum
    assert plan.count("- 完成证据：") >= minimum


def test_zero_beginner_skips_diagnosis():
    assert needs_diagnosis(submission(level="zero")) is False


def test_experienced_learner_needs_diagnosis():
    assert needs_diagnosis(submission(level="some")) is True
    assert needs_diagnosis(submission(level="experienced")) is True


def test_confirm_onboarding_writes_resolvable_plan(tmp_path):
    diagnosis = DiagnosisSummary(
        estimated_level="foundation",
        score=0.67,
        answered_count=3,
        strengths=["能识别基本语法"],
        gaps=["并发心智模型"],
    )
    result = confirm_onboarding(tmp_path, submission(), diagnosis=diagnosis)
    user_dir = tmp_path / "userdir" / "u_learner"
    state = json.loads((user_dir / "learning-state.json").read_text(encoding="utf-8"))

    assert state["profile_status"] == "confirmed"
    assert state["active_plan"].startswith("plans/")
    assert (user_dir / state["active_plan"]).is_file()
    assert result["first_lesson"]["start_immediately"] is False
    assert result["first_lesson"]["forbid_more_onboarding"] is True
    assert state["diagnosis"]["strengths"] == ["能识别基本语法"]
    assert state["diagnosis"]["gaps"] == ["并发心智模型"]


def test_complete_mastery_plan_rejects_shallow_outline_and_accepts_detailed_capstone():
    shallow = """# Go 学习计划

## 当前任务
学习 Go。

## 学习成果
会写 Go。

## 教学策略
边学边练。

""" + "\n\n".join(
        f"### 阶段 {index}：阶段 {index}\n- 本阶段要学：Go 知识 {index}\n- 练习：练习 {index}\n- 完成证据：完成 {index}"
        for index in range(1, 6)
    )

    detailed = """# Go 从零到工程师学习计划

## 当前任务
先建立运行环境和程序执行直觉。

## 学习成果
能够独立设计、实现、测试、调试和交付 Go 服务。

## 教学策略
从直觉到工程，课堂检查、课后独立练习和延迟复习结合。

## 知识覆盖地图
- 语言与运行时
- 数据与控制流
- 调试与测试
- 工程结构、性能和安全

## 最终达成标准
- 能在陌生需求下独立完成设计、实现、测试、调试和复盘。

## 毕业项目
独立完成一个包含 API、持久化、并发任务、可观测性、测试和部署说明的 Go 服务。

""" + "\n\n".join(
        f"### 阶段 {index}：{'毕业项目交付' if index == 12 else f'具体能力 {index}'}\n"
        "#### 知识点\n"
        f"- Go 原子知识 {index}.1\n"
        f"- Go 原子知识 {index}.2\n"
        f"- 本阶段要学：围绕能力 {index} 建立可迁移理解\n"
        f"- 练习：完成阶段任务 {index}\n"
        f"- 完成证据：留下独立产出 {index}\n"
        "- 预计课次：2"
        for index in range(1, 13)
    )

    assert normalize_and_validate_plan(shallow, "Go", "foundation_engineer") is None
    assert normalize_and_validate_plan(detailed, "Go", "foundation_engineer") is not None


def test_complete_mastery_plan_prompt_uses_diagnosis_and_requires_research_even_for_known_topic():
    selected = submission(level="some", topic="go", goal_route="foundation_engineer")
    diagnosis = DiagnosisSummary(
        estimated_level="foundation",
        score=0.67,
        answered_count=3,
        strengths=["syntax"],
        gaps=["concurrency", "debugging"],
    )

    prompt = build_plan_prompt(
        selected,
        render_plan(selected, diagnosis, "knowledge_base"),
        "knowledge_base",
        diagnosis=diagnosis,
    )

    assert "concurrency" in prompt and "debugging" in prompt
    assert "tools/web_search.py" in prompt
    assert "先检查已有" in prompt
    assert "不重复搜索" in prompt
    assert "知识覆盖地图" in prompt
    assert "毕业项目" in prompt
    assert "Plan 不承载教学代码" in prompt


def test_plan_rejects_programming_code_that_should_be_taught_in_lesson_pages():
    plan = """# RAG 概念学习计划

## 当前任务
确认计划后开始第一课。

```python
print("RAG")
```

## 学习成果
能解释 RAG。

## 教学策略
用图示和点击题。

### 阶段 1：建立直觉
- 本阶段要学：RAG 的信息流
- 练习：点击判断场景
- 完成证据：选对适用场景
"""

    assert normalize_and_validate_plan(plan, "RAG", "concept_clarity") is None


def test_concept_scope_is_persisted_for_skills_to_read(tmp_path):
    selected = submission(level="zero", topic="RAG 是什么", goal_route="concept_clarity")
    selected.concept_scope = "meaning_only"

    confirm_onboarding(tmp_path, selected, diagnosis=None)
    user_dir = tmp_path / "userdir/u_learner"
    state = json.loads((user_dir / "learning-state.json").read_text(encoding="utf-8"))
    profile = (user_dir / "profile.md").read_text(encoding="utf-8")

    assert state["concept_scope"] == "meaning_only"
    assert "概念范围：只理解概念" in profile


def test_validated_plan_hides_internal_user_directory_paths():
    plan = """# RAG 是什么 概念速学

> 资料见 `$USER_DIR/research/rag/sources.json`

## 当前任务
先理解 RAG 的用途。

## 学习成果
能判断适用场景。

## 教学策略
比喻与点击题。

### 阶段 1：建立直觉
- 本阶段要学：RAG 先检索后生成的核心流程
- 练习：点击判断适用场景
- 完成证据：能选对并看懂反馈
"""

    validated = normalize_and_validate_plan(plan, "RAG 是什么", "concept_clarity")

    assert validated is not None
    assert "$USER_DIR" not in validated
    assert "已核对的资料来源" in validated


def test_known_topic_uses_knowledge_base(tmp_path):
    result = confirm_onboarding(tmp_path, submission(level="zero"), diagnosis=None)
    assert result["knowledge_source"] == "knowledge_base"


def test_missing_knowledge_uses_skill_guided_plan(tmp_path):
    result = confirm_onboarding(
        tmp_path,
        submission(level="zero", topic="webhook retry API"),
        diagnosis=None,
    )
    assert result["knowledge_source"] == "skill_guided"
    assert result["first_lesson"]["start_immediately"] is False


def test_unsafe_user_id_is_rejected(tmp_path):
    unsafe = submission(user_id="../outside", level="zero")
    try:
        confirm_onboarding(tmp_path, unsafe, diagnosis=None)
    except ValueError as exc:
        assert "user_id" in str(exc)
    else:
        raise AssertionError("unsafe user id should fail")


def test_project_topic_preserves_detectable_language(tmp_path):
    project = OnboardingSubmission(
        user_id="python-project",
        learning_mode="project",
        level_claim="some",
        topic={"type": "project", "value": "Python 后端 API 项目"},
    )
    diagnosis = DiagnosisSummary(
        estimated_level="foundation",
        score=0.5,
        answered_count=4,
    )

    confirm_onboarding(tmp_path, project, diagnosis)
    state = json.loads(
        (tmp_path / "userdir/u_python-project/learning-state.json").read_text(encoding="utf-8")
    )

    assert state["active_language"] == "python"


def test_confirmed_state_matches_workspace_schema(tmp_path):
    confirm_onboarding(tmp_path, submission(level="zero"), diagnosis=None)
    state = json.loads(
        (tmp_path / "userdir/u_learner/learning-state.json").read_text(encoding="utf-8")
    )
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "workspace/dev/memory/schemas/learning-state.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    validate(state, schema)
    assert state["revision"] == 1
    assert state["updated_at"]


def test_non_language_topic_uses_null_language_in_persisted_state(tmp_path):
    confirm_onboarding(
        tmp_path,
        submission(level="zero", topic="webhook retry API"),
        diagnosis=None,
    )
    state = json.loads(
        (tmp_path / "userdir/u_learner/learning-state.json").read_text(encoding="utf-8")
    )

    assert state["active_language"] is None
