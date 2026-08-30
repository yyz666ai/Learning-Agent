"""A Plan may receive one structural repair, without confirmation or early writes."""
import json
import logging
from pathlib import Path

import pytest
from fastapi import HTTPException

from backend import main
from backend.onboarding import OnboardingSubmission, confirm_onboarding
from tests.test_plan_list_wrapper import plan


@pytest.fixture
def learner(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    monkeypatch.setattr(main, "latest_release", lambda: Path("/synthetic/release"))
    selected = OnboardingSubmission.model_validate({
        "user_id": "plan_repair", "learning_mode": "systematic",
        "goal_route": "foundation_engineer", "level_claim": "zero",
        "topic": {"type": "go", "value": "Go"},
        "session_minutes": 40, "teaching_preference": "hands_on",
    })
    confirmation = confirm_onboarding(tmp_path, selected, None)
    request = main.PlanPersonalizeRequest.model_validate({
        **selected.model_dump(), "generation_id": confirmation["generation_id"],
    })
    user = tmp_path / "userdir/u_plan_repair"
    plan_path = user / confirmation["active_plan"]
    return request, user, plan_path, plan_path.read_bytes()


def model_outputs(monkeypatch, outputs, plan_path, original):
    calls = []

    def chat(user_id, prompt, release, **options):
        assert plan_path.read_bytes() == original, "Plan was written before validation"
        calls.append((prompt, options))
        assert len(calls) <= len(outputs), "Unexpected extra generation attempt"
        return outputs[len(calls) - 1]

    monkeypatch.setattr(main, "chat", chat)
    return calls


def test_valid_initial_plan_uses_one_call_and_waits_for_confirmation(learner, monkeypatch):
    request, user, path, original = learner
    calls = model_outputs(monkeypatch, [plan()], path, original)
    result = main.personalize_plan(request)
    assert result["personalized"] is True and len(calls) == 1
    assert result["plan_status"] == "awaiting_confirmation"
    assert json.loads((user / "learning-state.json").read_text())["plan_status"] == "awaiting_confirmation"


def test_missing_heading_is_repaired_once_without_research_or_early_commit(
    learner, monkeypatch, caplog,
):
    request, user, path, original = learner
    invalid = plan().replace("## 知识覆盖地图", "## 课程领域")
    calls = model_outputs(monkeypatch, [invalid, plan()], path, original)
    with caplog.at_level(logging.INFO, logger=main.logger.name):
        result = main.personalize_plan(request)
    assert result["personalized"] is True and len(calls) == 2
    assert calls[1][1] == {"generation": "plan", "allow_research": False}
    assert calls[0][0] in calls[1][0] and invalid in calls[1][0]
    assert "缺失的必需标题：## 知识覆盖地图" in calls[1][0]
    assert "不重新询问画像" in calls[1][0] and "不联网" in calls[1][0]
    assert "plan.repair" in caplog.text and "## 知识覆盖地图" in caplog.text
    assert result["plan_status"] == "awaiting_confirmation"
    assert json.loads((user / "learning-state.json").read_text())["plan_status"] == "awaiting_confirmation"


def test_two_invalid_plans_leave_original_state_and_never_loop(learner, monkeypatch):
    request, user, path, original = learner
    state_path = user / "learning-state.json"
    original_state = state_path.read_bytes()
    calls = model_outputs(monkeypatch, ["invalid first", "invalid second"], path, original)
    result = main.personalize_plan(request)
    assert len(calls) == 2 and result["reason"] == "validation_failed"
    assert result["personalized"] is False
    assert path.read_bytes() == original and state_path.read_bytes() == original_state


def test_cancelled_lease_stops_before_repair(learner, monkeypatch, tmp_path):
    request, _, path, original = learner
    calls = []

    def chat(*args, **kwargs):
        calls.append(args)
        main.cancel_generation(tmp_path, request.user_id, request.generation_id)
        return "invalid cancelled output"

    monkeypatch.setattr(main, "chat", chat)
    with pytest.raises(HTTPException) as failure:
        main.personalize_plan(request)
    assert failure.value.status_code == 409
    assert len(calls) == 1 and path.read_bytes() == original


@pytest.mark.parametrize("error", ["[出错] model failed", "[超时] model timeout", "[空回复]"])
def test_initial_transport_failure_does_not_trigger_repair(learner, monkeypatch, error):
    request, _, path, original = learner
    calls = model_outputs(monkeypatch, [error], path, original)
    result = main.personalize_plan(request)
    assert result["reason"] == "model_generation_failed" and len(calls) == 1
    assert path.read_bytes() == original


def test_repair_transport_failure_stops_without_a_third_attempt(learner, monkeypatch):
    request, user, path, original = learner
    original_state = (user / "learning-state.json").read_bytes()
    calls = model_outputs(monkeypatch, ["invalid draft", "[出错] transport failed"], path, original)
    result = main.personalize_plan(request)
    assert result["reason"] == "model_generation_failed" and len(calls) == 2
    assert path.read_bytes() == original
    assert (user / "learning-state.json").read_bytes() == original_state


@pytest.mark.parametrize("route", ["academic_course", "concept_clarity", "senior_engineer"])
def test_repair_required_headings_are_route_specific(learner, monkeypatch, route):
    request, user, path, original = learner
    request = request.model_copy(update={"goal_route": route})
    state_path = user / "learning-state.json"
    state = json.loads(state_path.read_text())
    state["goal_route"] = route
    state_path.write_text(json.dumps(state), encoding="utf-8")
    calls = model_outputs(monkeypatch, ["invalid draft", "still invalid"], path, original)
    result = main.personalize_plan(request)
    assert result["reason"] == "validation_failed" and len(calls) == 2
    required_line = next(line for line in calls[1][0].splitlines()
                         if line.startswith("本路线严格必需标题："))
    assert "## 当前任务、## 学习成果、## 教学策略" in required_line
    assert ("## 毕业项目" in required_line) == (route == "senior_engineer")


def test_repaired_plan_still_checks_original_research_requirement(learner, monkeypatch):
    request, _, path, original = learner
    monkeypatch.setattr(main, "requires_authoritative_research", lambda *a, **k: True)
    calls = model_outputs(monkeypatch, ["invalid first", plan()], path, original)
    research_checks = []

    def invalid_research(*args, **kwargs):
        research_checks.append(kwargs)
        raise ValueError("synthetic missing research")

    monkeypatch.setattr(main, "load_valid_research", invalid_research)
    result = main.personalize_plan(request)
    assert len(calls) == 2 and len(research_checks) == 1
    assert calls[0][1]["allow_research"] is True
    assert calls[1][1]["allow_research"] is False
    assert result["reason"] == "research_validation_failed"
    assert path.read_bytes() == original
