import json
import pytest
from fastapi import HTTPException
from backend import main as api
from backend.user_memory import persist_intent_decision, read_intent_state


def question():
    return {"action": "clarify", "confidence": .8, "summary": "问目标", "slots": {"topic": "Go"},
            "question": {"prompt": "想做什么？", "slot": "desired_outcome", "options": []}}


def test_refresh_recovers_history_and_duplicate_request_replays(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "SERVER_ROOT", tmp_path)
    monkeypatch.setattr(api, "latest_release", lambda: tmp_path)
    monkeypatch.setattr(api, "_intent_skill_text", lambda _: "test")
    persist_intent_decision(tmp_path, "test", message="我想学Go，初学", decision=question(), session_id="s1")
    prompts = []
    def chat(prompt, skill):
        prompts.append(prompt)
        return json.dumps(question(), ensure_ascii=False)
    monkeypatch.setattr(api, "intent_chat", chat)
    request = api.IntentRequest(user_id="test", message="还不确定目标", session_id="s1", revision=1, request_id="r1")
    first = api.onboarding_intent(request)
    assert "我想学Go，初学" in prompts[0]
    assert api.onboarding_intent(request) == first
    assert len(prompts) == 1
    assert first["revision"] == 2
    with pytest.raises(HTTPException) as err:
        api.onboarding_intent(api.IntentRequest(user_id="test", message="旧标签页", session_id="s1", revision=1, request_id="r2"))
    assert err.value.status_code == 409


def test_material_excerpt_is_ingested_once_without_second_paste(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "SERVER_ROOT", tmp_path)
    monkeypatch.setattr(api, "latest_release", lambda: tmp_path)
    monkeypatch.setattr(api, "_intent_skill_text", lambda _: "test")
    text = "面试Java后端，初学，Spring。题目：Spring如何解决循环依赖？"
    decision = {"action": "interview_bank_intake", "confidence": .9, "summary": "收到题目",
                "slots": {"topic": "Java", "target_role": "Java后端", "tech_stack": ["Spring"],
                          "interview_question_source": "has_questions"},
                "material_text": "Spring如何解决循环依赖？"}
    monkeypatch.setattr(api, "intent_chat", lambda *_: json.dumps(decision, ensure_ascii=False))
    request = api.IntentRequest(user_id="test", message=text, session_id="s1", reset_session=True, request_id="r1")
    result = api.onboarding_intent(request)
    assert result["slots"]["interview_question_count"] == 1
    assert api.onboarding_intent(request) == result
    assert len(api.InterviewBankStore(tmp_path).list_questions("test")) == 1
    assert read_intent_state(tmp_path, "test")["history"][0]["content"] == text
