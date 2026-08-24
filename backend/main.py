"""FastAPI bridge for the Learning Agent web workbench."""

from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

try:
    from .codex_driver import chat, latest_release, stream_chat
    from .curriculum import curriculum_from_plan, load_curriculum, render_curriculum_plan, save_curriculum
    from .diagnostics import (
        answer_diagnosis,
        build_diagnosis_prompt,
        has_curated_bank,
        parse_generated_diagnosis,
        public_session,
        start_diagnosis,
        summarize_diagnosis,
    )
    from .learning_content import default_exercise, read_learning_context
    from .learning_intent import IntentSlots, build_intent_correction_prompt, build_intent_prompt, parse_intent_response, recover_explicit_interview_intent, validate_intent_against_message
    from .knowledge_library import load_completed_chapter, save_completed_chapter
    from .lesson_generator import generate_and_save_lesson, load_lesson_bundle, save_lesson_bundle
    from .lesson_manifest import ensure_practice_workspace, resolve_practice_folder
    from .lesson_progression import CompletionEvidence, QuizAttempt, apply_completion_decision, evaluate_completion
    from .learning_plan_personalizer import active_plan_path, build_plan_prompt, build_plan_revision_prompt, normalize_and_validate_plan, replace_plan, requires_authoritative_research, set_plan_status
    from .research_artifact import load_valid_research, render_research_evidence
    from .interview_bank import InterviewBankStore
    from .interview_coach import expand_question
    from .interview_plan import reconcile_interview_plan
    from .llm import chat as llm_chat
    from .onboarding import DiagnosisSummary, OnboardingSubmission, confirm_onboarding, needs_diagnosis
    from .project_snapshot import archive_project_snapshot, create_project_snapshot, delete_learning_project, discard_project_snapshot, find_learning_project, list_learning_projects, restore_project_snapshot, switch_project_archive
    from .practice_bank import PracticeBankStore
    from .review_material import append_attempt, append_learning_question, append_lesson_note, read_lesson_notes, read_review_document
    from .reminders import ReminderScheduler, read_reminder, save_reminder
    from .review_cards import rate_card, read_cards
    from .supplemental_practice import parse_supplemental_response
except ImportError:
    from codex_driver import chat, latest_release, stream_chat
    from curriculum import curriculum_from_plan, load_curriculum, render_curriculum_plan, save_curriculum
    from diagnostics import answer_diagnosis, build_diagnosis_prompt, has_curated_bank, parse_generated_diagnosis, public_session, start_diagnosis, summarize_diagnosis
    from learning_content import default_exercise, read_learning_context
    from learning_intent import IntentSlots, build_intent_correction_prompt, build_intent_prompt, parse_intent_response, recover_explicit_interview_intent, validate_intent_against_message
    from knowledge_library import load_completed_chapter, save_completed_chapter
    from lesson_generator import generate_and_save_lesson, load_lesson_bundle, save_lesson_bundle
    from lesson_manifest import ensure_practice_workspace, resolve_practice_folder
    from lesson_progression import CompletionEvidence, QuizAttempt, apply_completion_decision, evaluate_completion
    from learning_plan_personalizer import active_plan_path, build_plan_prompt, build_plan_revision_prompt, normalize_and_validate_plan, replace_plan, requires_authoritative_research, set_plan_status
    from research_artifact import load_valid_research, render_research_evidence
    from interview_bank import InterviewBankStore
    from interview_coach import expand_question
    from interview_plan import reconcile_interview_plan
    from llm import chat as llm_chat
    from onboarding import DiagnosisSummary, OnboardingSubmission, confirm_onboarding, needs_diagnosis
    from project_snapshot import archive_project_snapshot, create_project_snapshot, delete_learning_project, discard_project_snapshot, find_learning_project, list_learning_projects, restore_project_snapshot, switch_project_archive
    from practice_bank import PracticeBankStore
    from review_material import append_attempt, append_learning_question, append_lesson_note, read_lesson_notes, read_review_document
    from reminders import ReminderScheduler, read_reminder, save_reminder
    from review_cards import rate_card, read_cards
    from supplemental_practice import parse_supplemental_response

SERVER_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = SERVER_ROOT / "frontend"
HOST = "127.0.0.1"
PORT = 8787
logger = logging.getLogger(__name__)


def _intent_skill_text(release: Path) -> str:
    """Load the exact workspace Skill used by the fast onboarding router."""

    candidates = (
        release / ".codex" / "skills" / "learning-intent-router" / "SKILL.md",
        SERVER_ROOT / "workspace" / "dev" / ".codex" / "skills" / "learning-intent-router" / "SKILL.md",
    )
    for path in candidates:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    raise FileNotFoundError("learning-intent-router Skill is unavailable")


def intent_chat(prompt: str, skill_text: str) -> str:
    """Run one low-latency, non-thinking DeepSeek decision with the Skill injected."""

    system = (
        "你是 Learning Agent 的快速意图路由器。以下 SKILL.md 是本轮最高优先级业务规则。"
        "严格按它判断，只返回用户提示中要求的 JSON。\n\n"
        + skill_text
    )
    return llm_chat(
        prompt,
        system=system,
        model="deepseek-v4-flash",
        max_tokens=1_100,
        temperature=0.0,
        thinking=False,
        json_object=True,
        timeout=45,
    )

app = FastAPI(
    title="Learning Agent",
    version="3.0.0",
    docs_url="/api/docs",
    redoc_url=None,
)

for route, folder in (("/css", "css"), ("/js", "js"), ("/assets", "assets")):
    target = FRONTEND / folder
    target.mkdir(parents=True, exist_ok=True)
    app.mount(route, StaticFiles(directory=target), name=folder)


@app.middleware("http")
async def disable_frontend_asset_cache(request: Any, call_next: Any) -> Any:
    """Local iterations must not keep an old UI talking to new APIs."""
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith(("/css/", "/js/")):
        response.headers["Cache-Control"] = "no-store"
    return response


class HistoryItem(BaseModel):
    role: str = Field(pattern="^(user|agent|assistant)$")
    content: str = Field(min_length=1, max_length=20_000)


class ChatRequest(BaseModel):
    user_id: str = Field(default="yang", max_length=64)
    message: str = Field(min_length=1, max_length=20_000)
    lesson_id: str | None = Field(default=None, max_length=96, pattern=r"^[A-Za-z0-9_-]+$")
    history: list[HistoryItem] = Field(default_factory=list, max_length=24)


class IntentRequest(BaseModel):
    user_id: str = Field(default="yang", min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=4_000)
    history: list[HistoryItem] = Field(default_factory=list, max_length=8)
    slots: IntentSlots = Field(default_factory=IntentSlots)
    has_active_project: bool = False
    clarification_count: int = Field(default=0, ge=0, le=10)


class GradeRequest(BaseModel):
    user_id: str = Field(default="yang", max_length=64)
    question: str = Field(min_length=1, max_length=10_000)
    answer: str = Field(min_length=1, max_length=20_000)
    kind: str = Field(default="text", max_length=64)


class ExerciseGenerateRequest(BaseModel):
    user_id: str = Field(default="yang", max_length=64)
    module: str = Field(min_length=1, max_length=500)
    level: str = Field(default="beginner", max_length=64)


class SupplementalPracticeRequest(ExerciseGenerateRequest):
    count: int = Field(default=3, ge=3, le=5)


class OnboardingConfirmRequest(OnboardingSubmission):
    diagnostic_session_id: str | None = Field(default=None, max_length=64)


class PlanConfirmRequest(BaseModel):
    user_id: str = Field(default="yang", min_length=1, max_length=64)


class PlanRevisionRequest(OnboardingSubmission):
    feedback: str = Field(min_length=2, max_length=4_000)


class DiagnosticAnswerRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    session_id: str = Field(min_length=1, max_length=64)
    question_id: str = Field(min_length=1, max_length=128)
    selected_option_id: str = Field(min_length=1, max_length=64)


class LessonCheckRequest(BaseModel):
    user_id: str = Field(default="yang", max_length=64)
    lesson_id: str = Field(min_length=1, max_length=96)
    page_id: str = Field(min_length=1, max_length=96)
    selected_option_id: str = Field(min_length=1, max_length=32)


class LessonGenerateRequest(BaseModel):
    user_id: str = Field(default="yang", min_length=1, max_length=64)
    remediation: str = Field(default="", max_length=2_000)
    force: bool = False


class CurriculumGenerateRequest(BaseModel):
    user_id: str = Field(default="yang", min_length=1, max_length=64)


class LessonCompleteRequest(BaseModel):
    user_id: str = Field(default="yang", min_length=1, max_length=64)
    lesson_id: str = Field(min_length=1, max_length=96)
    action: str = Field(pattern="^(submit|reteach|stuck)$")
    evidence: str = Field(default="", max_length=20_000)
    output_values: dict[str, str] = Field(default_factory=dict, max_length=6)
    quiz_attempts: list[QuizAttempt] = Field(default_factory=list, max_length=30)


class PracticeOpenRequest(BaseModel):
    user_id: str = Field(default="yang", min_length=1, max_length=64)
    path: str = Field(min_length=1, max_length=240)


class ProjectSnapshotRequest(BaseModel):
    user_id: str = Field(default="yang", min_length=1, max_length=64)
    snapshot_id: str | None = Field(default=None, max_length=32)


class ProjectSwitchRequest(BaseModel):
    user_id: str = Field(default="yang", min_length=1, max_length=64)
    project_id: str = Field(min_length=24, max_length=24, pattern=r"^[a-f0-9]{24}$")


class ReminderRequest(BaseModel):
    user_id: str = Field(default="yang", max_length=64)
    enabled: bool = True
    time: str = Field(default="20:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    kind: str = Field(default="both", pattern="^(learn|review|both)$")


class ReviewRatingRequest(BaseModel):
    user_id: str = Field(default="yang", max_length=64)
    card_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
    title: str = Field(min_length=1, max_length=240)
    rating: str = Field(pattern="^(forgot|hard|easy)$")


class PracticeReviewItemRequest(BaseModel):
    user_id: str = Field(default="yang", max_length=64)
    item_id: str = Field(min_length=1, max_length=240)


class PracticeReviewRateRequest(PracticeReviewItemRequest):
    rating: str = Field(pattern="^(forgot|hard|easy)$")


class InterviewIntakeRequest(BaseModel):
    user_id: str = Field(default="yang", min_length=1, max_length=64)
    raw_text: str = Field(min_length=2, max_length=50_000)
    source: str = Field(default="chat", max_length=64)


class InterviewStudyModeRequest(BaseModel):
    user_id: str = Field(default="yang", min_length=1, max_length=64)
    mode: str = Field(pattern="^(from_scratch|systematic|assess_first)$")


class InterviewMasteryRequest(BaseModel):
    user_id: str = Field(default="yang", min_length=1, max_length=64)
    mastery: str = Field(pattern="^(forgot|hard|smooth)$")


INTERVIEW_STUDY_CHOICES = [
    {"value": "from_scratch", "label": "逐题从头讲", "description": "每道题先建立直觉，再组织面试表达"},
    {"value": "systematic", "label": "系统学习", "description": "按知识依赖重排，补齐相关知识体系"},
    {"value": "assess_first", "label": "先测后学", "description": "先像真实面试一样回答，再针对薄弱处讲解"},
]


def _interview_payload(user_id: str) -> dict[str, Any]:
    store = InterviewBankStore(SERVER_ROOT)
    questions = store.list_questions(user_id)
    state_payload = read_state(user_id).get("state") or {}
    reconciled = reconcile_interview_plan(state_payload, questions)
    return {
        "study_mode": store.read_bank(user_id).get("study_mode"),
        "questions": questions,
        "coverage": reconciled["bank_coverage"],
        "plan_progress": {
            "display_progress": reconciled.get("display_progress", 0),
            "progress_floor": reconciled.get("progress_floor", 0),
        },
    }


def _practice_payload(user_id: str) -> dict[str, Any]:
    practice = PracticeBankStore(SERVER_ROOT).read_bank(user_id)
    interview = _interview_payload(user_id)
    interview_items = [
        {
            **question,
            "source": "interview",
            "kind": "interview",
            "title": question.get("normalized_text") or "面试题",
            "prompt": question.get("normalized_text") or "",
            "status": "mastered" if question.get("mastery") == "smooth" else "incorrect" if question.get("mastery") == "forgot" else "unattempted",
            "needs_review": question.get("mastery") in {"forgot", "hard"},
            "attempt_count": len(question.get("evidence") or []),
            "wrong_count": sum(item.get("value") == "forgot" for item in question.get("evidence") or []),
        }
        for question in interview["questions"]
    ]
    important_items = [
        {
            "id": card["card_id"],
            "source": "important_question",
            "kind": "short_answer",
            "title": card.get("title") or "重要问题",
            "normalized_text": card.get("title") or "",
            "prompt": card.get("title") or "",
            "options": [],
            "status": "mastered" if card.get("last_rating") == "easy" else "incorrect" if card.get("last_rating") == "forgot" else "unattempted",
            "needs_review": card.get("last_rating") in {None, "forgot", "hard"},
            "attempt_count": int(card.get("attempts") or 0),
            "wrong_count": sum(
                item.get("rating") == "forgot" for item in card.get("review_history") or []
            ),
            "next_review": card.get("next_review"),
        }
        for card in read_cards(SERVER_ROOT, user_id).get("cards", {}).values()
        if isinstance(card, dict) and card.get("summary")
    ]
    questions = [*practice["questions"], *interview_items, *important_items]
    mastered = sum(question.get("status") == "mastered" for question in questions)
    total = len(questions)
    return {
        "study_mode": interview.get("study_mode"),
        "questions": [
            {
                key: value for key, value in question.items()
                if key not in {
                    "answer", "answer_markdown", "correct_option_id", "explanation",
                    "review_history", "rubric", "follow_ups",
                }
            }
            for question in questions
        ],
        "coverage": {
            "mastered": mastered,
            "total": total,
            "percent": round(mastered * 100 / total) if total else 0,
        },
        "plan_progress": interview.get("plan_progress", {}),
    }


def _unified_review_session(user_id: str, *, limit: int = 5) -> dict[str, Any]:
    practice = PracticeBankStore(SERVER_ROOT).review_session(user_id, limit=20)
    today = date.today().isoformat()
    interview_cards = []
    for question in InterviewBankStore(SERVER_ROOT).list_questions(user_id):
        next_review = str(question.get("next_review") or "")
        if question.get("answer_status") != "ready" or not question.get("answer_markdown"):
            continue
        if next_review and next_review > today:
            continue
        interview_cards.append({
            "id": question["id"],
            "source": "interview",
            "kind": "interview",
            "title": question.get("normalized_text") or "面试题",
            "prompt": question.get("normalized_text") or "",
            "options": [],
            "needs_review": question.get("mastery") in {"forgot", "hard"},
            "wrong_count": sum(
                item.get("value") == "forgot" for item in question.get("evidence") or []
            ),
            "next_review": question.get("next_review"),
        })
    important_cards = []
    for card in read_cards(SERVER_ROOT, user_id).get("cards", {}).values():
        next_review = str(card.get("next_review") or "")
        if not card.get("summary") or (next_review and next_review > today):
            continue
        important_cards.append({
            "id": card["card_id"],
            "source": "important_question",
            "kind": "short_answer",
            "title": card.get("title") or "重要问题",
            "prompt": card.get("title") or "",
            "options": [],
            "needs_review": card.get("last_rating") in {"forgot", "hard"},
            "wrong_count": sum(
                item.get("rating") == "forgot" for item in card.get("review_history") or []
            ),
            "next_review": card.get("next_review"),
        })
    cards = [*practice["cards"], *interview_cards, *important_cards]
    cards.sort(key=lambda item: (
        0 if item.get("needs_review") else 1,
        0 if item.get("source") == "interview" else 1,
        str(item.get("next_review") or "0000-00-00"),
        -int(item.get("wrong_count") or 0),
    ))
    selected = cards[:limit]
    return {"cards": selected, "total": len(selected), "due_count": len(cards)}


def read_state(user_id: str) -> dict[str, Any]:
    user_dir = SERVER_ROOT / "userdir" / f"u_{user_id}"
    state_file = user_dir / "learning-state.json"
    profile_file = user_dir / "profile.md"
    state: dict[str, Any] = {}
    if state_file.exists():
        try:
            value = json.loads(state_file.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                state = value
        except json.JSONDecodeError:
            state = {"error": "state 文件损坏"}
    profile = profile_file.read_text(encoding="utf-8") if profile_file.exists() else ""
    return {"user_id": user_id, "state": state, "profile": profile}


def build_prompt(user_id: str, history: list[HistoryItem], message: str) -> str:
    """Add only a small recent window for one-shot Codex executions."""
    state_payload = read_state(user_id).get("state") or {}
    lines: list[str] = []
    if state_payload.get("profile_status") == "confirmed":
        lines.append(
            "（画像已由界面确认；禁止继续摸底或要求再次确认；"
            "用户说‘开始吧’时立即讲一个核心概念；其他情况直接回答用户当前的问题，每轮只推进一个小步。"
            "课堂选择题只在 HTML PPT 内以按钮出现；"
            "选择题和动手题不能同轮：课堂完成选择题，课后再独立动手练习；"
            "回答完不要再追加一道要求用户作答的文字题，也不要让用户在聊天框输入 A/B/C。"
            "不要播报读取状态、路由 Skill、检查 Schema 或核对规则等内部过程；第一句直接教学。）"
        )
        lines.append(
            "（练习目录由界面和后端预先创建：不要另造项目路径，也不要要求全局 pip install。"
            "需要依赖时先说明如何检查现有项目环境，再给最小且可撤销的操作。）"
        )
        lines.append(
            "（课堂只用点击选择题；课后练习由学习者自己完成。用户发送代码、运行结果、报错或问题时，"
            "直接答疑和总结，不要求逐项粘贴打印结果，不把输出检测当作进入下一章的门禁。"
            "如果回答包含代码，代码必须有详细中文注释，并先给最小可理解骨架，不能突然倾倒长代码。）"
        )
    if history:
        lines.append("（以下是最近对话，只用于避免重复。请继续当前学习目标。）")
    for item in history[-12:]:
        role = "用户" if item.role == "user" else "学习教练"
        content = item.content.strip()
        if len(content) > 500:
            content = content[:500] + "…"
        lines.append(f"{role}：{content}")
    if lines:
        lines.extend(("", "用户刚才说：" + message.strip()))
    else:
        lines.append(message.strip())
    return "\n".join(lines)


def _diagnostic_path(user_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", user_id):
        raise HTTPException(status_code=422, detail="invalid user_id")
    return SERVER_ROOT / "userdir" / f"u_{user_id}" / "onboarding" / "diagnostic.json"


def _write_diagnostic(user_id: str, session: dict[str, Any]) -> None:
    path = _diagnostic_path(user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _read_diagnostic(user_id: str, session_id: str) -> dict[str, Any]:
    path = _diagnostic_path(user_id)
    try:
        session = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        session = None
    if not isinstance(session, dict) or session.get("session_id") != session_id:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "诊断会话已失效，请重新开始。",
                "recovery": "restart_diagnosis",
            },
        )
    return session


def format_sse(item: dict[str, Any]) -> str:
    event = str(item.get("event") or "message")
    data = item.get("data")
    if not isinstance(data, dict):
        data = {"value": data}
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(FRONTEND / "index.html", media_type="text/html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "model": "deepseek-v4-flash",
        "backend": "fastapi",
        "streaming": True,
    }


@app.get("/api/state")
def state(user_id: str = Query(default="yang", max_length=64)) -> dict[str, Any]:
    return read_state(user_id)


@app.post("/api/interview/intake")
def interview_intake(request: InterviewIntakeRequest) -> dict[str, Any]:
    try:
        result = InterviewBankStore(SERVER_ROOT).intake(
            request.user_id, request.raw_text, source=request.source,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    payload = _interview_payload(request.user_id)
    return {"intake": result, "study_choices": INTERVIEW_STUDY_CHOICES, **payload}


@app.get("/api/interview/bank")
def interview_bank(user_id: str = Query(default="yang", max_length=64)) -> dict[str, Any]:
    try:
        return _interview_payload(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/practice/bank")
def practice_bank(user_id: str = Query(default="yang", max_length=64)) -> dict[str, Any]:
    """Return classroom choices, homework, and interview questions in one bank."""
    try:
        return _practice_payload(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/practice/review/session")
def practice_review_session(
    user_id: str = Query(default="yang", max_length=64),
    limit: int = Query(default=5, ge=1, le=20),
) -> dict[str, Any]:
    try:
        return _unified_review_session(user_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/practice/review/reveal")
def practice_review_reveal(request: PracticeReviewItemRequest) -> dict[str, Any]:
    try:
        if request.item_id.startswith("question:"):
            card = read_cards(SERVER_ROOT, request.user_id).get("cards", {}).get(request.item_id)
            if not isinstance(card, dict) or not card.get("summary"):
                raise KeyError(request.item_id)
            return {
                "id": request.item_id,
                "answer": card["summary"],
                "explanation": f"关联主题：{card.get('topic') or '当前课程'}",
                "last_wrong": None,
            }
        if request.item_id.startswith("iq_"):
            question = InterviewBankStore(SERVER_ROOT).get_question(
                request.user_id, request.item_id,
            )
            if question.get("answer_status") != "ready" or not question.get("answer_markdown"):
                raise KeyError(request.item_id)
            last_wrong = next((
                evidence for evidence in reversed(question.get("evidence") or [])
                if evidence.get("value") == "forgot"
            ), None)
            return {
                "id": request.item_id,
                "answer": question["answer_markdown"],
                "explanation": "\n".join(f"- {item}" for item in question.get("rubric") or []),
                "last_wrong": last_wrong,
            }
        return PracticeBankStore(SERVER_ROOT).reveal_review_item(
            request.user_id, request.item_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="复习题不存在或还没有参考答案") from exc


@app.post("/api/practice/review/rate")
def practice_review_rate(request: PracticeReviewRateRequest) -> dict[str, Any]:
    try:
        if request.item_id.startswith("question:"):
            card = read_cards(SERVER_ROOT, request.user_id).get("cards", {}).get(request.item_id)
            if not isinstance(card, dict):
                raise KeyError(request.item_id)
            return rate_card(
                SERVER_ROOT,
                request.user_id,
                card_id=request.item_id,
                title=str(card.get("title") or "重要问题"),
                rating=request.rating,
            )
        if request.item_id.startswith("iq_"):
            return InterviewBankStore(SERVER_ROOT).record_mastery(
                request.user_id,
                request.item_id,
                {"forgot": "forgot", "hard": "hard", "easy": "smooth"}[request.rating],
            )
        return PracticeBankStore(SERVER_ROOT).rate_review_item(
            request.user_id, item_id=request.item_id, rating=request.rating,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="复习题不存在或还没有参考答案") from exc


@app.post("/api/practice/supplemental/generate")
def generate_supplemental_practice(request: SupplementalPracticeRequest) -> dict[str, Any]:
    skill_texts = []
    for skill_name in ("practice-drill", "quiz-designer"):
        candidates = (
            SERVER_ROOT / "workspace/dev/.codex/skills" / skill_name / "SKILL.md",
            SERVER_ROOT / "workspace/releases/current/.codex/skills" / skill_name / "SKILL.md",
        )
        skill_path = next((path for path in candidates if path.is_file()), None)
        if skill_path is None:
            raise HTTPException(status_code=503, detail=f"教学 Skill 不可用：{skill_name}")
        skill_texts.append(skill_path.read_text(encoding="utf-8"))
    system = (
        "你是 Learning Agent 的针对性练习设计器。必须严格遵守下面两个教学 Skill。\n\n"
        + "\n\n---\n\n".join(skill_texts)
        + "\n\n只输出 JSON：{\"questions\":[...]}。每题字段为 title、prompt、options、"
        "correct_option_id、explanation。options 必须有 2 至 4 项且只有一个最佳答案；"
        "答案 id 必须属于 options。题目不得重复，必须检验理解或迁移，不考无意义术语背诵。"
    )
    raw = llm_chat(
        f"模块：{request.module}\n学习程度：{request.level}\n请生成 {request.count} 道题。",
        system=system,
        max_tokens=3200,
        temperature=0.2,
    )
    try:
        questions = parse_supplemental_response(raw, expected_count=request.count)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=f"练习题没有通过结构校验：{exc}") from exc
    result = PracticeBankStore(SERVER_ROOT).add_supplemental_questions(
        request.user_id, topic=request.module, questions=questions,
    )
    return {**result, "requested_count": request.count, "source": "supplemental"}


@app.get("/api/interview/questions/{question_id}")
def interview_question(
    question_id: str,
    user_id: str = Query(default="yang", max_length=64),
) -> dict[str, Any]:
    try:
        return {"question": InterviewBankStore(SERVER_ROOT).get_question(user_id, question_id)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="面试题不存在") from exc


@app.post("/api/interview/questions/{question_id}/mastery")
def interview_question_mastery(
    question_id: str,
    request: InterviewMasteryRequest,
) -> dict[str, Any]:
    try:
        question = InterviewBankStore(SERVER_ROOT).record_mastery(
            request.user_id, question_id, request.mastery,
        )
        return {"question": question, **_interview_payload(request.user_id)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="面试题不存在") from exc


@app.post("/api/interview/study-mode")
def interview_study_mode(request: InterviewStudyModeRequest) -> dict[str, Any]:
    try:
        bank = InterviewBankStore(SERVER_ROOT).set_study_mode(request.user_id, request.mode)
        return {"study_mode": bank["study_mode"], "study_choices": INTERVIEW_STUDY_CHOICES}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/interview/questions/{question_id}/expand")
def interview_question_expand(
    question_id: str,
    request: InterviewStudyModeRequest,
) -> dict[str, Any]:
    def interview_model(prompt: str, system: str) -> str:
        return llm_chat(prompt, system=system, max_tokens=2400, temperature=0.15)

    try:
        return expand_question(
            InterviewBankStore(SERVER_ROOT), request.user_id, question_id,
            interview_model, mode=request.mode,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="面试题不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/reminders")
def get_reminder(user_id: str = Query(default="yang", max_length=64)) -> dict[str, Any]:
    try:
        return read_reminder(SERVER_ROOT, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/reminders")
def update_reminder(request: ReminderRequest) -> dict[str, Any]:
    try:
        return save_reminder(
            SERVER_ROOT,
            request.user_id,
            enabled=request.enabled,
            reminder_time=request.time,
            kind=request.kind,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/review/cards")
def review_cards(user_id: str = Query(default="yang", max_length=64)) -> dict[str, Any]:
    try:
        return read_cards(SERVER_ROOT, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/review/rate")
def review_rate(request: ReviewRatingRequest) -> dict[str, Any]:
    try:
        return rate_card(
            SERVER_ROOT, request.user_id, card_id=request.card_id,
            title=request.title, rating=request.rating,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/learning-context")
def learning_context(
    user_id: str = Query(default="yang", max_length=64),
) -> dict[str, Any]:
    return read_learning_context(user_id, SERVER_ROOT)


@app.get("/api/lesson/current")
def current_lesson(
    user_id: str = Query(default="yang", max_length=64),
) -> dict[str, Any]:
    context = read_learning_context(user_id, SERVER_ROOT)
    if context["profile_status"] != "confirmed":
        raise HTTPException(
            status_code=409,
            detail={
                "message": "先用几个点击选项确定学习目标，就可以立即开始。",
                "recovery": "complete_onboarding",
            },
        )
    if context.get("plan_status") != "confirmed":
        raise HTTPException(
            status_code=409,
            detail={
                "message": "请先查看并确认学习计划，再开始第一章。",
                "recovery": "confirm_plan",
            },
        )
    try:
        curriculum = load_curriculum(SERVER_ROOT, user_id)
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "需要先根据你的目标生成详细课程大纲。",
                "recovery": "generate_curriculum",
            },
        ) from exc
    try:
        bundle = load_lesson_bundle(
            SERVER_ROOT, user_id, curriculum.current_knowledge_point_id,
        )
        if not bundle.manifest.chapter_id or not bundle.manifest.covered_knowledge_point_ids:
            raise ValueError("legacy single-point lesson must be regenerated as a chapter")
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "正在为当前知识点准备个性化课程。",
                "recovery": "generate_lesson",
            },
        ) from exc
    ensure_practice_workspace(SERVER_ROOT, user_id, bundle.manifest)
    PracticeBankStore(SERVER_ROOT).register_lesson(
        user_id, bundle.manifest, answer_keys=bundle.answer_keys,
    )
    return bundle.public_manifest()


@app.post("/api/lesson/generate")
def generate_lesson(request: LessonGenerateRequest) -> dict[str, Any]:
    context = read_learning_context(request.user_id, SERVER_ROOT)
    if context["profile_status"] != "confirmed":
        raise HTTPException(status_code=409, detail={"recovery": "complete_onboarding"})
    try:
        curriculum = load_curriculum(SERVER_ROOT, request.user_id)
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={"message": "请先生成详细课程大纲。", "recovery": "generate_curriculum"},
        ) from exc
    if not request.force:
        try:
            existing = load_lesson_bundle(
                SERVER_ROOT, request.user_id, curriculum.current_knowledge_point_id,
            )
            if not existing.manifest.chapter_id or not existing.manifest.covered_knowledge_point_ids:
                raise ValueError("legacy single-point lesson must be regenerated as a chapter")
            ensure_practice_workspace(SERVER_ROOT, request.user_id, existing.manifest)
            PracticeBankStore(SERVER_ROOT).register_lesson(
                request.user_id, existing.manifest, answer_keys=existing.answer_keys,
            )
            return existing.public_manifest()
        except (OSError, ValueError):
            pass
        cached = load_completed_chapter(SERVER_ROOT, curriculum)
        if cached is not None:
            save_lesson_bundle(SERVER_ROOT, request.user_id, cached)
            try:
                migrated = load_lesson_bundle(
                    SERVER_ROOT, request.user_id, curriculum.current_knowledge_point_id,
                )
            except (OSError, ValueError):
                # Shared knowledge can outlive the teaching contract that created it.
                # If it cannot be upgraded safely, regenerate it instead of showing a
                # long first code dump or uncommented historical material.
                pass
            else:
                ensure_practice_workspace(SERVER_ROOT, request.user_id, migrated.manifest)
                PracticeBankStore(SERVER_ROOT).register_lesson(
                    request.user_id, migrated.manifest, answer_keys=migrated.answer_keys,
                )
                return migrated.public_manifest()
    release = latest_release()
    if release is None:
        raise HTTPException(
            status_code=503,
            detail={"message": "教学模型暂时不可用，请稍后重试。", "retryable": True},
        )
    profile = str(read_state(request.user_id).get("profile") or "")
    try:
        try:
            research_evidence = render_research_evidence(
                load_valid_research(SERVER_ROOT, request.user_id, curriculum.topic)
            )
        except (OSError, ValueError, json.JSONDecodeError):
            research_evidence = ""
        bundle = generate_and_save_lesson(
            SERVER_ROOT,
            request.user_id,
            curriculum=curriculum,
            profile=profile,
            recent_evidence=list(context.get("recent_evidence") or []),
            session_minutes=int(context.get("session_minutes") or 25),
            remediation=request.remediation,
            research_evidence=research_evidence,
            model_call=lambda prompt: chat(request.user_id, prompt, release),
        )
        ensure_practice_workspace(SERVER_ROOT, request.user_id, bundle.manifest)
        PracticeBankStore(SERVER_ROOT).register_lesson(
            request.user_id, bundle.manifest, answer_keys=bundle.answer_keys,
        )
    except Exception as exc:
        error_type = "validation" if isinstance(exc, (ValueError, TypeError, json.JSONDecodeError)) else "provider"
        message = (
            "课程内容已返回，但未通过结构检查。请重新生成。"
            if error_type == "validation"
            else "教学模型没有完成这次课程生成。请稍后重试。"
        )
        logger.exception(
            "lesson generation failed user_id=%s knowledge_point_id=%s error_type=%s",
            request.user_id,
            curriculum.current_knowledge_point_id,
            error_type,
        )
        raise HTTPException(
            status_code=502,
            detail={
                "message": message,
                "retryable": True,
                "error_stage": "lesson_generation",
                "error_type": error_type,
            },
        ) from exc
    return bundle.public_manifest()


@app.post("/api/lesson/remediate")
def remediate_lesson(request: LessonGenerateRequest) -> dict[str, Any]:
    """Regenerate the current lesson with a model-authored remedial angle."""
    return generate_lesson(request.model_copy(update={"force": True}))


@app.post("/api/lesson/check")
def check_lesson_answer(request: LessonCheckRequest) -> dict[str, Any]:
    context = read_learning_context(request.user_id, SERVER_ROOT)
    if context["profile_status"] != "confirmed":
        raise HTTPException(status_code=409, detail={"recovery": "complete_onboarding"})
    try:
        curriculum = load_curriculum(SERVER_ROOT, request.user_id)
        bundle = load_lesson_bundle(
            SERVER_ROOT, request.user_id, curriculum.current_knowledge_point_id,
        )
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=409, detail={"recovery": "reload_lesson"}) from exc
    if request.lesson_id != bundle.manifest.lesson_id or request.page_id not in bundle.answer_keys:
        raise HTTPException(status_code=409, detail={"recovery": "reload_lesson"})
    correct = bundle.answer_keys[request.page_id] == request.selected_option_id
    page = next(page for page in bundle.manifest.pages if page.id == request.page_id)
    practice_store = PracticeBankStore(SERVER_ROOT)
    practice_store.register_lesson(
        request.user_id, bundle.manifest, answer_keys=bundle.answer_keys,
    )
    practice_store.record_choice_attempt(
        request.user_id,
        lesson_id=request.lesson_id,
        page_id=request.page_id,
        selected_option_id=request.selected_option_id,
        correct=correct,
    )
    return {
        "correct": correct,
        "verified": correct,
        "feedback": (
            f"答对了。你已经抓住「{page.title}」的关键点。"
            if correct
            else f"还差一点。回到「{page.title}」前一页再看一次例子，然后重新选择。"
        ),
    }


@app.post("/api/lesson/complete")
def complete_lesson(request: LessonCompleteRequest) -> dict[str, Any]:
    context = read_learning_context(request.user_id, SERVER_ROOT)
    if context["profile_status"] != "confirmed":
        raise HTTPException(status_code=409, detail={"recovery": "complete_onboarding"})
    try:
        curriculum = load_curriculum(SERVER_ROOT, request.user_id)
        bundle = load_lesson_bundle(
            SERVER_ROOT, request.user_id, curriculum.current_knowledge_point_id,
        )
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=409, detail={"recovery": "reload_lesson"}) from exc
    if request.lesson_id != bundle.manifest.lesson_id:
        raise HTTPException(status_code=409, detail={"recovery": "reload_lesson"})
    evidence = CompletionEvidence(
        action=request.action,
        evidence=request.evidence,
        output_values=request.output_values,
        quiz_attempts=request.quiz_attempts,
    )
    release = latest_release() if bundle.manifest.completion_mode == "text" else None
    if bundle.manifest.completion_mode == "text" and release is None:
        raise HTTPException(
            status_code=503,
            detail={"message": "教学评价暂时不可用，请稍后重试。", "retryable": True},
        )
    try:
        decision = evaluate_completion(
            curriculum,
            bundle.manifest,
            evidence,
            model_call=lambda prompt: chat(request.user_id, prompt, release),
        )
        if decision.verdict == "advance":
            try:
                save_completed_chapter(SERVER_ROOT, curriculum, bundle)
            except OSError:
                pass
        applied = apply_completion_decision(
            SERVER_ROOT, request.user_id, curriculum, evidence, decision,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"message": "本课评价失败，请保留答案并重试。", "retryable": True},
        ) from exc
    return applied.model_dump()


@app.post("/api/practice/open")
def open_practice_folder(request: PracticeOpenRequest) -> dict[str, Any]:
    try:
        target = resolve_practice_folder(SERVER_ROOT, request.user_id, request.path)
        subprocess.run(["open", str(target)], check=True)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"message": "练习文件夹还没有创建，请重新打开本课。"},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"message": "这个练习路径不安全，已经停止打开。"},
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise HTTPException(
            status_code=500,
            detail={"message": "系统暂时无法打开文件夹，请稍后重试。"},
        ) from exc
    return {"opened": True, "path": request.path}


@app.post("/api/projects/snapshot")
def snapshot_project(request: ProjectSnapshotRequest) -> dict[str, Any]:
    try:
        return {"snapshot_id": create_project_snapshot(SERVER_ROOT, request.user_id)}
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=409, detail={"message": "当前课程暂时无法安全备份。"}) from exc


@app.post("/api/projects/restore")
def restore_project(request: ProjectSnapshotRequest) -> dict[str, Any]:
    if not request.snapshot_id:
        raise HTTPException(status_code=422, detail={"message": "缺少课程备份标识。"})
    try:
        restore_project_snapshot(SERVER_ROOT, request.user_id, request.snapshot_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"message": "课程备份已不存在。"}) from exc
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=409, detail={"message": "原课程恢复失败，请重试。"}) from exc
    return {"restored": True}


@app.post("/api/projects/snapshot/discard")
def discard_project(request: ProjectSnapshotRequest) -> dict[str, Any]:
    if not request.snapshot_id:
        raise HTTPException(status_code=422, detail={"message": "缺少课程备份标识。"})
    try:
        discard_project_snapshot(SERVER_ROOT, request.user_id, request.snapshot_id)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=409, detail={"message": "课程备份暂时无法清理。"}) from exc
    return {"discarded": True}


@app.post("/api/projects/snapshot/archive")
def archive_project(request: ProjectSnapshotRequest) -> dict[str, Any]:
    if not request.snapshot_id:
        raise HTTPException(status_code=422, detail={"message": "缺少课程备份标识。"})
    try:
        return {"project": archive_project_snapshot(SERVER_ROOT, request.user_id, request.snapshot_id)}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"message": "课程备份已不存在。"}) from exc


@app.get("/api/projects")
def list_projects(user_id: str = Query(default="yang", max_length=64)) -> dict[str, Any]:
    try:
        return {"projects": list_learning_projects(SERVER_ROOT, user_id)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"message": "用户标识不合法。"}) from exc


@app.get("/api/projects/match")
def match_project(
    user_id: str = Query(default="yang", min_length=1, max_length=64),
    topic: str = Query(min_length=1, max_length=240),
) -> dict[str, Any]:
    try:
        return {"project": find_learning_project(SERVER_ROOT, user_id, topic)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"message": "项目主题或用户标识不合法。"}) from exc


@app.delete("/api/projects/{project_id}")
def delete_project(
    project_id: str,
    user_id: str = Query(default="yang", min_length=1, max_length=64),
) -> dict[str, Any]:
    try:
        projects = delete_learning_project(SERVER_ROOT, user_id, project_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"message": "项目标识不合法。"}) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"message": "这个学习项目已经不存在。"}) from exc
    except OSError as exc:
        raise HTTPException(status_code=409, detail={"message": "项目暂时无法删除，请稍后重试。"}) from exc
    return {"deleted_project_id": project_id, "projects": projects}


@app.post("/api/projects/switch")
def switch_project(request: ProjectSwitchRequest) -> dict[str, Any]:
    try:
        return {"project": switch_project_archive(SERVER_ROOT, request.user_id, request.project_id)}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"message": "这个学习项目已不存在。"}) from exc
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=409, detail={"message": "切换学习项目失败，当前项目没有被清除。"}) from exc


@app.post("/api/onboarding/intent")
def onboarding_intent(request: IntentRequest) -> dict[str, Any]:
    """Ask the workspace Skill through Flash for one validated slot decision."""

    release = latest_release()
    if release is None:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "意图分析服务暂时不可用，你的输入已保留。",
                "retryable": True,
                "recovery": "retry_intent",
            },
        )
    prompt = build_intent_prompt(
        message=request.message,
        history=[item.model_dump() for item in request.history],
        slots=request.slots.model_dump(),
        has_active_project=request.has_active_project,
        clarification_count=request.clarification_count,
    )
    skill_text = _intent_skill_text(release)
    decision = None
    last_error: Exception | None = None
    # Flash models occasionally need one structural repair followed by one
    # semantic repair (for example: malformed JSON, then a repeated level
    # question). Keep the normal path at one call while allowing both repairs.
    for attempt in range(3):
        try:
            raw_decision = intent_chat(prompt, skill_text)
        except Exception as exc:
            # Transport, provider, authentication and timeout failures are not
            # repaired by asking the same unavailable service two more times.
            last_error = exc
            break
        try:
            decision = validate_intent_against_message(
                parse_intent_response(raw_decision), request.message,
                history=request.history,
                existing_slots=request.slots,
            )
            break
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                prompt = build_intent_correction_prompt(prompt, str(exc))
    if decision is None:
        decision = recover_explicit_interview_intent(request.message, request.slots)
    if decision is None:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "这次还没有分析出可靠的学习意图，可以直接重试。",
                "retryable": True,
                "recovery": "retry_intent",
            },
        ) from last_error
    return decision.model_dump()


@app.post("/api/onboarding/start")
def onboarding_start(request: OnboardingSubmission) -> dict[str, Any]:
    if not needs_diagnosis(request):
        return {"next": "confirm", "diagnosis_required": False}
    questions = None
    source = "fallback"
    release = latest_release()
    if release is not None:
        try:
            questions = parse_generated_diagnosis(
                chat(request.user_id, build_diagnosis_prompt(request.topic.value, request.level_claim, request.goal_route), release),
                expected_topic=request.topic.value,
            )
            source = "skill_generated"
        except (ValueError, json.JSONDecodeError):
            questions = None
    if questions is None and not has_curated_bank(request.topic.value, request.goal_route):
        raise HTTPException(status_code=502, detail={
            "message": "这次岗位专属诊断没有生成完成，你的目标已保留。",
            "retryable": True,
            "recovery": "retry_diagnosis",
        })
    session = start_diagnosis(request.topic.value, request.level_claim, questions=questions)
    session["diagnostic_source"] = source
    session["submission"] = request.model_dump()
    _write_diagnostic(request.user_id, session)
    payload = public_session(session)
    payload["next"] = "diagnosis"
    payload["diagnostic_source"] = source
    return payload


@app.post("/api/diagnostics/answer")
def diagnostic_answer(request: DiagnosticAnswerRequest) -> dict[str, Any]:
    session = _read_diagnostic(request.user_id, request.session_id)
    try:
        updated = answer_diagnosis(
            session,
            request.selected_option_id,
            question_id=request.question_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"message": str(exc), "recovery": "use_current_question"},
        ) from exc
    _write_diagnostic(request.user_id, updated)
    payload = public_session(updated)
    payload["next"] = "confirm" if updated["complete"] else "diagnosis"
    if updated["complete"]:
        payload["diagnosis"] = summarize_diagnosis(updated).model_dump()
    return payload


@app.post("/api/onboarding/confirm")
def onboarding_confirm(request: OnboardingConfirmRequest) -> dict[str, Any]:
    submission = OnboardingSubmission.model_validate(
        request.model_dump(exclude={"diagnostic_session_id"})
    )
    diagnosis = None
    if needs_diagnosis(submission):
        if not request.diagnostic_session_id:
            raise HTTPException(status_code=409, detail={"recovery": "restart_diagnosis"})
        session = _read_diagnostic(request.user_id, request.diagnostic_session_id)
        if not session.get("complete"):
            raise HTTPException(status_code=409, detail={"recovery": "continue_diagnosis"})
        diagnosis = summarize_diagnosis(session)
    try:
        return confirm_onboarding(SERVER_ROOT, submission, diagnosis)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/plans/personalize")
def personalize_plan(request: OnboardingSubmission) -> dict[str, Any]:
    try:
        plan_path = active_plan_path(SERVER_ROOT, request.user_id)
        fallback = plan_path.read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=409, detail={"message": "请先确认学习目标，再生成计划。"}) from exc

    release = latest_release()
    if release is None:
        return {"personalized": False, "active_plan": plan_path.name, "reason": "codex_unavailable", "user_message": "课程生成服务暂时不可用，你的目标已经保留，请稍后重试。"}
    stage = "model_generation"
    try:
        context = read_learning_context(request.user_id, SERVER_ROOT)
        knowledge_source = str(context.get("knowledge_source") or "skill_guided")
        state = (read_state(request.user_id).get("state") or {})
        raw_diagnosis = state.get("diagnosis")
        diagnosis = DiagnosisSummary.model_validate(raw_diagnosis) if isinstance(raw_diagnosis, dict) else None
        generated = chat(
            request.user_id,
            build_plan_prompt(request, fallback, knowledge_source, diagnosis=diagnosis),
            release,
        )
        if generated.lstrip().startswith(("[超时]", "[出错]", "[空回复]")):
            return {
                "personalized": False,
                "active_plan": plan_path.name,
                "reason": "model_generation_failed",
                "user_message": "课程生成超时或暂时中断，你的目标和选择都已保留，请直接重试。",
            }
        stage = "plan_validation"
        validated = normalize_and_validate_plan(generated, request.topic.value, request.goal_route)
        if validated is None:
            return {"personalized": False, "active_plan": plan_path.name, "reason": "validation_failed", "user_message": "课程草案已经生成，但完整性检查没有通过。原计划仍然保留，请重试生成。"}
        if requires_authoritative_research(request, knowledge_source):
            stage = "research_validation"
            load_valid_research(
                SERVER_ROOT,
                request.user_id,
                request.topic.value,
                require_deep=request.goal_route in {"foundation_engineer", "senior_engineer"},
            )
        stage = "curriculum_build"
        curriculum = curriculum_from_plan(
            validated,
            topic=request.topic.value,
            route=request.goal_route,
            level=request.level_claim,
        )
        save_curriculum(SERVER_ROOT, request.user_id, curriculum)
        replace_plan(plan_path, validated)
        set_plan_status(SERVER_ROOT, request.user_id, "awaiting_confirmation")
        plan_markdown = plan_path.read_text(encoding="utf-8")
        return {
            "personalized": True,
            "active_plan": plan_path.name,
            "current_knowledge_point_id": curriculum.current_knowledge_point_id,
            "plan_status": "awaiting_confirmation",
            "plan_markdown": plan_markdown,
        }
    except Exception as exc:
        user_messages = {
            "research_validation": "课程和资料已经生成，但权威资料的结构检查没有通过。原计划仍然保留，请重试。",
            "curriculum_build": "详细计划已经生成，但转换为课程大纲时没有通过检查。原计划仍然保留，请重试。",
            "model_generation": "课程生成暂时中断，你的目标和选择都已保留，请直接重试。",
        }
        return {
            "personalized": False,
            "active_plan": plan_path.name,
            "reason": f"{stage}_failed",
            "error_type": type(exc).__name__,
            "user_message": user_messages.get(stage, "课程生成暂时中断，你的目标和选择都已保留，请直接重试。"),
        }


@app.post("/api/plans/confirm")
def confirm_plan(request: PlanConfirmRequest) -> dict[str, Any]:
    try:
        active_plan_path(SERVER_ROOT, request.user_id)
        set_plan_status(SERVER_ROOT, request.user_id, "confirmed")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=409, detail={"message": "学习计划还没有准备好，请先重新生成。"}) from exc
    return {"user_id": request.user_id, "plan_status": "confirmed"}


@app.post("/api/plans/revise")
def revise_plan(request: PlanRevisionRequest) -> dict[str, Any]:
    try:
        plan_path = active_plan_path(SERVER_ROOT, request.user_id)
        current_plan = plan_path.read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=409, detail={"message": "当前没有可修改的学习计划。"}) from exc
    release = latest_release()
    if release is None:
        return {"revised": False, "reason": "codex_unavailable"}
    try:
        generated = chat(
            request.user_id,
            build_plan_revision_prompt(request, current_plan, request.feedback),
            release,
        )
        validated = normalize_and_validate_plan(generated, request.topic.value, request.goal_route)
        if validated is None:
            return {"revised": False, "reason": "validation_failed"}
        curriculum = curriculum_from_plan(
            validated, topic=request.topic.value, route=request.goal_route, level=request.level_claim,
        )
        save_curriculum(SERVER_ROOT, request.user_id, curriculum)
        replace_plan(plan_path, validated)
        set_plan_status(SERVER_ROOT, request.user_id, "awaiting_confirmation")
        return {
            "revised": True,
            "plan_status": "awaiting_confirmation",
            "plan_markdown": plan_path.read_text(encoding="utf-8"),
        }
    except Exception:
        return {"revised": False, "reason": "generation_failed"}


@app.post("/api/curriculum/generate")
def generate_curriculum(request: CurriculumGenerateRequest) -> dict[str, Any]:
    context = read_learning_context(request.user_id, SERVER_ROOT)
    state_payload = read_state(request.user_id)
    state = state_payload.get("state") or {}
    if context["profile_status"] != "confirmed":
        raise HTTPException(status_code=409, detail={"recovery": "complete_onboarding"})
    profile = str(state_payload.get("profile") or "")
    level_match = re.search(r"自报基础[：:]\s*(zero|some|experienced)", profile)
    preference_match = re.search(r"教学偏好[：:]\s*(visual|balanced|hands_on)", profile)
    topic = str(context.get("topic") or state.get("active_topic") or "").strip()
    language = str(context.get("language") or "custom")
    topic_type = language if language in {"go", "python"} else "custom"
    try:
        submission = OnboardingSubmission(
            user_id=request.user_id,
            learning_mode=state.get("learning_mode") if state.get("learning_mode") in {"systematic", "project", "practice"} else "systematic",
            goal_route=state.get("goal_route") or "foundation_engineer",
            level_claim=level_match.group(1) if level_match else "zero",
            topic={"type": topic_type, "value": topic},
            session_minutes=int(context.get("session_minutes") or 25),
            deadline_days=state.get("deadline_days"),
            teaching_preference=preference_match.group(1) if preference_match else "balanced",
            concept_scope=state.get("concept_scope") if state.get("concept_scope") in {"not_applicable", "meaning_only", "code_walkthrough"} else "not_applicable",
        )
        plan_path = active_plan_path(SERVER_ROOT, request.user_id)
        fallback = plan_path.read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=409, detail={"recovery": "complete_onboarding"}) from exc
    release = latest_release()
    if release is None:
        raise HTTPException(status_code=503, detail={"message": "课程模型暂时不可用。", "retryable": True})
    try:
        raw_diagnosis = state.get("diagnosis")
        diagnosis = DiagnosisSummary.model_validate(raw_diagnosis) if isinstance(raw_diagnosis, dict) else None
        knowledge_source = str(context.get("knowledge_source") or "skill_guided")
        generated = chat(
            request.user_id,
            build_plan_prompt(submission, fallback, knowledge_source, diagnosis=diagnosis),
            release,
        )
        validated = normalize_and_validate_plan(generated, topic, submission.goal_route)
        if validated is None:
            raise ValueError("invalid model curriculum")
        if requires_authoritative_research(submission, knowledge_source):
            load_valid_research(
                SERVER_ROOT,
                request.user_id,
                topic,
                require_deep=submission.goal_route in {"foundation_engineer", "senior_engineer"},
            )
        curriculum = curriculum_from_plan(
            validated, topic=topic, route=submission.goal_route, level=submission.level_claim,
        )
        save_curriculum(SERVER_ROOT, request.user_id, curriculum)
        replace_plan(plan_path, render_curriculum_plan(curriculum))
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"message": "详细课程大纲生成失败，请重试。", "retryable": True},
        ) from exc
    return {
        "generated": True,
        "active_plan": plan_path.name,
        "current_knowledge_point_id": curriculum.current_knowledge_point_id,
    }


@app.post("/api/chat")
def chat_once(request: ChatRequest) -> dict[str, str]:
    release = latest_release()
    if release is None:
        raise HTTPException(status_code=503, detail="没有可用的教学版本")
    reply = chat(
        request.user_id,
        build_prompt(request.user_id, request.history, request.message),
        release,
    )
    return {"reply": reply}


@app.post("/api/chat/stream")
def chat_stream(request: ChatRequest) -> StreamingResponse:
    release = latest_release()
    if release is None:
        raise HTTPException(status_code=503, detail="没有可用的教学版本")
    context = read_learning_context(request.user_id, SERVER_ROOT)
    append_learning_question(
        SERVER_ROOT, request.user_id, question=request.message, topic=str(context.get("topic") or ""),
    )
    prompt = build_prompt(request.user_id, request.history, request.message)

    def events() -> Iterator[str]:
        answer_parts: list[str] = []
        try:
            for item in stream_chat(request.user_id, prompt, release):
                if item.get("event") == "message.delta":
                    data = item.get("data")
                    text = data.get("text") if isinstance(data, dict) else None
                    if isinstance(text, str):
                        answer_parts.append(text)
                yield format_sse(item)
            if request.lesson_id and answer_parts:
                note = append_lesson_note(
                    SERVER_ROOT,
                    request.user_id,
                    lesson_id=request.lesson_id,
                    topic=str(context.get("topic") or ""),
                    question=request.message,
                    summary="".join(answer_parts),
                )
                yield format_sse({
                    "event": "notes.updated",
                    "data": {"lesson_id": request.lesson_id, "important": note["important"]},
                })
        except Exception:
            yield format_sse(
                {
                    "event": "error",
                    "data": {
                        "message": "连接学习引擎时出现问题，请稍后继续。",
                        "retryable": True,
                    },
                }
            )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/lesson/notes")
def lesson_notes(
    user_id: str = Query(default="yang", max_length=64),
    lesson_id: str = Query(min_length=1, max_length=96, pattern=r"^[A-Za-z0-9_-]+$"),
) -> dict[str, Any]:
    return read_lesson_notes(SERVER_ROOT, user_id, lesson_id)


def grade_answer(*, question: str, answer: str, kind: str) -> dict[str, Any]:
    system = (
        "你是严格但温和的学习教练。只输出一个 JSON 对象，字段为 feedback、correct、verified。"
        "correct 只能是 true、false 或 null；只有答案和题目中的可观察标准一致，或包含足够的独立"
        "运行/推理证据时，verified 才能为 true。跳过、猜测、信息不足和模糊回答必须 verified=false。"
        "feedback 先给结论，再说一个具体优点、一个最关键问题和下一步独立动作。"
    )
    prompt = (
        f"题目：{question}\n\n学生作答：{answer}"
        f"\n\n题型：{kind}"
    )
    raw = llm_chat(prompt, system=system).strip()
    cleaned = raw
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        feedback = parsed.get("feedback")
        correct = parsed.get("correct")
        verified = parsed.get("verified")
        if (
            isinstance(feedback, str)
            and isinstance(verified, bool)
            and (isinstance(correct, bool) or correct is None)
        ):
            return {
                "feedback": feedback,
                "correct": correct,
                "verified": verified and correct is True,
            }
    return {"feedback": raw, "correct": None, "verified": False}


@app.post("/api/grade")
def grade(request: GradeRequest) -> dict[str, Any]:
    result = grade_answer(
        question=request.question,
        answer=request.answer,
        kind=request.kind,
    )
    append_attempt(
        SERVER_ROOT,
        request.user_id,
        question=request.question,
        answer=request.answer,
        feedback=str(result["feedback"]),
        kind=request.kind,
    )
    return result


@app.get("/api/review-document")
def review_document(
    user_id: str = Query(default="yang", max_length=64),
) -> dict[str, Any]:
    return read_review_document(SERVER_ROOT, user_id)


@app.post("/api/exercises/generate")
def generate_exercise(request: ExerciseGenerateRequest) -> dict[str, Any]:
    system = (
        "你是教学题目设计师。根据模块和学习程度只输出一个 JSON 对象，字段必须是 "
        "kind,title,prompt,instructions,completion_criteria。题目要小、可独立作答、能留下学习证据；"
        "零基础先预测或解释，熟练者优先调试、重构或迁移。不要输出参考答案。"
    )
    raw = llm_chat(
        f"模块：{request.module}\n学习程度：{request.level}",
        system=system,
    )
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        exercise = json.loads(cleaned)
    except json.JSONDecodeError:
        language = "go" if "go" in request.module.lower() else "python"
        exercise = default_exercise(language)
    required = {"kind", "title", "prompt", "instructions", "completion_criteria"}
    if not isinstance(exercise, dict) or not required.issubset(exercise):
        language = "go" if "go" in request.module.lower() else "python"
        exercise = default_exercise(language)
    return {"exercise": exercise}


def main() -> None:
    port = PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    print(f"Learning Agent 已启动 → http://{HOST}:{port}")
    scheduler = ReminderScheduler(lambda: SERVER_ROOT)
    scheduler.start()
    try:
        uvicorn.run(app, host=HOST, port=port, log_level="info")
    finally:
        scheduler.stop()


if __name__ == "__main__":
    main()
