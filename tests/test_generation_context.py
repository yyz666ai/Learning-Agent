import json
import subprocess
import sys
from pathlib import Path

import pytest

from backend import codex_driver
from backend.learning_plan_personalizer import requires_authoritative_research
from backend.onboarding import OnboardingSubmission

ROOT = Path(__file__).resolve().parents[1]


def test_diagnosis_preloads_skill_without_old_course_profile(tmp_path):
    from backend.generation_context import prepare_generation_context
    (tmp_path / 'profile.md').write_text('OLD_GO_COURSE')
    prompt = prepare_generation_context(ROOT / 'workspace/dev', tmp_path, 'diagnosis', '前端 Vue 学过一些', False)
    assert '自适应建档与诊断' in prompt
    assert '前端 Vue 学过一些' in prompt
    assert 'OLD_GO_COURSE' not in prompt
    assert '不调用工具' in prompt


def submission(topic="Go", route="foundation_engineer"):
    return OnboardingSubmission.model_validate(dict(
        user_id="prepared_test", learning_mode="systematic", goal_route=route,
        level_claim="zero", topic={"type": "custom", "value": topic},
        session_minutes=40, teaching_preference="hands_on"))


def test_stable_known_curriculum_does_not_force_a_new_research_loop():
    assert not requires_authoritative_research(submission(), "knowledge_base")
    assert requires_authoritative_research(submission("NewFramework"), "skill_guided")
    assert requires_authoritative_research(submission("Go 1.27 新特性"), "knowledge_base")


def test_explicit_current_version_request_still_requires_research():
    assert requires_authoritative_research(submission(), "knowledge_base",
        intent_slots={"constraints": ["需要最新版本发布变化"]})


@pytest.mark.parametrize("constraint", ["只学习 Python 3.13 新特性", "用新框架 LangGraph 构建项目"])
def test_specific_versions_and_framework_constraints_need_sources(constraint):
    assert requires_authoritative_research(submission("Python"), "knowledge_base",
        intent_slots={"constraints": [constraint]})


def test_missing_topic_map_fails_before_model_call(tmp_path):
    import shutil
    from backend.generation_context import prepare_generation_context
    release = tmp_path / "release"
    shutil.copytree(ROOT / "workspace/dev/.codex", release / ".codex")
    user = tmp_path / "user"
    user.mkdir()
    (user / "learning-state.json").write_text('{"active_topic":"Go"}')
    with pytest.raises(FileNotFoundError):
        prepare_generation_context(release, user, "plan", "生成", False)


def test_prepared_context_contains_only_this_learner_and_exact_topic(tmp_path):
    from backend.generation_context import prepare_generation_context
    user = tmp_path / "u_test"
    user.mkdir()
    (user / "profile.json").write_text(json.dumps({"intent_slots": {
        "target_role": "普通前端", "tech_stack": ["Vue"], "constraints": ["不学习 AI"]}}))
    (user / "profile.md").write_text("已确认：零基础")
    (user / "learning-state.json").write_text(json.dumps({"active_topic": "Go"}))
    prompt = prepare_generation_context(ROOT / "workspace/dev", user, "plan", "生成大纲", False)
    assert "普通前端" in prompt and "不学习 AI" in prompt
    assert "learning-plan/SKILL.md" in prompt and "curriculum-quality.md" in prompt
    assert "curriculum/go/concept-map.json" in prompt
    assert "curriculum/python/concept-map.json" not in prompt
    assert "不调用工具" in prompt


def test_missing_required_skill_fails_before_model_call(tmp_path):
    from backend.generation_context import prepare_generation_context
    with pytest.raises(FileNotFoundError):
        prepare_generation_context(tmp_path, tmp_path, "plan", "生成", False)


@pytest.mark.parametrize("topic,has_go_reference", [("Go", True), ("Python", False), ("前端", False)])
def test_lesson_never_injects_unrelated_language_reference(tmp_path, topic, has_go_reference):
    from backend.generation_context import prepare_generation_context
    (tmp_path / "learning-state.json").write_text(json.dumps({"active_topic": topic}))
    prompt = prepare_generation_context(ROOT / "workspace/dev", tmp_path, "lesson", "讲解", False)
    assert ("【规则 .codex/skills/project-practice/references/go-cancellation.md】" in prompt) == has_go_reference


def test_generation_command_disables_reasoning_without_changing_user_config(tmp_path, monkeypatch):
    captured = {}
    user = codex_driver.ensure_user("prepared_test", tmp_path)
    config = user / ".codex-runtime/home/config.toml"
    config.write_text('model = "deepseek-v4-flash"\nmodel_reasoning_effort = "high"\n')
    original = config.read_bytes()

    def capture(cmd, message, release, env, timeout):
        captured.update(cmd=cmd, message=message, env=env)
        return subprocess.CompletedProcess(cmd, 0, json.dumps({"type": "item.completed",
            "item": {"type": "agent_message", "text": "# Go Plan"}}) + '\n{"type":"turn.completed"}', "")

    monkeypatch.setattr(codex_driver, "_capture_process", capture)
    assert codex_driver.chat("prepared_test", "生成", ROOT / "workspace/dev", server_root=tmp_path,
        generation="plan") == "# Go Plan"
    assert 'model_reasoning_effort="none"' in captured["cmd"]
    assert 'model_supports_reasoning_summaries=true' in captured["cmd"]
    assert not any("model_providers.deepseek" in arg for arg in captured["cmd"])
    assert "shell_tool" in captured["cmd"]
    assert captured["cmd"][captured["cmd"].index("--sandbox") + 1] == "read-only"
    assert captured["env"]["LEARNING_AGENT_PYTHON"] == sys.executable
    assert config.read_bytes() == original


def test_research_generation_keeps_tool_access(tmp_path, monkeypatch):
    commands = []
    def capture(cmd, *args):
        commands.extend(cmd)
        return subprocess.CompletedProcess(cmd, 0, '{"type":"item.completed","item":{"type":"agent_message","text":"plan"}}', "")
    monkeypatch.setattr(codex_driver, "_capture_process", capture)
    codex_driver.chat("prepared_test", "生成", ROOT / "workspace/dev", server_root=tmp_path,
        generation="plan", allow_research=True)
    assert "shell_tool" not in commands


@pytest.mark.parametrize("research", [False, True])
def test_official_deepseek_generation_uses_only_ephemeral_relay_credentials(tmp_path, monkeypatch, research):
    from contextlib import contextmanager
    from types import SimpleNamespace
    user = codex_driver.ensure_user("prepared_test", tmp_path)
    (user / ".codex-runtime/home/config.toml").write_text(
        'model_provider="deepseek"\n[model_providers.deepseek]\nbase_url="https://api.deepseek.com/v1"\nenv_key="DEEPSEEK_API_KEY"\n')
    monkeypatch.setenv("DEEPSEEK_API_KEY", "synthetic-real-key")
    state = []
    @contextmanager
    def relay(key, timeout, **options):
        assert key == "synthetic-real-key"
        assert options == {"allow_tools": research, "json_output": False}
        state.append("start")
        try:
            yield SimpleNamespace(base_url="http://127.0.0.1:12345/v1", token="ephemeral-test-token")
        finally:
            state.append("closed")
    monkeypatch.setattr(codex_driver, "deepseek_generation_transport", relay)
    def capture(cmd, message, release, env, timeout):
        assert 'model_providers.deepseek.base_url="http://127.0.0.1:12345/v1"' in cmd
        assert env["LEARNING_AGENT_RELAY_TOKEN"] == "ephemeral-test-token"
        assert env["DEEPSEEK_API_KEY"] == "synthetic-real-key"
        assert 'model_providers.deepseek.env_key="LEARNING_AGENT_RELAY_TOKEN"' in cmd
        assert "127.0.0.1" in env["NO_PROXY"] and "127.0.0.1" in env["no_proxy"]
        assert "synthetic-real-key" not in str(cmd)
        raise subprocess.TimeoutExpired(cmd, timeout)
    monkeypatch.setattr(codex_driver, "_capture_process", capture)
    result = codex_driver.chat("prepared_test", "生成", ROOT / "workspace/dev", server_root=tmp_path, generation="plan", allow_research=research)
    assert "超时" in result and state == ["start", "closed"]
    assert "ephemeral-test-token" not in (user / ".codex-runtime/home/config.toml").read_text()


def test_generation_returns_final_message_not_progress_commentary(tmp_path, monkeypatch):
    events = [{"type": "item.completed", "item": {"type": "agent_message", "text": text}}
              for text in ["我正在整理课程结构，准备输出。", "# Go Plan"]]
    events.append({"type": "turn.completed"})
    monkeypatch.setattr(codex_driver, "_capture_process", lambda *a:
                        subprocess.CompletedProcess([], 0, "\n".join(map(json.dumps, events)), ""))
    assert codex_driver.chat("prepared_test", "生成", ROOT / "workspace/dev",
                             server_root=tmp_path, generation="plan") == "# Go Plan"


@pytest.mark.parametrize("exit_code,terminal", [(1, "turn.failed"), (0, "turn.failed"), (0, "")])
def test_generation_never_accepts_partial_output_after_failure(tmp_path, monkeypatch, exit_code, terminal):
    events = [{"type": "item.completed", "item": {"type": "agent_message", "text": "# Go Plan"}}]
    if terminal:
        events.append({"type": terminal})
    monkeypatch.setattr(codex_driver, "_capture_process", lambda *a:
                        subprocess.CompletedProcess([], exit_code, "\n".join(map(json.dumps, events)), "private-error"))
    result = codex_driver.chat("prepared_test", "生成", ROOT / "workspace/dev",
                              server_root=tmp_path, generation="plan")
    assert result.startswith("[出错]")
    assert "Go Plan" not in result and "private-error" not in result


def test_generation_accepts_successful_reconnection_not_partial_failure(tmp_path, monkeypatch):
    events = [{"type": "error", "message": "Reconnecting... 1/5"},
              {"type": "item.completed", "item": {"type": "agent_message", "text": "# Go Plan"}},
              {"type": "turn.completed"}]
    monkeypatch.setattr(codex_driver, "_capture_process", lambda *a:
                        subprocess.CompletedProcess([], 0, "\n".join(map(json.dumps, events)), ""))
    assert codex_driver.chat("prepared_test", "生成", ROOT / "workspace/dev",
                            server_root=tmp_path, generation="plan") == "# Go Plan"
