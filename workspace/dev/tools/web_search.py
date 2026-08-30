#!/usr/bin/env python3
"""联网搜索：调 DeepSeek Responses API 的内置 web_search 工具，返回带引用的结果。

用法：python tools/web_search.py <查询词>
依赖：环境变量 DEEPSEEK_API_KEY（由桥服务 spawn 时注入）。
说明：DeepSeek 的 Responses API 原生支持 web_search（服务端执行），不需要额外搜索 API。
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request

BASE_URL = "https://api.deepseek.com/v1/responses"


def extract_search_result(data: dict) -> str:
    """Do not mistake an intermediate 'let me search' message for evidence."""
    if data.get("status") in {"incomplete", "failed", "cancelled", "queued", "in_progress"} or data.get("error"):
        return "[搜索失败] 搜索未完成；不能作为课程研究证据。"
    candidates = []
    for item in data.get("output", []):
        if item.get("type") != "message" or item.get("status") in {"incomplete", "in_progress"}:
            continue
        pieces = []
        for content in item.get("content", []):
            if content.get("type") != "output_text":
                continue
            text = str(content.get("text") or "").strip()
            links = []
            for annotation in content.get("annotations", []):
                citation = annotation.get("url_citation", annotation)
                url = citation.get("url", "")
                if isinstance(url, str) and re.match(r"https?://", url):
                    links.append(url)
            if text and (links or re.search(r"https?://\S+", text)):
                pieces.append(text + ("\n来源：" + "\n".join(links) if links else ""))
        if pieces:
            candidates.append("\n".join(pieces))
    return candidates[-1] if candidates else "[搜索失败] 未收到带来源的研究结果；不能把准备搜索的说明当作事实。"


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
        with urllib.request.urlopen(req, timeout=35) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        return f"[搜索失败] {e}"

    return extract_search_result(data)


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]).strip()
    if not q:
        print("用法: python tools/web_search.py <查询词>", file=sys.stderr)
        sys.exit(2)
    print(web_search(q))
