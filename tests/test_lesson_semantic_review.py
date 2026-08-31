import json

import pytest

from backend.curriculum import Chapter, Curriculum, KnowledgePoint
from backend.lesson_generator import generate_and_save_lesson


def curriculum():
    point = KnowledgePoint(id="terminal", title="命令行 / 终端", outcome="能打开终端并切换到项目目录", practice="切换目录", mastery_criteria="解释当前所在目录")
    return Curriculum(topic="Vue", route="concept_clarity", level="zero", current_knowledge_point_id="terminal", chapters=[Chapter(id="chapter-1", title="准备环境", knowledge_points=[point])])


def payload():
    return {"title": "开始动手", "language": "javascript", "completion_mode": "self_practice", "pages": [
        {"id": "intro", "type": "explain", "title": "一个输入命令的窗口", "markdown": "命令行也叫终端。在 macOS 打开 Terminal，Windows 打开 PowerShell。输入 pwd 查看当前目录，再输入 cd 项目目录进入它，用 pwd 确认路径已改变。"},
        {"id": "homework", "type": "practice", "practice_kind": "homework", "title": "动手", "markdown": "进入你建立的项目目录，解释为什么要先切换位置。"},
        {"id": "end", "type": "mastery", "title": "总结", "markdown": "你现在能够定位项目目录。"},
    ], "answer_keys": {}}


def verdict(status="covered", reason="正文说明打开方式、查看目录及切换目录的步骤。", page_ids=None):
    return json.dumps({"coverage": [{"knowledge_point_id": "terminal", "status": status, "reason": reason, "page_ids": ["intro"] if page_ids is None else page_ids}]}, ensure_ascii=False)


@pytest.mark.parametrize("omit_title_terms", [False, True])
def test_semantic_review_accepts_synonyms_and_one_page_without_title_matching(tmp_path, omit_title_terms):
    calls = []
    lesson = payload()
    if omit_title_terms:
        lesson["pages"][0]["markdown"] = "在 macOS 打开 Terminal，Windows 打开 PowerShell。输入 pwd 查看当前目录，再输入 cd 项目目录进入它，用 pwd 确认路径已改变。"
        assert "命令行" not in lesson["pages"][0]["markdown"] and "终端" not in lesson["pages"][0]["markdown"]
    responses = iter([json.dumps(lesson, ensure_ascii=False), verdict()])
    def model(prompt):
        calls.append(prompt)
        return next(responses)
    bundle = generate_and_save_lesson(tmp_path, "review", curriculum=curriculum(), profile="零基础", recent_evidence=[], session_minutes=25, model_call=model)
    assert bundle.manifest.pages[0].markdown == lesson["pages"][0]["markdown"]
    assert len(calls) == 2
    assert "lesson_semantic_review" in calls[1]
    assert "切换到项目目录" in calls[1] and "零基础" in calls[1]
    assert "词面检查" not in calls[0] and "覆盖词组" not in calls[0]


@pytest.mark.parametrize("status,exception_name", [("missing", "LessonCoverageError"), ("uncertain", "LessonReviewUnavailable")])
def test_semantic_failure_does_not_regenerate_or_save(tmp_path, status, exception_name):
    calls = []
    responses = iter([json.dumps(payload()), verdict(status, "尚未说明如何切换目录", [])])
    def model(prompt):
        calls.append(prompt)
        return next(responses)
    try:
        generate_and_save_lesson(tmp_path, "review", curriculum=curriculum(), profile="零基础", recent_evidence=[], session_minutes=25, model_call=model)
    except Exception as error:
        assert type(error).__name__ == exception_name
    else:
        pytest.fail("unreviewed or incomplete lesson was saved")
    assert len(calls) == 2
    assert not (tmp_path / "userdir/u_review/lessons").exists()


@pytest.mark.parametrize("raw", ["not json", '{"coverage":[]}', verdict(page_ids=["invented"]), verdict(page_ids=[]), verdict(status="yes"), verdict(reason=""), '{"coverage":null}'])
def test_malformed_review_is_not_reported_as_structure_error_or_accepted(tmp_path, raw):
    from backend.lesson_review import LessonReviewUnavailable, review_lesson
    from backend.lesson_generator import parse_lesson_response
    bundle = parse_lesson_response(json.dumps(payload()), topic="Vue", route="foundation_engineer", knowledge_point_id="terminal", session_minutes=25)
    with pytest.raises(LessonReviewUnavailable):
        review_lesson(bundle, curriculum(), profile="零基础", model_call=lambda _: raw)


def test_review_timeout_does_not_call_generation_again(tmp_path):
    calls = []
    def model(prompt):
        calls.append(prompt)
        if len(calls) == 1:
            return json.dumps(payload())
        raise TimeoutError("simulated timeout")
    with pytest.raises(Exception) as error:
        generate_and_save_lesson(tmp_path, "review", curriculum=curriculum(), profile="零基础", recent_evidence=[], session_minutes=25, model_call=model)
    assert type(error.value).__name__ == "LessonReviewUnavailable"
    assert len(calls) == 2


def test_review_context_ignores_old_profile_and_never_loads_generation_skills(tmp_path):
    from backend.generation_context import prepare_generation_context
    (tmp_path / "profile.md").write_text("OLD_UNRELATED_COURSE")
    prompt = prepare_generation_context(tmp_path, tmp_path, "lesson_review", "CURRENT_REVIEW", False)
    assert "CURRENT_REVIEW" in prompt and "不调用工具" in prompt
    assert "OLD_UNRELATED_COURSE" not in prompt


def test_generator_receives_the_same_full_learning_targets_as_the_reviewer():
    from backend.lesson_generator import build_lesson_prompt
    course = curriculum()
    course.chapters[0].knowledge_points.append(KnowledgePoint(id="server", title="本地服务",
        outcome="解释只在当前电脑可访问的预览服务", practice="打开预览地址", mastery_criteria="能停止并再次启动预览"))
    prompt = build_lesson_prompt(course, profile="零基础", recent_evidence=[], session_minutes=25)
    assert "解释只在当前电脑可访问的预览服务" in prompt
    assert "能停止并再次启动预览" in prompt
