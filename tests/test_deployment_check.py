from __future__ import annotations

from pathlib import Path

from backend.deployment_check import check_local_deployment, parse_codex_version


def required_tree(root: Path) -> None:
    for relative in (
        "workspace/dev/AGENTS.md",
        "workspace/dev/.codex/skills/learning-plan/SKILL.md",
        "workspace/dev/.codex/skills/adaptive-lesson-flow/SKILL.md",
        "workspace/dev/tools/web_search.py",
        "templates/codex-home-config.toml",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ready\n", encoding="utf-8")
    (root / ".secrets.env").write_text("DEEPSEEK_API_KEY=sk-test\n", encoding="utf-8")


def test_codex_version_parser_requires_responses_compatible_release() -> None:
    assert parse_codex_version("codex-cli 0.146.1") == (0, 146, 1)
    assert parse_codex_version("codex 1.2.3") == (1, 2, 3)
    assert parse_codex_version("unknown") is None


def test_deployment_check_reports_old_codex_and_missing_runtime_files(tmp_path: Path) -> None:
    issues = check_local_deployment(tmp_path, codex_version_text="codex-cli 0.120.0")

    assert any("Codex 0.146.0" in issue for issue in issues)
    assert any(".secrets.env" in issue for issue in issues)
    assert any("learning-plan/SKILL.md" in issue for issue in issues)


def test_deployment_check_accepts_complete_project_local_configuration(tmp_path: Path) -> None:
    required_tree(tmp_path)

    issues = check_local_deployment(tmp_path, codex_version_text="codex-cli 0.146.1")

    assert issues == []
