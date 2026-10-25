"""Operator-invoked model-free smoke using the same bounded Harbor verifier path."""

from __future__ import annotations

import asyncio
import json
import secrets
import tempfile
import uuid
from pathlib import Path
from typing import Any

from probe import fingerprints
from swebench_adapter.configuration import load_config
from swebench_adapter.containers import Docker, DockerResources
from swebench_adapter.proxy import ModelProxy
from swebench_adapter.runner import _runtime, agent_environment, image_identity
from swebench_adapter.smoke import (
    _STORAGE_PROBE,
    _clean,
    _egress_probe,
    _port_present,
    _SmokeUpstream,
    cpu_probe,
)
from swebench_adapter.smoke import (
    assess_smoke as assess_shared_smoke,
)

from .contracts import reward_assessment, verify_source
from .runner import _verifier_container, binding
from .transfer import collect_tree


def assess_smoke(observed: dict[str, Any], cleanup: list[dict[str, Any]]) -> dict[str, bool]:
    shared = assess_shared_smoke(observed, cleanup)
    reference, empty = observed.get("reference", {}), observed.get("empty", {})
    memory = observed.get("container", {}).get("HostConfig", {}).get("Memory")
    return {
        "cpu_cap": shared["cpu_cap"],
        "memory_cap": type(memory) is int and 0 < memory <= 2 * 1024**3,
        "storage_cap": shared["storage_cap"],
        "egress": shared["egress"],
        "hidden_separation": observed.get("hidden_separation") is True and observed.get("source_inputs") is True,
        "native_plugin": observed.get("native_plugin") is True,
        "native_cli": observed.get("native_cli") is True,
        "artifact_handoff": observed.get("artifact_handoff") is True,
        "verifier_dependencies": (
            reference.get("native_result") is not None and reference.get("execution_error") is None
        ),
        "reference_pass": reference.get("assessment", {}).get("verdict") == "PASS"
        and observed.get("reference_returncode") == 0,
        "empty_fail": empty.get("assessment", {}).get("verdict") == "FAIL",
        "missing_reward_inconclusive": observed.get("missing_reward", {}).get("verdict") == "INCONCLUSIVE",
        "cleanup": _clean(cleanup),
    }


def run_smoke(
    *,
    config_path: Path,
    manifest: dict[str, Any],
    case: dict[str, Any],
    source: Path,
    output: Path,
    docker: Docker | None = None,
) -> dict[str, Any]:
    """Create disposable containers and exercise quotas; no model/provider credentials used."""
    from harbor.models.task.task import Task  # noqa: PLC0415
    from harbor.models.trial.paths import TrialPaths  # noqa: PLC0415

    from .sdk import FleetEnvironment, require_sdk, verify_task  # noqa: PLC0415

    require_sdk()
    task = Task(verify_source(source, case))
    config = load_config(config_path)
    docker = docker or Docker()
    bound = binding(config, manifest, docker)
    author_image = image_identity(docker, config, case["source_path"] + "-author")
    verifier_image = image_identity(docker, config, case["source_path"] + "-verifier")
    output.mkdir(parents=True, exist_ok=False)
    observed: dict[str, Any] = {}
    cleanup: list[dict[str, Any]] = []
    resources = DockerResources(docker, "wp09-smoke-" + uuid.uuid4().hex[:24])
    error = None
    upstream = proxy = None
    try:
        for control in ("reference", "empty"):
            control_resources = DockerResources(docker, "wp09-control-" + uuid.uuid4().hex[:24])
            try:
                container = _verifier_container(control_resources, verifier_image)
                paths = TrialPaths(output / control)
                paths.trial_dir.mkdir()
                environment = FleetEnvironment(
                    resources=control_resources,
                    container=container,
                    role="verifier",
                    task=task,
                    trial_paths=paths,
                    wall_seconds=case["verifier_timeout_sec"],
                )
                if control == "reference":
                    docker.call(["cp", str(task.paths.solution_dir), container + ":/solution"])
                    solved = asyncio.run(environment.exec("/bin/bash /solution/solve.sh"))
                    (paths.trial_dir / "reference.stdout.txt").write_text(solved.stdout or "")
                    (paths.trial_dir / "reference.stderr.txt").write_text(solved.stderr or "")
                    observed["reference_returncode"] = solved.return_code
                observed[control] = asyncio.run(verify_task(task, environment, paths, submission_script=False))
            finally:
                control_cleanup = control_resources.cleanup()
                cleanup.extend(control_cleanup)
            if not _clean(control_cleanup):
                raise RuntimeError("control cleanup incomplete; no next environment admitted")
        observed["missing_reward"] = reward_assessment(output / "unavailable")
        upstream = _SmokeUpstream()
        token = secrets.token_hex(32)
        proxy = ModelProxy(
            "wp09-local-model-free-host-credential",
            token,
            [config["model"], config["haiku_model"]],
            bind_host=config["proxy_bind"],
            upstream_origin=f"http://127.0.0.1:{upstream.port}",
        )
        proxy.start()
        with tempfile.TemporaryDirectory(prefix="wp09-smoke-plugin-") as temporary:
            plugin = fingerprints.stage_plugin(Path(config["plugin_root"]), Path(temporary) / "fleet")
            if fingerprints.plugin_digest(plugin) != bound["plugin_sha256"]:
                raise ValueError("plugin changed while staging smoke")
            network = resources.internal_network()
            relay = resources.start_relay(network, config["proxy_target"], proxy.port)
            container = resources.start_agent(
                network,
                author_image,
                Path(config["cli_path"]),
                plugin,
                agent_environment(config, token),
                relay,
                storage_quota=True,
            )
            observed["native_cli"] = (
                docker.call(["exec", container, "/opt/claude", "--version"]).stdout.decode().strip()
                == config["cli_version"]
            )
            observed["container_runtime"] = _runtime(docker, container, config["cli_version"])
            validation = docker.call(
                ["exec", container, "/opt/claude", "plugin", "validate", "/opt/fleet"], check=False
            )
            observed["native_plugin"] = validation.returncode == 0
            absent = "test ! -e /tests && test ! -e /solution"
            if case["source_path"] == "write-compressor":
                absent += " && test ! -e /app/main.rs"
            observed["hidden_separation"] = (
                docker.call(["exec", container, "/bin/sh", "-c", absent], check=False).returncode == 0
            )
            expected_inputs = {}
            for relative in case["candidate_source_files"]:
                if relative == "instruction.md":
                    continue
                target = "/app/" + relative.removeprefix("environment/")
                if target.endswith("main.db-wal.encrypted"):
                    target = target.removesuffix(".encrypted")
                expected_inputs[target] = case["files"][relative]
            check_inputs = (
                "import hashlib,json,pathlib; expected=json.loads(" + repr(json.dumps(expected_inputs)) + "); "
                "print(json.dumps(all(pathlib.Path(p).is_file() and not pathlib.Path(p).is_symlink() "
                "and hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==digest for p,digest in expected.items())))"
            )
            observed["source_inputs"] = (
                json.loads(docker.call(["exec", container, "python3", "-c", check_inputs]).stdout) is True
            )

            observed["container"] = json.loads(docker.call(["inspect", container]).stdout)[0]
            observed["network"] = json.loads(docker.call(["network", "inspect", network]).stdout)[0]
            for name, script in (
                ("cpu", cpu_probe()),
                ("egress", _egress_probe(config["model"], token, config["proxy_bind"], proxy.port)),
            ):
                observed[name] = json.loads(
                    docker.call(["exec", container, "python3", "-c", script], timeout=45).stdout
                )
            fill = resources.execute(
                container,
                ["python3", "-c", _STORAGE_PROBE.replace("/testbed/", "/app/")],
                wall_seconds=150,
                storage_quota=True,
            )
            try:
                filled = json.loads(fill.stdout)
            except ValueError:
                filled = {}
            observed["storage"] = {
                "quota_rejected": fill.returncode == 0
                and fill.stop is None
                and filled.get("quota") is True
                and type(filled.get("written")) is int
                and 9 * 1024**3 <= filled["written"] <= 10 * 1024**3
                and observed["container"].get("HostConfig", {}).get("StorageOpt", {}).get("size") == "10G",
                "stop": fill.stop,
                "written": filled.get("written"),
            }
            docker.call(
                [
                    "exec",
                    container,
                    "/bin/sh",
                    "-c",
                    "rm -f /app/.wp08-storage-probe && printf wp09-owned-handoff > /app/.wp09-handoff",
                ]
            )
            docker.call(["stop", "--time", "0", container])
            snapshot = Path(temporary) / "handoff"
            collect_tree(docker, container, "/app", snapshot)
            restored = _verifier_container(resources, verifier_image)
            docker.call(["cp", str(snapshot) + "/.", restored + ":/app"])
            readback = docker.call(["exec", restored, "cat", "/app/.wp09-handoff"]).stdout
            observed["artifact_handoff"] = (
                snapshot / ".wp09-handoff"
            ).read_text() == "wp09-owned-handoff" and readback == b"wp09-owned-handoff"
    except (Exception, KeyboardInterrupt) as exc:
        error = type(exc).__name__
    finally:
        cleanup.extend(resources.cleanup())
        for listener, host, name in (
            (proxy, config["proxy_bind"], "model-free-proxy"),
            (upstream, "127.0.0.1", "model-free-upstream"),
        ):
            if listener is not None:
                try:
                    port = listener.port
                    listener.close()
                    present: bool | None = _port_present(host, port)
                except Exception:
                    present = None
                    error = error or "listener cleanup failed"
                cleanup.append({"kind": "listener", "name": name, "present": present, "removed": present is False})
        receipt = {
            "format": "wp09-terminal-smoke",
            "schema_version": 1,
            "binding": bound,
            "case_id": case["local_case_id"],
            "checks": assess_smoke(observed, cleanup),
            "cleanup": cleanup,
            "error": error,
            "model_calls": 0,
        }
        (output / "observations.json").write_text(json.dumps(observed, indent=2) + "\n")
        (output / "smoke.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt
