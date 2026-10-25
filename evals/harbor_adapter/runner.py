"""Explicit host admission and serial Terminal-Bench lifecycle; no default live run."""

from __future__ import annotations

import asyncio
import json
import re
import secrets
import shutil
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from probe import fingerprints, invocation, tracing
from probe.records import RecordV1
from swebench_adapter import artifacts, configuration
from swebench_adapter.containers import Docker, DockerResources
from swebench_adapter.proxy import ModelProxy, read_key
from swebench_adapter.runner import _budget, _measured, _runtime, agent_environment, image_identity, runtime_binding

from .contracts import HARBOR_VERSION, SOURCE_COMMIT, canonical_digest, read_json, sha256, verify_source
from .transfer import collect_tree

CHECKS = (
    "cpu_cap",
    "memory_cap",
    "storage_cap",
    "egress",
    "hidden_separation",
    "native_plugin",
    "native_cli",
    "artifact_handoff",
    "verifier_dependencies",
    "reference_pass",
    "empty_fail",
    "missing_reward_inconclusive",
    "cleanup",
)


def binding(config: dict[str, Any], manifest: dict[str, Any], docker: Docker) -> dict[str, Any]:
    result = runtime_binding(config, manifest, docker)
    if result["host_runtime"]["identity"]["elevated"] is not False:
        raise ValueError("live evaluation requires an observed unelevated account")
    sources = {p.name: sha256(p) for p in Path(__file__).parent.glob("*.py")}
    root = Path(__file__).resolve().parents[2]
    sources["harbor_pilot.py"] = sha256(root / "evals/harbor_pilot.py")
    sources["requirements-harbor.txt"] = sha256(root / "requirements-harbor.txt")
    result["harbor_adapter_sha256"] = canonical_digest(sources)
    result["shared_adapter_sha256"] = result["adapter_sha256"]
    result["adapter_sha256"] = canonical_digest(
        {"harbor": result["harbor_adapter_sha256"], "shared": result["shared_adapter_sha256"]}
    )
    result["images"] = dict(result["images"])
    for case in manifest["cases"]:
        result["images"][case["local_case_id"]] = config["images"][case["source_path"] + "-author"]
    result["harbor_version"] = HARBOR_VERSION
    return result


def admit(admission: dict[str, Any], bound: dict[str, Any], case: dict[str, Any], *, base: Path = Path(".")) -> None:
    if (
        admission.get("format") != "wp09-terminal-admission"
        or admission.get("schema_version") != 1
        or admission.get("binding") != bound
        or admission.get("accepted") is not True
        or not isinstance(admission.get("human_owner"), str)
        or not admission["human_owner"].strip()
    ):
        raise ValueError("human exact-candidate admission is absent or does not match current inputs")
    reference = admission.get("case_smoke", {}).get(case["local_case_id"], {})
    relative = reference.get("evidence_path")
    if not isinstance(relative, str) or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("case smoke must reference retained relative operator evidence")
    path = base / relative
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError("case smoke evidence must not cross a symlink")
    try:
        if sha256(path) != reference.get("sha256"):
            raise ValueError("case smoke evidence digest changed")
        smoke = read_json(path)
    except OSError:
        raise ValueError("case smoke evidence is unavailable") from None
    if (
        smoke.get("format") != "wp09-terminal-smoke"
        or smoke.get("schema_version") != 1
        or smoke.get("binding") != bound
        or smoke.get("case_id") != case["local_case_id"]
        or smoke.get("error") is not None
        or smoke.get("model_calls") != 0
        or any(smoke.get("checks", {}).get(check) is not True for check in CHECKS)
        or not isinstance(smoke.get("cleanup"), list)
        or not smoke["cleanup"]
        or any(item.get("present") is not False for item in smoke["cleanup"])
    ):
        raise ValueError("all per-case isolation and upstream control smoke checks must pass")


def make_record(
    *,
    case: dict[str, Any],
    candidate: dict[str, Any],
    runner: dict[str, Any],
    runtime: dict[str, Any],
    model: str,
    label: str,
    started: str,
    ended: str,
    execution: dict[str, Any] | None,
    verification: dict[str, Any] | None,
    problem: str | None,
    cleanup_ok: bool,
    identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = verification["assessment"]["verdict"] if verification else "INCONCLUSIVE"
    reason = verification["assessment"]["reason"] if verification else (problem or "verification unavailable")
    raw = artifacts.make_record(
        identity=identity
        or {
            "instance_id": case["local_case_id"],
            "source_commit": SOURCE_COMMIT,
            "task_id": case["task_id"],
            "content_sha256": case["content_sha256"],
        },
        candidate=candidate,
        runner=runner,
        model=model,
        runtime=runtime,
        label=label,
        started=started,
        ended=ended,
        state=state,
        reason=reason,
        ending=("turn_limit" if execution and execution.get("result_subtype") == "error_max_turns" else "completed")
        if verification is not None
        else "cut_short",
        stop=None
        if verification is not None
        else ("error_result" if execution and execution.get("result_is_error") else "cut_short"),
        estimated_cost=execution.get("cost_usd_estimate") if execution else None,
        evidence={
            "verification": "verification.json",
            "cleanup": "cleanup.json",
            "identity": "identity.json",
            "binding": "binding.json",
            "execution_receipt": "execution-receipt.json",
            **({"trace": "agent/stdout.jsonl", "invocation": "agent/argv.json"} if execution else {}),
        },
        after_assessment=problem if verification else None,
    )
    raw["conditions"]["execution_profile"]["name"] = "terminal-static-authoring-independent-verification-dec13-v1"
    raw["conditions"]["wall_clock_seconds"] = int(case["agent_timeout_sec"])
    raw["conditions"]["observed_models"] = execution.get("observed_models") if execution else None
    raw["checks"][0].update(
        id="independent-terminal-verification", text="Pinned Harbor Terminal-Bench verifier", evidence=reason
    )
    if not cleanup_ok:
        raw["verdict"]["after_assessment"] = "; ".join(
            filter(None, [raw["verdict"]["after_assessment"], "cleanup incomplete; reuse blocked"])
        )
    return RecordV1.model_validate_json(json.dumps(raw)).model_dump(mode="json")


def _verifier_container(resources: DockerResources, image: str) -> str:
    name = resources._own("verifier")
    resources.docker.call(
        [
            "run",
            "-d",
            "--name",
            name,
            "--network",
            "none",
            *resources._hardening(256, "2g"),
            "--storage-opt",
            "size=10G",
            "--env",
            "UV_OFFLINE=1",
            "--env",
            "PIP_NO_INDEX=1",
            "--workdir",
            "/app",
            "--entrypoint",
            "/bin/sleep",
            image,
            "infinity",
        ]
    )
    resources.docker.call(["exec", name, "/bin/sh", "-c", "mkdir -p /tests /logs/verifier"])
    return name


def run_trial(
    *,
    config_path: Path,
    manifest: dict[str, Any],
    case: dict[str, Any],
    source: Path,
    admission_path: Path,
    key_file: Path,
    output: Path,
    label: str,
    docker: Docker | None = None,
) -> dict[str, Any]:
    """One explicit paid attempt. No retries, builds, image pulls or credential provisioning."""
    from harbor.models.agent.context import AgentContext  # noqa: PLC0415
    from harbor.models.task.task import Task  # noqa: PLC0415
    from harbor.models.trial.paths import TrialPaths  # noqa: PLC0415

    from .sdk import FleetAgent, FleetEnvironment, require_sdk, verify_task  # noqa: PLC0415

    require_sdk()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", label):
        raise ValueError("label must be a safe arm name")
    source_task = verify_source(source, case)
    config = configuration.load_config(config_path)
    docker = docker or Docker()
    bound = binding(config, manifest, docker)
    admit(read_json(admission_path), bound, case, base=admission_path.resolve().parent)
    author_image = image_identity(docker, config, case["source_path"] + "-author")
    verifier_image = image_identity(docker, config, case["source_path"] + "-verifier")
    pending = output / "harbor-pending.json"
    if pending.exists():
        raise ValueError("prior lifecycle requires cleanup reconciliation before reuse")
    run = output / ("eval-" + case["local_case_id"]) / label / "run-1"
    run.mkdir(parents=True, exist_ok=False)
    started = datetime.now(UTC).isoformat(timespec="seconds")
    candidate = fingerprints.plugin_provenance(Path(config["plugin_root"]))
    runner = fingerprints.runner_provenance()
    runner["runner_source_sha256"] = bound["adapter_sha256"]
    runner["runner_source_dirty"] = None  # adapter-specific Git dirtiness is not yet observed
    runtime: dict[str, Any] = {"cli_version": None, "host_platform": {}, "host_identity": None}
    resources = DockerResources(docker, "wp09-" + uuid.uuid4().hex)
    pending.write_text(json.dumps({"prefix": resources.prefix, "binding": bound}) + "\n")
    execution = verification = None
    problem = None
    cleanup: list[dict[str, Any]] = []
    proxy = None
    before = after = None
    identity = {
        "instance_id": case["local_case_id"],
        "task_id": case["task_id"],
        "dataset": manifest.get("dataset"),
        "revision": SOURCE_COMMIT,
        "content_sha256": case["content_sha256"],
        "image_digest": author_image,
        "verifier_image_digest": verifier_image,
    }
    execution_receipt = {
        "binding": bound,
        "case": case,
        "execution_actor": "independent-verifier",
        "policy_review": "unmeasured",
    }
    (run / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    (run / "binding.json").write_text(json.dumps(bound, indent=2) + "\n")
    try:
        with tempfile.TemporaryDirectory(prefix="wp09-terminal-") as temporary:
            private = Path(temporary)
            plugin = fingerprints.stage_plugin(Path(config["plugin_root"]), private / "fleet")
            cli = private / "claude"
            shutil.copy2(config["cli_path"], cli)
            cli.chmod(0o500)
            if fingerprints.plugin_digest(plugin) != bound["plugin_sha256"] or sha256(cli) != bound["cli_sha256"]:
                raise ValueError("frozen plugin or CLI identity changed")
            # Freeze hidden task bytes before model activity, outside all author mounts.
            shutil.copytree(source_task, private / "task")
            task = Task(private / "task")
            key = read_key(key_file)
            token = secrets.token_urlsafe(32)
            proxy = ModelProxy(key, token, {config["model"], config["haiku_model"]}, bind_host=config["proxy_bind"])
            proxy.start()
            before = proxy.usage()
            if not _budget(before):
                raise ValueError("provider budget is unavailable or outside the approved cap")
            network = resources.internal_network()
            relay = resources.start_relay(network, config["proxy_target"], proxy.port)
            author = resources.start_agent(
                network, author_image, cli, plugin, agent_environment(config, token), relay, storage_quota=True
            )
            version = docker.call(["exec", author, "/opt/claude", "--version"]).stdout.decode().strip()
            if version != config["cli_version"]:
                raise ValueError("mounted CLI version differs from approved identity")
            runtime = _runtime(docker, author, version)
            paths = TrialPaths(run)
            env = FleetEnvironment(
                resources=resources,
                container=author,
                role="author",
                task=task,
                trial_paths=paths,
                wall_seconds=case["agent_timeout_sec"],
                config=config,
                sensitive=(key, token),
            )
            context = AgentContext()
            asyncio.run(
                FleetAgent(logs_dir=run / "agent", model_name=config["model"]).run(task.instruction, env, context)
            )
            execution = env.execution
            # Stop all author processes before artifact collection or hidden-test exposure.
            docker.call(["stop", "--time", "0", author])
            if execution is None or execution["stop"]:
                raise RuntimeError("author instrumentation stopped before a complete artifact handoff")
            parsed = tracing.parse_trace(run / "agent/stdout.jsonl")
            if proxy.auth_failed or not parsed.saw_init or not parsed.has_result or not parsed.tool_counts_complete:
                raise ValueError("author authentication or trace completion unavailable")
            if (
                parsed.foreign_skills
                or parsed.denials
                or any(
                    tracing.is_guard_denial(text) or tracing.GUARD_UNAVAILABLE_MARKER in text.lower()
                    for text in parsed.tool_errors
                )
            ):
                raise ValueError("author tool or skill boundary failed")
            if (execution["returncode"] or parsed.result_is_error) and parsed.result_subtype != "error_max_turns":
                raise ValueError("author execution did not complete successfully")
            if fingerprints.plugin_digest(plugin) != bound["plugin_sha256"] or sha256(cli) != bound["cli_sha256"]:
                raise ValueError("frozen plugin or CLI identity changed during authoring")
            tools = invocation.expected_runtime_tools(plugin, "software-engineer")
            mismatch = artifacts.runtime_problem(
                run / "agent/stdout.jsonl", plugin, "/opt/fleet", config["model"], tools
            )
            if mismatch:
                raise ValueError("native identity boundary: " + mismatch)
            submission = private / "submission"
            collect_tree(docker, author, "/app", submission)
            for submitted in submission.rglob("*"):
                if submitted.is_file():
                    artifacts.screen(submitted.read_bytes(), (key, token))
            submission_files = {
                p.relative_to(submission).as_posix(): sha256(p) for p in submission.rglob("*") if p.is_file()
            }
            execution_receipt["submission_sha256"] = canonical_digest(submission_files)
            execution_receipt["submission_files"] = submission_files
            # /app is the sole writable task handoff. No author home, logs, policy,
            # credentials or running processes enter the verifier container.
            verifier = _verifier_container(resources, verifier_image)
            docker.call(["exec", verifier, "/bin/sh", "-c", "find /app -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +"])
            docker.call(["cp", str(submission) + "/.", verifier + ":/app"])
            independent = FleetEnvironment(
                resources=resources,
                container=verifier,
                role="verifier",
                task=task,
                trial_paths=paths,
                wall_seconds=case["verifier_timeout_sec"],
            )
            verification = asyncio.run(
                verify_task(task, independent, paths, submission_script=case["submission_script"])
            )
            (run / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    except (Exception, KeyboardInterrupt) as exc:
        problem = type(exc).__name__
    finally:
        if proxy:
            try:
                after = proxy.usage()
            except Exception:
                problem = problem or "provider billing unavailable after assessment"
            try:
                proxy.close()
            except Exception:
                problem = problem or "model proxy cleanup failed"
                cleanup.append(
                    {
                        "kind": "proxy",
                        "name": resources.prefix + "-proxy",
                        "bind": config["proxy_bind"],
                        "port": proxy.port,
                        "present": None,
                        "removed": False,
                    }
                )
        cleanup.extend(resources.cleanup())
        cleanup_ok = bool(cleanup) and all(item.get("present") is False for item in cleanup)
        (run / "cleanup.json").write_text(json.dumps(cleanup, indent=2) + "\n")
        (run / "billing.json").write_text(
            json.dumps(
                {
                    "complete": _measured(before, after) is not None,
                    "measured_usd": _measured(before, after),
                    "before": before,
                    "after": after,
                },
                indent=2,
            )
            + "\n"
        )
        if verification is None:
            (run / "verification.json").write_text(
                json.dumps(
                    {"native_result": None, "execution_error": problem, "assessment": {"verdict": "INCONCLUSIVE"}}
                )
                + "\n"
            )
        (run / "verifier").mkdir(exist_ok=True)
        (run / "verifier/verifier-receipt.json").write_text(
            json.dumps(
                {
                    "instance_id": case["local_case_id"],
                    "outcome": verification["assessment"]["verdict"] if verification else "INCONCLUSIVE",
                    "native_result": verification["native_result"] if verification else None,
                    "execution_actor": "independent-verifier",
                    "identity": identity,
                },
                indent=2,
            )
            + "\n"
        )
        (run / "policy-review.json").write_text(
            json.dumps({"status": "pending", "reason": "human trace review required"}) + "\n"
        )
        (run / "execution-receipt.json").write_text(json.dumps(execution_receipt, indent=2) + "\n")
        record = make_record(
            case=case,
            candidate=candidate,
            runner=runner,
            runtime=runtime,
            model=config["model"],
            label=label,
            started=started,
            ended=datetime.now(UTC).isoformat(timespec="seconds"),
            execution=execution,
            verification=verification,
            problem=problem,
            cleanup_ok=cleanup_ok,
            identity=identity,
        )
        (run / "record.json").write_text(json.dumps(record, indent=2) + "\n")
        if cleanup_ok:
            pending.unlink()
    return record
