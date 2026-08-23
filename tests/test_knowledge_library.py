from __future__ import annotations

from backend.curriculum import curriculum_from_plan
from backend.knowledge_library import load_completed_chapter, save_completed_chapter
from backend.lesson_generator import parse_lesson_response
from tests.test_curriculum import GO_PLAN
from tests.test_lesson_generator import model_lesson_json


def test_verified_completed_chapter_is_saved_as_reusable_knowledge_assets(tmp_path) -> None:
    curriculum = curriculum_from_plan(GO_PLAN, topic="Go", route="foundation_engineer", level="zero")
    chapter = curriculum.current_chapter()
    bundle = parse_lesson_response(
        model_lesson_json(curriculum.current_knowledge_point_id), topic="Go",
        route="foundation_engineer", knowledge_point_id=curriculum.current_knowledge_point_id,
        session_minutes=25, chapter=chapter,
    )

    saved = save_completed_chapter(tmp_path, curriculum, bundle)
    loaded = load_completed_chapter(tmp_path, curriculum)

    assert saved["atom"].is_file()
    assert saved["deck"].is_file()
    assert "程序结构与运行" in saved["atom"].read_text(encoding="utf-8")
    assert loaded is not None
    assert loaded.manifest.covered_knowledge_point_ids == [point.id for point in chapter.knowledge_points]
