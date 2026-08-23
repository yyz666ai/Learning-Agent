from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "workspace/dev"
AGENTS = WORKSPACE / "AGENTS.md"
ONBOARDING_SKILL = WORKSPACE / ".codex/skills/learner-onboarding/SKILL.md"
CONCEPT_SKILL = WORKSPACE / ".codex/skills/concept-teaching/SKILL.md"
PRACTICE_SKILL = WORKSPACE / ".codex/skills/practice-drill/SKILL.md"
FAST_LOOP_SKILL = WORKSPACE / ".codex/skills/adaptive-lesson-flow/SKILL.md"
CURATOR_SKILL = WORKSPACE / ".codex/skills/knowledge-curator/SKILL.md"
REVIEW_SKILL = WORKSPACE / ".codex/skills/assignment-review/SKILL.md"
PLAN_SKILL = WORKSPACE / ".codex/skills/learning-plan/SKILL.md"
RESEARCH_SKILL = WORKSPACE / ".codex/skills/new-topic-research/SKILL.md"
PLAN_REVISION_SKILL = WORKSPACE / ".codex/skills/plan-revision/SKILL.md"
VISUAL_SKILL = WORKSPACE / ".codex/skills/visual-explainer/SKILL.md"
CODE_STEPS_SKILL = WORKSPACE / ".codex/skills/progressive-code-teaching/SKILL.md"
QUIZ_SKILL = WORKSPACE / ".codex/skills/quiz-designer/SKILL.md"
PROJECT_SKILL = WORKSPACE / ".codex/skills/project-scaffolder/SKILL.md"
LESSON_REVISION_SKILL = WORKSPACE / ".codex/skills/lesson-revision/SKILL.md"
INTENT_ROUTER_SKILL = WORKSPACE / ".codex/skills/learning-intent-router/SKILL.md"
ENVIRONMENT_SKILL = WORKSPACE / ".codex/skills/environment-setup/SKILL.md"
VALIDATOR = WORKSPACE / "tools/validate_workspace.py"
EVAL_RUNNER = WORKSPACE / "tools/run_behavior_evals.py"


def test_confirmed_profile_forbids_more_onboarding():
    agents = AGENTS.read_text(encoding="utf-8")
    skill = ONBOARDING_SKILL.read_text(encoding="utf-8")

    assert "画像已由界面确认时，不得再次摸底" in agents
    assert "forbid_more_onboarding" in skill
    assert "直接交给教学 Skill" in skill


def test_topic_only_intent_uses_three_meaningful_routes_before_detail_questions() -> None:
    skill = INTENT_ROUTER_SKILL.read_text(encoding="utf-8")

    assert "初学" in skill
    assert "精进" in skill
    assert "面试" in skill
    assert "仅有主题" in skill
    assert "初学" in skill and "想学到什么程度" in skill
    assert "精进" in skill and "现有项目" in skill
    assert "面试" in skill and "面试题" in skill


def test_onboarding_skills_branch_for_one_concept_without_time_interrogation():
    agents = AGENTS.read_text(encoding="utf-8")
    onboarding = ONBOARDING_SKILL.read_text(encoding="utf-8")
    adaptive = (WORKSPACE / ".codex/skills/adaptive-onboarding/SKILL.md").read_text(encoding="utf-8")
    concept = CONCEPT_SKILL.read_text(encoding="utf-8")

    assert "concept_clarity" in agents
    assert "只理解概念" in onboarding
    assert "还要看代码实现" in onboarding
    assert "不问每日时长" in onboarding
    assert "概念速学不做起点诊断" in adaptive
    assert "meaning_only" in concept and "code_walkthrough" in concept


def test_onboarding_contract_uses_input_first_topic_routing():
    agents = AGENTS.read_text(encoding="utf-8")
    onboarding = ONBOARDING_SKILL.read_text(encoding="utf-8")
    adaptive = (WORKSPACE / ".codex/skills/adaptive-onboarding/SKILL.md").read_text(encoding="utf-8")

    assert "左侧学习项目列表是继续历史学习的唯一入口" in agents
    assert "输入框负责新需求和当前答疑" in agents
    assert "显式概念问句" in onboarding
    assert "不再追问学习路线" in onboarding
    assert "领域学习才进入目标选择" in adaptive


def test_intent_router_skill_owns_multiturn_slot_filling_and_dynamic_questions():
    agents = AGENTS.read_text(encoding="utf-8")
    intent = INTENT_ROUTER_SKILL.read_text(encoding="utf-8")
    onboarding = ONBOARDING_SKILL.read_text(encoding="utf-8")

    assert "learning-intent-router" in agents
    assert "slot filling" in intent
    assert "最近 8 条" in intent
    assert "新输入优先" in intent
    assert "一次只问一个问题" in intent
    assert "2–3 个" in intent
    assert "其他" in intent and "不得" in intent
    assert "ready_for_plan" in intent
    assert "不为了补齐表单" in intent
    assert "意图槽位" in onboarding

    evals = (INTENT_ROUTER_SKILL.parent / "evals/evals.json").read_text(encoding="utf-8")
    for case_id in (
        "concept-question", "ambiguous-langgraph", "interview-with-evidence",
        "current-debugging", "interview-intake", "correct-previous-slot",
    ):
        assert case_id in evals


def test_intent_router_forbids_duplicate_same_topic_learning_projects():
    intent = INTENT_ROUTER_SKILL.read_text(encoding="utf-8")

    assert "同主题项目" in intent
    assert "不得创建重复项目" in intent
    assert "继续已有项目" in intent
    assert "合并" in intent


def test_plan_review_contract_is_conversational_and_text_revisable():
    agents = AGENTS.read_text(encoding="utf-8")
    onboarding = ONBOARDING_SKILL.read_text(encoding="utf-8")
    plan = PLAN_SKILL.read_text(encoding="utf-8")
    revision = PLAN_REVISION_SKILL.read_text(encoding="utf-8")

    assert "Plan 作为普通 Agent 消息" in agents
    assert "只保留一个紧凑的确认按钮" in onboarding
    assert "不套独立文档框" in plan
    assert "对话输入框中的文字直接视为修改意见" in revision


def test_teaching_limits_visible_work():
    skill = CONCEPT_SKILL.read_text(encoding="utf-8")

    assert "每轮最多一个新核心概念" in skill
    assert "默认只展示 1–3 道当前选择题" in skill
    assert "点击选择判断 → 动手运行 → 仅终端输出验收" in skill
    assert "在同一份翻页讲义中按页出现" in skill
    assert "不要向学习者播报读文件、路由 Skill、检查 Schema" in skill
    assert "正确选项必须与本页讲解事实一致" in skill


def test_advanced_drill_does_not_dump_a_batch():
    skill = PRACTICE_SKILL.read_text(encoding="utf-8")

    assert "一次只展示一道练习" in skill
    assert "跳过不算答对" in skill


def test_fast_lesson_skill_separates_classroom_checks_from_optional_homework():
    skill = FAST_LOOP_SKILL.read_text(encoding="utf-8")
    concept = CONCEPT_SKILL.read_text(encoding="utf-8")
    review = REVIEW_SKILL.read_text(encoding="utf-8")

    assert "课堂讲解 → 点击选择题 → 课后独立练习 → 对话答疑" in skill
    assert "4–8 页、1 道选择题" in skill
    assert "课后练习不作为下一章的门禁" in skill
    assert "不再生成终端输出框" in skill
    assert "在讲义内答对后自动进入下一页" in concept
    assert "对话输入栏" in review
    assert "不要求逐项粘贴终端输出" in review


def test_zero_beginner_lessons_prepare_the_environment_before_first_code() -> None:
    flow = FAST_LOOP_SKILL.read_text(encoding="utf-8")
    environment = ENVIRONMENT_SKILL.read_text(encoding="utf-8")
    plan = PLAN_SKILL.read_text(encoding="utf-8")

    for requirement in (
        "第一次运行代码前",
        "需要下载的软件",
        "官方入口",
        "版本验证命令",
        "课程项目目录",
        "首次运行命令",
    ):
        assert requirement in flow
        assert requirement in environment
    assert "环境准备阶段" in plan
    assert "environment_ready" in plan
    assert "后续章节不得重复" in flow
    reference = ENVIRONMENT_SKILL.parent / "references/environment-setup.md"
    assert reference.is_file()
    checklist = reference.read_text(encoding="utf-8")
    assert "https://go.dev/dl/" in checklist
    assert "https://www.python.org/downloads/" in checklist
    assert "只展示当前课程实际需要" in checklist


def test_fast_lesson_skill_has_a_behavior_case_for_independent_blank_code():
    evals = (FAST_LOOP_SKILL.parent / "evals/evals.json").read_text(encoding="utf-8")

    assert "blank" in evals
    assert "结果直接发对话输入栏" in evals


def test_chapter_deck_and_verified_knowledge_reuse_are_part_of_the_teaching_contract():
    flow = FAST_LOOP_SKILL.read_text(encoding="utf-8")
    curator = CURATOR_SKILL.read_text(encoding="utf-8")
    agents = AGENTS.read_text(encoding="utf-8")

    assert "一章" in flow
    assert "课堂练习" in flow and "课后练习" in flow
    assert "最后一页" in flow
    assert "待整理" in curator and "复核" in curator
    assert "复用" in curator
    assert "当前章" in agents


def test_skills_require_commented_code_and_personal_notes_rewards_in_the_ppt():
    flow = FAST_LOOP_SKILL.read_text(encoding="utf-8")
    code = CODE_STEPS_SKILL.read_text(encoding="utf-8")
    curator = CURATOR_SKILL.read_text(encoding="utf-8")
    agents = AGENTS.read_text(encoding="utf-8")

    assert "详细中文注释" in code
    assert "个人课堂笔记" in flow
    assert "专属奖励" in flow
    assert "待整理" in curator
    assert "重点问题" in curator
    assert "课后练习" in agents and "课堂练习" in agents


def test_lesson_skill_controls_bold_highlights_and_go_pointer_function_value_coverage() -> None:
    flow = FAST_LOOP_SKILL.read_text(encoding="utf-8")
    route = (WORKSPACE / "curriculum/go/learning-paths/foundations.md").read_text(encoding="utf-8")
    pointer = (WORKSPACE / "curriculum/go/atoms/go.pointers.basics.md").read_text(encoding="utf-8")
    pointer_usage = (WORKSPACE / "curriculum/go/atoms/go.pointers.parameters-receivers.md").read_text(encoding="utf-8")
    function_values = (WORKSPACE / "curriculum/go/atoms/go.functions.values-closures-callbacks.md").read_text(encoding="utf-8")

    assert "**关键结论**" in flow
    assert "==核心警告==" in flow
    assert "每页最多" in flow and "高亮" in flow
    assert "go.pointers.basics" in route
    assert "go.pointers.parameters-receivers" in route
    assert "go.functions.values-closures-callbacks" in route
    assert "&" in pointer and "*" in pointer
    assert "指针参数" in pointer_usage and "指针接收者" in pointer_usage
    assert "Go 使用函数值和函数类型" in function_values
    assert "不是 C/C++ 式函数指针" in function_values


def test_skills_define_deep_mastery_research_capstone_and_progressive_code_contracts():
    plan = PLAN_SKILL.read_text(encoding="utf-8")
    research = RESEARCH_SKILL.read_text(encoding="utf-8")
    lesson = FAST_LOOP_SKILL.read_text(encoding="utf-8")
    code = CODE_STEPS_SKILL.read_text(encoding="utf-8")

    assert "知识覆盖地图" in plan
    assert "最终达成标准" in plan
    assert "毕业项目" in plan
    assert "诊断" in plan and "强项" in plan and "缺口" in plan
    assert "知识库已有" in research and "完整掌握" in research
    assert "coverage_areas" in research and "graduation_project" in research
    assert "12–24 页" in lesson
    assert "超过 12 行" in code
    assert "中文注释" in code


def test_agentic_teaching_skills_own_research_plan_visual_code_quiz_project_and_revision_judgment():
    research = RESEARCH_SKILL.read_text(encoding="utf-8")
    plan = PLAN_SKILL.read_text(encoding="utf-8")
    plan_revision = PLAN_REVISION_SKILL.read_text(encoding="utf-8")
    visual = VISUAL_SKILL.read_text(encoding="utf-8")
    code_steps = CODE_STEPS_SKILL.read_text(encoding="utf-8")
    quiz = QUIZ_SKILL.read_text(encoding="utf-8")
    project = PROJECT_SKILL.read_text(encoding="utf-8")
    lesson_revision = LESSON_REVISION_SKILL.read_text(encoding="utf-8")
    agents = AGENTS.read_text(encoding="utf-8")

    assert "知识库没有可靠内容" in research
    assert "官方文档" in research and "sources.json" in research
    assert "先展示草案" in plan and "用户确认" in plan
    assert "保留已完成进度" in plan_revision
    assert "Mermaid" in visual and "流程图" in visual
    assert "6–10 个有效行" in code_steps and "逐行中文注释" in code_steps
    assert "题量由知识密度" in quiz and "不能绕过" in quiz
    assert "Cursor 或 Trae" in project and "课程根目录" in project
    assert "应用新版本" in lesson_revision and "保留旧版本" in lesson_revision
    assert "new-topic-research" in agents and "lesson-revision" in agents


def test_agentic_skills_have_real_behavior_cases():
    for skill in (
        RESEARCH_SKILL, PLAN_REVISION_SKILL, VISUAL_SKILL, CODE_STEPS_SKILL,
        QUIZ_SKILL, PROJECT_SKILL, LESSON_REVISION_SKILL,
    ):
        evals = (skill.parent / "evals/evals.json").read_text(encoding="utf-8")
        assert '"cases"' in evals
        assert '"expectations"' in evals


def test_workspace_validator_reads_real_codex_skills():
    validator = VALIDATOR.read_text(encoding="utf-8")

    assert 'root / ".codex/skills"' in validator
    for required in (
        "adaptive-lesson-flow",
        "environment-setup",
        "knowledge-curator",
        "practice-drill",
        "project-practice",
    ):
        assert f'"{required}"' in validator


def test_all_skills_have_behavior_cases_and_runner_can_find_them():
    skill_dirs = [path for path in (WORKSPACE / ".codex/skills").iterdir() if path.is_dir()]
    assert skill_dirs
    assert all((path / "evals/evals.json").is_file() for path in skill_dirs)
    runner = EVAL_RUNNER.read_text(encoding="utf-8")
    assert 'root / ".codex/skills"' in runner
