"""Shared native startup: validate, publish, then serve with one Python environment."""
from __future__ import annotations

import argparse
import socket
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
    # Never republish a live Codex working directory just to discover later
    # that another server already owns the port (including service restarts).
    try:
        with socket.socket() as probe:
            if sys.platform == "win32":
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            else:
                # Like the HTTP server, permit TIME_WAIT after a clean restart,
                # while still rejecting a live listener on this address.
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(("127.0.0.1", args.port))
    except OSError:
        print(f"端口 {args.port} 已被占用或无法绑定；未发布、未启动第二个服务。", file=sys.stderr)
        return 3
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
