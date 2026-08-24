from __future__ import annotations

import json
from pathlib import Path

from backend.learning_content import read_learning_context, resolve_plan_path


def make_user(root: Path, active_plan: str) -> Path:
    user = root / "userdir" / "u_yang"
    user.mkdir(parents=True)
    (user / "learning-state.json").write_text(
        json.dumps(
            {
                "profile_status": "confirmed",
                "active_language": "go",
                "active_plan": active_plan,
                "active_task": "stage0_first_program",
                "due_review_count": 1,
                "recent_evidence": ["first lesson started"],
            }
        ),
        encoding="utf-8",
    )
    (user / "profile.md").write_text(
        "# 学习者画像\n\n- 每周时间：约 5 小时\n- 单次时长：25 分钟\n",
        encoding="utf-8",
    )
    return user


def test_prefers_active_plan_inside_plans(tmp_path: Path) -> None:
    user = make_user(tmp_path, active_plan="plans/go-zero.md")
    plan = user / "plans" / "go-zero.md"
    plan.parent.mkdir()
    plan.write_text(
        "# Go 从零开始\n\n## 阶段\n\n### 阶段 0 · 基础入门\n- 第一个 Go 程序\n\n## 当前任务\n\n运行 Hello Go\n",
        encoding="utf-8",
    )

    context = read_learning_context("yang", tmp_path)

    assert context["plan"]["title"] == "Go 从零开始"
    assert context["plan"]["source"] == "plans/go-zero.md"
    assert context["current_task"] == "运行 Hello Go"


def test_reads_legacy_root_plan(tmp_path: Path) -> None:
    user = make_user(tmp_path, active_plan="learning-plan.md")
    (user / "learning-plan.md").write_text(
        "# 学习计划：Python\n\n## 当前任务\n\n写一个问候语\n",
        encoding="utf-8",
    )

    context = read_learning_context("yang", tmp_path)

    assert context["plan"]["source"] == "learning-plan.md"
    assert context["plan"]["title"] == "Python"


def test_rejects_plan_path_outside_user_dir(tmp_path: Path) -> None:
    user = make_user(tmp_path, active_plan="../../outside.md")
    (tmp_path / "outside.md").write_text("# Secret", encoding="utf-8")

    context = read_learning_context("yang", tmp_path)

    assert context["plan"]["content"] == ""
    assert context["plan"]["source"] == ""


def test_resolves_plan_inside_symlinked_user_dir(tmp_path: Path) -> None:
    real_user = tmp_path / "persistent" / "u_yang"
    real_user.mkdir(parents=True)
    plan = real_user / "plans" / "frontend-interview.md"
    plan.parent.mkdir()
    plan.write_text("# 前端面试路线", encoding="utf-8")
    linked_user = tmp_path / "runtime" / "userdir" / "u_yang"
    linked_user.parent.mkdir(parents=True)
    linked_user.symlink_to(real_user, target_is_directory=True)

    resolved = resolve_plan_path(linked_user, "plans/frontend-interview.md")

    assert resolved == plan.resolve()


def test_rejects_unsafe_user_id(tmp_path: Path) -> None:
    context = read_learning_context("../yang", tmp_path)

    assert context["user_id"] == "yang"


def test_returns_learner_facing_summary(tmp_path: Path) -> None:
    user = make_user(tmp_path, active_plan="learning-plan.md")
    (user / "learning-plan.md").write_text(
        "# Go 零基础路线\n\n## 当前任务\n\n完成第一课\n",
        encoding="utf-8",
    )

    context = read_learning_context("yang", tmp_path)

    assert context["language"] == "go"
    assert context["session_minutes"] == 25
    assert context["due_review_count"] == 1
    assert "revision" not in context


def test_custom_topic_does_not_fall_back_to_go(tmp_path: Path) -> None:
    user_dir = tmp_path / "userdir/u_webhook"
    user_dir.mkdir(parents=True)
    (user_dir / "learning-state.json").write_text(
        json.dumps(
            {
                "profile_status": "confirmed",
                "active_language": None,
                "active_topic": "webhook retry API",
                "active_plan": None,
            }
        ),
        encoding="utf-8",
    )

    context = read_learning_context("webhook", tmp_path)

    assert context["language"] == "custom"
    assert context["topic"] == "webhook retry API"


def test_detailed_curriculum_chapters_are_visible_in_left_outline(tmp_path: Path) -> None:
    user = make_user(tmp_path, active_plan="plans/go.md")
    plan = user / "plans/go.md"
    plan.parent.mkdir()
    plan.write_text(
        "# Go 详细学习大纲\n\n### 第 1 章：程序结构\n\n#### 1.1 package main\n\n"
        "### 第 2 章：变量与类型\n\n#### 2.1 var 与 :=（当前）\n",
        encoding="utf-8",
    )

    context = read_learning_context("yang", tmp_path)

    assert [stage["title"] for stage in context["plan"]["stages"]] == [
        "第 1 章：程序结构", "第 2 章：变量与类型",
    ]
    assert context["plan"]["stages"][0]["status"] == "completed"
    assert context["plan"]["stages"][1]["status"] == "active"
