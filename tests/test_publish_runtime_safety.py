import json
import socket
from pathlib import Path

from backend import publish, startup


def setup_release(tmp_path, monkeypatch):
    dev = tmp_path / 'dev'
    dev.mkdir()
    (dev / 'manifest.json').write_text(json.dumps({'publishable': ['AGENTS.md', 'manifest.json']}))
    (dev / 'AGENTS.md').write_text('first')
    current = tmp_path / 'releases/current'
    monkeypatch.setattr(publish, 'DEV', dev)
    monkeypatch.setattr(publish, 'CURRENT', current)
    return dev, current


def test_republish_keeps_running_codex_working_directory(tmp_path, monkeypatch):
    dev, current = setup_release(tmp_path, monkeypatch)
    publish.publish()
    inode = current.stat().st_ino
    monkeypatch.chdir(current)
    (dev / 'AGENTS.md').write_text('second')
    publish.publish()
    assert Path.cwd() == current
    assert current.stat().st_ino == inode
    assert (current / 'AGENTS.md').read_text() == 'second'


def test_failed_staging_preserves_previous_release(tmp_path, monkeypatch):
    dev, current = setup_release(tmp_path, monkeypatch)
    publish.publish()
    def fail(*a, **k):
        raise OSError('synthetic copy failure')
    monkeypatch.setattr(publish.shutil, 'copy2', fail)
    import pytest
    with pytest.raises(OSError):
        publish.publish()
    assert (current / 'AGENTS.md').read_text() == 'first'


def test_occupied_port_never_publishes_or_starts_another_server(tmp_path, monkeypatch):
    calls = []
    from types import SimpleNamespace
    monkeypatch.setattr(startup.subprocess, 'run', lambda *a, **k: (calls.append(a) or SimpleNamespace(returncode=0)))
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        listener.listen()
        assert startup.main([str(listener.getsockname()[1])], server_root=tmp_path) != 0
    assert calls == []


def test_restart_port_probe_allows_recently_closed_connections(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import sys
    import pytest
    if sys.platform == 'win32':
        pytest.skip('POSIX TIME_WAIT binding semantics')
    monkeypatch.setattr(startup.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=0))
    with socket.socket() as listener, socket.socket() as client:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
        listener.listen()
        client.connect(('127.0.0.1', port))
        connection, _ = listener.accept()
        connection.close()  # server-side TIME_WAIT
        assert client.recv(1) == b''
    assert startup.main([str(port)], server_root=tmp_path) == 0
