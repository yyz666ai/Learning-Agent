from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend import main
from backend.curriculum import curriculum_from_plan, load_curriculum, save_curriculum
from backend.lesson_generator import parse_lesson_response, save_lesson_bundle
from backend.lesson_progression import (
    CompletionEvidence,
    apply_completion_decision,
    evaluate_completion,
)
from tests.test_curriculum import GO_PLAN
from tests.test_lesson_generator import model_lesson_json


def decision_json(verdict: str) -> str:
    return json.dumps(
        {
            "verdict": verdict,
            "feedback": {
                "advance": "运行证据和解释都达标，可以进入下一课。",
                "practice": "概念基本正确，再做一个短练习就稳了。",
                "reteach": "当前解释混淆了编译与运行，我换一种方式讲。",
            }[verdict],
            "mastery_score": {"advance": 92, "practice": 68, "reteach": 35}[verdict],
        },
        ensure_ascii=False,
    )


def _curriculum():
    return curriculum_from_plan(
        GO_PLAN, topic="Go", route="foundation_engineer", level="zero",
    )


def _completed_evidence(manifest, **kwargs):
    return CompletionEvidence(
        **kwargs,
        quiz_attempts=[
            {"page_id": page.id, "correct": True}
            for page in manifest.pages if page.question and page.options
        ],
    )


def test_evaluation_prompt_uses_criteria_quiz_attempts_and_real_evidence() -> None:
    curriculum = _curriculum()
    bundle = parse_lesson_response(
        model_lesson_json(curriculum.current_knowledge_point_id),
        topic="Go", route="foundation_engineer",
        knowledge_point_id=curriculum.current_knowledge_point_id, session_minutes=25,
    )
    captured: dict[str, str] = {}

    decision = evaluate_completion(
        curriculum,
        bundle.manifest.model_copy(update={"completion_mode": "text"}),
        CompletionEvidence(
            action="submit",
            evidence="go run main.go 输出：你好；package main 表示可执行程序入口。",
            quiz_attempts=[{"page_id": "check", "correct": True}],
        ),
        model_call=lambda prompt: captured.setdefault("prompt", prompt) and decision_json("advance"),
    )

    assert "请贴出 go run 的结果" in captured["prompt"]
    assert "check" in captured["prompt"] and "true" in captured["prompt"].lower()
    assert "package main 表示" in captured["prompt"]
    assert "不要调用任何工具" in captured["prompt"]
    assert decision.verdict == "advance"


def test_output_completion_requires_each_choice_page_to_be_passed() -> None:
    curriculum = _curriculum()
    bundle = parse_lesson_response(
        model_lesson_json(curriculum.current_knowledge_point_id),
        topic="Go", route="foundation_engineer",
        knowledge_point_id=curriculum.current_knowledge_point_id, session_minutes=25,
    )

    decision = evaluate_completion(
        curriculum,
        bundle.manifest,
        CompletionEvidence(action="submit", output_values={"legacy-output": "ok"}),
        model_call=lambda _: "should not be called",
    )

    assert decision.verdict == "practice"
    assert "确认理解" in decision.feedback


def test_choice_only_concept_completion_advances_without_model_or_output() -> None:
    curriculum = _curriculum()
    bundle = parse_lesson_response(
        model_lesson_json(curriculum.current_knowledge_point_id),
        topic="Go", route="foundation_engineer",
        knowledge_point_id=curriculum.current_knowledge_point_id, session_minutes=15,
    )
    manifest = bundle.manifest.model_copy(update={
        "completion_mode": "choice",
        "output_requirements": [],
        "output_patterns": [],
    })

    decision = evaluate_completion(
        curriculum,
        manifest,
        _completed_evidence(manifest, action="submit"),
        model_call=lambda _: (_ for _ in ()).throw(AssertionError("choice completion must not call model")),
    )

    assert decision.verdict == "advance"
    assert decision.cta_label == "完成这个概念"


def test_advance_marks_current_complete_and_activates_a_different_next_point(tmp_path: Path) -> None:
    curriculum = _curriculum()
    current_id = curriculum.current_knowledge_point_id
    first_next = curriculum.knowledge_points()[1]
    save_curriculum(tmp_path, "learner", curriculum)
    user_dir = tmp_path / "userdir/u_learner"
    (user_dir / "plans").mkdir(parents=True)
    (user_dir / "plans/go-plan.md").write_text("old plan", encoding="utf-8")
    (user_dir / "learning-state.json").write_text(
        json.dumps({"active_plan": "plans/go-plan.md", "revision": 1, "recent_evidence": []}),
        encoding="utf-8",
    )

    manifest = parse_lesson_response(
        model_lesson_json(current_id), topic="Go", route="foundation_engineer",
        knowledge_point_id=current_id, session_minutes=25,
    ).manifest.model_copy(update={"completion_mode": "text"})
    result = apply_completion_decision(
        tmp_path,
        "learner",
        curriculum,
        CompletionEvidence(action="submit", evidence="真实运行成功"),
        evaluate_completion(
            curriculum,
            manifest,
            _completed_evidence(manifest, action="submit", evidence="真实运行成功"),
            model_call=lambda _: decision_json("advance"),
        ),
    )

    saved = load_curriculum(tmp_path, "learner")
    assert saved.current_knowledge_point_id == first_next.id
    assert saved.current_knowledge_point_id != current_id
    assert saved.knowledge_points()[0].status == "completed"
    assert saved.knowledge_points()[1].status == "active"
    assert result.next_knowledge_point_id == first_next.id
    assert first_next.title in result.cta_label
    assert first_next.title in (user_dir / "plans/go-plan.md").read_text(encoding="utf-8")
    state = json.loads((user_dir / "learning-state.json").read_text(encoding="utf-8"))
    assert state["active_task"] == first_next.id
    assert all(isinstance(item, str) for item in state["recent_evidence"])


def test_practice_and_reteach_keep_the_current_knowledge_point(tmp_path: Path) -> None:
    for verdict in ("practice", "reteach"):
        curriculum = _curriculum()
        manifest = parse_lesson_response(
            model_lesson_json(curriculum.current_knowledge_point_id),
            topic="Go", route="foundation_engineer",
            knowledge_point_id=curriculum.current_knowledge_point_id, session_minutes=25,
        ).manifest.model_copy(update={"completion_mode": "text"})
        evidence = _completed_evidence(manifest, action="stuck", evidence="我分不清编译和运行")
        decision = evaluate_completion(
            curriculum,
            manifest,
            evidence,
            model_call=lambda _, value=verdict: decision_json(value),
        )
        original = curriculum.current_knowledge_point_id
        result = apply_completion_decision(tmp_path, f"learner-{verdict}", curriculum, evidence, decision)
        assert result.next_knowledge_point_id == original
        assert result.cta_label in {"做一道针对性练习", "换一种讲法", "回到练习继续修改"}


def test_finishing_the_last_point_opens_summary_instead_of_reopening_the_lesson(tmp_path: Path) -> None:
    curriculum = _curriculum()
    points = curriculum.knowledge_points()
    for point in points[:-1]:
        point.status = "completed"
    points[-1].status = "active"
    curriculum.current_knowledge_point_id = points[-1].id

    manifest = parse_lesson_response(
        model_lesson_json(points[-1].id), topic="Go", route="foundation_engineer",
        knowledge_point_id=points[-1].id, session_minutes=25,
    ).manifest
    decision = apply_completion_decision(
        tmp_path,
        "graduate",
        curriculum,
        CompletionEvidence(action="submit", evidence="最终项目和复习证据均已提交"),
        evaluate_completion(
            curriculum,
            manifest,
            _completed_evidence(manifest, action="submit", evidence="最终项目和复习证据均已提交"),
            model_call=lambda _: decision_json("advance"),
        ),
    )

    assert decision.next_knowledge_point_id is None
    assert decision.cta_label == "查看课程总结"
    assert load_curriculum(tmp_path, "graduate").knowledge_points()[-1].status == "completed"


def test_fractional_model_mastery_score_is_normalized_to_percent() -> None:
    curriculum = _curriculum()
    manifest = parse_lesson_response(
        model_lesson_json(curriculum.current_knowledge_point_id), topic="Go",
        route="foundation_engineer", knowledge_point_id=curriculum.current_knowledge_point_id,
        session_minutes=25,
        ).manifest.model_copy(update={"completion_mode": "text"})

    decision = evaluate_completion(
        curriculum, manifest, _completed_evidence(manifest, action="submit", evidence="运行成功"),
        model_call=lambda _: '{"verdict":"advance","feedback":"证据达标。","mastery_score":0.85}',
    )

    assert decision.mastery_score == 85


def test_legacy_output_completion_no_longer_uses_regex_or_calls_the_model() -> None:
    curriculum = _curriculum()
    manifest = parse_lesson_response(
        model_lesson_json(curriculum.current_knowledge_point_id), topic="Go",
        route="foundation_engineer", knowledge_point_id=curriculum.current_knowledge_point_id,
        session_minutes=25,
    ).manifest.model_copy(update={
        "completion_mode": "output",
        "output_patterns": [r"Hello,\s+."],
    })

    decision = evaluate_completion(
        curriculum, manifest,
        _completed_evidence(manifest, action="submit", evidence="Hello, 小林"),
        model_call=lambda _: (_ for _ in ()).throw(AssertionError("output check must not call model")),
    )

    assert decision.verdict == "advance"
    assert decision.cta_label == "完成课堂，进入下一章"


def test_self_practice_completion_uses_only_classroom_choices_and_never_checks_output() -> None:
    curriculum = _curriculum()
    manifest = parse_lesson_response(
        model_lesson_json(curriculum.current_knowledge_point_id), topic="Go",
        route="foundation_engineer", knowledge_point_id=curriculum.current_knowledge_point_id,
        session_minutes=25,
    ).manifest.model_copy(update={
        "completion_mode": "self_practice",
        "output_patterns": [],
        "output_requirements": [],
    })

    decision = evaluate_completion(
        curriculum, manifest,
        _completed_evidence(manifest, action="submit", evidence="panic: 这段结果也不应成为课堂门禁"),
        model_call=lambda _: (_ for _ in ()).throw(AssertionError("self practice must not call model")),
    )

    assert decision.verdict == "advance"
    assert decision.mastery_score == 70
    assert "课后练习" in decision.feedback
    assert "输入栏" in decision.feedback


def test_legacy_output_completion_does_not_block_on_a_nonmatching_result() -> None:
    curriculum = _curriculum()
    manifest = parse_lesson_response(
        model_lesson_json(curriculum.current_knowledge_point_id), topic="Go",
        route="foundation_engineer", knowledge_point_id=curriculum.current_knowledge_point_id,
        session_minutes=25,
    ).manifest.model_copy(update={
        "completion_mode": "output",
        "output_patterns": [r"Hello,\s+."],
    })

    decision = evaluate_completion(
        curriculum, manifest, _completed_evidence(manifest, action="submit", evidence="build failed"),
        model_call=lambda _: (_ for _ in ()).throw(AssertionError("output check must not call model")),
    )

    assert decision.verdict == "advance"
    assert "课后练习" in decision.feedback


def test_legacy_output_content_is_not_used_as_a_classroom_gate() -> None:
    curriculum = _curriculum()
    manifest = parse_lesson_response(
        model_lesson_json(curriculum.current_knowledge_point_id), topic="Go",
        route="foundation_engineer", knowledge_point_id=curriculum.current_knowledge_point_id,
        session_minutes=25,
    ).manifest.model_copy(update={"completion_mode": "output", "output_patterns": []})

    success = evaluate_completion(
        curriculum, manifest, _completed_evidence(manifest, action="submit", evidence="1"),
        model_call=lambda _: (_ for _ in ()).throw(AssertionError("output check must not call model")),
    )
    failure = evaluate_completion(
        curriculum, manifest, _completed_evidence(manifest, action="submit", evidence="1\npanic: boom"),
        model_call=lambda _: (_ for _ in ()).throw(AssertionError("output check must not call model")),
    )

    assert success.verdict == "advance"
    assert failure.verdict == "advance"


def test_course_specific_regex_can_accept_a_successful_output_that_mentions_error() -> None:
    curriculum = _curriculum()
    manifest = parse_lesson_response(
        model_lesson_json(curriculum.current_knowledge_point_id), topic="Go",
        route="foundation_engineer", knowledge_point_id=curriculum.current_knowledge_point_id,
        session_minutes=25,
    ).manifest.model_copy(update={"completion_mode": "output", "output_patterns": [r"error:\s+nil"]})

    decision = evaluate_completion(
        curriculum, manifest, _completed_evidence(manifest, action="submit", evidence="error: nil"),
        model_call=lambda _: (_ for _ in ()).throw(AssertionError("output check must not call model")),
    )

    assert decision.verdict == "advance"


def test_lesson_complete_api_returns_named_next_step(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    client = TestClient(main.app)
    client.post(
        "/api/onboarding/confirm",
        json={
            "user_id": "progress-user", "learning_mode": "systematic",
            "goal_route": "foundation_engineer", "level_claim": "zero",
            "topic": {"type": "go", "value": "Go"}, "session_minutes": 25,
        },
    )
    curriculum = _curriculum()
    save_curriculum(tmp_path, "progress-user", curriculum)
    bundle = parse_lesson_response(
        model_lesson_json(curriculum.current_knowledge_point_id), topic="Go",
        route="foundation_engineer", knowledge_point_id=curriculum.current_knowledge_point_id,
        session_minutes=25,
    )
    save_lesson_bundle(tmp_path, "progress-user", bundle)
    monkeypatch.setattr(main, "latest_release", lambda: Path("/tmp/codex-release"))
    monkeypatch.setattr(main, "chat", lambda *_: decision_json("advance"))

    response = client.post(
        "/api/lesson/complete",
        json={
            "user_id": "progress-user",
            "lesson_id": bundle.manifest.lesson_id,
            "action": "submit",
            "evidence": "go run main.go 成功；package main 是程序入口。",
            "quiz_attempts": [{"page_id": "check", "correct": True}],
        },
    )

    assert response.status_code == 200
    assert response.json()["verdict"] == "advance"
    assert response.json()["next_knowledge_point_id"] != curriculum.current_knowledge_point_id
    assert response.json()["cta_label"].startswith("开始下一章：")


def test_completed_chapter_advances_past_all_covered_points(tmp_path: Path) -> None:
    curriculum = _curriculum()
    chapter = curriculum.current_chapter()
    manifest = parse_lesson_response(
        model_lesson_json(curriculum.current_knowledge_point_id), topic="Go",
        route="foundation_engineer", knowledge_point_id=curriculum.current_knowledge_point_id,
        session_minutes=25, chapter=chapter,
    ).manifest
    manifest = manifest.model_copy(update={
        "completion_mode": "output",
        "output_requirements": [{"id": "run", "label": "运行输出", "instruction": "粘贴输出", "patterns": [r"成功"]}],
    })
    decision = evaluate_completion(
        curriculum, manifest,
        _completed_evidence(manifest, action="submit", output_values={"run": "成功"}),
        model_call=lambda _: (_ for _ in ()).throw(AssertionError("output check must not call model")),
    )

    applied = apply_completion_decision(tmp_path, "chapter-user", curriculum, CompletionEvidence(action="submit", output_values={"run": "成功"}), decision)

    assert all(point.status == "completed" for point in chapter.knowledge_points)
    assert applied.next_knowledge_point_id not in {point.id for point in chapter.knowledge_points}
