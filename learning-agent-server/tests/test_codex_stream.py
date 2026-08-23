from __future__ import annotations

import json

from backend.codex_driver import parse_codex_event


def test_parse_agent_message() -> None:
    line = json.dumps(
        {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": "你好"},
        }
    )

    assert parse_codex_event(line) == {
        "event": "message.delta",
        "data": {"text": "你好"},
    }


def test_parse_turn_started_as_status() -> None:
    line = json.dumps({"type": "turn.started"})

    assert parse_codex_event(line) == {
        "event": "status",
        "data": {"message": "已连接学习引擎"},
    }


def test_parse_tool_activity_as_safe_status() -> None:
    line = json.dumps(
        {
            "type": "item.started",
            "item": {"type": "command_execution", "command": "secret command"},
        }
    )

    assert parse_codex_event(line) == {
        "event": "status",
        "data": {"message": "正在准备学习内容"},
    }


def test_parse_invalid_json_is_none() -> None:
    assert parse_codex_event("not-json") is None


def test_parse_empty_agent_message_is_none() -> None:
    line = json.dumps(
        {"type": "item.completed", "item": {"type": "agent_message", "text": ""}}
    )

    assert parse_codex_event(line) is None
