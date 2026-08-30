"""Offline portability checks; Windows cases are simulations, not native runs."""
import importlib.util
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend import codex_driver, deployment_check


def runtime():
    assert importlib.util.find_spec('backend.platform_runtime'), 'shared platform runtime is missing'
    from backend import platform_runtime
    return platform_runtime


def test_native_codex_path_preserves_unicode_and_spaces(tmp_path, monkeypatch):
    module = runtime()
    binary = tmp_path / '学习 项目' / 'codex.exe'
    monkeypatch.setattr(module.shutil, 'which', lambda name: str(binary) if name == 'codex.exe' else None)
    assert module.codex_command(platform_name='win32') == [str(binary)]


@pytest.mark.parametrize('suffix', ['.cmd', '.ps1'])
@pytest.mark.parametrize('local_install', [False, True])
def test_windows_npm_shim_resolves_node_and_package_without_shell(tmp_path, monkeypatch, suffix, local_install):
    module = runtime()
    prefix = tmp_path / '中文 有空格'
    shim = prefix / ('node_modules/.bin' if local_install else '') / ('codex' + suffix)
    entry = prefix / 'node_modules/@openai/codex/bin/codex.js'
    entry.parent.mkdir(parents=True)
    entry.write_text('// synthetic npm installation', encoding='utf-8')
    node = tmp_path / 'Node JS/node.exe'
    monkeypatch.setattr(module.shutil, 'which', lambda name: str(shim) if name == 'codex' else str(node) if name == 'node' else None)
    assert module.codex_command(platform_name='win32') == [str(node), str(entry)]


def test_windows_shim_missing_node_reports_actionable_error(tmp_path, monkeypatch):
    module = runtime()
    monkeypatch.setattr(module.shutil, 'which', lambda name: str(tmp_path / 'codex.cmd') if name == 'codex' else None)
    with pytest.raises(RuntimeError, match='Node'):
        module.codex_command(platform_name='win32')


def test_missing_codex_reports_error_without_guessing_user_directories(monkeypatch):
    module = runtime()
    monkeypatch.setattr(module.shutil, 'which', lambda _: None)
    with pytest.raises(FileNotFoundError, match='Codex'):
        module.codex_command(platform_name='linux')


@pytest.mark.parametrize('method', ['chat', 'run_once_capture', 'stream_chat', 'run_once'])
def test_all_driver_paths_send_long_unicode_prompt_via_utf8_stdin(tmp_path, monkeypatch, capsys, method):
    assert hasattr(codex_driver, 'codex_command'), 'every driver path must use shared command resolver'
    prompt = '学习项目 空格与中文\n' * 14000
    child = ('import json,sys,os; text=sys.stdin.read(); '
             f'assert len(text)=={len(prompt)}; assert os.environ["DEEPSEEK_API_KEY"]=="fixture-key"; '
             'assert ".codex-runtime" in os.environ["CODEX_HOME"]; '
             'print(json.dumps({"type":"item.completed","item":{"type":"agent_message","text":"中文回复"}},ensure_ascii=False))')
    calls = []
    real_popen = subprocess.Popen
    def spawn(command, **kwargs):
        calls.append((command, kwargs))
        return real_popen(command, **kwargs)
    monkeypatch.setattr(codex_driver, 'codex_command', lambda: [sys.executable, '-c', child])
    monkeypatch.setattr(codex_driver.subprocess, 'Popen', spawn)
    monkeypatch.setattr(codex_driver, 'load_secrets', lambda _: {'DEEPSEEK_API_KEY': 'fixture-key'})
    release = tmp_path / '课件 发布'
    release.mkdir()
    result = getattr(codex_driver, method)('test', prompt, release, server_root=tmp_path, sandbox='read-only')
    if method == 'stream_chat':
        result = list(result)
        assert any(event.get('data', {}).get('text') == '中文回复' for event in result)
    elif method == 'chat':
        assert result == '中文回复'
    elif method == 'run_once_capture':
        assert result['exit_code'] == 0 and '中文回复' in result['output']
    else:
        assert result == 0 and '中文回复' in capsys.readouterr().out
    command, kwargs = calls[0]
    assert command[-1] == '-' and prompt not in command
    assert kwargs['encoding'] == 'utf-8'
    assert kwargs['stdin'] == subprocess.PIPE
    assert not kwargs.get('shell', False)
    assert command[command.index('--sandbox') + 1] == 'read-only'


@pytest.mark.parametrize('method', ['stream_chat', 'run_once'])
def test_streaming_paths_timeout_even_without_stdout_and_drain_stderr(tmp_path, monkeypatch, method):
    assert hasattr(codex_driver, 'codex_command'), 'shared resolver is required'
    child = 'import sys,time; sys.stderr.write("e"*200000); sys.stderr.flush(); sys.stdin.read(); time.sleep(10)'
    monkeypatch.setattr(codex_driver, 'codex_command', lambda: [sys.executable, '-c', child])
    monkeypatch.setattr(codex_driver, 'load_secrets', lambda _: {})
    started = time.monotonic()
    result = getattr(codex_driver, method)('test', '中文'*10000, tmp_path, server_root=tmp_path, timeout=0.2)
    if method == 'stream_chat':
        events = list(result)
        assert any(event['event'] == 'error' and '超时' in event['data']['message'] for event in events)
    else:
        assert result == 124
    assert time.monotonic() - started < 4


def test_deployment_uses_same_resolver_and_reports_nonzero_probe(tmp_path, monkeypatch, capsys):
    assert hasattr(deployment_check, 'codex_command'), 'deployment and driver must share resolver'
    monkeypatch.setattr(deployment_check, 'codex_command', lambda: ['node fixture', 'codex fixture.js'])
    commands = []
    def run(command, **kwargs):
        commands.append(command)
        return SimpleNamespace(returncode=7, stdout='codex 0.146.1', stderr='probe failed')
    monkeypatch.setattr(deployment_check.subprocess, 'run', run)
    assert deployment_check.main(server_root=tmp_path) != 0
    assert commands == [['node fixture', 'codex fixture.js', '--version']]


@pytest.mark.parametrize('failed_stage,code', [(0, 6), (1, 7), (2, 8)])
def test_startup_preserves_stage_error_and_port_without_shell(tmp_path, monkeypatch, failed_stage, code):
    assert importlib.util.find_spec('backend.startup'), 'shared startup entry point is missing'
    from backend import startup
    calls = []
    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=code if len(calls) - 1 == failed_stage else 0)
    monkeypatch.setattr(startup.subprocess, 'run', run)
    assert startup.main(['8899'], server_root=tmp_path) == code
    assert len(calls) == failed_stage + 1
    assert all(command[0] == sys.executable and not opts.get('shell', False) for command, opts in calls)
    if failed_stage == 2:
        assert calls[-1][0][-1] == '8899'


@pytest.mark.parametrize('port', ['0', '65536', 'abc', '8787 & echo unsafe'])
def test_invalid_port_is_rejected_before_startup_work(tmp_path, monkeypatch, port):
    assert importlib.util.find_spec('backend.startup'), 'shared startup entry point is missing'
    from backend import startup
    monkeypatch.setattr(startup.subprocess, 'run', lambda *a, **k: pytest.fail('invalid port launched a process'))
    with pytest.raises(SystemExit) as error:
        startup.main([port], server_root=tmp_path)
    assert error.value.code == 2


def test_headless_linux_returns_path_without_claiming_folder_opened(tmp_path, monkeypatch):
    module = runtime()
    monkeypatch.delenv('DISPLAY', raising=False)
    monkeypatch.delenv('WAYLAND_DISPLAY', raising=False)
    monkeypatch.setattr(module.subprocess, 'run', lambda *a, **k: pytest.fail('headless GUI launch'))
    result = module.open_folder(tmp_path, platform_name='linux')
    assert result['opened'] is False and result['path'] == str(tmp_path)


def test_windows_folder_open_uses_native_startfile_and_unicode_path(tmp_path, monkeypatch):
    module = runtime()
    opened = []
    monkeypatch.setattr(module.os, 'startfile', lambda path: opened.append(path), raising=False)
    assert module.open_folder(tmp_path, platform_name='win32')['opened'] is True
    assert opened == [str(tmp_path)]


@pytest.mark.parametrize('method', ['stream_chat', 'run_once'])
def test_stderr_flood_does_not_block_successful_stream(tmp_path, monkeypatch, method, capsys):
    child = ('import sys,json; sys.stderr.write("diagnostic"*50000); sys.stderr.flush(); '
             'sys.stdin.read(); print(json.dumps({"type":"item.completed",'
             '"item":{"type":"agent_message","text":"done"}}))')
    monkeypatch.setattr(codex_driver, 'codex_command', lambda: [sys.executable, '-c', child])
    monkeypatch.setattr(codex_driver, 'load_secrets', lambda _: {})
    result = getattr(codex_driver, method)('test', '中文'*20000, tmp_path, server_root=tmp_path, timeout=3)
    if method == 'stream_chat':
        events = list(result)
        assert events[-1]['event'] == 'message.completed'
        assert not any(event['event'] == 'error' for event in events)
    else:
        assert result == 0
        assert len(capsys.readouterr().err) <= 32 * 4096


@pytest.mark.skipif(sys.platform == 'win32', reason='POSIX wrapper tested natively; Windows has a separate launcher')
@pytest.mark.parametrize('venv_path', ['bin/python', 'Scripts/python.exe'])
def test_shell_wrapper_quotes_project_paths_and_propagates_port_and_error(tmp_path, venv_path):
    root = tmp_path / '学习 项目'
    root.mkdir()
    launcher = Path(__file__).resolve().parents[1] / 'run.sh'
    (root / 'run.sh').write_text(launcher.read_text(encoding='utf-8'), encoding='utf-8')
    python = root / '.venv' / venv_path
    python.parent.mkdir(parents=True)
    python.symlink_to(sys.executable)
    (root / 'backend').mkdir()
    (root / 'backend/startup.py').write_text(
        'import sys; print(sys.argv[1]); raise SystemExit(7)', encoding='utf-8')
    result = subprocess.run(['bash', str(root / 'run.sh'), '8899'], cwd=tmp_path,
                            capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 7 and result.stdout.strip() == '8899'


def test_windows_launcher_quotes_native_python_and_propagates_error_contract():
    # Static contract only: this does not execute cmd.exe on macOS/Linux.
    source = (Path(__file__).resolve().parents[1] / 'run.cmd').read_text(encoding='utf-8')
    assert 'cd /d "%~dp0"' in source
    assert '.venv\\Scripts\\python.exe' in source
    assert '"%LEARNING_AGENT_PYTHON%" -m backend.startup %*' in source
    assert 'set "LEARNING_AGENT_EXIT_CODE=%ERRORLEVEL%"' in source
    assert 'exit /b %LEARNING_AGENT_EXIT_CODE%' in source


def test_direct_driver_entrypoint_retains_usage_without_import_failure(tmp_path):
    driver = Path(__file__).resolve().parents[1] / 'backend/codex_driver.py'
    result = subprocess.run([sys.executable, str(driver)], cwd=tmp_path,
                            capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 2 and 'usage: codex_driver.py' in result.stderr
    assert 'ModuleNotFoundError' not in result.stderr


@pytest.mark.parametrize('platform_name', ['darwin', 'linux'])
def test_gui_failure_returns_honest_path_fallback(tmp_path, monkeypatch, platform_name):
    module = runtime()
    monkeypatch.setenv('DISPLAY', ':fixture')
    monkeypatch.setattr(module.shutil, 'which', lambda _: '/fixture/xdg-open')
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0])
    monkeypatch.setattr(module.subprocess, 'run', fail)
    result = module.open_folder(tmp_path, platform_name=platform_name)
    assert result['opened'] is False and result['path'] == str(tmp_path)


@pytest.mark.skipif(sys.platform == 'win32', reason='Real POSIX process tree test; Windows cleanup is simulated separately')
@pytest.mark.parametrize('method', ['chat', 'run_once_capture', 'stream_chat', 'run_once'])
@pytest.mark.parametrize('parent_exits', [False, True])
def test_timeout_kills_wrapper_and_actual_model_grandchild(tmp_path, monkeypatch, method, parent_exits):
    pidfile = tmp_path / 'grandchild.pid'
    child = 'import time; time.sleep(20)'
    wrapper = ('import subprocess,sys,time,pathlib; '
               f'p=subprocess.Popen([sys.executable,"-c",{child!r}]); '
               f'pathlib.Path({str(pidfile)!r}).write_text(str(p.pid)); '
               + ('sys.exit(0)' if parent_exits else 'sys.stdin.read(); time.sleep(20)'))
    processes = []
    real_popen = subprocess.Popen
    def spawn(command, **kwargs):
        proc = real_popen(command, **kwargs)
        processes.append(proc)
        return proc
    monkeypatch.setattr(codex_driver, 'codex_command', lambda: [sys.executable, '-c', wrapper])
    monkeypatch.setattr(codex_driver, 'load_secrets', lambda _: {})
    monkeypatch.setattr(codex_driver.subprocess, 'Popen', spawn)
    try:
        started = time.monotonic()
        result = getattr(codex_driver, method)('tree', '中文', tmp_path, server_root=tmp_path, timeout=0.3)
        if method == 'stream_chat':
            assert any(event['event'] == 'error' for event in list(result))
        elif method == 'run_once_capture':
            assert result['timed_out'] is True
        elif method == 'run_once':
            assert result == 124
        else:
            assert '超时' in result
        assert time.monotonic() - started < 4
        pid = int(pidfile.read_text())
        deadline = time.monotonic() + 1
        alive = True
        while alive and time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
                # A killed orphan can briefly remain a zombie pending system reap.
                with real_popen(['ps', '-o', 'stat=', '-p', str(pid)], stdout=subprocess.PIPE, text=True) as check:
                    state = check.communicate(timeout=1)[0].strip()
                alive = bool(state) and not state.startswith('Z')
            except ProcessLookupError:
                alive = False
            if alive:
                time.sleep(0.02)
        assert not alive, 'model grandchild survives wrapper timeout'
        assert processes[0].poll() is not None
        assert processes[0].stdout.closed and processes[0].stderr.closed
    finally:
        if pidfile.exists():
            try:
                os.kill(int(pidfile.read_text()), signal.SIGKILL)
            except ProcessLookupError:
                pass


def test_windows_cleanup_uses_new_group_and_exact_child_tree_without_shell(monkeypatch):
    monkeypatch.setattr(codex_driver.subprocess, 'CREATE_NEW_PROCESS_GROUP', 512, raising=False)
    assert codex_driver._process_group_options('win32') == {'creationflags': 512}
    commands = []
    waits = []
    def run(command, **kwargs):
        commands.append((command, kwargs))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(codex_driver.subprocess, 'run', run)
    proc = SimpleNamespace(pid=12345, poll=lambda: 1, wait=lambda **kwargs: waits.append(kwargs))
    codex_driver._stop_process_tree(proc, 'win32')
    assert commands[0][0] == ['taskkill', '/PID', '12345', '/T', '/F']
    assert not commands[0][1].get('shell', False)
    assert commands[0][1]['timeout'] == 2 and waits == [{'timeout': 2}]


@pytest.mark.parametrize('method', ['chat', 'run_once_capture', 'stream_chat', 'run_once'])
def test_deadline_is_not_blocked_when_process_never_reads_long_stdin(tmp_path, monkeypatch, method):
    monkeypatch.setattr(codex_driver, 'codex_command', lambda: [sys.executable, '-c', 'import time; time.sleep(20)'])
    monkeypatch.setattr(codex_driver, 'load_secrets', lambda _: {})
    started = time.monotonic()
    result = getattr(codex_driver, method)('stdin', '中文'*200000, tmp_path, server_root=tmp_path, timeout=0.2)
    if method == 'stream_chat':
        assert any(event['event'] == 'error' for event in list(result))
    elif method == 'run_once_capture':
        assert result['timed_out'] is True
    elif method == 'run_once':
        assert result == 124
    else:
        assert '超时' in result
    assert time.monotonic() - started < 4
