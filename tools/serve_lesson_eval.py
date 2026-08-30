#!/usr/bin/env python3
"""Serve an explicitly selected isolated evaluation directory, never userdir/."""
import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend import main as api, codex_driver as driver
import uvicorn


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--port", type=int, default=8789)
    args = parser.parse_args()
    isolated = args.root.resolve()
    if ROOT / "evals/runs" not in isolated.parents or not (isolated / "workspace/dev").is_dir():
        raise SystemExit("root must be an existing evals/runs isolated workspace")
    for key, value in driver.load_secrets(ROOT / ".secrets.env").items():
        if key.startswith("DEEPSEEK_"):
            os.environ[key] = value
    api.SERVER_ROOT = isolated
    api.latest_release = lambda: isolated / "workspace/dev"
    api.chat = lambda user, prompt, release, **kwargs: driver.chat(user, prompt, release, **{**kwargs, "server_root": isolated})
    api.stream_chat = lambda user, prompt, release, **kwargs: driver.stream_chat(user, prompt, release, **{**kwargs, "server_root": isolated})
    uvicorn.run(api.app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
