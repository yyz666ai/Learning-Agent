"""Project-bound generation leases and rollback-safe filesystem commits."""

from __future__ import annotations

import json
import secrets
import shutil
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from .curriculum import Curriculum
    from .learning_content import SAFE_USER_ID, resolve_plan_path
except ImportError:
    from curriculum import Curriculum
    from learning_content import SAFE_USER_ID, resolve_plan_path


class GenerationStaleError(RuntimeError):
    """The generated result no longer belongs to the active project revision."""


@dataclass(frozen=True)
class ProjectGuard:
    revision: int
    topic: str
    active_plan: str
    current_knowledge_point_id: str


_LOCKS_GUARD = threading.Lock()
_USER_LOCKS: dict[str, threading.RLock] = {}


def _lock(server_root: Path, user_id: str) -> threading.RLock:
    key = f"{server_root.resolve()}::{user_id}"
    with _LOCKS_GUARD:
        return _USER_LOCKS.setdefault(key, threading.RLock())


@contextmanager
def project_lock(server_root: Path, user_id: str):
    """Serialize all active-project mutations for one local learner."""

    with _lock(server_root, user_id):
        yield


def _user_dir(server_root: Path, user_id: str) -> Path:
    if not SAFE_USER_ID.fullmatch(user_id):
        raise ValueError("invalid user_id")
    return server_root / "userdir" / f"u_{user_id}"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"invalid JSON object: {path.name}")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _assert_current(state: dict[str, Any], generation_id: str) -> None:
    if state.get("generation_id") != generation_id or state.get("generation_status") != "active":
        raise GenerationStaleError("generation is no longer active for this project")


def cancel_generation(server_root: Path, user_id: str, generation_id: str) -> bool:
    """Cancel only the matching active lease; restored projects remain untouched."""

    user_dir = _user_dir(server_root, user_id)
    state_path = user_dir / "learning-state.json"
    with _lock(server_root, user_id):
        state = _read_json(state_path)
        if state.get("generation_id") != generation_id:
            return False
        state["generation_id"] = None
        state["generation_status"] = "cancelled"
        state["revision"] = int(state.get("revision") or 0) + 1
        temporary = state_path.with_suffix(".json.cancel.tmp")
        _write_json(temporary, state)
        temporary.replace(state_path)
        return True


def begin_generation_lease(server_root: Path, user_id: str) -> str:
    """Supersede any previous generation and bind a fresh lease to current state."""

    user_dir = _user_dir(server_root, user_id)
    state_path = user_dir / "learning-state.json"
    with _lock(server_root, user_id):
        state = _read_json(state_path)
        generation_id = secrets.token_hex(16)
        state["generation_id"] = generation_id
        state["generation_status"] = "active"
        state["revision"] = int(state.get("revision") or 0) + 1
        temporary = state_path.with_suffix(".json.generation.tmp")
        _write_json(temporary, state)
        temporary.replace(state_path)
        return generation_id


def validate_generation_lease(server_root: Path, user_id: str, generation_id: str) -> dict[str, Any]:
    """Return a copy of the active state or reject a stale generation request."""

    with _lock(server_root, user_id):
        state = _read_json(_user_dir(server_root, user_id) / "learning-state.json")
        _assert_current(state, generation_id)
        return dict(state)


def commit_plan_generation(
    server_root: Path,
    user_id: str,
    generation_id: str,
    *,
    plan_markdown: str,
    curriculum: Curriculum,
    plan_status: str = "awaiting_confirmation",
) -> dict[str, Any]:
    """Commit Plan, curriculum and state only if their generation lease is current."""

    user_dir = _user_dir(server_root, user_id)
    state_path = user_dir / "learning-state.json"
    with _lock(server_root, user_id):
        state = _read_json(state_path)
        _assert_current(state, generation_id)
        topic = str(state.get("active_topic") or "").strip()
        route = str(state.get("goal_route") or "").strip()
        if curriculum.topic != topic or curriculum.route != route:
            raise GenerationStaleError("generated curriculum does not match the active project")
        plan_path = resolve_plan_path(user_dir, state.get("active_plan"))
        if plan_path is None:
            raise GenerationStaleError("active plan path changed during generation")

        next_state = dict(state)
        if plan_status not in {"awaiting_confirmation", "confirmed"}:
            raise ValueError("invalid committed plan status")
        next_state.update({
            "generation_id": None,
            "generation_status": "completed",
            "plan_status": plan_status,
            "revision": int(state.get("revision") or 0) + 1,
        })
        staging = user_dir / ".generation-jobs" / generation_id
        backup = user_dir / ".generation-backups" / generation_id
        if staging.exists():
            shutil.rmtree(staging)
        if backup.exists():
            shutil.rmtree(backup)
        staging.mkdir(parents=True, exist_ok=False)
        backup.mkdir(parents=True, exist_ok=False)

        relative_plan = plan_path.relative_to(user_dir)
        staged = {
            relative_plan: staging / relative_plan,
            Path("curriculum.json"): staging / "curriculum.json",
            Path("learning-state.json"): staging / "learning-state.json",
        }
        staged[relative_plan].parent.mkdir(parents=True, exist_ok=True)
        staged[relative_plan].write_text(plan_markdown, encoding="utf-8")
        _write_json(staged[Path("curriculum.json")], curriculum.model_dump(mode="json"))
        _write_json(staged[Path("learning-state.json")], next_state)

        moved_old: list[Path] = []
        installed: list[Path] = []
        try:
            for relative in staged:
                target = user_dir / relative
                if target.exists() or target.is_symlink():
                    backup_target = backup / relative
                    backup_target.parent.mkdir(parents=True, exist_ok=True)
                    target.replace(backup_target)
                    moved_old.append(relative)
            for relative, source in staged.items():
                target = user_dir / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                source.replace(target)
                installed.append(relative)
        except Exception as commit_error:
            rollback_error: Exception | None = None
            try:
                for relative in reversed(installed):
                    target = user_dir / relative
                    if target.exists() or target.is_symlink():
                        if target.is_dir() and not target.is_symlink():
                            shutil.rmtree(target)
                        else:
                            target.unlink()
                for relative in reversed(moved_old):
                    saved = backup / relative
                    target = user_dir / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    saved.replace(target)
            except Exception as exc:  # preserve the only recovery copy
                rollback_error = exc
            if rollback_error is not None:
                raise RuntimeError(f"plan commit failed; recovery backup preserved at {backup}") from commit_error
            shutil.rmtree(backup, ignore_errors=True)
            raise
        else:
            shutil.rmtree(backup, ignore_errors=True)
            shutil.rmtree(staging, ignore_errors=True)
            return {
                "plan_status": plan_status,
                "revision": next_state["revision"],
                "active_plan": relative_plan.as_posix(),
            }


def project_guard(server_root: Path, user_id: str) -> ProjectGuard:
    user_dir = _user_dir(server_root, user_id)
    state = _read_json(user_dir / "learning-state.json")
    curriculum = _read_json(user_dir / "curriculum.json")
    return ProjectGuard(
        revision=int(state.get("revision") or 0),
        topic=str(state.get("active_topic") or ""),
        active_plan=str(state.get("active_plan") or ""),
        current_knowledge_point_id=str(curriculum.get("current_knowledge_point_id") or ""),
    )


def validate_project_guard(server_root: Path, user_id: str, guard: ProjectGuard) -> None:
    current = project_guard(server_root, user_id)
    if current != guard:
        raise GenerationStaleError("project changed while content was being generated")
