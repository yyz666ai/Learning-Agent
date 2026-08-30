"""Shared native startup: validate, publish, then serve with one Python environment."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _port(value: str) -> int:
    if not value.isascii() or not value.isdecimal() or not 1 <= int(value) <= 65535:
        raise argparse.ArgumentTypeError("端口必须是 1 到 65535 的整数。")
    return int(value)


def main(argv: list[str] | None = None, *, server_root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", nargs="?", default=8787, type=_port)
    args = parser.parse_args(argv)
    root = server_root or Path(__file__).resolve().parent.parent
    for module, arguments in (
        ("backend.deployment_check", []),
        ("backend.publish", []),
        ("backend.main", [str(args.port)]),
    ):
        try:
            result = subprocess.run([sys.executable, "-m", module, *arguments], cwd=str(root), check=False)
        except OSError:
            print("启动失败：无法运行项目 Python 环境。", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            return 130
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
