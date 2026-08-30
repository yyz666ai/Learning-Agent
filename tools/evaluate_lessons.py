#!/usr/bin/env python3
"""Opt-in paid-model evaluation of confirmed profiles, isolated from real users.

This deliberately does NOT claim to test natural-language onboarding. Its input
is a confirmed fixture profile. Raw prompts/results are retained under evals/runs.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend import main as api, codex_driver as driver
from backend.onboarding import OnboardingSubmission, DiagnosisSummary, confirm_onboarding


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=["beginner", "advanced", "interview", "all"], default="all")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--from-confirmed", type=Path, help="Copy a synthetic eval root and reuse its already-confirmed Plan; generate only its lesson")
    parser.add_argument("--remediation", default="", help="Explicit user-requested lesson correction (recorded in raw prompt)")
    parser.add_argument("--plan-response", type=Path, help="Replay a saved synthetic Plan response to verify parser fixes without paying for the same Plan again")
    parser.add_argument("--lesson-response", type=Path, help="Replay an actual saved lesson response against current validators (requires --from-confirmed)")
    args = parser.parse_args()
    if args.plan_response and (args.case == "all" or ROOT / "evals/runs" not in args.plan_response.resolve().parents):
        parser.error("--plan-response requires one case and a saved evals/runs response")
    if args.lesson_response and (not args.from_confirmed or args.case == "all" or ROOT / "evals/runs" not in args.lesson_response.resolve().parents):
        parser.error("--lesson-response requires a single copied confirmed fixture and an evals/runs response")
    if args.from_confirmed and ROOT / "evals/runs" not in args.from_confirmed.resolve().parents:
        parser.error("--from-confirmed must be an isolated evals/runs directory")
    run = ROOT / "evals/runs" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-lesson-retest")
    isolated = run / "isolated"
    shutil.copytree(ROOT / "workspace/dev", isolated / "workspace/dev")
    if (ROOT / "templates").is_dir():
        shutil.copytree(ROOT / "templates", isolated / "templates")
    # The key is passed through the process environment, never written to logs.
    for key, value in driver.load_secrets(ROOT / ".secrets.env").items():
        if key.startswith("DEEPSEEK_"):
            os.environ[key] = value
    api.SERVER_ROOT = isolated
    api.latest_release = lambda: isolated / "workspace/dev"
    counters = {}
    def model(user_id, prompt, release, **kwargs):
        n = counters.get(user_id, 0) + 1
        counters[user_id] = n
        started = time.monotonic()
        replay_path = args.lesson_response or (args.plan_response if n == 1 else None)
        replay = bool(replay_path)
        result = json.loads(replay_path.read_text(encoding="utf-8"))["output"] if replay else driver.chat(user_id, prompt, release, **{**kwargs, "server_root":isolated,"timeout":args.timeout})
        target = run / user_id
        target.mkdir(parents=True, exist_ok=True)
        (target / f"call-{n}.json").write_text(json.dumps({"replayed":replay,"seconds":round(time.monotonic()-started,2),"prompt":prompt,"output":result},ensure_ascii=False,indent=2))
        print(json.dumps({"case":user_id,"call":n,"seconds":round(time.monotonic()-started,2)},ensure_ascii=False),flush=True)
        return result
    api.chat = model
    def evaluate(name):
        user_id = "lesson_retest_" + name
        data = dict(user_id=user_id,learning_mode="practice" if name=="advanced" else "systematic",goal_route={"beginner":"foundation_engineer","advanced":"gap_upgrade","interview":"interview_sprint"}[name],level_claim="experienced" if name=="advanced" else "zero",topic={"type":"language","value":"Python" if name=="interview" else "Go"},session_minutes=40,teaching_preference="hands_on")
        data["topic"]["type"] = "python" if name == "interview" else "go"
        submission = OnboardingSubmission.model_validate(data)
        diagnosis = DiagnosisSummary(estimated_level="experienced",score=.8,answered_count=4,strengths=["HTTP handler 实现","表驱动单元测试"],gaps=["并发取消与资源泄漏排查"],evidence=[{"source":"evaluation fixture, not actual learner answers"}]) if name=="advanced" else None
        report = {"case":name,"scope":"confirmed fixture -> real Plan -> explicit confirm -> real first chapter", "stages":[]}
        def record(stage, operation):
            started = time.monotonic()
            result = operation()
            report["stages"].append({"stage":stage,"seconds":round(time.monotonic()-started,2),"result":result})
            return result
        try:
            if args.from_confirmed:
                shutil.copytree(args.from_confirmed / "userdir" / f"u_{user_id}", isolated / "userdir" / f"u_{user_id}", ignore=shutil.ignore_patterns(".codex-runtime"))
                report["scope"] = "copied confirmed fixture Plan -> freshly generated first lesson (no Plan regeneration)"
            else:
                confirmed = record("confirmed_fixture", lambda:confirm_onboarding(isolated,submission,diagnosis))
                plan = record("plan",lambda:api.personalize_plan(api.PlanPersonalizeRequest(**data,generation_id=confirmed["generation_id"])))
                if not plan.get("personalized"):
                    raise ValueError("plan failed: " + str(plan.get("reason")))
                record("confirm_plan",lambda:api.confirm_plan(api.PlanConfirmRequest(user_id=user_id)))
            lesson = record("lesson",lambda:api.generate_lesson(api.LessonGenerateRequest(user_id=user_id,force=True,remediation=args.remediation)))
            report["ok"] = bool(lesson.get("pages"))
        except Exception as exc:
            report.update(ok=False,error={"type":type(exc).__name__,"message":str(exc)})
        target = run / user_id
        target.mkdir(parents=True,exist_ok=True)
        (target / "journey.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print(json.dumps({"completed":name,"ok":report.get("ok"),"error":report.get("error")},ensure_ascii=False),flush=True)
        return report
    print(json.dumps({"evidence":str(run)}),flush=True)
    names = ["beginner","advanced","interview"] if args.case=="all" else [args.case]
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(evaluate,names))
    (run / "summary.json").write_text(json.dumps(results,ensure_ascii=False,indent=2))
    return 0 if all(result.get("ok") for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
