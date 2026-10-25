"""Native static-test author lifecycle, using the admitted WP08 isolation primitives."""

from __future__ import annotations

import contextlib
import hashlib
import json
import secrets
import shutil
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from probe import fingerprints, invocation, tracing
from probe.records import RecordV1
from swebench_adapter import artifacts
from swebench_adapter.containers import Docker, DockerResources
from swebench_adapter.proxy import ModelProxy, read_key
from swebench_adapter.runner import _budget, _measured, _runtime, agent_environment, image_identity, runtime_binding

from swt_adapter import core, verifier

SWT_REQUIREMENTS = Path(__file__).resolve().parents[2] / "requirements-swt.txt"

SMOKE_CHECKS = (
    "reference_reproduces",
    "always_fail_rejected",
    "pass_both_rejected",
    "unrelated_import_rejected",
    "patch_text_rejected",
    "code_fix_rejected",
    "guard_allow",
    "guard_deny",
    "no_cr",
    "history_pruned",
    "egress",
    "cpu_cap",
    "storage_cap",
    "cleanup",
)


def author_command(config: dict[str, Any], public: dict[str, Any]) -> list[str]:
    prompt = (
        "Write regression tests for this public repository issue using static authoring. "
        "Inspect source and edit only test files; do not run repository code or tests. "
        "An independent verifier runs your tests before and after a hidden repair. "
        "Test observable behavior; do not inspect source text, Git history or reference patches. "
        "Leave changes in the working tree without committing. Report verification honestly.\n\n"
        "Public issue:\n" + public["problem_statement"]
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
    position = command.index("--disallowedTools") + 1
    command[position] = ",".join(dict.fromkeys([*command[position].split(","), "WebFetch", "WebSearch"]))
    if config.get("api_key_helper"):
        position = command.index("--settings") + 1
        settings = json.loads(command[position])
        settings["apiKeyHelper"] = 'printf "%s" "$ANTHROPIC_AUTH_TOKEN"'
        command[position] = json.dumps(settings)
    return command


def adapter_digest() -> str:
    files = [*Path(__file__).parent.glob("*.py"), Path(__file__).parents[1] / "swt_pilot.py"]
    return core.digest({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files})


def live_binding(
    config: dict[str, Any], manifest: dict[str, Any], row: dict[str, Any], docker: Docker
) -> dict[str, Any]:
    binding = runtime_binding(config, manifest, docker)
    if binding["host_runtime"]["identity"]["elevated"] is not False:
        raise ValueError("live evaluation requires an observed unelevated account")
    shared_digest = binding["adapter_sha256"]
    swt_digest = adapter_digest()
    requirements_digest = hashlib.sha256(SWT_REQUIREMENTS.read_bytes()).hexdigest()
    binding.update(
        shared_adapter_sha256=shared_digest,
        swt_adapter_sha256=swt_digest,
        swt_requirements_sha256=requirements_digest,
        adapter_sha256=core.digest(
            {"shared": shared_digest, "swt": swt_digest, "requirements-swt": requirements_digest}
        ),
        swt_upstream_revision=core.UPSTREAM_REVISION,
        instance_id=row["instance_id"],
        task_sha256=core.digest(row),
        execution_profile="static-tests-independently-verified-dec13",
    )
    return binding


def bound_provenance(binding: dict[str, Any]) -> dict[str, Any]:
    provenance = fingerprints.runner_provenance()
    provenance["runner_source_sha256"] = binding["adapter_sha256"]
    return provenance


def _json_bytes(path: Path) -> tuple[dict[str, Any], bytes]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("invalid receipt file")
    data = path.read_bytes()
    if len(data) > 8 * 1024 * 1024:
        raise ValueError("receipt grew beyond limit")

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate receipt field")
            result[key] = value
        return result

    value = json.loads(data, object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError("receipt is not an object")
    return value, data


def require_admission(admission_path: Path, binding: dict[str, Any]) -> None:
    """Reopen actual hash-bound smoke evidence before credentials or paid setup."""
    try:
        receipt, _ = _json_bytes(admission_path)
    except (OSError, ValueError, TypeError, AttributeError):
        raise ValueError("exact SWT acceptance file is required") from None
    if (
        receipt.get("accepted") is not True
        or not isinstance(receipt.get("owner"), str)
        or not receipt["owner"].strip()
        or receipt.get("binding") != binding
    ):
        raise ValueError("exact SWT candidate and run-condition acceptance is required")
    try:
        relative = receipt.get("smoke_receipt")
        if (
            not isinstance(relative, str)
            or not relative
            or "\\" in relative
            or PurePosixPath(relative).is_absolute()
            or PureWindowsPath(relative).drive
            or any(p in {".", ".."} for p in relative.split("/"))
        ):
            raise ValueError
        path = admission_path.absolute().parent
        for part in PurePosixPath(relative).parts:
            path = path / part
            if path.is_symlink():
                raise ValueError
        smoke, raw = _json_bytes(path)
        if hashlib.sha256(raw).hexdigest() != receipt.get("smoke_sha256"):
            raise ValueError
        checks = smoke.get("checks")
        clean = smoke.get("cleanup")
        if (
            smoke.get("format") != "wp09-swt-smoke"
            or type(smoke.get("schema_version")) is not int
            or smoke["schema_version"] != 1
            or smoke.get("instance_id") != binding["instance_id"]
            or smoke.get("binding") != binding
            or "error" not in smoke
            or smoke["error"] is not None
            or type(smoke.get("model_calls")) is not int
            or smoke["model_calls"] != 0
            or not isinstance(checks, dict)
            or set(checks) != set(SMOKE_CHECKS)
            or any(checks[k] is not True for k in SMOKE_CHECKS)
            or not isinstance(clean, list)
            or not clean
            or any(
                not isinstance(c, dict) or c.get("present") is not False or c.get("removed") is not True for c in clean
            )
        ):
            raise ValueError
        observations = smoke.get("observations")
        if not isinstance(observations, dict) or set(observations) != {
            "gold",
            "always-fail",
            "pass-both",
            "unrelated-import",
        }:
            raise ValueError
        for name, evidence in observations.items():
            supervisor, result = evidence["supervisor"], evidence["verifier"]
            cleanup = supervisor.get("cleanup")
            expected_names = set(verifier.container_names(supervisor["run_id"]))
            if (
                supervisor.get("process_cleanup_complete") is not True
                or supervisor.get("receipt_available") is not True
                or supervisor.get("stop") is not None
                or type(supervisor.get("exit_code")) is not int
                or supervisor["exit_code"] != 0
                or not isinstance(cleanup, list)
                or not cleanup
                or any(not isinstance(c, dict) or c.get("removed") is not True for c in cleanup)
                or len(cleanup) != 6
                or {c.get("name") for c in cleanup} != expected_names
                or result.get("instance_id") != binding["instance_id"]
                or result.get("row_sha256") != binding["task_sha256"]
                or result.get("mechanical") != ("PASS" if name == "gold" else "FAIL")
            ):
                raise ValueError
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise ValueError("complete digest-bound model-free SWT smoke evidence is required") from None


def make_record(
    identity: dict[str, Any], author: dict[str, Any], verified: dict[str, Any], evidence: dict[str, str]
) -> dict[str, Any]:
    value = artifacts.make_record(
        identity=identity,
        candidate=author["candidate"],
        runner=author["runner"],
        model=author["model"],
        runtime=author["runtime"],
        label="claude",
        started=author["started"],
        ended=author["ended"],
        state=verified["verdict"],
        reason=verified.get("reason"),
        ending=author["ending"],
        stop=author["stop"],
        estimated_cost=author["estimate"],
        evidence=evidence,
        after_assessment=author.get("after_assessment"),
    )
    value["conditions"]["execution_profile"] = {
        "name": "static-tests-independently-verified-dec13",
        "authentication": "openrouter-host-proxy",
    }
    value["checks"] = []
    for key, title, state in [
        ("independent-reproduction", "Independent SWT fail-before/pass-after", verified["mechanical"]),
        ("reproduction-relevance", "Human behavioral relevance", verified.get("relevance", "INCONCLUSIVE")),
        ("test-patch-admission", "Submitted patch changes admitted tests", verified.get("admission", "INCONCLUSIVE")),
    ]:
        if state == "UNVERIFIED":
            state = "INCONCLUSIVE"
        value["checks"].append(
            {
                "id": key,
                "text": title,
                "kind": "requires",
                "state": state,
                "reason": verified.get("reason") if state == "INCONCLUSIVE" else None,
                "evidence": verified.get("reason") or title,
                "evidence_truncated": False,
            }
        )
    return RecordV1.model_validate_json(json.dumps(value)).model_dump(mode="json")


def run_trial(
    config: dict[str, Any],
    manifest: dict[str, Any],
    rows: list[dict[str, Any]],
    excluded: set[str],
    instance_id: str,
    output: Path,
    key_file: Path,
    source: Path,
    admission: Path,
) -> dict[str, Any]:
    """One explicitly accepted native-author trial followed by independent upstream verification."""
    selected = core.select(manifest, rows, excluded)
    row = next((r for r in selected if r["instance_id"] == instance_id), None)
    if row is None:
        raise ValueError("instance is outside SWT selection")
    verifier.check_source(source)
    docker = Docker()
    problems = verifier.runtime_problems()
    if problems:
        raise ValueError("; ".join(problems))
    binding = live_binding(config, manifest, row, docker)
    require_admission(admission, binding)
    image = image_identity(docker, config, instance_id)
    run = output / f"eval-{instance_id}" / "claude" / "run-1"
    if run.exists():
        raise ValueError("attempt already exists; refusing overwrite or automatic repeat")
    if (output / "swt-pending-cleanup.json").exists():
        raise ValueError("prior SWT cleanup requires reconciliation")
    run.mkdir(parents=True, mode=0o700)
    prefix = "wp09-" + uuid.uuid4().hex
    resources = DockerResources(docker, prefix)
    artifacts.store_json(
        output,
        "swt-pending-cleanup.json",
        {
            "prefix": prefix,
            "run": str(run),
            "author_resources": [prefix + "-agent", prefix + "-relay", prefix + "-network"],
            "verifier_containers": verifier.container_names(prefix),
        },
    )
    candidate = fingerprints.plugin_provenance(Path(config["plugin_root"]))
    provenance = bound_provenance(binding)
    author = {
        "candidate": candidate,
        "runner": provenance,
        "model": config["model"],
        "runtime": {"cli_version": None, "host_platform": {}, "host_identity": None},
        "started": datetime.now(UTC).isoformat(),
        "ending": "cut_short",
        "stop": "cut_short",
        "estimate": None,
    }
    verified = {
        "instance_id": instance_id,
        "mechanical": "INCONCLUSIVE",
        "verdict": "INCONCLUSIVE",
        "reason": "author or verifier did not complete",
        "relevance": "UNVERIFIED",
    }
    proxy = None
    key = ""
    before = None
    after = None
    cleanup = []
    evidence = {}
    supervised = None
    verifier_started = False
    try:
        with tempfile.TemporaryDirectory(prefix="wp09-author-") as temporary:
            private = Path(temporary)
            plugin = fingerprints.stage_plugin(Path(config["plugin_root"]), private / "fleet")
            cli = private / "claude"
            shutil.copy2(config["cli_path"], cli)
            cli.chmod(0o500)
            if (
                fingerprints.plugin_digest(plugin) != binding["plugin_sha256"]
                or hashlib.sha256(cli.read_bytes()).hexdigest() != binding["cli_sha256"]
            ):
                raise ValueError("staged native candidate identity mismatch")
            key = read_key(key_file)
            token = secrets.token_urlsafe(32)
            proxy = ModelProxy(key, token, {config["model"], config["haiku_model"]}, bind_host=config["proxy_bind"])
            proxy.start()
            before = proxy.usage()
            if proxy.auth_failed or not _budget(before):
                raise ValueError("unknown or exhausted approved model budget")
            network = resources.internal_network()
            address = resources.start_relay(network, config["proxy_target"], proxy.port)
            container = resources.start_agent(
                network, image, cli, plugin, agent_environment(config, token), address, storage_quota=True
            )
            resources.setup_repository(container, row["base_commit"])
            version = docker.call(["exec", container, "/opt/claude", "--version"]).stdout.decode().strip()
            if version != config["cli_version"]:
                raise ValueError("native CLI version mismatch")
            author["runtime"] = _runtime(docker, container, version)
            command = author_command(config, core.author_input(row))
            artifacts.store_json(run, "command.json", command, secrets=(key,))
            evidence["command"] = "command.json"
            executed = resources.execute(container, command, wall_seconds=2700, storage_quota=True)
            artifacts.store_bytes(run, "stdout.jsonl", executed.stdout, secrets=(key,))
            evidence["trace"] = "stdout.jsonl"
            artifacts.store_bytes(run, "stderr.txt", executed.stderr, secrets=(key,))
            parsed = tracing.parse_trace(run / "stdout.jsonl")
            author["estimate"] = tracing.known_usd(parsed.total_cost_usd)
            tools = invocation.expected_runtime_tools(plugin, "software-engineer")
            problem = artifacts.runtime_problem(run / "stdout.jsonl", plugin, "/opt/fleet", config["model"], tools)
            if (
                executed.stop
                or proxy.auth_failed
                or problem
                or parsed.foreign_skills
                or parsed.denials
                or not parsed.tool_counts_complete
                or (executed.returncode and parsed.result_subtype != "error_max_turns")
                or (parsed.result_is_error and parsed.result_subtype != "error_max_turns")
                or fingerprints.plugin_digest(plugin) != binding["plugin_sha256"]
                or hashlib.sha256(cli.read_bytes()).hexdigest() != binding["cli_sha256"]
            ):
                raise ValueError("author execution or native runtime identity failed")
            author.update(ending="turn_limit" if parsed.result_subtype == "error_max_turns" else "completed", stop=None)
            staged = resources.execute(
                container, ["git", "-c", "core.hooksPath=/dev/null", "add", "-A"], wall_seconds=60, storage_quota=True
            )
            captured = resources.execute(
                container,
                ["git", "-c", "core.hooksPath=/dev/null", "diff", "--cached", row["base_commit"]],
                wall_seconds=60,
                storage_quota=True,
            )
            if staged.stop or staged.returncode or captured.stop or captured.returncode:
                raise ValueError("patch capture failed")
            artifacts.store_bytes(run, "submitted.diff", captured.stdout, secrets=(key,))
            evidence["patch"] = "submitted.diff"
            patch = captured.stdout.decode()
            roots = next(c["test_roots"] for c in manifest["cases"] if c["instance_id"] == instance_id)
            admitted = core.admit_patch(patch, roots)
            artifacts.store_json(run, "patch-admission.json", admitted)
            if admitted["state"] == "FAIL":
                verified.update(verdict="FAIL", admission="FAIL", reason=admitted["reason"])
            else:
                endpoint = docker.argv[2]
                info = json.loads(docker.call(["info", "--format", "{{json .}}"]).stdout)
                verifier_started = True
                supervised = verifier.supervise(
                    source, row, patch, roots, run / "verifier", prefix, image, endpoint, info["ID"]
                )
                if supervised["receipt_available"]:
                    verified = json.loads((run / "verifier/verifier-receipt.json").read_text())
                    evidence["verifier"] = "verifier/verifier-receipt.json"
    except (Exception, KeyboardInterrupt) as error:
        author["execution_failure"] = type(error).__name__
    finally:
        if proxy is not None:
            with contextlib.suppress(Exception):
                after = proxy.usage()
            try:
                proxy.close()
            except Exception:
                cleanup.append({"kind": "proxy", "present": None, "removed": False})
        cleanup.extend(resources.cleanup())
        if supervised is not None:
            cleanup.extend(
                {
                    "kind": "verifier-container",
                    "name": c["name"],
                    "present": False if c["removed"] else None,
                    "removed": c["removed"],
                }
                for c in supervised["cleanup"]
            )
            if not supervised["process_cleanup_complete"]:
                cleanup.append({"kind": "host_process", "present": None, "removed": False})
        if verifier_started and supervised is None:
            cleanup.append({"kind": "verifier_process_or_containers", "present": None, "removed": False})
        clean = bool(cleanup) and all(c.get("present") is False for c in cleanup)
        if clean:
            (output / "swt-pending-cleanup.json").unlink()
        else:
            author["after_assessment"] = "cleanup remains unresolved"
        author["ended"] = datetime.now(UTC).isoformat()
        verified["outcome"] = verified["mechanical"]
        artifacts.store_json(run, "author-receipt.json", author)
        artifacts.store_json(run, "binding.json", binding)
        artifacts.store_json(run, "cleanup.json", cleanup)
        artifacts.store_json(
            run,
            "billing.json",
            {
                "before": before,
                "after": after,
                "measured_usd": _measured(before, after),
                "complete": _measured(before, after) is not None,
            },
        )
        artifacts.store_json(
            run,
            "policy-review.json",
            {
                "status": "unreviewed",
                "agent_executed_tests": None,
                "profile": "static-tests-independently-verified-dec13",
            },
        )
        if not (run / "verifier/verifier-receipt.json").exists():
            artifacts.store_json(run / "verifier", "verifier-receipt.json", verified)
        artifacts.store_json(
            run,
            "record.json",
            make_record({"instance_id": instance_id, "row_sha256": core.digest(row)}, author, verified, evidence),
        )
    return verified
