import argparse
import json
from pathlib import Path

try:
    from tools.workspace_utils import state_root
except ModuleNotFoundError:  # Support direct execution from tools/.
    from workspace_utils import state_root


def _load_cases(root: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted((root / ".codex/skills").glob("*/evals/evals.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for case in data.get("cases", []):
            case_id = case.get("id")
            expected = case.get("expectations")
            if not case_id or not expected:
                raise ValueError(f"{path}: case missing id or expectations")
            rows.append(
                {
                    "id": f"skill:{data['skill_name']}:{case_id}",
                    "prompt": case.get("prompt", ""),
                    "expected": expected,
                    "forbidden": case.get("forbidden", []),
                }
            )
    for path in sorted((root / "evals/journeys").glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        if not case.get("id") or not case.get("expected"):
            raise ValueError(f"{path}: journey missing id or expectations")
        rows.append(case)
    ids = [str(row["id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("behavior eval IDs must be unique")
    return rows


def _cell(value: object) -> str:
    if isinstance(value, list):
        value = "; ".join(str(item) for item in value)
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def write_sheet(root: Path, output: Path) -> int:
    root = root.resolve()
    output = output.resolve()
    user_data = state_root(root)
    if output == user_data or user_data in output.parents:
        raise ValueError("behavior eval sheet must not be written into the state root")
    cases = _load_cases(root)
    lines = [
        "# Learning Agent 行为评估表",
        "",
        "逐项在 Codex 中执行提示词，填写实际结果并勾选通过或失败。本工具不会调用模型。",
        "",
        "| ID | 提示词 | 预期行为 | 禁止行为 | 实际结果 | 通过/失败 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for case in cases:
        lines.append(
            "| "
            + " | ".join(
                [
                    _cell(case["id"]),
                    _cell(case.get("prompt", "")),
                    _cell(case.get("expected", [])),
                    _cell(case.get("forbidden", [])),
                    "",
                    "[ ] 通过 / [ ] 失败",
                ]
            )
            + " |"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(cases)


def main() -> int:
    parser = argparse.ArgumentParser(description="生成手工行为评估表，不调用模型。")
    parser.add_argument("output", type=Path, help="Markdown 评估表输出路径")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    count = write_sheet(root, args.output)
    print(f"已生成 {count} 条行为评估：{args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
