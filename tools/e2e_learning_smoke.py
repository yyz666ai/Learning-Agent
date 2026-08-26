#!/usr/bin/env python3
"""Run a real learner journey against a running Learning Agent service."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Case:
    name: str
    user_id: str
    message: str
    clarification: str | None = None


CASES = {
    case.name: case
    for case in (
        Case("frontend-interview-missing-level", "qa_frontend_missing_level", "我要面试前端岗", "初学"),
        Case("java-backend-interview-some", "qa_java_backend_some", "我要面试 Java 后端岗，有一点基础"),
        Case("ai-frontend-interview-zero", "qa_ai_frontend_zero", "我是初学者，想面试 AI 前端岗"),
        Case("ai-pm-interview-experienced", "qa_ai_pm_experienced", "我是一名熟练的产品经理，想准备 AI 产品经理面试"),
        Case("rag-concept", "qa_rag_concept", "我想弄懂大模型的 RAG 是什么意思"),
        Case("langgraph-project", "qa_langgraph_project", "我想用 LangGraph 做一个客服 Agent 项目", "初学"),
    )
}

DIRECT_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class JourneyError(RuntimeError):
    def __init__(self, stage: str, payload: Any):
        super().__init__(f"{stage} failed: {payload}")
        self.stage = stage
        self.payload = payload


def post(base_url: str, path: str, payload: dict[str, Any], timeout: int = 1320) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with DIRECT_OPENER.open(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(body)
        except json.JSONDecodeError:
            detail = body
        raise JourneyError(path, {"status": exc.code, "body": detail}) from exc
    except (TimeoutError, urllib.error.URLError) as exc:
        raise JourneyError(path, {"error_type": type(exc).__name__, "message": str(exc)}) from exc


def submission(user_id: str, decision: dict[str, Any]) -> dict[str, Any]:
    onboarding = decision.get("onboarding") or {}
    slots = decision.get("slots") or {}
    if decision.get("action") != "ready_for_plan" or not slots.get("topic"):
        raise JourneyError("intent", decision)
    return {
        "user_id": user_id,
        "learning_mode": onboarding["learning_mode"],
        "goal_route": onboarding["goal_route"],
        "level_claim": onboarding["level_claim"],
        "topic": {"type": onboarding.get("topic_type") or "custom", "value": slots["topic"]},
        "session_minutes": onboarding.get("session_minutes") or 25,
        "deadline_days": onboarding.get("deadline_days"),
        "teaching_preference": onboarding.get("teaching_preference") or "balanced",
        "concept_scope": onboarding.get("concept_scope") or "not_applicable",
    }


def run_case(base_url: str, case: Case, through: str = "lesson") -> dict[str, Any]:
    started = time.monotonic()
    stages: list[dict[str, Any]] = []
    history: list[dict[str, str]] = []
    decision = post(base_url, "/api/onboarding/intent", {
        "user_id": case.user_id, "message": case.message, "history": history,
        "slots": {}, "clarification_count": 0,
    })
    stages.append({"stage": "intent", "seconds": round(time.monotonic() - started, 2), "action": decision.get("action")})
    if decision.get("action") == "clarify":
        if not case.clarification:
            raise JourneyError("clarification_missing", decision)
        history.append({"role": "user", "content": case.message})
        decision = post(base_url, "/api/onboarding/intent", {
            "user_id": case.user_id, "message": case.clarification, "history": history,
            "slots": decision.get("slots") or {}, "clarification_count": 1,
        })
        stages.append({"stage": "clarification", "seconds": round(time.monotonic() - started, 2), "action": decision.get("action")})
    data = submission(case.user_id, decision)
    if through == "intent":
        return {"case": case.name, "ok": True, "submission": data, "stages": stages}

    diagnostic_session_id = None
    if data["level_claim"] != "zero" and data["goal_route"] != "concept_clarity":
        diagnostic = post(base_url, "/api/onboarding/start", data)
        diagnostic_session_id = diagnostic["session_id"]
        while not diagnostic.get("complete"):
            question = diagnostic["question"]
            diagnostic = post(base_url, "/api/diagnostics/answer", {
                "user_id": case.user_id,
                "session_id": diagnostic_session_id,
                "question_id": question["id"],
                "selected_option_id": question["options"][0]["id"],
            })
        stages.append({"stage": "diagnosis", "seconds": round(time.monotonic() - started, 2), "answered": diagnostic.get("answered_count")})

    confirmed = post(base_url, "/api/onboarding/confirm", {
        **data, "diagnostic_session_id": diagnostic_session_id,
    })
    stages.append({"stage": "onboarding_confirm", "seconds": round(time.monotonic() - started, 2), "active_plan": confirmed.get("active_plan")})
    plan = post(base_url, "/api/plans/personalize", {
        **data, "generation_id": confirmed["generation_id"],
    })
    if not plan.get("personalized"):
        raise JourneyError("plan", plan)
    stages.append({"stage": "plan", "seconds": round(time.monotonic() - started, 2), "knowledge_point": plan.get("current_knowledge_point_id")})
    if through == "plan":
        return {"case": case.name, "ok": True, "submission": data, "stages": stages}

    post(base_url, "/api/plans/confirm", {"user_id": case.user_id})
    lesson = post(base_url, "/api/lesson/generate", {"user_id": case.user_id})
    pages = lesson.get("pages") or []
    if not pages or not lesson.get("chapter_id") or not lesson.get("covered_knowledge_point_ids"):
        raise JourneyError("lesson", lesson)
    stages.append({
        "stage": "lesson", "seconds": round(time.monotonic() - started, 2),
        "lesson_id": lesson.get("lesson_id"), "pages": len(pages),
        "checks": sum(page.get("type") == "check" for page in pages),
    })
    return {"case": case.name, "ok": True, "submission": data, "stages": stages}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("case", choices=[*CASES, "all"])
    parser.add_argument("--base-url", default="http://127.0.0.1:8787")
    parser.add_argument("--through", choices=["intent", "plan", "lesson"], default="lesson")
    args = parser.parse_args()
    selected = CASES.values() if args.case == "all" else [CASES[args.case]]
    results = []
    for case in selected:
        try:
            result = run_case(args.base_url, case, through=args.through)
        except JourneyError as exc:
            result = {"case": case.name, "ok": False, "stage": exc.stage, "detail": exc.payload}
        except Exception as exc:
            result = {
                "case": case.name, "ok": False, "stage": "runner",
                "detail": {"error_type": type(exc).__name__, "message": str(exc)},
            }
        results.append(result)
        print(json.dumps({"completed": result}, ensure_ascii=False), flush=True)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(result["ok"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
