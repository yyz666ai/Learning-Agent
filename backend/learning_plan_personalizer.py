"""Validated Codex personalization for learner-owned plan.md files."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .learning_content import SAFE_USER_ID, resolve_plan_path
from .onboarding import DiagnosisSummary, OnboardingSubmission, ROUTE_STRATEGIES
from .research_artifact import research_slug


COMPREHENSIVE_ROUTES = {"foundation_engineer", "senior_engineer"}


def requires_authoritative_research(
    submission: OnboardingSubmission,
    knowledge_source: str,
) -> bool:
    """Deep mastery needs a fresh coverage audit even when starter atoms exist."""
    return knowledge_source != "knowledge_base" or submission.goal_route in COMPREHENSIVE_ROUTES


def _stage_requirement(goal_route: str) -> str:
    if goal_route == "concept_clarity":
        return "1–3 个"
    if goal_route in COMPREHENSIVE_ROUTES:
        return "根据完整能力地图动态安排，通常 12–60 个"
    return "根据目标范围动态安排 4–30 个"


def _diagnosis_context(diagnosis: DiagnosisSummary | None) -> str:
    if diagnosis is None:
        return "未做诊断；按零基础补齐必要先修，不得假设已经掌握。"
    strengths = "、".join(diagnosis.strengths) or "暂无稳定强项"
    gaps = "、".join(diagnosis.gaps) or "暂无明确缺口"
    return (
        f"诊断等级：{diagnosis.estimated_level}；正确率：{diagnosis.score:.0%}；"
        f"答题数：{diagnosis.answered_count}；强项：{strengths}；缺口：{gaps}。"
        "Plan 必须说明哪些内容快进、哪些缺口补学，不能只使用自报水平。"
    )


def build_plan_prompt(
    submission: OnboardingSubmission,
    fallback_plan: str,
    knowledge_source: str = "skill_guided",
    *,
    diagnosis: DiagnosisSummary | None = None,
) -> str:
    strategy = ROUTE_STRATEGIES[submission.goal_route]
    concept_quickstart = submission.goal_route == "concept_clarity"
    stage_requirement = _stage_requirement(submission.goal_route)
    schedule_requirement = (
        "这是单次概念速学：不询问每日学习时长，不排长期日程，根据 concept_scope 决定是否进入代码。"
        if concept_quickstart
        else f"计划要符合每次 {submission.session_minutes} 分钟的节奏。"
    )
    research_instruction = ""
    if requires_authoritative_research(submission, knowledge_source):
        research_instruction = f"""
这个主题需要权威覆盖研究：可能是知识库缺少可靠原子，也可能是完整掌握路线需要核对知识体系是否遗漏。
即使知识库已有基础内容，也必须先读取 `.codex/skills/new-topic-research/SKILL.md`，
先检查已有 `$USER_DIR/research/{research_slug(submission.topic.value)}/sources.json`。若它是当前日期生成、版本当前且已包含完整深度字段，先验证并复用，不重复搜索。
仅在文件缺失、过期、版本不清或覆盖不足时，执行 `python tools/web_search.py \"{submission.topic.value} official documentation getting started\"`，
优先核对官方文档或官方仓库，并把可追溯结果写到
`$USER_DIR/research/{research_slug(submission.topic.value)}/sources.json`。研究文件除来源和事实外，必须包含
coverage_areas、prerequisites 和 graduation_project。搜索或证据校验失败时，不得输出正式计划。
"""
    mastery_instruction = ""
    if submission.goal_route in COMPREHENSIVE_ROUTES:
        mastery_instruction = """
这是完整掌握路线。必须先写“## 知识覆盖地图”，覆盖核心直觉、基础、运行机制、调试、测试、工程结构、错误与边界、性能、安全、真实项目、迁移与复习；不适用项写明替代能力。
还必须写“## 最终达成标准”和“## 毕业项目”。最后一个阶段必须是毕业项目交付，覆盖需求、设计、实现、测试、调试、性能/安全检查、使用说明和复盘。
每个阶段必须增加“#### 知识点”，列出至少 2 个原子知识点，并写“- 预计课次：N”。不要为了凑数量拆同义阶段，也不要把多个庞大主题塞进一个知识点。
"""
    return f"""你是 Learning Agent 的课程总设计师。请为这一位学习者重写一份具体、可执行的 plan.md。

先完整读取 `.codex/skills/learning-plan/SKILL.md`，严格按其中“先展示草案、确认后开课”的流程执行。
{research_instruction}

主题：{submission.topic.value}
路线：{strategy['label']}
起点：{submission.level_claim}
诊断证据：{_diagnosis_context(diagnosis)}
概念范围：{submission.concept_scope}
期限：{submission.deadline_days or '无硬期限'}
教学重点：{strategy['teaching_focus']}

硬性要求：
0. 只读取本任务点名的 Skills、用户画像和必要资料；不要扫描无关历史。
1. 研究阶段只允许写上面指定的 `sources.json`。Plan 只能在最终回复中输出；不要直接写入或修改用户的 Plan、状态、课程树和学习进度，这些文件由服务端校验通过后原子保存。
   Plan 是给学习者看的：不得展示 `$USER_DIR`、内部研究文件路径或运行时目录。
2. 最终回复只输出 Markdown，不要解释工具过程，也不要使用代码围栏包住全文。
3. 必须含“## 当前任务”“## 学习成果”“## 教学策略”。
4. 安排 {stage_requirement}“### 阶段 N：具体名称”，内容必须针对“{submission.topic.value}”。
5. 每个阶段都必须含“- 本阶段要学：”“- 练习：”“- 完成证据：”。
6. 第一阶段必须能马上开始；不要继续向学习者摸底。
7. {schedule_requirement}避免宽泛的“学习基础知识”。
8. Plan 不承载教学代码：可以用 Mermaid 表达知识依赖，但不得嵌入 Go、Python 等编程代码。实际代码必须留到用户确认后的 HTML PPT，再按能力逐页讲解并加详细中文注释。
{mastery_instruction}

下面是系统安全兜底计划。保留它的可靠结构，但把内容进一步具体化：

{fallback_plan}
"""


def build_plan_revision_prompt(
    submission: OnboardingSubmission,
    current_plan: str,
    feedback: str,
) -> str:
    stage_requirement = _stage_requirement(submission.goal_route)
    schedule_line = (
        "这是单次概念速学，不增加每日时长和长期课表。"
        if submission.goal_route == "concept_clarity" else f"每次学习：{submission.session_minutes} 分钟"
    )
    return f"""你正在修订学习者尚未确认的学习计划。

必须先读取 `.codex/skills/plan-revision/SKILL.md` 和 `.codex/skills/learning-plan/SKILL.md`。
保留已完成进度与可定位的当前知识点；只修改用户意见影响到的部分。

主题：{submission.topic.value}
路线：{submission.goal_route}
起点：{submission.level_claim}
{schedule_line}
概念范围：{submission.concept_scope}
用户修改意见：{feedback}

最终只输出完整 Markdown Plan。仍必须包含“## 当前任务”“## 学习成果”“## 教学策略”，
以及 {stage_requirement} 个具体阶段；每阶段包含“- 本阶段要学：”“- 练习：”“- 完成证据：”。
完整掌握路线仍必须保留“## 知识覆盖地图”“## 最终达成标准”“## 毕业项目”、阶段知识点和预计课次，最后一阶段交付毕业项目。

当前 Plan：

{current_plan}
"""


def normalize_and_validate_plan(
    markdown: str,
    topic: str,
    goal_route: str = "foundation_engineer",
) -> str | None:
    candidate = markdown.strip()
    if candidate.startswith("```") and candidate.endswith("```"):
        lines = candidate.splitlines()
        candidate = "\n".join(lines[1:-1]).strip()
    title = re.search(r"(?m)^# [^#\n].*$", candidate)
    if title is None:
        return None
    candidate = candidate[title.start():].strip()
    candidate = re.sub(
        r"`?\$USER_DIR(?:/[^\s`)），。]+)+`?",
        "已核对的资料来源",
        candidate,
    )
    for fence in re.finditer(r"(?ms)^```(?P<info>[^\n]*)\n.*?^```[ \t]*$", candidate):
        if fence.group("info").strip().casefold() != "mermaid":
            return None
    comprehensive = goal_route in COMPREHENSIVE_ROUTES
    minimum_length = 120 if goal_route == "concept_clarity" else (1_200 if comprehensive else 300)
    if not minimum_length <= len(candidate) <= 30_000:
        return None
    if topic.casefold() not in candidate.casefold():
        return None
    for heading in ("## 当前任务", "## 学习成果", "## 教学策略"):
        if heading not in candidate:
            return None
    stages = list(re.finditer(r"(?m)^### 阶段\s*\d+[^\n]*$", candidate))
    if goal_route == "concept_clarity":
        minimum_stages, maximum_stages = 1, 3
    elif comprehensive:
        minimum_stages, maximum_stages = 12, 60
    else:
        minimum_stages, maximum_stages = 4, 30
    if not minimum_stages <= len(stages) <= maximum_stages:
        return None
    for index, match in enumerate(stages):
        end = stages[index + 1].start() if index + 1 < len(stages) else len(candidate)
        section = candidate[match.start():end]
        if not all(marker in section for marker in ("- 本阶段要学：", "- 练习：", "- 完成证据：")):
            return None
        if comprehensive:
            knowledge = re.search(
                r"(?ms)^#### 知识点\s*$\n(?P<body>.*?)(?=^- 本阶段要学[：:]|^#### |\Z)",
                section,
            )
            if knowledge is None or len(re.findall(r"(?m)^-\s+(?!本阶段)", knowledge.group("body"))) < 2:
                return None
            if re.search(r"(?m)^- 预计课次[：:]\s*[1-9]\d*$", section) is None:
                return None
    if comprehensive:
        for heading in ("## 知识覆盖地图", "## 最终达成标准", "## 毕业项目"):
            if heading not in candidate:
                return None
        last_section = candidate[stages[-1].start():]
        if re.search(r"毕业项目|综合项目|capstone", last_section, re.IGNORECASE) is None:
            return None
    return candidate + "\n"


def active_plan_path(server_root: Path, user_id: str) -> Path:
    if not SAFE_USER_ID.fullmatch(user_id):
        raise ValueError("invalid user_id")
    user_dir = server_root / "userdir" / f"u_{user_id}"
    try:
        state = json.loads((user_dir / "learning-state.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("learner plan is not confirmed") from exc
    plan_path = resolve_plan_path(user_dir, state.get("active_plan"))
    if plan_path is None or not plan_path.is_file():
        raise ValueError("active plan is missing")
    return plan_path


def replace_plan(path: Path, content: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def set_plan_status(server_root: Path, user_id: str, status: str) -> None:
    if status not in {"draft", "awaiting_confirmation", "confirmed"}:
        raise ValueError("invalid plan status")
    if not SAFE_USER_ID.fullmatch(user_id):
        raise ValueError("invalid user_id")
    state_path = server_root / "userdir" / f"u_{user_id}" / "learning-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(state, dict):
        raise ValueError("learning state is invalid")
    state["plan_status"] = status
    state["revision"] = int(state.get("revision") or 0) + 1
    temporary = state_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(state_path)
