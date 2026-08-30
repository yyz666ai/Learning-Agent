"""Validated Codex personalization for learner-owned plan.md files."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .curriculum import normalize_plan_knowledge
from .learning_content import SAFE_USER_ID, resolve_plan_path
from .onboarding import DiagnosisSummary, OnboardingSubmission, ROUTE_STRATEGIES
from .research_artifact import research_slug


COMPREHENSIVE_ROUTES = {"foundation_engineer", "senior_engineer"}


def requires_authoritative_research(
    submission: OnboardingSubmission,
    knowledge_source: str,
    *,
    intent_slots: dict | None = None,
) -> bool:
    """Stable local curricula need no live search solely to arrange chapters."""
    stable_topic = submission.topic.value.strip().casefold() in {
        "go", "golang", "go 语言", "python", "python 语言",
    }
    constraints = json.dumps(intent_slots or {}, ensure_ascii=False)
    version_sensitive = re.search(r"最新|当前版本|版本变化|发布变化|版本升级|新特性|新框架|新库|latest|release|\bv?\d+\.\d+|langgraph|langchain", constraints, re.I)
    # A stack outside our two stable language maps needs its own sources.
    stack = (intent_slots or {}).get("tech_stack") or []
    if isinstance(stack, str):
        stack = [stack]
    external_stack = any(str(item).strip().casefold() not in {"go", "golang", "python", "go 语言", "python 语言"} for item in stack)
    return (knowledge_source != "knowledge_base" or not stable_topic
            or submission.goal_route == "interview_sprint" or bool(version_sensitive) or external_stack)


def _stage_requirement(goal_route: str) -> str:
    if goal_route == "concept_clarity":
        return "1–3 个"
    if goal_route in COMPREHENSIVE_ROUTES:
        return "根据完整能力地图动态安排，通常 12–60 个"
    return "根据目标范围动态安排 1–30 个，不为凑章数重复已会内容"


def _diagnosis_context(diagnosis: DiagnosisSummary | None) -> str:
    if diagnosis is None:
        return "未做诊断；按零基础补齐必要先修，不得假设已经掌握。"
    strengths = "、".join(diagnosis.strengths) or "暂无稳定强项"
    gaps = "、".join(diagnosis.gaps) or "暂无明确缺口"
    if any("fixture" in str(item).lower() or "synthetic" in str(item).lower() for item in diagnosis.evidence):
        return (f"合成画像（不是实际用户作答统计）：等级 {diagnosis.estimated_level}；"
                f"已给定强项：{strengths}；缺口：{gaps}。按这些输入规划，不声称用户做过题或给出正确率。")
    return (
        f"诊断等级：{diagnosis.estimated_level}；正确率：{diagnosis.score:.0%}；"
        f"答题数：{diagnosis.answered_count}；强项：{strengths}；缺口：{gaps}。"
        "Plan 必须说明哪些内容快进、哪些缺口补学，不能只使用自报水平。"
        "已经完成起点诊断，不要再安排一整章重复摸底；第一章直接补已确认的缺口，强项只作简短回顾。"
    )


def build_plan_prompt(
    submission: OnboardingSubmission,
    fallback_plan: str,
    knowledge_source: str = "skill_guided",
    *,
    diagnosis: DiagnosisSummary | None = None,
    research_required: bool | None = None,
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
    needs_research = research_required if research_required is not None else requires_authoritative_research(submission, knowledge_source)
    if needs_research:
        research_instruction = f"""
这个主题需要权威覆盖研究：知识库缺少可靠内容，或涉及岗位要求、新框架、明确的版本敏感需求。
使用已提供的 `.codex/skills/new-topic-research/SKILL.md` 规则，
先检查已有 `$USER_DIR/research/{research_slug(submission.topic.value)}/sources.json`。若它是当前日期生成、版本当前且已包含完整深度字段，先验证并复用，不重复搜索。
仅在文件缺失、过期、版本不清或覆盖不足时，按当前 shell 执行搜索：
- macOS / Linux 的 POSIX shell：`"$LEARNING_AGENT_PYTHON" tools/web_search.py \"{submission.topic.value} official documentation getting started\"`。
- Windows PowerShell：`& $env:LEARNING_AGENT_PYTHON tools/web_search.py \"{submission.topic.value} official documentation getting started\"`；同样用 `$env:USER_DIR` 解析下面的用户目录，不把 POSIX 环境变量语法直接用于 PowerShell。
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
知识点标题使用简短的概念名词（例如“Go 安装”“go version”“package main”“func main”），一条只描述一个概念。安装步骤、网址、版本说明、验收细节放在本阶段要学/练习/完成证据中，不把整段行动说明或多个概念塞进知识点标题。
"""
    return f"""你是 Learning Agent 的课程总设计师。请为这一位学习者重写一份具体、可执行的 plan.md。

使用后台已提供的 `.codex/skills/learning-plan/SKILL.md`，严格按其中“先展示草案、确认后开课”的流程执行。
依据已提供的 `.codex/skills/learning-plan/references/curriculum-quality.md`，检查先修、承诺能力的练习/证据、时间口径。
使用已提供的 profile.json 中的 intent_slots 和 profile.md，保留用户目标、经验原文、约束、每周节奏、课程范围、题型和暂缓提供的资料；材料未提供不能宣称读过。
academic_course 按已给章节跟课、讲解、课堂练习与拓展；exam_review 按考试范围、期限、题型、错题安排复习。两者都不能强制工程师路线或毕业项目；研究文件中的 graduation_project 可明确写“不适用，改为考试/课程成果”。
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
9. 当前执行器按章节线性学习；Mermaid 如有只展示同一条线性顺序，不声明尚未实现的并行解锁。非概念速学路线每阶段写“- 预计课次：N”“- 单次分钟：{submission.session_minutes}”“- 课外练习分钟：M”；多课章还写“- 分次安排：第1课目标与暂停点；第2课目标与暂停点…”。课次是整章总量，不是每个知识点各一课。N/M 是合理估计，安装故障可另加时间，未交作业不代表掌握；概念速学只安排短小目标，不强加长期课表。
10. 面试岗位未确认时，只能生成明确标为“通用预备”的草案，不能承诺岗位面试达标；未知题源不等于用户已经回答没有资料。岗位与材料确认后再定专项；可以调整任何未完成阶段。
11. 所有路线每阶段均显式列出“#### 知识点”：使用简短的概念名词，一条一个概念（例如 goroutine、context 取消、资源泄漏），不要把“能描述…完整路径”这种学习目标当作知识点标题。学习目标放在“本阶段要学”，验收要求放在“完成证据”。
{mastery_instruction}

输出前检查：必须原样使用“## 当前任务”“## 学习成果”“## 教学策略”。
{"本路线还必须原样使用独立的二级标题：## 知识覆盖地图、## 最终达成标准、## 毕业项目。不能用“学习目标”“阶段”或最后一个阶段的毕业项目代替这些章节；分别填写覆盖范围、验收能力、综合项目设计。" if submission.goal_route in COMPREHENSIVE_ROUTES else "本路线只保留与用户目标相关的章节，不强制毕业项目。"}
不要照抄统一兜底课程：依据已确认画像、诊断与知识地图自行安排具体阶段。
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
还必须读取 `.codex/skills/learning-plan/references/curriculum-quality.md`，校验先修顺序、每个能力的实践证据、明确面试评分锚点及完整范围。
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
所有路线每阶段保留整章预计课次、单次分钟和课外练习分钟，不把概念数量当课次；当前执行按线性顺序，不展示未实现的并行解锁。

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
    if title is None and re.match(r"^学习计划[：:]\s*[^\n]+", candidate):
        first_line = candidate.splitlines()[0]
        if topic.casefold() in first_line.casefold():
            candidate = "# " + candidate
            title = re.search(r"(?m)^# [^#\n].*$", candidate)
    if title is None:
        # A display title is recoverable only for an otherwise structured Plan
        # whose original content already names the confirmed topic. Validation
        # below still requires every route-specific field and concrete stage.
        if not (topic.strip() and "\n" not in topic and "\r" not in topic
                and candidate.startswith("## ") and topic.casefold() in candidate.casefold()):
            return None
        candidate = f"# {topic} 学习计划\n\n{candidate}"
        title = re.search(r"(?m)^# [^#\n].*$", candidate)
    candidate = candidate[title.start():].strip()
    # Accept equivalent outcome headings; never fabricate missing content.
    if not re.search(r"(?m)^## 学习成果\s*$", candidate):
        candidate = re.sub(r"(?m)^## (?:成功证据|预期成果|学习产出)\s*$", "## 学习成果", candidate, count=1)
    candidate = re.sub(
        r"(?m)^## (\u9636\u6bb5\s*\d+[^\n]*)$",
        r"### \1",
        candidate,
    )
    candidate = re.sub(
        r"`?\$USER_DIR(?:/[^\s`)），。]+)+`?",
        "已核对的资料来源",
        candidate,
    )
    for fence in re.finditer(r"(?ms)^```(?P<info>[^\n]*)\n.*?^```[ \t]*$", candidate):
        if fence.group("info").strip().casefold() != "mermaid":
            return None
    candidate = normalize_plan_knowledge(candidate)
    comprehensive = goal_route in COMPREHENSIVE_ROUTES
    minimum_length = 120 if goal_route == "concept_clarity" else (1_200 if comprehensive else 180)
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
        minimum_stages, maximum_stages = 1, 30
    if not minimum_stages <= len(stages) <= maximum_stages:
        return None
    for index, match in enumerate(stages):
        end = stages[index + 1].start() if index + 1 < len(stages) else len(candidate)
        section = candidate[match.start():end]
        if not all(marker in section for marker in ("- 本阶段要学：", "- 练习：", "- 完成证据：")):
            return None
        if comprehensive:
            knowledge = re.search(
                r"(?m)^#### 知识点[ \t]*\n(?P<body>(?:"
                r"-[ \t]+(?!(?:本阶段要学|练习|完成证据|预计课次|单次分钟|课外练习分钟|分次安排|为什么现在学|必要知识点|真实产出|验收方式)[：:])"
                r"\S[^\n]*(?:\n|\Z)|[ \t]*\n)*)",
                section,
            )
            if knowledge is None or len(re.findall(r"(?m)^-[ \t]+\S", knowledge.group("body"))) < 2:
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
