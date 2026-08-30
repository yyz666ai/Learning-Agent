import pytest
from backend import llm


def test_strict_intent_transport_does_not_turn_failure_into_model_text(monkeypatch):
    monkeypatch.setattr(llm, "load_api_key", lambda: "test-only")
    calls = []
    def fail(*args, **kwargs):
        calls.append(1)
        raise TimeoutError("network unavailable")
    monkeypatch.setattr(llm.urllib.request, "urlopen", fail)
    with pytest.raises(RuntimeError, match="unavailable"):
        llm.chat("test", raise_errors=True)
    assert len(calls) == 1


def test_strict_missing_key_fails_before_network(monkeypatch):
    monkeypatch.setattr(llm, "load_api_key", lambda: None)
    with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
        llm.chat("test", raise_errors=True)
