"""Platform-specific process boundaries; never execute npm shims through a shell."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def codex_command(*, platform_name: str | None = None) -> list[str]:
    platform_name = platform_name or sys.platform
    executable = shutil.which("codex.exe") if platform_name == "win32" else None
    executable = executable or shutil.which("codex")
    if not executable and platform_name == "win32":
        executable = shutil.which("codex.cmd") or shutil.which("codex.ps1")
    if not executable:
        raise FileNotFoundError("没有找到 Codex，请安装 @openai/codex 并确认 PATH。")
    shim = Path(executable)
    if platform_name != "win32" or shim.suffix.lower() not in {".cmd", ".ps1", ".bat"}:
        return [executable]
    node = shutil.which("node") or shutil.which("node.exe")
    if not node:
        raise RuntimeError("Codex npm 启动器需要 Node.js，请安装 Node.js 并确认 PATH。")
    candidates = [shim.parent / "node_modules/@openai/codex/bin/codex.js"]
    if shim.parent.name == ".bin":
        candidates.insert(0, shim.parent.parent / "@openai/codex/bin/codex.js")
    for entry in candidates:
        if entry.is_file():
            return [node, str(entry)]
    raise RuntimeError("Codex npm 安装不完整，请重新执行 npm install -g @openai/codex。")


def open_folder(path: Path, *, platform_name: str | None = None) -> dict:
    platform_name = platform_name or sys.platform
    result = {"opened": False, "path": str(path)}
    try:
        if platform_name == "win32":
            startfile = getattr(os, "startfile", None)
            if startfile is None:
                return {**result, "message": "当前环境不能打开文件夹，请手动打开此路径。"}
            startfile(str(path))
        elif platform_name == "darwin":
            subprocess.run(["open", str(path)], check=True, timeout=10)
        elif platform_name.startswith("linux"):
            opener = shutil.which("xdg-open")
            if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")) or not opener:
                return {**result, "message": "当前环境没有可用桌面，请手动打开此路径。"}
            subprocess.run([opener, str(path)], check=True, timeout=10)
        else:
            return {**result, "message": "请手动打开此路径。"}
    except (OSError, subprocess.SubprocessError):
        return {**result, "message": "系统未能打开文件夹，请手动打开此路径。"}
    return {**result, "opened": True}
