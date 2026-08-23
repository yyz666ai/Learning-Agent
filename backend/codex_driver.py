"""Codex 驱动层：spawn codex exec 子进程，注入三层参数，流式回传。

三层注入（与 PRD 3.2 / 老师线上架构一致）：
  cwd        = releases/r…/           只读剧本快照（站进剧本，自动读到 AGENTS.md + .codex/skills/）
  CODEX_HOME = users/u_xxx/.codex-runtime/home   每用户运行时配置投影（模型/API 与个人命令行彻底分离）
  USER_DIR   = users/u_xxx            唯一可写区（learning-state.json / memory / demos）

模型与 API key：模型在 CODEX_HOME/config.toml 里声明 model_providers.deepseek，
key 通过 env_key="DEEPSEEK_API_KEY" 从进程环境读取；本层从 .secrets.env 加载后注入，
绝不出现在命令行参数或 config.toml 里。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from collections.abc import Iterator

SERVER_ROOT = Path(__file__).resolve().parent.parent
SECRETS_FILE = SERVER_ROOT / ".secrets.env"

# 沙箱档位：MVP 沿用老师线上验证过的方案 —— danger-full-access + 目录分离 + AGENTS.md 红线，
# 只读保护靠「快照副本 + 引导写 USER_DIR」兜底；正式版升级为 workspace-write / Docker :ro。
SANDBOX_MODE = os.environ.get("LEARNING_AGENT_SANDBOX", "danger-full-access")


def parse_codex_event(line: str) -> dict | None:
    """Convert one Codex JSONL line to a learner-facing stream event."""
    try:
        payload = json.loads(line)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    event_type = payload.get("type")
    if event_type == "turn.started":
        return {"event": "status", "data": {"message": "已连接学习引擎"}}
    item = payload.get("item")
    if not isinstance(item, dict):
        return None
    if event_type == "item.completed" and item.get("type") == "agent_message":
        text = item.get("text")
        if isinstance(text, str) and text:
            return {"event": "message.delta", "data": {"text": text}}
        return None
    if event_type == "item.started":
        return {"event": "status", "data": {"message": "正在准备学习内容"}}
    return None


def stream_chat(
    user_id: str,
    message: str,
    release_dir: Path,
    *,
    server_root: Path = SERVER_ROOT,
    sandbox: str | None = None,
    timeout: int = 600,
) -> Iterator[dict]:
    """Stream learner-facing events from one ``codex exec --json`` process."""
    user_dir = ensure_user(user_id, server_root)
    codex_home = user_dir / ".codex-runtime" / "home"
    secrets = load_secrets(server_root / ".secrets.env")
    env = build_env(user_dir, codex_home, secrets)
    request_id = uuid.uuid4().hex
    cmd = [
        "codex",
        "exec",
        "--json",
        "--skip-git-repo-check",
        "--sandbox",
        sandbox or SANDBOX_MODE,
        message,
    ]
    proc: subprocess.Popen[str] | None = None
    started = time.monotonic()
    yield {
        "event": "session.started",
        "data": {"request_id": request_id},
    }
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(release_dir),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            if time.monotonic() - started > timeout:
                proc.terminate()
                yield {
                    "event": "error",
                    "data": {
                        "request_id": request_id,
                        "message": "学习引擎响应超时，请稍后继续。",
                        "retryable": True,
                    },
                }
                return
            event = parse_codex_event(line)
            if event:
                yield event
        exit_code = proc.wait()
        if exit_code != 0:
            yield {
                "event": "error",
                "data": {
                    "request_id": request_id,
                    "message": "学习引擎暂时没有完成这次回答。",
                    "retryable": True,
                },
            }
            return
        yield {
            "event": "message.completed",
            "data": {"request_id": request_id},
        }
    except FileNotFoundError:
        yield {
            "event": "error",
            "data": {
                "request_id": request_id,
                "message": "没有找到 Codex 命令行，请检查运行环境。",
                "retryable": False,
            },
        }
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()


def load_secrets(path: Path = SECRETS_FILE) -> dict[str, str]:
    """从 .secrets.env 读取 key=value（不解析引号、不做 shell 展开）。"""
    secrets: dict[str, str] = {}
    if not path.exists():
        return secrets
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        secrets[k.strip()] = v.strip()
    return secrets


def resolve_user_dir(user_id: str, server_root: Path = SERVER_ROOT) -> Path:
    return server_root / "userdir" / f"u_{user_id}"


def ensure_user(user_id: str, server_root: Path = SERVER_ROOT) -> Path:
    """首次消息时创建用户目录骨架（USER_DIR + CODEX_HOME + 状态文件）。"""
    user_dir = resolve_user_dir(user_id, server_root)
    codex_home = user_dir / ".codex-runtime" / "home"
    (user_dir / "memory").mkdir(parents=True, exist_ok=True)
    (user_dir / "workspace" / "demos").mkdir(parents=True, exist_ok=True)
    codex_home.mkdir(parents=True, exist_ok=True)

    # CODEX_HOME 的 config.toml：从模板复制（模板不含密钥）
    config_tpl = server_root / "templates" / "codex-home-config.toml"
    config_dst = codex_home / "config.toml"
    if not config_dst.exists() and config_tpl.exists():
        config_dst.write_text(config_tpl.read_text(encoding="utf-8"), encoding="utf-8")

    # 初始学习状态
    state = user_dir / "learning-state.json"
    if not state.exists():
        state.write_text(
            '{\n'
            '  "schema_version": 1,\n'
            '  "revision": 0,\n'
            '  "profile_status": "uninitialized",\n'
            '  "active_language": null,\n'
            '  "active_plan": null,\n'
            '  "active_task": null,\n'
            '  "recent_evidence": [],\n'
            '  "due_review_count": 0,\n'
            '  "updated_at": null\n'
            '}\n',
            encoding="utf-8",
        )
    return user_dir


def build_env(user_dir: Path, codex_home: Path, secrets: dict[str, str]) -> dict[str, str]:
    env = dict(os.environ)
    env["CODEX_HOME"] = str(codex_home)
    env["USER_DIR"] = str(user_dir)
    env["LEARNING_AGENT_USER_ID"] = user_dir.name.removeprefix("u_")
    # 知识库自生长的写入目标：dev 母本的 curriculum（不是 cwd 里的只读快照）
    server_root = user_dir.parent.parent
    env["DEV_CURRICULUM"] = str(server_root / "workspace" / "dev" / "curriculum")
    if secrets.get("DEEPSEEK_API_KEY"):
        env["DEEPSEEK_API_KEY"] = secrets["DEEPSEEK_API_KEY"]
    # 清除宿主机可能残留的 Codex 相关变量，避免串到个人配置
    env.pop("CODEX_API_KEY", None)
    env.pop("OPENAI_API_KEY", None)
    return env


def run_once(
    user_id: str,
    message: str,
    release_dir: Path,
    *,
    server_root: Path = SERVER_ROOT,
    sandbox: str | None = None,
    stream: bool = True,
) -> int:
    """spawn 一次 codex exec，流式输出到 stdout，返回退出码。"""
    user_dir = ensure_user(user_id, server_root)
    codex_home = user_dir / ".codex-runtime" / "home"
    secrets = load_secrets(server_root / ".secrets.env")
    env = build_env(user_dir, codex_home, secrets)

    cmd = [
        "codex", "exec",
        "--skip-git-repo-check",
        "--sandbox", sandbox or SANDBOX_MODE,
        message,
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=str(release_dir),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    assert proc.stdout is not None and proc.stderr is not None
    for line in proc.stdout:
        if stream:
            sys.stdout.write(line)
            sys.stdout.flush()
    proc.wait()

    stderr = proc.stderr.read()
    if stderr.strip():
        sys.stderr.write(stderr)
    return proc.returncode


def run_once_capture(
    user_id: str,
    message: str,
    release_dir: Path,
    *,
    server_root: Path = SERVER_ROOT,
    sandbox: str | None = None,
    timeout: int = 600,
) -> dict:
    """spawn 一次 codex exec，捕获完整输出（供 Web API 用）。"""
    user_dir = ensure_user(user_id, server_root)
    codex_home = user_dir / ".codex-runtime" / "home"
    secrets = load_secrets(server_root / ".secrets.env")
    env = build_env(user_dir, codex_home, secrets)

    cmd = [
        "codex", "exec",
        "--skip-git-repo-check",
        "--sandbox", sandbox or SANDBOX_MODE,
        message,
    ]
    try:
        proc = subprocess.run(
            cmd, cwd=str(release_dir), env=env,
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        return {"output": (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or ""),
                "exit_code": None, "timed_out": True}
    return {"output": proc.stdout, "stderr": proc.stderr, "exit_code": proc.returncode, "timed_out": False}


def chat(
    user_id: str,
    message: str,
    release_dir: Path,
    *,
    server_root: Path = SERVER_ROOT,
    sandbox: str | None = None,
    timeout: int = 600,
) -> str:
    """一次对话：spawn `codex exec --json`，只提取最终 agent 回复文本（干净、无 banner/工具噪声）。"""
    user_dir = ensure_user(user_id, server_root)
    codex_home = user_dir / ".codex-runtime" / "home"
    secrets = load_secrets(server_root / ".secrets.env")
    env = build_env(user_dir, codex_home, secrets)

    cmd = [
        "codex", "exec", "--json",
        "--skip-git-repo-check",
        "--sandbox", sandbox or SANDBOX_MODE,
        message,
    ]
    try:
        proc = subprocess.run(
            cmd, cwd=str(release_dir), env=env,
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return "[超时] 学习 Agent 处理超时（>%ds），请稍后再试。" % timeout

    parts: list[str] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("type") == "item.completed":
            item = d.get("item") or {}
            if item.get("type") == "agent_message" and item.get("text"):
                parts.append(item["text"])
    if not parts and proc.stderr.strip():
        return "[出错] " + proc.stderr.strip()[-400:]
    return "\n".join(parts) if parts else "[空回复]"


def latest_release(server_root: Path = SERVER_ROOT) -> Path | None:
    current = server_root / "workspace" / "releases" / "current"
    if current.is_dir():
        return current
    return None


if __name__ == "__main__":
    # 用法：python backend/codex_driver.py <user_id> <release_dir> <message...>
    if len(sys.argv) < 4:
        print("usage: codex_driver.py <user_id> <release_dir> <message...>", file=sys.stderr)
        sys.exit(2)
    uid = sys.argv[1]
    release = Path(sys.argv[2]).resolve()
    msg = " ".join(sys.argv[3:])
    sys.exit(run_once(uid, msg, release))
