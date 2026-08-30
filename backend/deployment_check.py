"""Fail-fast checks for a cloned Learning Agent installation."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
if __package__:
    from .platform_runtime import codex_command
else:
    from platform_runtime import codex_command


MIN_CODEX_VERSION = (0, 146, 0)
REQUIRED_FILES = (
    "workspace/dev/AGENTS.md",
    "workspace/dev/.codex/skills/learning-plan/SKILL.md",
    "workspace/dev/.codex/skills/adaptive-lesson-flow/SKILL.md",
    "workspace/dev/tools/web_search.py",
    "templates/codex-home-config.toml",
)


def parse_codex_version(value: str) -> tuple[int, int, int] | None:
    match = re.search(r"\b(\d+)\.(\d+)\.(\d+)\b", value)
    return tuple(map(int, match.groups())) if match else None


def check_local_deployment(
    server_root: Path,
    *,
    codex_version_text: str,
) -> list[str]:
    issues: list[str] = []
    version = parse_codex_version(codex_version_text)
    if version is None or version < MIN_CODEX_VERSION:
        issues.append(
            "Codex 0.146.0 或更高版本才支持当前 DeepSeek Responses 配置；"
            "请重新执行 npm install -g @openai/codex 或 brew upgrade codex。"
        )
    secrets = server_root / ".secrets.env"
    secret_text = secrets.read_text(encoding="utf-8") if secrets.is_file() else ""
    if (
        re.search(r"(?m)^DEEPSEEK_API_KEY=\S+$", secret_text) is None
        or "replace_with_your_deepseek_api_key" in secret_text
    ):
        issues.append("项目根目录 .secrets.env 还没有配置有效的 DEEPSEEK_API_KEY。")
    for relative in REQUIRED_FILES:
        if not (server_root / relative).is_file():
            issues.append(f"部署包缺少 {relative}，请重新拉取完整仓库。")
    return issues


def main(*, server_root: Path | None = None) -> int:
    server_root = server_root or Path(__file__).resolve().parent.parent
    try:
        version = subprocess.run(
            [*codex_command(), "--version"], capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=10, check=False,
        )
    except (OSError, RuntimeError, subprocess.SubprocessError):
        print("部署自检失败：无法运行 Codex，请检查 Codex 和 Node.js 安装及 PATH。", file=sys.stderr)
        return 1
    if version.returncode:
        print("部署自检失败：Codex 版本检查未成功，请修复安装后重试。", file=sys.stderr)
        return 1
    issues = check_local_deployment(
        server_root,
        codex_version_text=f"{version.stdout}\n{version.stderr}",
    )
    if issues:
        print("部署自检失败：", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1
    print("部署自检通过：Codex、DeepSeek 配置、Skills 与教学工具完整。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
