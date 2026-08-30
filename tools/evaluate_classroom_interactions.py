#!/usr/bin/env python3
"""Opt-in paid-model classroom checks on copies of synthetic evaluation users.

No browser interaction and no production userdir writes. Records actual model
outputs; successful transport is not a claim of pedagogical correctness.
"""
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
from fastapi.testclient import TestClient
from backend import main as api, codex_driver as driver
from backend.curriculum import load_curriculum
from backend.lesson_generator import load_lesson_bundle
from backend.lesson_context import lesson_revision


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--interview-source", type=Path, required=True)
    args = parser.parse_args()
    for path in [args.source.resolve(), args.interview_source.resolve()]:
        if ROOT / "evals/runs" not in path.parents:
            raise SystemExit("Only isolated evals/runs sources are permitted")
    run = ROOT / "evals/runs" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-classroom-interactions")
    isolated = run / "isolated"
    shutil.copytree(ROOT / "workspace/dev", isolated / "workspace/dev")
    if (ROOT / "templates").is_dir():
        shutil.copytree(ROOT / "templates", isolated / "templates")
    advanced = "lesson_retest_advanced"
    interview = "lesson_audit_interview"
    for source, user in [(args.source, advanced), (args.interview_source, interview)]:
        shutil.copytree(source / "userdir" / f"u_{user}", isolated / "userdir" / f"u_{user}", ignore=shutil.ignore_patterns(".codex-runtime"))
    for key, value in driver.load_secrets(ROOT / ".secrets.env").items():
        if key.startswith("DEEPSEEK_"):
            os.environ[key] = value
    api.SERVER_ROOT = isolated
    api.latest_release = lambda: isolated / "workspace/dev"
    counters = {}

    def model(user, prompt, release, **kwargs):
        started = time.monotonic()
        options = {**kwargs, "server_root": isolated}
        options.setdefault("timeout", 300)
        output = driver.chat(user, prompt, release, **options)
        counters[user] = counters.get(user, 0) + 1
        (run / f"{user}-model-{counters[user]}.json").write_text(json.dumps({"seconds":round(time.monotonic()-started,2),"prompt":prompt,"output":output},ensure_ascii=False,indent=2))
        return output

    def stream(user, prompt, release, **kwargs):
        # Actual streaming adapter, not a synthetic stream of a completed reply.
        started = time.monotonic()
        events = []
        try:
            for event in driver.stream_chat(user, prompt, release, **{**kwargs, "server_root": isolated}):
                events.append(event)
                yield event
        finally:
            counters[user] = counters.get(user, 0) + 1
            (run / f"{user}-stream-{counters[user]}.json").write_text(json.dumps({"seconds":round(time.monotonic()-started,2),"prompt":prompt,"events":events},ensure_ascii=False,indent=2))

    api.chat, api.stream_chat = model, stream

    def record(name, operation):
        started = time.monotonic()
        try:
            response = operation()
            result = {"status":response.status_code,"body":response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text}
        except Exception as error:
            result = {"error":type(error).__name__ + ": " + str(error)}
        result["seconds"] = round(time.monotonic()-started, 2)
        (run / f"{name}.json").write_text(json.dumps(result,ensure_ascii=False,indent=2))
        print(json.dumps({"case":name,"seconds":result["seconds"],"status":result.get("status"),"error":result.get("error")},ensure_ascii=False),flush=True)
        return result

    def lesson(user):
        curriculum = load_curriculum(isolated, user)
        return load_lesson_bundle(isolated,user,curriculum.current_knowledge_point_id)

    def project_task():
        client = TestClient(api.app)
        bundle = lesson(advanced)
        proposal = record("advanced-project-proposal", lambda: client.post("/api/lesson/proposals", json={
            "user_id": advanced, "base_revision": lesson_revision(bundle.manifest), "kind": "supplemental",
            "instruction": "再追加一个比当前更难的编程项目：并发请求取消与资源泄漏排查。请分三步引导，给提示和可运行的测试验收要求，不要直接给完整答案。",
        }))
        if proposal.get("status") != 200 or not proposal.get("body", {}).get("proposal_id"):
            return
        proposal_id = proposal["body"]["proposal_id"]
        candidate = record("advanced-project-candidate", lambda: client.post(
            f"/api/lesson/proposals/{proposal_id}/generate", json={"user_id": advanced, "confirmed": True},
        ))
        if candidate.get("status") != 200 or candidate.get("body", {}).get("status") != "candidate":
            return
        record("advanced-project", lambda: client.post(
            f"/api/lesson/proposals/{proposal_id}/apply", json={"user_id": advanced, "confirmed": True},
        ))

    def conversation_task():
        client = TestClient(api.app)
        bundle = lesson(interview)
        common = {"user_id":interview,"lesson_id":bundle.manifest.lesson_id}
        for name, message in [("interview-start","开始一场新的模拟面试，围绕刚学的 Python 入门内容，一次只问一个问题。"),("interview-answer","我觉得 python --version 是运行我写好的程序，打开编辑器就表示 Python 已经装好了。"),("interview-reference","这题我还不会，请给我参考答案并解释，别记成我已经掌握。")]:
            record(name, lambda message=message:client.post("/api/chat/stream",json={**common,"message":message}))
        bundle = lesson(interview)
        page = next(page for page in bundle.manifest.pages if page.code.strip())
        quote = page.code.strip().splitlines()[0]
        ref = {"lesson_id":bundle.manifest.lesson_id,"page_id":page.id,"revision":lesson_revision(bundle.manifest),"quote":quote}
        record("quoted-explanation",lambda:client.post("/api/chat/stream",json={**common,"message":"结束模拟面试。请解释我选中的这一行，告诉零基础的我应该在哪里输入。","reference":ref}))
        record("history-reload",lambda:client.get("/api/chat/history",params={"user_id":interview,"lesson_id":bundle.manifest.lesson_id}))

    print(str(run),flush=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda task:task(), [project_task,conversation_task]))


if __name__ == "__main__":
    main()
