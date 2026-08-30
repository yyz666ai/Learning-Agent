"""Durable, session-bound diagnosis jobs for the single-process local server.

Only validated diagnostic sessions are committed. Job files are outside project
snapshots; the active pointer is inside onboarding so restoring a project cannot
make a late worker write into a different course. This is not a distributed queue.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .diagnostics import public_session, summarize_diagnosis
from .generation_transaction import project_lock
from .learning_content import SAFE_USER_ID
from .user_memory import _atomic_json, read_intent_state
from .onboarding import OnboardingSubmission

REQUEST_ID = re.compile(r"[A-Za-z0-9_-]{1,100}")
ACTIVE = {"queued", "running"}


class StaleDiagnosis(ValueError):
    pass


def _read(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except FileNotFoundError:
        return {}


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class DiagnosisJobs:
    def __init__(self, root: Path, max_workers=2, max_seconds=300):
        self.root = Path(root)
        self.instance = uuid.uuid4().hex
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="diagnosis")
        self.futures = {}
        self.max_seconds = max_seconds

    def shutdown(self):
        self.executor.shutdown(wait=True, cancel_futures=True)

    def _user(self, user):
        if not SAFE_USER_ID.fullmatch(user):
            raise ValueError("invalid user_id")
        return self.root / "userdir" / f"u_{user}"

    def _path(self, user, rid):
        if not REQUEST_ID.fullmatch(rid):
            raise ValueError("invalid request_id")
        return self._user(user) / ".diagnosis-jobs" / f"{rid}.json"

    def _pointer(self, user):
        return self._user(user) / "onboarding" / "diagnosis-task.json"

    def _fingerprint(self, user):
        return _digest(_read(self._user(user) / "learning-state.json"))

    def _current(self, user, job):
        intent = read_intent_state(self.root, user)
        return (intent.get("session_id") == job.get("intent_session_id")
                and intent.get("revision") == job.get("intent_revision")
                and (self._confirmation_state_matches(user, job)
                     if job.get("confirmation") else self._fingerprint(user) == job.get("project_fingerprint"))
                and _read(self._pointer(user)).get("request_id") == job["request_id"])

    def _confirmation_state_matches(self, user, job):
        """Permit only the original confirmation or its exact lease cancellation.

        Do not ignore revision or broadly compare topic names: restoring another
        project or changing its content must still invalidate an old tab.
        """
        expected = job["confirmation"]["state"]
        actual = _read(self._user(user) / "learning-state.json")
        cancelled = dict(expected, generation_id=None, generation_status="cancelled",
                         revision=expected["revision"] + 1)
        return actual == expected or (expected.get("generation_status") == "active" and actual == cancelled)

    def _save(self, user, job):
        _atomic_json(self._path(user, job["request_id"]), job)

    def _end(self, user, job, status, message):
        job.update(status=status, phase=status, error=message, finished_at=time.time())
        self._save(user, job)

    def _load(self, user, rid):
        job = _read(self._path(user, rid))
        if not job:
            raise KeyError(rid)
        if job["status"] in ACTIVE:
            if job.get("owner") != self.instance:
                self._end(user, job, "interrupted", "服务已重启，原诊断任务已中断。请点击重试。")
            elif time.time() - job["created_at"] > self.max_seconds:
                self._end(user, job, "failed", "诊断生成超过等待上限，请点击重试。")
            elif not self._current(user, job):
                self._end(user, job, "cancelled", "学习目标或项目已变化，旧诊断结果不会应用。")
        return job

    def _public(self, user, job):
        keys = ("request_id", "status", "phase", "intent_session_id", "intent_revision", "error", "submission")
        payload = {key: job[key] for key in keys if key in job}
        payload["elapsed_seconds"] = round(max(0, job.get("finished_at", time.time()) - job["created_at"]), 2)
        payload["retryable"] = job["status"] in {"failed", "interrupted"}
        if job["status"] == "completed":
            # Read the authoritative answered state, not the first-question snapshot.
            session = _read(self._user(user) / "onboarding" / "diagnostic.json")
            if not self._current(user, job) or session.get("session_id") != job.get("diagnostic_session_id"):
                payload.update(status="cancelled", phase="cancelled", error="诊断已不属于当前目标，请刷新后继续。")
            else:
                result = public_session(session)
                result.update(next="confirm" if session["complete"] else "diagnosis", diagnostic_source=session.get("diagnostic_source"))
                if session["complete"]:
                    result["diagnosis"] = summarize_diagnosis(session).model_dump()
                payload["result"] = result
        return payload

    def start(self, user, rid, intent_session_id, intent_revision, submission, work):
        # Same lock ordering in start/commit. Generation itself never holds either lock.
        with project_lock(self.root, user), self.lock:
            path = self._path(user, rid)
            signature = _digest([intent_session_id, intent_revision, submission])
            if path.exists():
                job = self._load(user, rid)
                if job.get("signature") is not None and job["signature"] != signature:
                    raise StaleDiagnosis("同一请求标识不能用于不同诊断内容。")
                return self._public(user, job)
            intent = read_intent_state(self.root, user)
            if not intent_session_id or intent.get("session_id") != intent_session_id or intent.get("revision") != intent_revision:
                raise StaleDiagnosis("建档状态已更新，请刷新后继续。")
            normalized = intent.get("onboarding") or {}
            if intent.get("action") != "ready_for_plan" or not normalized:
                raise StaleDiagnosis("请先完成学习目标确认，再开始诊断。")
            expected = {key: value for key, value in normalized.items() if key != "topic_type"}
            expected.update(user_id=user, topic={"type": normalized.get("topic_type", "custom"), "value": (intent.get("slots") or {}).get("topic")})
            try:
                if OnboardingSubmission.model_validate(expected) != OnboardingSubmission.model_validate(submission):
                    raise StaleDiagnosis("诊断内容与已确认目标不一致，请刷新后继续。")
            except ValueError as exc:
                raise StaleDiagnosis("诊断内容与已确认目标不一致，请刷新后继续。") from exc
            self.futures = {key: value for key, value in self.futures.items() if not value.done()}
            if len(self.futures) >= 8:
                raise RuntimeError("诊断队列繁忙，请稍后重试。")
            old = _read(self._pointer(user)).get("request_id")
            if old:
                self.cancel(user, old)
            job = dict(request_id=rid, signature=signature, owner=self.instance, status="queued", phase="queued",
                       created_at=time.time(), intent_session_id=intent_session_id, intent_revision=intent_revision,
                       project_fingerprint=self._fingerprint(user), submission=submission)
            self._save(user, job)
            _atomic_json(self._pointer(user), {"request_id": rid})
            self.futures[(user, rid)] = self.executor.submit(self._run, user, rid, work)
            return self._public(user, job)

    def _run(self, user, rid, work):
        def phase(name):
            with self.lock:
                job = self._load(user, rid)
                if job["status"] not in ACTIVE:
                    raise StaleDiagnosis("diagnosis no longer active")
                job.update(status="running", phase=name)
                self._save(user, job)
        try:
            phase("generating")
            session = work(phase)
            # Validate public shape before any filesystem commit; no model writes allowed.
            public_session(session)
            with project_lock(self.root, user), self.lock:
                job = self._load(user, rid)
                if job["status"] not in ACTIVE or not self._current(user, job):
                    return
                _atomic_json(self._user(user) / "onboarding" / "diagnostic.json", session)
                job.update(status="completed", phase="completed", finished_at=time.time(), diagnostic_session_id=session["session_id"])
                self._save(user, job)
        except StaleDiagnosis:
            return
        except Exception:
            # Never expose raw model/process exception text (it may include credentials).
            with self.lock:
                job = self._load(user, rid)
                if job["status"] in ACTIVE:
                    self._end(user, job, "failed", "诊断题暂时未生成完成，你的目标已保留，请点击重试。")

    def get(self, user, rid):
        with self.lock:
            return self._public(user, self._load(user, rid))

    def current(self, user):
        with self.lock:
            rid = _read(self._pointer(user)).get("request_id")
            if not rid:
                return {"status": "none"}
            try:
                return self.get(user, rid)
            except KeyError:
                return {"status": "none"}

    def validate_answer(self, user, session_id):
        """Caller holds project_lock across validation and read/modify/write."""
        with self.lock:
            rid = _read(self._pointer(user)).get("request_id")
            if not rid:
                return  # Legacy synchronous clients have no job pointer.
            current = self.get(user, rid)
            if current["status"] != "completed" or current.get("result", {}).get("session_id") != session_id:
                raise StaleDiagnosis("这份诊断已经过期，请刷新后继续当前目标。")

    def confirm(self, user, session_id, submission, work):
        """Replay a durable confirmation; renew only an explicitly cancelled lease."""
        with project_lock(self.root, user), self.lock:
            self.validate_answer(user, session_id)
            rid = _read(self._pointer(user)).get("request_id")
            if not rid:
                return work()  # Legacy synchronous client.
            job = self._load(user, rid)
            if OnboardingSubmission.model_validate(submission) != OnboardingSubmission.model_validate(job["submission"]):
                raise StaleDiagnosis("确认内容与这轮诊断目标不一致，请刷新后继续。")
            receipt = job.get("confirmation")
            current = _read(self._user(user) / "learning-state.json")
            if receipt and current == receipt["state"]:
                return receipt["result"]
            result = work()
            job["confirmation"] = {
                "state": _read(self._user(user) / "learning-state.json"),
                "result": result,
            }
            self._save(user, job)
            return result

    def cancel(self, user, rid):
        with self.lock:
            path = self._path(user, rid)
            job = _read(path)
            if not job:
                job = {"request_id": rid, "created_at": time.time()}
            elif job["status"] not in ACTIVE:
                return self._public(user, job)
            self._end(user, job, "cancelled", "这轮诊断已取消，迟到结果不会应用。")
            future = self.futures.get((user, rid))
            if future:
                future.cancel()
            return self._public(user, job)
