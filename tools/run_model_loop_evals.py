"""Exercise the model-authored curriculum -> lesson loop for fixed learner personas."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import httpx

from run_persona_evals import _choose_option


ROOT = Path(__file__).resolve().parents[1]


def post(client: httpx.Client, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(path, json=payload, timeout=240)
    body = response.json()
    if not response.is_success:
        raise RuntimeError(f"{path} -> {response.status_code}: {body}")
    return body


def run_persona(client: httpx.Client, persona: dict[str, Any]) -> dict[str, Any]:
    user_id = f"model_loop_{persona['id'].replace('-', '_')}"
    payload = {
        "user_id": user_id,
        "learning_mode": persona["learning_mode"],
        "goal_route": persona["goal_route"],
        "level_claim": persona["level_claim"],
        "topic": persona["topic"],
        "session_minutes": persona["session_minutes"],
        "teaching_preference": "balanced",
    }
    started = time.monotonic()
    calls: list[dict[str, Any]] = []
    diagnosis_count = 0
    started_onboarding = post(client, "/api/onboarding/start", payload)
    calls.append({"path": "/api/onboarding/start", "response": started_onboarding})
    session_id = started_onboarding.get("session_id")
    current = started_onboarding
    pattern = list(persona.get("diagnostic_pattern") or [True, True, True])
    while current.get("next") == "diagnosis" and not current.get("complete"):
        question = current["question"]
        current = post(
            client,
            "/api/diagnostics/answer",
            {
                "user_id": user_id,
                "session_id": session_id,
                "question_id": question["id"],
                "selected_option_id": _choose_option(
                    question, pattern[min(diagnosis_count, len(pattern) - 1)],
                ),
            },
        )
        diagnosis_count += 1
        calls.append({"path": "/api/diagnostics/answer", "response": current})
    confirm_payload = dict(payload)
    if session_id:
        confirm_payload["diagnostic_session_id"] = session_id
    calls.append({"path": "/api/onboarding/confirm", "response": post(client, "/api/onboarding/confirm", confirm_payload)})
    personalized = post(client, "/api/plans/personalize", payload)
    calls.append({"path": "/api/plans/personalize", "response": personalized})
    lesson = post(client, "/api/lesson/generate", {"user_id": user_id, "force": True})
    calls.append({"path": "/api/lesson/generate", "response": lesson})

    curriculum = json.loads((ROOT / "userdir" / f"u_{user_id}" / "curriculum.json").read_text(encoding="utf-8"))
    points = [point for chapter in curriculum["chapters"] for point in chapter["knowledge_points"]]
    pages = lesson.get("pages") or []
    question_pages = [page for page in pages if page.get("question")]
    quality = {
        "personalized": personalized.get("personalized") is True,
        "diagnostic_questions": diagnosis_count,
        "diagnostic_bounded": diagnosis_count <= 4,
        "chapter_count": len(curriculum["chapters"]),
        "knowledge_point_count": len(points),
        "topic_match": persona["topic"]["value"].casefold() in curriculum["topic"].casefold(),
        "lesson_matches_current_point": lesson.get("knowledge_point_id") == curriculum["current_knowledge_point_id"],
        "lesson_pages": len(pages),
        "question_pages": len(question_pages),
        "has_practice": any(page.get("type") == "practice" for page in pages),
        "ends_with_mastery": bool(pages) and pages[-1].get("type") == "mastery",
        "has_completion_prompt": bool(lesson.get("completion_prompt")),
    }
    quality["passed"] = all(
        (
            quality["personalized"],
            quality["diagnostic_bounded"],
            quality["chapter_count"] >= 5,
            quality["knowledge_point_count"] >= 5,
            quality["topic_match"],
            quality["lesson_matches_current_point"],
            3 <= quality["lesson_pages"] <= 12,
            quality["has_practice"],
            quality["ends_with_mastery"],
            quality["has_completion_prompt"],
        )
    )
    return {
        "persona_id": persona["id"],
        "label": persona["label"],
        "user_id": user_id,
        "duration_seconds": round(time.monotonic() - started, 2),
        "quality": quality,
        "current_point": next(point for point in points if point["id"] == curriculum["current_knowledge_point_id"]),
        "lesson_title": lesson.get("title"),
        "lesson_preview": [
            {"type": page.get("type"), "title": page.get("title"), "markdown": str(page.get("markdown") or "")[:240]}
            for page in pages
        ],
        "calls": calls,
    }


def write_summary(output: Path, results: list[dict[str, Any]]) -> None:
    lines = [
        "# Model-driven learning loop persona evaluation",
        "",
        "| Persona | Diagnosis | Chapters | Points | Lesson pages | Questions | Time | Result |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for result in results:
        quality = result["quality"]
        lines.append(
            f"| {result['label']} | {quality['diagnostic_questions']} | {quality['chapter_count']} | "
            f"{quality['knowledge_point_count']} | {quality['lesson_pages']} | {quality['question_pages']} | "
            f"{result['duration_seconds']}s | {'PASS' if quality['passed'] else 'FAIL'} |"
        )
    (output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8791")
    parser.add_argument("--personas", type=Path, default=ROOT / "evals/personas-v3.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--only", action="append", default=[])
    args = parser.parse_args()
    personas = json.loads(args.personas.read_text(encoding="utf-8"))["personas"]
    personas = [item for item in personas if not args.only or item["id"] in args.only]
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    with httpx.Client(base_url=args.base_url, timeout=240) as client:
        for persona in personas:
            print(f"RUN {persona['id']}", flush=True)
            result = run_persona(client, persona)
            (args.output / f"{persona['id']}.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
            )
            results.append(result)
            print(f"DONE {persona['id']} {result['quality']['passed']} {result['duration_seconds']}s", flush=True)
    write_summary(args.output, results)
    return 0 if all(result["quality"]["passed"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
