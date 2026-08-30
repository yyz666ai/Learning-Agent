"""直连 DeepSeek 判题（轻量、不走 codex，供前端即时判题/作业批改用）。

用 /chat/completions（OpenAI 兼容），模型默认 deepseek-v4-flash（快/省）。
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "https://api.deepseek.com/v1/chat/completions"


def load_api_key() -> str | None:
    p = SERVER_ROOT / ".secrets.env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() == "DEEPSEEK_API_KEY":
                    return v.strip()
    return os.environ.get("DEEPSEEK_API_KEY")


def chat(
    prompt: str,
    system: str | None = None,
    model: str = "deepseek-v4-flash",
    max_tokens: int = 900,
    temperature: float = 0.2,
    *,
    thinking: bool = False,
    json_object: bool = False,
    timeout: int = 120,
    raise_errors: bool = False,
) -> str:
    key = load_api_key()
    if not key:
        if raise_errors:
            raise RuntimeError("Missing DEEPSEEK_API_KEY")
        return "[错误] 缺少 DEEPSEEK_API_KEY"

    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        # DeepSeek V4 defaults to thinking mode. Bounded UI decisions should opt
        # out explicitly so a three-option onboarding question does not pay for
        # a long hidden reasoning pass.
        "thinking": {"type": "enabled" if thinking else "disabled"},
    }
    if json_object:
        payload["response_format"] = {"type": "json_object"}
    body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        BASE_URL,
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    except Exception as e:  # noqa: BLE001
        if raise_errors:
            raise RuntimeError("Model service unavailable") from e
        return f"[判题服务调用失败] {e}"
