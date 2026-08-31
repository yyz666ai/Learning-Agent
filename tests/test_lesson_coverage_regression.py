"""Regression coverage for the generation boundary, not cached lesson loading."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from backend.curriculum import Chapter, Curriculum, KnowledgePoint, curriculum_from_plan
from backend.lesson_generator import _scope_concepts, _validate_scope_evidence, generate_and_save_lesson, parse_lesson_response


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


def test_repair_gets_all_missing_scope_obligations_in_one_pass():
    curriculum = coverage_curriculum()
    payload = coverage_payload()
    for page in payload["pages"]:
        page["markdown"] = "无关内容，不能作为本章证据。"
    bundle = parse_lesson_response(json.dumps(payload), topic="Go", route="concept_clarity",
        knowledge_point_id="http-handler", session_minutes=30,
        chapter=curriculum.current_chapter(), covered_knowledge_points=curriculum.knowledge_points())
    with pytest.raises(ValueError) as error:
        _validate_scope_evidence(payload, bundle, curriculum.knowledge_points())
    assert "http-handler" in str(error.value)
    assert "cancellation" in str(error.value)


@pytest.mark.parametrize("title", ["Go 并发（进阶）", "Context 取消信号与「资源泄漏」排查", "并发（channel、goroutine）取消", "Context 取消与资源泄漏（channel、goroutine）"])
def test_incidental_parentheses_and_quotes_do_not_discard_outer_concepts(title: str) -> None:
    concepts = _scope_concepts(title)
    # Technical label and descriptor can now be separate literal obligations;
    # the outer topic must still survive extraction (not just the parentheses).
    assert ("Go" in concepts and "并发" in concepts) or any("取消" in concept for concept in concepts)


def generate(tmp_path: Path, payload: dict, *, repaired: bool = False, curriculum: Curriculum | None = None):
    responses = []
    if repaired:
        broken = copy.deepcopy(payload)
        broken["answer_keys"] = {}
        responses.append(json.dumps(broken, ensure_ascii=False))
    responses.extend([json.dumps(payload, ensure_ascii=False)] * 2)
    iterator = iter(responses)
    return generate_and_save_lesson(tmp_path, "coverage", curriculum=curriculum or coverage_curriculum(), profile="学习者画像", recent_evidence=[], session_minutes=30, model_call=lambda _: next(iterator))


@pytest.mark.parametrize("repaired", [False, True])
def test_python_interview_audit_fragments_keep_topics_not_instructional_wrappers(tmp_path: Path, repaired: bool) -> None:
    """Portable excerpts of call-4/5; this tests scope, not their factual quality."""
    titles = [
        ("python-python-org", "确认系统与 Python 版本（官方来源 python.org）、练习目录结构、编辑器打开方式"),
        ("chapter-1-point-2", "附带一个面试点「解释器与脚本」"),
    ]
    points = [KnowledgePoint(id=key, title=title, outcome=title, practice="检查并运行", mastery_criteria="完成检查") for key, title in titles]
    curriculum = Curriculum(topic="Python", route="concept_clarity", level="zero", current_knowledge_point_id=points[0].id, chapters=[Chapter(id="chapter-1", title="准备环境", knowledge_points=points)])
    payload = coverage_payload()
    payload["language"] = "python"
    payload["pages"][0].update(id="environment", markdown="第一件事是确认系统。确认 Python 版本（官方来源 python.org）的方法很简单：在终端运行一条验证命令。本课程的练习目录结构是：demos/python/01_first_run/。编辑器打开方式：打开编辑器 → 文件（File）→ 打开文件夹（Open Folder）。")
    payload["pages"][1]["markdown"] = "main.py 是脚本文件，python3 是解释器；python3 main.py 就是让解释器执行这个脚本。"
    payload["pages"][2].update(id="version", markdown="python3 --version（Windows 用 python --version）显示 3.10 或更高。")
    payload["pages"][3].update(id="directory", markdown="改好的 main.py 仍然留在练习目录 demos/python/01_first_run/ 里。")
    payload["pages"][-1]["markdown"] = "解释器是什么？脚本是什么？运行 python3 main.py 时发生了什么？"
    payload["scope_evidence"] = [
        {"knowledge_point_id": points[0].id, "page_ids": ["environment", "version", "directory"]},
        {"knowledge_point_id": points[1].id, "page_ids": ["tests", "mastery"]},
    ]
    assert generate(tmp_path, payload, repaired=repaired, curriculum=curriculum).manifest.covered_knowledge_point_ids == [point.id for point in points]


def test_source_annotation_and_interview_wrapper_keep_substantive_requirements() -> None:
    assert _scope_concepts("附带一个面试点「解释器与脚本」") == ["解释器", "脚本"]
    assert _scope_concepts("确认系统与 Python 版本（官方来源 python.org）、练习目录结构、编辑器打开方式") == ["确认系统", "Python", "版本", "python.org", "练习目录结构", "编辑器打开方式"]


def test_bare_knowledge_id_that_is_real_terminology_is_not_deleted(tmp_path: Path) -> None:
    """Portable beginner replay: go is both the point ID and the real command."""
    curriculum = coverage_curriculum()
    point = curriculum.chapters[0].knowledge_points[0]
    point.id = "go"
    point.title = "编译型语言与工具链心智：源代码 → `go` 命令编译 → 可执行文件 → 运行"
    curriculum.current_knowledge_point_id = "go"
    payload = coverage_payload()
    payload["pages"][0]["markdown"] = "Go 是编译型语言——源代码要先编译成可执行文件，电脑才能运行它。"
    payload["pages"][1]["markdown"] = "工具链心智：源代码 → `go` 命令编译 → 可执行文件 → 运行。"
    payload["scope_evidence"][0]["knowledge_point_id"] = "go"
    assert generate(tmp_path, payload, curriculum=curriculum).manifest.knowledge_point_id == "go"


def test_question_titles_and_surplus_citation_replay(tmp_path: Path) -> None:
    """Portable advanced excerpts: substantive supporting pages plus an extra quiz."""
    curriculum = coverage_curriculum()
    first, second = curriculum.chapters[0].knowledge_points
    first.title = "请求上下文是什么"
    second.title = "客户端断开时取消信号如何自动产生"
    payload = coverage_payload()
    payload["pages"][0]["markdown"] = "请求上下文是什么。请求上下文是每个 HTTP 请求自带的随身背包。"
    payload["pages"][1]["markdown"] = "客户端断开 → 自动取消请求上下文 → 信号沿着上下文传下去。"
    payload["pages"][2]["markdown"] = "客户端断开时取消信号如何自动产生？net/http 会自动关闭 r.Context() 的 Done()。"
    payload["pages"][3]["markdown"] = "用一道题确认：取消信号什么时候自动产生。"
    payload["scope_evidence"][0]["page_ids"].append("practice")
    assert generate(tmp_path, payload, curriculum=curriculum).manifest.covered_knowledge_point_ids == [first.id, second.id]


@pytest.mark.parametrize("failure", ["unknown_extra", "fake_extra_excerpt", "missing_concept_in_retained_pages"])
def test_surplus_citations_cannot_hide_invalid_or_missing_evidence(tmp_path: Path, failure: str) -> None:
    payload = coverage_payload()
    payload["scope_evidence"][0]["page_ids"].append("practice")
    if failure == "unknown_extra":
        payload["scope_evidence"][0]["page_ids"].append("invented")
    elif failure == "fake_extra_excerpt":
        payload["scope_evidence"][0]["excerpts"] = [{"page_id": "practice", "quote": "这里有完整的 HTTP handler 实现"}]
    else:
        payload["pages"][1]["markdown"] = "HTTP handler 将请求交给处理函数。"
    with pytest.raises(ValueError, match="scope evidence|drifted"):
        generate(tmp_path, payload)


@pytest.mark.parametrize("repaired", [False, True])
def test_valid_compound_title_paraphrase_is_accepted(tmp_path: Path, repaired: bool) -> None:
    bundle = generate(tmp_path, coverage_payload(), repaired=repaired)
    assert bundle.manifest.covered_knowledge_point_ids == ["http-handler", "cancellation"]


@pytest.mark.parametrize("repaired", [False, True])
@pytest.mark.parametrize("failure", ["missing", "missing_point", "unknown_page", "duplicate_page", "duplicate_point", "unrelated", "missing_concept", "fake_quote", "title_only", "cross_page_phrase", "unrelated_second_page", "id_only_second_page"])
def test_invalid_scope_never_persists(tmp_path: Path, repaired: bool, failure: str) -> None:
    payload = coverage_payload()
    evidence = payload["scope_evidence"]
    if failure == "missing":
        payload.pop("scope_evidence")
    elif failure == "missing_point":
        evidence.pop()
    elif failure == "unknown_page":
        evidence[0]["page_ids"] = ["handler", "invented"]
    elif failure == "duplicate_page":
        evidence[0]["page_ids"] = ["handler", "handler"]
    elif failure == "duplicate_point":
        evidence.append(copy.deepcopy(evidence[0]))
    elif failure == "unrelated":
        evidence[1]["page_ids"] = ["handler", "tests"]
    elif failure == "missing_concept":
        payload["pages"][1]["markdown"] = "HTTP handler 将请求交给处理函数。"
    elif failure == "fake_quote":
        evidence[1]["excerpts"] = [{"page_id": "cancel", "quote": "这里逐行证明了资源泄漏排查的正确性。"}]
    elif failure == "title_only":
        payload["pages"][2]["title"] = coverage_curriculum().knowledge_points()[1].title
        payload["pages"][2]["markdown"] = "今天学习 HTTP handler。"
        payload["pages"][3]["markdown"] = "今天继续处理 HTTP 请求。"
    elif failure == "cross_page_phrase":
        payload["pages"][2]["markdown"] = "并发取消需要处理。资源泄漏"
        payload["pages"][3]["markdown"] = "排查 HTTP handler 的请求路径。"
    elif failure in {"unrelated_second_page", "id_only_second_page"}:
        payload["pages"][2]["markdown"] += "资源泄漏排查也需要检查。"
        payload["pages"][3]["markdown"] = "本页讨论 SQL 索引和查询计划。"
        if failure == "id_only_second_page":
            payload["pages"][3]["markdown"] += "知识点 cancellation。"
        evidence[1]["excerpts"] = [{"page_id": "leak", "quote": payload["pages"][3]["markdown"]}]
    with pytest.raises(ValueError, match="scope evidence|drifted"):
        generate(tmp_path, payload, repaired=repaired)
    assert not (tmp_path / "userdir/u_coverage/lessons/http-handler.json").exists()


def test_exact_title_legacy_evidence_still_accepted(tmp_path: Path) -> None:
    payload = coverage_payload()
    for point, page in zip(coverage_curriculum().knowledge_points(), [payload["pages"][0], payload["pages"][2]]):
        page["markdown"] += "\n" + point.title
    assert generate(tmp_path, payload, repaired=True).manifest.knowledge_point_id == "http-handler"


def test_grounded_quote_evidence_is_accepted(tmp_path: Path) -> None:
    payload = coverage_payload()
    payload["scope_evidence"][1]["excerpts"] = [{"page_id": "cancel", "quote": payload["pages"][2]["markdown"]}]
    assert generate(tmp_path, payload).manifest.knowledge_point_id == "http-handler"


def test_audited_advanced_response_reparses_without_rewriting_its_content(tmp_path: Path) -> None:
    audit = Path(__file__).resolve().parents[1] / "evals/runs/2026-08-30-lesson-audit/lesson_audit_advanced"
    if not (audit / "journey.json").is_file():
        pytest.skip("local real-model audit artifact is not part of the portable test suite")
    journey = json.loads((audit / "journey.json").read_text())
    plan = next(stage["result"]["plan_markdown"] for stage in journey["stages"] if stage["stage"] == "plan")
    curriculum = curriculum_from_plan(plan, topic="Go", route="gap_upgrade", level="experienced")
    responses = [json.loads((audit / f"call-{index}.json").read_text())["output"] for index in (2, 3)]
    iterator = iter(responses)
    calls = []

    def model(prompt: str) -> str:
        calls.append(prompt)
        return next(iterator)

    bundle = generate_and_save_lesson(tmp_path, "audited", curriculum=curriculum, profile="已有基础", recent_evidence=[], session_minutes=45, model_call=model, persist=False)
    assert len(calls) == 2  # The genuinely long first code block still needs repair.
    assert bundle.manifest.covered_knowledge_point_ids == ["http-handler", "chapter-1-point-2"]
    assert len(bundle.manifest.pages) == 15
