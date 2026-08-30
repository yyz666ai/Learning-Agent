from __future__ import annotations

import json
import http.client
import socket
import threading
import time
from urllib.parse import urlsplit

import httpx
import pytest

from backend import deepseek_transport


def post(*args, **kwargs):
    return httpx.post(*args, trust_env=False, **kwargs)


def relay(handler, timeout=2, **options):
    return deepseek_transport.deepseek_generation_transport(
        "real-secret", timeout, **options, _client_factory=lambda **kw: httpx.Client(
            transport=httpx.MockTransport(handler), **kw
        )
    )


def test_upstream_read_uses_invocation_deadline_not_arbitrary_30_seconds():
    def factory(**options):
        assert options["timeout"].read == 120
        assert options["timeout"].connect <= 10
        return httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200)), **options)
    with deepseek_transport.deepseek_generation_transport("test-key", 120, _client_factory=factory):
        pass


@pytest.mark.parametrize("allow_tools,json_output", [(False, False), (False, True), (True, False)])
def test_generation_output_contract(allow_tools, json_output):
    payloads = []
    def upstream(request):
        payloads.append(json.loads(request.content))
        return httpx.Response(200, json={})
    with relay(upstream, allow_tools=allow_tools, json_output=json_output) as endpoint:
        post(endpoint.base_url + "/responses", headers={"Authorization": "Bearer " + endpoint.token},
             json={"tools": [{"type": "function", "name": "update_plan"}], "tool_choice": "auto"})
    payload = payloads[0]
    assert payload["tools"] == ([{"type": "function", "name": "update_plan"}] if allow_tools else [])
    assert payload["tool_choice"] == ("auto" if allow_tools else "none")
    if json_output:
        assert payload["text"]["format"] == {"type": "json_object"}
    else:
        assert "text" not in payload


def test_forwards_payload_without_codex_fingerprints():
    requests = []

    def upstream(request):
        requests.append(request)
        return httpx.Response(200, json={"output": "unchanged"})

    with relay(upstream) as endpoint:
        assert endpoint.base_url.startswith("http://127.0.0.1:")
        assert endpoint.base_url.endswith("/v1")
        assert endpoint.token != "real-secret"
        response = post(endpoint.base_url + "/responses", headers={
            "Authorization": "Bearer " + endpoint.token,
            "User-Agent": "codex_cli_rs/1.0",
            "X-Codex-Turn-Metadata": "{}",
            "Originator": "codex_cli_rs",
        }, json={"input": "hello", "client_metadata": {}, "reasoning": {"effort": "high"}})
        assert response.json() == {"output": "unchanged"}
    request = requests[0]
    assert str(request.url) == "https://api.deepseek.com/v1/responses"
    assert request.headers["authorization"] == "Bearer real-secret"
    assert "codex" not in request.headers["user-agent"].lower()
    assert "x-codex-turn-metadata" not in request.headers
    assert "originator" not in request.headers
    assert json.loads(request.content) == {"input": "hello", "reasoning": {"effort": "none"}}


@pytest.mark.parametrize("authorization", [None, "Bearer wrong"])
def test_rejects_missing_or_wrong_token(authorization):
    def forbidden(request):
        pytest.fail("unauthorized request reached upstream")

    with relay(forbidden) as endpoint:
        headers = {} if authorization is None else {"Authorization": authorization}
        assert post(endpoint.base_url + "/responses", headers=headers, json={}).status_code == 401


@pytest.mark.parametrize("path", ["/models", "/responses?x=1", "/responses/extra"])
def test_rejects_other_paths(path):
    with relay(lambda r: pytest.fail("unexpected upstream request")) as endpoint:
        assert post(endpoint.base_url + path, headers={
            "Authorization": "Bearer " + endpoint.token
        }, json={}).status_code == 404


def test_preserves_sse_and_upstream_error():
    sse = b'event: response.completed\ndata: {"output": "hello"}\n\n'
    for status, content, content_type in [(200, sse, "text/event-stream"), (429, b'{"error":"busy"}', "application/json")]:
        with relay(lambda r: httpx.Response(status, content=content, headers={"Content-Type": content_type})) as endpoint:
            response = post(endpoint.base_url + "/responses", headers={"Authorization": "Bearer " + endpoint.token}, json={"stream": True})
            assert response.status_code == status
            assert response.content == content
            assert response.headers["content-type"] == content_type


def test_redirect_is_not_followed():
    requests = []
    def upstream(request):
        requests.append(request)
        return httpx.Response(307, headers={"Location": "https://evil.example/steal"})
    with relay(upstream) as endpoint:
        response = post(endpoint.base_url + "/responses", headers={"Authorization": "Bearer " + endpoint.token}, json={})
        assert response.status_code == 502
    assert len(requests) == 1


def test_cleanup_closes_listener_and_does_not_log_secrets(capsys):
    with relay(lambda r: httpx.Response(200, json={})) as endpoint:
        url = endpoint.base_url + "/responses"
        post(url, headers={"Authorization": "Bearer " + endpoint.token}, json={"input": "private-prompt"})
    with pytest.raises(httpx.ConnectError):
        post(url, timeout=0.3)
    captured = capsys.readouterr()
    assert not captured.out and not captured.err


def test_broken_upstream_stream_does_not_report_clean_completion():
    class Broken(httpx.SyncByteStream):
        def __iter__(self):
            yield b"event: response.created\ndata: {}\n\n"
            raise httpx.ReadError("private-upstream-failure")
    with relay(lambda r: httpx.Response(200, stream=Broken())) as endpoint:
        with pytest.raises(httpx.RemoteProtocolError):
            post(endpoint.base_url + "/responses", headers={"Authorization": "Bearer " + endpoint.token}, json={})


@pytest.mark.parametrize("body", [b"invalid", b"[]"])
def test_rejects_malformed_payload(body):
    with relay(lambda r: pytest.fail("unexpected upstream request")) as endpoint:
        response = post(endpoint.base_url + "/responses", headers={"Authorization": "Bearer " + endpoint.token}, content=body)
        assert response.status_code == 400


@pytest.mark.parametrize("headers, status", [
    ({"Content-Length": str(8 * 1024 * 1024 + 1)}, 413),
    ({"Content-Length": "-1"}, 413),
    ({"Content-Length": "bad"}, 400),
    ({"Transfer-Encoding": "chunked"}, 400),
])
def test_rejects_unbounded_body_before_reading(headers, status):
    with relay(lambda r: pytest.fail("unexpected upstream request")) as endpoint:
        address = urlsplit(endpoint.base_url)
        connection = http.client.HTTPConnection(address.hostname, address.port, timeout=1)
        connection.request("POST", "/v1/responses", headers={
            "Authorization": "Bearer " + endpoint.token, **headers,
        })
        assert connection.getresponse().status == status
        connection.close()


def test_network_failure_is_safe_gateway_error(capsys):
    def upstream(request):
        raise httpx.ConnectError("real-secret private-prompt")
    with relay(upstream) as endpoint:
        response = post(endpoint.base_url + "/responses", headers={"Authorization": "Bearer " + endpoint.token}, json={})
        assert response.status_code == 502
        assert not response.content
    assert not capsys.readouterr().err


def test_deadline_closes_slow_client():
    with relay(lambda r: pytest.fail("unexpected upstream request"), timeout=0.15) as endpoint:
        address = urlsplit(endpoint.base_url)
        with socket.create_connection((address.hostname, address.port), timeout=1) as connection:
            connection.sendall(b"POST /v1/responses HTTP/1.1\r\n")
            started = time.monotonic()
            assert connection.recv(1024) == b""
            assert time.monotonic() - started < 1


def test_context_exit_cancels_active_upstream_and_downstream():
    entered = threading.Event()
    closed = threading.Event()
    errors = []

    class Waiting(httpx.SyncByteStream):
        def __iter__(self):
            yield b"data: start\n\n"
            entered.set()
            closed.wait(2)
        def close(self):
            closed.set()

    with relay(lambda r: httpx.Response(200, stream=Waiting())) as endpoint:
        def receive():
            try:
                post(endpoint.base_url + "/responses", headers={"Authorization": "Bearer " + endpoint.token}, json={})
            except httpx.HTTPError as error:
                errors.append(error)
        reader = threading.Thread(target=receive)
        reader.start()
        assert entered.wait(1)
    reader.join(timeout=1)
    assert not reader.is_alive()
    assert closed.is_set()
    assert len(errors) == 1
