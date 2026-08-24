from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from backend import project_snapshot
from backend.project_snapshot import create_project_snapshot, restore_project_snapshot


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_project_snapshot_restores_every_project_owned_store(tmp_path: Path) -> None:
    user_dir = tmp_path / "userdir/u_learner"
    _write(user_dir / "learning-state.json", json.dumps({"active_topic": "Go"}))
    _write(user_dir / "profile.md", "# Go learner\n")
    _write(user_dir / "profile.json", json.dumps({"topic": "Go"}))
    _write(user_dir / "onboarding/intent-state.json", json.dumps({"slots": {"topic": "Go"}}))
    _write(user_dir / "projects/go/main.go", "package main\n")
    _write(user_dir / "practice-bank/items/go-question.json", json.dumps({"topic": "Go"}))

    snapshot_id = create_project_snapshot(tmp_path, "learner")

    _write(user_dir / "profile.json", json.dumps({"topic": "Python"}))
    _write(user_dir / "onboarding/intent-state.json", json.dumps({"slots": {"topic": "Python"}}))
    _write(user_dir / "projects/python/main.py", "print('python')\n")
    _write(user_dir / "practice-bank/items/python-question.json", json.dumps({"topic": "Python"}))

    restore_project_snapshot(tmp_path, "learner", snapshot_id)

    assert json.loads((user_dir / "profile.json").read_text())["topic"] == "Go"
    assert json.loads((user_dir / "onboarding/intent-state.json").read_text())["slots"]["topic"] == "Go"
    assert (user_dir / "projects/go/main.go").is_file()
    assert not (user_dir / "projects/python/main.py").exists()
    assert (user_dir / "practice-bank/items/go-question.json").is_file()
    assert not (user_dir / "practice-bank/items/python-question.json").exists()


def test_restore_copy_failure_keeps_the_active_project_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_dir = tmp_path / "userdir/u_learner"
    _write(user_dir / "learning-state.json", json.dumps({"active_topic": "Go"}))
    _write(user_dir / "projects/go/main.go", "package main\n")
    snapshot_id = create_project_snapshot(tmp_path, "learner")
    _write(user_dir / "learning-state.json", json.dumps({"active_topic": "Python"}))
    _write(user_dir / "projects/python/main.py", "print('python')\n")

    original_copytree = shutil.copytree
    calls = 0

    def fail_during_stage(source: Path, target: Path, *args: object, **kwargs: object) -> Path:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("simulated copy failure")
        return original_copytree(source, target, *args, **kwargs)

    monkeypatch.setattr(project_snapshot.shutil, "copytree", fail_during_stage)
    with pytest.raises(OSError, match="simulated copy failure"):
        restore_project_snapshot(tmp_path, "learner", snapshot_id)

    assert json.loads((user_dir / "learning-state.json").read_text())["active_topic"] == "Python"
    assert (user_dir / "projects/python/main.py").is_file()
    assert (user_dir / "projects/go/main.go").is_file()
    assert not list(user_dir.glob(".project-restore-*"))


def test_failed_rollback_preserves_the_recovery_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_dir = tmp_path / "userdir/u_learner"
    source = tmp_path / "source"
    _write(user_dir / "learning-state.json", json.dumps({"active_topic": "Python"}))
    _write(source / "learning-state.json", json.dumps({"active_topic": "Go"}))
    original_replace = Path.replace

    def fail_commit_and_rollback(path: Path, target: Path) -> Path:
        if ".project-restore-stage-" in str(path) and path.name == "learning-state.json":
            raise OSError("commit failed")
        if ".project-restore-backup-" in str(path) and path.name == "learning-state.json":
            raise OSError("rollback failed")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_commit_and_rollback)
    with pytest.raises(RuntimeError, match="recovery backup preserved"):
        project_snapshot._replace_project_paths(user_dir, source)

    backups = list(user_dir.glob(".project-restore-backup-*"))
    assert len(backups) == 1
    assert json.loads((backups[0] / "learning-state.json").read_text())["active_topic"] == "Python"
