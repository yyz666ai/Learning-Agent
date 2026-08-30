"""Learner-owned current facts and append-only memory events."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from collections import deque
from pathlib import Path
from typing import Any

try:
    from .learning_content import SAFE_USER_ID
except ImportError:
    from learning_content import SAFE_USER_ID


def _user_dir(server_root: Path, user_id: str) -> Path:
    if not SAFE_USER_ID.fullmatch(user_id):
        raise ValueError("invalid user_id")
    return Path(server_root) / "userdir" / f"u_{user_id}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as temporary:
            json.dump(payload, temporary, ensure_ascii=False, indent=2)
            temporary.write("\n")
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    return path


def _append_jsonl(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return path


def read_intent_state(server_root: Path, user_id: str) -> dict[str, Any]:
    path = _user_dir(server_root, user_id) / "onboarding" / "intent-state.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": 1, "slots": {}}
    return value if isinstance(value, dict) else {"schema_version": 1, "slots": {}}


def persist_intent_decision(
    server_root: Path,
    user_id: str,
    *,
    message: str,
    decision: dict[str, Any],
    session_id: str | None = None,
    request_id: str | None = None,
    message_kind: str = "user",
) -> dict[str, Any]:
    user_dir = _user_dir(server_root, user_id)
    previous = read_intent_state(server_root, user_id)
    session_id = session_id or previous.get("session_id") or "legacy"
    history = list(previous.get("history") or []) if session_id == previous.get("session_id", "legacy") else []
    if message_kind == "user":
        history.append({"role": "user", "content": message.strip()[:4000]})
    reply = (decision.get("question") or {}).get("prompt") or decision.get("summary")
    if reply:
        history.append({"role": "assistant", "content": str(reply)[:1000]})
    recorded_at = _now()
    state = {
        "schema_version": 1,
        "session_id": session_id,
        "revision": int(previous.get("revision") or 0) + 1,
        "request_id": request_id,
        "history": history[-40:],
        "response": decision,
        "updated_at": recorded_at,
        "last_message": message.strip()[:4_000],
        "action": decision.get("action"),
        "summary": str(decision.get("summary") or "")[:1_000],
        "slots": decision.get("slots") if isinstance(decision.get("slots"), dict) else {},
        "question": decision.get("question") if isinstance(decision.get("question"), dict) else None,
        "onboarding": decision.get("onboarding") if isinstance(decision.get("onboarding"), dict) else None,
    }
    _atomic_json(user_dir / "onboarding" / "intent-state.json", state)
    _append_jsonl(user_dir / "onboarding" / "intent-events.jsonl", {
        "schema_version": 1,
        "recorded_at": recorded_at,
        "session_id": session_id,
        "request_id": request_id,
        "message": message.strip()[:4_000],
        "message_kind": message_kind,
        "decision": decision,
    })
    return state


def write_profile_json(
    server_root: Path,
    user_id: str,
    profile: dict[str, Any],
) -> Path:
    payload = {
        "schema_version": 1,
        **profile,
        "intent_slots": read_intent_state(server_root, user_id).get("slots", {}),
        "updated_at": _now(),
    }
    return _atomic_json(_user_dir(server_root, user_id) / "profile.json", payload)


def append_conversation_event(
    server_root: Path,
    user_id: str,
    *,
    role: str,
    content: str,
    lesson_id: str | None = None,
    status: str = "completed",
    reference: dict[str, Any] | None = None,
    chat_mode: str = "learning",
) -> Path:
    if role not in {"user", "assistant"}:
        raise ValueError("invalid conversation role")
    return _append_jsonl(
        _user_dir(server_root, user_id) / "memory" / "conversation-events.jsonl",
        {
            "schema_version": 1,
            "recorded_at": _now(),
            "role": role,
            "content": content.strip()[:20_000],
            "lesson_id": lesson_id,
            "status": status,
            "reference": reference,
            "chat_mode": chat_mode,
        },
    )


def read_conversation_events(server_root: Path, user_id: str, *, lesson_id: str | None = None, limit: int = 40) -> list[dict]:
    """Read the active project's memory only; tolerate an interrupted last line."""
    path = _user_dir(server_root, user_id) / "memory" / "conversation-events.jsonl"
    events: deque = deque(maxlen=max(1, min(limit, 100)))
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict) or event.get("role") not in {"user", "assistant"}:
                continue
            if lesson_id is not None and event.get("lesson_id") != lesson_id:
                continue
            if event.get("status") not in {"completed", "submitted"}:
                continue
            events.append(event)
    return list(events)
