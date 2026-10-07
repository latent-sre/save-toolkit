"""Backing services a trial measures against: reviewed containers behind a loopback audit proxy.

A service that will not start, become ready, seed, snapshot or start its proxy is harness breakage,
reported as `ServiceUnavailable` and turned into INCONCLUSIVE by the caller, never a verdict.
"""

from __future__ import annotations

import base64
import contextlib
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
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(response_raw)

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = _forward

    try:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FixedTargetProxy)
    except OSError as exc:
        raise ServiceUnavailable(f"{service.name}: could not start loopback audit proxy: {exc}") from exc
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, name=f"build-probe-{service.name}", daemon=True)
    thread.start()
    service.proxy = server
    service.proxy_thread = thread
    service.agent_url = f"http://127.0.0.1:{server.server_address[1]}"


def _run_docker(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, capture_output=True, text=True)
    except OSError as exc:
        raise ServiceUnavailable(f"container runtime {command[0]!r} failed: {exc}") from exc


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
        network = _run_docker([docker, "network", "create", "--driver", "bridge", "--internal", network_name])
        if network.returncode != 0:
            raise ServiceUnavailable(f"docker network create failed: {network.stderr.strip()[:300]}")
        network_created = True
        for declared in declared_services:
            image = str(declared["image"])
            if "@sha256:" not in image:
                raise ServiceUnavailable(f"service image must be pinned by digest, got {image!r}")
            if image not in TRUSTED_SERVICE_IMAGES:
                raise ServiceUnavailable(f"service image has not been reviewed for this harness: {image!r}")
            name = str(declared["name"])
            if re.fullmatch(r"[a-z][a-z0-9-]{0,62}", name) is None:
                raise ServiceUnavailable(f"service needs a canonical name, got {name!r}")
            pending_config_root = Path(tempfile.mkdtemp(prefix=f"build-probe-{name}-"))
            for relative, content in (declared.get("files") or {}).items():
                target = pending_config_root / str(relative)
                if target.is_absolute() and not target.resolve().is_relative_to(pending_config_root.resolve()):
                    raise ServiceUnavailable(f"service file escapes its disposable root: {relative!r}")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(str(content), encoding="utf-8")
            command = [
                docker,
                "run",
                "-d",
                "--rm",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--pids-limit",
                "512",
                "--memory",
                "2g",
                "--network",
                network_name,
                "--network-alias",
                name,
            ]
            for key, value in (declared.get("env") or {}).items():
                command += ["-e", f"{key}={value}"]
            for mount in declared.get("mounts") or []:
                source = (pending_config_root / str(mount["source"])).resolve()
                if not source.is_relative_to(pending_config_root.resolve()) or not source.is_file():
                    raise ServiceUnavailable(
                        f"service mount source is not a declared runtime file: {mount['source']!r}"
                    )
                option = f"type=bind,source={source},target={mount['target']}"
                if mount.get("read_only") is True:
                    option += ",readonly"
                command += ["--mount", option]
            command.append(image)
            command.extend(str(item) for item in (declared.get("command") or []))
            run = _run_docker(command)
            if run.returncode != 0:
                raise ServiceUnavailable(f"{declared['name']}: docker run failed: {run.stderr.strip()[:300]}")
            container_id = run.stdout.strip()
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
            # Docker Desktop 29 suppresses host publication for containers on an --internal
            # network. Keep the service isolated and publish only a fixed-target TCP relay. The
            # relay has no target-selection input: every connection goes to this declared service.
            relay_command = [
                docker,
                "run",
                "-d",
                "--rm",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--pids-limit",
                "64",
                "--memory",
                "64m",
                "--read-only",
                "--user",
                "65534:65534",
                "-p",
                f"127.0.0.1::{SERVICE_RELAY_PORT}",
                SERVICE_RELAY_IMAGE,
                "python",
                "-I",
                "-S",
                "-B",
                "-c",
                SERVICE_RELAY_SCRIPT,
                name,
                str(int(declared.get("port", 80))),
            ]
            relay_run = _run_docker(relay_command)
            if relay_run.returncode != 0:
                raise ServiceUnavailable(f"{service.name}: relay docker run failed: {relay_run.stderr.strip()[:300]}")
            service.relay_container_id = relay_run.stdout.strip()
            connected = _run_docker(
                [
                    docker,
                    "network",
                    "connect",
                    "--alias",
                    f"relay-{name}",
                    network_name,
                    service.relay_container_id,
                ]
            )
            if connected.returncode != 0:
                raise ServiceUnavailable(
                    f"{service.name}: relay network connect failed: {connected.stderr.strip()[:300]}"
                )
            port_result = _run_docker(
                [
                    docker,
                    "port",
                    service.relay_container_id,
                    f"{SERVICE_RELAY_PORT}/tcp",
                ]
            )
            mapped = port_result.stdout.strip()
            if not mapped:
                raise ServiceUnavailable(f"{service.name}: no published port: {port_result.stderr.strip()[:300]}")
            service.base_url = "http://127.0.0.1:" + mapped.splitlines()[0].rsplit(":", 1)[1]
            deadline = time.time() + int(declared.get("ready_timeout", 120))
            ready_path = str(declared.get("ready", "/"))
            while time.time() < deadline:
                status, _ = request(service, ready_path, timeout=5)
                if status == 200:
                    break
                time.sleep(2)
            else:
                raise ServiceUnavailable(f"{service.name}: never became ready at {ready_path}")
            wait_for = declared.get("wait_for")
            if wait_for:
                while time.time() < deadline:
                    status, payload = request(service, str(wait_for["path"]), timeout=5)
                    found = json_pointer(payload, str(wait_for["pointer"])) if status == 200 else None
                    equals_ready = (
                        "equals" in wait_for
                        and wait_for["equals"] is not None
                        and isinstance(wait_for["equals"], (str, int, float, bool))
                        and found is not None
                        and found == wait_for["equals"]
                    )
                    if (wait_for.get("nonempty") is True and bool(found)) or equals_ready:
                        break
                    time.sleep(2)
                else:
                    raise ServiceUnavailable(
                        f"{service.name}: readiness data never appeared at {wait_for['path']} "
                        f"pointer {wait_for['pointer']}"
                    )
            for step in declared.get("seed") or []:
                status, payload = request(service, str(step["path"]), str(step.get("method", "POST")), step.get("json"))
                if status == 0 or status >= 400:
                    raise ServiceUnavailable(f"{service.name}: seed {step['path']} -> {status} {str(payload)[:200]}")
            for path in declared.get("snapshot") or []:
                status, payload = request(service, str(path))
                if status == 0 or status >= 400:
                    raise ServiceUnavailable(f"{service.name}: snapshot {path} -> {status} {str(payload)[:200]}")
                service.snapshots[str(path)] = payload
            _start_service_proxy(service)
        return started
    except Exception as exc:
        cleanup_error: ServiceUnavailable | None = None
        try:
            stop_services(started, docker)
        except ServiceUnavailable as cleanup_exc:
            cleanup_error = cleanup_exc
        if pending_config_root is not None:
            shutil.rmtree(pending_config_root, ignore_errors=True)
        if network_created and not started:
            try:
                removed = _run_docker([docker, "network", "rm", network_name])
                if removed.returncode != 0:
                    cleanup_error = ServiceUnavailable(
                        f"docker network rm {network_name} failed: {removed.stderr.strip()[:300]}"
                    )
            except ServiceUnavailable as cleanup_exc:
                cleanup_error = cleanup_exc
        if cleanup_error is not None:
            raise ServiceUnavailable(f"{exc}; cleanup also failed: {cleanup_error}") from exc
        raise


def stop_services(services: list[Service], docker: str = "docker") -> None:
    networks = {service.network_name for service in services if service.network_name}
    errors: list[str] = []
    for service in services:
        if service.proxy is not None:
            with contextlib.suppress(OSError):
                service.proxy.shutdown()
                service.proxy.server_close()
        for container_id in (service.relay_container_id, service.container_id):
            if not container_id:
                continue
            try:
                stopped = _run_docker([docker, "stop", "-t", "2", container_id])
                if stopped.returncode != 0:
                    errors.append(f"docker stop {container_id} failed: {stopped.stderr.strip()[:200]}")
            except ServiceUnavailable as exc:
                errors.append(str(exc))
        if service.config_root is not None:
            try:
                shutil.rmtree(service.config_root)
            except OSError as exc:
                errors.append(f"remove {service.config_root} failed: {exc}")
    for network_name in sorted(networks):
        try:
            removed = _run_docker([docker, "network", "rm", network_name])
            if removed.returncode != 0:
                errors.append(f"docker network rm {network_name} failed: {removed.stderr.strip()[:200]}")
        except ServiceUnavailable as exc:
            errors.append(str(exc))
    if errors:
        raise ServiceUnavailable("service cleanup failed: " + "; ".join(errors))


class ServiceUnavailable(RuntimeError):
    """A backing service could not be started, readied, or seeded — harness breakage, never a verdict."""


def json_pointer(payload: object, pointer: str) -> object:
    """Walk a slash-separated path through parsed JSON: `dashboard/version`, `0/message`."""
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
