from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from backend.interview_bank import InterviewBankStore
from backend.interview_plan import reconcile_interview_plan
from backend.interview_coach import expand_question


def test_intake_preserves_source_and_deduplicates_questions(tmp_path: Path) -> None:
    store = InterviewBankStore(tmp_path)

    result = store.intake("demo", "1. 什么是闭包？\n2. 什么是闭包？")

    assert result["source_count"] == 2
    assert result["new_count"] == 1
    assert len(store.list_questions("demo")) == 1
    assert store.list_sources("demo")[0]["raw_text"].startswith("1.")


def test_intake_keeps_missing_answer_and_unrated_mastery(tmp_path: Path) -> None:
    store = InterviewBankStore(tmp_path)

    result = store.intake("demo", "Go 的 goroutine 和线程有什么区别？")
    question = store.get_question("demo", result["question_ids"][0])

    assert question["answer_status"] == "missing"
    assert question["mastery"] == "unrated"
    assert question["origin"] == "collected"


def test_intake_rejects_invalid_user_id(tmp_path: Path) -> None:
    store = InterviewBankStore(tmp_path)

    with pytest.raises(ValueError, match="user_id"):
        store.intake("../escape", "什么是闭包？")


def test_mastery_and_study_mode_persist(tmp_path: Path) -> None:
    store = InterviewBankStore(tmp_path)
    question_id = store.intake("demo", "什么是闭包？")["question_ids"][0]

    store.set_study_mode("demo", "systematic")
    updated = store.record_mastery("demo", question_id, "smooth")

    assert updated["mastery"] == "smooth"
    assert InterviewBankStore(tmp_path).read_bank("demo")["study_mode"] == "systematic"


def test_reconcile_adds_backlog_without_lowering_display_progress() -> None:
    plan = {"display_progress": 60, "progress_floor": 60, "completed": ["syntax"]}

    result = reconcile_interview_plan(
        plan,
        [
            {"id": "q1", "concept_ids": ["closure"], "mastery": "smooth"},
            {"id": "q2", "concept_ids": ["scope"], "mastery": "unrated"},
        ],
    )

    assert result["display_progress"] == 60
    assert result["progress_floor"] == 60
    assert result["completed"] == ["syntax"]
    assert result["interview_backlog"][0]["question_id"] == "q1"
    assert result["bank_coverage"] == {"mastered": 1, "total": 2, "percent": 50}


def test_store_writes_expected_user_folder(tmp_path: Path) -> None:
    store = InterviewBankStore(tmp_path)
    store.intake("demo", "什么是闭包？")

    bank_path = tmp_path / "userdir/u_demo/interview-bank/bank.json"
    payload = json.loads(bank_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1


def test_expand_question_stores_answer_and_draft_related_questions(tmp_path: Path) -> None:
    store = InterviewBankStore(tmp_path)
    identifier = store.intake("demo", "什么是闭包？")["question_ids"][0]

    result = expand_question(
        store,
        "demo",
        identifier,
        lambda prompt, system: json.dumps({
            "answer_markdown": "闭包是函数与其词法环境的组合。",
            "rubric": ["定义", "使用场景"],
            "prerequisites": ["作用域"],
            "related_questions": ["闭包可能造成什么内存问题？"],
        }, ensure_ascii=False),
    )

    assert result["question"]["answer_status"] == "ready"
    related = store.get_question("demo", result["related_question_ids"][0])
    assert related["origin"] == "expanded"
    assert related["answer_status"] == "draft"


def test_expand_question_does_not_mutate_question_on_invalid_json(tmp_path: Path) -> None:
    store = InterviewBankStore(tmp_path)
    identifier = store.intake("demo", "什么是闭包？")["question_ids"][0]

    with pytest.raises(ValueError, match="结构化"):
        expand_question(store, "demo", identifier, lambda prompt, system: "not json")

    assert store.get_question("demo", identifier)["answer_status"] == "missing"


def test_expand_question_normalizes_model_rubric_object(tmp_path: Path) -> None:
    store = InterviewBankStore(tmp_path)
    identifier = store.intake("demo", "什么是闭包？")["question_ids"][0]

    result = expand_question(
        store,
        "demo",
        identifier,
        lambda prompt, system: json.dumps({
            "answer_markdown": "闭包会携带词法环境。",
            "rubric": {
                "核心标准": ["函数与环境", "说明使用场景"],
                "评分等级": {"优秀": "能应对追问", "一般": "只能背定义"},
            },
            "prerequisites": ["作用域"],
            "related_questions": [],
        }, ensure_ascii=False),
    )

    assert result["question"]["rubric"] == [
        "核心标准：函数与环境；说明使用场景",
        "评分等级：优秀：能应对追问；一般：只能背定义",
    ]


def test_expanded_compound_question_is_kept_as_one_question(tmp_path: Path) -> None:
    store = InterviewBankStore(tmp_path)
    identifier = store.intake("demo", "什么是闭包？")["question_ids"][0]

    result = expand_question(
        store,
        "demo",
        identifier,
        lambda prompt, system: json.dumps({
            "answer_markdown": "闭包会携带词法环境。",
            "rubric": ["能解释生命周期"],
            "prerequisites": ["作用域"],
            "related_questions": ["闭包会导致内存泄漏吗？如何避免？"],
        }, ensure_ascii=False),
    )

    assert len(result["related_question_ids"]) == 1
    related = store.get_question("demo", result["related_question_ids"][0])
    assert related["normalized_text"] == "闭包会导致内存泄漏吗？如何避免"


def test_interview_coach_supports_direct_server_script_import() -> None:
    backend_dir = Path(__file__).resolve().parents[1] / "backend"

    result = subprocess.run(
        [sys.executable, "-c", "import interview_coach; print('ok')"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
