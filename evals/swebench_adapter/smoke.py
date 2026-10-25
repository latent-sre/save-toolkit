"""Model-free, observed acceptance controls for the owner-started WP-08 smoke."""

from __future__ import annotations

import json
import math
import secrets
import socket
import tempfile
import threading
import uuid
from collections.abc import Mapping
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from probe import fingerprints
from probe.records import utc_now

from .artifacts import store_json
from .configuration import dependency_problems
from .containers import Docker, DockerResources
from .limits import STORAGE_LIMIT
from .proxy import ModelProxy
from .selection import resolve_task


def _object(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _clean(value: object) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, dict) and item.get("present") is False for item in value)
    )


def assess_smoke(observed: Mapping[str, Any], cleanup: list[dict[str, Any]]) -> dict[str, bool]:
    reference, empty = _object(observed.get("reference")), _object(observed.get("empty"))
    allow, deny = _object(observed.get("guard_allow")), _object(observed.get("guard_deny"))
    try:
        denial = _object(json.loads(deny.get("stdout", ""))).get("hookSpecificOutput", {})
    except (ValueError, TypeError):
        denial = {}
    denial = _object(denial)
    reason = str(denial.get("permissionDecisionReason", "")).lower()
    cpu = _object(observed.get("cpu"))
    wall, used = cpu.get("wall_seconds"), cpu.get("cpu_seconds")
    measured_cpu = (
        isinstance(wall, (int, float))
        and not isinstance(wall, bool)
        and isinstance(used, (int, float))
        and not isinstance(used, bool)
        and math.isfinite(wall)
        and math.isfinite(used)
        and wall > 0
        and 0 < used <= wall * 2.2
    )
    container = _object(observed.get("container"))
    host = _object(container.get("HostConfig"))
    mounts = container.get("Mounts")
    bounded = (
        host.get("NanoCpus") == 2_000_000_000
        and host.get("CapDrop") == ["ALL"]
        and not host.get("CapAdd")
        and host.get("Privileged") is False
        and any(str(option).startswith("no-new-privileges") for option in host.get("SecurityOpt", []))
    )
    memory, pids = host.get("Memory"), host.get("PidsLimit")
    bounded = bounded and type(memory) is int and 0 < memory <= 2_147_483_648 and type(pids) is int and 0 < pids <= 256
    mount_check = (
        isinstance(mounts, list)
        and len(mounts) == 2
        and all(isinstance(mount, dict) and mount.get("RW") is False for mount in mounts)
    )
    if mount_check and isinstance(mounts, list):
        mount_check = {mount["Destination"] for mount in mounts} == {"/opt/claude", "/opt/fleet"}
    network, egress = _object(observed.get("network")), _object(observed.get("egress"))
    isolated = (
        network.get("Internal") is True
        and network.get("EnableIPv6") is False
        and _object(network.get("Options")).get("com.docker.network.bridge.gateway_mode_ipv4") == "isolated"
    )
    storage = _object(observed.get("storage"))
    return {
        "reference_resolves": reference.get("outcome") == "PASS" and _clean(reference.get("cleanup")),
        "empty_rejected": empty.get("outcome") == "FAIL"
        and empty.get("baseline") is True
        and _clean(empty.get("cleanup")),
        "guard_allow": allow.get("returncode") == 0 and allow.get("stdout") == "",
        "guard_deny": (
            deny.get("returncode") == 0
            and denial.get("permissionDecision") == "deny"
            and "credential" in reason
            and "unavailable" not in reason
            and "failed" not in reason
        ),
        "no_cr": observed.get("no_cr") is True,
        "history_pruned": observed.get("history_pruned") is True,
        "egress": isolated
        and egress.get("proxy") is True
        and all(egress.get(name) is False for name in ("internet", "host", "dns", "key_route")),
        "cpu_cap": bool(measured_cpu and bounded and mount_check),
        "storage_cap": storage.get("stop") == "storage_limit" or storage.get("quota_rejected") is True,
        "cleanup": _clean(cleanup),
    }


def cpu_probe(seconds: float = 5.0) -> str:
    """Observe aggregate child CPU against elapsed time inside the capped container."""
    if not 0 < seconds <= 10:
        raise ValueError("CPU probe duration must be between zero and ten seconds")
    return f"""import json, multiprocessing, resource, time
def burn():
    end = time.monotonic() + {seconds!r}
    while time.monotonic() < end:
        pass
start = time.monotonic()
children = [multiprocessing.get_context('fork').Process(target=burn) for _ in range(4)]
for child in children:
    child.start()
for child in children:
    child.join()
assert all(child.exitcode == 0 for child in children)
usage = resource.getrusage(resource.RUSAGE_CHILDREN)
print(json.dumps({{'wall_seconds': time.monotonic()-start, 'cpu_seconds': usage.ru_utime+usage.ru_stime}}))
"""


def _egress_probe(model: str, token: str, host: str, port: int) -> str:
    data = json.dumps({"model": model, "token": token, "host": host, "port": port})
    return f"""import json, socket, urllib.request, urllib.error
c = json.loads({data!r})
request = urllib.request.Request('http://model-proxy:8080/v1/messages', data=json.dumps({{'model':c['model'],'messages':[{{'role':'user','content':'smoke'}}],'max_tokens':1}}).encode(), headers={{'Authorization':'Bearer '+c['token'],'Content-Type':'application/json'}})
with urllib.request.urlopen(request, timeout=10) as response:
    proxy = json.load(response).get('wp08_model_free_smoke') is True
def connects(host, port):
    try:
        with socket.create_connection((host,port),timeout=2):
            return True
    except OSError:
        return False
try:
    socket.getaddrinfo('example.com',443)
    dns = True
except OSError:
    dns = False
try:
    request = urllib.request.Request('http://model-proxy:8080/api/v1/key',headers={{'Authorization':'Bearer '+c['token']}})
    with urllib.request.urlopen(request,timeout=5) as response:
        key_route = response.status < 400
except urllib.error.HTTPError:
    key_route = False
print(json.dumps({{'proxy':proxy,'internet':connects('1.1.1.1',443),'host':connects(c['host'],c['port']),'dns':dns,'key_route':key_route}}))
"""


_STORAGE_PROBE = f"""import errno, json, time
size = 0
try:
    with open('/testbed/.wp08-storage-probe','wb',buffering=0) as stream:
        block = bytes(1024*1024)
        while size < {STORAGE_LIMIT + 100 * 1024**2}:
            size += stream.write(block)
    time.sleep(90)
    print(json.dumps({{'quota':False,'written':size}}))
except OSError as error:
    print(json.dumps({{'quota':error.errno in (errno.ENOSPC,errno.EDQUOT),'written':size}}))
"""


class _SmokeUpstream:
    """Local-only model substitute; the smoke never contacts a model provider."""

    def __init__(self) -> None:
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                self.rfile.read(min(length, 65536))
                body = b'{"wp08_model_free_smoke":true}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def port(self) -> int:
        return int(self.server.server_address[1])

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def _port_present(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except ConnectionRefusedError:
        return False


def run_smoke(
    config: Mapping[str, Any], manifest: Mapping[str, Any], rows: list[dict[str, Any]], output: Path
) -> dict[str, Any]:
    from .runner import agent_environment, image_identity, runtime_binding, verify_patch  # noqa: PLC0415

    problems = dependency_problems()
    if problems:
        raise ValueError("; ".join(problems))
    task = resolve_task(manifest, rows, manifest["tasks"][0]["instance_id"])
    docker = Docker()
    bound = runtime_binding(config, manifest, docker)
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    resources = DockerResources(docker, "wp08-" + uuid.uuid4().hex)
    observed: dict[str, Any] = {}
    cleanup: list[dict[str, Any]] = []
    error: str | None = None
    upstream: _SmokeUpstream | None = None
    proxy: ModelProxy | None = None
    proxy_port: int | None = None
    try:
        image = image_identity(docker, config, task["instance_id"])
        observed["reference"] = verify_patch(
            task,
            task["patch"],
            output / "reference",
            "wp08-" + uuid.uuid4().hex,
            image,
            docker,
            storage_quota=config["storage_quota"],
        )
        if not _clean(observed["reference"].get("cleanup")):
            raise RuntimeError("reference verifier cleanup unresolved")
        observed["empty"] = verify_patch(
            task,
            "",
            output / "empty",
            "wp08-" + uuid.uuid4().hex,
            image,
            docker,
            baseline=True,
            storage_quota=config["storage_quota"],
        )
        if not _clean(observed["reference"].get("cleanup")) or not _clean(observed["empty"].get("cleanup")):
            raise RuntimeError("verifier cleanup unresolved")
        upstream = _SmokeUpstream()
        token = secrets.token_hex(32)
        proxy = ModelProxy(
            "wp08-model-free-host-credential",
            token,
            [config["model"], config["haiku_model"]],
            bind_host=config["proxy_bind"],
            upstream_origin=f"http://127.0.0.1:{upstream.port}",
        )
        proxy.start()
        proxy_port = proxy.port
        with tempfile.TemporaryDirectory(prefix="wp08-plugin-") as temporary:
            plugin = fingerprints.stage_plugin(Path(config["plugin_root"]), Path(temporary) / "plugin")
            observed["no_cr"] = not any(
                b"\r" in path.read_bytes()
                for path in plugin.rglob("*")
                if path.is_file() and path.suffix in {".py", ".sh", ".ps1"}
            )
            network = resources.internal_network()
            relay = resources.start_relay(network, config["proxy_target"], proxy.port)
            container = resources.start_agent(
                network,
                image,
                Path(config["cli_path"]),
                plugin,
                agent_environment(config, token),
                relay,
                storage_quota=config["storage_quota"],
            )
            resources.setup_repository(container, task["base_commit"])
            version = docker.call(["exec", container, "/opt/claude", "--version"]).stdout.decode().strip()
            if version != config["cli_version"]:
                raise RuntimeError("mounted CLI version differs from the frozen configuration")
            history = docker.call(
                ["exec", "-w", "/testbed", container, "git", "rev-list", "--all", "--not", task["base_commit"]]
            )
            observed["history_pruned"] = history.returncode == 0 and not history.stdout.strip()
            hooks = json.loads((plugin / "hooks/hooks.json").read_text())["hooks"]
            bash_hooks = [
                hook["command"]
                for entry in hooks["PreToolUse"]
                if entry["matcher"] == "Bash"
                for hook in entry["hooks"]
            ]
            if len(bash_hooks) != 1:
                raise RuntimeError("smoke requires the reviewed single Bash guard command")
            for name, command in (("guard_allow", "git status --short"), ("guard_deny", "cf env")):
                payload = json.dumps(
                    {
                        "agent_type": "save-toolkit:software-engineer",
                        "tool_name": "Bash",
                        "tool_input": {"command": command},
                    }
                ).encode()
                result = docker.call(
                    ["exec", "-i", "-e", "CLAUDE_PLUGIN_ROOT=/opt/fleet", container, "bash", "-c", bash_hooks[0]],
                    input=payload,
                    check=False,
                )
                observed[name] = {"returncode": result.returncode, "stdout": result.stdout.decode().strip()}
            observed["container"] = json.loads(docker.call(["inspect", container]).stdout)[0]
            observed["network"] = json.loads(docker.call(["network", "inspect", network]).stdout)[0]
            for name, script in (
                ("egress", _egress_probe(config["model"], token, config["proxy_bind"], proxy.port)),
                ("cpu", cpu_probe()),
            ):
                result = docker.call(["exec", container, "python3", "-c", script], timeout=45)
                observed[name] = json.loads(result.stdout)
            fill = resources.execute(
                container, ["python3", "-c", _STORAGE_PROBE], wall_seconds=150, storage_quota=config["storage_quota"]
            )
            try:
                filled = json.loads(fill.stdout)
            except ValueError:
                filled = {}
            storage_opt = _object(_object(observed["container"].get("HostConfig")).get("StorageOpt"))
            observed["storage"] = {
                "stop": fill.stop,
                "quota_rejected": bool(
                    config["storage_quota"]
                    and fill.returncode == 0
                    and filled.get("quota") is True
                    and type(filled.get("written")) is int
                    and STORAGE_LIMIT * 9 // 10 <= filled["written"] <= STORAGE_LIMIT
                    and storage_opt.get("size") == "10G"
                ),
            }
    except (ValueError, OSError, RuntimeError, KeyError, TypeError):
        error = "smoke setup or measurement failed; inspect the retained observations"
    except KeyboardInterrupt:
        error = "smoke interrupted"
    finally:
        cleanup.extend(resources.cleanup())
        for control in ("reference", "empty"):
            cleanup.extend(_object(observed.get(control)).get("cleanup", []))
        if proxy is not None:
            proxy.close()
            if proxy_port is not None:
                try:
                    present: bool | None = _port_present(config["proxy_bind"], proxy_port)
                except OSError:
                    present = None
                cleanup.append(
                    {"kind": "proxy", "name": "model-free-proxy", "present": present, "removed": present is False}
                )
        if upstream is not None:
            port = upstream.port
            upstream.close()
            try:
                present = _port_present("127.0.0.1", port)
            except OSError:
                present = None
            cleanup.append(
                {"kind": "proxy", "name": "model-free-upstream", "present": present, "removed": present is False}
            )
    checks = assess_smoke(observed, cleanup)
    receipt = {
        "format": "wp08-smoke",
        "schema_version": 1,
        "binding": bound,
        "checks": checks,
        "cleanup": cleanup,
        "observed_at": utc_now(),
        "error": error,
    }
    store_json(output, "observations.json", observed)
    store_json(output, "smoke.json", receipt)
    return receipt
