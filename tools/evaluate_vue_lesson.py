#!/usr/bin/env python3
"""Opt-in paid Vue regression, isolated from all real learner state.

Run: .venv/bin/python tools/evaluate_vue_lesson.py
Tests a synthetic confirmed curriculum -> real Codex/DeepSeek -> validation ->
save -> current-lesson reload. This is not a claim to test onboarding or Windows.
Raw inputs/outputs stay in ignored evals/runs; no credentials are copied.
"""
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend import codex_driver as driver, main as api
from backend.curriculum import Chapter, Curriculum, KnowledgePoint, render_curriculum_plan


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    run = ROOT / "evals/runs" / (datetime.now().strftime("%Y%m%d-%H%M%S-%f") + "-vue-recovery")
    isolated = run / "isolated"
    shutil.copytree(ROOT / "workspace/dev", isolated / "workspace/dev")
    shutil.copytree(ROOT / "templates", isolated / "templates")
    for key, value in driver.load_secrets(ROOT / ".secrets.env").items():
        if key.startswith("DEEPSEEK_"):
            os.environ[key] = value
    user_id = "vue_recovery_fixture"
    user = driver.ensure_user(user_id, isolated)
    points = [KnowledgePoint(id=key, title=title, outcome="能够解释并用于调试 Vue 响应式",
                             practice="运行最小示例并改变一个输入", mastery_criteria="能解释读写时发生什么")
              for key, title in [("ref", "ref"), ("reactive", "reactive"), ("proxy", "Proxy 代理"),
                                 ("track-trigger", "track / trigger 依赖收集"), ("computed", "computed"),
                                 ("watcheffect", "watchEffect"), ("shallowref-shallowreactive", "shallowRef / shallowReactive"),
                                 ("chapter-1-point-8", "解构失响应"), ("chapter-1-point-9", "代理与原对象的相等性")]]
    curriculum = Curriculum(topic="Vue", route="interview_sprint", level="experienced",
        chapters=[Chapter(id="reactivity", title="Vue 响应式原理与面试表达", knowledge_points=points)],
        current_knowledge_point_id="ref")
    (user / "curriculum.json").write_text(curriculum.model_dump_json(indent=2), encoding="utf-8")
    (user / "plan.md").write_text(render_curriculum_plan(curriculum), encoding="utf-8")
    (user / "profile.md").write_text(
        "# 合成测试画像\n有 JavaScript 和 Vue 基础，目标是 Vue 前端面试，不是 AI 前端。"
        "已安装 Node.js，能用终端运行 JavaScript；希望从短示例逐步理解响应式，"
        "包含一次真正可独立完成的编程作业和带参考答案的口述面试题。", encoding="utf-8")
    (user / "learning-state.json").write_text(json.dumps({
        "profile_status": "confirmed", "plan_status": "confirmed", "active_topic": "Vue",
        "active_plan": "plan.md", "goal_route": "interview_sprint", "revision": 1,
        "session_minutes": 35, "recent_evidence": [],
    }), encoding="utf-8")
    api.SERVER_ROOT = isolated
    api.latest_release = lambda: isolated / "workspace/dev"
    calls = []

    def model(uid, prompt, release, **kwargs):
        start = time.monotonic()
        kwargs.setdefault("timeout", 240)
        result = driver.chat(uid, prompt, release, server_root=isolated, **kwargs)
        call = {"seconds": round(time.monotonic() - start, 2), "prompt": prompt, "output": result}
        calls.append(call)
        (run / f"call-{len(calls)}.json").write_text(json.dumps(call, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"call": len(calls), "seconds": call["seconds"]}), flush=True)
        return result

    api.chat = model
    start = time.monotonic()
    report = {"scope": "synthetic confirmed Vue curriculum -> lesson -> reload", "evidence": str(run)}
    print(json.dumps(report), flush=True)
    try:
        result = api.generate_lesson(api.LessonGenerateRequest(user_id=user_id))
        reloaded = api.current_lesson(user_id=user_id)
        report.update(ok=bool(result.get("pages")) and reloaded["lesson_id"] == result["lesson_id"],
                      pages=len(result["pages"]), lesson_id=result["lesson_id"])
        (run / "lesson.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        report.update(ok=False, error_type=type(exc).__name__, error=str(exc))
        logging.exception("Vue synthetic lesson evaluation failed")
    report.update(seconds=round(time.monotonic() - start, 2), model_calls=len(calls))
    (run / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
