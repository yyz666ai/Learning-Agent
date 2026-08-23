#!/usr/bin/env bash
# 本地网页入口：始终使用项目自己的依赖环境启动当前 FastAPI 服务。
set -euo pipefail

cd "$(dirname "$0")"
PORT="${1:-8787}"
PYTHON=".venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  echo "未找到 .venv。请先执行：python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt"
  exit 1
fi

exec "$PYTHON" -m backend.main "$PORT"
