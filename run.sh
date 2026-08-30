#!/usr/bin/env bash
# 本地网页入口：校验、发布和启动流程统一由项目 Python 执行。
set -euo pipefail

cd -- "$(dirname -- "$0")"
if [[ -x ".venv/bin/python" ]]; then
  runtime_python=".venv/bin/python"
elif [[ -f ".venv/Scripts/python.exe" ]]; then
  runtime_python=".venv/Scripts/python.exe"
else
  echo "未找到 .venv。请先创建项目虚拟环境并安装 requirements.txt 中的依赖。" >&2
  exit 1
fi
exec "$runtime_python" -m backend.startup "$@"
