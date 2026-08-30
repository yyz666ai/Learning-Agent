import subprocess
import sys


def test_plan_replay_and_confirmed_root_are_mutually_exclusive():
    result = subprocess.run([
        sys.executable, "tools/evaluate_lessons.py", "--case", "beginner",
        "--plan-response", "evals/runs/synthetic/call-1.json",
        "--from-confirmed", "evals/runs/synthetic/isolated",
    ], text=True, capture_output=True, timeout=10)
    assert result.returncode == 2
    assert "cannot be combined" in result.stderr
