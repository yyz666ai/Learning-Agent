from backend.learning_plan_personalizer import _diagnosis_context, build_plan_prompt
from backend.onboarding import DiagnosisSummary, OnboardingSubmission


def test_synthetic_diagnosis_is_not_reported_as_real_answers():
    diagnosis = DiagnosisSummary(estimated_level="experienced", score=.8, answered_count=4,
        strengths=["HTTP"], gaps=["并发"], evidence=[{"source":"evaluation fixture, not actual learner answers"}])
    result = _diagnosis_context(diagnosis)
    assert "合成画像" in result
    assert "正确率：80%" not in result


def test_plan_generation_requires_quality_reference_and_chapter_budget():
    data = OnboardingSubmission.model_validate(dict(user_id="plan_test", learning_mode="systematic",
        goal_route="interview_sprint",level_claim="zero",topic={"type":"python","value":"Python"},
        session_minutes=40,teaching_preference="hands_on"))
    prompt = build_plan_prompt(data, "# Python")
    assert "curriculum-quality.md" in prompt
    assert "课外练习分钟" in prompt
    assert "线性" in prompt
    assert "岗位未确认" in prompt


def test_semantically_equivalent_outcome_heading_does_not_reject_complete_plan():
    from backend.learning_plan_personalizer import normalize_and_validate_plan
    plan = "# Python 面试通用预备\n## 当前任务\n运行首个程序\n## 成功证据\n独立运行和解释\n## 教学策略\n先练习再讲解\n"
    for n in range(1, 5):
        plan += f"### 阶段 {n}：Python 实践\n- 本阶段要学：解释当前程序并找出具体边界条件\n- 练习：独立编写一个小程序并用正常与异常输入验证\n- 完成证据：运行结果正确，能够说明每一行代码的作用\n- 预计课次：1\n- 单次分钟：40\n- 课外练习分钟：20\n"
    result = normalize_and_validate_plan(plan, "Python", "interview_sprint")
    assert result and "## 学习成果" in result
    assert normalize_and_validate_plan(plan.replace("## 成功证据\n独立运行和解释\n", ""), "Python", "interview_sprint") is None


def test_short_gap_route_is_allowed_without_padding_four_chapters():
    from backend.learning_plan_personalizer import normalize_and_validate_plan
    plan = "# Go 精进\n## 当前任务\n修复取消路径\n## 学习成果\n取消后工作单元有界退出\n## 教学策略\n复用HTTP基础，仅修复并发缺口\n### 阶段 1：取消与退出\n- 本阶段要学：确认任务所有者与退出条件\n- 练习：在已有服务中修改两个遗漏的取消分支，并写正常完成与取消退出的回归测试；复用已有的表驱动测试框架，不重复实现整个HTTP服务。\n- 完成证据：取消后收到工作单元自己的done信号，不使用全局goroutine数量作为充分证明。运行正常完成、提前取消、到期取消三组测试；重复执行并检查race。\n- 预计课次：2\n- 单次分钟：40\n- 课外练习分钟：40\n"
    assert normalize_and_validate_plan(plan,"Go","gap_upgrade")
