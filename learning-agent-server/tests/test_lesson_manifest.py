from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import main
from backend.curriculum import curriculum_from_plan, save_curriculum
from backend.lesson_generator import parse_lesson_response, save_lesson_bundle
from backend.lesson_manifest import (
    LessonManifest,
    LessonPage,
    LessonProgress,
    build_starter_lesson,
    ensure_practice_workspace,
    resolve_practice_folder,
)
from backend.knowledge_library import save_completed_chapter
from tests.test_curriculum import GO_PLAN
from tests.test_lesson_generator import model_lesson_json


def test_starter_lesson_has_teaching_practice_and_mastery_pages() -> None:
    bundle = build_starter_lesson(
        topic="Go",
        language="go",
        session_minutes=25,
        goal_route="foundation_engineer",
    )

    page_types = [page.type for page in bundle.manifest.pages]
    assert page_types == ["explain", "example", "check", "practice", "mastery"]
    assert bundle.manifest.progress.total_pages == len(bundle.manifest.pages)
    assert bundle.manifest.practice_path == "projects/go-first-steps/lesson-01"


def test_fastapi_topic_starts_with_a_real_api_lesson_instead_of_generic_variables() -> None:
    bundle = build_starter_lesson(
        topic="FastAPI 发 API",
        language="custom",
        session_minutes=25,
        goal_route="project_delivery",
    )

    text = "\n".join(
        [page.title + " " + page.markdown + " " + page.code for page in bundle.manifest.pages]
    )
    assert bundle.manifest.language == "python"
    assert "@app.get" in text
    assert "请求" in text and "响应" in text
    assert "变量像贴了标签的盒子" not in text


def test_public_manifest_never_exposes_answer_keys() -> None:
    bundle = build_starter_lesson(
        topic="Go",
        language="go",
        session_minutes=25,
        goal_route="foundation_engineer",
    )

    public = bundle.public_manifest()
    serialized = str(public).casefold()
    assert "correct_option" not in serialized
    assert "answer_key" not in serialized
    assert bundle.answer_keys


def test_practice_workspace_is_confined_to_user_directory(tmp_path: Path) -> None:
    bundle = build_starter_lesson(
        topic="Go",
        language="go",
        session_minutes=25,
        goal_route="project_delivery",
    )

    created = ensure_practice_workspace(tmp_path, "learner", bundle.manifest)

    user_dir = (tmp_path / "userdir/u_learner").resolve()
    assert created.resolve().is_relative_to(user_dir)
    assert (created / "README.md").is_file()
    assert (created / "main.go").is_file()


def test_practice_workspace_uses_model_lesson_code_for_java(tmp_path: Path) -> None:
    manifest = LessonManifest(
        lesson_id="java-class-lesson",
        title="Java · class 与 main",
        topic="Java",
        language="java",
        route="foundation_engineer",
        knowledge_point_id="class-main",
        practice_path="projects/java-course/class-main",
        completion_prompt="运行 Main.java，并贴出输出。",
        pages=[
            LessonPage(id="explain", type="explain", title="程序入口", markdown="先建立直觉。"),
            LessonPage(
                id="example", type="example", title="最小程序", language="java",
                code='public class Main { public static void main(String[] args) { System.out.println("你好"); } }',
            ),
            LessonPage(id="mastery", type="mastery", title="提交结果", markdown="贴出运行证据。"),
        ],
        progress=LessonProgress(total_pages=3, remaining_minutes=25),
    )

    created = ensure_practice_workspace(tmp_path, "java-learner", manifest)

    assert (created / "Main.java").read_text(encoding="utf-8").startswith("public class Main")
    assert "运行 Main.java" in (created / "README.md").read_text(encoding="utf-8")


def test_practice_folder_resolver_accepts_only_existing_learner_folder(tmp_path: Path) -> None:
    target = tmp_path / "userdir/u_learner/projects/api/lesson-01"
    target.mkdir(parents=True)

    assert resolve_practice_folder(tmp_path, "learner", "projects/api/lesson-01") == target.resolve()

    with pytest.raises(ValueError, match="inside"):
        resolve_practice_folder(tmp_path, "learner", "../u_other/secrets")
    with pytest.raises(FileNotFoundError):
        resolve_practice_folder(tmp_path, "learner", "projects/missing")


def test_practice_open_api_uses_safe_resolved_folder(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    client = TestClient(main.app)
    practice_path = "projects/go-course/package-main"
    (tmp_path / "userdir/u_folder-user" / practice_path).mkdir(parents=True)
    opened: list[list[str]] = []
    monkeypatch.setattr(main.subprocess, "run", lambda args, check: opened.append(args))

    response = client.post(
        "/api/practice/open",
        json={"user_id": "folder-user", "path": practice_path},
    )

    expected = (tmp_path / "userdir/u_folder-user" / practice_path).resolve()
    assert response.status_code == 200
    assert response.json() == {"opened": True, "path": practice_path}
    assert opened == [["open", str(expected)]]


def test_practice_open_api_rejects_traversal_without_opening(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    opened: list[list[str]] = []
    monkeypatch.setattr(main.subprocess, "run", lambda args, check: opened.append(args))

    response = TestClient(main.app).post(
        "/api/practice/open",
        json={"user_id": "folder-user", "path": "../u_other/secrets"},
    )

    assert response.status_code == 422
    assert opened == []


def test_lesson_api_requires_confirmed_profile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    response = TestClient(main.app).get("/api/lesson/current?user_id=new-user")

    assert response.status_code == 409
    assert response.json()["detail"]["recovery"] == "complete_onboarding"


def test_current_lesson_requests_model_generation_when_manifest_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    client = TestClient(main.app)
    confirmed = client.post(
        "/api/onboarding/confirm",
        json={
            "user_id": "go-learner",
            "learning_mode": "systematic",
            "goal_route": "foundation_engineer",
            "level_claim": "zero",
            "topic": {"type": "go", "value": "Go"},
            "session_minutes": 25,
        },
    )
    assert confirmed.status_code == 200

    curriculum = curriculum_from_plan(
        GO_PLAN, topic="Go", route="foundation_engineer", level="zero",
    )
    save_curriculum(tmp_path, "go-learner", curriculum)
    client.post("/api/plans/confirm", json={"user_id": "go-learner"})

    response = client.get("/api/lesson/current?user_id=go-learner")

    assert response.status_code == 409
    assert response.json()["detail"]["recovery"] == "generate_lesson"


def test_generate_lesson_reuses_a_verified_chapter_without_calling_the_model(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    client = TestClient(main.app)
    client.post(
        "/api/onboarding/confirm",
        json={
            "user_id": "cached-go", "learning_mode": "systematic", "goal_route": "foundation_engineer",
            "level_claim": "zero", "topic": {"type": "go", "value": "Go"}, "session_minutes": 25,
        },
    )
    curriculum = curriculum_from_plan(GO_PLAN, topic="Go", route="foundation_engineer", level="zero")
    save_curriculum(tmp_path, "cached-go", curriculum)
    bundle = parse_lesson_response(
        model_lesson_json(curriculum.current_knowledge_point_id), topic="Go", route="foundation_engineer",
        knowledge_point_id=curriculum.current_knowledge_point_id, session_minutes=25,
        chapter=curriculum.current_chapter(),
    )
    save_completed_chapter(tmp_path, curriculum, bundle)
    monkeypatch.setattr(main, "latest_release", lambda: None)

    response = client.post("/api/lesson/generate", json={"user_id": "cached-go"})

    assert response.status_code == 200
    assert response.json()["covered_knowledge_point_ids"] == [point.id for point in curriculum.current_chapter().knowledge_points]


def test_output_completion_does_not_require_a_model_release(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    client = TestClient(main.app)
    client.post(
        "/api/onboarding/confirm",
        json={
            "user_id": "offline-output", "learning_mode": "systematic", "goal_route": "foundation_engineer",
            "level_claim": "zero", "topic": {"type": "go", "value": "Go"}, "session_minutes": 25,
        },
    )
    curriculum = curriculum_from_plan(GO_PLAN, topic="Go", route="foundation_engineer", level="zero")
    save_curriculum(tmp_path, "offline-output", curriculum)
    bundle = parse_lesson_response(
        model_lesson_json(curriculum.current_knowledge_point_id), topic="Go", route="foundation_engineer",
        knowledge_point_id=curriculum.current_knowledge_point_id, session_minutes=25,
        chapter=curriculum.current_chapter(),
    )
    save_lesson_bundle(tmp_path, "offline-output", bundle)
    monkeypatch.setattr(main, "latest_release", lambda: None)

    response = client.post(
        "/api/lesson/complete",
        json={"user_id": "offline-output", "lesson_id": bundle.manifest.lesson_id, "action": "submit", "output_values": {"legacy-output": "ok"}, "quiz_attempts": [{"page_id": "check", "correct": True}]},
    )

    assert response.status_code == 200
    assert response.json()["verdict"] == "advance"


def test_generate_lesson_api_persists_model_manifest_and_grades_saved_answers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    client = TestClient(main.app)
    client.post(
        "/api/onboarding/confirm",
        json={
            "user_id": "go-learner", "learning_mode": "systematic",
            "goal_route": "foundation_engineer", "level_claim": "zero",
            "topic": {"type": "go", "value": "Go"}, "session_minutes": 25,
        },
    )
    curriculum = curriculum_from_plan(
        GO_PLAN, topic="Go", route="foundation_engineer", level="zero",
    )
    save_curriculum(tmp_path, "go-learner", curriculum)
    client.post("/api/plans/confirm", json={"user_id": "go-learner"})
    monkeypatch.setattr(main, "latest_release", lambda: Path("/tmp/codex-release"))
    captured: dict[str, str] = {}

    def fake_chat(user_id: str, prompt: str, release: Path) -> str:
        captured["prompt"] = prompt
        return model_lesson_json(curriculum.current_knowledge_point_id)

    monkeypatch.setattr(main, "chat", fake_chat)

    generated = client.post(
        "/api/lesson/generate",
        json={"user_id": "go-learner"},
    )

    assert generated.status_code == 200
    payload = generated.json()
    assert payload["knowledge_point_id"] == curriculum.current_knowledge_point_id
    assert curriculum.current_knowledge_point_id in captured["prompt"]
    assert payload["pages"][0]["type"] == "explain"
    assert payload["progress"]["total_pages"] == len(payload["pages"])
    assert "answer_keys" not in generated.text
    project = tmp_path / "userdir/u_go-learner" / payload["practice_path"]
    assert (project / "main.go").is_file()

    current = client.get("/api/lesson/current?user_id=go-learner")
    assert current.status_code == 200
    assert current.json() == payload

    checked = client.post(
        "/api/lesson/check",
        json={
            "user_id": "go-learner",
            "lesson_id": payload["lesson_id"],
            "page_id": "check",
            "selected_option_id": "b",
        },
    )
    assert checked.status_code == 200
    assert checked.json()["correct"] is True
    assert checked.json()["verified"] is True
    assert "程序入口" in checked.json()["feedback"] or "答对" in checked.json()["feedback"]


def test_generate_lesson_api_returns_retryable_error_without_fixed_fallback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(main, "SERVER_ROOT", tmp_path)
    client = TestClient(main.app)
    client.post(
        "/api/onboarding/confirm",
        json={
            "user_id": "java-learner", "learning_mode": "systematic",
            "goal_route": "foundation_engineer", "level_claim": "zero",
            "topic": {"type": "custom", "value": "Java"}, "session_minutes": 25,
        },
    )
    java_plan = GO_PLAN.replace("Go 学习计划", "Java 学习计划").replace(
        "package main；func main；go run 与 go build", "JDK 与 JVM；class 与 main；javac 与 java",
    )
    save_curriculum(
        tmp_path, "java-learner",
        curriculum_from_plan(java_plan, topic="Java", route="foundation_engineer", level="zero"),
    )
    monkeypatch.setattr(main, "latest_release", lambda: Path("/tmp/codex-release"))
    monkeypatch.setattr(main, "chat", lambda *_: model_lesson_json("jdk-jvm"))

    response = client.post("/api/lesson/generate", json={"user_id": "java-learner"})

    assert response.status_code == 502
    assert response.json()["detail"]["retryable"] is True
    assert response.json()["detail"]["error_stage"] == "lesson_generation"
    assert response.json()["detail"]["error_type"] == "validation"
    assert "未通过结构检查" in response.json()["detail"]["message"]
    assert not list((tmp_path / "userdir/u_java-learner/lessons").glob("*.json"))
