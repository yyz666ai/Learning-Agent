from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.curriculum import Curriculum
from backend.generation_transaction import (
    GenerationStaleError,
    begin_generation_lease,
    cancel_generation,
    commit_plan_generation,
    project_guard,
    validate_generation_lease,
    validate_project_guard,
)


def _write_state(root: Path, *, generation_id: str = "gen-current", revision: int = 4) -> Path:
    user = root / "userdir/u_learner"
    (user / "plans").mkdir(parents=True)
    (user / "plans/ai-old-plan.md").write_text("# old plan\n", encoding="utf-8")
    (user / "learning-state.json").write_text(json.dumps({
        "active_topic": "AI前端",
        "active_plan": "plans/ai-old-plan.md",
        "goal_route": "interview_sprint",
        "plan_status": "draft",
        "revision": revision,
        "generation_id": generation_id,
        "generation_status": "active",
    }, ensure_ascii=False), encoding="utf-8")
    return user


def _curriculum(topic: str = "AI前端") -> Curriculum:
    return Curriculum.model_validate({
        "topic": topic,
        "route": "interview_sprint",
        "level": "zero",
        "current_knowledge_point_id": "one",
        "chapters": [{
            "id": "chapter-1", "title": "基础", "knowledge_points": [
                {
                    "id": key, "title": f"知识点 {key}", "outcome": "能解释",
                    "practice": "完成练习", "mastery_criteria": "回答正确",
                    "prerequisites": [] if index == 0 else [previous],
                    "status": "active" if index == 0 else "upcoming",
                }
                for index, (key, previous) in enumerate([
                    ("one", ""), ("two", "one"), ("three", "two"),
                    ("four", "three"), ("five", "four"),
                ])
            ],
        }],
    })


def test_late_plan_result_cannot_write_after_project_restore(tmp_path: Path) -> None:
    user = _write_state(tmp_path)
    original_plan = (user / "plans/ai-old-plan.md").read_text(encoding="utf-8")
    restored = json.loads((user / "learning-state.json").read_text(encoding="utf-8"))
    restored.update({"active_topic": "Go", "generation_id": None, "revision": 9})
    (user / "learning-state.json").write_text(json.dumps(restored), encoding="utf-8")

    with pytest.raises(GenerationStaleError):
        commit_plan_generation(
            tmp_path, "learner", "gen-current",
            plan_markdown="# AI前端 新计划\n", curriculum=_curriculum(),
        )

    assert (user / "plans/ai-old-plan.md").read_text(encoding="utf-8") == original_plan
    assert not (user / "curriculum.json").exists()


def test_cancelled_generation_cannot_commit(tmp_path: Path) -> None:
    user = _write_state(tmp_path)

    assert cancel_generation(tmp_path, "learner", "gen-current") is True
    with pytest.raises(GenerationStaleError):
        commit_plan_generation(
            tmp_path, "learner", "gen-current",
            plan_markdown="# AI前端 新计划\n", curriculum=_curriculum(),
        )

    state = json.loads((user / "learning-state.json").read_text(encoding="utf-8"))
    assert state["generation_status"] == "cancelled"
    assert state["generation_id"] is None


def test_starting_a_new_generation_supersedes_the_previous_lease(tmp_path: Path) -> None:
    user = _write_state(tmp_path)

    new_generation = begin_generation_lease(tmp_path, "learner")

    assert new_generation != "gen-current"
    state = json.loads((user / "learning-state.json").read_text(encoding="utf-8"))
    assert state["generation_id"] == new_generation
    assert state["generation_status"] == "active"
    with pytest.raises(GenerationStaleError):
        validate_generation_lease(tmp_path, "learner", "gen-current")


def test_successful_plan_commit_updates_all_project_files_together(tmp_path: Path) -> None:
    user = _write_state(tmp_path)

    result = commit_plan_generation(
        tmp_path, "learner", "gen-current",
        plan_markdown="# AI前端 新计划\n", curriculum=_curriculum(),
    )

    state = json.loads((user / "learning-state.json").read_text(encoding="utf-8"))
    curriculum = json.loads((user / "curriculum.json").read_text(encoding="utf-8"))
    assert result["plan_status"] == "awaiting_confirmation"
    assert state["generation_id"] is None
    assert state["generation_status"] == "completed"
    assert state["plan_status"] == "awaiting_confirmation"
    assert state["active_topic"] == curriculum["topic"] == "AI前端"
    assert (user / state["active_plan"]).read_text(encoding="utf-8") == "# AI前端 新计划\n"


def test_project_guard_detects_topic_revision_or_knowledge_point_change(tmp_path: Path) -> None:
    user = _write_state(tmp_path)
    (user / "curriculum.json").write_text(
        json.dumps(_curriculum().model_dump(mode="json"), ensure_ascii=False), encoding="utf-8",
    )
    guard = project_guard(tmp_path, "learner")

    validate_project_guard(tmp_path, "learner", guard)
    state = json.loads((user / "learning-state.json").read_text(encoding="utf-8"))
    state["revision"] += 1
    (user / "learning-state.json").write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(GenerationStaleError):
        validate_project_guard(tmp_path, "learner", guard)
