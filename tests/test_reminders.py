from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json

import pytest
from fastapi.testclient import TestClient

from backend import main, reminders
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


@pytest.mark.parametrize('system', ['Windows', 'Linux'])
def test_unsupported_reminders_api_preserves_preference_without_claiming_notifications(tmp_path, monkeypatch, system):
    monkeypatch.setattr(main, 'SERVER_ROOT', tmp_path)
    monkeypatch.setattr(reminders.platform, 'system', lambda: system)
    client = TestClient(main.app)
    default = client.get('/api/reminders?user_id=platform').json()
    assert default['notification_supported'] is False
    response = client.post('/api/reminders', json={
        'user_id': 'platform', 'enabled': True, 'time': '20:15', 'kind': 'both',
    })
    assert response.status_code == 200
    saved = response.json()
    assert saved['enabled'] is True  # Preference, not delivery capability.
    assert saved['notification_supported'] is False
    assert '不会发送通知' in saved['message'] and '偏好' in saved['message']
    assert client.get('/api/reminders?user_id=platform').json() == saved
    raw = json.loads((tmp_path / 'userdir/u_platform/preferences/reminder.json').read_text())
    assert raw['enabled'] is True and 'notification_supported' not in raw


def test_notification_capability_is_recomputed_for_current_platform(tmp_path, monkeypatch):
    monkeypatch.setattr(reminders.platform, 'system', lambda: 'Windows')
    save_reminder(tmp_path, 'portable', enabled=True, reminder_time='20:15', kind='both')
    monkeypatch.setattr(reminders.platform, 'system', lambda: 'Darwin')
    current = read_reminder(tmp_path, 'portable')
    assert current['enabled'] is True and current['notification_supported'] is True
    assert '服务运行' in current['message']
    saved = save_reminder(tmp_path, 'portable', enabled=False, reminder_time='20:15', kind='both')
    assert saved['notification_supported'] is True
