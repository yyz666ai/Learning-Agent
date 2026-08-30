"""Real intent evaluation in temporary learner storage; never generates lessons.

Run: .venv/bin/python tools/evaluate_intent.py --output evals/runs/intent-after
Optional --cases JSON accepts [{name, messages, active?}], --repeat N.
No API secrets or production conversations are included in results.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CASES = [
    {"name": "concept", "messages": ["RAG 是什么意思？"]},
    {"name": "concept_code", "messages": ["我是初学者，解释一下 RAG 是什么，还要用 Python 最小代码演示它怎么实现。"]},
    {"name": "greeting", "messages": ["你好"]},
    {"name": "topic_only", "messages": ["我想学 Go", "初学", "我要完整学会 Go，从零到能独立开发后端项目"]},
    {"name": "beginner_full", "messages": ["我零基础，想系统学 Python，直到能独立开发项目。"]},
    {"name": "project", "messages": ["我是初学者，想用 LangGraph 做一个客服 Agent。"]},
    {"name": "gap", "messages": ["我学过一点 Java，想查漏补缺，重点补泛型和并发。"]},
    {"name": "senior", "messages": ["我是熟练的 Go 工程师，想进阶高级工程师，深入并发、性能调优与分布式系统，最后做一个完整项目。"]},
    {"name": "urgent_repo", "messages": ["我有一点基础，只有两天，要看懂同事的 LangGraph 客服项目，不用从头学整门 Python。"]},
    {"name": "syntax", "messages": ["我有一点基础，只想看懂 Java 语法以便读项目，不想做完整工程课程。"]},
    {"name": "interview", "messages": ["我要面试前端岗", "初学", "React 和 TypeScript", "暂时没有，你先按常见题准备"]},
    {"name": "interview_complete", "messages": ["我要面试 AI 前端，初学，技术栈是 React 和 TypeScript，没有现成面试题。"]},
    {"name": "interview_material", "messages": ["我要面试 Java 后端，有一点基础，技术栈 Spring Boot 和 MySQL。我整理了题：1. Spring 如何解决循环依赖？2. MySQL 索引为什么用 B+ 树？", "请根据已收录的题目继续制定计划"]},
    {"name": "interview_pm", "messages": ["我是熟练的产品经理，想面试 AI 产品经理", "我不写代码，重点是 RAG 产品设计、评测和业务落地", "没有"]},
    {"name": "natural_level", "messages": ["我写了三年 Python，做过两个线上项目，想用 FastAPI 开发服务端 API。"]},
    {"name": "negated_level", "messages": ["我不是零基础，我写了三年 Go，想进阶并发与性能优化。"]},
    {"name": "exam", "messages": ["我是计算机本科生，有一点基础，十天后考数据结构，按大学期末考试复习，重点是树、图和算法题。"]},
    {"name": "course", "messages": ["本科操作系统跟课学习，有C基础，每周按课程章节练习"]},
    {"name": "current_definition", "active": True, "messages": ["这里的 state 是什么意思？"]},
    {"name": "current_error", "active": True, "messages": ["这段代码为什么报 TypeError？"]},
    {"name": "correction", "messages": ["我想学 Go", "不对，我想学 Java，我是初学者，只想看懂现有项目。"]},
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cases", type=Path)
    parser.add_argument("--repeat", type=int, default=1, choices=range(1, 4))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    from backend import main as api
    from backend.user_memory import read_intent_state
    ctx = threading.local()
    original = api.intent_chat
    def traced(prompt, skill):
        start = time.monotonic()
        try:
            raw = original(prompt, skill)
        except Exception as exc:
            # Record type only: URLs/headers or provider exception text may contain secrets.
            ctx.calls.append({"seconds": round(time.monotonic()-start, 3),
                              "error_type": type(exc.__cause__ or exc).__name__})
            raise
        ctx.calls.append({"seconds": round(time.monotonic()-start, 3), "raw": raw})
        return raw
    api.intent_chat = traced
    original_validate = api.validate_intent_against_message
    original_parse = api.parse_intent_response
    def trace_check(check, stage):
        def checked(*values, **kwargs):
            try:
                return check(*values, **kwargs)
            except Exception as exc:
                ctx.failures.append({"stage": stage, "error": str(exc)})
                raise
        return checked
    api.validate_intent_against_message = trace_check(original_validate, "semantic_validation")
    api.parse_intent_response = trace_check(original_parse, "structure_validation")
    api.latest_release = lambda: ROOT / "workspace/dev"
    cases = json.loads(args.cases.read_text()) if args.cases else CASES
    source_hashes = {relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() for relative in (
        "backend/learning_intent.py", "backend/main.py", "backend/user_memory.py",
        "workspace/dev/.codex/skills/learning-intent-router/SKILL.md")}
    with tempfile.TemporaryDirectory(prefix="learning-intent-eval-") as isolated:
        api.SERVER_ROOT = Path(isolated)
        def run(item):
            case, repetition = item
            user = f"eval_{case['name']}_{repetition}"
            rows, slots = [], {}
            for i, message in enumerate(case["messages"]):
                ctx.calls = []
                ctx.failures = []
                before = read_intent_state(api.SERVER_ROOT, user)
                started = time.monotonic()
                result, error = None, None
                try:
                    result = api.onboarding_intent(api.IntentRequest(
                        user_id=user, message=message, slots=slots,
                        session_id=user, request_id=f"r{i}", revision=before.get("revision"),
                        reset_session=i==0, has_active_project=bool(case.get("active")),
                        clarification_count=i, history=[],  # exercise server recovery
                    ))
                except Exception as exc:
                    error = {"type": type(exc).__name__, "detail": getattr(exc, "detail", str(exc))}
                rows.append({"input": message, "before": before, "result": result, "error": error,
                             "seconds": round(time.monotonic()-started, 3), "calls": ctx.calls, "validation_errors": ctx.failures})
                print(json.dumps({"case":case["name"],"repeat":repetition,"round":i+1,
                    "action":(result or {}).get("action"),"question":(result or {}).get("question"),
                    "error":error,"calls":len(ctx.calls)},ensure_ascii=False),flush=True)
                if not result or result["action"] in {"ready_for_plan", "answer_in_context"}:
                    break
                slots = result["slots"]
            return {"name":case["name"],"repeat":repetition,"rounds":rows}
        jobs = [(case, n+1) for case in cases for n in range(args.repeat)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(run, jobs))
    skill = ROOT / "workspace/dev/.codex/skills/learning-intent-router/SKILL.md"
    metadata = {"scope":"real intent handler, isolated state, no browser or Plan/PPT generation",
        "git_head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "working_tree":subprocess.check_output(["git","status","--short"],cwd=ROOT,text=True),
        "skill_sha256":hashlib.sha256(skill.read_bytes()).hexdigest(),
        "model":"deepseek-v4-flash","thinking":False,"temperature":0,
        "source_sha256_at_start": source_hashes}
    (args.output/"results.json").write_text(json.dumps({"metadata":metadata,"cases":results},ensure_ascii=False,indent=2))
    print(f"Saved {len(results)} case runs to {args.output/'results.json'}")


if __name__ == "__main__":
    main()
