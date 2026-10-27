"""Runner lifecycle tests retaining real selection, binding, staging and records."""

from __future__ import annotations

import copy
import hashlib
import io
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path, PureWindowsPath
from types import SimpleNamespace

import pytest
from probe.backing import SERVICE_RELAY_IMAGE
from probe.constants import BUILD_TOOLS
from probe.records import RecordV1
from swebench_adapter import configuration, runner, selection
from swebench_adapter.limits import ProcessResult

IMAGE = "sha256:" + "a" * 64
REFERENCE = "registry.test/repair@sha256:" + "b" * 64
MODEL = "anthropic/claude-sonnet-5.5"
KEY = "offline-test-key-not-a-real-credential"
PATCH = "diff --git a/a b/a\n--- a/a\n+++ b/a\n@@ -1 +1 @@\n-bad\n+good\n"


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def trace(model=MODEL, subtype="success", denials=None):
    return ("\n".join(json.dumps(event) for event in [
        {"type": "system", "subtype": "init", "model": model, "tools": list(BUILD_TOOLS),
         "plugins": [{"name": "save-toolkit", "path": "/opt/fleet"}], "mcp_servers": [], "session_id": "offline"},
        {"type": "result", "subtype": subtype, "result": "Static repair left for independent verification.",
         "num_turns": 3, "modelUsage": {model: {}}, "total_cost_usd": 0.25,
         "permission_denials": denials or []},
    ]) + "\n").encode()


class FakeDocker:
    executable = "docker-offline-fixture"

    def __init__(self):
        self.calls = []
        self.resources = set()
        self.trace = trace()
        self.stderr = b""
        self.patch = PATCH.encode()
        self.returncode = 0
        self.running = False
        self.size = 0
        self.cleanup_error = False
        self.unknown_inspect = False
        self.version = "2.1.99"
        self.image_id = IMAGE
        self.digests = [REFERENCE]
        self.setup_error = False
        self.setup_interrupt = False
        self.agent_interrupt = False
        self.engine_id = "offline-engine"
        self.relay_id = "sha256:" + "e" * 64
        self.endpoint = "unix:///var/run/docker.sock"
        self.engine_os = "linux"
        self.pinned = None

    def pin(self, endpoint):
        if self.pinned is not None and self.pinned != endpoint:
            raise ValueError("different endpoint")
        self.pinned = endpoint

    @property
    def argv(self):
        return [self.executable] + (["--host", self.pinned] if self.pinned else [])

    def call(self, args, *, input=None, timeout=120, check=True):
        self.calls.append((list(args), input))
        code, out, err = 0, b"", b""
        if args[:2] == ["image", "inspect"]:
            out = json.dumps([{"Id": self.relay_id, "RepoDigests": [SERVICE_RELAY_IMAGE]}]
                if args[-1] == SERVICE_RELAY_IMAGE else [{"Id": self.image_id, "RepoDigests": self.digests}]).encode()
        elif args[0] == "info":
            out = json.dumps({"ID": self.engine_id, "ServerVersion": "28.5", "OSType": self.engine_os,
                "OperatingSystem": "Offline Fixture", "KernelVersion": "6.0", "Driver": "overlay2"}).encode()
        elif args[:2] == ["context", "inspect"]:
            out = json.dumps([{"Name": "offline-local", "Endpoints": {"docker": {"Host": self.endpoint}}}]).encode()
        elif args[:2] == ["network", "create"]:
            self.resources.add(("network", args[-1]))
        elif args[:2] == ["run", "-d"]:
            self.resources.add(("container", args[args.index("--name") + 1]))
        elif args[0] == "inspect" and "--size" in args:
            out = str(self.size).encode()
        elif args[0] == "inspect":
            out = b'"172.30.0.2"'
        elif len(args) >= 2 and args[1] == "inspect" and args[0] in ("container", "network"):
            if self.unknown_inspect:
                code, err = 1, b"Cannot connect to Docker daemon"
            elif (args[0], args[-1]) in self.resources:
                out = b'[{"Id":"offline-resource"}]'
            else:
                code, err = 1, f"Error: No such {args[0]}: {args[-1]}".encode()
        elif args[0] == "rm" or args[:2] == ["network", "rm"]:
            kind = "container" if args[0] == "rm" else "network"
            if self.cleanup_error:
                code, err = 1, b"removal failed"
            else:
                self.resources.discard((kind, args[-1]))
        elif args[0] == "exec":
            if input and self.setup_interrupt:
                raise KeyboardInterrupt
            if input and self.setup_error:
                raise RuntimeError("offline setup failed")
            if args[-1] == "--version":
                out = (self.version + "\n").encode()
            elif "diff" in args:
                out = self.patch
            elif args[-1] == "uname -s; uname -r; uname -m; id -u; hostname":
                out = b"Linux\noffline-release\nx86_64\n0\noffline-container\n"
        if check and code:
            raise RuntimeError("offline Docker failure")
        return subprocess.CompletedProcess(args, code, out, err)


class FakeProxy:
    instances = []
    usage_rows = None
    fail_auth = False

    def __init__(self, key, token, models, *, bind_host):
        assert key == KEY
        assert token != key
        self.token, self.models, self.bind_host = token, models, bind_host
        self.port = 12345
        self.auth_failed = self.fail_auth
        self.started = self.closed = False
        self.reads = 0
        self.instances.append(self)

    def start(self):
        self.started = True

    def close(self):
        self.closed = True

    def usage(self):
        rows = self.usage_rows or [{"usage": 1.0, "limit": 30.0, "limit_remaining": 29.0},
                                   {"usage": 1.5, "limit": 30.0, "limit_remaining": 28.5}]
        row = rows[min(self.reads, len(rows) - 1)]
        self.reads += 1
        if isinstance(row, Exception):
            raise row
        return copy.deepcopy(row)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    plugin = tmp_path / "plugin"
    for name in ("agents", "skills", "commands", "hooks"):
        (plugin / name).mkdir(parents=True)
    (plugin / "agents/software-engineer.md").write_text(
        "---\nname: software-engineer\ntools: " + ", ".join(BUILD_TOOLS) + "\n---\nStatic repair.\n")
    for name, text in ((".claude-plugin/plugin.json", '{"name":"save-toolkit"}'),
                       ("scripts/fleet_frontmatter.py", "# fixture\n"),
                       ("scripts/readonly-guard.py", "# fixture\n"),
                       ("scripts/readonly-guard-hook.sh", "#!/bin/sh\nexit 42\n")):
        path = plugin / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, newline="\n")
    subprocess.run(["git", "init", "-q", str(plugin)], check=True)
    subprocess.run(["git", "-C", str(plugin), "add", "."], check=True)
    subprocess.run(["git", "-C", str(plugin), "-c", "user.name=Offline Fixture",
                    "-c", "user.email=fixture@example.invalid", "commit", "-qm", "offline fixture"], check=True)
    cli = tmp_path / "claude"
    cli.write_bytes(b"\x7fELFoffline fixture")
    cli.chmod(0o700)
    rows = [{"instance_id": f"org__repo{i:02}-1", "repo": f"org/repo{i:02}", "version": "1.0",
             "base_commit": "c" * 40, "difficulty": "<15 min fix", "problem_statement": "Public bug description",
             "FAIL_TO_PASS": ["test_bug"], "PASS_TO_PASS": ["test_existing"], "image": REFERENCE,
             "eval_script": "PRIVATE VERIFIER SCRIPT", "log_parser": "pytest", "eval_type": "pass_and_fail",
             "patch": "PRIVATE GOLD PATCH", "test_patch": "PRIVATE TEST PATCH", "hints_text": "PRIVATE HINTS"}
            for i in range(10)]
    manifest = selection.select_tasks(rows, "d" * 40, {row["repo"]: "BSD-3-Clause" for row in rows})
    config = {"schema_version": 1, "plugin_root": str(plugin), "cli_path": str(cli),
              "cli_sha256": hashlib.sha256(cli.read_bytes()).hexdigest(), "cli_version": "2.1.99",
              "model": MODEL, "haiku_model": "anthropic/claude-haiku-4.5",
              "images": {row["instance_id"]: {"reference": REFERENCE, "image_id": IMAGE} for row in rows},
              "proxy_bind": "172.18.0.1", "proxy_target": "host.docker.internal", "storage_quota": True,
              "api_key_helper": False}
    docker = FakeDocker()
    smoke = {"format": "wp08-smoke", "schema_version": 1, "binding": runner.runtime_binding(config, manifest, docker),
             "checks": {name: True for name in configuration._CHECKS},
             "cleanup": [{"name": "offline-smoke", "present": False, "removed": True}]}
    key_file = tmp_path / "protected-key"
    key_file.write_text(KEY)
    key_file.chmod(0o600)
    monkeypatch.setattr(runner, "Docker", lambda: docker)
    monkeypatch.setattr(runner, "ModelProxy", FakeProxy)
    FakeProxy.instances = []
    monkeypatch.setattr(FakeProxy, "usage_rows", None)
    monkeypatch.setattr(FakeProxy, "fail_auth", False)
    monkeypatch.setattr(configuration.shutil, "which", lambda name: "/offline/docker")
    monkeypatch.setattr(configuration.metadata, "version", lambda name: "5.0.2")
    real_popen = subprocess.Popen

    def popen(args, **kwargs):
        if args[0] != docker.executable:
            return real_popen(args, **kwargs)
        class Process:
            stdout = io.BytesIO(docker.patch if "diff" in args else b"" if "git" in args else docker.trace)
            stderr = io.BytesIO(docker.stderr)
            returncode = None if docker.running else docker.returncode
            def poll(self):
                if docker.agent_interrupt:
                    raise KeyboardInterrupt
                return self.returncode
            def kill(self):
                self.returncode = -9
            def wait(self, timeout=None):
                return self.returncode
        return Process()

    monkeypatch.setattr(subprocess, "Popen", popen)
    real_run = subprocess.run

    def process(args, **kwargs):
        if len(args) < 2 or not str(args[1]).endswith("/swebench_adapter/verifier.py"):
            return real_run(args, **kwargs)
        assert kwargs["timeout"] == 2700
        assert KEY not in str(kwargs.get("env", {}))
        assert "ANTHROPIC_AUTH_TOKEN" not in kwargs.get("env", {})
        parsed = {args[i]: args[i + 1] for i in range(2, len(args) - 1, 2)}
        task = json.loads(Path(parsed["--task"]).read_text())
        patch = Path(parsed["--patch"]).read_bytes()
        out = Path(parsed["--output"])
        raw = {task["instance_id"]: {"patch_is_None": False, "patch_exists": True,
               "patch_successfully_applied": True, "resolved": True, "infra_failure": False,
               "tests_status": {field: {"success": task[field], "failure": []}
                                for field in ("FAIL_TO_PASS", "PASS_TO_PASS")}}}
        receipt = {"instance_id": task["instance_id"], "base_commit": task["base_commit"],
                   "observed_base_commit": task["base_commit"], "initial_state": {
                       "head": task["base_commit"], "tracked_clean": True, "index_clean": True,
                       "replace_objects_disabled": True, "untracked_policy": "preserved"},
                   "docker_engine_id": docker.engine_id, "docker_endpoint": docker.endpoint,
                   "interrupted": False, "storage_quota": "--storage-quota" in args,
                   "baseline": "--baseline" in args,
                   "patch_sha256": hashlib.sha256(patch).hexdigest(), "swebench_version": "5.0.2",
                   "verifier_image_digest": IMAGE, "command": args, "exit_status": 0,
                   "report_path": "verifier-report.json", "evaluated_at": datetime.now(UTC).isoformat(),
                   "outcome": "PASS", "reason": None,
                   "cleanup": [{"name": f"sweb.eval.{task['instance_id'].lower()}.{parsed['--run-id']}",
                                "present": False, "removed": True}]}
        dump(out / "verifier-report.json", raw)
        dump(out / "verifier-receipt.json", receipt)
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"", stop=None, seconds=0.01)

    monkeypatch.setattr(runner, "run_bounded", process, raising=False)
    return SimpleNamespace(config=config, manifest=manifest, rows=rows, smoke=smoke, key_file=key_file,
                           docker=docker, output=tmp_path / "results", tmp=tmp_path)


def trial(setup):
    return runner.run_trial(setup.config, setup.manifest, setup.rows, setup.rows[0]["instance_id"],
                            setup.output, setup.key_file, setup.smoke)


def folder(setup):
    return setup.output / f"eval-{setup.rows[0]['instance_id']}" / "claude/run-1"


def test_agent_environment_and_command_never_inherit_host_credentials(setup, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "parent-credential")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "parent-credential")
    env = runner.agent_environment(setup.config, "attempt-placeholder")
    assert env["ANTHROPIC_AUTH_TOKEN"] == "attempt-placeholder"
    assert env["ANTHROPIC_API_KEY"] == ""
    assert env["ANTHROPIC_BASE_URL"] == "http://model-proxy:8080"
    assert env["ANTHROPIC_DEFAULT_SONNET_MODEL"] == MODEL
    assert env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == setup.config["haiku_model"]
    assert "parent-credential" not in str(env)
    command = runner.agent_command(setup.config, setup.rows[0])
    assert command[0] == "/opt/claude"
    assert command[command.index("--agent") + 1] == "save-toolkit:software-engineer"
    assert command[command.index("--max-turns") + 1] == "64"
    assert command[command.index("--permission-mode") + 1] == "dontAsk"
    assert {"WebFetch", "WebSearch"} <= set(command[command.index("--disallowedTools") + 1].split(","))
    prompt = command[command.index("-p") + 1]
    assert "Public bug description" in prompt and "no commit" in prompt.lower()
    assert all(secret not in str(command) for secret in ("PRIVATE GOLD", "PRIVATE TEST", "PRIVATE HINTS", "PRIVATE VERIFIER"))
    setup.config["api_key_helper"] = True
    command = runner.agent_command(setup.config, setup.rows[0])
    settings = json.loads(command[command.index("--settings") + 1])
    assert "ANTHROPIC_AUTH_TOKEN" in settings["apiKeyHelper"]
    assert "attempt-placeholder" not in settings["apiKeyHelper"]


def test_image_requires_pinned_repository_digest_and_matching_observed_id(setup):
    instance = setup.rows[0]["instance_id"]
    assert runner.image_identity(setup.docker, setup.config, instance) == IMAGE
    setup.docker.digests = ["other@sha256:" + "e" * 64]
    with pytest.raises(ValueError):
        runner.image_identity(setup.docker, setup.config, instance)


def test_trial_writes_real_v1_record_billing_and_private_screened_evidence(setup):
    summary = trial(setup)
    assert summary["status"] == "PASS"
    assert summary["measured_usd"] == 0.5
    assert summary["billing_known"] and summary["cleanup_ok"]
    record = RecordV1.model_validate_json((folder(setup) / "record.json").read_text())
    assert record.conditions.execution_profile.authentication == "openrouter-host-proxy"
    assert record.cost.trial_usd == 0.25
    assert record.runner.runner_source_sha256 == setup.smoke["binding"]["adapter_sha256"]
    billing = json.loads((folder(setup) / "billing.json").read_text())
    assert billing["measured_usd"] == 0.5 and billing["complete"] is True
    assert json.loads((folder(setup) / "policy-review.json").read_text())["status"] == "unreviewed"
    assert not setup.docker.resources and not (setup.output / "pending-cleanup.json").exists()
    assert FakeProxy.instances[0].closed
    assert all(KEY.encode() not in path.read_bytes() for path in setup.output.rglob("*") if path.is_file())
    mounts = next(args for args, _ in setup.docker.calls if args[:2] == ["run", "-d"] and "--mount" in args)
    assert sum(arg.startswith("type=bind") for arg in mounts) == 2
    assert "PRIVATE" not in str(mounts)
    receipt = json.loads((folder(setup) / "verifier/verifier-receipt.json").read_text())
    assert receipt["host_cleanup_complete"] is True and receipt["stop"] is None


def test_smoke_gate_precedes_key_read_and_proxy_start(setup):
    setup.key_file.unlink()
    setup.smoke["checks"]["egress"] = False
    with pytest.raises(ValueError, match="smoke"):
        trial(setup)
    assert not FakeProxy.instances


@pytest.mark.parametrize("field,value", [("engine_id", "another-engine"), ("relay_id", "sha256:" + "f" * 64)])
def test_smoke_is_bound_to_current_engine_and_relay(setup, field, value):
    setattr(setup.docker, field, value)
    with pytest.raises(ValueError, match="smoke binding"):
        trial(setup)
    assert not FakeProxy.instances


def test_smoke_is_bound_to_observed_host_identity(setup, monkeypatch):
    monkeypatch.setattr(runner.fingerprints.socket, "gethostname", lambda: "another-host")
    with pytest.raises(ValueError, match="smoke binding"):
        trial(setup)
    assert not FakeProxy.instances


@pytest.mark.parametrize("field,value", [("endpoint", "tcp://remote.example:2375"), ("engine_os", "windows")])
def test_remote_or_non_linux_engine_is_refused_before_key(setup, field, value):
    setattr(setup.docker, field, value)
    with pytest.raises(ValueError, match="Docker"):
        trial(setup)
    assert not FakeProxy.instances


@pytest.mark.parametrize("metadata", [
    {"usage": 0, "limit": None, "limit_remaining": None},
    {"usage": 0, "limit": 31, "limit_remaining": 31},
    {"usage": 30, "limit": 30, "limit_remaining": 0},
])
def test_unknown_or_exhausted_key_budget_stops_before_agent(setup, monkeypatch, metadata):
    monkeypatch.setattr(FakeProxy, "usage_rows", [metadata])
    result = trial(setup)
    assert result["status"] == "INCONCLUSIVE" and result["budget_exhausted"]
    assert not any(args[:2] == ["run", "-d"] for args, _ in setup.docker.calls)
    assert FakeProxy.instances[0].closed


@pytest.mark.parametrize("payload,ending,status", [(b"", "cut_short", "INCONCLUSIVE"),
    (trace(model="wrong-model"), "void", "INCONCLUSIVE"),
    (trace(subtype="error_max_turns"), "turn_limit", "FAIL"),
    (trace(denials=[{"tool_name": "Bash"}]), "cut_short", "INCONCLUSIVE")])
def test_missing_trace_identity_turn_budget_and_denial_classification(setup, payload, ending, status):
    setup.docker.trace = payload
    if ending == "turn_limit":
        setup.docker.patch = b""
    result = trial(setup)
    assert (result["ending"], result["status"]) == (ending, status)
    assert result["cleanup_ok"] and FakeProxy.instances[0].closed


def test_empty_patch_after_normal_run_is_fail(setup):
    setup.docker.patch = b""
    assert trial(setup)["status"] == "FAIL"


@pytest.mark.parametrize("where", ["trace", "stderr", "patch"])
def test_disclosure_is_rejected_before_candidate_bytes_are_persisted(setup, where):
    setattr(setup.docker, where, KEY.encode())
    result = trial(setup)
    assert result["status"] == "INCONCLUSIVE"
    assert all(KEY.encode() not in path.read_bytes() for path in setup.output.rglob("*") if path.is_file())
    assert FakeProxy.instances[0].closed


def test_failed_cleanup_blocks_next_call_until_fresh_absence(setup):
    setup.docker.cleanup_error = True
    result = trial(setup)
    assert not result["cleanup_ok"]
    assert (setup.output / "pending-cleanup.json").is_file()
    before = len(FakeProxy.instances)
    next_id = setup.rows[1]["instance_id"]
    with pytest.raises(ValueError, match="cleanup"):
        runner.run_trial(setup.config, setup.manifest, setup.rows, next_id, setup.output, setup.key_file, setup.smoke)
    assert len(FakeProxy.instances) == before
    setup.docker.resources.clear()
    setup.docker.cleanup_error = False
    result = runner.run_trial(setup.config, setup.manifest, setup.rows, next_id,
                              setup.output, setup.key_file, setup.smoke)
    assert result["status"] == "PASS"


def test_unknown_inspect_error_does_not_clear_pending_cleanup(setup):
    setup.output.mkdir()
    dump(setup.output / "pending-cleanup.json", [{"kind": "container", "name": "wp08-old-agent"}])
    setup.docker.unknown_inspect = True
    with pytest.raises(ValueError, match="cleanup"):
        trial(setup)
    assert (setup.output / "pending-cleanup.json").is_file()
    assert not FakeProxy.instances


def test_setup_failure_keeps_record_billing_and_cleanup(setup):
    setup.docker.setup_error = True
    result = trial(setup)
    assert result["status"] == "INCONCLUSIVE" and result["environment_failure"]
    assert (folder(setup) / "record.json").is_file()
    assert (folder(setup) / "billing.json").is_file()
    assert not setup.docker.resources and FakeProxy.instances[0].closed


def test_missing_hard_quota_is_inconclusive_and_retains_cleanup(setup):
    setup.config["storage_quota"] = False
    setup.smoke["binding"] = runner.runtime_binding(setup.config, setup.manifest, setup.docker)
    setup.docker.running = True
    setup.docker.size = 10_737_418_241
    result = trial(setup)
    assert result["status"] == "INCONCLUSIVE"
    assert result["cleanup_ok"]
    assert not setup.docker.resources


def test_wall_clock_stop_is_inconclusive_and_retains_cleanup(setup, monkeypatch):
    ticks = iter((0, 2701, 2702))
    monkeypatch.setattr(time, "monotonic", lambda: next(ticks, 2703))
    setup.docker.running = True
    result = trial(setup)
    assert result["status"] == "INCONCLUSIVE" and result["stop"] == "wall_clock"
    assert result["cleanup_ok"]


def test_mounted_cli_version_mismatch_is_void(setup):
    setup.docker.version = "unexpected-version"
    result = trial(setup)
    assert result["ending"] == "void" and result["identity_mismatch"]
    assert result["status"] == "INCONCLUSIVE" and result["cleanup_ok"]


def test_cr_script_is_refused_before_key_access(setup):
    script = Path(setup.config["plugin_root"]) / "scripts/readonly-guard-hook.sh"
    script.write_bytes(script.read_bytes().replace(b"\n", b"\r\n"))
    setup.key_file.unlink()
    result = trial(setup)
    assert result["status"] == "INCONCLUSIVE"
    assert not FakeProxy.instances


def test_authentication_failure_stops_trial_and_is_explicit(setup, monkeypatch):
    monkeypatch.setattr(FakeProxy, "fail_auth", True)
    result = trial(setup)
    assert result["status"] == "INCONCLUSIVE" and result["auth_failed"]
    assert not any(args[:2] == ["run", "-d"] for args, _ in setup.docker.calls)


def test_trial_refuses_overwrite(setup):
    trial(setup)
    with pytest.raises(ValueError, match="already"):
        trial(setup)
    assert len(FakeProxy.instances) == 1


def test_batch_requires_first_trial_then_runs_remaining_nine_serially(setup):
    with pytest.raises(ValueError, match="first"):
        runner.run_batch(setup.config, setup.manifest, setup.rows, setup.output, setup.key_file, setup.smoke)
    trial(setup)
    results = runner.run_batch(setup.config, setup.manifest, setup.rows, setup.output, setup.key_file, setup.smoke)
    assert len(results) == 10
    assert [r["instance_id"] for r in results] == [r["instance_id"] for r in setup.manifest["tasks"]]
    assert all(proxy.closed for proxy in FakeProxy.instances)


def test_batch_stops_after_three_consecutive_environment_failures(setup):
    trial(setup)
    setup.docker.setup_error = True
    results = runner.run_batch(setup.config, setup.manifest, setup.rows, setup.output, setup.key_file, setup.smoke)
    assert len(results) == 4


def test_first_trial_over_two_dollars_blocks_batch(setup):
    trial(setup)
    path = folder(setup) / "billing.json"
    billing = json.loads(path.read_text())
    billing["measured_usd"] = 2.01
    dump(path, billing)
    with pytest.raises(ValueError, match="first"):
        runner.run_batch(setup.config, setup.manifest, setup.rows, setup.output, setup.key_file, setup.smoke)


def test_first_trial_measured_billing_must_agree_with_usage_and_summary(setup):
    trial(setup)
    path = folder(setup) / "billing.json"
    billing = json.loads(path.read_text())
    billing["measured_usd"] = 0.01
    dump(path, billing)
    with pytest.raises(ValueError, match="first"):
        runner.run_batch(setup.config, setup.manifest, setup.rows, setup.output, setup.key_file, setup.smoke)


def test_first_trial_missing_stop_evidence_blocks_batch(setup):
    trial(setup)
    path = folder(setup) / "summary.json"
    summary = json.loads(path.read_text())
    summary.pop("auth_failed")
    dump(path, summary)
    with pytest.raises(ValueError, match="first"):
        runner.run_batch(setup.config, setup.manifest, setup.rows, setup.output, setup.key_file, setup.smoke)


def test_verify_patch_forwards_baseline_and_retains_actual_resolved_result(setup):
    result = runner.verify_patch(setup.rows[0], "", setup.tmp / "baseline", "baseline-run", IMAGE, setup.docker, baseline=True)
    assert result["outcome"] == "PASS" and result["baseline"] is True
    assert result["command"][-1] == "--baseline"
    assert result["cleanup"][0]["present"] is False


@pytest.mark.parametrize("field,value", [("instance_id", "other"), ("base_commit", "f" * 40),
    ("patch_sha256", "f" * 64), ("swebench_version", "5.0.1"), ("verifier_image_digest", "sha256:" + "f" * 64),
    ("command", ["wrong"]), ("exit_status", 1), ("report_path", "../old-report.json"),
    ("evaluated_at", "2020-01-01T00:00:00+00:00"), ("baseline", True), ("cleanup", [])])
def test_verify_patch_rejects_mismatched_or_stale_receipts(setup, monkeypatch, field, value):
    original = runner.run_bounded
    def corrupt(args, **kwargs):
        result = original(args, **kwargs)
        if len(args) > 1 and str(args[1]).endswith("/swebench_adapter/verifier.py"):
            out = Path(args[args.index("--output") + 1])
            path = out / "verifier-receipt.json"
            receipt = json.loads(path.read_text())
            receipt[field] = value
            dump(path, receipt)
        return result
    monkeypatch.setattr(runner, "run_bounded", corrupt)
    result = runner.verify_patch(setup.rows[0], PATCH, setup.tmp / "corrupt", "corrupt-run", IMAGE, setup.docker)
    assert result["outcome"] == "INCONCLUSIVE"
    assert result["cleanup"][0]["present"] is False


@pytest.mark.parametrize("error", [subprocess.TimeoutExpired("verifier", 2700), KeyboardInterrupt()])
def test_verify_patch_timeout_and_interrupt_inspect_and_remove_owned_container(setup, monkeypatch, error):
    name = f"sweb.eval.{setup.rows[0]['instance_id']}.interrupted-run"
    original = runner.run_bounded
    def interrupted(args, **kwargs):
        if len(args) > 1 and str(args[1]).endswith("/swebench_adapter/verifier.py"):
            setup.docker.resources.add(("container", name))
            raise error
        return original(args, **kwargs)
    monkeypatch.setattr(runner, "run_bounded", interrupted)
    result = runner.verify_patch(setup.rows[0], PATCH, setup.tmp / "interrupted", "interrupted-run", IMAGE, setup.docker)
    assert result["outcome"] == "INCONCLUSIVE"
    assert result["cleanup"][0] == {"kind": "container", "name": name, "present": False, "removed": True}
    assert result["cleanup"][1]["kind"] == "host_process"
    assert result["host_cleanup_complete"] is False
    assert ("container", name) not in setup.docker.resources


def test_complete_unresolved_patch_is_fail(setup, monkeypatch):
    original = runner.run_bounded
    def failed_tests(args, **kwargs):
        result = original(args, **kwargs)
        if len(args) > 1 and str(args[1]).endswith("/swebench_adapter/verifier.py"):
            out = Path(args[args.index("--output") + 1])
            receipt = json.loads((out / "verifier-receipt.json").read_text())
            receipt.update(outcome="FAIL", exit_status=1, reason="one required test failed")
            dump(out / "verifier-receipt.json", receipt)
            raw = json.loads((out / "verifier-report.json").read_text())
            row = raw[setup.rows[0]["instance_id"]]
            row["resolved"] = False
            row["tests_status"]["FAIL_TO_PASS"] = {"success": [], "failure": ["test_bug"]}
            dump(out / "verifier-report.json", raw)
            return SimpleNamespace(returncode=1, stdout=b"", stderr=b"", stop=None, seconds=0.01)
        return result
    monkeypatch.setattr(runner, "run_bounded", failed_tests)
    assert trial(setup)["status"] == "FAIL"


def test_plugin_mount_argument_is_posix_even_when_host_resolver_is_windows(setup, monkeypatch):
    resolve = Path.resolve
    def windows_resolve(path, *args, **kwargs):
        if str(path) == "/opt/fleet":
            return PureWindowsPath("C:/opt/fleet")
        return resolve(path, *args, **kwargs)
    monkeypatch.setattr(Path, "resolve", windows_resolve)
    command = runner.agent_command(setup.config, setup.rows[0])
    assert command[command.index("--plugin-dir") + 1] == "/opt/fleet"


@pytest.mark.parametrize("phase", ["setup", "agent", "verifier"])
def test_interruption_stops_batch_before_any_next_paid_task(setup, monkeypatch, phase):
    trial(setup)
    if phase == "setup":
        setup.docker.setup_interrupt = True
    elif phase == "agent":
        setup.docker.agent_interrupt = True
    else:
        def interrupted(*args, **kwargs):
            return SimpleNamespace(returncode=-9, stdout=b"", stderr=b"", stop="interrupted", seconds=0.01)
        monkeypatch.setattr(runner, "run_bounded", interrupted)
    results = runner.run_batch(setup.config, setup.manifest, setup.rows, setup.output, setup.key_file, setup.smoke)
    assert len(results) == 2
    assert results[-1]["interrupted"] is True
    assert results[-1]["cleanup_ok"] and results[-1]["billing_known"]
    assert len(FakeProxy.instances) == 2


def test_verifier_environment_uses_resolved_local_endpoint_with_private_home(setup, monkeypatch):
    setup.docker.endpoint = "unix:///home/operator/.docker/desktop/docker.sock"
    setup.docker.pinned = None
    original = runner.run_bounded
    def inspect_process(args, **kwargs):
        assert kwargs["env"]["DOCKER_HOST"] == setup.docker.endpoint
        assert "DOCKER_CONTEXT" not in kwargs["env"]
        assert KEY not in str(kwargs["env"])
        assert args[args.index("--engine-id") + 1] == setup.docker.engine_id
        return original(args, **kwargs)
    monkeypatch.setattr(runner, "run_bounded", inspect_process)
    result = runner.verify_patch(setup.rows[0], PATCH, setup.tmp / "desktop", "desktop-run", IMAGE, setup.docker)
    assert result["outcome"] == "PASS"
    assert result["docker_endpoint"] == setup.docker.endpoint
    assert result["docker_engine_id"] == setup.docker.engine_id


@pytest.mark.parametrize("field,value", [("observed_base_commit", "f" * 40),
    ("docker_engine_id", "another-engine"), ("docker_endpoint", "unix:///another.sock"),
    ("initial_state", {"head": "c" * 40, "tracked_clean": False, "index_clean": True})])
def test_parent_rejects_unproven_base_or_engine_receipt(setup, monkeypatch, field, value):
    original = runner.run_bounded
    def corrupt(args, **kwargs):
        result = original(args, **kwargs)
        path = Path(args[args.index("--output") + 1]) / "verifier-receipt.json"
        receipt = json.loads(path.read_text())
        receipt[field] = value
        dump(path, receipt)
        return result
    monkeypatch.setattr(runner, "run_bounded", corrupt)
    result = runner.verify_patch(setup.rows[0], PATCH, setup.tmp / "unproven", "unproven-run", IMAGE, setup.docker)
    assert result["outcome"] == "INCONCLUSIVE"


def test_oversized_verifier_artifacts_are_rejected_before_read(setup, monkeypatch):
    original = runner.run_bounded
    def oversized(args, **kwargs):
        result = original(args, **kwargs)
        path = Path(args[args.index("--output") + 1]) / "oversized.log"
        with path.open("wb") as stream:
            stream.truncate(64 * 1024 * 1024 + 1)
        return result
    monkeypatch.setattr(runner, "run_bounded", oversized)
    read = Path.read_bytes
    def reject_large_read(path):
        assert path.name != "oversized.log", "artifact read before size validation"
        return read(path)
    monkeypatch.setattr(Path, "read_bytes", reject_large_read)
    result = runner.verify_patch(setup.rows[0], PATCH, setup.tmp / "oversized", "oversized-run", IMAGE, setup.docker)
    assert result["outcome"] == "INCONCLUSIVE"
    assert not (setup.tmp / "oversized/oversized.log").exists()


def test_total_verifier_artifact_limit_is_checked_before_any_artifact_read(setup, monkeypatch):
    original = runner.run_bounded
    def oversized(args, **kwargs):
        result = original(args, **kwargs)
        root = Path(args[args.index("--output") + 1])
        for index in range(5):
            with (root / f"large-{index}.log").open("wb") as stream:
                stream.truncate(64 * 1024 * 1024)
        return result
    monkeypatch.setattr(runner, "run_bounded", oversized)
    result = runner.verify_patch(setup.rows[0], PATCH, setup.tmp / "total", "total-run", IMAGE, setup.docker)
    assert result["outcome"] == "INCONCLUSIVE"
    assert not list((setup.tmp / "total").glob("large-*.log"))


def test_unknown_after_usage_preserves_assessment_and_stops_batch(setup, monkeypatch):
    monkeypatch.setattr(FakeProxy, "usage_rows", [
        {"usage": 1, "limit": 30, "limit_remaining": 29}, ValueError("unavailable usage")])
    result = trial(setup)
    assert result["status"] == "PASS" and not result["billing_known"]
    assert "usage" in result["after_assessment"]
    with pytest.raises(ValueError, match="first"):
        runner.run_batch(setup.config, setup.manifest, setup.rows, setup.output, setup.key_file, setup.smoke)


@pytest.mark.parametrize("failure", ["authentication", "budget", "identity", "cleanup"])
def test_batch_stops_on_required_non_environment_controls(setup, monkeypatch, failure):
    trial(setup)
    if failure == "authentication":
        monkeypatch.setattr(FakeProxy, "fail_auth", True)
    elif failure == "budget":
        monkeypatch.setattr(FakeProxy, "usage_rows", [
            {"usage": 1, "limit": 30, "limit_remaining": 29},
            {"usage": 1.5, "limit": 30, "limit_remaining": 0}])
    elif failure == "identity":
        setup.docker.version = "wrong CLI"
    else:
        setup.docker.cleanup_error = True
    results = runner.run_batch(setup.config, setup.manifest, setup.rows, setup.output, setup.key_file, setup.smoke)
    assert len(results) == 2


@pytest.mark.parametrize("stop", ["cleanup_failure", "ownership_failure", "interrupted", None])
def test_unresolved_host_process_cleanup_blocks_batch_and_future_trials(setup, monkeypatch, stop):
    trial(setup)
    def unresolved(*args, **kwargs):
        return ProcessResult(b"", b"", -9, stop, 0.01, cleanup_complete=False, pid=12345)
    monkeypatch.setattr(runner, "run_bounded", unresolved)
    results = runner.run_batch(setup.config, setup.manifest, setup.rows, setup.output, setup.key_file, setup.smoke)
    assert len(results) == 2
    result = results[-1]
    assert result["status"] == "INCONCLUSIVE" and result["cleanup_ok"] is False
    assert result["interrupted"] is (stop == "interrupted")
    assert result["billing_known"] is True
    run = setup.output / f"eval-{setup.rows[1]['instance_id']}" / "claude/run-1"
    receipt = json.loads((run / "verifier/verifier-receipt.json").read_text())
    assert receipt["host_cleanup_complete"] is False and receipt["stop"] == stop
    host = next(item for item in receipt["cleanup"] if item["kind"] == "host_process")
    assert host["present"] is None and host["removed"] is False
    assert host["owner_pid"] > 0 and host["command"] == receipt["command"]
    assert host["pid"] == 12345
    assert (run / "verifier/host-process-cleanup.json").is_file()
    pending = json.loads((setup.output / "pending-cleanup.json").read_text())
    assert any(item["kind"] == "host_process" for item in pending)
    setup.docker.resources.clear()  # Docker absence cannot resolve host process uncertainty.
    before = len(FakeProxy.instances)
    with pytest.raises(ValueError, match="cleanup"):
        runner.run_trial(setup.config, setup.manifest, setup.rows, setup.rows[2]["instance_id"],
                         setup.output, setup.key_file, setup.smoke)
    assert len(FakeProxy.instances) == before
    assert not any(args[0] == "host_process" or host["name"] in args for args, _ in setup.docker.calls)


@pytest.mark.parametrize("expected", ["PASS", "FAIL"])
@pytest.mark.parametrize("late_problem", ["cleanup", "billing", "proxy_close"])
def test_supported_assessment_survives_late_instrument_failure(setup, monkeypatch, expected, late_problem):
    if expected == "FAIL":
        setup.docker.patch = b""
    if late_problem == "cleanup":
        setup.docker.cleanup_error = True
    elif late_problem == "billing":
        monkeypatch.setattr(FakeProxy, "usage_rows", [
            {"usage": 1, "limit": 30, "limit_remaining": 29}, ValueError("unavailable usage")])
    else:
        def failed_close(self):
            self.closed = True
            raise RuntimeError("closure could not be confirmed")
        monkeypatch.setattr(FakeProxy, "close", failed_close)
    result = trial(setup)
    record = RecordV1.model_validate_json((folder(setup) / "record.json").read_text())
    assert result["status"] == expected
    assert record.verdict.status == expected
    assert record.checks[0].state == expected
    assert record.verdict.after_assessment == result["after_assessment"]
    assert record.verdict.after_assessment
    assert result["environment_failure"]
    with pytest.raises(ValueError):
        runner.run_batch(setup.config, setup.manifest, setup.rows, setup.output, setup.key_file, setup.smoke)


@pytest.mark.parametrize("recovered", [False, True])
def test_supported_verifier_assessment_survives_late_container_cleanup(setup, monkeypatch, recovered):
    original = runner.run_bounded

    def late_cleanup(args, **kwargs):
        result = original(args, **kwargs)
        out = Path(args[args.index("--output") + 1])
        path = out / "verifier-receipt.json"
        receipt = json.loads(path.read_text())
        receipt["cleanup"][0].update(present=True, removed=False)
        receipt["after_assessment"] = "verifier container cleanup is unresolved"
        dump(path, receipt)
        if not recovered:
            setup.docker.cleanup_error = True
        return result

    monkeypatch.setattr(runner, "run_bounded", late_cleanup)
    result = trial(setup)
    assert result["status"] == "PASS"
    assert result["after_assessment"]
    assert result["environment_failure"] is True
    record = RecordV1.model_validate_json((folder(setup) / "record.json").read_text())
    assert record.verdict.status == "PASS" and record.verdict.after_assessment
    receipt = json.loads((folder(setup) / "verifier/verifier-receipt.json").read_text())
    assert receipt["verifier_cleanup"][0]["present"] is True
    if recovered:
        assert receipt["cleanup"][0]["present"] is False
    with pytest.raises(ValueError):
        runner.run_batch(setup.config, setup.manifest, setup.rows, setup.output, setup.key_file, setup.smoke)


@pytest.mark.parametrize("elevated", [True, None, 0, "false"])
def test_shared_host_binding_requires_unelevated_account_before_docker(monkeypatch, elevated):
    monkeypatch.setattr(configuration, "binding", lambda *args: {})
    monkeypatch.setattr(runner.fingerprints, "host_identity", lambda: {
        "hostname": "host", "account_id": "account", "elevated": elevated})
    docker = SimpleNamespace(call=lambda *args, **kwargs: pytest.fail("unsafe host reached Docker"))
    with pytest.raises(ValueError, match="unelevated"):
        runner.runtime_binding({}, {}, docker)
