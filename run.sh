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

if ! command -v codex >/dev/null 2>&1; then
  echo "未找到 Codex。请先执行：npm install -g @openai/codex（或 brew install codex）"
  exit 1
fi

if [[ ! -s ".secrets.env" ]] || ! grep -Eq '^DEEPSEEK_API_KEY=.+$' .secrets.env || grep -q 'replace_with_your_deepseek_api_key' .secrets.env; then
  echo "尚未配置 DeepSeek。请先执行：cp .secrets.env.example .secrets.env，然后填入 DEEPSEEK_API_KEY。"
  exit 1
fi

if [[ ! -d "workspace/releases/current" ]]; then
  echo "首次启动：正在准备教学知识库…"
  "$PYTHON" -m backend.publish
fi

exec "$PYTHON" -m backend.main "$PORT"
