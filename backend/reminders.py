"""Persistent daily study reminders delivered by the local backend service."""

from __future__ import annotations

import json
import platform
import re
import subprocess
import threading
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from .learning_content import SAFE_USER_ID

ReminderKind = Literal["learn", "review", "both"]
SAFE_TIME = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def _path(server_root: Path, user_id: str) -> Path:
    if not SAFE_USER_ID.fullmatch(user_id):
        raise ValueError("invalid user_id")
    return server_root / "userdir" / f"u_{user_id}" / "preferences" / "reminder.json"


def _with_capability(preference: dict[str, Any]) -> dict[str, Any]:
    """enabled is the saved preference, never a guarantee of notification delivery."""
    supported = platform.system() == "Darwin"
    return {
        **preference,
        "notification_supported": supported,
        "message": (
            "系统通知需要保持本机服务运行，并在系统设置中允许通知。"
            if supported else
            "当前平台尚不支持系统通知；提醒偏好仍可保存，但不会发送通知。"
        ),
    }


def read_reminder(server_root: Path, user_id: str) -> dict[str, Any]:
    path = _path(server_root, user_id)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        value = None
    return _with_capability(value if isinstance(value, dict) else {
        "enabled": False, "time": "20:00", "kind": "both", "last_sent_date": None,
    })


def save_reminder(
    server_root: Path,
    user_id: str,
    *,
    enabled: bool,
    reminder_time: str,
    kind: ReminderKind,
    last_sent_date: str | None = None,
) -> dict[str, Any]:
    path = _path(server_root, user_id)
    if not SAFE_TIME.fullmatch(reminder_time):
        raise ValueError("invalid reminder time")
    if kind not in {"learn", "review", "both"}:
        raise ValueError("invalid reminder kind")
    payload = {"enabled": enabled, "time": reminder_time, "kind": kind, "last_sent_date": last_sent_date}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return _with_capability(payload)


def due_reminders(server_root: Path, now: datetime | None = None) -> list[tuple[str, dict[str, Any]]]:
    selected_now = now or datetime.now().astimezone()
    current_time = selected_now.strftime("%H:%M")
    today = selected_now.date().isoformat()
    user_root = server_root / "userdir"
    if not user_root.is_dir():
        return []
    due: list[tuple[str, dict[str, Any]]] = []
    for path in user_root.glob("u_*/preferences/reminder.json"):
        user_id = path.parents[1].name.removeprefix("u_")
        reminder = read_reminder(server_root, user_id)
        if reminder.get("enabled") and reminder.get("time") == current_time and reminder.get("last_sent_date") != today:
            due.append((user_id, reminder))
    return due


def send_system_notification(kind: str) -> bool:
    if platform.system() != "Darwin":
        return False
    message = "今天的学习和复习已经准备好。" if kind == "both" else "今天的复习卡片已经准备好。" if kind == "review" else "今天的学习小步已经准备好。"
    script = 'on run argv\ndisplay notification (item 1 of argv) with title "Learning Agent"\nend run'
    result = subprocess.run(["osascript", "-e", script, message], capture_output=True, text=True, timeout=10)
    return result.returncode == 0


class ReminderScheduler:
    def __init__(self, root_provider: Callable[[], Path], interval_seconds: int = 30) -> None:
        self.root_provider = root_provider
        self.interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="learning-reminders", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            now = datetime.now().astimezone()
            for user_id, reminder in due_reminders(self.root_provider(), now):
                if send_system_notification(str(reminder.get("kind") or "both")):
                    save_reminder(
                        self.root_provider(), user_id,
                        enabled=True, reminder_time=str(reminder["time"]), kind=reminder.get("kind", "both"),
                        last_sent_date=now.date().isoformat(),
                    )
