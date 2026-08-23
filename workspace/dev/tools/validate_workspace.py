import json
import re
import sys
from pathlib import Path

import yaml
from jsonschema import ValidationError, validate

try:
    from tools.validate_curriculum import validate_maps
    from tools.workspace_utils import state_root
except ModuleNotFoundError:  # Support direct execution from tools/.
    from validate_curriculum import validate_maps
    from workspace_utils import state_root


REQUIRED_SKILLS = {
    "learning-intent-router",
    "adaptive-onboarding",
    "adaptive-lesson-flow",
    "learner-onboarding",
    "learning-plan",
    "codebase-learning-plan",
    "concept-teaching",
    "code-learning",
    "exercise-coach",
    "assignment-review",
    "spaced-review",
    "learning-progress",
    "environment-setup",
    "knowledge-curator",
    "practice-drill",
    "project-practice",
    "new-topic-research",
    "plan-revision",
    "visual-explainer",
    "progressive-code-teaching",
    "quiz-designer",
    "project-scaffolder",
    "lesson-revision",
}


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        raise ValueError("missing YAML frontmatter")
    value = yaml.safe_load(match.group(1))
    if not isinstance(value, dict):
        raise ValueError("frontmatter must be an object")
    return value


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _validate_state_documents(root: Path, errors: list[str]) -> None:
    schema_root = root / "memory/schemas"
    state_root_path = state_root(root)
    targets = [
        (root / "memory/templates/learning-state.json", "learning-state.schema.json"),
        (root / "memory/templates/mastery.json", "mastery.schema.json"),
        (root / "memory/templates/project-links.json", "project-links.schema.json"),
        (root / "memory/templates/review-schedule.json", "review-schedule.schema.json"),
    ]
    optional_targets = [
        (state_root_path / "learning-state.json", "learning-state.schema.json"),
        (state_root_path / "projects/project-links.json", "project-links.schema.json"),
        (state_root_path / "reviews/review-schedule.json", "review-schedule.schema.json"),
    ]
    targets.extend((path, schema) for path, schema in optional_targets if path.is_file())
    targets.extend(
        (path, "mastery.schema.json")
        for path in sorted((state_root_path / "mastery").glob("*.json"))
    )
    for document, schema_name in targets:
        try:
            validate(_load_json(document), _load_json(schema_root / schema_name))
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            errors.append(f"invalid state document {_rel(root, document)}: {exc}")


def _validate_skills(root: Path, errors: list[str]) -> int:
    skill_root = root / ".codex/skills"
    folders = sorted(path for path in skill_root.iterdir() if path.is_dir())
    actual = {path.name for path in folders}
    if actual != REQUIRED_SKILLS:
        errors.append(
            f"skill names differ: missing={sorted(REQUIRED_SKILLS - actual)}, "
            f"extra={sorted(actual - REQUIRED_SKILLS)}"
        )
    for folder in folders:
        try:
            metadata = _frontmatter(folder / "SKILL.md")
            if metadata.get("name") != folder.name:
                raise ValueError("frontmatter name does not match directory")
            description = metadata.get("description")
            if not isinstance(description, str) or not description.strip():
                raise ValueError("description is missing")
            evals = _load_json(folder / "evals/evals.json")
            if evals.get("skill_name") != folder.name or not evals.get("cases"):
                raise ValueError("eval metadata or cases are invalid")
            for case in evals["cases"]:
                if not case.get("id") or not case.get("expectations"):
                    raise ValueError("eval case is missing id or expectations")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"invalid skill {folder.name}: {exc}")
    return len(folders)


def _validate_journeys(root: Path, errors: list[str]) -> int:
    files = sorted((root / "evals/journeys").glob("*.json"))
    ids: list[str] = []
    for path in files:
        try:
            case = _load_json(path)
            journey_id = case.get("id")
            if not journey_id or not case.get("expected") or not case.get("forbidden"):
                raise ValueError("missing id, expected, or forbidden")
            ids.append(journey_id)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"invalid journey {path.name}: {exc}")
    if len(set(ids)) != len(ids):
        errors.append("journey IDs are not unique")
    return len(files)


def validate_workspace(root: Path) -> dict[str, object]:
    root = root.resolve()
    errors: list[str] = []

    try:
        curriculum = validate_maps(root / "curriculum")
        concept_count = int(curriculum["concept_count"])
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        errors.append(f"invalid curriculum: {exc}")
        concept_count = 0

    _validate_state_documents(root, errors)
    skill_count = _validate_skills(root, errors)
    journey_count = _validate_journeys(root, errors)

    state_root_path = state_root(root)
    for path in state_root_path.rglob("*"):
        if path.is_symlink():
            errors.append(f"symlink is forbidden in state root: {_rel(root, path)}")

    return {
        "errors": errors,
        "skill_count": skill_count,
        "journey_count": journey_count,
        "concept_count": concept_count,
    }


def main() -> int:
    report = validate_workspace(Path(__file__).resolve().parents[1])
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
