from __future__ import annotations

import json

from backend import llm


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self) -> bytes:
        return json.dumps({"choices": [{"message": {"content": '{"ok":true}'}}]}).encode()


def test_fast_json_call_explicitly_disables_deepseek_thinking(monkeypatch) -> None:
    captured: dict = {}

    def fake_urlopen(request, timeout):
        captured.update(json.loads(request.data.decode("utf-8")))
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr(llm, "load_api_key", lambda: "test-key")
    monkeypatch.setattr(llm.urllib.request, "urlopen", fake_urlopen)

    result = llm.chat(
        "Return JSON",
        model="deepseek-v4-flash",
        max_tokens=700,
        thinking=False,
        json_object=True,
        timeout=30,
    )

    assert result == '{"ok":true}'
    assert captured["thinking"] == {"type": "disabled"}
    assert captured["response_format"] == {"type": "json_object"}
    assert captured["timeout"] == 30
