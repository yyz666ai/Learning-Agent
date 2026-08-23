from __future__ import annotations

from datetime import datetime
from pathlib import Path

from backend.reminders import due_reminders, read_reminder, save_reminder


def test_reminder_persists_inside_user_directory(tmp_path: Path) -> None:
    saved = save_reminder(tmp_path, "learner", enabled=True, reminder_time="20:15", kind="both")

    assert saved["enabled"] is True
    assert saved["time"] == "20:15"
    assert read_reminder(tmp_path, "learner") == saved
    assert (tmp_path / "userdir/u_learner/preferences/reminder.json").is_file()


def test_due_reminders_fire_once_per_local_day(tmp_path: Path) -> None:
    save_reminder(tmp_path, "learner", enabled=True, reminder_time="20:15", kind="review")
    now = datetime(2026, 8, 20, 20, 15)

    due = due_reminders(tmp_path, now)
    assert due[0][0] == "learner"

    save_reminder(
        tmp_path,
        "learner",
        enabled=True,
        reminder_time="20:15",
        kind="review",
        last_sent_date="2026-08-20",
    )
    assert due_reminders(tmp_path, now) == []


def test_invalid_time_or_user_is_rejected(tmp_path: Path) -> None:
    for user_id, reminder_time in (("../escape", "20:15"), ("learner", "25:99")):
        try:
            save_reminder(tmp_path, user_id, enabled=True, reminder_time=reminder_time, kind="learn")
        except ValueError:
            pass
        else:
            raise AssertionError("invalid reminder input should fail")
