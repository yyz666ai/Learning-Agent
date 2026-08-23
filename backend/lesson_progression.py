"""Model-evaluated lesson completion and deterministic curriculum progression."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal

from pydantic import BaseModel, Field

try:
    from .curriculum import Curriculum, render_curriculum_plan, save_curriculum
    from .learning_content import SAFE_USER_ID
    from .lesson_manifest import LessonManifest
except ImportError:
    from curriculum import Curriculum, render_curriculum_plan, save_curriculum
    from learning_content import SAFE_USER_ID
    from lesson_manifest import LessonManifest


class QuizAttempt(BaseModel):
    page_id: str = Field(min_length=1, max_length=96)
    correct: bool


class CompletionEvidence(BaseModel):
    action: Literal["submit", "reteach", "stuck"]
    evidence: str = Field(default="", max_length=20_000)
    output_values: dict[str, str] = Field(default_factory=dict, max_length=6)
    quiz_attempts: list[QuizAttempt] = Field(default_factory=list, max_length=30)


class CompletionDecision(BaseModel):
    verdict: Literal["advance", "practice", "reteach"]
    feedback: str = Field(min_length=1, max_length=4_000)
    mastery_score: int = Field(ge=0, le=100)
    next_action: Literal["advance", "practice", "reteach"] | None = None
    next_knowledge_point_id: str | None = Field(default=None, max_length=96)
    cta_label: str = Field(default="", max_length=240)
    covered_knowledge_point_ids: list[str] = Field(default_factory=list, max_length=30)


def _extract_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("completion decision is not JSON")
    try:
        payload = json.loads(text[start:end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError("completion decision is invalid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("completion decision must be an object")
    return payload


def build_completion_prompt(
    curriculum: Curriculum,
    manifest: LessonManifest,
    evidence: CompletionEvidence,
) -> str:
    criteria = [page.completion_criteria for page in manifest.pages if page.completion_criteria]
    quiz = [attempt.model_dump() for attempt in evidence.quiz_attempts]
    return f"""你是严格、温和的学习评价模型。判断学习者是否真正掌握当前知识点。

主题：{curriculum.topic}
当前知识点：{curriculum.current_knowledge_point_id}
本课提交要求：{manifest.completion_prompt}
页面完成标准：{'；'.join(criteria) or '以本课提交要求为准'}
用户选择的动作：{evidence.action}
客观随堂题记录：{json.dumps(quiz, ensure_ascii=False)}
用户提交证据：{evidence.evidence or '未提交文字证据'}

不要调用任何工具、不要读取文件；只根据以上证据判断。只输出 JSON：verdict, feedback, mastery_score。
verdict 只能是 advance、practice、reteach：
- advance：有足够运行、推理或表达证据，允许进入下一个知识点；
- practice：基本理解但证据不足或需要一道针对性练习；
- reteach：核心理解错误、明确求助或需要换一种讲法。
mastery_score 必须是 0–100 的整数。feedback 必须先给结论，再指出一条具体证据和下一步，不要泛泛夸奖。
"""


def evaluate_completion(
    curriculum: Curriculum,
    manifest: LessonManifest,
    evidence: CompletionEvidence,
    *,
    model_call: Callable[[str], str],
) -> CompletionDecision:
    required_checks = {page.id: page.title for page in manifest.pages if page.question and page.options}
    latest_attempts = {attempt.page_id: attempt.correct for attempt in evidence.quiz_attempts}
    missing_checks = [title for page_id, title in required_checks.items() if latest_attempts.get(page_id) is not True]
    if missing_checks:
        decision = CompletionDecision(
            verdict="practice",
            feedback=f"这些选择题还需要先答对：{'、'.join(missing_checks)}。回到对应页面直接点击选项，不需要写文字回答。",
            mastery_score=45,
            cta_label="回到选择题再试",
        )
        decision.covered_knowledge_point_ids = list(manifest.covered_knowledge_point_ids)
        return decision
    if manifest.completion_mode in {"self_practice", "output", "evidence"}:
        return CompletionDecision(
            verdict="advance",
            feedback="课堂选择题已经完成。课后练习已留在项目目录，你可以自己练；完成后的代码、运行结果或问题直接发到右侧输入栏即可。",
            mastery_score=70,
            next_action="advance",
            cta_label="完成课堂，进入下一章",
            covered_knowledge_point_ids=list(manifest.covered_knowledge_point_ids),
        )
    if manifest.completion_mode == "choice":
        return CompletionDecision(
            verdict="advance",
            feedback="必答选择题都已通过，你已经抓住了这个概念的核心。",
            mastery_score=100,
            next_action="advance",
            cta_label="完成这个概念",
            covered_knowledge_point_ids=list(manifest.covered_knowledge_point_ids),
        )
    payload = _extract_json(model_call(build_completion_prompt(curriculum, manifest, evidence)))
    score = payload.get("mastery_score")
    if isinstance(score, float) and 0 <= score <= 1:
        payload["mastery_score"] = round(score * 100)
    decision = CompletionDecision.model_validate(payload)
    decision.covered_knowledge_point_ids = list(manifest.covered_knowledge_point_ids)
    decision.next_action = decision.verdict
    decision.next_knowledge_point_id = curriculum.current_knowledge_point_id
    decision.cta_label = {
        "advance": "开始下一章",
        "practice": "做一道针对性练习",
        "reteach": "换一种讲法",
    }[decision.verdict]
    return decision


def _atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def _read_state(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def apply_completion_decision(
    server_root: Path,
    user_id: str,
    curriculum: Curriculum,
    evidence: CompletionEvidence,
    decision: CompletionDecision,
) -> CompletionDecision:
    if not SAFE_USER_ID.fullmatch(user_id):
        raise ValueError("invalid user_id")
    points = curriculum.knowledge_points()
    current_index = next(
        index for index, point in enumerate(points)
        if point.id == curriculum.current_knowledge_point_id
    )
    current = points[current_index]
    if decision.verdict == "advance":
        covered_ids = decision.covered_knowledge_point_ids or [current.id]
        covered = [point for point in points if point.id in covered_ids]
        if current.id not in {point.id for point in covered}:
            covered = [current]
        for point in covered:
            point.status = "completed"
        last_covered_index = max(points.index(point) for point in covered)
        next_point = next(
            (point for point in points[last_covered_index + 1:] if point.status != "completed"),
            None,
        )
        if next_point is not None:
            next_point.status = "active"
            curriculum.current_knowledge_point_id = next_point.id
            decision.next_knowledge_point_id = next_point.id
            decision.cta_label = f"开始下一章：{next_point.title}"
        else:
            decision.next_knowledge_point_id = None
            decision.cta_label = "查看课程总结"
    else:
        current.status = "active"
        decision.next_knowledge_point_id = current.id

    save_curriculum(server_root, user_id, curriculum)
    user_dir = server_root / "userdir" / f"u_{user_id}"
    state_path = user_dir / "learning-state.json"
    state = _read_state(state_path)
    revision = state.get("revision")
    state["revision"] = revision + 1 if isinstance(revision, int) else 1
    state["active_task"] = curriculum.current_knowledge_point_id
    recent = state.get("recent_evidence")
    recent = recent if isinstance(recent, list) else []
    recent.append(
        f"{current.id} · {decision.verdict} · {decision.mastery_score} 分 · "
        f"{evidence.evidence[-1000:] or '课堂选择题完成；课后练习自主进行'}"
    )
    state["recent_evidence"] = recent[-10:]
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    _atomic_text(state_path, json.dumps(state, ensure_ascii=False, indent=2) + "\n")

    active_plan = state.get("active_plan")
    if isinstance(active_plan, str) and active_plan.strip():
        plan_path = (user_dir / active_plan).resolve()
        if plan_path == user_dir.resolve() or user_dir.resolve() in plan_path.parents:
            _atomic_text(plan_path, render_curriculum_plan(curriculum))

    attempts = user_dir / "attempts" / "lesson-completions.jsonl"
    attempts.parent.mkdir(parents=True, exist_ok=True)
    with attempts.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "at": state["updated_at"],
                    "knowledge_point_id": current.id,
                    "evidence": evidence.model_dump(),
                    "decision": decision.model_dump(),
                },
                ensure_ascii=False,
            )
            + "\n"
        )
    return decision
