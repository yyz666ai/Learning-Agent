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
import logging
import os
import signal
import subprocess
import sys
import time
import uuid
from contextlib import nullcontext
from collections import deque
from queue import Empty, Full, Queue
from threading import Event, Thread
from pathlib import Path
from collections.abc import Iterator
try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 remains a supported runtime.
    import tomli as tomllib

if __package__:
    from .platform_runtime import codex_command
    from .deepseek_transport import deepseek_generation_transport
else:  # Preserve the documented python backend/codex_driver.py entry point.
    from platform_runtime import codex_command
    from deepseek_transport import deepseek_generation_transport

SERVER_ROOT = Path(__file__).resolve().parent.parent
SECRETS_FILE = SERVER_ROOT / ".secrets.env"
logger = logging.getLogger(__name__)

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


def _process_group_options(platform_name: str | None = None) -> dict:
    if (platform_name or sys.platform) == "win32":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _stop_process_tree(proc: subprocess.Popen, platform_name: str | None = None) -> None:
    """Stop only the new process group created for this invocation, then reap its parent."""
    if proc.pid <= 0:
        raise ValueError("invalid child pid")
    if (platform_name or sys.platform) == "win32":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=2, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            pass
    else:
        # start_new_session makes the child PID the process-group ID, even when
        # its npm/Node parent has exited but a native descendant still owns pipes.
        if proc.pid == os.getpgrp():
            raise ValueError("refusing to terminate the host process group")
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if proc.poll() is None:
        proc.kill()
    proc.wait(timeout=2)


def _stream_process(cmd: list[str], message: str, release_dir: Path, env: dict,
                    timeout: float, *, full_stderr: bool = False) -> Iterator[tuple[str, str | int]]:
    """Drain both pipes while feeding stdin; deadline also applies to silent children."""
    proc = subprocess.Popen(
        cmd, cwd=str(release_dir), env=env, stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
        **_process_group_options(),
    )
    assert proc.stdout is not None and proc.stderr is not None and proc.stdin is not None
    lines: Queue[str | None] = Queue(maxsize=256)
    stopped = Event()
    stderr_tail: deque[str] = deque(maxlen=None if full_stderr else 32)
    deadline = time.monotonic() + timeout
    completed = False

    def enqueue(line: str | None) -> None:
        while not stopped.is_set():
            try:
                lines.put(line, timeout=0.05)
                return
            except Full:
                pass

    def read_stdout() -> None:
        try:
            for line in proc.stdout:
                if stopped.is_set():
                    break
                enqueue(line)
        finally:
            enqueue(None)

    def read_stderr() -> None:
        while chunk := proc.stderr.read(4096):
            stderr_tail.append(chunk)

    def write_input() -> None:
        try:
            proc.stdin.write(message)
            proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass

    workers = [Thread(target=target, daemon=True) for target in (read_stdout, read_stderr, write_input)]
    for worker in workers:
        worker.start()
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(cmd, timeout)
            try:
                line = lines.get(timeout=remaining)
            except Empty:
                raise subprocess.TimeoutExpired(cmd, timeout) from None
            if line is None:
                break
            yield "stdout", line
        code = proc.wait(timeout=max(0, deadline - time.monotonic()))
        workers[1].join(timeout=max(0, deadline - time.monotonic()))
        if workers[1].is_alive():
            raise subprocess.TimeoutExpired(cmd, timeout)
        completed = True
        yield "stderr", "".join(stderr_tail)
        yield "exit", code
    finally:
        stopped.set()
        if not completed:
            _stop_process_tree(proc)
        for worker in workers:
            worker.join(timeout=0.2)
        for pipe, worker in zip((proc.stdout, proc.stderr, proc.stdin), workers):
            if not worker.is_alive():
                pipe.close()


def _capture_process(cmd: list[str], message: str, release_dir: Path, env: dict,
                     timeout: float) -> subprocess.CompletedProcess:
    """Capture through the same deadline/tree cleanup boundary as streaming.

    Unlike communicate(input=...) on Windows, stdin writing cannot block the
    deadline thread when a wrapper/native child stops reading its input.
    """
    output: list[str] = []
    stderr = ""
    code = 1
    try:
        for kind, value in _stream_process(cmd, message, release_dir, env, timeout, full_stderr=True):
            if kind == "stdout":
                output.append(value)
            elif kind == "stderr":
                stderr = value
            elif kind == "exit":
                code = value
    except subprocess.TimeoutExpired as exc:
        exc.output = "".join(output)
        raise
    return subprocess.CompletedProcess(cmd, code, "".join(output), stderr)


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
    yield {
        "event": "session.started",
        "data": {"request_id": request_id},
    }
    try:
        cmd = [*codex_command(), "exec", "--json", "--skip-git-repo-check",
               "--sandbox", sandbox or SANDBOX_MODE, "-"]
        exit_code = 1
        for kind, value in _stream_process(cmd, message, release_dir, env, timeout):
            if kind == "stdout":
                event = parse_codex_event(value)
                if event:
                    yield event
            elif kind == "exit":
                exit_code = value
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
    except subprocess.TimeoutExpired:
        yield {"event": "error", "data": {"request_id": request_id,
               "message": "学习引擎响应超时，请稍后继续。", "retryable": True}}
    except (OSError, RuntimeError):
        yield {
            "event": "error",
            "data": {
                "request_id": request_id,
                "message": "无法运行 Codex 命令行，请检查 Codex 和 Node.js 运行环境。",
                "retryable": False,
            },
        }


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
    env["LEARNING_AGENT_PYTHON"] = sys.executable
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
    timeout: int = 600,
) -> int:
    """spawn 一次 codex exec，流式输出到 stdout，返回退出码。"""
    user_dir = ensure_user(user_id, server_root)
    codex_home = user_dir / ".codex-runtime" / "home"
    secrets = load_secrets(server_root / ".secrets.env")
    env = build_env(user_dir, codex_home, secrets)

    cmd = [
        *codex_command(), "exec",
        "--skip-git-repo-check",
        "--sandbox", sandbox or SANDBOX_MODE,
        "-",
    ]
    try:
        for kind, value in _stream_process(cmd, message, release_dir, env, timeout):
            if kind == "stdout" and stream:
                sys.stdout.write(value)
                sys.stdout.flush()
            elif kind == "stderr" and value.strip():
                sys.stderr.write(value)
            elif kind == "exit":
                return value
    except subprocess.TimeoutExpired:
        print("学习引擎响应超时，请稍后继续。", file=sys.stderr)
        return 124
    return 1


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
        *codex_command(), "exec",
        "--skip-git-repo-check",
        "--sandbox", sandbox or SANDBOX_MODE,
        "-",
    ]
    try:
        proc = _capture_process(cmd, message, release_dir, env, timeout)
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
    generation: str | None = None,
    allow_research: bool = False,
) -> str:
    """一次对话：spawn `codex exec --json`，只提取最终 agent 回复文本（干净、无 banner/工具噪声）。"""
    user_dir = ensure_user(user_id, server_root)
    codex_home = user_dir / ".codex-runtime" / "home"
    secrets = load_secrets(server_root / ".secrets.env")
    env = build_env(user_dir, codex_home, secrets)

    cmd = [
        *codex_command(), "exec", "--json",
        "--skip-git-repo-check",
        "--sandbox", sandbox or SANDBOX_MODE,
        "-",
    ]
    if generation:
        if not allow_research and sandbox is None:
            cmd[cmd.index("--sandbox") + 1] = "read-only"
        from backend.generation_context import prepare_generation_context
        message = prepare_generation_context(release_dir, user_dir, generation, message, allow_research)
        options = ["-c", 'model_reasoning_effort="none"',
                   "-c", "model_supports_reasoning_summaries=true"]
        if not allow_research:
            options += ["--disable", "shell_tool", "-c", 'web_search="disabled"']
        cmd[-1:-1] = options
    transport = nullcontext(None)
    config_path = codex_home / "config.toml"
    if generation and config_path.is_file():
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        provider = config.get("model_providers", {}).get("deepseek", {})
        if (config.get("model_provider") == "deepseek"
                and str(provider.get("base_url", "")).rstrip("/") in {
                    "https://api.deepseek.com", "https://api.deepseek.com/v1"}
                and provider.get("env_key") == "DEEPSEEK_API_KEY"
                and env.get("DEEPSEEK_API_KEY")):
            transport = deepseek_generation_transport(env["DEEPSEEK_API_KEY"], timeout,
                allow_tools=allow_research, json_output=generation in {"lesson", "diagnosis"})
    started = time.monotonic()
    if generation:
        logger.info("generation.start kind=%s research=%s requested_reasoning=none", generation, allow_research)
    try:
        with transport as relay:
            if relay is not None:
                cmd[-1:-1] = ["-c", f'model_providers.deepseek.base_url="{relay.base_url}"',
                               "-c", 'model_providers.deepseek.env_key="LEARNING_AGENT_RELAY_TOKEN"']
                # Research scripts still call the public API with the real key;
                # the private relay credential must never be sent upstream.
                env["LEARNING_AGENT_RELAY_TOKEN"] = relay.token
                for proxy_key in ("NO_PROXY", "no_proxy"):
                    env[proxy_key] = ",".join(filter(None, (env.get(proxy_key, ""), "127.0.0.1", "localhost")))
            proc = _capture_process(cmd, message, release_dir, env, timeout)
    except subprocess.TimeoutExpired:
        if generation:
            logger.warning("generation.timeout kind=%s elapsed=%.2fs", generation, time.monotonic() - started)
        return "[超时] 学习 Agent 处理超时（>%ds），请稍后再试。" % timeout

    parts: list[str] = []
    tool_count = 0
    usage = {}
    completed = False
    failed = False
    stream_errors = 0
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
            if item.get("type") in {"command_execution", "mcp_tool_call", "web_search", "file_change"}:
                tool_count += 1
            if item.get("type") == "agent_message" and item.get("text"):
                parts.append(item["text"])
        elif d.get("type") == "turn.completed":
            completed = True
            usage = {key: value for key, value in (d.get("usage") or {}).items()
                     if key in {"input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens"}}
        elif d.get("type") == "turn.failed":
            failed = True
        elif d.get("type") == "error":
            stream_errors += 1
    if generation:
        logger.info("generation.finish kind=%s elapsed=%.2fs tool_calls=%s stream_errors=%s exit_code=%s usage=%s",
                    generation, time.monotonic() - started, tool_count, stream_errors, proc.returncode, usage)
        if proc.returncode != 0 or failed or not completed:
            return "[出错] 学习引擎未完整完成生成，已保留原有内容，请重试。"
    if not parts and proc.stderr.strip():
        return "[出错] " + proc.stderr.strip()[-400:]
    # Progress commentary is not part of a generated Markdown/JSON artifact.
    # Interactive chat keeps its existing multi-message behavior.
    return (parts[-1] if generation else "\n".join(parts)) if parts else "[空回复]"


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
