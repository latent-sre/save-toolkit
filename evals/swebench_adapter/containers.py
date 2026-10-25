"""Bounded Docker resources for the isolated static-repair adapter."""

from __future__ import annotations

import ipaddress
import json
import math
import re
import subprocess
import threading
import time
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from probe.backing import SERVICE_RELAY_IMAGE, SERVICE_RELAY_SCRIPT

STDOUT_LIMIT = 64 * 1024 * 1024
STDERR_LIMIT = 1024 * 1024
STORAGE_LIMIT = 10_000_000_000
STORAGE_INTERVAL = 60.0
_NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,62}")
_IMAGE = re.compile(r"(?:[A-Za-z0-9][A-Za-z0-9._:/-]*@)?sha256:[0-9a-f]{64}")
_CREDENTIAL = re.compile(r"sk-|gh[pousr]_|AKIA|ASIA|ya29\.|-----BEGIN .*PRIVATE KEY")


class Docker:
    """Small argv-only Docker boundary with bounded, output-free failures."""

    def __init__(self, docker_executable: str = "docker") -> None:
        if not docker_executable or "\x00" in docker_executable:
            raise ValueError("Docker executable is required")
        self.executable = docker_executable
        self._endpoint: str | None = None

    @property
    def argv(self) -> list[str]:
        """Return a fresh command prefix, with an immutable daemon binding if pinned."""
        return [self.executable] if self._endpoint is None else [self.executable, "--host", self._endpoint]

    def pin(self, endpoint: str) -> None:
        """Bind this attempt to one explicit local daemon, independent of CLI context."""
        if (
            not isinstance(endpoint, str)
            or not endpoint
            or any(not char.isprintable() or char.isspace() for char in endpoint)
            or any(char in endpoint for char in "@?#%")
            or _CREDENTIAL.search(endpoint)
        ):
            raise ValueError("Docker endpoint must be a credential-free local socket or named pipe")
        local_unix = (
            endpoint.startswith("unix:///") and not endpoint.startswith("unix:////") and not endpoint.endswith("/")
        )
        local_pipe = re.fullmatch(r"npipe:////\./pipe/[A-Za-z0-9_.-]+", endpoint) is not None
        if not local_unix and not local_pipe:
            raise ValueError("Docker endpoint must be a local unix socket or named pipe")
        if self._endpoint is not None and endpoint != self._endpoint:
            raise ValueError("Docker endpoint is already pinned for this attempt")
        self._endpoint = endpoint

    def call(
        self,
        args: Sequence[str],
        *,
        input: bytes | None = None,
        timeout: float = 120,
        check: bool = True,
    ) -> subprocess.CompletedProcess[bytes]:
        try:
            result = subprocess.run(
                [*self.argv, *args],
                input=input,
                capture_output=True,
                timeout=timeout,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Docker command timed out") from None
        except OSError:
            raise RuntimeError("Docker command could not start") from None
        if check and result.returncode:
            raise RuntimeError(f"Docker command failed (exit {result.returncode})")
        return result


@dataclass(frozen=True)
class Execution:
    stdout: bytes
    stderr: bytes
    returncode: int
    stop: str | None
    seconds: float


def git_prune_script(base_commit: str) -> str:
    """Remove all future Git reachability in the disposable image's /testbed."""
    if re.fullmatch(r"[0-9a-f]{40}", base_commit) is None:
        raise ValueError("base_commit must be an immutable 40-character commit")
    return f"""set -eu
cd /testbed
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_TERMINAL_PROMPT=0 GIT_NO_REPLACE_OBJECTS=1
g() {{ git -c core.hooksPath=/dev/null -c core.fsmonitor=false "$@"; }}
g checkout --detach --force {base_commit}
g reset --hard {base_commit}
g clean -ffdqx
refs=$(g for-each-ref --format='%(refname)')
printf '%s\\n' "$refs" | while IFS= read -r ref; do
    if [ -n "$ref" ]; then g update-ref -d "$ref"; fi
done
remotes=$(g remote)
printf '%s\\n' "$remotes" | while IFS= read -r remote; do
    if [ -n "$remote" ]; then g remote remove "$remote"; fi
done
for ref in ORIG_HEAD FETCH_HEAD MERGE_HEAD AUTO_MERGE; do
    rm -f -- "$(g rev-parse --git-path "$ref")"
done
g reflog expire --expire=now --expire-unreachable=now --all
g gc --prune=now
test "$(g rev-parse HEAD)" = {base_commit}
test -z "$(g symbolic-ref -q HEAD || :)"
test -z "$(g for-each-ref)"
test -z "$(g status --porcelain)"
test -z "$(g rev-list --all --not {base_commit})"
"""


class DockerResources:
    """Track names before mutations and keep ownership until absence is inspected."""

    def __init__(self, docker: Docker, prefix: str) -> None:
        if not isinstance(prefix, str) or re.fullmatch(r"[a-z0-9][a-z0-9-]{0,47}", prefix) is None:
            raise ValueError("resource prefix must be a unique safe attempt name")
        self.docker = docker
        self.prefix = prefix
        self._containers: list[str] = []
        self._networks: list[str] = []

    def _own(self, kind: str) -> str:
        name = f"{self.prefix}-{kind}"
        resources = self._networks if kind == "network" else self._containers
        if name in resources:
            raise ValueError("resource creation was already attempted for this name")
        if self._present("network" if kind == "network" else "container", name) is not False:
            raise RuntimeError("resource name already exists or absence could not be verified")
        resources.append(name)
        return name

    def _container(self, name: str) -> None:
        if name not in self._containers:
            raise ValueError("container is not owned by this attempt")

    def _network(self, name: str) -> None:
        if name not in self._networks:
            raise ValueError("network is not owned by this attempt")

    def internal_network(self) -> str:
        name = self._own("network")
        self.docker.call(
            [
                "network",
                "create",
                "--driver",
                "bridge",
                "--internal",
                "--opt",
                "com.docker.network.bridge.gateway_mode_ipv4=isolated",
                name,
            ]
        )
        return name

    @staticmethod
    def _hardening(pids: int, memory: str) -> list[str]:
        return [
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            str(pids),
            "--memory",
            memory,
            "--cpus",
            "2",
        ]

    def start_relay(self, network: str, target_host: str, port: int) -> str:
        self._network(network)
        if not isinstance(target_host, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", target_host) is None:
            raise ValueError("relay target must be a fixed host name or IPv4 address")
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("relay port is invalid")
        name = self._own("relay")
        self.docker.call(
            [
                "run",
                "-d",
                "--name",
                name,
                "--network",
                "bridge",
                *self._hardening(64, "64m"),
                "--read-only",
                "--user",
                "65534:65534",
                "--sysctl",
                "net.ipv4.ip_forward=0",
                "--add-host",
                "host.docker.internal:host-gateway",
                SERVICE_RELAY_IMAGE,
                "python",
                "-I",
                "-S",
                "-B",
                "-c",
                SERVICE_RELAY_SCRIPT,
                target_host,
                str(port),
            ]
        )
        self.docker.call(["network", "connect", network, name])
        result = self.docker.call(
            [
                "inspect",
                "--format",
                '{{json (index .NetworkSettings.Networks "' + network + '").IPAddress}}',
                name,
            ]
        )
        try:
            address = ipaddress.IPv4Address(json.loads(result.stdout))
            if address.is_unspecified or address.is_multicast or address.is_loopback:
                raise ValueError
        except (ValueError, TypeError):
            raise RuntimeError("relay internal IPv4 evidence is invalid") from None
        return str(address)

    def start_agent(
        self,
        network: str,
        image: str,
        cli: Path,
        plugin: Path,
        env: Mapping[str, str],
        proxy_ip: str,
        *,
        storage_quota: bool,
    ) -> str:
        if not isinstance(image, str) or _IMAGE.fullmatch(image) is None:
            raise ValueError("agent image must be an immutable sha256 image identity")
        environment: list[str] = []
        for key, value in env.items():
            if (
                not isinstance(key, str)
                or re.fullmatch(r"[A-Z][A-Z0-9_]*", key) is None
                or not isinstance(value, str)
                or "\x00" in value
                or _CREDENTIAL.search(value)
            ):
                raise ValueError("invalid or credential-shaped agent environment")
            environment.extend(["--env", f"{key}={value}"])
        self._network(network)
        try:
            address = ipaddress.IPv4Address(proxy_ip)
            if address.is_unspecified or address.is_loopback or address.is_multicast:
                raise ValueError
        except (ValueError, TypeError):
            raise ValueError("proxy_ip must be an internal IPv4 address") from None
        cli, plugin = cli.resolve(strict=True), plugin.resolve(strict=True)
        if (
            not cli.is_file()
            or not plugin.is_dir()
            or any(char in str(cli) + str(plugin) for char in (",", "\n", "\r"))
        ):
            raise ValueError("CLI and plugin must be valid frozen bind sources")
        name = self._own("agent")
        quota = ["--storage-opt", "size=10G"] if storage_quota else []
        self.docker.call(
            [
                "run",
                "-d",
                "--name",
                name,
                "--network",
                network,
                *self._hardening(256, "2g"),
                "--dns",
                "127.0.0.1",
                "--add-host",
                f"model-proxy:{address}",
                *quota,
                "--mount",
                f"type=bind,source={cli},target=/opt/claude,readonly",
                "--mount",
                f"type=bind,source={plugin},target=/opt/fleet,readonly",
                *environment,
                "--workdir",
                "/testbed",
                "--entrypoint",
                "/bin/sleep",
                image,
                "infinity",
            ]
        )
        return name

    def setup_repository(self, container: str, base_commit: str) -> None:
        self._container(container)
        self.docker.call(["exec", "-i", container, "/bin/sh", "-s"], input=git_prune_script(base_commit).encode())

    def _present(self, kind: str, name: str) -> bool | None:
        try:
            result = self.docker.call([kind, "inspect", name], check=False, timeout=10)
        except (RuntimeError, OSError):
            return None
        if result.returncode == 0:
            try:
                evidence = json.loads(result.stdout)
                return True if isinstance(evidence, list) and evidence else None
            except (ValueError, TypeError):
                return None
        error = result.stderr.decode("utf-8", "replace").lower()
        if result.returncode == 1 and (
            "no such object:" in error
            or "no such container:" in error
            or "no such network:" in error
            or f"network {name} not found" in error
        ):
            return False
        return None

    def cleanup(self) -> list[dict[str, Any]]:
        receipt: list[dict[str, Any]] = []
        for kind, names in (("container", self._containers), ("network", self._networks)):
            for name in reversed(names):
                try:
                    argv = ["rm", "--force", name] if kind == "container" else ["network", "rm", name]
                    removed = self.docker.call(argv, check=False, timeout=20).returncode == 0
                except (RuntimeError, OSError):
                    removed = False
                receipt.append({"kind": kind, "name": name, "present": self._present(kind, name), "removed": removed})
        return receipt

    def _size(self, container: str, timeout: float) -> int:
        result = self.docker.call(["inspect", "--size", "--format", "{{json .SizeRw}}", container], timeout=timeout)
        try:
            size = json.loads(result.stdout)
        except (ValueError, TypeError):
            raise RuntimeError("writable-layer measurement is invalid") from None
        if type(size) is not int or size < 0:
            raise RuntimeError("writable-layer measurement is unavailable")
        return size

    def execute(
        self,
        container: str,
        argv: Sequence[str],
        *,
        wall_seconds: float = 2700,
        storage_quota: bool = False,
    ) -> Execution:
        """Drain bounded streams while enforcing wall time and exact writable size."""
        self._container(container)
        if not math.isfinite(wall_seconds) or not 0 < wall_seconds <= 2700:
            raise ValueError("execution wall limit must be positive and at most 2700 seconds")
        if not argv or any(not isinstance(arg, str) or "\x00" in arg for arg in argv):
            raise ValueError("execution requires an argv sequence")
        started = time.monotonic()
        try:
            process = subprocess.Popen(
                [*self.docker.argv, "exec", container, *argv],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
            )
        except OSError:
            raise RuntimeError("Docker execution could not start") from None
        stdout, stderr = bytearray(), bytearray()
        overflow, read_failure = threading.Event(), threading.Event()

        def drain(stream: BinaryIO | None, output: bytearray, limit: int) -> None:
            if stream is None:
                read_failure.set()
                return
            try:
                while chunk := stream.read(65536):
                    remaining = limit - len(output)
                    output.extend(chunk[:remaining])
                    if len(chunk) > remaining:
                        overflow.set()
            except (OSError, ValueError):
                read_failure.set()
            finally:
                stream.close()

        threads = [
            threading.Thread(target=drain, args=(stream, output, limit), daemon=True)
            for stream, output, limit in (
                (process.stdout, stdout, STDOUT_LIMIT),
                (process.stderr, stderr, STDERR_LIMIT),
            )
        ]
        stop: str | None = None
        for thread in threads:
            thread.start()
        next_storage = started
        try:
            while True:
                now = time.monotonic()
                if overflow.is_set():
                    stop = "output_limit"
                    break
                if read_failure.is_set():
                    stop = "monitor_failure"
                    break
                if now - started >= wall_seconds:
                    stop = "wall_clock"
                    break
                if not storage_quota and now >= next_storage:
                    try:
                        if self._size(container, min(10, max(0.01, wall_seconds - (now - started)))) > STORAGE_LIMIT:
                            stop = "storage_limit"
                            break
                    except (RuntimeError, OSError):
                        stop = "monitor_failure"
                        break
                    next_storage = now + STORAGE_INTERVAL
                if time.monotonic() - started >= wall_seconds:
                    stop = "wall_clock"
                    break
                if process.poll() is not None:
                    break
                time.sleep(min(0.05, max(0, wall_seconds - (time.monotonic() - started))))
        except KeyboardInterrupt:
            stop = "interrupted"
        finally:
            if stop:
                self._halt(process, container)
            for thread in threads:
                thread.join(timeout=1)
            if not stop and (
                overflow.is_set() or read_failure.is_set() or any(thread.is_alive() for thread in threads)
            ):
                stop = "output_limit" if overflow.is_set() else "monitor_failure"
                self._halt(process, container)
        return Execution(
            bytes(stdout),
            bytes(stderr),
            process.returncode if process.returncode is not None else -1,
            stop,
            time.monotonic() - started,
        )

    def _halt(self, process: subprocess.Popen[bytes], container: str) -> None:
        with suppress(OSError):
            process.kill()
        # The caller's final cleanup receipt must still prove absence.
        with suppress(RuntimeError, OSError):
            self.docker.call(["rm", "--force", container], timeout=20, check=False)
        with suppress(subprocess.TimeoutExpired, OSError):
            process.wait(timeout=5)
