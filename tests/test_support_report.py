import json

import pytest
from fastapi.testclient import TestClient

from backend import main, support_report
from tests.test_api import onboarding_payload
from tests.test_curriculum import GO_PLAN
from backend.curriculum import curriculum_from_plan


def test_export_available_without_lesson_and_contains_no_private_files(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    user = tmp_path / "userdir/u_demo"
    user.mkdir(parents=True)
    (user / "profile.md").write_text("private-profile-secret")
    (tmp_path / ".secrets.env").write_text("DEEPSEEK_API_KEY=private-api-secret")
    response = TestClient(main.app).get("/api/support/bug-report?user_id=demo")
    assert response.status_code == 200
    assert 'attachment;' in response.headers["content-disposition"]
    assert response.json()["generation"] == {}
    assert response.json()["privacy"]["includes_conversation"] is False
    assert "private-" not in response.text
    assert str(tmp_path) not in response.text
    assert not (user / "diagnostics").exists()  # Download does not create state.


def test_generation_report_is_allowlisted_and_scoped(tmp_path):
    support_report.record_generation(tmp_path, "demo", "lesson", error=ValueError(
        "generated lesson drifted: scope evidence needs at least two relevant pages for private-title"
    ))
    report = support_report.build_report(tmp_path, "demo")
    assert report["generation"]["lesson"]["status"] == "failed"
    assert report["generation"]["lesson"]["rule"] == "scope_relevant_pages"
    assert "private-title" not in json.dumps(report)
    assert support_report.build_report(tmp_path, "another")["generation"] == {}
    support_report.record_generation(tmp_path, "demo", "lesson")
    assert support_report.build_report(tmp_path, "demo")["generation"]["lesson"]["status"] == "succeeded"


@pytest.mark.parametrize("payload", ["not json", "[]", '{"lesson":{"status":[]}}', '{"lesson":{"status":"my-secret","prompt":"secret"}}',
    '{"lesson":{"status":"failed","category":"validation","rule":"scope_relevant_pages","at":"api-secret"}}'])
def test_malformed_or_tampered_records_are_not_exported(tmp_path, payload):
    folder = tmp_path / "userdir/u_demo/diagnostics"
    folder.mkdir(parents=True)
    (folder / "generation.json").write_text(payload)
    assert support_report.build_report(tmp_path, "demo")["generation"] == {}


@pytest.mark.parametrize("user_id", ["../demo", "", "x" * 65])
def test_export_rejects_invalid_user_id(tmp_path, monkeypatch, user_id):
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    assert TestClient(main.app).get("/api/support/bug-report", params={"user_id": user_id}).status_code == 422


def test_diagnostics_write_failure_does_not_fail_successful_generation(tmp_path, monkeypatch):
    def fail(*args):
        raise OSError("disk unavailable")
    monkeypatch.setattr(support_report, "_atomic_json", fail)
    support_report.record_generation(tmp_path, "demo", "lesson")


@pytest.mark.parametrize("outputs,available,category", [
    (["[超时] 原始调用失败"], True, "provider"),
    (["无效草案", "[超时] 修复调用失败"], True, "provider"),
    (["无效草案", "仍无效"], True, "validation"),
    ([], False, "provider"),
])
def test_plan_early_failure_overwrites_previous_success(tmp_path, monkeypatch, outputs, available, category):
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    monkeypatch.setattr(main, "latest_release", lambda: tmp_path / "release" if available else None)
    responses = iter(outputs)
    monkeypatch.setattr(main, "chat", lambda *a, **k: next(responses))
    client = TestClient(main.app)
    payload = onboarding_payload("support-demo")
    payload["generation_id"] = client.post("/api/onboarding/confirm", json=payload).json()["generation_id"]
    support_report.record_generation(tmp_path, "support-demo", "plan")
    result = client.post("/api/plans/personalize", json=payload)
    assert result.status_code == 200 and result.json()["personalized"] is False
    record = client.get("/api/support/bug-report?user_id=support-demo").json()["generation"]["plan"]
    assert record["status"] == "failed"
    assert record["category"] == category


def test_lesson_unavailable_overwrites_previous_success(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    monkeypatch.setattr(main, "latest_release", lambda: None)
    monkeypatch.setattr(main, "read_learning_context", lambda *a: {"profile_status": "confirmed", "plan_status": "confirmed"})
    curriculum = curriculum_from_plan(GO_PLAN, topic="Go", route="foundation_engineer", level="zero")
    monkeypatch.setattr(main, "load_curriculum", lambda *a: curriculum)
    monkeypatch.setattr(main, "project_guard", lambda *a: None)
    monkeypatch.setattr(main, "load_completed_chapter", lambda *a: None)
    support_report.record_generation(tmp_path, "demo", "lesson")
    client = TestClient(main.app)
    assert client.post("/api/lesson/generate", json={"user_id": "demo"}).status_code == 503
    record = client.get("/api/support/bug-report?user_id=demo").json()["generation"]["lesson"]
    assert record["status"] == "failed"
    assert record["category"] == "provider"
