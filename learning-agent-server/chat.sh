#!/usr/bin/env bash
# 用户侧交互入口：在「只读发布快照」里打开 Codex 命令行，和你的学习 Agent 直接对话。
# 用法：./chat.sh [用户ID，默认 yang] [指定版本目录，可选，默认最新 workspace/releases]
# 审批：默认 on-request（模型自己判断何时问）。想完全少打断：LEARNING_AGENT_APPROVAL=never ./chat.sh
set -euo pipefail
cd "$(dirname "$0")"

USER_ID="${1:-yang}"
RELEASE="${2:-workspace/releases/current}"
if [ ! -d "$RELEASE" ]; then
  echo "还没有发布版本，先运行：python backend/publish.py" >&2
  exit 1
fi
APPROVAL="${LEARNING_AGENT_APPROVAL:-on-request}"

set -a; source .secrets.env; set +a

USER_DIR="$PWD/userdir/u_$USER_ID"
export CODEX_HOME="$USER_DIR/.codex-runtime/home"
export USER_DIR
mkdir -p "$CODEX_HOME" "$USER_DIR/memory" "$USER_DIR/workspace/demos"

echo "→ 进入学习 Agent（用户 u_$USER_ID，快照 $RELEASE，审批 $APPROVAL）"
exec codex --sandbox danger-full-access -a "$APPROVAL" -C "$RELEASE"
