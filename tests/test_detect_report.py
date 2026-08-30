"""The public report must preserve evidence and never turn missing data into passes."""
import json
from pathlib import Path

import pytest

from tools.build_detect_report import build_report, validate_batch


def sample():
    return {
        "batch_id": "local-test", "baseline": "abc", "candidate": "diff:123",
        "generated_at": "2026-08-30", "limitations": ["Windows 实机未测"],
        "cases": [{"id": "C1", "gt_id": "G1", "title": "输入长中文",
                   "module": "platform", "platform": "Windows 模拟", "risk": "high",
                   "input": "中文", "expected": "UTF-8 stdin", "fix": "统一入口",
                   "runs": [{"id": "r1", "status": "PASS", "actual": "round trip OK",
                             "evidence": "tests/test_platform_runtime.py", "seconds": 0.4,
                             "rationale": "逐字一致"}]}],
    }


@pytest.mark.parametrize("evidence", ["", "   \n\t", {"opaque": True}, 123])
def test_missing_evidence_cannot_pass(evidence):
    batch = sample()
    batch["cases"][0]["runs"][0]["evidence"] = evidence
    with pytest.raises(ValueError, match="evidence"):
        validate_batch(batch)


def test_gt_one_to_one_and_run_ids_unique():
    batch = sample()
    batch["cases"].append({**batch["cases"][0], "id": "C2"})
    with pytest.raises(ValueError, match="unique"):
        validate_batch(batch)


def test_preserves_first_failure_and_no_forged_review(tmp_path):
    batch = sample()
    batch["cases"][0]["runs"].insert(0, {"id": "r0", "status": "FAIL", "actual": "broken",
        "evidence": "baseline probe", "seconds": None, "rationale": "blocked long request"})
    build_report(batch, tmp_path)
    data = json.loads((tmp_path / "report_data.json").read_text())
    assert [r["status"] for r in data["cases"][0]["runs"]] == ["FAIL", "PASS"]
    scores = [json.loads(line) for line in (tmp_path / "scores.jsonl").read_text().splitlines()]
    assert all(s["review_status"] == "pending" and s["valid_score"] is None for s in scores)
    assert (tmp_path / "cases.jsonl").exists() and (tmp_path / "ground_truth.jsonl").exists()


def test_unknown_has_no_elapsed_or_numeric_score_and_html_is_offline_safe(tmp_path):
    batch = sample()
    run = batch["cases"][0]["runs"][0]
    run.update(status="UNVERIFIABLE", evidence="", seconds=None, actual="未执行 </script><script>alert(1)</script>")
    build_report(batch, tmp_path)
    html = (tmp_path / "index.html").read_text()
    assert "</script><script>alert(1)" not in html
    assert "\\u003c/script" in html
    assert "fetch(" not in html and 'src="http' not in html
    assert "textContent" in html and 'id="search"' in html
    assert 'id="export-review"' in html and "localStorage" in html


def test_invalid_status_or_negative_duration_rejected():
    batch = sample()
    batch["cases"][0]["runs"][0]["seconds"] = -1
    with pytest.raises(ValueError, match="seconds"):
        validate_batch(batch)


def test_refuses_silent_overwrite_of_an_existing_evidence_batch(tmp_path):
    build_report(sample(), tmp_path)
    with pytest.raises(FileExistsError):
        build_report(sample(), tmp_path)


@pytest.mark.parametrize("field,value", [("limitations", {}), ("limitations", [3]), ("extra", float('nan'))])
def test_bad_render_data_rejected_before_writing(tmp_path, field, value):
    batch = sample()
    batch[field] = value
    with pytest.raises(ValueError):
        build_report(batch, tmp_path)
    assert not list(tmp_path.iterdir())
