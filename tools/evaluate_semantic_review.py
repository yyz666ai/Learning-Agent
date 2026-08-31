#!/usr/bin/env python3
"""Paid, isolated reviewer replay; never modifies the source learner's files.

Usage: .venv/bin/python tools/evaluate_semantic_review.py --rollout PATH --curriculum PATH
Private source content/results stay in ignored evals/runs. No credentials copied.
"""
import argparse
from datetime import datetime
import json
import logging
import os
import shutil
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend import codex_driver
from backend.curriculum import Curriculum
from backend.lesson_generator import _extract_json, _repair_generated_wire_format, parse_lesson_response, generate_and_save_lesson, load_lesson_bundle
from backend.lesson_review import LessonCoverageError, review_lesson
from tests.test_lesson_semantic_review import curriculum as example_curriculum, payload as example_payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rollout", type=Path, required=True)
    parser.add_argument("--curriculum", type=Path, required=True)
    parser.add_argument("--generate", action="store_true", help="Also generate, review, save and reload the supplied curriculum in isolation")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    run = ROOT / "evals/runs" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-semantic-review")
    isolated = run / "isolated"
    isolated.mkdir(parents=True)
    shutil.copytree(ROOT / "templates", isolated / "templates")
    for key, value in codex_driver.load_secrets(ROOT / ".secrets.env").items():
        if key.startswith("DEEPSEEK_"):
            os.environ[key] = value
    curriculum = Curriculum.model_validate_json(args.curriculum.read_text())
    candidate = None
    for line in args.rollout.read_text().splitlines():
        row = json.loads(line)
        value = row.get("payload", {})
        if row.get("type") != "response_item" or value.get("role") != "assistant":
            continue
        for part in value.get("content", []):
            text = part.get("text", "")
            try:
                if _extract_json(text).get("pages"):
                    candidate = text
            except ValueError:
                pass
    if not candidate:
        raise ValueError("no lesson in supplied rollout")
    synthetic = example_payload()
    paraphrase = example_payload()
    paraphrase["pages"][0]["markdown"] = "在 macOS 打开 Terminal，Windows 打开 PowerShell。输入 pwd 查看当前目录，再输入 cd 项目目录进入它，用 pwd 确认路径已改变。"
    missing = example_payload()
    for page in missing["pages"]:
        page["markdown"] = "命令行、终端、项目目录。这些名词以后再学，今天只介绍番茄炒蛋的材料。"
    cases = [("actual_failed_lesson", curriculum, candidate, True),
             ("synonym_single_page", example_curriculum(), json.dumps(synthetic), True),
             ("no_title_terms", example_curriculum(), json.dumps(paraphrase), True),
             ("keywords_without_teaching", example_curriculum(), json.dumps(missing), False)]
    results = []
    for name, course, raw, expected in cases:
        bundle = parse_lesson_response(_repair_generated_wire_format(raw, course.topic), topic=course.topic,
            route=course.route, knowledge_point_id=course.current_knowledge_point_id, session_minutes=25,
            chapter=course.current_chapter(), covered_knowledge_points=course.current_chapter_remaining_points())
        calls = []
        def model(prompt):
            output = codex_driver.chat("semantic_eval", prompt, ROOT / "workspace/dev", server_root=isolated,
                generation="lesson_review", timeout=120)
            calls.append({"prompt": prompt, "output": output})
            return output
        started = time.monotonic()
        try:
            review_lesson(bundle, course, profile="零基础，希望循序渐进学习", model_call=model)
            result = {"case": name, "covered": True}
        except LessonCoverageError as exc:
            result = {"case": name, "covered": False, "reason": str(exc)}
        except Exception as exc:
            result = {"case": name, "error": type(exc).__name__, "reason": str(exc)}
        result.update(seconds=round(time.monotonic() - started, 2), model_calls=len(calls), expected=expected)
        result["ok"] = "error" not in result and (expected is None or result["covered"] == expected)
        (run / f"{name}.json").write_text(json.dumps({"result": result, "calls": calls}, ensure_ascii=False, indent=2))
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    if args.generate:
        started = time.monotonic()
        calls = []
        def call(prompt, kind):
            output = codex_driver.chat("semantic_eval", prompt, ROOT / "workspace/dev", server_root=isolated,
                generation=kind, timeout=180)
            calls.append({"kind": kind, "prompt": prompt, "output": output})
            return output
        try:
            bundle = generate_and_save_lesson(isolated, "semantic_eval", curriculum=curriculum,
                profile="零基础，希望从环境安装开始，循序渐进学习", recent_evidence=[], session_minutes=25,
                model_call=lambda prompt: call(prompt, "lesson"), review_call=lambda prompt: call(prompt, "lesson_review"))
            reloaded = load_lesson_bundle(isolated, "semantic_eval", curriculum.current_knowledge_point_id)
            result = {"case": "fresh_generation_save_reload", "ok": reloaded.manifest.pages == bundle.manifest.pages,
                      "pages": len(bundle.manifest.pages)}
        except Exception as exc:
            result = {"case": "fresh_generation_save_reload", "ok": False, "error": type(exc).__name__, "reason": str(exc)}
        result.update(seconds=round(time.monotonic() - started, 2), model_calls=len(calls))
        (run / "fresh-generation.json").write_text(json.dumps({"result": result, "calls": calls}, ensure_ascii=False, indent=2))
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    (run / "summary.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"Private evidence: {run}", flush=True)
    return 0 if all(item["ok"] for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
