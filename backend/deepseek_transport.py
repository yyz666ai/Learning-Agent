"""Invocation-scoped Responses relay for DeepSeek's Codex-header incompatibility.

This is not a general proxy: only the fixed Responses endpoint is accessible,
using a short-lived local credential rather than exposing the upstream key.
"""

from __future__ import annotations

import hmac
import json
import logging
import secrets
import socket
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Iterator

import httpx


_UPSTREAM_URL = "https://api.deepseek.com/v1/responses"
_MAX_BODY_BYTES = 8 * 1024 * 1024
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GenerationTransport:
    base_url: str
    token: str


@contextmanager
def deepseek_generation_transport(
    api_key: str,
    timeout: float,
    *,
    allow_tools: bool = True,
    json_output: bool = False,
    _client_factory: Callable[..., httpx.Client] = httpx.Client,
) -> Iterator[GenerationTransport]:
    """Yield an authenticated loopback endpoint and close it on every exit path.

    ``_client_factory`` allows network-free transport tests, not URL overrides.
    The absolute invocation deadline also bounds streaming and slow clients.
    """
    if not api_key or timeout <= 0:
        raise ValueError("DeepSeek transport requires credentials and a positive timeout")
    token = secrets.token_urlsafe(32)
    deadline = time.monotonic() + timeout
    # The invocation timer below is the absolute deadline. A shorter arbitrary
    # read timeout can truncate healthy long output and make Codex regenerate it.
    client = _client_factory(timeout=httpx.Timeout(timeout, connect=min(timeout, 10)), follow_redirects=False, trust_env=False)
    lock = threading.Lock()
    connections: set[socket.socket] = set()
    responses: set[httpx.Response] = set()
    stopped = threading.Event()

    class Server(ThreadingHTTPServer):
        daemon_threads = True
        block_on_close = False
        slots = threading.BoundedSemaphore(4)

        def process_request(self, request, client_address):
            if stopped.is_set() or not self.slots.acquire(blocking=False):
                self.shutdown_request(request)
                return
            with lock:
                connections.add(request)
            try:
                super().process_request(request, client_address)
            except BaseException:
                with lock:
                    connections.discard(request)
                self.slots.release()
                raise

        def process_request_thread(self, request, client_address):
            try:
                super().process_request_thread(request, client_address)
            finally:
                with lock:
                    connections.discard(request)
                self.slots.release()

        def handle_error(self, request, client_address):
            # HTTP server tracebacks can include request data or provider errors.
            pass

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def setup(self):
            self.request.settimeout(max(0.01, min(10, deadline - time.monotonic())))
            super().setup()

        def log_message(self, format, *args):
            pass

        def fail(self, status):
            self.send_response(status)
            self.send_header("Content-Length", "0")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True

        def do_GET(self):
            self.fail(405)

        do_PUT = do_DELETE = do_PATCH = do_OPTIONS = do_HEAD = do_GET

        def do_POST(self):
            self.close_connection = True
            if self.path != "/v1/responses":
                self.fail(404)
                return
            auth = self.headers.get_all("Authorization", [])
            if len(auth) != 1 or not hmac.compare_digest(auth[0].encode(), ("Bearer " + token).encode()):
                self.fail(401)
                return
            lengths = self.headers.get_all("Content-Length", [])
            if self.headers.get("Transfer-Encoding") or len(lengths) != 1:
                self.fail(400)
                return
            try:
                length = int(lengths[0])
            except ValueError:
                self.fail(400)
                return
            if not 0 < length <= _MAX_BODY_BYTES:
                self.fail(413)
                return
            try:
                body = self.rfile.read(length)
                if len(body) != length:
                    self.fail(400)
                    return
                payload = json.loads(body)
                if not isinstance(payload, dict):
                    self.fail(400)
                    return
            except (ValueError, UnicodeDecodeError, OSError):
                self.fail(400)
                return
            payload.pop("client_metadata", None)
            payload["reasoning"] = {"effort": "none"}
            if not allow_tools:
                # The prepared context contains all inputs. Suppress the full
                # CLI tool inventory, not just shell/search feature switches.
                payload["tools"] = []
                payload["tool_choice"] = "none"
            if json_output:
                payload["text"] = {"format": {"type": "json_object"}}
            headers_sent = False
            response = None
            request_started = time.monotonic()
            first_chunk = True
            try:
                if stopped.is_set() or time.monotonic() >= deadline:
                    self.fail(504)
                    return
                # Never forward Codex UA, turn metadata, arbitrary auth or origin.
                request = client.build_request("POST", _UPSTREAM_URL, json=payload, headers={
                    "Authorization": "Bearer " + api_key,
                    "Content-Type": "application/json",
                    "User-Agent": "LearningAgent-DeepSeek-Transport/1.0",
                    "Accept-Encoding": "identity",
                })
                response = client.send(request, stream=True, follow_redirects=False)
                logger.info("generation.upstream.headers elapsed=%.2fs status=%s",
                            time.monotonic() - request_started, response.status_code)
                with lock:
                    responses.add(response)
                if 300 <= response.status_code < 400:
                    self.fail(502)
                    return
                self.send_response(response.status_code)
                self.send_header("Content-Type", response.headers.get("Content-Type", "application/json"))
                self.send_header("Transfer-Encoding", "chunked")
                self.send_header("Connection", "close")
                self.end_headers()
                headers_sent = True
                for chunk in response.iter_bytes():
                    if stopped.is_set() or time.monotonic() >= deadline:
                        raise TimeoutError("transport deadline")
                    if chunk:
                        if first_chunk:
                            logger.info("generation.upstream.first_bytes elapsed=%.2fs",
                                        time.monotonic() - request_started)
                            first_chunk = False
                        self.wfile.write(f"{len(chunk):x}\r\n".encode() + chunk + b"\r\n")
                        self.wfile.flush()
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
            except (httpx.HTTPError, OSError, RuntimeError) as exc:
                logger.warning("generation.upstream.error elapsed=%.2fs type=%s response_started=%s",
                               time.monotonic() - request_started, type(exc).__name__, headers_sent)
                if not headers_sent:
                    self.fail(502)
                # A truncated chunked body is deliberately an observable error;
                # never synthesize a successful SSE completion after a failure.
            finally:
                if response is not None:
                    with lock:
                        responses.discard(response)
                    response.close()

    server = Server(("127.0.0.1", 0), Handler)

    def cancel():
        stopped.set()
        with lock:
            active_connections = list(connections)
            active_responses = list(responses)
        for connection in active_connections:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            connection.close()
        for response in active_responses:
            response.close()
        client.close()

    worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    timer = threading.Timer(timeout, cancel)
    timer.daemon = True
    worker.start()
    timer.start()
    try:
        yield GenerationTransport(f"http://127.0.0.1:{server.server_port}/v1", token)
    finally:
        timer.cancel()
        cancel()
        server.shutdown()
        server.server_close()
        worker.join(timeout=1)
