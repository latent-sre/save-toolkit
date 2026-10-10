"""Backing services a trial measures against: reviewed containers behind a loopback audit proxy.

A service that will not start, become ready, seed, snapshot or start its proxy is harness breakage,
reported as `ServiceUnavailable` and turned into INCONCLUSIVE by the caller, never a verdict.
"""

from __future__ import annotations

import base64
import json
import re
import secrets
import shutil
import subprocess
import tempfile
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

TRUSTED_SERVICE_IMAGES = frozenset(
    {
        "grafana/grafana@sha256:62d2b9d20a19714ebfe48d1bb405086081bc602aa053e28cf6d73c7537640dfb",
        "prom/prometheus:v3.14.0-distroless@sha256:50c707e96da5ade383cb1707790576480485e93de06aa60ad8802cb5f744bd0a",
    }
)


SERVICE_RELAY_IMAGE = (
    "python:3.12.10-slim-bookworm@sha256:97983fa8cc88343512862c62307159a82261c3528dc025f79e5a3f7af43e50b4"
)


SERVICE_RELAY_PORT = 8080
SERVICE_NAME = re.compile(r"[a-z][a-z0-9-]{0,62}")  # a container network alias and a temp-dir prefix


SERVICE_RELAY_SCRIPT = r"""
import select
import socket
import socketserver
import sys

target = (sys.argv[1], int(sys.argv[2]))

class Relay(socketserver.BaseRequestHandler):
    def handle(self):
        with socket.create_connection(target, timeout=30) as upstream:
            peers = [self.request, upstream]
            while True:
                readable, _, _ = select.select(peers, [], [], 60)
                if not readable:
                    return
                for source in readable:
                    data = source.recv(65536)
                    if not data:
                        return
                    destination = upstream if source is self.request else self.request
                    destination.sendall(data)

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

with Server(("0.0.0.0", 8080), Relay) as server:
    server.serve_forever()
"""


class _Proxy(Protocol):
    def shutdown(self) -> None: ...
    def server_close(self) -> None: ...


@dataclass
class Service:
    """A disposable, reviewed-digest container the trial talks to through a loopback audit proxy.

    Some lanes can only be measured against a real system: `observability-engineer` has a scoped
    Grafana write exception, measured through proxied requests and final resource state. These
    observations cannot rule out writes that bypass the proxy and are later restored. The container
    is `--rm`, bound to 127.0.0.1 on an ephemeral port, capability/resource limited, and torn down
    with the workspace. The model receives a fixed-target proxy URL; grading uses the direct URL.
    """

    name: str
    image: str
    container_id: str
    base_url: str
    auth: str | None = None
    snapshots: dict[str, Any] = field(default_factory=dict)
    agent_url: str = ""
    requests: list[dict[str, Any]] = field(default_factory=list)
    network_name: str = ""
    config_root: Path | None = None
    proxy: _Proxy | None = field(default=None, repr=False)
    proxy_thread: object | None = field(default=None, repr=False)
    proxy_stopped: bool = False
    relay_container_id: str = ""


def request(
    service: Service, path: str, method: str = "GET", body: dict[str, Any] | None = None, timeout: int = 20
) -> tuple[int, object]:
    """One JSON request against a service, returning (status, parsed-or-text). Never raises on 4xx/5xx."""
    import urllib.error  # noqa: PLC0415 — stdlib, imported where the probe actually talks to a service
    import urllib.request  # noqa: PLC0415

    headers = {"Content-Type": "application/json"}
    if service.auth:
        headers["Authorization"] = "Basic " + base64.b64encode(service.auth.encode()).decode()
    outgoing = urllib.request.Request(
        service.base_url + path,
        method=method,
        headers=headers,
        data=json.dumps(body).encode() if body is not None else None,
    )
    try:
        with urllib.request.urlopen(outgoing, timeout=timeout) as response:
            raw = response.read().decode("utf-8", "replace")
            status = response.status
    except urllib.error.HTTPError as exc:
        raw, status = exc.read().decode("utf-8", "replace"), exc.code
    except (urllib.error.URLError, OSError) as exc:
        return 0, f"unreachable: {exc}"
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, raw


def _start_service_proxy(service: Service) -> None:
    """Expose one fixed-target loopback proxy and retain request/response facts for post-run checks.

    The proxy cannot select another upstream: every request is forwarded only to the reviewed
    container's loopback URL. Authorization is forwarded but never retained in the audit entries.
    """
    import http.server  # noqa: PLC0415 — stdlib and local to the backing-service feature
    import threading  # noqa: PLC0415
    import urllib.error  # noqa: PLC0415
    import urllib.request  # noqa: PLC0415

    def decoded(raw: bytes) -> object:
        text = raw.decode("utf-8", "replace")
        try:
            return json.loads(text) if text else None
        except json.JSONDecodeError:
            return text

    class FixedTargetProxy(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        timeout = 30  # an idle accepted socket cannot keep the grading boundary open forever

        def log_message(self, _format: str, *_args: object) -> None:
            return

        def _forward(self) -> None:
            length = int(self.headers.get("Content-Length", "0") or 0)
            request_raw = self.rfile.read(length) if length else b""
            headers = {
                key: value
                for key, value in self.headers.items()
                if key.lower() not in {"host", "content-length", "connection", "transfer-encoding"}
            }
            request = urllib.request.Request(
                service.base_url + self.path,
                data=request_raw if length else None,
                headers=headers,
                method=self.command,
            )
            entry = {
                "method": self.command,
                "path": self.path,
                "status": None,
                "request": decoded(request_raw),
                "response": None,
            }
            # Append at receipt time, before I/O, so a later fast request cannot appear to have
            # preceded a slower write and manufacture a false preflight sequence.
            service.requests.append(entry)
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    response_raw = response.read()
                    status = response.status
                    response_headers = response.headers
            except urllib.error.HTTPError as exc:
                response_raw = exc.read()
                status = exc.code
                response_headers = exc.headers
            except (urllib.error.URLError, OSError) as exc:
                response_raw = json.dumps({"message": f"backing service unreachable: {exc}"}).encode()
                status = 502
                response_headers = {"Content-Type": "application/json"}

            entry["status"] = status
            entry["response"] = decoded(response_raw)
            self.send_response(status)
            for key, value in response_headers.items():
                if key.lower() not in {"content-length", "connection", "transfer-encoding"}:
                    self.send_header(key, value)
            self.send_header("Content-Length", str(len(response_raw)))
            self.send_header("Connection", "close")
            self.close_connection = True
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(response_raw)

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = _forward

    try:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FixedTargetProxy)
    except OSError as exc:
        raise ServiceUnavailable(f"{service.name}: could not start loopback audit proxy: {exc}") from exc
    # server_close joins these handlers after shutdown stops accepting requests. Each connection
    # serves one request, so an idle keepalive client cannot issue more writes during grading.
    server.daemon_threads = False
    thread = threading.Thread(target=server.serve_forever, name=f"build-probe-{service.name}", daemon=True)
    thread.start()
    service.proxy = server
    service.proxy_thread = thread
    service.proxy_stopped = False
    service.agent_url = f"http://127.0.0.1:{server.server_address[1]}"


DOCKER_TIMEOUT = 600  # seconds: room for an image pull, while a hung daemon cannot stall the batch


def _run_docker(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=DOCKER_TIMEOUT)
    except subprocess.TimeoutExpired as exc:
        raise ServiceUnavailable(f"container runtime {command[0]!r} timed out after {DOCKER_TIMEOUT}s") from exc
    except OSError as exc:
        raise ServiceUnavailable(f"container runtime {command[0]!r} failed: {exc}") from exc


def _stderr(proc: subprocess.CompletedProcess[str]) -> str:
    """The part of a failed container command's stderr that a failure message quotes."""
    return proc.stderr.strip()[:300]


def _docker(command: list[str], action: str) -> str:
    """Run a container command and return its trimmed stdout; a nonzero exit raises `ServiceUnavailable`
    naming the action and quoting its stderr."""
    proc = _run_docker(command)
    if proc.returncode != 0:
        raise ServiceUnavailable(f"{action} failed: {_stderr(proc)}")
    return proc.stdout.strip()


def _hardened_run(docker: str, pids_limit: int, memory: str) -> list[str]:
    """`docker run` for a disposable container without capabilities or privilege escalation."""
    hardening = ["--rm", "--cap-drop", "ALL", "--security-opt", "no-new-privileges"]
    return [docker, "run", "-d", *hardening, "--pids-limit", str(pids_limit), "--memory", memory]


def _write_service_files(root: Path, files: Mapping[str, object]) -> None:
    for relative, content in files.items():
        target = root / str(relative)
        if not target.resolve().is_relative_to(root.resolve()):
            raise ServiceUnavailable(f"service file escapes its disposable root: {relative!r}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(content), encoding="utf-8")


def _service_command(docker: str, declared: Mapping[str, Any], network_name: str, config_root: Path) -> list[str]:
    """The service's own container, reachable only on the probe's internal network by its declared name."""
    name, image = str(declared["name"]), str(declared["image"])
    command = [*_hardened_run(docker, 512, "2g"), "--network", network_name, "--network-alias", name]
    for key, value in (declared.get("env") or {}).items():
        command += ["-e", f"{key}={value}"]
    for mount in declared.get("mounts") or []:
        source = (config_root / str(mount["source"])).resolve()
        if not source.is_relative_to(config_root.resolve()) or not source.is_file():
            raise ServiceUnavailable(f"service mount source is not a declared runtime file: {mount['source']!r}")
        option = f"type=bind,source={source},target={mount['target']}"
        if mount.get("read_only") is True:
            option += ",readonly"
        command += ["--mount", option]
    return [*command, image, *(str(item) for item in (declared.get("command") or []))]


def _start_relay(service: Service, declared: Mapping[str, Any], docker: str) -> None:
    """Publish the service through a relay and record the loopback URL the probe reaches it on.

    Docker Desktop 29 suppresses host publication for containers on an --internal network. Keep the
    service isolated and publish only a fixed-target TCP relay. The relay has no target-selection
    input: every connection goes to this declared service.
    """
    published = ["--read-only", "--user", "65534:65534", "-p", f"127.0.0.1::{SERVICE_RELAY_PORT}"]
    script = ["python", "-I", "-S", "-B", "-c", SERVICE_RELAY_SCRIPT, service.name, str(int(declared.get("port", 80)))]
    service.relay_container_id = _docker(
        [*_hardened_run(docker, 64, "64m"), *published, SERVICE_RELAY_IMAGE, *script],
        f"{service.name}: relay docker run",
    )
    alias = f"relay-{service.name}"
    _docker(
        [docker, "network", "connect", "--alias", alias, service.network_name, service.relay_container_id],
        f"{service.name}: relay network connect",
    )
    port_result = _run_docker([docker, "port", service.relay_container_id, f"{SERVICE_RELAY_PORT}/tcp"])
    mapped = port_result.stdout.strip()
    if not mapped:
        raise ServiceUnavailable(f"{service.name}: no published port: {_stderr(port_result)}")
    service.base_url = "http://127.0.0.1:" + mapped.splitlines()[0].rsplit(":", 1)[1]


def wait_predicates(wait_for: Mapping[str, Any]) -> tuple[bool, bool]:
    """The readiness predicates a `wait_for` declares: `nonempty: true`, and an `equals` scalar. A
    null `equals` reads as absent, so validation refuses it."""
    return wait_for.get("nonempty") is True, isinstance(wait_for.get("equals"), (str, int, float, bool))


def _wait_until_ready(service: Service, declared: Mapping[str, Any]) -> None:
    deadline = time.monotonic() + int(declared.get("ready_timeout", 120))
    ready_path = str(declared.get("ready", "/"))
    while time.monotonic() < deadline:
        status, _ = request(service, ready_path, timeout=5)
        if status == 200:
            break
        time.sleep(2)
    else:
        raise ServiceUnavailable(f"{service.name}: never became ready at {ready_path}")
    wait_for = declared.get("wait_for")
    if wait_for:
        nonempty, has_equals = wait_predicates(wait_for)
        while time.monotonic() < deadline:
            status, payload = request(service, str(wait_for["path"]), timeout=5)
            found = json_pointer(payload, str(wait_for["pointer"])) if status == 200 else None
            if (nonempty and bool(found)) or (has_equals and found is not None and found == wait_for["equals"]):
                break
            time.sleep(2)
        else:
            raise ServiceUnavailable(
                f"{service.name}: readiness data never appeared at {wait_for['path']} pointer {wait_for['pointer']}"
            )


def _seed_and_snapshot(service: Service, declared: Mapping[str, Any]) -> None:
    for step in declared.get("seed") or []:
        status, payload = request(service, str(step["path"]), str(step.get("method", "POST")), step.get("json"))
        if status == 0 or status >= 400:
            raise ServiceUnavailable(f"{service.name}: seed {step['path']} -> {status} {str(payload)[:200]}")
    for path in declared.get("snapshot") or []:
        status, payload = request(service, str(path))
        if status == 0 or status >= 400:
            raise ServiceUnavailable(f"{service.name}: snapshot {path} -> {status} {str(payload)[:200]}")
        service.snapshots[str(path)] = payload


def start_services(spec: Mapping[str, Any], docker: str = "docker") -> list[Service]:
    """Start each declared service, wait for its readiness path, seed it, and snapshot what must not change.

    A service that will not start, become ready, seed, snapshot, or start its audit proxy is harness
    breakage: the caller turns it into INCONCLUSIVE rather than a verdict about the agent.
    """
    # Routing and contract scenarios carry no fixture at all; the first live routing trial after
    # the consolidation died here with KeyError before any grade.
    declared_services = (spec.get("fixture") or {}).get("services") or []
    if not declared_services:
        return []
    started: list[Service] = []
    network_name = "save-toolkit-probe-" + secrets.token_hex(6)
    network_created = False
    pending_config_root: Path | None = None
    try:
        _docker(
            [docker, "network", "create", "--driver", "bridge", "--internal", network_name], "docker network create"
        )
        network_created = True
        for declared in declared_services:
            image = str(declared["image"])
            if "@sha256:" not in image:
                raise ServiceUnavailable(f"service image must be pinned by digest, got {image!r}")
            if image not in TRUSTED_SERVICE_IMAGES:
                raise ServiceUnavailable(f"service image has not been reviewed for this harness: {image!r}")
            name = str(declared["name"])
            if SERVICE_NAME.fullmatch(name) is None:
                raise ServiceUnavailable(f"service needs a canonical name, got {name!r}")
            # Recorded before anything is written into it, so a failure from here on removes it.
            pending_config_root = Path(tempfile.mkdtemp(prefix=f"build-probe-{name}-"))
            _write_service_files(pending_config_root, declared.get("files") or {})
            container_id = _docker(
                _service_command(docker, declared, network_name, pending_config_root), f"{name}: docker run"
            )
            service = Service(
                name,
                image,
                container_id,
                "",
                declared.get("auth"),
                network_name=network_name,
                config_root=pending_config_root,
            )
            started.append(service)
            pending_config_root = None
            _start_relay(service, declared, docker)
            _wait_until_ready(service, declared)
            _seed_and_snapshot(service, declared)
            _start_service_proxy(service)
        return started
    except BaseException as exc:  # an interrupt still stops what already started
        cleanup_error: ServiceUnavailable | None = None
        try:
            stop_services(started, docker)
        except ServiceUnavailable as cleanup_exc:
            cleanup_error = cleanup_exc
        if pending_config_root is not None:
            shutil.rmtree(pending_config_root, ignore_errors=True)
        if network_created and not started:
            try:
                _docker([docker, "network", "rm", network_name], f"docker network rm {network_name}")
            except ServiceUnavailable as cleanup_exc:
                cleanup_error = cleanup_exc
        if cleanup_error is not None:
            if not isinstance(exc, Exception):  # an interrupt stays an interrupt; the leftover is noted on it
                exc.add_note(f"service cleanup also failed: {cleanup_error}")
                raise
            raise ServiceUnavailable(f"{exc}; cleanup also failed: {cleanup_error}") from exc
        raise


def stop_proxies(services: list[Service]) -> None:
    """Stop agent request admission and settle every accepted request before grading reads state.

    Keep the proxy and its audit attached as evidence, and leave backing containers available for
    the checks' direct GETs. Repeating this at cleanup is harmless.
    """
    errors: list[str] = []
    for service in services:
        if service.proxy is not None and not service.proxy_stopped:
            try:
                service.proxy.shutdown()
                service.proxy.server_close()
                service.proxy_stopped = True
            except OSError as exc:
                errors.append(f"{service.name}: audit proxy did not settle: {exc}")
    if errors:
        raise ServiceUnavailable("; ".join(errors))


def stop_services(services: list[Service], docker: str = "docker") -> None:
    networks = {service.network_name for service in services if service.network_name}
    errors: list[str] = []
    try:
        stop_proxies(services)
    except ServiceUnavailable as exc:
        errors.append(str(exc))
    for service in services:
        for container_id in (service.relay_container_id, service.container_id):
            if not container_id:
                continue
            try:
                _docker([docker, "stop", "-t", "2", container_id], f"docker stop {container_id}")
            except ServiceUnavailable as exc:
                errors.append(str(exc))
        if service.config_root is not None:
            try:
                shutil.rmtree(service.config_root)
            except OSError as exc:
                errors.append(f"remove {service.config_root} failed: {exc}")
    for network_name in sorted(networks):
        try:
            _docker([docker, "network", "rm", network_name], f"docker network rm {network_name}")
        except ServiceUnavailable as exc:
            errors.append(str(exc))
    if errors:
        raise ServiceUnavailable("service cleanup failed: " + "; ".join(errors))


class ServiceUnavailable(RuntimeError):
    """A backing service could not be started, readied, or seeded — harness breakage, never a verdict."""


def json_pointer(payload: object, pointer: str) -> object:
    """Walk a slash-separated path through parsed JSON: `dashboard/version`, `0/message`.

    A missing path and an explicit JSON null both read as None, which is why validation refuses
    `equals: null`; a negative list index counts from the end.
    """
    node = payload
    for part in [p for p in pointer.split("/") if p]:
        if isinstance(node, list):
            if not part.lstrip("-").isdigit():
                return None
            index = int(part)
            node = node[index] if -len(node) <= index < len(node) else None
        elif isinstance(node, dict):
            node = node.get(part)
        else:
            return None
        if node is None:
            return None
    return node
