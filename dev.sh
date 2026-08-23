#!/usr/bin/env bash
# 作者侧（管理端）交互入口：在 workspace/dev（可写）里打开 Codex，用对话方式改剧本/策展。
set -euo pipefail
cd "$(dirname "$0")"

USER_ID="${1:-yang}"
APPROVAL="${LEARNING_AGENT_APPROVAL:-on-request}"

set -a; source .secrets.env; set +a

USER_DIR="$PWD/userdir/u_$USER_ID"
export CODEX_HOME="$USER_DIR/.codex-runtime/home"
export USER_DIR
mkdir -p "$CODEX_HOME" "$USER_DIR/memory" "$USER_DIR/workspace/demos"

echo "→ 进入作者工作台（workspace/dev，可写；改完记得 git commit + 发布）"
exec codex --sandbox danger-full-access -a "$APPROVAL" -C workspace/dev
