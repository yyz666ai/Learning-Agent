"""The prepared route template must satisfy the same contract as validation."""

import json
import re
import shutil
from pathlib import Path

import pytest

from backend.generation_context import prepare_generation_context
from backend.learning_plan_personalizer import COMPREHENSIVE_ROUTES, normalize_and_validate_plan


RELEASE = Path(__file__).resolve().parents[1] / "workspace/dev"
TEMPLATE = ".codex/skills/learning-plan/assets/learning-plan-template.md"
COMPREHENSIVE_HEADINGS = ("## 知识覆盖地图", "## 最终达成标准", "## 毕业项目")


def prepared_template(tmp_path, route):
    (tmp_path / "learning-state.json").write_text(json.dumps({"active_topic": "Go", "goal_route": route}))
    context = prepare_generation_context(RELEASE, tmp_path, "plan", "生成课程", False)
    return context.split(f"【规则 {TEMPLATE}】\n", 1)[1].split("\n【", 1)[0].strip()


def completed_plan(template):
    template = template.replace("{目标名称}", "Go 工程学习")
    template = re.sub(r"\{[^{}]+\}", "解释并实现可运行的模块，验证正常与错误边界", template)
    template = re.sub(r"(?m)(^- [^\n]+：)$", r"\1独立编写、运行、解释和测试模块并保留执行结果", template)
    start, end = template.index("### 阶段 1"), template.index("## 当前任务")
    stage = template[start:end]
    stages = [stage.replace("### 阶段 1：", f"### 阶段 {i}：") for i in range(1, 13)]
    stages[-1] = stages[-1].replace("### 阶段 12：", "### 阶段 12：毕业项目交付——")
    return template[:start] + "\n".join(stages) + template[end:]


@pytest.mark.parametrize("route", sorted(COMPREHENSIVE_ROUTES))
def test_prepared_comprehensive_template_satisfies_strict_plan_contract(tmp_path, route):
    template = prepared_template(tmp_path, route)
    for heading in COMPREHENSIVE_HEADINGS:
        assert template.count(heading) == 1
        assert template.index(heading) < template.index("### 阶段 1")
    source = completed_plan(template)
    assert normalize_and_validate_plan(source, "Go", route) is not None
    for heading in COMPREHENSIVE_HEADINGS:
        assert normalize_and_validate_plan(source.replace(heading, "## 非必需说明"), "Go", route) is None


@pytest.mark.parametrize("route", ["concept_clarity", "gap_upgrade", "interview_sprint", "academic_course", "exam_review"])
def test_other_routes_receive_unmodified_general_template(tmp_path, route):
    assert prepared_template(tmp_path, route) == (RELEASE / TEMPLATE).read_text().strip()


def test_comprehensive_template_inherits_all_general_teaching_fields(tmp_path):
    template = prepared_template(tmp_path, "foundation_engineer")
    general = (RELEASE / TEMPLATE).read_text()
    assert template.startswith(general.split("## 阶段\n", 1)[0])
    assert template.endswith("## 阶段\n" + general.split("## 阶段\n", 1)[1].rstrip())


def test_missing_comprehensive_template_piece_fails_before_generation(tmp_path):
    from backend.generation_context import COMPREHENSIVE_SECTIONS

    release = tmp_path / "release"
    shutil.copytree(RELEASE / ".codex", release / ".codex")
    (release / COMPREHENSIVE_SECTIONS).unlink()
    user = tmp_path / "learner"
    user.mkdir()
    (user / "learning-state.json").write_text(json.dumps({"goal_route": "foundation_engineer"}))
    with pytest.raises(FileNotFoundError):
        prepare_generation_context(release, user, "plan", "生成课程", False)
