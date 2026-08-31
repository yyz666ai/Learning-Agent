"""Regression coverage for the generation boundary, not cached lesson loading."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from backend.curriculum import Chapter, Curriculum, KnowledgePoint, curriculum_from_plan
from backend.lesson_generator import generate_and_save_lesson
from backend.lesson_review import LessonCoverageError, LessonReviewUnavailable
from tests.semantic_review_fixtures import review_response


def coverage_curriculum() -> Curriculum:
    titles = [
        ("http-handler", "快进确认已掌握区（HTTP handler 实现、表驱动单元测试）"),
        ("cancellation", "定位并发取消缺口的具体表现，把「并发取消与资源泄漏排查」拆成可练习的症状"),
    ]
    points = [KnowledgePoint(id=key, title=title, outcome=title, practice="观察并练习", mastery_criteria="完成检查") for key, title in titles]
    return Curriculum(topic="Go", route="concept_clarity", level="experienced", current_knowledge_point_id="http-handler", chapters=[Chapter(id="chapter-1", title="定标", knowledge_points=points)])


def coverage_payload() -> dict:
    return {
        "title": "迁移练习", "language": "go", "practice_path": "projects/go/calibration",
        "completion_mode": "self_practice",
        "pages": [
            {"id": "handler", "type": "explain", "title": "响应请求", "markdown": "HTTP handler 将请求交给处理函数，由 ResponseWriter 写响应。"},
            {"id": "tests", "type": "check", "title": "检查处理结果", "markdown": "表驱动单元测试把输入和期望输出存成用例表，循环检查状态码。", "question": "应该核对什么？", "options": [{"id": "a", "label": "状态码和响应体"}, {"id": "b", "label": "随机值"}]},
            {"id": "cancel", "type": "explain", "title": "请求结束之后", "markdown": "并发取消需要传播请求的 Context，否则后台 goroutine 仍然运行。"},
            {"id": "leak", "type": "explain", "title": "找出只进不出的资源", "markdown": "资源泄漏排查先观察阻塞发送，再核对响应体是否 Close。"},
            {"id": "practice", "type": "practice", "title": "独立练习", "markdown": "复现取消后 goroutine 仍运行的现象。"},
            {"id": "mastery", "type": "mastery", "title": "结束", "markdown": "完成选择题。"},
        ],
        "answer_keys": {"tests": "a"},
        "scope_evidence": [
            {"knowledge_point_id": "http-handler", "page_ids": ["handler", "tests"]},
            {"knowledge_point_id": "cancellation", "page_ids": ["cancel", "leak"]},
        ],
    }


@pytest.mark.parametrize("broken_structure", [False, True])
@pytest.mark.parametrize("status", ["covered", "missing", "uncertain"])
def test_review_happens_once_after_structure_repair_without_rewriting_on_rejection(tmp_path, broken_structure, status):
    payload = coverage_payload()
    broken = copy.deepcopy(payload)
    broken["answer_keys"] = {}
    generation = []
    reviews = []
    def generate(prompt):
        generation.append(prompt)
        return json.dumps(broken if broken_structure and len(generation) == 1 else payload)
    def review(prompt):
        reviews.append(prompt)
        raw = json.loads(review_response(prompt, missing=status == "missing"))
        for item in raw["coverage"]:
            item["status"] = status
        return json.dumps(raw)
    kwargs = dict(curriculum=coverage_curriculum(), profile="已有基础", recent_evidence=[], session_minutes=25,
                  model_call=generate, review_call=review)
    if status == "covered":
        bundle = generate_and_save_lesson(tmp_path, "coverage", **kwargs)
        assert bundle.manifest.covered_knowledge_point_ids == ["http-handler", "cancellation"]
    else:
        with pytest.raises(LessonCoverageError if status == "missing" else LessonReviewUnavailable):
            generate_and_save_lesson(tmp_path, "coverage", **kwargs)
        assert not (tmp_path / "userdir/u_coverage/lessons").exists()
    assert len(generation) == (2 if broken_structure else 1)
    assert len(reviews) == 1


@pytest.mark.parametrize("bad_report", ["duplicate", "missing_point", "unknown_point", "duplicate_page", "blank_reason"])
def test_review_protocol_cannot_fake_complete_coverage(tmp_path, bad_report):
    def review(prompt):
        raw = json.loads(review_response(prompt))
        items = raw["coverage"]
        if bad_report == "duplicate":
            items.append(items[0])
        elif bad_report == "missing_point":
            items.pop()
        elif bad_report == "unknown_point":
            items[0]["knowledge_point_id"] = "invented"
        elif bad_report == "duplicate_page":
            items[0]["page_ids"] *= 2
        else:
            items[0]["reason"] = "  "
        return json.dumps(raw)
    with pytest.raises(LessonReviewUnavailable):
        generate_and_save_lesson(tmp_path, "coverage", curriculum=coverage_curriculum(), profile="已有基础",
            recent_evidence=[], session_minutes=25, model_call=lambda _: json.dumps(coverage_payload()), review_call=review)
    assert not (tmp_path / "userdir/u_coverage/lessons").exists()


def test_failed_review_preserves_preexisting_saved_lesson(tmp_path):
    kwargs = dict(curriculum=coverage_curriculum(), profile="已有基础", recent_evidence=[], session_minutes=25,
                  model_call=lambda _: json.dumps(coverage_payload()))
    generate_and_save_lesson(tmp_path, "coverage", review_call=review_response, **kwargs)
    directory = tmp_path / "userdir/u_coverage/lessons"
    before = {str(path): path.read_bytes() for path in directory.rglob("*") if path.is_file()}
    with pytest.raises(LessonCoverageError):
        generate_and_save_lesson(tmp_path, "coverage", review_call=lambda prompt: review_response(prompt, missing=True), **kwargs)
    assert before == {str(path): path.read_bytes() for path in directory.rglob("*") if path.is_file()}
