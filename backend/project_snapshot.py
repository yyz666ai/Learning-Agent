"""Private, reversible snapshots for switching learning projects safely."""

from __future__ import annotations

import json
import re
import secrets
import shutil
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .learning_content import SAFE_USER_ID
except ImportError:
    from learning_content import SAFE_USER_ID


SNAPSHOT_ID = re.compile(r"^[a-f0-9]{24}$")
PROJECT_PATHS = (
    "learning-state.json",
    "profile.md",
    "profile.json",
    "curriculum.json",
    "plans",
    "lessons",
    "attempts",
    "memory",
    "reviews",
    "interview-bank",
    "practice-bank",
    "projects",
    "onboarding",
)


def normalize_project_topic(topic: str) -> str:
    """Return a stable comparison key without changing the learner-facing title."""

    normalized = unicodedata.normalize("NFKC", topic).casefold()
    return "".join(character for character in normalized if character.isalnum())


def _user_dir(server_root: Path, user_id: str) -> Path:
    if not SAFE_USER_ID.fullmatch(user_id):
        raise ValueError("invalid user_id")
    return server_root / "userdir" / f"u_{user_id}"


def _snapshot_dir(server_root: Path, user_id: str, snapshot_id: str) -> Path:
    if not SNAPSHOT_ID.fullmatch(snapshot_id):
        raise ValueError("invalid snapshot_id")
    return _user_dir(server_root, user_id) / ".project-snapshots" / snapshot_id


def create_project_snapshot(server_root: Path, user_id: str) -> str:
    user_dir = _user_dir(server_root, user_id)
    snapshot_id = secrets.token_hex(12)
    snapshot = _snapshot_dir(server_root, user_id, snapshot_id)
    snapshot.mkdir(parents=True, exist_ok=False)
    for relative in PROJECT_PATHS:
        source = user_dir / relative
        target = snapshot / relative
        if source.is_dir():
            shutil.copytree(source, target)
        elif source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    return snapshot_id


def restore_project_snapshot(server_root: Path, user_id: str, snapshot_id: str) -> None:
    user_dir = _user_dir(server_root, user_id)
    snapshot = _snapshot_dir(server_root, user_id, snapshot_id)
    if not snapshot.is_dir():
        raise FileNotFoundError(snapshot)
    _replace_project_paths(user_dir, snapshot)
    shutil.rmtree(snapshot)


def discard_project_snapshot(server_root: Path, user_id: str, snapshot_id: str) -> None:
    snapshot = _snapshot_dir(server_root, user_id, snapshot_id)
    if snapshot.is_dir():
        shutil.rmtree(snapshot)


def _archive_root(server_root: Path, user_id: str) -> Path:
    return _user_dir(server_root, user_id) / ".project-archives"


def _progress(project_root: Path) -> int:
    try:
        curriculum = json.loads((project_root / "curriculum.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    chapters = curriculum.get("chapters") if isinstance(curriculum, dict) else None
    if not isinstance(chapters, list):
        return 0
    points = [
        point
        for chapter in chapters if isinstance(chapter, dict)
        for point in chapter.get("knowledge_points", []) if isinstance(point, dict)
    ]
    if not points:
        return 0
    completed = sum(point.get("status") == "completed" for point in points)
    return round((completed / len(points)) * 100)


def _metadata(project_root: Path, project_id: str, *, current: bool = False) -> dict[str, Any]:
    topic = "未命名学习项目"
    updated_at = ""
    try:
        state = json.loads((project_root / "learning-state.json").read_text(encoding="utf-8"))
        if isinstance(state, dict) and isinstance(state.get("active_topic"), str) and state["active_topic"].strip():
            topic = state["active_topic"].strip()
        if isinstance(state, dict) and isinstance(state.get("updated_at"), str):
            updated_at = state["updated_at"]
    except (OSError, json.JSONDecodeError):
        pass
    if not updated_at:
        try:
            updated_at = datetime.fromtimestamp(project_root.stat().st_mtime, timezone.utc).isoformat()
        except OSError:
            updated_at = ""
    return {
        "id": project_id,
        "topic": topic,
        "current": current,
        "progress": _progress(project_root),
        "updated_at": updated_at,
    }


def archive_project_snapshot(server_root: Path, user_id: str, snapshot_id: str) -> dict[str, Any]:
    snapshot = _snapshot_dir(server_root, user_id, snapshot_id)
    if not snapshot.is_dir():
        raise FileNotFoundError(snapshot)
    archive = _archive_root(server_root, user_id) / snapshot_id
    archive.parent.mkdir(parents=True, exist_ok=True)
    snapshot.replace(archive)
    metadata = _metadata(archive, snapshot_id)
    (archive / "project.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata


def list_project_archives(server_root: Path, user_id: str) -> list[dict[str, Any]]:
    root = _archive_root(server_root, user_id)
    projects: list[dict[str, Any]] = []
    for folder in sorted(root.iterdir(), reverse=True) if root.is_dir() else []:
        if folder.is_dir() and SNAPSHOT_ID.fullmatch(folder.name):
            projects.append(_metadata(folder, folder.name))
    return projects


def list_learning_projects(server_root: Path, user_id: str) -> list[dict[str, Any]]:
    """Return the active project first, followed by reversible archives."""

    user_dir = _user_dir(server_root, user_id)
    projects: list[dict[str, Any]] = []
    if (user_dir / "learning-state.json").is_file():
        projects.append(_metadata(user_dir, "current", current=True))
    projects.extend(list_project_archives(server_root, user_id))
    return projects


def find_learning_project(server_root: Path, user_id: str, topic: str) -> dict[str, Any] | None:
    """Find the strongest existing project for a normalized learner topic."""

    topic_key = normalize_project_topic(topic)
    if not topic_key:
        return None
    matches = [
        project for project in list_learning_projects(server_root, user_id)
        if normalize_project_topic(str(project.get("topic") or "")) == topic_key
    ]
    if not matches:
        return None
    return max(matches, key=lambda project: (
        int(project.get("progress") or 0),
        str(project.get("updated_at") or ""),
        bool(project.get("current")),
    ))


def delete_learning_project(server_root: Path, user_id: str, project_id: str) -> list[dict[str, Any]]:
    """Delete one private project without crossing into shared curriculum paths."""

    user_dir = _user_dir(server_root, user_id)
    if project_id == "current":
        if not (user_dir / "learning-state.json").is_file():
            raise FileNotFoundError(project_id)
        for relative in PROJECT_PATHS:
            target = user_dir / relative
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
        pending = user_dir / ".project-snapshots"
        if pending.is_dir():
            shutil.rmtree(pending)
        return list_learning_projects(server_root, user_id)
    if not SNAPSHOT_ID.fullmatch(project_id):
        raise ValueError("invalid project id")
    archive = _archive_root(server_root, user_id) / project_id
    if not archive.is_dir():
        raise FileNotFoundError(project_id)
    shutil.rmtree(archive)
    return list_learning_projects(server_root, user_id)


def _replace_project_paths(user_dir: Path, source: Path) -> None:
    """Replace project-owned paths only after a complete staged copy exists."""

    operation_id = secrets.token_hex(12)
    staging = user_dir / f".project-restore-stage-{operation_id}"
    backup = user_dir / f".project-restore-backup-{operation_id}"
    staging.mkdir(parents=True, exist_ok=False)
    backup.mkdir(parents=True, exist_ok=False)
    cleanup_backup = False
    moved_current: list[str] = []
    moved_staged: list[str] = []
    try:
        # A failed source copy cannot touch the active project.
        for relative in PROJECT_PATHS:
            source_item = source / relative
            staged_item = staging / relative
            if source_item.is_dir():
                shutil.copytree(source_item, staged_item)
            elif source_item.is_file():
                staged_item.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_item, staged_item)

        try:
            for relative in PROJECT_PATHS:
                target = user_dir / relative
                if target.exists() or target.is_symlink():
                    backup_item = backup / relative
                    backup_item.parent.mkdir(parents=True, exist_ok=True)
                    target.replace(backup_item)
                    moved_current.append(relative)
            for relative in PROJECT_PATHS:
                staged_item = staging / relative
                if staged_item.exists() or staged_item.is_symlink():
                    target = user_dir / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    staged_item.replace(target)
                    moved_staged.append(relative)
            cleanup_backup = True
        except Exception:
            try:
                for relative in reversed(moved_staged):
                    target = user_dir / relative
                    if target.is_dir() and not target.is_symlink():
                        shutil.rmtree(target)
                    elif target.exists() or target.is_symlink():
                        target.unlink()
                for relative in reversed(moved_current):
                    backup_item = backup / relative
                    target = user_dir / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    backup_item.replace(target)
                cleanup_backup = True
            except Exception as rollback_error:
                raise RuntimeError(
                    f"project restore failed; recovery backup preserved at {backup}"
                ) from rollback_error
            raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        if cleanup_backup or not moved_current:
            shutil.rmtree(backup, ignore_errors=True)


def switch_project_archive(server_root: Path, user_id: str, project_id: str) -> dict[str, Any]:
    if not SNAPSHOT_ID.fullmatch(project_id):
        raise ValueError("invalid project id")
    archive = _archive_root(server_root, user_id) / project_id
    if not archive.is_dir():
        raise FileNotFoundError(archive)
    current_snapshot = create_project_snapshot(server_root, user_id)
    archive_project_snapshot(server_root, user_id, current_snapshot)
    _replace_project_paths(_user_dir(server_root, user_id), archive)
    metadata = _metadata(archive, project_id, current=True)
    shutil.rmtree(archive)
    return metadata
