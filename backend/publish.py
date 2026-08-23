"""发布流水线：workspace/dev → workspace/releases/current（单版本，覆盖发布）。

单人使用不需要版本回滚，所以只保留一个「当前版本」目录，发布即覆盖。
白名单来自 manifest.json 的 publishable；non_publishable 强制排除。
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parent.parent
DEV = SERVER_ROOT / "workspace" / "dev"
RELEASES = SERVER_ROOT / "workspace" / "releases"
CURRENT = RELEASES / "current"

# 强制排除（无论白名单怎么配都不进发布）
HARD_EXCLUDE = {".git", ".codex-runtime", "__pycache__", ".DS_Store", "scratch", "node_modules", ".venv", ".pytest_cache"}


def _match(path: str, pattern: str) -> bool:
    """简易 glob：`*` 匹配除 `/` 外的任意，`**` 匹配任意（含 `/`），目录尾缀 `/` 匹配整棵子树。"""
    if pattern.endswith("/"):
        return path.startswith(pattern) or (path + "/").startswith(pattern)
    if "**" in pattern:
        pre, _, post = pattern.partition("**")
        return path.startswith(pre) and path.endswith(post)
    if "*" in pattern:
        return re.fullmatch(pattern.replace(".", r"\.").replace("*", "[^/]*"), path) is not None
    return path == pattern


def _publishable(root: Path) -> list[str]:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    allowed = manifest.get("publishable", [])
    excluded = set(manifest.get("non_publishable", [])) | HARD_EXCLUDE

    result: list[str] = []
    for p in root.rglob("*"):
        if p.is_dir():
            continue
        rel = p.relative_to(root).as_posix()
        if any(seg in excluded for seg in p.parts):
            continue
        if any(_match(rel, pat) for pat in allowed):
            result.append(rel)
    return sorted(result)


def publish() -> Path:
    files = _publishable(DEV)
    if not files:
        sys.exit("manifest.json 的 publishable 白名单为空，拒绝发布")
    dst = CURRENT
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for rel in files:
        src = DEV / rel
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    (dst / "manifest.json").write_text(
        json.dumps({"published_from": DEV.name, "published_at": datetime.now(timezone.utc).isoformat(), "files": files},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"published {len(files)} files -> {dst}")
    return dst


if __name__ == "__main__":
    publish()
