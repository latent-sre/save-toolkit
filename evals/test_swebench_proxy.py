"""Offline contract tests: all network peers are ephemeral loopback servers."""

import contextlib
import http.client
import importlib
import json
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

KEY = "sk-test-credential-never-deliver-to-agent"
TOKEN = "attempt-placeholder"
MODEL = "anthropic/claude-sonnet-test"


@contextlib.contextmanager
def upstream(respond=None):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            size = int(self.headers.get("Content-Length", "0"))
            requests.append((self.command, self.path, dict(self.headers), self.rfile.read(size)))
            if respond:
                respond(self)
            else:
                body = b'{"type":"message","content":[]}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        def do_GET(self):
            requests.append((self.command, self.path, dict(self.headers), b""))
            if respond:
                respond(self)
            else:
                body = json.dumps(
                    {"data": {"usage": 1.25, "limit": 10, "limit_remaining": 8.75, "label": KEY}}
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)


@contextlib.contextmanager
def relay(origin):
    module = importlib.import_module("swebench_adapter.proxy")
    proxy = module.ModelProxy(KEY, TOKEN, {MODEL}, upstream_origin=origin)
    proxy.start()
    try:
        yield proxy
    finally:
        proxy.close()


def request(proxy, *, path="/v1/messages", method="POST", body=None, headers=None):
    if body is None:
        body = json.dumps({"model": MODEL, "messages": []}).encode()
    if headers is None:
        headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    conn = http.client.HTTPConnection("127.0.0.1", proxy.port, timeout=3)
    try:
        conn.request(method, path, body, headers)
        response = conn.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        conn.close()


def test_fixed_messages_target_replaces_auth_and_filters_headers():
    with upstream() as (origin, calls), relay(origin) as proxy:
        status, headers, body = request(
            proxy,
            path="/v1/messages?beta=true",
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "x-api-key": TOKEN,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
                "anthropic-beta": "tools-2024-04-04",
                "X-Forwarded-Host": "evil.test",
                "Cookie": "secret",
                "X-Target-URL": "https://evil.test",
            },
        )
        assert status == 200
        assert json.loads(body)["type"] == "message"
        assert KEY not in str(headers) + body.decode()
        assert len(calls) == 1
        method, path, sent, payload = calls[0]
        assert (method, path) == ("POST", "/api/v1/messages")
        assert sent["Authorization"] == f"Bearer {KEY}"
        assert sent["anthropic-version"] == "2023-06-01"
        assert "Cookie" not in sent and "X-Target-URL" not in sent
        assert "x-api-key" not in sent and "X-Forwarded-Host" not in sent
        assert json.loads(payload)["model"] == MODEL


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/key",
        "http://evil.test/v1/messages",
        "//evil.test/v1/messages",
        "/v1/../api/v1/key",
        "/v1/%2e%2e/messages",
        "/v1/messages?url=evil",
        "/v1/messages/",
        "/v1/messages#fragment",
    ],
)
def test_routes_cannot_choose_upstream_or_expose_usage(path):
    with upstream() as (origin, calls), relay(origin) as proxy:
        assert request(proxy, path=path)[0] == 404
        assert calls == []


@pytest.mark.parametrize(
    "body",
    [b"{}", b"[]", b"null", b"{", b'{"model":"other"}', b'{"model":"first","model":"anthropic/claude-sonnet-test"}'],
)
def test_invalid_or_unallowlisted_model_never_reaches_upstream(body):
    with upstream() as (origin, calls), relay(origin) as proxy:
        assert request(proxy, body=body)[0] in {400, 403}
        assert calls == []


def test_placeholder_auth_required_and_conflicting_credentials_rejected():
    with upstream() as (origin, calls), relay(origin) as proxy:
        for headers in [
            {},
            {"Authorization": "Bearer wrong"},
            {"Authorization": f"Bearer {TOKEN}", "x-api-key": "wrong"},
        ]:
            assert request(proxy, headers=headers)[0] == 401
        assert proxy.auth_failed
        assert calls == []
        assert request(proxy, headers={"x-api-key": TOKEN, "Content-Type": "application/json"})[0] == 200


@pytest.mark.parametrize(
    "extra",
    [
        b"Transfer-Encoding: chunked\r\n",
        b"Content-Length: 1\r\n",
        b"Content-Length: -1\r\n",
        b"Content-Length: 999999999\r\n",
        b"Expect: 100-continue\r\n",
    ],
)
def test_ambiguous_or_excessive_request_framing_rejected(extra):
    with upstream() as (origin, calls), relay(origin) as proxy:
        with socket.create_connection(("127.0.0.1", proxy.port), timeout=3) as sock:
            sock.sendall(
                b"POST /v1/messages HTTP/1.1\r\nHost: localhost\r\nAuthorization: Bearer "
                + TOKEN.encode()
                + b"\r\nContent-Type: application/json\r\nContent-Length: 2\r\n"
                + extra
                + b"\r\n{}"
            )
            assert b" 200 " not in sock.recv(4096)
        assert calls == []


@pytest.mark.parametrize("status", [301, 307, 401, 403, 429, 500])
def test_upstream_errors_are_sanitized_and_redirects_not_followed(status, capsys):
    def respond(handler):
        handler.send_response(status, KEY)
        handler.send_header("Location", f"http://127.0.0.1/leak?key={KEY}")
        handler.send_header("Content-Type", "application/json")
        handler.end_headers()
        handler.wfile.write(KEY.encode())

    with upstream(respond) as (origin, calls), relay(origin) as proxy:
        code, headers, body = request(proxy)
        assert code >= 400
        assert KEY not in str(headers) + body.decode()
        assert len(calls) == 1
        assert proxy.auth_failed is (status in {401, 403})
    captured = capsys.readouterr()
    assert KEY not in captured.out + captured.err


def test_split_chunked_stream_is_incremental_and_scrubs_reflected_key():
    first_sent = threading.Event()
    continue_stream = threading.Event()
    first = b"event: message_start\ndata: " + b"x" * 100 + b"\n\n"

    def chunk(handler, data):
        handler.wfile.write(f"{len(data):x}\r\n".encode() + data + b"\r\n")
        handler.wfile.flush()

    def respond(handler):
        handler.send_response(200)
        handler.send_header("Content-Type", "text/event-stream")
        handler.send_header("Transfer-Encoding", "chunked")
        handler.send_header("X-Secret", KEY)
        handler.end_headers()
        chunk(handler, first)
        first_sent.set()
        if continue_stream.wait(3):
            for part in [b"data: ", KEY[:10].encode(), KEY[10:].encode(), b"\n\nevent: done\n\n"]:
                chunk(handler, part)
            handler.wfile.write(b"0\r\n\r\n")

    with upstream(respond) as (origin, _calls), relay(origin) as proxy:
        conn = http.client.HTTPConnection("127.0.0.1", proxy.port, timeout=2)
        try:
            conn.request(
                "POST",
                "/v1/messages",
                json.dumps({"model": MODEL}),
                {"x-api-key": TOKEN, "Content-Type": "application/json"},
            )
            response = conn.getresponse()
            assert first_sent.wait(1)
            prefix = response.read(40)
            assert prefix == first[:40]
            assert "X-Secret" not in dict(response.getheaders())
            continue_stream.set()
            result = prefix + response.read()
            assert KEY.encode() not in result
            assert b"[REDACTED]" in result
            assert result.endswith(b"event: done\n\n")
        finally:
            continue_stream.set()
            conn.close()


def test_usage_is_host_only_and_returns_only_numeric_accounting():
    with upstream() as (origin, calls), relay(origin) as proxy:
        assert proxy.usage() == {"usage": 1.25, "limit": 10, "limit_remaining": 8.75}
        assert calls[0][:2] == ("GET", "/api/v1/key")
        assert calls[0][2]["Authorization"] == f"Bearer {KEY}"
        assert request(proxy, path="/api/v1/key", method="GET")[0] == 404
        assert len(calls) == 1


@pytest.mark.parametrize(
    "payload",
    [
        {"data": {"usage": "secret"}},
        {"data": {"usage": True}},
        {"data": {"usage": -1}},
        {"data": {"usage": float("inf")}},
        {"data": {"usage": 0}},
        {"data": {"usage": None}},
    ],
)
def test_usage_rejects_malformed_accounting_without_echo(payload):
    def respond(handler):
        body = json.dumps(payload).encode()
        handler.send_response(200)
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)

    with upstream(respond) as (origin, _calls), relay(origin) as proxy:
        with pytest.raises(ValueError, match="usage") as error:
            proxy.usage()
        assert KEY not in str(error.value)


def test_usage_network_failure_is_sanitized():
    module = importlib.import_module("swebench_adapter.proxy")
    with upstream() as (origin, _calls):
        proxy = module.ModelProxy(KEY, TOKEN, {MODEL}, upstream_origin=origin)
    try:
        with pytest.raises(ValueError, match="usage") as error:
            proxy.usage()
        assert KEY not in str(error.value)
    finally:
        proxy.close()


def test_key_file_requires_protected_regular_nonsymlink_input(tmp_path):
    module = importlib.import_module("swebench_adapter.proxy")
    path = tmp_path / "key"
    path.write_text(KEY + "\n")
    path.chmod(0o600)
    assert module.read_key(path) == KEY
    link = tmp_path / "link"
    link.symlink_to(path)
    with pytest.raises(ValueError):
        module.read_key(link)
    with pytest.raises(ValueError):
        module.read_key(tmp_path)
    if os.name == "posix":
        path.chmod(0o644)
        with pytest.raises(ValueError):
            module.read_key(path)
        path.chmod(0o600)
    path.write_text(KEY + "\nsecond-line")
    with pytest.raises(ValueError) as error:
        module.read_key(path)
    assert KEY not in str(error.value)


@pytest.mark.parametrize(
    "origin",
    [
        "http://example.com",
        "https://user:password@example.com",
        "https://example.com/path",
        "https://example.com?query",
        "file:///tmp/upstream",
        "https://example.com/#fragment",
    ],
)
def test_origin_is_a_host_configured_origin_only(origin):
    module = importlib.import_module("swebench_adapter.proxy")
    with pytest.raises(ValueError):
        module.ModelProxy(KEY, TOKEN, {MODEL}, upstream_origin=origin)


def test_close_interrupts_active_upstream_stream():
    ready = threading.Event()
    disconnected = threading.Event()

    def respond(handler):
        handler.send_response(200)
        handler.send_header("Content-Type", "text/event-stream")
        handler.end_headers()
        handler.wfile.write(b"data: " + b"x" * 100 + b"\n\n")
        handler.wfile.flush()
        handler.connection.settimeout(2)
        ready.set()
        with contextlib.suppress(OSError):
            if handler.connection.recv(1) == b"":
                disconnected.set()

    with upstream(respond) as (origin, _calls), relay(origin) as proxy:
        conn = http.client.HTTPConnection("127.0.0.1", proxy.port, timeout=3)
        try:
            conn.request(
                "POST",
                "/v1/messages",
                json.dumps({"model": MODEL}),
                {"x-api-key": TOKEN, "Content-Type": "application/json"},
            )
            response = conn.getresponse()
            assert ready.wait(1)
            assert response.read(10) == b"data: xxxx"
            # Let the forwarding worker enter its next blocking upstream read.
            assert not disconnected.wait(0.1)
            proxy.close()
            assert disconnected.wait(1), "close must terminate the upstream socket too"
        finally:
            conn.close()


def test_upstream_read_timeout_fails_without_echo(monkeypatch):
    module = importlib.import_module("swebench_adapter.proxy")
    monkeypatch.setattr(module, "_IO_TIMEOUT", 0.1)
    release = threading.Event()

    def respond(_handler):
        release.wait(2)

    with upstream(respond) as (origin, _calls), relay(origin) as proxy:
        try:
            code, headers, body = request(proxy)
            assert code == 502
            assert KEY not in str(headers) + body.decode()
        finally:
            release.set()


def test_slow_clients_have_bounded_concurrency(monkeypatch):
    module = importlib.import_module("swebench_adapter.proxy")
    monkeypatch.setattr(module, "_CONCURRENCY", 2)
    with upstream() as (origin, calls), relay(origin) as proxy, contextlib.ExitStack() as stack:
        for _ in range(2):
            sock = stack.enter_context(socket.create_connection(("127.0.0.1", proxy.port), timeout=3))
            sock.sendall(b"POST /v1/messages HTTP/1.1\r\nHost: localhost\r\n")
        # Saturation is rejected at accept time, before the peer sends a body.
        with socket.create_connection(("127.0.0.1", proxy.port), timeout=3) as excess:
            assert b" 503 " in excess.recv(4096)
        assert calls == []


@pytest.mark.parametrize(
    "headers",
    [
        b"Content-Length: 1\r\nContent-Length: 1\r\n",
        b"Content-Length: 1\r\nTransfer-Encoding: chunked\r\n",
        b"Content-Length: 999999999\r\n",
        b"Content-Encoding: gzip\r\n",
    ],
)
def test_unsafe_upstream_framing_is_not_forwarded(headers):
    def respond(handler):
        handler.wfile.write(b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n" + headers + b"\r\n" + KEY.encode())

    with upstream(respond) as (origin, _calls), relay(origin) as proxy:
        status, result_headers, body = request(proxy)
        assert status == 502
        assert KEY not in str(result_headers) + body.decode()
