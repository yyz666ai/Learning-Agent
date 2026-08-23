from tools.run_persona_evals import score_run, score_state


def test_repeated_profile_question_fails_quality_gate():
    score = score_run(
        {
            "events": [
                {"role": "assistant", "text": "你学过 Go 吗？"},
                {"role": "assistant", "text": "再确认一次，你学过 Go 吗？"},
            ],
            "diagnostic_question_count": 2,
            "turns_to_first_teaching": 3,
        }
    )

    assert score["passed"] is False
    assert score["duplicate_question_count"] == 1


def test_invalid_active_plan_fails_quality_gate(tmp_path):
    user_dir = tmp_path / "userdir" / "u_invalid-plan"
    user_dir.mkdir(parents=True)

    score = score_state(user_dir, {"active_plan": "Go 精进计划"})

    assert score["active_plan_resolves"] is False


def test_plan_outside_user_directory_fails_quality_gate(tmp_path):
    user_dir = tmp_path / "userdir" / "u_escape"
    user_dir.mkdir(parents=True)
    outside = tmp_path / "secret.md"
    outside.write_text("secret", encoding="utf-8")

    score = score_state(user_dir, {"active_plan": "../../secret.md"})

    assert score["active_plan_resolves"] is False


def test_three_click_questions_and_first_lesson_can_pass():
    score = score_run(
        {
            "events": [
                {
                    "role": "assistant",
                    "text": "先把 Go channel 想成快递柜：它连接发送者和接收者。",
                },
                {
                    "role": "assistant",
                    "text": "现在只做一道题：这个发送会不会等待？",
                },
            ],
            "diagnostic_question_count": 3,
            "turns_to_first_teaching": 2,
        }
    )

    assert score["diagnostic_question_count"] == 3
    assert score["turns_to_first_teaching"] <= 2
    assert score["has_vivid_example"] is True
    assert score["passed"] is True


def test_more_than_ten_diagnostic_questions_fails():
    score = score_run(
        {
            "events": [{"role": "assistant", "text": "比如把变量想成贴标签的盒子。"}],
            "diagnostic_question_count": 11,
            "turns_to_first_teaching": 2,
        }
    )

    assert score["passed"] is False


def test_two_prompts_inside_one_current_exercise_count_as_one_question():
    score = score_run(
        {
            "events": [
                {
                    "role": "assistant",
                    "text": "想象电脑在照菜谱做事。**当前题** 会打印什么？为什么？",
                }
            ],
            "diagnostic_question_count": 0,
            "turns_to_first_teaching": 1,
        }
    )

    assert score["visible_question_count"] == 1
    assert score["has_vivid_example"] is True
    assert score["passed"] is True


def test_explicit_batch_of_questions_fails_small_step_gate():
    score = score_run(
        {
            "events": [
                {
                    "role": "assistant",
                    "text": "比如把变量想成盒子。下面有三道题，请全部回答。",
                }
            ],
            "diagnostic_question_count": 3,
            "turns_to_first_teaching": 2,
        }
    )

    assert score["small_step"] is False
    assert score["passed"] is False


def test_selection_and_hands_on_exercise_in_same_reply_fail_small_step():
    score = score_run(
        {
            "events": [
                {
                    "role": "assistant",
                    "text": "先打个比方。**判断**：A 还是 B？然后做这道小题。**练习**：写一句解释。把两个答案发给我。",
                }
            ],
            "diagnostic_question_count": 0,
            "turns_to_first_teaching": 1,
        }
    )

    assert score["visible_question_count"] == 2
    assert score["small_step"] is False
    assert score["has_vivid_example"] is True


def test_plain_simile_marker_counts_as_vivid_explanation():
    score = score_run(
        {
            "events": [
                {
                    "role": "assistant",
                    "text": "普通函数出错，像助手回来告诉你没有盐。当前题：错误会传回来吗？",
                }
            ],
            "diagnostic_question_count": 0,
            "turns_to_first_teaching": 1,
        }
    )

    assert score["has_vivid_example"] is True


def test_internal_file_and_skill_narration_fails_quality_gate():
    score = score_run(
        {
            "events": [
                {
                    "role": "assistant",
                    "text": "我先读取学习状态，再路由 concept-teaching Skill。比如把请求看成快递。当前题：会发生什么？",
                }
            ],
            "diagnostic_question_count": 3,
            "turns_to_first_teaching": 2,
        }
    )

    assert score["internal_process_leak"] is True
    assert score["passed"] is False


def test_recipe_and_core_request_flow_are_teaching_signals():
    for text in (
        "程序就是给电脑的菜谱。当前题：会打印什么？",
        "核心就一句：请求流是客户端到响应。用快递分拣来理解。当前题：在哪一环失败？",
    ):
        score = score_run(
            {
                "events": [{"role": "assistant", "text": text}],
                "diagnostic_question_count": 0,
                "turns_to_first_teaching": 1,
            }
        )
        assert score["has_teaching"] is True
        assert score["has_vivid_example"] is True


def test_interview_route_requires_short_answer_style_not_choices():
    score = score_run(
        {
            "goal_route": "interview_sprint",
            "events": [
                {
                    "role": "assistant",
                    "text": "把面试回答想成一个小型设计评审。简答题：你会怎样说明这个取舍？评价标准是边界、证据和表达。",
                }
            ],
            "diagnostic_question_count": 3,
            "turns_to_first_teaching": 2,
        }
    )

    assert score["route_fit"] is True
    assert score["interview_avoids_choices"] is True
    assert score["passed"] is True


def test_interview_route_rejects_lettered_multiple_choice():
    score = score_run(
        {
            "goal_route": "interview_sprint",
            "events": [
                {
                    "role": "assistant",
                    "text": "把面试想成实战。回答这道题：\nA. 方案一\nB. 方案二",
                }
            ],
            "diagnostic_question_count": 3,
            "turns_to_first_teaching": 2,
        }
    )

    assert score["interview_avoids_choices"] is False
    assert score["passed"] is False


def test_route_specific_content_is_required_when_route_is_present():
    score = score_run(
        {
            "goal_route": "senior_engineer",
            "events": [{"role": "assistant", "text": "比如把变量想成盒子。当前题：值是什么？"}],
            "diagnostic_question_count": 3,
            "turns_to_first_teaching": 2,
        }
    )

    assert score["route_fit"] is False
    assert score["passed"] is False


def test_global_pip_install_without_environment_check_fails():
    score = score_run(
        {
            "goal_route": "project_delivery",
            "events": [
                {
                    "role": "assistant",
                    "text": "把 API 想成服务员。先讲一个概念，然后运行文件；缺依赖就 pip install fastapi。",
                }
            ],
            "diagnostic_question_count": 3,
            "turns_to_first_teaching": 2,
        }
    )

    assert score["unsafe_install_instruction"] is True
    assert score["passed"] is False


def test_profile_statement_is_not_misread_as_a_profile_question():
    score = score_run(
        {
            "goal_route": "gap_upgrade",
            "events": [{"role": "assistant", "text": "你学过一点 Go，直接看切片这个坑。只做一道迁移题：为什么 b := a 会共享底层数组？"}],
            "diagnostic_question_count": 4,
            "turns_to_first_teaching": 2,
        }
    )

    assert score["profile_question_count"] == 0
    assert score["has_teaching"] is True


def test_two_related_rules_do_not_count_as_two_visible_questions():
    score = score_run(
        {
            "goal_route": "interview_sprint",
            "events": [{
                "role": "assistant",
                "text": "先讲 defer：参数像现在拍照。两个连带规则后面题目会用。简答题（只答这一题）：会输出什么？回答评价标准是解释求值时机。",
            }],
            "diagnostic_question_count": 3,
            "turns_to_first_teaching": 2,
        }
    )

    assert score["visible_question_count"] == 1
    assert score["has_vivid_example"] is True
    assert score["passed"] is True
