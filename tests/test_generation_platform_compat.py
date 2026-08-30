"""Compatibility regressions for the supported Python and shell platforms."""
import builtins
import importlib.util
from pathlib import Path

from backend.learning_plan_personalizer import build_plan_prompt
from backend.onboarding import OnboardingSubmission


ROOT = Path(__file__).resolve().parents[1]


def test_driver_import_falls_back_when_stdlib_tomllib_is_unavailable(monkeypatch):
    try:
        import tomllib as parser
    except ModuleNotFoundError:
        import tomli as parser
    original_import = builtins.__import__

    def python310_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "tomllib":
            raise ModuleNotFoundError("No module named 'tomllib'", name="tomllib")
        if name == "tomli":
            return parser
        return original_import(name, globals, locals, fromlist, level)

    spec = importlib.util.spec_from_file_location(
        "backend._driver_python310_test", ROOT / "backend/codex_driver.py"
    )
    module = importlib.util.module_from_spec(spec)
    with monkeypatch.context() as scoped:
        scoped.setattr(builtins, "__import__", python310_import)
        spec.loader.exec_module(module)
    assert module.tomllib.loads('model_provider = "deepseek"') == {
        "model_provider": "deepseek"
    }


def test_python310_installs_tomli_backport():
    dependencies = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert 'tomli>=2,<3; python_version < "3.11"' in dependencies.splitlines()


def test_research_prompt_supplies_native_powershell_and_posix_commands():
    selected = OnboardingSubmission.model_validate({
        "user_id": "platform_test", "learning_mode": "systematic",
        "goal_route": "foundation_engineer", "level_claim": "zero",
        "topic": {"type": "custom", "value": "NewFramework"},
        "session_minutes": 40, "teaching_preference": "hands_on",
    })
    prompt = build_plan_prompt(selected, "", research_required=True)
    query = '"NewFramework official documentation getting started"'
    assert f'"$LEARNING_AGENT_PYTHON" tools/web_search.py {query}' in prompt
    assert f'& $env:LEARNING_AGENT_PYTHON tools/web_search.py {query}' in prompt
    assert "Windows PowerShell" in prompt
