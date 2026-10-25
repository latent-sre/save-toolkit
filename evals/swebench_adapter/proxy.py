"""Host-owned, fixed-target Messages relay; the attempt receives only its token.

The listener exposes no accounting route. ``usage()`` is an in-process host API.
HTTP upstreams are restricted to literal loopback addresses for offline tests.
"""

from __future__ import annotations

import contextlib
import hmac
import http.client
import ipaddress
import json
import math
import os
import re
import socket
import stat
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn
from urllib.parse import urlsplit

_MAX_BODY = 8 * 1024 * 1024
_MAX_RESPONSE = 64 * 1024 * 1024
_IO_TIMEOUT = 30
_REQUEST_SECONDS = 300
_CONCURRENCY = 8
_ERROR = b'{"error":"model proxy rejected request"}'


def _credential(value: str) -> bool:
    return isinstance(value, str) and bool(value) and len(value) <= 4096 and all(33 <= ord(c) <= 126 for c in value)


def read_key(path: str | Path) -> str:
    """Read a protected regular file without following its final symlink."""
    descriptor = None
    try:
        if Path(path).is_symlink():
            raise ValueError
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > 4097:
            raise ValueError
        if os.name == "posix" and (info.st_uid != os.getuid() or info.st_mode & 0o077):
            raise ValueError
        data = os.read(descriptor, 4098)
        value = data.decode("ascii").removesuffix("\n").removesuffix("\r")
        if not _credential(value):
            raise ValueError
        return value
    except (OSError, UnicodeError, ValueError):
        raise ValueError("invalid protected key file") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _json(data: bytes) -> object:
    def invalid(_value: str) -> None:
        raise ValueError("invalid JSON number")

    return json.loads(data, object_pairs_hook=_object, parse_constant=invalid)


class _Server(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    block_on_close = False
    request_queue_size = _CONCURRENCY

    def __init__(self, address: tuple[str, int], owner: ModelProxy):
        self.owner = owner
        self.slots = threading.BoundedSemaphore(_CONCURRENCY)
        super().__init__(address, _Handler)

    def get_request(self) -> tuple[socket.socket, object]:
        request, address = super().get_request()
        request.settimeout(_IO_TIMEOUT)
        return request, address

    def process_request(self, request: socket.socket | tuple[bytes, socket.socket], client_address: object) -> None:
        if isinstance(request, tuple):
            raise TypeError("model proxy requires a TCP socket")
        if not self.slots.acquire(blocking=False):
            with contextlib.suppress(OSError):
                request.sendall(b"HTTP/1.0 503 Service Unavailable\r\nContent-Length: 0\r\n\r\n")
            self.shutdown_request(request)
            return
        self.owner._track(request)
        try:
            super().process_request(request, client_address)
        except Exception:
            self.owner._untrack(request)
            self.slots.release()
            raise

    def process_request_thread(
        self, request: socket.socket | tuple[bytes, socket.socket], client_address: object
    ) -> None:
        if isinstance(request, tuple):
            raise TypeError("model proxy requires a TCP socket")
        deadline = threading.Timer(_REQUEST_SECONDS, self._expire, args=(request,))
        deadline.daemon = True
        deadline.start()
        try:
            super().process_request_thread(request, client_address)
        finally:
            deadline.cancel()
            self.owner._untrack(request)
            self.slots.release()

    @staticmethod
    def _expire(request: socket.socket) -> None:
        with contextlib.suppress(OSError):
            request.shutdown(socket.SHUT_RDWR)

    def handle_error(self, request: object, client_address: object) -> None:
        # HTTP/parser/socket exceptions must never put request or upstream data in logs.
        pass


class _Handler(BaseHTTPRequestHandler):
    server: _Server

    def log_message(self, *_args: object) -> None:
        pass

    def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
        self._reject(code)

    def _reject(self, status: int) -> None:
        self.close_connection = True
        self.send_response_only(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(_ERROR)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(_ERROR)

    def do_GET(self) -> None:
        self._reject(404)

    do_HEAD = do_GET
    do_PUT = do_GET
    do_DELETE = do_GET
    do_PATCH = do_GET
    do_OPTIONS = do_GET
    do_CONNECT = do_GET

    def do_POST(self) -> None:
        owner = self.server.owner
        conn = None
        started = False
        try:
            if self.path not in {"/v1/messages", "/v1/messages?beta=true"}:
                self._reject(404)
                return
            credentials = []
            auth = self.headers.get_all("Authorization", [])
            keys = self.headers.get_all("x-api-key", [])
            if len(auth) > 1 or len(keys) > 1:
                owner._auth_failed.set()
                self._reject(401)
                return
            if auth:
                credentials.append(auth[0].removeprefix("Bearer ") if auth[0].startswith("Bearer ") else "")
            credentials.extend(keys)
            if not credentials or not all(hmac.compare_digest(c.encode(), owner._token) for c in credentials):
                owner._auth_failed.set()
                self._reject(401)
                return
            lengths = self.headers.get_all("Content-Length", [])
            if (
                len(lengths) != 1
                or not re.fullmatch(r"[0-9]{1,8}", lengths[0])
                or self.headers.get_all("Transfer-Encoding")
                or self.headers.get_all("Expect")
            ):
                self._reject(400)
                return
            size = int(lengths[0])
            if not 0 < size <= _MAX_BODY:
                self._reject(413)
                return
            if self.headers.get_all("Content-Type", []) != ["application/json"]:
                self._reject(400)
                return
            body = self.rfile.read(size)
            if len(body) != size:
                self._reject(400)
                return
            try:
                payload = _json(body)
            except (ValueError, UnicodeError, RecursionError):
                self._reject(400)
                return
            if not isinstance(payload, dict) or not isinstance(payload.get("model"), str):
                self._reject(400)
                return
            if payload["model"] not in owner._models:
                self._reject(403)
                return
            headers = {
                "Authorization": owner._authorization(),
                "Content-Type": "application/json",
                "Accept-Encoding": "identity",
            }
            for name in ("anthropic-version", "anthropic-beta"):
                values = self.headers.get_all(name, [])
                if len(values) > 1 or any(len(v) > 1024 or any(ord(c) < 32 or ord(c) > 126 for c in v) for v in values):
                    self._reject(400)
                    return
                if values:
                    headers[name] = values[0]
            conn = owner._connection()
            conn.request("POST", "/api/v1/messages", body, headers)
            response = conn.getresponse()
            if response.status in {401, 403}:
                owner._auth_failed.set()
            if response.status != 200 or not _response_framing(response, _MAX_RESPONSE):
                self._reject(502)
                return
            content_types = response.headers.get_all("Content-Type", [])
            if len(content_types) != 1:
                self._reject(502)
                return
            content_type = content_types[0].split(";", 1)[0].strip().lower()
            if content_type not in {"application/json", "text/event-stream"}:
                self._reject(502)
                return
            self.close_connection = True
            self.send_response_only(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Connection", "close")
            self.end_headers()
            started = True
            pending = b""
            total = 0
            deadline = time.monotonic() + _REQUEST_SECONDS
            while not owner._closed.is_set():
                chunk = response.read1(16384)
                if not chunk:
                    self.wfile.write(pending.replace(owner._key, b"[REDACTED]"))
                    self.wfile.flush()
                    break
                total += len(chunk)
                if total > _MAX_RESPONSE or time.monotonic() > deadline:
                    break
                # Retain enough raw suffix to detect a credential across arbitrary reads.
                data = pending + chunk
                cut = max(0, len(data) - len(owner._key) + 1)
                cursor = 0
                while True:
                    found = data.find(owner._key, cursor)
                    if found < 0 or found >= cut:
                        break
                    self.wfile.write(data[cursor:found] + b"[REDACTED]")
                    cursor = found + len(owner._key)
                cut = max(cut, cursor)
                self.wfile.write(data[cursor:cut])
                self.wfile.flush()
                pending = data[cut:]
        except (OSError, ValueError, http.client.HTTPException, RecursionError):
            if not started:
                with contextlib.suppress(OSError):
                    self._reject(502)
        finally:
            if conn is not None:
                owner._untrack(conn)
                conn.close()


def _response_framing(response: http.client.HTTPResponse, limit: int) -> bool:
    lengths = response.headers.get_all("Content-Length", [])
    transfers = response.headers.get_all("Transfer-Encoding", [])
    if len(lengths) > 1 or len(transfers) > 1 or (lengths and transfers):
        return False
    if lengths and (not re.fullmatch(r"[0-9]{1,9}", lengths[0]) or int(lengths[0]) > limit):
        return False
    if transfers and transfers != ["chunked"]:
        return False
    return response.headers.get("Content-Encoding", "identity") == "identity"


class ModelProxy:
    """A bounded ephemeral relay; only the host supplies the origin and real key."""

    def __init__(
        self,
        key: str,
        token: str,
        models: set[str] | list[str] | tuple[str, ...],
        *,
        bind_host: str = "127.0.0.1",
        upstream_origin: str = "https://openrouter.ai",
    ):
        if not _credential(key) or not _credential(token) or key == token:
            raise ValueError("invalid proxy credentials")
        if isinstance(models, str) or not models or any(not isinstance(m, str) or not m for m in models):
            raise ValueError("invalid allowed models")
        try:
            origin = urlsplit(upstream_origin)
            if (
                origin.scheme not in {"https", "http"}
                or not origin.hostname
                or origin.username is not None
                or origin.password is not None
                or origin.path
                or origin.query
                or origin.fragment
                or any(ord(c) < 33 or ord(c) > 126 for c in upstream_origin)
            ):
                raise ValueError
            if origin.scheme == "http" and not ipaddress.ip_address(origin.hostname).is_loopback:
                raise ValueError
            port = origin.port
        except ValueError:
            raise ValueError("invalid upstream origin") from None
        self._key = key.encode("ascii")
        self._token = token.encode("ascii")
        self._models = frozenset(models)
        self._bind_host = bind_host
        self._origin = (origin.scheme, origin.hostname, port)
        self._auth_failed = threading.Event()
        self._closed = threading.Event()
        self._lock = threading.Lock()
        self._active: set[object] = set()
        self._upstream_sockets: dict[http.client.HTTPConnection, socket.socket] = {}
        self._server: _Server | None = None
        self._thread: threading.Thread | None = None

    @property
    def auth_failed(self) -> bool:
        return self._auth_failed.is_set()

    @property
    def port(self) -> int:
        if self._server is None:
            raise RuntimeError("proxy is not started")
        return self._server.server_port

    def start(self) -> None:
        if self._server is not None or self._closed.is_set():
            raise RuntimeError("proxy cannot be started")
        self._server = _Server((self._bind_host, 0), self)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def _track(self, resource: object) -> None:
        with self._lock:
            if self._closed.is_set():
                raise OSError("proxy is closed")
            self._active.add(resource)

    def _untrack(self, resource: object) -> None:
        with self._lock:
            self._active.discard(resource)
            if isinstance(resource, http.client.HTTPConnection):
                self._active.discard(self._upstream_sockets.pop(resource, None))

    def close(self) -> None:
        self._closed.set()
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        with self._lock:
            resources = list(self._active)
        for resource in resources:
            with contextlib.suppress(OSError):
                if isinstance(resource, socket.socket):
                    resource.shutdown(socket.SHUT_RDWR)
                    resource.close()
                elif isinstance(resource, http.client.HTTPConnection):
                    if resource.sock is not None:
                        resource.sock.shutdown(socket.SHUT_RDWR)
                    resource.close()
        if self._thread is not None:
            self._thread.join(2)

    def _authorization(self) -> str:
        return "Bearer " + self._key.decode("ascii")

    def _connection(self) -> http.client.HTTPConnection:
        scheme, host, port = self._origin
        connection_type = http.client.HTTPSConnection if scheme == "https" else http.client.HTTPConnection
        connection = connection_type(host, port, timeout=_IO_TIMEOUT)
        self._track(connection)
        try:
            connection.connect()
            with self._lock:
                if self._closed.is_set() or connection.sock is None:
                    raise OSError("proxy is closed")
                # HTTP/1.0 responses detach their socket from HTTPConnection. Retain
                # the socket separately so close() still interrupts an active read.
                self._upstream_sockets[connection] = connection.sock
                self._active.add(connection.sock)
        except (OSError, http.client.HTTPException):
            self._untrack(connection)
            connection.close()
            raise
        return connection

    def usage(self) -> dict[str, float | int | None]:
        """Return only usage, limit and limit_remaining; malformed metadata raises."""
        connection = None
        try:
            connection = self._connection()
            connection.request(
                "GET", "/api/v1/key", headers={"Authorization": self._authorization(), "Accept-Encoding": "identity"}
            )
            response = connection.getresponse()
            if response.status in {401, 403}:
                self._auth_failed.set()
            if response.status != 200 or not _response_framing(response, 65536):
                raise ValueError
            raw = response.read(65537)
            if len(raw) > 65536:
                raise ValueError
            payload = _json(raw)
            data = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(data, dict) or not all(name in data for name in ("usage", "limit", "limit_remaining")):
                raise ValueError
            result = {name: data.get(name) for name in ("usage", "limit", "limit_remaining")}
            for name, value in result.items():
                if value is None and name != "usage":
                    continue
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (float, int))
                    or value < 0
                    or not math.isfinite(value)
                ):
                    raise ValueError
            return result
        except (OSError, ValueError, http.client.HTTPException, RecursionError, OverflowError):
            raise ValueError("upstream usage unavailable") from None
        finally:
            if connection is not None:
                self._untrack(connection)
                connection.close()
