import json
import os
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_STATE_ROOT = "user-data"


def state_root(workspace: Path) -> Path:
    """Resolve the writable learning-state root.

    Harness 架构下，状态根由桥服务注入的环境变量 ``USER_DIR`` 指定（唯一可写区）。
    读不到时回退到老式 manifest.json 的 ``state_root`` / workspace 内 ``user-data/``，
    供脱离桥的本地开发用。
    """
    env = os.environ.get("USER_DIR")
    if env and env.strip():
        root = Path(env).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    configured = DEFAULT_STATE_ROOT
    try:
        manifest = json.loads(
            (workspace / "manifest.json").read_text(encoding="utf-8")
        )
        value = manifest.get("state_root")
        if isinstance(value, str) and value.strip() and value.strip() != "$USER_DIR":
            configured = value.strip()
    except (OSError, json.JSONDecodeError):
        pass
    root = (workspace / configured).resolve()
    if root == workspace.resolve():
        raise ValueError("state_root must not resolve to the workspace root")
    return root


def user_path(workspace: Path, relative: str) -> Path:
    root = state_root(workspace)
    target = (root / relative).resolve()
    if target != root and root not in target.parents:
        raise ValueError("path is outside the state root")
    return target


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return value


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        json.loads(Path(temporary).read_text(encoding="utf-8"))
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
