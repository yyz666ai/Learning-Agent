"""Deterministic onboarding and learner-plan persistence."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from .learning_content import SAFE_USER_ID
from .user_memory import read_intent_state, write_profile_json

GoalRoute = Literal[
    "concept_clarity",
    "foundation_engineer",
    "urgent_codebase",
    "syntax_reading",
    "project_delivery",
    "gap_upgrade",
    "senior_engineer",
    "interview_sprint",
]

ROUTE_STRATEGIES: dict[str, dict[str, str]] = {
    "concept_clarity": {"label": "概念速学", "teaching_focus": "先建立准确直觉，再决定是否查看代码实现", "practice_focus": "用生活比喻、流程图和少量点击判断快速验证理解", "review_intensity": "本次即时回顾，不默认安排每日课表", "graduation_evidence": "能用大白话判断它解决什么问题、什么时候适合使用"},
    "foundation_engineer": {"label": "从零到工程师", "teaching_focus": "完整学习、复习、实战与阶段验收", "practice_focus": "选择判断、真实文件和综合项目逐步推进", "review_intensity": "完整间隔复习", "graduation_evidence": "独立完成并解释一个综合项目"},
    "urgent_codebase": {"label": "紧急看懂项目", "teaching_focus": "优先入口、调用链和关键文件", "practice_focus": "用选择判断快速理解项目，再修改一个目标位置", "review_intensity": "轻量回顾，减少繁琐记忆", "graduation_evidence": "能解释调用链并完成一次目标修改"},
    "syntax_reading": {"label": "看懂语法与代码", "teaching_focus": "优先语法辨析和代码阅读", "practice_focus": "输出预测、逐段解释和代码选择题", "review_intensity": "只回顾阻塞阅读的易错点", "graduation_evidence": "能逐段解释目标代码"},
    "project_delivery": {"label": "项目实战交付", "teaching_focus": "围绕要交付的功能补齐最小知识", "practice_focus": "真实文件、运行结果和测试", "review_intensity": "复习当前交付依赖的知识", "graduation_evidence": "目标功能与测试通过"},
    "gap_upgrade": {"label": "中级能力补全", "teaching_focus": "已掌握内容快进，薄弱点恢复小步教学", "practice_focus": "追踪、修复和迁移题", "review_intensity": "强化易错点和长期未用知识", "graduation_evidence": "薄弱点通过独立迁移题"},
    "senior_engineer": {"label": "高级工程师进阶", "teaching_focus": "架构取舍、可靠性和重构", "practice_focus": "大型项目、设计评审、性能与故障演练", "review_intensity": "围绕工程误判与设计原则复盘", "graduation_evidence": "完成设计文档、实现、测试和复盘"},
    "interview_sprint": {"label": "面试冲刺", "teaching_focus": "简答、追问和代码推演", "practice_focus": "每道题都按真实面试表达与 rubric 评价", "review_intensity": "把表达遗漏和易错点做成知识卡", "graduation_evidence": "完成一轮目标岗位模拟面试"},
}

ROUTE_PHASES: dict[str, list[tuple[str, str, str, str]]] = {
    "concept_clarity": [
        ("先讲懂它是什么", "用一个具体场景和比喻理解 {topic} 解决的问题", "完成 1–2 道点击判断", "能区分它和一个容易混淆的做法"),
        ("放回真实场景", "看懂 {topic} 的最小流程、输入输出和适用边界", "选择一个真实场景并判断是否适合使用", "能用一句大白话说清它的用途"),
    ],
    "foundation_engineer": [
        ("建立核心直觉", "从真实场景理解 {topic} 的作用、输入与输出", "看一个最小示例并完成 1 道概念判断", "能不用术语讲清它解决什么问题"),
        ("读懂最小结构", "识别 {topic} 中最常见的结构、关键语法和执行顺序", "逐行预测一个可运行示例的结果", "能指出每一行的职责并预测输出"),
        ("第一次真实运行", "学会在本机创建、运行和定位 {topic} 的最小程序", "在练习目录修改文件并真实运行", "提交运行命令、输出和自己的解释"),
        ("错误处理与调试", "理解 {topic} 常见失败、错误信息和排查顺序", "制造一个错误，再根据提示独立修好", "留下错误前后对比和修复理由"),
        ("完成可用小项目", "把分散知识组合成一个可交付的 {topic} 小项目", "实现功能、补测试并解释关键取舍", "项目可运行、测试通过且能独立讲解"),
        ("复习与迁移", "把错题、易忘点和工程经验整理成复习卡", "完成快问快答和一道新场景迁移题", "无需照抄即可解决相似新问题"),
    ],
    "urgent_codebase": [
        ("锁定项目目标", "明确要看懂的 {topic} 功能、时间限制和交付问题", "写出三个必须回答的项目问题", "目标范围可在两天内验证"),
        ("找到入口", "识别启动命令、入口文件、配置和依赖", "真实启动项目并记录第一条调用", "能从命令定位到入口文件"),
        ("画出关键调用链", "追踪 {topic} 的请求、数据和返回路径", "沿一条真实路径标注关键函数", "能用自己的话复述完整调用链"),
        ("补齐阻塞语法", "只学习阻碍阅读的语法和框架约定", "完成代码辨析与输出预测", "关键片段可以逐段解释"),
        ("完成目标修改", "理解改动影响、验证方法和回归风险", "修改一个目标位置并运行验证", "改动生效且能说明影响范围"),
    ],
    "syntax_reading": [
        ("建立语法地图", "认识 {topic} 最常见的表达式、语句和结构", "给真实代码片段分类", "能快速识别代码结构"),
        ("读懂数据流", "追踪变量、参数、返回值和类型变化", "逐行标注值从哪里来到哪里去", "能预测关键变量的值"),
        ("读懂控制流", "理解条件、循环、函数与异常路径", "预测不同输入下的执行分支", "能复述执行顺序"),
        ("识别常见惯用法", "学习 {topic} 项目里高频写法与约定", "把陌生片段改写成直白版本", "能解释惯用法为什么这样写"),
        ("整段代码讲解", "把语法点组合成完整阅读能力", "独立讲解一段目标项目代码", "不依赖答案完成逐段解释"),
    ],
    "project_delivery": [
        ("定义交付结果", "把 {topic} 需求拆成可验收的输入、输出和边界", "写出最小验收清单", "需求可以用具体结果判断完成"),
        ("搭建可运行骨架", "掌握项目结构、依赖与启动方式", "在练习目录启动最小版本", "本地可以稳定运行"),
        ("实现核心路径", "理解完成主功能所需的最小知识", "在真实文件里实现一条端到端路径", "主流程得到正确输出"),
        ("处理边界与错误", "学习参数校验、失败反馈和可观测信息", "补两个失败场景并验证", "错误行为明确且可排查"),
        ("测试与交付", "掌握自动验证、使用说明和交付检查", "补测试并从空环境复跑", "测试通过且他人按说明可运行"),
    ],
    "gap_upgrade": [
        ("快速能力体检", "用少量迁移题定位 {topic} 真正薄弱处", "完成 3–4 道诊断并解释思路", "形成明确的薄弱点清单"),
        ("修复核心误区", "重建最影响后续学习的心智模型", "对比错误写法与正确写法", "能解释原先为什么会错"),
        ("加强工程用法", "掌握 {topic} 在真实项目中的组合方式", "阅读并修改一段生产式代码", "修改正确且不破坏原行为"),
        ("独立调试", "建立从现象到根因的排查顺序", "完成一个故障定位任务", "用证据说明根因和修复"),
        ("迁移验收", "把补齐的能力迁移到陌生场景", "独立完成一道综合题", "不靠提示完成并复盘取舍"),
    ],
    "senior_engineer": [
        ("定义高级项目", "为 {topic} 设定规模、SLO、约束与演进目标", "输出项目简报和风险清单", "目标与质量属性可衡量"),
        ("架构与取舍", "比较边界、依赖、数据流和备选方案", "写设计文档并完成一次评审", "能解释选择和放弃了什么"),
        ("可靠实现", "处理并发、失败恢复、幂等和可观测性", "实现关键路径与故障保护", "正常与失败场景均有证据"),
        ("性能与容量", "建立基准、瓶颈假设和容量模型", "压测、定位并优化一个瓶颈", "用数据证明优化有效"),
        ("演进与重构", "评估技术债、兼容性和渐进迁移策略", "完成一次可回滚重构", "测试通过并留下迁移复盘"),
        ("技术领导力复盘", "沉淀决策、协作和长期维护原则", "做一次设计答辩与反事实复盘", "能清晰回答深度追问"),
    ],
    "interview_sprint": [
        ("整理岗位题图", "把 {topic} 题目按知识依赖和岗位频率分组", "导入题目并标记会、模糊、不会", "形成可追踪题库与优先级"),
        ("建立回答骨架", "掌握结论、原理、例子、边界的表达结构", "口述 3 道核心题并接受追问", "回答完整、简洁且有层次"),
        ("代码与场景推演", "把概念放进真实代码和故障场景", "现场写或讲解两道实战题", "过程可解释且结果正确"),
        ("修复易错表达", "针对遗漏、含糊和错误点补讲", "把错题改写成 Anki 卡并重答", "相同易错点不再遗漏"),
        ("模拟面试验收", "在时间压力下综合表达与追问", "完成一轮目标岗位模拟面试", "按 rubric 达标并形成最后清单"),
    ],
}


class TopicSelection(BaseModel):
    type: Literal["go", "python", "project", "custom"]
    value: str = Field(min_length=1, max_length=240)


class OnboardingSubmission(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    learning_mode: Literal["systematic", "project", "practice"]
    goal_route: GoalRoute = "foundation_engineer"
    level_claim: Literal["zero", "some", "experienced"]
    topic: TopicSelection
    session_minutes: int = Field(default=25, ge=10, le=120)
    deadline_days: int | None = Field(default=None, ge=1, le=365)
    teaching_preference: Literal["visual", "balanced", "hands_on"] = "balanced"
    concept_scope: Literal["not_applicable", "meaning_only", "code_walkthrough"] = "not_applicable"


class DiagnosisSummary(BaseModel):
    estimated_level: str = Field(min_length=1, max_length=64)
    score: float = Field(ge=0, le=1)
    answered_count: int = Field(ge=1, le=10)
    strengths: list[str] = Field(default_factory=list, max_length=8)
    gaps: list[str] = Field(default_factory=list, max_length=8)
    evidence: list[dict[str, object]] = Field(default_factory=list, max_length=10)


def needs_diagnosis(submission: OnboardingSubmission) -> bool:
    """Zero beginners start immediately; other learners get click diagnosis."""
    if submission.goal_route == "concept_clarity":
        return False
    return submission.level_claim != "zero"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (slug or "learning-topic")[:64]


def _knowledge_source(server_root: Path, topic: TopicSelection) -> str:
    if topic.type in {"go", "python"}:
        return "knowledge_base"
    curriculum = server_root / "workspace" / "dev" / "curriculum"
    needle = topic.value.casefold()
    if curriculum.is_dir():
        for atoms_dir in curriculum.rglob("atoms"):
            if not atoms_dir.is_dir() or not any(atoms_dir.glob("*.md")):
                continue
            topic_root = atoms_dir.parent
            searchable = " ".join(part.casefold() for part in topic_root.parts[-4:])
            if needle in searchable:
                return "knowledge_base"
    return "skill_guided"


def render_profile(
    submission: OnboardingSubmission,
    diagnosis: DiagnosisSummary | None,
) -> str:
    diagnosed = diagnosis.estimated_level if diagnosis else "零基础，跳过诊断"
    strengths = "、".join(diagnosis.strengths) if diagnosis and diagnosis.strengths else "暂无"
    gaps = "、".join(diagnosis.gaps) if diagnosis and diagnosis.gaps else "暂无"
    scope_label = {
        "meaning_only": "只理解概念（meaning_only）",
        "code_walkthrough": "还要看代码实现（code_walkthrough）",
        "not_applicable": "不适用（not_applicable）",
    }[submission.concept_scope]
    time_line = (
        "- 学习节奏：概念速学，不询问每日时长"
        if submission.goal_route == "concept_clarity"
        else f"- 单次时长：{submission.session_minutes} 分钟"
    )
    return "\n".join(
        (
            f"# 学习者画像：{submission.topic.value}",
            "",
            f"- 学习方式：{submission.learning_mode}",
            f"- 目标路线：{ROUTE_STRATEGIES[submission.goal_route]['label']}（{submission.goal_route}）",
            f"- 自报基础：{submission.level_claim}",
            f"- 诊断结果：{diagnosed}",
            f"- 诊断强项：{strengths}",
            f"- 诊断缺口：{gaps}",
            f"- 概念范围：{scope_label}",
            time_line,
            f"- 截止期限：{submission.deadline_days or '未设置'}",
            f"- 教学偏好：{submission.teaching_preference}",
            "- 画像状态：界面已确认，不再重复摸底",
            "",
        )
    )


def _render_interview_context(slots: dict[str, object]) -> str:
    """Render persisted interview slots for both people and downstream agents."""
    role = str(slots.get("target_role") or "").strip()
    raw_stack = slots.get("tech_stack")
    stack = [str(item).strip() for item in raw_stack] if isinstance(raw_stack, list) else []
    stack = [item for item in stack if item]
    source = str(slots.get("interview_question_source") or "unknown")
    source_label = {
        "has_questions": "已收录现成题",
        "none": "暂时没有现成题",
        "unknown": "尚未确认",
    }.get(source, "尚未确认")
    count = int(slots.get("interview_question_count") or 0)
    lines = ["## 面试上下文"]
    if role:
        lines.append(f"- 目标岗位：{role}")
    if stack:
        lines.append(f"- 技术栈：{'、'.join(stack)}")
    lines.append(f"- 面试题来源：{source_label}")
    if count:
        lines.append(f"- 已收录题目：{count} 道")
    return "\n".join((*lines, ""))


def render_plan(
    submission: OnboardingSubmission,
    diagnosis: DiagnosisSummary | None,
    knowledge_source: str,
) -> str:
    level = diagnosis.estimated_level if diagnosis else "zero"
    source_label = "现有知识库" if knowledge_source == "knowledge_base" else "通用教学 Skills"
    strategy = ROUTE_STRATEGIES[submission.goal_route]
    deadline = f"截止：{submission.deadline_days} 天" if submission.deadline_days else "截止：按长期节奏"
    phase_lines: list[str] = []
    for index, (title, learn, practice, evidence) in enumerate(ROUTE_PHASES[submission.goal_route], start=1):
        phase_lines.extend(
            (
                f"### 阶段 {index}：{title}",
                f"- 本阶段要学：{learn.format(topic=submission.topic.value)}",
                f"- 练习：{practice.format(topic=submission.topic.value)}",
                f"- 完成证据：{evidence.format(topic=submission.topic.value)}",
                "",
            )
        )
    scope_label = "只讲懂概念" if submission.concept_scope == "meaning_only" else "讲懂概念并拆解最小代码"
    schedule_line = (
        f"> 本次范围：{scope_label} · 不安排每日课表"
        if submission.goal_route == "concept_clarity"
        else f"> 每天 {submission.session_minutes} 分钟 · {deadline}"
    )
    current_task = (
        f"先用一个真实场景讲懂 {submission.topic.value}，再完成一道点击判断。"
        if submission.goal_route == "concept_clarity"
        else f"先理解 {submission.topic.value} 的第一个核心概念，完成一道判断题，并在真实练习目录留下可运行证据。"
    )
    return "\n".join(
        (
            f"# {submission.topic.value} 学习计划",
            "",
            f"> 路线：{strategy['label']} · 起点：{level} · 内容来源：{source_label}",
            schedule_line,
            "",
            "## 教学策略",
            f"- 讲解重点：{strategy['teaching_focus']}",
            f"- 练习重点：{strategy['practice_focus']}",
            f"- 复习强度：{strategy['review_intensity']}",
            f"- 毕业证据：{strategy['graduation_evidence']}",
            "",
            "## 学习成果",
            f"完成后，你需要能够围绕 {submission.topic.value} 达成这条路线的毕业证据：{strategy['graduation_evidence']}。",
            "",
            "## 当前任务",
            current_task,
            "",
            *phase_lines,
        )
    )


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def confirm_onboarding(
    server_root: Path,
    submission: OnboardingSubmission,
    diagnosis: DiagnosisSummary | None,
) -> dict[str, object]:
    """Persist confirmed profile and a resolvable plan before model teaching."""
    if not SAFE_USER_ID.fullmatch(submission.user_id):
        raise ValueError("invalid user_id")
    if needs_diagnosis(submission) and diagnosis is None:
        raise ValueError("diagnosis is required for this level")

    user_dir = server_root / "userdir" / f"u_{submission.user_id}"
    state_path = user_dir / "learning-state.json"
    try:
        existing = json.loads(state_path.read_text(encoding="utf-8"))
        state = existing if isinstance(existing, dict) else {}
    except (OSError, json.JSONDecodeError):
        state = {}

    knowledge_source = _knowledge_source(server_root, submission.topic)
    relative_plan = Path("plans") / f"{_slug(submission.topic.value)}-plan.md"
    plan_path = user_dir / relative_plan
    intent_slots = read_intent_state(server_root, submission.user_id).get("slots", {})
    profile_markdown = render_profile(submission, diagnosis)
    if submission.goal_route == "interview_sprint" and isinstance(intent_slots, dict):
        profile_markdown += "\n" + _render_interview_context(intent_slots)
    _atomic_write(user_dir / "profile.md", profile_markdown)
    write_profile_json(
        server_root,
        submission.user_id,
        {
            "topic": submission.topic.value,
            "topic_type": submission.topic.type,
            "learning_mode": submission.learning_mode,
            "goal_route": submission.goal_route,
            "level_claim": submission.level_claim,
            "session_minutes": submission.session_minutes,
            "deadline_days": submission.deadline_days,
            "teaching_preference": submission.teaching_preference,
            "concept_scope": submission.concept_scope,
            "diagnosis": diagnosis.model_dump() if diagnosis is not None else None,
        },
    )
    _atomic_write(
        plan_path,
        render_plan(submission, diagnosis, knowledge_source),
    )

    topic_text = submission.topic.value.casefold()
    if submission.topic.type in {"go", "python"}:
        language = submission.topic.type
    elif "python" in topic_text:
        language = "python"
    elif "golang" in topic_text or re.search(r"\bgo\b", topic_text):
        language = "go"
    else:
        language = None
    revision = state.get("revision")
    revision = revision + 1 if isinstance(revision, int) and revision >= 0 else 1
    recent_evidence = state.get("recent_evidence")
    if not isinstance(recent_evidence, list):
        recent_evidence = []
    due_review_count = state.get("due_review_count")
    if not isinstance(due_review_count, int) or due_review_count < 0:
        due_review_count = 0
    state.update(
        {
            "schema_version": 1,
            "revision": revision,
            "profile_status": "confirmed",
            "active_plan": relative_plan.as_posix(),
            "active_language": language,
            "active_task": state.get("active_task"),
            "recent_evidence": recent_evidence[-10:],
            "due_review_count": due_review_count,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "active_topic": submission.topic.value,
            "learning_mode": submission.learning_mode,
            "goal_route": submission.goal_route,
            "concept_scope": submission.concept_scope,
            "session_minutes": submission.session_minutes,
            "deadline_days": submission.deadline_days,
            "knowledge_source": knowledge_source,
            "diagnosis": diagnosis.model_dump() if diagnosis is not None else None,
            "plan_status": "draft",
        }
    )
    _atomic_write(state_path, json.dumps(state, ensure_ascii=False, indent=2) + "\n")

    return {
        "user_id": submission.user_id,
        "profile_status": "confirmed",
        "plan_status": "draft",
        "active_plan": relative_plan.as_posix(),
        "knowledge_source": knowledge_source,
        "first_lesson": {
            "start_immediately": False,
            "forbid_more_onboarding": True,
            "topic": submission.topic.value,
            "instruction": "先生成并展示完整 Plan；用户确认后立即开始第一章。",
        },
    }
