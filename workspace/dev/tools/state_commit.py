import json
from datetime import datetime
from pathlib import Path
from typing import Any

from tools.workspace_utils import atomic_write_json, load_json, user_path


def commit_state(
    workspace: Path,
    relative: str,
    expected_revision: int,
    changes: dict[str, Any],
    event: dict[str, Any] | None = None,
) -> dict[str, Any]:
    target = user_path(workspace, relative)
    current = load_json(target)
    if current.get("revision") != expected_revision:
        raise ValueError("revision conflict")
    if "revision" in changes:
        raise ValueError("revision is managed by state_commit")
    updated = {**current, **changes, "revision": expected_revision + 1}
    atomic_write_json(target, updated)
    if load_json(target) != updated:
        raise RuntimeError("state read-back mismatch")
    if event is not None:
        try:
            recorded_at = datetime.fromisoformat(event["recorded_at"])
            history = user_path(
                workspace,
                f"history/learning-events-{recorded_at:%Y-%m}.jsonl",
            )
            history.parent.mkdir(parents=True, exist_ok=True)
            with history.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception:
            atomic_write_json(target, current)
            raise
    return updated
