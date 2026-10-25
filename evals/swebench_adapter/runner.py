"""Serial, identity-bound static-repair trials with host-owned credentials."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import platform
import re
import secrets
import shutil
import tempfile
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from probe import fingerprints, invocation, tracing
from probe.backing import SERVICE_RELAY_IMAGE
from probe.records import RecordV1

from . import artifacts, configuration, selection, verifier
from .containers import Docker, DockerResources
from .limits import run_bounded
from .proxy import ModelProxy, read_key

_NAME = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,250}")


def agent_environment(config: Mapping[str, Any], token: str) -> dict[str, str]:
    """An explicit container environment: no inherited host/account credentials."""
    return {
        "ANTHROPIC_AUTH_TOKEN": token,
        "ANTHROPIC_API_KEY": "",
        "ANTHROPIC_BASE_URL": "http://model-proxy:8080",
        "ANTHROPIC_DEFAULT_SONNET_MODEL": config["model"],
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": config["haiku_model"],
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "DISABLE_TELEMETRY": "1",
        "DISABLE_ERROR_REPORTING": "1",
        "CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY": "1",
        "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
        "HOME": "/tmp/wp08-home",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
    }


def agent_command(config: Mapping[str, Any], task: Mapping[str, Any]) -> list[str]:
    prompt = (
        "Repair the public open-source repository selected by its owner, at the pinned base commit. "
        "Use the static-repair profile: inspect source and write a scoped patch without executing "
        "the repository's code or tests. Independent verification runs separately. "
        "Leave the patch in the working tree; no commit. Do not change .claude settings.\n\n"
        "Public problem statement:\n" + task["problem_statement"]
    )
    command = invocation.build_command(
        "/opt/claude",
        Path("/opt/fleet"),
        "save-toolkit:software-engineer",
        prompt,
        config["model"],
        pre_approve=True,
        max_turns=64,
    )
    command[command.index("--plugin-dir") + 1] = "/opt/fleet"
    denied = command.index("--disallowedTools") + 1
    command[denied] = ",".join(dict.fromkeys([*command[denied].split(","), "WebFetch", "WebSearch"]))
    settings = command.index("--settings") + 1
    value = json.loads(command[settings])
    if config.get("api_key_helper"):
        value["apiKeyHelper"] = 'printf "%s" "$ANTHROPIC_AUTH_TOKEN"'
    command[settings] = json.dumps(value)
    return command


def image_identity(docker: Docker, config: Mapping[str, Any], instance_id: str) -> str:
    image = config["images"][instance_id]
    reference, expected = image["reference"], image["image_id"]
    if (
        not isinstance(reference, str)
        or re.fullmatch(r"[a-z0-9][a-z0-9./_:-]*@sha256:[0-9a-f]{64}", reference) is None
        or not isinstance(expected, str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", expected) is None
    ):
        raise ValueError("image reference and Id must be explicitly pinned")
    try:
        observed = json.loads(docker.call(["image", "inspect", reference]).stdout)
        if (
            not isinstance(observed, list)
            or len(observed) != 1
            or not isinstance(observed[0], dict)
            or observed[0].get("Id") != expected
            or not isinstance(observed[0].get("RepoDigests"), list)
            or reference not in observed[0]["RepoDigests"]
        ):
            raise ValueError
    except (RuntimeError, ValueError, TypeError, OSError):
        raise ValueError("local image does not match its pinned reference and Id") from None
    return str(expected)


def runtime_binding(config: Mapping[str, Any], manifest: Mapping[str, Any], docker: Docker) -> dict[str, Any]:
    """Bind smoke to this host, effective local Linux engine and pinned relay image."""
    bound = configuration.binding(config, manifest)
    host = fingerprints.host_identity()
    if (
        not host.get("hostname")
        or not host.get("account_id")
        or type(host.get("elevated")) is not bool
        or host.get("problem")
    ):
        raise ValueError("host runtime identity is unavailable")
    try:
        contexts = json.loads(docker.call(["context", "inspect"]).stdout)
        if not isinstance(contexts, list) or len(contexts) != 1:
            raise ValueError
        context = contexts[0]
        if not isinstance(context, dict) or not isinstance(context.get("Name"), str) or not context["Name"]:
            raise ValueError
        endpoint = context["Endpoints"]["docker"]["Host"]
        if (
            not isinstance(endpoint, str)
            or not configuration._local_docker_host(endpoint)
            or (os.environ.get("DOCKER_HOST") and os.environ["DOCKER_HOST"] != endpoint)
        ):
            raise ValueError
        docker.pin(endpoint)
        info = json.loads(docker.call(["info", "--format", "{{json .}}"]).stdout)
        fields = ("ID", "ServerVersion", "OSType", "OperatingSystem", "KernelVersion", "Driver")
        if (
            not isinstance(info, dict)
            or info.get("OSType") != "linux"
            or any(not isinstance(info.get(field), str) or not info[field] for field in fields)
        ):
            raise ValueError
        relay = json.loads(docker.call(["image", "inspect", SERVICE_RELAY_IMAGE]).stdout)
        if (
            not isinstance(relay, list)
            or len(relay) != 1
            or not isinstance(relay[0], dict)
            or re.fullmatch(r"sha256:[0-9a-f]{64}", str(relay[0].get("Id"))) is None
            or not isinstance(relay[0].get("RepoDigests"), list)
            or SERVICE_RELAY_IMAGE not in relay[0]["RepoDigests"]
        ):
            raise ValueError
    except (RuntimeError, OSError, ValueError, TypeError, KeyError):
        raise ValueError("Docker runtime must identify the same local Linux engine and pinned relay image") from None
    return {
        **bound,
        "host_runtime": {
            "identity": host,
            "platform": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
        },
        "docker_runtime": {
            **{field: info[field] for field in fields},
            "context": context["Name"],
            "endpoint": endpoint,
        },
        "relay_image": {"reference": SERVICE_RELAY_IMAGE, "image_id": relay[0]["Id"]},
    }


def _present(docker: Docker, kind: str, name: str) -> bool | None:
    try:
        result = docker.call([kind, "inspect", name], timeout=10, check=False)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return True if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict) else None
        error = result.stderr.decode("utf-8", "replace").strip().lower()
        suffixes = (f"no such object: {name}", f"no such {kind}: {name}", f"network {name} not found")
        if result.returncode == 1 and any(error == text or error.endswith(": " + text) for text in suffixes):
            return False
    except (RuntimeError, OSError, ValueError, TypeError):
        pass
    return None


def _clean_named(docker: Docker, name: str, owned: bool) -> dict[str, Any]:
    present = _present(docker, "container", name)
    if owned and present is not False:
        with contextlib.suppress(RuntimeError, OSError):
            docker.call(["rm", "--force", name], timeout=20, check=False)
        present = _present(docker, "container", name)
    return {"kind": "container", "name": name, "present": present, "removed": present is False}


def _process_environment(home: Path, endpoint: str) -> dict[str, str]:
    env = {name: os.environ[name] for name in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP") if name in os.environ}
    return {
        **env,
        "HOME": str(home),
        "USERPROFILE": str(home),
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "DOCKER_HOST": endpoint,
    }


def _verifier_engine(docker: Docker) -> tuple[str, str]:
    contexts = json.loads(docker.call(["context", "inspect"]).stdout)
    if not isinstance(contexts, list) or len(contexts) != 1:
        raise ValueError("Docker context is unavailable")
    endpoint = contexts[0]["Endpoints"]["docker"]["Host"]
    if not isinstance(endpoint, str) or not configuration._local_docker_host(endpoint):
        raise ValueError("verifier requires a local Docker endpoint")
    docker.pin(endpoint)
    info = json.loads(docker.call(["info", "--format", "{{json .}}"]).stdout)
    if (
        not isinstance(info, dict)
        or not isinstance(info.get("ID"), str)
        or not info["ID"]
        or info.get("OSType") != "linux"
    ):
        raise ValueError("verifier requires observed Linux engine identity")
    return endpoint, info["ID"]


def verify_patch(
    task: Mapping[str, Any],
    patch: str,
    output: Path,
    run_id: str,
    image_digest: str,
    docker: Docker,
    *,
    baseline: bool = False,
    storage_quota: bool = True,
) -> dict[str, Any]:
    """Run a fresh verifier process with private host-only inputs and no model environment."""
    if storage_quota is not True:
        raise ValueError("a hard storage quota is required")
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    if any(
        (output / name).exists()
        for name in ("verifier-receipt.json", "verifier-report.json", "host-process-cleanup.json")
    ):
        raise ValueError("verifier output already exists")
    verifier._validate_task(task, run_id, image_digest)
    artifacts.screen(patch.encode())
    endpoint, engine_id = _verifier_engine(docker)
    name = f"sweb.eval.{task['instance_id'].lower()}.{run_id}"
    receipt: dict[str, Any] = {
        "instance_id": task["instance_id"],
        "base_commit": task["base_commit"],
        "baseline": baseline,
        "storage_quota": storage_quota,
        "docker_engine_id": engine_id,
        "docker_endpoint": endpoint,
        "interrupted": False,
        "host_cleanup_complete": True,
        "stop": None,
        "patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
        "swebench_version": None,
        "verifier_image_digest": image_digest,
        "command": [],
        "exit_status": None,
        "report_path": "verifier-report.json",
        "evaluated_at": datetime.now(UTC).isoformat(),
        "outcome": "INCONCLUSIVE",
        "reason": "verifier process did not establish a result",
        "cleanup": [],
    }
    raw: Any = {}
    files: list[tuple[str, bytes]] = []
    host_cleanup_complete = True
    host_stop: str | None = None
    host_process: dict[str, Any] = {
        "kind": "host_process",
        "name": "verifier-host-" + run_id,
        "run_id": run_id,
        "pid": None,
        "owner_pid": os.getpid(),
        "command": [],
        "started_at": None,
        "present": None,
        "removed": False,
    }
    owned = _present(docker, "container", name) is False
    try:
        if not owned:
            raise ValueError("verifier resource absence is not established")
        with tempfile.TemporaryDirectory(prefix="wp08-verifier-") as private:
            root = Path(private)
            task_path = artifacts.store_json(root, "task.json", dict(task))
            patch_path = artifacts.store_bytes(root, "candidate.patch", patch.encode())
            result_dir = root / "result"
            command = verifier.verifier_command(
                task_path,
                patch_path,
                result_dir,
                run_id,
                image_digest,
                baseline=baseline,
                storage_quota=storage_quota,
                engine_id=engine_id,
                docker_host=endpoint,
            )
            receipt["command"] = command
            started = datetime.now(UTC).replace(microsecond=0)
            host_process.update(command=command, started_at=started.isoformat())
            # No return from the process boundary means ownership/absence is unknown.
            host_cleanup_complete = False
            process = run_bounded(
                command,
                cwd=root,
                env=_process_environment(root, endpoint),
                timeout=2700,
            )
            receipt["exit_status"] = process.returncode
            host_cleanup_complete = getattr(process, "cleanup_complete", True) is True
            host_process["pid"] = getattr(process, "pid", None)
            host_stop = process.stop
            receipt["interrupted"] = process.stop == "interrupted"
            if process.stop is not None or not host_cleanup_complete:
                raise ValueError("verifier process hit an execution bound")
            artifacts.screen(process.stdout)
            artifacts.screen(process.stderr)
            inventory = verifier.artifact_files(result_dir)
            observed = json.loads(verifier.read_artifact(result_dir / "verifier-receipt.json"))
            raw = json.loads(verifier.read_artifact(result_dir / "verifier-report.json"))
            if isinstance(observed, dict) and observed.get("interrupted") is True:
                receipt["interrupted"] = True
            expected = {
                key: receipt[key]
                for key in (
                    "instance_id",
                    "base_commit",
                    "patch_sha256",
                    "verifier_image_digest",
                    "docker_engine_id",
                    "docker_endpoint",
                    "storage_quota",
                )
            }
            if (
                not isinstance(observed, dict)
                or any(observed.get(key) != value for key, value in expected.items())
                or observed.get("command") != command
                or observed.get("swebench_version") != "5.0.2"
                or observed.get("report_path") != "verifier-report.json"
                or observed.get("baseline") is not baseline
                or observed.get("storage_quota") is not storage_quota
                or type(observed.get("interrupted")) is not bool
                or type(observed.get("exit_status")) is not int
                or observed["exit_status"] != process.returncode
                or observed.get("outcome") not in verifier.EXIT_STATUS
                or verifier.EXIT_STATUS[observed["outcome"]] != process.returncode
            ):
                raise ValueError("verifier identity or process status disagrees")
            if patch.strip() or baseline:
                state = observed.get("initial_state")
                if (
                    observed.get("observed_base_commit") != task["base_commit"]
                    or not isinstance(state, dict)
                    or state.get("head") != task["base_commit"]
                    or state.get("tracked_clean") is not True
                    or state.get("index_clean") is not True
                    or state.get("replace_objects_disabled") is not True
                    or state.get("untracked_policy") != "preserved"
                ):
                    raise ValueError("verifier did not attest the selected clean source baseline")
            when = datetime.fromisoformat(observed["evaluated_at"])
            offset = when.utcoffset()
            if offset is None or offset.total_seconds() != 0 or not started <= when <= datetime.now(UTC):
                raise ValueError("verifier timestamp is not fresh UTC evidence")
            cleanup = observed.get("cleanup")
            if (
                not isinstance(cleanup, list)
                or (observed["outcome"] == "PASS" and not cleanup)
                or any(
                    not isinstance(item, dict)
                    or item.get("name") != name
                    or item.get("present") is not False
                    or item.get("removed") is not True
                    for item in cleanup
                )
            ):
                raise ValueError("verifier cleanup is not established")
            if observed["outcome"] == "PASS" and verifier._classify(raw, task)[0] != "PASS":
                raise ValueError("verifier PASS lacks complete expected-test evidence")
            total_read = 0
            for relative, path in inventory:
                if path.name not in ("verifier-receipt.json", "verifier-report.json"):
                    data = verifier.read_artifact(path)
                    total_read += len(data)
                    if total_read > verifier.ARTIFACT_TOTAL:
                        raise ValueError("verifier artifacts grew beyond the total limit")
                    artifacts.screen(data)
                    files.append((relative, data))
            artifacts.screen(json.dumps(observed).encode())
            artifacts.screen(json.dumps(raw).encode())
            receipt = observed
            receipt["baseline"] = baseline
    except KeyboardInterrupt:
        receipt.update(interrupted=True, outcome="INCONCLUSIVE", reason="verifier process interrupted")
        raw, files = {}, []
    except Exception:
        receipt.update(outcome="INCONCLUSIVE", reason="verifier process, identity or evidence validation failed")
        raw, files = {}, []
    finally:
        if host_cleanup_complete:
            host_process.update(present=False, removed=True)
        receipt.update(host_cleanup_complete=host_cleanup_complete, stop=host_stop, host_process=host_process)
        cleanup = _clean_named(docker, name, owned)
        receipt["cleanup"] = [cleanup]
        if not host_cleanup_complete:
            receipt["cleanup"].append(host_process)
            receipt.update(outcome="INCONCLUSIVE", reason="verifier host process cleanup is unresolved")
            artifacts.store_json(output, "host-process-cleanup.json", host_process)
        if cleanup["present"] is not False:
            receipt.update(outcome="INCONCLUSIVE", reason="verifier cleanup is unresolved")
        for relative, data in files:
            artifacts.store_bytes(output, relative, data)
        artifacts.store_json(output, "verifier-report.json", raw)
        artifacts.store_json(output, "verifier-receipt.json", receipt)
    return receipt


def _reconcile_pending(output: Path, docker: Docker) -> None:
    path = output / "pending-cleanup.json"
    if not path.exists():
        return
    manual_process_recovery = False
    try:
        entries = json.loads(path.read_text())
        if not isinstance(entries, list) or not entries:
            raise ValueError
        for item in entries:
            if isinstance(item, dict) and item.get("kind") == "host_process":
                manual_process_recovery = True
                raise ValueError
            if (
                not isinstance(item, dict)
                or item.get("kind") not in ("container", "network")
                or not isinstance(item.get("name"), str)
                or _NAME.fullmatch(item["name"]) is None
                or _present(docker, item["kind"], item["name"]) is not False
            ):
                raise ValueError
    except (ValueError, OSError, TypeError):
        if manual_process_recovery:
            raise ValueError(
                "previous host process cleanup remains unresolved; recorded process requires manual recovery"
            ) from None
        raise ValueError("previous cleanup remains unresolved; inspect and remove its resources first") from None
    path.unlink()


def _pending(output: Path, entries: Sequence[Mapping[str, Any]], *, first: bool = False) -> None:
    if first:
        artifacts.store_json(output, "pending-cleanup.json", list(entries))
    else:
        staged = artifacts.store_json(output, "cleanup-update-" + uuid.uuid4().hex + ".json", list(entries))
        staged.replace(output / "pending-cleanup.json")


def _budget(usage: Mapping[str, Any]) -> bool:
    values = {name: tracing.known_usd(usage.get(name)) for name in ("usage", "limit", "limit_remaining")}
    limit, remaining = values["limit"], values["limit_remaining"]
    return (
        values["usage"] is not None
        and limit is not None
        and remaining is not None
        and 0 < limit <= 30
        and remaining > 0
    )


def _measured(before: Any, after: Any) -> float | None:
    if isinstance(before, dict) and isinstance(after, dict):
        old, new = tracing.known_usd(before.get("usage")), tracing.known_usd(after.get("usage"))
        if old is not None and new is not None and new >= old:
            return round(new - old, 9)
    return None


def _runtime(docker: Docker, container: str, version: str) -> dict[str, Any]:
    result = docker.call(["exec", container, "/bin/sh", "-c", "uname -s; uname -r; uname -m; id -u; hostname"])
    lines = result.stdout.decode("utf-8").strip().splitlines()
    if len(lines) != 5 or not lines[3].isdigit() or not all(lines):
        raise ValueError("container runtime identity is unavailable")
    return {
        "cli_version": version,
        "host_platform": dict(zip(("system", "release", "machine"), lines[:3], strict=True)),
        "host_identity": {
            "hostname": lines[4],
            "account_id": "uid:" + lines[3],
            "elevated": lines[3] == "0",
            "identity_source": "posix_effective_uid",
        },
    }


def run_trial(
    config: Mapping[str, Any],
    manifest: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    instance_id: str,
    output: Path,
    key_file: Path,
    smoke_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """One authorized trial; all paid prerequisites are checked before reading the host key."""
    task = selection.resolve_task(manifest, rows, instance_id)
    run = output / f"eval-{instance_id}" / "claude" / "run-1"
    if run.exists():
        raise ValueError("this task already has an attempt; refusing overwrite or repeat")
    problems = configuration.dependency_problems()
    if problems:
        raise ValueError("; ".join(problems))
    docker = Docker()
    bound = runtime_binding(config, manifest, docker)
    problem = configuration.smoke_problem(smoke_receipt, bound)
    if problem:
        raise ValueError(problem)
    _reconcile_pending(output, docker)
    image = image_identity(docker, config, instance_id)
    candidate = fingerprints.plugin_provenance(Path(config["plugin_root"]))
    identity = selection.case_identity(task, manifest["revision"], image)
    run.mkdir(mode=0o700, parents=True, exist_ok=False)
    started = datetime.now(UTC).isoformat(timespec="seconds")
    summary: dict[str, Any] = {
        "instance_id": instance_id,
        "status": "INCONCLUSIVE",
        "reason": "trial did not complete",
        "ending": "cut_short",
        "stop": "no_result",
        "binding": bound,
        "measured_usd": None,
        "billing_known": False,
        "auth_failed": False,
        "identity_mismatch": False,
        "environment_failure": True,
        "budget_exhausted": False,
        "interrupted": False,
        "cleanup_ok": False,
        "record_path": str(run / "record.json"),
    }
    runtime: dict[str, Any] = {"cli_version": None, "host_platform": {}, "host_identity": None}
    prefix = "wp08-" + uuid.uuid4().hex
    resources = DockerResources(docker, prefix)
    pending: list[dict[str, Any]] = [
        {"kind": kind, "name": f"{prefix}-{suffix}"}
        for kind, suffix in (("container", "agent"), ("container", "relay"), ("network", "network"))
    ]
    _pending(output, pending, first=True)
    proxy: ModelProxy | None = None
    key = ""
    before: Any = None
    after: Any = None
    estimate = None
    seconds = None
    cleanup: list[dict[str, Any]] = []
    evidence: dict[str, str] = {}
    try:
        with tempfile.TemporaryDirectory(prefix="wp08-agent-") as private:
            private_root = Path(private)
            plugin = fingerprints.stage_plugin(Path(config["plugin_root"]), private_root / "fleet")
            if fingerprints.plugin_digest(plugin) != bound["plugin_sha256"]:
                raise ValueError("staged plugin identity mismatch")
            for path in plugin.rglob("*"):
                if (
                    path.is_file()
                    and path.suffix.lower() in (".py", ".sh", ".ps1", ".js")
                    and b"\r" in path.read_bytes()
                ):
                    raise ValueError("mounted scripts contain CR bytes")
            cli = private_root / "claude"
            shutil.copy2(config["cli_path"], cli)
            cli.chmod(0o500)
            if hashlib.sha256(cli.read_bytes()).hexdigest() != bound["cli_sha256"]:
                raise ValueError("frozen CLI identity mismatch")
            key = read_key(key_file)
            token = secrets.token_urlsafe(32)
            proxy = ModelProxy(key, token, {config["model"], config["haiku_model"]}, bind_host=config["proxy_bind"])
            proxy.start()
            before = proxy.usage()
            if proxy.auth_failed:
                summary["auth_failed"] = True
                raise ValueError("model proxy authentication failed")
            if not _budget(before):
                summary["budget_exhausted"] = True
                raise ValueError("key budget is unknown, exhausted or exceeds the approved limit")
            network = resources.internal_network()
            proxy_ip = resources.start_relay(network, config["proxy_target"], proxy.port)
            container = resources.start_agent(
                network,
                image,
                cli,
                plugin,
                agent_environment(config, token),
                proxy_ip,
                storage_quota=config["storage_quota"],
            )
            resources.setup_repository(container, task["base_commit"])
            version = docker.call(["exec", container, "/opt/claude", "--version"]).stdout.decode("utf-8").strip()
            if version != config["cli_version"]:
                summary.update(identity_mismatch=True, ending="void", stop=None)
                raise ValueError("mounted CLI version mismatch")
            runtime = _runtime(docker, container, version)
            command = agent_command(config, task)
            artifacts.store_json(run, "command.json", command, secrets=(key,))
            evidence["command"] = "command.json"
            executed = resources.execute(container, command, wall_seconds=2700, storage_quota=config["storage_quota"])
            seconds = executed.seconds
            # Screen every captured agent stream before persisting any of them.
            artifacts.screen(executed.stdout, (key,))
            artifacts.screen(executed.stderr, (key,))
            artifacts.store_bytes(run, "stdout.jsonl", executed.stdout, secrets=(key,))
            artifacts.store_bytes(run, "stderr.txt", executed.stderr, secrets=(key,))
            evidence.update(trace="stdout.jsonl", stderr="stderr.txt")
            parsed = tracing.parse_trace(run / "stdout.jsonl")
            estimate = tracing.known_usd(parsed.total_cost_usd)
            summary["auth_failed"] = proxy.auth_failed
            if proxy.auth_failed:
                summary["reason"] = "model proxy reported authentication failure"
            elif executed.stop:
                summary.update(
                    interrupted=executed.stop == "interrupted",
                    reason=f"agent execution stopped: {executed.stop}",
                    stop="wall_clock" if executed.stop == "wall_clock" else "cut_short",
                )
            elif not parsed.saw_init or not executed.stdout.strip():
                summary["reason"] = "agent trace is missing runtime initialization"
            else:
                tools = invocation.expected_runtime_tools(plugin, "software-engineer")
                problem = artifacts.runtime_problem(run / "stdout.jsonl", plugin, "/opt/fleet", config["model"], tools)
                drift = (
                    fingerprints.plugin_digest(plugin) != bound["plugin_sha256"]
                    or hashlib.sha256(cli.read_bytes()).hexdigest() != bound["cli_sha256"]
                )
                if problem or drift or parsed.foreign_skills:
                    summary.update(identity_mismatch=True, ending="void", stop=None, reason="runtime identity mismatch")
                elif parsed.denials or any(
                    tracing.is_guard_denial(text) or tracing.GUARD_UNAVAILABLE_MARKER in text.lower()
                    for text in parsed.tool_errors
                ):
                    summary["reason"] = "runtime or guard denied a required tool"
                elif not parsed.tool_counts_complete:
                    summary["reason"] = "agent trace is incomplete or malformed"
                elif executed.returncode and parsed.result_subtype != "error_max_turns":
                    summary["reason"] = "agent process failed before a usable completion"
                elif parsed.result_is_error and parsed.result_subtype != "error_max_turns":
                    summary["reason"] = "agent returned an execution error"
                else:
                    summary.update(
                        ending="turn_limit" if parsed.result_subtype == "error_max_turns" else "completed",
                        stop=None,
                        environment_failure=False,
                    )
                    staged = resources.execute(
                        container,
                        ["git", "-c", "core.hooksPath=/dev/null", "add", "-A"],
                        wall_seconds=60,
                        storage_quota=config["storage_quota"],
                    )
                    artifacts.screen(staged.stdout, (key,))
                    artifacts.screen(staged.stderr, (key,))
                    if staged.stop or staged.returncode:
                        summary["interrupted"] = staged.stop == "interrupted"
                        raise ValueError("patch staging failed or hit a bound")
                    captured = resources.execute(
                        container,
                        [
                            "git",
                            "-c",
                            "core.hooksPath=/dev/null",
                            "diff",
                            "--cached",
                            task["base_commit"],
                            "--",
                            ".",
                            ":(exclude).claude",
                            ":(exclude).claude/**",
                        ],
                        wall_seconds=60,
                        storage_quota=config["storage_quota"],
                    )
                    if captured.stop or captured.returncode:
                        summary["interrupted"] = captured.stop == "interrupted"
                        raise ValueError("patch capture failed or hit a bound")
                    artifacts.screen(captured.stdout, (key,))
                    artifacts.screen(captured.stderr, (key,))
                    patch = captured.stdout.decode("utf-8")
                    artifacts.store_bytes(run, "candidate.patch", captured.stdout, secrets=(key,))
                    evidence["patch"] = "candidate.patch"
                    if not patch.strip():
                        summary.update(status="FAIL", reason="candidate patch is empty")
                    else:
                        verifier_id = "wp08-" + uuid.uuid4().hex
                        verifier_name = f"sweb.eval.{instance_id.lower()}.{verifier_id}"
                        pending.append({"kind": "container", "name": verifier_name})
                        _pending(output, pending)
                        verified = verify_patch(
                            task,
                            patch,
                            run / "verifier",
                            verifier_id,
                            image,
                            docker,
                            storage_quota=config["storage_quota"],
                        )
                        cleanup.extend(verified["cleanup"])
                        summary.update(
                            status=verified["outcome"],
                            reason=verified.get("reason"),
                            environment_failure=verified["outcome"] == "INCONCLUSIVE",
                            interrupted=verified["interrupted"],
                        )
                        evidence.update(
                            verifier="verifier/verifier-receipt.json", verifier_report="verifier/verifier-report.json"
                        )
    except KeyboardInterrupt:
        summary.update(
            interrupted=True,
            status="INCONCLUSIVE",
            reason="trial interrupted",
            ending="cut_short",
            stop="cut_short",
            environment_failure=True,
        )
    except Exception:
        summary.update(
            status="INCONCLUSIVE",
            reason="trial setup, execution or artifact screening failed",
            environment_failure=not summary["identity_mismatch"],
        )
        if not summary["identity_mismatch"]:
            summary.update(ending="cut_short", stop="cut_short")
    finally:
        if proxy is not None:
            summary["auth_failed"] = proxy.auth_failed
            if before is not None:
                with contextlib.suppress(Exception):
                    after = proxy.usage()
            try:
                proxy.close()
            except Exception:
                summary.update(status="INCONCLUSIVE", reason="model proxy cleanup failed")
                cleanup.append({"kind": "proxy", "name": prefix, "present": None, "removed": False})
        cleanup.extend(resources.cleanup())
        # Inspect even resources whose creation was attempted but failed before tracking returned.
        for item in pending:
            present = _present(docker, item["kind"], item["name"])
            if not any(existing["name"] == item["name"] for existing in cleanup):
                cleanup.append({**item, "present": present, "removed": present is False})
            elif present is not False:
                for existing in cleanup:
                    if existing["name"] == item["name"]:
                        existing.update(present=present, removed=False)
        summary["cleanup_ok"] = bool(cleanup) and all(item.get("present") is False for item in cleanup)
        if summary["cleanup_ok"]:
            (output / "pending-cleanup.json").unlink(missing_ok=True)
        else:
            _pending(output, [item for item in cleanup if item.get("present") is not False])
            summary.update(status="INCONCLUSIVE", reason="attempt cleanup is unresolved", environment_failure=True)
        measured = _measured(before, after)
        if isinstance(after, dict) and not _budget(after):
            summary["budget_exhausted"] = True
        summary.update(measured_usd=measured, billing_known=measured is not None)
        if measured is None:
            summary.update(status="INCONCLUSIVE", reason="measured key usage is unavailable", environment_failure=True)
        if summary["auth_failed"]:
            summary.update(status="INCONCLUSIVE", reason="model proxy reported authentication failure")
        artifacts.store_json(
            run,
            "billing.json",
            {"before": before, "after": after, "measured_usd": measured, "complete": measured is not None},
            secrets=(key,),
        )
        artifacts.store_json(run, "cleanup.json", cleanup, secrets=(key,))
        artifacts.store_json(run, "identity.json", identity, secrets=(key,))
        artifacts.store_json(run, "binding.json", bound, secrets=(key,))
        artifacts.store_json(run, "timing.json", {"seconds": seconds}, secrets=(key,))
        artifacts.store_json(
            run,
            "policy-review.json",
            {
                "status": "unreviewed",
                "ac25": "Human trace review is required to assess refusal or execution of repository code; no automatic policy grade.",
            },
            secrets=(key,),
        )
        evidence.update(
            billing="billing.json",
            cleanup="cleanup.json",
            identity="identity.json",
            binding="binding.json",
            timing="timing.json",
            policy_review="policy-review.json",
        )
        provenance = fingerprints.runner_provenance()
        record = artifacts.make_record(
            identity=identity,
            candidate=candidate,
            runner={
                "runner_commit": provenance["runner_commit"],
                "runner_source_dirty": None,
                "runner_source_sha256": bound["adapter_sha256"],
            },
            model=config["model"],
            runtime=runtime,
            label="claude",
            started=started,
            ended=datetime.now(UTC).isoformat(timespec="seconds"),
            state=summary["status"],
            reason=summary["reason"],
            ending=summary["ending"],
            stop=summary["stop"],
            estimated_cost=estimate,
            evidence=evidence,
        )
        artifacts.store_json(run, "record.json", record, secrets=(key,))
        artifacts.store_json(run, "summary.json", summary, secrets=(key,))
    return summary


def run_batch(
    config: Mapping[str, Any],
    manifest: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    output: Path,
    key_file: Path,
    smoke_receipt: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """The first paid trial is its one task trial; continue only after its USD 2 check."""
    bound = runtime_binding(config, manifest, Docker())
    problem = configuration.smoke_problem(smoke_receipt, bound)
    if problem:
        raise ValueError(problem)
    tasks = manifest["tasks"]
    first_task = selection.resolve_task(manifest, rows, tasks[0]["instance_id"])
    first = output / f"eval-{tasks[0]['instance_id']}" / "claude" / "run-1"
    try:
        record = RecordV1.model_validate_json((first / "record.json").read_text())
        summary = json.loads((first / "summary.json").read_text())
        billing = json.loads((first / "billing.json").read_text())
        measured = tracing.known_usd(billing.get("measured_usd"))
        expected_identity = selection.case_identity(
            first_task, manifest["revision"], config["images"][first_task["instance_id"]]["image_id"]
        )
        if (
            record.case.id != tasks[0]["instance_id"]
            or summary.get("binding") != bound
            or summary.get("status") != record.verdict.status
            or any(
                type(summary.get(field)) is not bool
                for field in (
                    "auth_failed",
                    "identity_mismatch",
                    "environment_failure",
                    "budget_exhausted",
                    "cleanup_ok",
                    "billing_known",
                    "interrupted",
                )
            )
            or billing.get("complete") is not True
            or measured is None
            or measured > 2
            or measured != _measured(billing.get("before"), billing.get("after"))
            or summary.get("measured_usd") != measured
            or summary.get("billing_known") is not True
            or record.case.case_sha256 != selection.identity_digest(expected_identity)
            or record.candidate.plugin_source_sha256 != bound["plugin_sha256"]
            or record.runner.runner_source_sha256 != bound["adapter_sha256"]
            or record.conditions.requested_model != config["model"]
            or record.conditions.execution_profile is None
            or record.conditions.execution_profile.model_dump() != artifacts.PROFILE
            or not summary.get("cleanup_ok")
            or summary.get("auth_failed")
            or summary.get("identity_mismatch")
            or summary.get("budget_exhausted")
            or summary.get("interrupted")
        ):
            raise ValueError
    except (ValueError, OSError, TypeError, KeyError):
        raise ValueError("first trial record and matching measured billing at or below USD 2 are required") from None
    result = [summary]
    environments = int(bool(summary.get("environment_failure")))
    for task in tasks[1:]:
        current = run_trial(config, manifest, rows, task["instance_id"], output, key_file, smoke_receipt)
        result.append(current)
        environments = environments + 1 if current["environment_failure"] else 0
        if (
            current["auth_failed"]
            or current["interrupted"]
            or current["identity_mismatch"]
            or current["budget_exhausted"]
            or not current["cleanup_ok"]
            or not current["billing_known"]
            or environments >= 3
        ):
            break
    return result
