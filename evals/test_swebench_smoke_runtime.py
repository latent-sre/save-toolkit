"""Model-free smoke orchestration across real selection, binding and receipts.

Only Docker transport and the independent verifier process are substituted. The
proxy, loopback upstream, mounted Bash guard, artifact screening and assessment
run normally; this suite does not claim that a real Docker engine is isolated.
"""

from __future__ import annotations

import hashlib
import io
import ipaddress
import json
import os
import shutil
import socket
import subprocess
import urllib.error
import urllib.request
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from probe.backing import SERVICE_RELAY_IMAGE
from swebench_adapter import configuration, proxy, runner, selection, smoke
from swebench_adapter.containers import Docker
from swebench_adapter.limits import ProcessResult

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "sha256:" + "a" * 64
REFERENCE = "registry.invalid/repair@sha256:" + "b" * 64
MODEL = "anthropic/claude-sonnet-5.5"
PATCH = "diff --git a/a b/a\n--- a/a\n+++ b/a\n@@ -1 +1 @@\n-bad\n+good\n"


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


class SmokeDocker(Docker):
    def __init__(self):
        super().__init__("wp08-smoke-offline-docker")
        self.calls = []
        self.resources = set()
        self.mounts = {}
        self.environment = {}
        self.setup_error = None
        self.cleanup_error = False
        self.baseline_resolves = False
        self.verifier_calls = []
        self.receipt_updates = {}
        self.processes = []
        self.fill_stdout = b'{"quota":true,"written":10200000000}'
        self.size = 10_737_418_241
        self.foreign_history = b""
        self.guard_unavailable = False
        self.proxy_port = None
        self.proxy_token = None
        self.connections = []

    def call(self, args, *, input=None, timeout=120, check=True):
        args = list(args)
        self.calls.append((args, input))
        code, out, err = 0, b"", b""
        if args[:2] == ["context", "inspect"]:
            out = json.dumps(
                [{"Name": "offline-local", "Endpoints": {"docker": {"Host": "unix:///var/run/docker.sock"}}}]
            ).encode()
        elif args[0] == "info":
            out = json.dumps(
                {
                    "ID": "offline-engine",
                    "ServerVersion": "28.5",
                    "OSType": "linux",
                    "OperatingSystem": "Offline Linux",
                    "KernelVersion": "6.0",
                    "Driver": "overlay2",
                }
            ).encode()
        elif args[:2] == ["image", "inspect"]:
            reference = args[-1]
            out = json.dumps(
                [{"Id": IMAGE if reference == REFERENCE else "sha256:" + "e" * 64, "RepoDigests": [reference]}]
            ).encode()
            assert reference in (REFERENCE, SERVICE_RELAY_IMAGE)
        elif args[:2] == ["network", "create"]:
            self.resources.add(("network", args[-1]))
        elif args[:2] == ["run", "-d"]:
            self.resources.add(("container", args[args.index("--name") + 1]))
            if "--mount" in args:
                for argument in args:
                    if argument.startswith("type=bind,"):
                        fields = dict(part.split("=", 1) for part in argument.split(",") if "=" in part)
                        self.mounts[fields["target"]] = fields["source"]
                self.environment = dict(args[i + 1].split("=", 1) for i, arg in enumerate(args) if arg == "--env")
                self.proxy_token = self.environment["ANTHROPIC_AUTH_TOKEN"]
            else:
                self.proxy_port = int(args[-1])
        elif args[:2] == ["network", "connect"]:
            pass
        elif args[0] == "inspect":
            if "--size" in args:
                out = str(self.size).encode()
            elif "--format" in args:
                out = b'"172.30.0.2"'
            else:
                out = json.dumps(
                    [
                        {
                            "HostConfig": {
                                "NanoCpus": 2_000_000_000,
                                "CapDrop": ["ALL"],
                                "CapAdd": None,
                                "Privileged": False,
                                "SecurityOpt": ["no-new-privileges"],
                                "Memory": 2_147_483_648,
                                "PidsLimit": 256,
                                "StorageOpt": {"size": "10G"},
                            },
                            "Mounts": [{"Destination": name, "RW": False} for name in self.mounts],
                        }
                    ]
                ).encode()
        elif len(args) > 1 and args[1] == "inspect" and args[0] in ("container", "network"):
            if (args[0], args[-1]) not in self.resources:
                code, err = 1, f"Error: No such {args[0]}: {args[-1]}".encode()
            else:
                out = json.dumps(
                    [
                        {
                            "Internal": True,
                            "EnableIPv6": False,
                            "Options": {"com.docker.network.bridge.gateway_mode_ipv4": "isolated"},
                        }
                    ]
                ).encode()
        elif args[0] == "rm" or args[:2] == ["network", "rm"]:
            if self.cleanup_error:
                code, err = 1, b"offline removal failed"
            else:
                self.resources.discard(("container" if args[0] == "rm" else "network", args[-1]))
        elif args[0] == "exec":
            if args[-1] == "--version":
                out = b"2.1.99\n"
            elif args[-2:] == ["/bin/sh", "-s"]:
                assert b"git" in input and b"reflog expire" in input
                if self.setup_error:
                    raise self.setup_error
            elif "rev-list" in args:
                out = self.foreign_history
            elif args[-2] == "-c" and args[-3] == "bash":
                env = {**os.environ, "CLAUDE_PLUGIN_ROOT": self.mounts["/opt/fleet"]}
                if self.guard_unavailable:
                    env["CLAUDE_PLUGIN_ROOT"] += "/missing"
                result = subprocess.run(
                    ["bash", "-c", args[-1]], input=input, capture_output=True, env=env, check=False, timeout=10
                )
                code, out, err = result.returncode, result.stdout, result.stderr
            elif args[-3:-1] == ["python3", "-c"]:
                script = args[-1]
                if "socket.getaddrinfo" in script:
                    request = urllib.request.Request(
                        f"http://127.0.0.1:{self.proxy_port}/v1/messages",
                        data=json.dumps(
                            {"model": MODEL, "messages": [{"role": "user", "content": "smoke"}], "max_tokens": 1}
                        ).encode(),
                        headers={"Authorization": "Bearer " + self.proxy_token, "Content-Type": "application/json"},
                    )
                    with urllib.request.urlopen(request, timeout=5) as response:
                        success = json.load(response).get("wp08_model_free_smoke") is True
                    request = urllib.request.Request(
                        f"http://127.0.0.1:{self.proxy_port}/api/v1/key",
                        headers={"Authorization": "Bearer " + self.proxy_token},
                    )
                    with pytest.raises(urllib.error.HTTPError) as rejected:
                        urllib.request.urlopen(request, timeout=5)
                    assert rejected.value.code >= 400
                    out = json.dumps(
                        {"proxy": success, "internet": False, "host": False, "dns": False, "key_route": False}
                    ).encode()
                else:
                    assert "getrusage" in script
                    out = b'{"wall_seconds":5,"cpu_seconds":9.5}'
            else:
                raise AssertionError(f"Unexpected Docker exec: {args!r}")
        else:
            raise AssertionError(f"Unexpected Docker call: {args!r}")
        if check and code:
            raise RuntimeError("offline Docker transport failed")
        return subprocess.CompletedProcess(args, code, out, err)


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    plugin = tmp_path / "plugin"
    for name in ("agents", "skills", "commands", "hooks", "scripts", ".claude-plugin"):
        (plugin / name).mkdir(parents=True)
    (plugin / ".claude-plugin/plugin.json").write_text('{"name":"save-toolkit"}')
    (plugin / "agents/software-engineer.md").write_text(
        "---\nname: software-engineer\ntools: Bash\n---\nStatic repair.\n"
    )
    for name in (
        "hooks/hooks.json",
        "scripts/fleet_frontmatter.py",
        "scripts/readonly-guard.py",
        "scripts/readonly-guard-hook.sh",
    ):
        shutil.copy2(ROOT / name, plugin / name)
    cli = tmp_path / "claude"
    cli.write_bytes(b"\x7fELFoffline-smoke-cli")
    rows = [
        {
            "instance_id": f"org__repo{i:02}-1",
            "repo": f"org/repo{i:02}",
            "version": "1.0",
            "base_commit": "c" * 40,
            "difficulty": "<15 min fix",
            "problem_statement": "Public bug description",
            "FAIL_TO_PASS": ["test_bug"],
            "PASS_TO_PASS": ["test_existing"],
            "image": REFERENCE,
            "eval_script": "PRIVATE VERIFIER SCRIPT",
            "log_parser": "pytest",
            "eval_type": "pass_and_fail",
            "patch": PATCH,
            "test_patch": "PRIVATE TEST PATCH",
            "hints_text": "PRIVATE HINTS",
        }
        for i in range(10)
    ]
    manifest = selection.select_tasks(rows, "d" * 40, {row["repo"]: "BSD-3-Clause" for row in rows})
    config = {
        "schema_version": 1,
        "plugin_root": str(plugin),
        "cli_path": str(cli),
        "cli_sha256": hashlib.sha256(cli.read_bytes()).hexdigest(),
        "cli_version": "2.1.99",
        "model": MODEL,
        "haiku_model": "anthropic/claude-haiku-4.5",
        "images": {row["instance_id"]: {"reference": REFERENCE, "image_id": IMAGE} for row in rows},
        "proxy_bind": "127.0.0.1",
        "proxy_target": "host.docker.internal",
        "storage_quota": True,
        "api_key_helper": False,
    }
    docker = SmokeDocker()
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    monkeypatch.delenv("DOCKER_CONTEXT", raising=False)
    monkeypatch.setattr(smoke, "Docker", lambda: docker)
    monkeypatch.setattr(configuration.shutil, "which", lambda name: "/offline/docker")
    monkeypatch.setattr(configuration.metadata, "version", lambda name: "5.0.2")

    def forbidden(*args, **kwargs):
        raise AssertionError("Model-free smoke must not read a key or query provider usage")

    monkeypatch.setattr(runner, "read_key", forbidden)
    monkeypatch.setattr(proxy, "read_key", forbidden)
    monkeypatch.setattr(proxy.ModelProxy, "usage", forbidden)
    real_connection = socket.create_connection

    def loopback_only(address, *args, **kwargs):
        assert ipaddress.ip_address(address[0]).is_loopback, "model-free smoke attempted external networking"
        docker.connections.append(address)
        return real_connection(address, *args, **kwargs)

    monkeypatch.setattr(socket, "create_connection", loopback_only)

    def process(args, **kwargs):
        assert len(args) >= 2 and str(args[1]).endswith("/swebench_adapter/verifier.py")
        assert kwargs["timeout"] == 2700
        assert not any(name.startswith(("ANTHROPIC_", "OPENROUTER_")) for name in kwargs["env"])
        fields = {
            name: args[args.index(name) + 1]
            for name in ("--task", "--patch", "--output", "--run-id", "--image-digest", "--engine-id", "--docker-host")
        }
        assert fields["--engine-id"] == "offline-engine"
        assert fields["--docker-host"] == "unix:///var/run/docker.sock"
        assert docker.argv == [docker.executable, "--host", fields["--docker-host"]]
        assert ("--storage-quota" in args) is config["storage_quota"]
        task = json.loads(Path(fields["--task"]).read_text())
        patch = Path(fields["--patch"]).read_bytes()
        baseline = "--baseline" in args
        docker.verifier_calls.append({"task": task, "patch": patch, "baseline": baseline, "args": args})
        resolved = docker.baseline_resolves if baseline else True
        status = 0 if resolved else 1
        output = Path(fields["--output"])
        raw = {
            task["instance_id"]: {
                "patch_is_None": False,
                "patch_exists": True,
                "patch_successfully_applied": True,
                "resolved": resolved,
                "infra_failure": False,
                "tests_status": {
                    field: {
                        "success": task[field] if resolved or field == "PASS_TO_PASS" else [],
                        "failure": task[field] if not resolved and field == "FAIL_TO_PASS" else [],
                    }
                    for field in ("FAIL_TO_PASS", "PASS_TO_PASS")
                },
            }
        }
        receipt = {
            "instance_id": task["instance_id"],
            "base_commit": task["base_commit"],
            "baseline": baseline,
            "interrupted": False,
            "docker_engine_id": "offline-engine",
            "docker_endpoint": "unix:///var/run/docker.sock",
            "observed_base_commit": task["base_commit"],
            "initial_state": {
                "head": task["base_commit"],
                "tracked_clean": True,
                "index_clean": True,
                "replace_objects_disabled": True,
                "untracked_policy": "preserved",
            },
            "storage_quota": "--storage-quota" in args,
            "patch_sha256": hashlib.sha256(patch).hexdigest(),
            "swebench_version": "5.0.2",
            "verifier_image_digest": IMAGE,
            "command": args,
            "exit_status": status,
            "report_path": "verifier-report.json",
            "evaluated_at": datetime.now(UTC).isoformat(),
            "outcome": "PASS" if resolved else "FAIL",
            "reason": None if resolved else "one required test failed",
            "cleanup": [
                {
                    "name": f"sweb.eval.{task['instance_id'].lower()}.{fields['--run-id']}",
                    "present": False,
                    "removed": True,
                }
            ],
        }
        receipt.update(docker.receipt_updates)
        dump(output / "verifier-report.json", raw)
        dump(output / "verifier-receipt.json", receipt)
        return ProcessResult(b"", b"", status, None, 0.01)

    monkeypatch.setattr(runner, "run_bounded", process)
    real_popen = subprocess.Popen

    def popen(args, **kwargs):
        if args[0] != docker.executable:
            return real_popen(args, **kwargs)
        assert args[: len(docker.argv)] == docker.argv
        assert args[len(docker.argv)] == "exec" and args[-1] == smoke._STORAGE_PROBE

        class Process:
            stdout = io.BytesIO(docker.fill_stdout)
            stderr = io.BytesIO(b"")
            returncode = 0 if config["storage_quota"] else None
            killed = False

            def poll(self):
                return self.returncode

            def kill(self):
                self.killed = True
                self.returncode = -9

            def wait(self, timeout=None):
                return self.returncode

        result = Process()
        docker.processes.append(result)
        return result

    monkeypatch.setattr(subprocess, "Popen", popen)
    return SimpleNamespace(config=config, manifest=manifest, rows=rows, docker=docker, output=tmp_path / "smoke")


def run(runtime):
    return smoke.run_smoke(runtime.config, runtime.manifest, runtime.rows, runtime.output)


def observations(runtime):
    return json.loads((runtime.output / "observations.json").read_text())


def test_model_free_smoke_runs_reference_and_baseline_with_real_binding_and_artifacts(runtime):
    receipt = run(runtime)
    assert receipt["error"] is None
    assert all(receipt["checks"].values())
    assert (
        configuration.smoke_problem(receipt, runner.runtime_binding(runtime.config, runtime.manifest, runtime.docker))
        is None
    )
    reference, empty = runtime.docker.verifier_calls
    assert reference["task"] == empty["task"] == runtime.rows[0]
    assert reference["patch"] == PATCH.encode() and reference["baseline"] is False
    assert empty["patch"] == b"" and empty["baseline"] is True
    assert "--baseline" in empty["args"] and "--baseline" not in reference["args"]
    assert observations(runtime)["empty"]["outcome"] == "FAIL"
    assert not runtime.docker.resources
    assert len(receipt["cleanup"]) == 7
    assert all(item["present"] is False for item in receipt["cleanup"])
    assert runtime.docker.connections
    assert json.loads((runtime.output / "smoke.json").read_text()) == receipt


def test_unexpected_resolved_empty_baseline_is_not_rewritten_to_failure(runtime):
    runtime.docker.baseline_resolves = True
    receipt = run(runtime)
    assert observations(runtime)["empty"]["outcome"] == "PASS"
    assert receipt["checks"]["empty_rejected"] is False
    assert "empty_rejected" in configuration.smoke_problem(receipt, receipt["binding"])
    assert receipt["checks"]["cleanup"] is True


def test_guard_wrapper_zero_exit_with_deny_json_is_interpreted_as_deny(runtime):
    receipt = run(runtime)
    observed = observations(runtime)
    assert observed["guard_allow"] == {"returncode": 0, "stdout": ""}
    deny = observed["guard_deny"]
    assert deny["returncode"] == 0
    assert json.loads(deny["stdout"])["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert receipt["checks"]["guard_allow"] and receipt["checks"]["guard_deny"]


def test_guard_wrapper_unavailable_cannot_satisfy_expected_credential_denial(runtime):
    runtime.docker.guard_unavailable = True
    receipt = run(runtime)
    assert "unavailable" in observations(runtime)["guard_deny"]["stdout"]
    assert not receipt["checks"]["guard_deny"]
    assert not receipt["checks"]["guard_allow"]
    assert receipt["checks"]["cleanup"]


def test_storage_watchdog_stop_comes_from_real_execute_and_still_cleans(runtime):
    runtime.config["storage_quota"] = False
    receipt = run(runtime)
    assert observations(runtime)["storage"] == {"stop": "storage_limit", "quota_rejected": False}
    assert receipt["checks"]["storage_cap"] and receipt["checks"]["cleanup"]
    assert runtime.docker.processes[0].killed
    assert any(args[:3] == ["inspect", "--size", "--format"] for args, _ in runtime.docker.calls)
    assert not runtime.docker.resources


@pytest.mark.parametrize("payload", [b'{"quota":true,"written":100}', b'{"quota":false,"written":10200000000}'])
def test_quota_needs_an_actual_fill_at_the_approved_cap(runtime, payload):
    runtime.docker.fill_stdout = payload
    receipt = run(runtime)
    assert not receipt["checks"]["storage_cap"]
    assert receipt["checks"]["cleanup"]


@pytest.mark.parametrize('written, accepted', [(10_737_418_240, True), (10_737_418_241, False)])
def test_quota_acceptance_uses_binary_docker_size(runtime, written, accepted):
    runtime.docker.fill_stdout = json.dumps({'quota': True, 'written': written}).encode()
    receipt = run(runtime)
    assert receipt['checks']['storage_cap'] is accepted


@pytest.mark.parametrize(
    "error,reason",
    [(RuntimeError("offline setup failed"), "setup or measurement failed"), (KeyboardInterrupt(), "interrupted")],
)
def test_setup_failure_or_interrupt_retains_receipt_and_cleans_all_started_resources(runtime, error, reason):
    runtime.docker.setup_error = error
    receipt = run(runtime)
    assert reason in receipt["error"]
    assert receipt["checks"]["reference_resolves"] and receipt["checks"]["empty_rejected"]
    assert not receipt["checks"]["storage_cap"]
    assert receipt["checks"]["cleanup"]
    assert all(item["present"] is False for item in receipt["cleanup"])
    assert not runtime.docker.resources
    assert len(runtime.docker.verifier_calls) == 2
    assert (runtime.output / "smoke.json").is_file()


def test_unremoved_resource_prevents_smoke_acceptance(runtime):
    runtime.docker.cleanup_error = True
    receipt = run(runtime)
    assert not receipt["checks"]["cleanup"]
    assert any(item["present"] is True for item in receipt["cleanup"])
    assert "cleanup" in configuration.smoke_problem(receipt, receipt["binding"])


def test_unresolved_verifier_process_cleanup_stops_before_next_control(runtime, monkeypatch):
    process = runner.run_bounded
    def unresolved(*args, **kwargs):
        return replace(process(*args, **kwargs), cleanup_complete=False, stop="cleanup_failure", pid=12345)
    monkeypatch.setattr(runner, "run_bounded", unresolved)
    receipt = run(runtime)
    assert len(runtime.docker.verifier_calls) == 1
    assert receipt["checks"]["cleanup"] is False
    assert any(item.get("kind") == "host_process" and item["present"] is None for item in receipt["cleanup"])


def test_changed_frozen_task_is_refused_before_docker_or_output(runtime):
    runtime.rows[0]["patch"] += "changed"
    with pytest.raises(ValueError, match="manifest"):
        run(runtime)
    assert not runtime.docker.calls
    assert not runtime.output.exists()


@pytest.mark.skipif(os.name != "posix", reason="POSIX private mode assertions")
def test_smoke_evidence_is_private_and_gold_inputs_never_enter_agent_mounts(runtime):
    run(runtime)
    assert runtime.output.stat().st_mode & 0o777 == 0o700
    for path in runtime.output.rglob("*"):
        if path.is_file():
            assert path.stat().st_mode & 0o077 == 0
    agent_args = next(args for args, _ in runtime.docker.calls if args[:2] == ["run", "-d"] and "--mount" in args)
    assert sum(arg.startswith("type=bind,") for arg in agent_args) == 2
    assert "PRIVATE" not in str(agent_args)
    assert runtime.docker.environment["ANTHROPIC_API_KEY"] == ""
    assert "wp08-model-free-host-credential" not in str(runtime.docker.environment)
    for path in runtime.output.rglob("*"):
        if path.is_file():
            assert b"PRIVATE HINTS" not in path.read_bytes()
            assert b"PRIVATE TEST PATCH" not in path.read_bytes()


def test_reachable_future_history_prevents_smoke_acceptance(runtime):
    runtime.docker.foreign_history = b"future-commit-still-reachable\n"
    receipt = run(runtime)
    assert observations(runtime)["history_pruned"] is False
    assert receipt["checks"]["history_pruned"] is False
    assert receipt["checks"]["cleanup"] is True


def test_cr_bytes_in_a_staged_script_prevent_smoke_acceptance(runtime):
    script = Path(runtime.config["plugin_root"]) / "scripts/readonly-guard-hook.sh"
    script.write_bytes(script.read_bytes().replace(b"\n", b"\r\n"))
    receipt = run(runtime)
    assert observations(runtime)["no_cr"] is False
    assert receipt["checks"]["no_cr"] is False
    assert receipt["checks"]["cleanup"] is True


@pytest.mark.parametrize(
    "field,value",
    [
        ("docker_engine_id", "another-engine"),
        ("docker_endpoint", "unix:///other/docker.sock"),
        ("observed_base_commit", "f" * 40),
        (
            "initial_state",
            {
                "head": "c" * 40,
                "tracked_clean": False,
                "index_clean": True,
                "replace_objects_disabled": True,
                "untracked_policy": "preserved",
            },
        ),
    ],
)
def test_verifier_engine_base_and_initial_state_attestation_must_match_smoke(runtime, field, value):
    runtime.docker.receipt_updates[field] = value
    receipt = run(runtime)
    observed = observations(runtime)
    assert observed["reference"]["outcome"] == "INCONCLUSIVE"
    assert observed["empty"]["outcome"] == "INCONCLUSIVE"
    assert receipt["checks"]["reference_resolves"] is False
    assert receipt["checks"]["empty_rejected"] is False
    assert configuration.smoke_problem(receipt, receipt["binding"]) is not None
    assert receipt["checks"]["cleanup"] is True
    assert not runtime.docker.resources
