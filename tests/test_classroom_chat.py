from backend import main
from backend.user_memory import append_conversation_event, read_conversation_events


def test_mock_interview_is_explicit_and_survives_new_request(tmp_path, monkeypatch):
    from backend.classroom_chat import chat_mode
    assert chat_mode("请开始模拟面试，一次问一道", []) == "interview"
    assert chat_mode("我是为了面试学Python", []) == "learning"
    assert chat_mode("我的答案是变量可以重赋值", [{"role": "assistant", "chat_mode": "interview"}]) == "interview"
    assert chat_mode("结束模拟面试，给我讲讲变量", [{"role": "assistant", "chat_mode": "interview"}]) == "learning"


def test_interview_prompt_does_not_forbid_followup(monkeypatch):
    monkeypatch.setattr(main, "read_state", lambda _: {"state": {"profile_status": "confirmed"}})
    text = main.build_prompt("test", [], "开始模拟面试", mode="interview")
    assert "回答完不要再追加一道" not in text
    assert "一次只问一道" in text
    assert "参考答案" in text


def test_memory_read_excludes_failed_answer_and_preserves_reference(tmp_path):
    reference = {"quote": "x = 1", "page_id": "p1"}
    append_conversation_event(tmp_path, "test", role="user", content="为什么", lesson_id="go", reference=reference, chat_mode="interview")
    append_conversation_event(tmp_path, "test", role="assistant", content="half", lesson_id="go", status="failed")
    messages = read_conversation_events(tmp_path, "test", lesson_id="go")
    assert len(messages) == 1
    assert messages[0]["reference"] == reference
    assert messages[0]["chat_mode"] == "interview"
    assert read_conversation_events(tmp_path, "other") == []
