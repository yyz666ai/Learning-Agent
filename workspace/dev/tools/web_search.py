#!/usr/bin/env python3
"""联网搜索：调 DeepSeek Responses API 的内置 web_search 工具，返回带引用的结果。

用法：python tools/web_search.py <查询词>
依赖：环境变量 DEEPSEEK_API_KEY（由桥服务 spawn 时注入）。
说明：DeepSeek 的 Responses API 原生支持 web_search（服务端执行），不需要额外搜索 API。
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

BASE_URL = "https://api.deepseek.com/v1/responses"


def web_search(query: str) -> str:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        return "[错误] 缺少 DEEPSEEK_API_KEY（桥服务应注入该环境变量）"

    body = {
        "model": "deepseek-v4-flash",
        "input": query,
        "tools": [{"type": "web_search"}],
    }
    req = urllib.request.Request(
        BASE_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        return f"[搜索失败] {e}"

    for item in data.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    return c.get("text", "")
    return "[无结果]"


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]).strip()
    if not q:
        print("用法: python tools/web_search.py <查询词>", file=sys.stderr)
        sys.exit(2)
    print(web_search(q))
