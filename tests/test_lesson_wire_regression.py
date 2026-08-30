import json
import pytest
from backend.lesson_generator import _repair_generated_wire_format


def test_display_page_type_echo_is_not_a_practice_kind():
    raw = json.dumps({"pages": [{"id":"end", "type":"mastery", "practice_kind":"mastery"}]})
    fixed = json.loads(_repair_generated_wire_format(raw, "Python"))
    assert fixed["pages"][0]["practice_kind"] is None


def test_unknown_practice_type_is_not_silently_reclassified():
    raw = json.dumps({"pages": [{"id":"task", "type":"practice", "practice_kind":"mastery"}]})
    assert json.loads(_repair_generated_wire_format(raw, "Python"))["pages"][0]["practice_kind"] == "mastery"
