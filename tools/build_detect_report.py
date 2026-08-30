"""Build a self-contained, offline report from explicit sanitized evaluation evidence.

This is a renderer, not a grader. It does not invent test outcomes or human approval.
Run: python tools/build_detect_report.py batch.json output-directory
Existing batches cannot be overwritten; use a new output directory for a retest.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

STATUSES = {"PASS", "FAIL", "UNVERIFIABLE", "BLOCKED"}
TEMPLATE = Path(__file__).with_name("detect_report.html")


def validate_batch(batch: dict) -> None:
    # Validate even extra fields: Python's JSON decoder accepts NaN but browsers do not.
    json.dumps(batch, allow_nan=False)
    if not isinstance(batch.get("limitations", []), list) or any(not isinstance(item, str) for item in batch.get("limitations", [])):
        raise ValueError("limitations must be a list of strings")
    for name in ("batch_id", "baseline", "candidate", "generated_at"):
        if not isinstance(batch.get(name), str) or not batch[name]:
            raise ValueError(f"Missing {name}")
    if not isinstance(batch.get("cases"), list) or not batch["cases"]:
        raise ValueError("cases must be nonempty")
    ids, gt_ids, run_ids = set(), set(), set()
    for case in batch["cases"]:
        for name in ("id", "gt_id", "title", "module", "platform", "risk", "input", "expected"):
            if not isinstance(case.get(name), str) or not case[name]:
                raise ValueError(f"Missing case {name}")
        if case["id"] in ids or case["gt_id"] in gt_ids:
            raise ValueError("case and GT ids must be unique")
        ids.add(case["id"])
        gt_ids.add(case["gt_id"])
        if not case.get("runs"):
            raise ValueError("Missing runs: record UNVERIFIABLE explicitly")
        for run in case["runs"]:
            if not run.get("id") or run["id"] in run_ids:
                raise ValueError("run ids must be unique")
            run_ids.add(run["id"])
            if run.get("status") not in STATUSES:
                raise ValueError("Invalid status")
            for name in ("actual", "rationale"):
                if not isinstance(run.get(name), str) or not run[name]:
                    raise ValueError(f"Missing run {name}")
            if run["status"] in {"PASS", "FAIL"} and (not isinstance(run.get("evidence"), str) or not run["evidence"].strip()):
                raise ValueError("PASS/FAIL requires evidence")
            seconds = run.get("seconds")
            if seconds is not None and (isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds < 0):
                raise ValueError("seconds must be nonnegative or null")


def artifacts(batch: dict) -> dict:
    cases, gt, runs, scores = [], [], [], []
    for case in batch["cases"]:
        cases.append({k: v for k, v in case.items() if k not in {"runs", "expected"}})
        gt.append({"id": case["gt_id"], "case_id": case["id"], "expected": case["expected"]})
        for run in case["runs"]:
            runs.append({**run, "case_id": case["id"], "batch_id": batch["batch_id"]})
            scores.append({"case_id": case["id"], "gt_id": case["gt_id"], "run_id": run["id"],
                "judgment": run["status"], "rationale": run["rationale"], "evidence": run.get("evidence", ""),
                "grader": "evidence-review-v1", "review_status": "pending", "valid_score": None})
    return {"cases": cases, "ground_truth": gt, "runs": runs, "scores": scores}


def build_report(batch: dict, output: Path) -> Path:
    validate_batch(batch)
    output = Path(output)
    # Evidence and its rendered view form one immutable batch.
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Use a new batch directory; refusing to overwrite {output}")
    output.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(batch, ensure_ascii=False, indent=2, allow_nan=False)
    (output / "report_data.json").write_text(serialized + "\n", encoding="utf-8")
    for name, rows in artifacts(batch).items():
        (output / f"{name}.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    # Escape HTML parser delimiters even though JSON is in an inert script element.
    embedded = serialized.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    html = TEMPLATE.read_text(encoding="utf-8").replace("__BATCH_JSON__", embedded)
    destination = output / "index.html"
    destination.write_text(html, encoding="utf-8")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(build_report(json.loads(args.batch.read_text(encoding="utf-8")), args.output))
