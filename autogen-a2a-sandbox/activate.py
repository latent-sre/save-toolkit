#!/usr/bin/env python
"""Sole host entrypoint for the offline AutoGen/A2A sandbox."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


EXIT_USAGE = 64
EXIT_PRECONDITION = 69
EXIT_RUNTIME = 70
EXIT_PENDING = 20
EXIT_TERMINAL = 2

_REVISION = re.compile(r"^[0-9a-f]{40}$")
_IMAGE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
_RUN_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_RESOURCE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")
_CASE_IDS = frozenset(
    {
        "mission-healthy-001",
        "confirmed-regression-001",
        "stale-evidence-reconciled-001",
        "unresolved-contradiction-001",
        "slow-analysis-cancel-001",
        "checkpoint-resume-001",
    }
)
_HANDOFF_FIELDS = frozenset(
    {
        "handoff_version",
        "state",
        "run_id",
        "source_revision",
        "case_id",
        "case_digest",
        "candidate_revision",
        "artifact_digest",
        "checkpoint_id",
        "image_id",
        "project",
        "state_volume",
        "evidence_volume",
    }
)
_SENSITIVE_EXACT = frozenset(
    {
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "DOCKER_HOST",
        "DOCKER_CONTEXT",
        "DOCKER_CONFIG",
        "DOCKER_TLS_VERIFY",
        "DOCKER_CERT_PATH",
        "COMPOSE_FILE",
        "COMPOSE_PROJECT_NAME",
        "COMPOSE_PROFILES",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "CF_HOME",
        "SSH_AUTH_SOCK",
        "MODEL_NAME",
    }
)
_SENSITIVE_PREFIXES = (
    "OPENAI_",
    "ANTHROPIC_",
    "AZURE_",
    "AWS_",
    "GCP_",
    "GOOGLE_CLOUD_",
    "GITHUB_",
    "CF_",
    "PCF_",
    "SSH_",
    "DOCKER_",
    "COMPOSE_",
    "MODEL_",
)


class ActivationError(RuntimeError):
    """A fail-closed host precondition or runtime boundary failed."""

    def __init__(self, error_class: str, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.error_class = error_class
        self.exit_code = exit_code


class ActivationArgumentParser(argparse.ArgumentParser):
    """Translate invalid CLI input into the activation error envelope."""

    def error(self, message: str) -> None:
        raise ActivationError("invalid_arguments", message, EXIT_USAGE)


@dataclass(frozen=True, slots=True)
class ComposeExpectation:
    image: str
    project: str
    state_volume: str
    evidence_volume: str
    network: str
    mode: str
    source_revision: str
    run_id: str
    case_id: str
    decision: str


@dataclass(frozen=True, slots=True)
class RunIdentity:
    project: str
    state_volume: str
    evidence_volume: str
    network: str


def build_parser() -> argparse.ArgumentParser:
    parser = ActivationArgumentParser(
        description="Build and run the bounded AutoGen GraphFlow + A2A sandbox."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="build the exact revision-bound image")
    _common_identity_arguments(build)

    fresh = commands.add_parser("fresh", help="run one immutable case to its terminal")
    _common_identity_arguments(fresh)
    fresh.add_argument("--run-id", required=True)
    fresh.add_argument("--evidence-root", required=True)
    fresh.add_argument("--case", required=True, choices=sorted(_CASE_IDS))
    fresh.add_argument("--approval-fixture", required=True, choices=("PENDING",))

    resume = commands.add_parser("resume", help="restore the exact final approval checkpoint")
    _common_identity_arguments(resume)
    resume.add_argument("--run-id", required=True)
    resume.add_argument("--evidence-root", required=True)
    resume.add_argument("--decision", required=True, choices=("ACCEPT", "REJECT"))
    return parser


def _common_identity_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--docker-context", required=True)
    parser.add_argument("--source-revision", required=True)


def reject_ambient_environment(environment: Mapping[str, str]) -> None:
    """Reject ambient values that could redirect Docker or reach a provider."""

    rejected: list[str] = []
    for raw_name in environment:
        name = raw_name.upper()
        if (
            name in _SENSITIVE_EXACT
            or name.endswith("_PROXY")
            or any(name.startswith(prefix) for prefix in _SENSITIVE_PREFIXES)
        ):
            rejected.append(raw_name)
    if rejected:
        names = ", ".join(sorted(rejected, key=str.upper))
        raise ActivationError(
            "unsafe_environment",
            f"remove rejected ambient environment variable(s): {names}",
            EXIT_PRECONDITION,
        )


def validate_compose_model(
    model: Mapping[str, object], expectation: ComposeExpectation
) -> None:
    """Fail closed unless Compose rendered the exact bounded topology."""

    if type(model) is not dict:
        _model_error("topology", "rendered Compose model is not an object")
    if set(model) - {"name", "services", "networks", "volumes"}:
        _model_error("topology", "rendered model has unsupported top-level fields")
    if model.get("name") != expectation.project:
        _model_error("topology", "rendered project identity mismatch")
    services = model.get("services")
    if type(services) is not dict or set(services) != {"worker", "orchestrator"}:
        _model_error("third", "topology must contain exactly two named services")
    networks = model.get("networks")
    if type(networks) is not dict or set(networks) != {"sandbox"}:
        _model_error("network", "topology must contain exactly one network")
    network = networks["sandbox"]
    if (
        type(network) is not dict
        or set(network) - {"name", "internal", "external", "ipam"}
        or network.get("internal") is not True
        or network.get("name") != expectation.network
        or network.get("external") not in (None, False)
        or network.get("ipam", {}) != {}
    ):
        _model_error("external", "network must be the expected internal-only network")
    volumes = model.get("volumes")
    if type(volumes) is not dict or set(volumes) != {"state", "evidence"}:
        _model_error("volume", "topology must contain only state and evidence volumes")
    if type(volumes["state"]) is not dict or set(volumes["state"]) != {"name"}:
        _model_error("volume", "state volume may not carry driver or bind options")
    if type(volumes["evidence"]) is not dict or set(volumes["evidence"]) != {"name"}:
        _model_error("volume", "evidence volume may not carry driver or bind options")
    if volumes["state"].get("name") != expectation.state_volume:
        _model_error("volume", "state volume identity mismatch")
    if volumes["evidence"].get("name") != expectation.evidence_volume:
        _model_error("volume", "evidence volume identity mismatch")

    for service_name in ("worker", "orchestrator"):
        service = services[service_name]
        if type(service) is not dict:
            _model_error("service", f"{service_name} is not an object")
        _validate_service(service_name, service, expectation)


def _validate_service(
    name: str, service: Mapping[str, object], expectation: ComposeExpectation
) -> None:
    common_fields = {
        "cap_drop",
        "command",
        "cpus",
        "entrypoint",
        "image",
        "init",
        "mem_limit",
        "networks",
        "pids_limit",
        "read_only",
        "restart",
        "security_opt",
        "tmpfs",
        "user",
        "volumes",
    }
    allowed_fields = common_fields | (
        {"healthcheck"} if name == "worker" else {"depends_on"}
    )
    forbidden = {
        "build",
        "ports",
        "expose",
        "cap_add",
        "devices",
        "device_cgroup_rules",
        "privileged",
        "network_mode",
        "pid",
        "ipc",
        "uts",
        "secrets",
        "configs",
        "environment",
        "env_file",
        "extra_hosts",
        "external_links",
    }
    present = sorted(forbidden & set(service))
    if present:
        label = "host port" if "ports" in present else present[0]
        if "build" in present:
            label = "build"
        if "cap_add" in present:
            label = "capability"
        _model_error(label, f"{name} has forbidden fields: {present}")
    unknown_fields = sorted(set(service) - allowed_fields)
    if unknown_fields:
        _model_error(unknown_fields[0], f"{name} has unsupported fields: {unknown_fields}")
    if service.get("image") != expectation.image:
        _model_error("different", f"{name} does not use the exact immutable image")
    if service.get("entrypoint") is not None:
        _model_error("entrypoint", f"{name} may not override the image entrypoint")
    if service.get("user") != "65532:65532":
        _model_error("root", f"{name} must use numeric uid:gid 65532:65532")
    if service.get("read_only") is not True:
        _model_error("writable", f"{name} root filesystem must be read-only")
    if service.get("init") is not True:
        _model_error("init", f"{name} must run with an init process")
    if service.get("cap_drop") != ["ALL"]:
        _model_error("capability", f"{name} must drop every capability")
    if service.get("security_opt") != ["no-new-privileges:true"]:
        _model_error("security", f"{name} must set no-new-privileges")
    if service.get("restart") not in (None, "no"):
        _model_error("restart", f"{name} must not restart automatically")
    pids_limit = service.get("pids_limit")
    if type(pids_limit) is not int or not 1 <= pids_limit <= 128:
        _model_error("unbounded", f"{name} pids limit is absent or excessive")
    cpus = service.get("cpus")
    if type(cpus) not in (int, float) or not 0 < float(cpus) <= 2:
        _model_error("resource", f"{name} cpu limit is absent or excessive")
    try:
        memory = int(service.get("mem_limit", 0))
    except (TypeError, ValueError):
        memory = 0
    if not 64 * 1024 * 1024 <= memory <= 1024 * 1024 * 1024:
        _model_error("resource", f"{name} memory limit is absent or excessive")
    tmpfs = service.get("tmpfs")
    if type(tmpfs) is not list or len(tmpfs) != 1:
        _model_error("tmpfs", f"{name} must have one bounded tmpfs")
    tmpfs_value = tmpfs[0]
    if (
        type(tmpfs_value) is not str
        or not tmpfs_value.startswith("/tmp:")
        or not all(flag in tmpfs_value for flag in ("noexec", "nosuid", "nodev", "size="))
    ):
        _model_error("tmpfs", f"{name} tmpfs is not bounded and hardened")
    if service.get("networks") != {"sandbox": None}:
        _model_error("network", f"{name} is not attached only to the internal network")
    _validate_mounts(name, service.get("volumes"))
    _validate_command(name, service.get("command"), expectation)
    if name == "worker":
        healthcheck = service.get("healthcheck")
        expected_test = [
            "CMD",
            "python",
            "-m",
            "interop_sandbox.runtime_cli",
            "healthcheck",
            "--url",
            "http://127.0.0.1:8081/readyz",
        ]
        if type(healthcheck) is not dict or healthcheck.get("test") != expected_test:
            _model_error("healthcheck", "worker readiness healthcheck drifted")
        if set(healthcheck) != {"test", "interval", "timeout", "retries", "start_period"}:
            _model_error("healthcheck", "worker readiness healthcheck is not closed")
        if (
            healthcheck.get("interval") != "2s"
            or healthcheck.get("timeout") != "2s"
            or healthcheck.get("retries") != 20
            or healthcheck.get("start_period") != "2s"
        ):
            _model_error("healthcheck", "worker readiness retry budget drifted")
    elif service.get("depends_on") != {
        "worker": {"condition": "service_healthy", "required": True}
    }:
        _model_error("depends_on", "orchestrator dependency contract drifted")


def _validate_mounts(name: str, value: object) -> None:
    if type(value) is not list:
        _model_error("mount", f"{name} mounts are missing")
    expected = (
        {("state", "/state")}
        if name == "worker"
        else {("state", "/state"), ("evidence", "/evidence")}
    )
    actual: set[tuple[str, str]] = set()
    for mount in value:
        if type(mount) is not dict or mount.get("type") != "volume":
            _model_error("bind", f"{name} contains a non-volume mount")
        if set(mount) - {"type", "source", "target", "read_only", "volume"}:
            _model_error("mount", f"{name} mount has unsupported options")
        source = mount.get("source")
        target = mount.get("target")
        if type(source) is not str or type(target) is not str:
            _model_error("mount", f"{name} mount identity is malformed")
        actual.add((source, target))
    if actual != expected:
        _model_error("mount", f"{name} mount set does not match the contract")


def _validate_command(
    name: str, value: object, expectation: ComposeExpectation
) -> None:
    if type(value) is not list or not all(type(item) is str for item in value):
        _model_error("command", f"{name} command must be an argument array")
    if value[:3] != ["python", "-m", "interop_sandbox.runtime_cli"]:
        _model_error("command", f"{name} command does not invoke the runtime module")
    if name == "worker":
        required = [
            "worker",
            "--state-directory",
            "/state",
            "--agent-url",
            "http://worker:8081/a2a/jsonrpc",
            "--host",
            "0.0.0.0",
            "--port",
            "8081",
        ]
        if value[3:] != required:
            _model_error("command", "worker command drifted")
    else:
        required = [
            "orchestrate",
            "--mode",
            expectation.mode,
            "--source-revision",
            expectation.source_revision,
            "--run-id",
            expectation.run_id,
            "--case",
            expectation.case_id,
            "--decision",
            expectation.decision,
            "--worker-url",
            "http://worker:8081",
            "--state-directory",
            "/state",
            "--evidence-directory",
            "/evidence",
            "--cases-directory",
            "/opt/interop-sandbox/cases",
        ]
        if value[3:] != required:
            _model_error("command", "orchestrator command drifted")


def _model_error(label: str, message: str) -> None:
    raise ActivationError("unsafe_compose_model", f"{label}: {message}", EXIT_PRECONDITION)


def validate_resume_handoff(
    value: object,
    *,
    source_revision: str,
    run_id: str,
    image_id: str,
    project: str,
    state_volume: str,
    evidence_volume: str,
) -> Mapping[str, object]:
    if type(value) is not dict or set(value) != _HANDOFF_FIELDS:
        raise ActivationError("invalid_handoff", "resume handoff is not a closed object", EXIT_PRECONDITION)
    expected = {
        "handoff_version": "autogen-a2a-resume-handoff/v1",
        "state": "AWAITING_APPROVAL",
        "run_id": run_id,
        "source_revision": source_revision,
        "image_id": image_id,
        "project": project,
        "state_volume": state_volume,
        "evidence_volume": evidence_volume,
    }
    for field, expected_value in expected.items():
        if value.get(field) != expected_value:
            raise ActivationError("invalid_handoff", f"resume handoff {field} mismatch", EXIT_PRECONDITION)
    if value.get("case_id") not in _CASE_IDS:
        raise ActivationError("invalid_handoff", "resume handoff case_id mismatch", EXIT_PRECONDITION)
    for field, pattern in (
        ("case_digest", re.compile(r"^[0-9a-f]{64}$")),
        ("candidate_revision", _REVISION),
        ("artifact_digest", re.compile(r"^[0-9a-f]{64}$")),
    ):
        item = value.get(field)
        if type(item) is not str or pattern.fullmatch(item) is None:
            raise ActivationError("invalid_handoff", f"resume handoff {field} is malformed", EXIT_PRECONDITION)
    checkpoint_id = value.get("checkpoint_id")
    if type(checkpoint_id) is not str or not checkpoint_id or len(checkpoint_id) > 256:
        raise ActivationError("invalid_handoff", "resume handoff checkpoint_id is malformed", EXIT_PRECONDITION)
    return value


def publish_file_once(path: Path, data: bytes) -> None:
    """Atomically create evidence, accepting only an exact idempotent replay."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() == data:
            return
        raise ActivationError("evidence_conflict", f"refusing to overwrite changed evidence: {path.name}", EXIT_PRECONDITION)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            raise ActivationError("evidence_conflict", f"refusing to overwrite changed evidence: {path.name}", EXIT_PRECONDITION)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main(argv: Sequence[str] | None = None) -> int:
    try:
        parser = build_parser()
        args = parser.parse_args(argv)
        reject_ambient_environment(os.environ)
        revision = _validated_revision(args.source_revision)
        context = _validated_context_name(args.docker_context)
        root = Path(__file__).resolve().parent
        repo = root.parent
        _validate_source_tree(repo, root, revision)
        _validate_docker_context(context)
        if args.command == "build":
            return _build(root, context, revision)
        evidence_root = _existing_evidence_root(args.evidence_root, repo)
        run_id = _validated_run_id(args.run_id)
        if args.command == "fresh":
            return _fresh(root, context, revision, run_id, args.case, evidence_root)
        return _resume(root, context, revision, run_id, evidence_root, args.decision)
    except ActivationError as exc:
        _emit_error(exc.error_class, str(exc))
        return exc.exit_code
    except KeyboardInterrupt:
        _emit_error("interrupted", "activation interrupted before success")
        return 130
    except Exception as exc:  # process boundary: bounded diagnostic, never false success
        _emit_error("activation_failure", f"activation failed ({type(exc).__name__})")
        return EXIT_RUNTIME


def _build(root: Path, context: str, revision: str) -> int:
    tag = _image_tag(revision)
    command = [
        "docker", "--context", context, "build", "--no-cache", "--platform", "linux/amd64",
        "--build-arg", f"SANDBOX_SOURCE_REVISION={revision}", "--file", str(root / "Dockerfile"),
        "--tag", tag, str(root),
    ]
    _run(command, timeout=900, capture=False)
    image_id = _resolve_image(context, tag, revision)
    print(json.dumps({"event": "image_built", "image_id": image_id, "source_revision": revision, "tag": tag}, sort_keys=True, separators=(",", ":")))
    return 0


def _fresh(root: Path, context: str, revision: str, run_id: str, case_id: str, evidence_root: Path) -> int:
    if case_id not in _CASE_IDS:
        raise ActivationError("invalid_case", "case is not one of the six immutable cases", EXIT_USAGE)
    image_id = _resolve_image(context, _image_tag(revision), revision)
    identity = _run_identity(run_id, revision)
    _require_resources_absent(context, identity)
    expectation = ComposeExpectation(image_id, identity.project, identity.state_volume, identity.evidence_volume, identity.network, "fresh", revision, run_id, case_id, "NONE")
    compose_env = _compose_environment(expectation)
    model_bytes = _render_compose(root, context, compose_env, expectation)
    authentic_pending = False
    exit_code = EXIT_RUNTIME
    try:
        result = _compose_up(root, context, compose_env)
        exit_code = result.returncode
        container_id = _orchestrator_container(context, identity.project)
        if exit_code == EXIT_PENDING:
            runtime_handoff = _copy_container_json(context, container_id, "/evidence/pending-handoff.json")
            host_handoff = dict(runtime_handoff)
            host_handoff.update({"image_id": image_id, "project": identity.project, "state_volume": identity.state_volume, "evidence_volume": identity.evidence_volume})
            validate_resume_handoff(host_handoff, source_revision=revision, run_id=run_id, image_id=image_id, project=identity.project, state_volume=identity.state_volume, evidence_volume=identity.evidence_volume)
            handoff_bytes = _canonical_json(host_handoff)
            authentic_pending = True
            publish_file_once(_handoff_path(evidence_root, run_id), handoff_bytes)
        elif exit_code == EXIT_TERMINAL:
            terminal = _copy_container_bytes(context, container_id, "/evidence/runtime-terminal.json")
            publish_file_once(evidence_root / run_id / "runtime-terminal.json", terminal)
        else:
            raise ActivationError("runtime_failed", f"orchestrator exited {exit_code}; inspect bounded container logs", EXIT_RUNTIME)
    finally:
        _compose_down(root, context, compose_env, remove_volumes=not authentic_pending)
    if authentic_pending:
        _verify_pending_cleanup(context, identity)
        print(json.dumps({"event": "AWAITING_APPROVAL", "handoff": str(_handoff_path(evidence_root, run_id)), "run_id": run_id}, sort_keys=True, separators=(",", ":")))
        return EXIT_PENDING
    _verify_full_cleanup(context, identity)
    print(json.dumps({"event": "terminal_without_approval", "run_id": run_id}, sort_keys=True, separators=(",", ":")))
    return EXIT_TERMINAL


def _resume(root: Path, context: str, revision: str, run_id: str, evidence_root: Path, decision: str) -> int:
    image_id = _resolve_image(context, _image_tag(revision), revision)
    identity = _run_identity(run_id, revision)
    handoff = _load_json_file(_handoff_path(evidence_root, run_id), "resume handoff")
    validate_resume_handoff(handoff, source_revision=revision, run_id=run_id, image_id=image_id, project=identity.project, state_volume=identity.state_volume, evidence_volume=identity.evidence_volume)
    case_id = str(handoff["case_id"])
    final_target = evidence_root / run_id / "final-bundle"
    if final_target.exists():
        raise ActivationError("evidence_conflict", "refusing to overwrite an existing final bundle", EXIT_PRECONDITION)
    _require_pending_resources(context, identity)
    expectation = ComposeExpectation(image_id, identity.project, identity.state_volume, identity.evidence_volume, identity.network, "resume", revision, run_id, case_id, decision)
    compose_env = _compose_environment(expectation)
    model_bytes = _render_compose(root, context, compose_env, expectation)
    staged: tuple[Path, Path] | None = None
    failure: BaseException | None = None
    try:
        result = _compose_up(root, context, compose_env)
        if result.returncode != 0:
            raise ActivationError("resume_failed", f"resume orchestrator exited {result.returncode}", EXIT_RUNTIME)
        container_id = _orchestrator_container(context, identity.project)
        runtime_final = _copy_container_bytes(context, container_id, "/evidence/runtime-final.json")
        graph_state = _copy_container_bytes(context, container_id, f"/state/{run_id}.graphflow-state.json")
        runtime_object = _validate_runtime_final(
            runtime_final,
            run_id=run_id,
            source_revision=revision,
            case_id=case_id,
        )
        staged = _stage_final_bundle(
            root,
            context,
            revision,
            image_id,
            case_id,
            final_target,
            model_bytes,
            runtime_final,
            runtime_object,
            graph_state,
        )
    except BaseException as exc:  # retain the authentic pending state on every failed resume
        failure = exc
    finally:
        _compose_down(root, context, compose_env, remove_volumes=staged is not None)
    if failure is not None:
        _verify_pending_cleanup(context, identity)
        raise failure
    if staged is None:
        _verify_pending_cleanup(context, identity)
        raise ActivationError("resume_incomplete", "resume did not stage final evidence; pending volumes were preserved", EXIT_RUNTIME)
    try:
        _verify_full_cleanup(context, identity)
        _finalize_bundle(*staged, run_id=run_id, revision=revision, image_id=image_id)
    except BaseException:
        if staged[0].exists():
            shutil.rmtree(staged[0])
        raise
    print(json.dumps({"event": "decision_published", "bundle": str(evidence_root / run_id / "final-bundle"), "run_id": run_id}, sort_keys=True, separators=(",", ":")))
    return 0


def _stage_final_bundle(
    root: Path,
    context: str,
    revision: str,
    image_id: str,
    case_id: str,
    target: Path,
    model_bytes: bytes,
    runtime_final: bytes,
    runtime_object: Mapping[str, object],
    graph_state: bytes,
) -> tuple[Path, Path]:
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".final-bundle.", dir=target.parent))
    try:
        try:
            graph_object = json.loads(graph_state)
        except (json.JSONDecodeError, UnicodeError) as exc:
            raise ActivationError("runtime_evidence_invalid", "GraphFlow state is not JSON", EXIT_RUNTIME) from exc
        if type(graph_object) is not dict:
            raise ActivationError("runtime_evidence_invalid", "GraphFlow state is not an object", EXIT_RUNTIME)
        graph_digest = hashlib.sha256(
            json.dumps(graph_object, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
        ).hexdigest()
        if graph_digest != runtime_object["graphflow"]["state_sha256"]:
            raise ActivationError("runtime_evidence_invalid", "GraphFlow state digest does not match final evidence", EXIT_RUNTIME)
        (stage / "case.json").write_bytes((root / "cases" / f"{case_id}.json").read_bytes())
        (stage / "case-manifest.json").write_bytes((root / "cases" / "manifest.json").read_bytes())
        (stage / "compose-model.json").write_bytes(model_bytes)
        (stage / "runtime-final.json").write_bytes(runtime_final)
        (stage / "graphflow-state.json").write_bytes(graph_state)
        (stage / "artifact.json").write_bytes(_canonical_json(runtime_object["artifact"]))
        (stage / "decision.json").write_bytes(_canonical_json(runtime_object["decision"]))
        docker_version = _run(["docker", "--context", context, "version", "--format", "{{json .Server}}"], timeout=20).stdout
        compose_version = _run(["docker", "--context", context, "compose", "version", "--short"], timeout=20).stdout.strip()
        identity_object = {"evidence_version": "autogen-a2a-environment/v1", "source_revision": revision, "image_id": image_id, "docker_context": context, "docker_server": json.loads(docker_version), "docker_compose": compose_version, "host_python": sys.version.split()[0], "runtime_python": runtime_object["python"], "packages": runtime_object["packages"]}
        (stage / "environment.json").write_bytes(_canonical_json(identity_object))
        return stage, target
    except BaseException:
        shutil.rmtree(stage)
        raise


def _finalize_bundle(
    stage: Path,
    target: Path,
    *,
    run_id: str,
    revision: str,
    image_id: str,
) -> None:
    try:
        if target.exists():
            raise ActivationError("evidence_conflict", "refusing to overwrite an existing final bundle", EXIT_PRECONDITION)
        verification = {"verification_version": "autogen-a2a-verification/v1", "result": "PASS", "run_id": run_id, "source_revision": revision, "image_id": image_id, "release_effect_executed": False, "resource_cleanup_verified": True}
        (stage / "verification.json").write_bytes(_canonical_json(verification))
        checksums = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(stage.iterdir()) if path.is_file()}
        (stage / "checksums.json").write_bytes(_canonical_json({"checksums_version": "autogen-a2a-checksums/v1", "files": checksums}))
        os.replace(stage, target)
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def _validate_runtime_final(
    value: bytes,
    *,
    run_id: str,
    source_revision: str,
    case_id: str,
) -> Mapping[str, object]:
    try:
        root = json.loads(value)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ActivationError("runtime_evidence_invalid", "final runtime evidence is not JSON", EXIT_RUNTIME) from exc
    fields = {
        "runtime_evidence_version", "status", "run_id", "source_revision", "case_id",
        "case_digest", "candidate_revision", "python", "packages", "analysis_invocations",
        "a2a", "graphflow", "approval", "artifact", "decision", "release_effect_executed",
    }
    if type(root) is not dict or set(root) != fields:
        raise ActivationError("runtime_evidence_invalid", "final runtime evidence is not closed", EXIT_RUNTIME)
    expected = {
        "runtime_evidence_version": "autogen-a2a-runtime-evidence/v1",
        "status": "DECISION_RECORDED",
        "run_id": run_id,
        "source_revision": source_revision,
        "case_id": case_id,
        "analysis_invocations": 1,
        "release_effect_executed": False,
    }
    for field, expected_value in expected.items():
        if root.get(field) != expected_value:
            raise ActivationError("runtime_evidence_invalid", f"final runtime {field} mismatch", EXIT_RUNTIME)
    artifact = root.get("artifact")
    decision = root.get("decision")
    a2a = root.get("a2a")
    graphflow = root.get("graphflow")
    approval = root.get("approval")
    if not all(type(item) is dict for item in (artifact, decision, a2a, graphflow, approval)):
        raise ActivationError("runtime_evidence_invalid", "final runtime proof sections are malformed", EXIT_RUNTIME)
    bindings = ("run_id", "source_revision", "case_id", "case_digest", "candidate_revision", "artifact_digest")
    for field in bindings:
        expected_value = artifact.get(field)
        if field != "artifact_digest" and root.get(field) != expected_value:
            raise ActivationError("runtime_evidence_invalid", f"artifact {field} mismatch", EXIT_RUNTIME)
        if decision.get(field) != expected_value:
            raise ActivationError("runtime_evidence_invalid", f"decision {field} mismatch", EXIT_RUNTIME)
    if decision.get("decision") not in ("ACCEPT", "REJECT"):
        raise ActivationError("runtime_evidence_invalid", "decision is not closed", EXIT_RUNTIME)
    if (
        a2a.get("state") != "completed"
        or a2a.get("authoritative_content") != "data"
        or a2a.get("used_streaming_workflow") is not True
        or a2a.get("task_id") != artifact.get("a2a_task_id")
        or a2a.get("context_id") != artifact.get("a2a_context_id")
        or a2a.get("artifact_id") != artifact.get("artifact_id")
    ):
        raise ActivationError("runtime_evidence_invalid", "A2A proof does not bind the artifact", EXIT_RUNTIME)
    if (
        graphflow.get("analysis_rerun_on_approval_resume") is not False
        or graphflow.get("state_sha256") != artifact.get("graph_state_sha256")
        or approval.get("checkpoint_id") != approval.get("restored_checkpoint_id")
        or approval.get("initial_request_info_count") != 1
        or approval.get("resume_request_info_count") != 0
    ):
        raise ActivationError("runtime_evidence_invalid", "resume proof does not bind one analysis and checkpoint", EXIT_RUNTIME)
    packages = root.get("packages")
    if type(packages) is not dict or set(packages) != {"agent-framework-core", "agent-framework-a2a", "autogen-agentchat", "a2a-sdk"}:
        raise ActivationError("runtime_evidence_invalid", "runtime package identity is incomplete", EXIT_RUNTIME)
    return root


def _render_compose(root: Path, context: str, environment: Mapping[str, str], expectation: ComposeExpectation) -> bytes:
    result = _run(["docker", "--context", context, "compose", "--file", str(root / "compose.yaml"), "config", "--format", "json"], timeout=30, environment=environment)
    try:
        model = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ActivationError("compose_render_failed", "Compose did not return JSON", EXIT_PRECONDITION) from exc
    validate_compose_model(model, expectation)
    return _canonical_json(model)


def _compose_up(root: Path, context: str, environment: Mapping[str, str]) -> subprocess.CompletedProcess[str]:
    return _run(["docker", "--context", context, "compose", "--file", str(root / "compose.yaml"), "up", "--abort-on-container-exit", "--exit-code-from", "orchestrator"], timeout=180, environment=environment, check=False, capture=False)


def _compose_down(root: Path, context: str, environment: Mapping[str, str], *, remove_volumes: bool) -> None:
    command = ["docker", "--context", context, "compose", "--file", str(root / "compose.yaml"), "down", "--remove-orphans", "--timeout", "10"]
    if remove_volumes:
        command.append("--volumes")
    _run(command, timeout=60, environment=environment, check=False, capture=False)


def _compose_environment(expectation: ComposeExpectation) -> dict[str, str]:
    environment = _minimal_environment()
    environment.update({"SANDBOX_PROJECT": expectation.project, "SANDBOX_IMAGE": expectation.image, "SANDBOX_MODE": expectation.mode, "SANDBOX_SOURCE_REVISION": expectation.source_revision, "SANDBOX_RUN_ID": expectation.run_id, "SANDBOX_CASE_ID": expectation.case_id, "SANDBOX_DECISION": expectation.decision, "SANDBOX_NETWORK": expectation.network, "SANDBOX_STATE_VOLUME": expectation.state_volume, "SANDBOX_EVIDENCE_VOLUME": expectation.evidence_volume})
    return environment


def _minimal_environment() -> dict[str, str]:
    # Docker Desktop discovers CLI plugins from ProgramFiles on Windows. These
    # path identities are not Docker/Compose overrides and carry no credentials.
    allowed = (
        "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "TEMP", "TMP",
        "USERPROFILE", "HOME", "LOCALAPPDATA", "APPDATA", "PROGRAMDATA",
        "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432",
        "COMMONPROGRAMFILES", "COMMONPROGRAMFILES(X86)", "COMMONPROGRAMW6432",
    )
    return {name: os.environ[name] for name in allowed if name in os.environ}


def _run(command: Sequence[str], *, timeout: int, environment: Mapping[str, str] | None = None, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(list(command), check=False, text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE if capture else None, stderr=subprocess.PIPE if capture else None, timeout=timeout, env=None if environment is None else dict(environment))
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ActivationError("command_failed", f"required command failed: {command[0]}", EXIT_RUNTIME) from exc
    if check and result.returncode != 0:
        diagnostic = (result.stderr or "").strip().splitlines()
        suffix = diagnostic[-1][:300] if diagnostic else "no diagnostic"
        raise ActivationError("command_failed", f"{command[0]} exited {result.returncode}: {suffix}", EXIT_RUNTIME)
    return result


def _validated_revision(value: str) -> str:
    if _REVISION.fullmatch(value) is None:
        raise ActivationError("invalid_revision", "source revision must be 40 lowercase hexadecimal characters", EXIT_USAGE)
    return value


def _validated_context_name(value: str) -> str:
    if not value or len(value) > 128 or re.fullmatch(r"[A-Za-z0-9_.-]+", value) is None:
        raise ActivationError("invalid_context", "docker context name is malformed", EXIT_USAGE)
    return value


def _validated_run_id(value: str) -> str:
    if _RUN_ID.fullmatch(value) is None:
        raise ActivationError("invalid_run", "run ID is malformed", EXIT_USAGE)
    return value


def _validate_source_tree(repo: Path, sandbox: Path, revision: str) -> None:
    head = _run(["git", "-C", str(repo), "rev-parse", "HEAD"], timeout=20).stdout.strip()
    if head != revision:
        raise ActivationError("source_mismatch", "source revision does not match current HEAD", EXIT_PRECONDITION)
    status = _run(["git", "-C", str(repo), "status", "--porcelain=v1", "--untracked-files=all", "--", sandbox.relative_to(repo).as_posix()], timeout=20).stdout
    if status.strip():
        raise ActivationError("dirty_source", "sandbox has uncommitted or untracked bytes", EXIT_PRECONDITION)


def _validate_docker_context(context: str) -> None:
    result = _run(["docker", "context", "inspect", context], timeout=20, environment=_minimal_environment())
    try:
        contexts = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ActivationError("invalid_context", "docker context inspection was not JSON", EXIT_PRECONDITION) from exc
    if type(contexts) is not list or len(contexts) != 1 or contexts[0].get("Name") != context:
        raise ActivationError("invalid_context", "docker context identity mismatch", EXIT_PRECONDITION)


def _existing_evidence_root(value: str, repo: Path) -> Path:
    try:
        root = Path(value).resolve(strict=True)
    except OSError as exc:
        raise ActivationError("invalid_evidence_root", "evidence root must already exist", EXIT_USAGE) from exc
    if not root.is_dir():
        raise ActivationError("invalid_evidence_root", "evidence root is not a directory", EXIT_USAGE)
    if root == repo or repo in root.parents:
        raise ActivationError("invalid_evidence_root", "evidence root must be outside the source checkout", EXIT_PRECONDITION)
    return root


def _image_tag(revision: str) -> str:
    return f"autogen-a2a-sandbox:{revision}"


def _resolve_image(context: str, tag: str, revision: str) -> str:
    result = _run(["docker", "--context", context, "image", "inspect", "--format", "{{json .}}", tag], timeout=30, environment=_minimal_environment())
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ActivationError("image_missing", "image inspection was not JSON", EXIT_PRECONDITION) from exc
    image_id = value.get("Id")
    labels = value.get("Config", {}).get("Labels", {})
    if type(image_id) is not str or _IMAGE_ID.fullmatch(image_id) is None:
        raise ActivationError("image_mismatch", "built image lacks an immutable sha256 ID", EXIT_PRECONDITION)
    if labels.get("org.opencontainers.image.revision") != revision or labels.get("org.opencontainers.image.version") != "autogen-a2a-sandbox/v1":
        raise ActivationError("image_mismatch", "built image labels do not bind the requested source revision", EXIT_PRECONDITION)
    return image_id


def _run_identity(run_id: str, revision: str) -> RunIdentity:
    suffix = hashlib.sha256(f"autogen-a2a-sandbox/v1\0{revision}\0{run_id}".encode()).hexdigest()[:16]
    project = f"a2a-{suffix}"
    values = RunIdentity(project, f"{project}-state", f"{project}-evidence", f"{project}-network")
    if any(_RESOURCE.fullmatch(item) is None for item in (values.project, values.state_volume, values.evidence_volume, values.network)):
        raise ActivationError("invalid_resource", "derived Docker resource name is malformed", EXIT_PRECONDITION)
    return values


def _require_resources_absent(context: str, identity: RunIdentity) -> None:
    if _container_ids(context, identity.project) or _resource_exists(context, "network", identity.network) or _resource_exists(context, "volume", identity.state_volume) or _resource_exists(context, "volume", identity.evidence_volume):
        raise ActivationError("resource_conflict", "fresh run resources already exist", EXIT_PRECONDITION)


def _require_pending_resources(context: str, identity: RunIdentity) -> None:
    if _container_ids(context, identity.project) or _resource_exists(context, "network", identity.network):
        raise ActivationError("resource_conflict", "pending run has leftover containers or network", EXIT_PRECONDITION)
    if not _resource_exists(context, "volume", identity.state_volume) or not _resource_exists(context, "volume", identity.evidence_volume):
        raise ActivationError("resource_missing", "pending run volumes are missing", EXIT_PRECONDITION)


def _verify_pending_cleanup(context: str, identity: RunIdentity) -> None:
    _require_pending_resources(context, identity)


def _verify_full_cleanup(context: str, identity: RunIdentity) -> None:
    if _container_ids(context, identity.project) or any(_resource_exists(context, kind, name) for kind, name in (("network", identity.network), ("volume", identity.state_volume), ("volume", identity.evidence_volume))):
        raise ActivationError("cleanup_failed", "run-scoped Docker resources remain", EXIT_RUNTIME)


def _container_ids(context: str, project: str, service: str | None = None) -> tuple[str, ...]:
    command = ["docker", "--context", context, "ps", "--all", "--quiet", "--filter", f"label=com.docker.compose.project={project}"]
    if service:
        command.extend(["--filter", f"label=com.docker.compose.service={service}"])
    lines = _run(command, timeout=20, environment=_minimal_environment()).stdout.splitlines()
    return tuple(line.strip() for line in lines if line.strip())


def _orchestrator_container(context: str, project: str) -> str:
    ids = _container_ids(context, project, "orchestrator")
    if len(ids) != 1:
        raise ActivationError("runtime_evidence_missing", "expected exactly one stopped orchestrator container", EXIT_RUNTIME)
    return ids[0]


def _resource_exists(context: str, kind: str, name: str) -> bool:
    result = _run(["docker", "--context", context, kind, "inspect", name], timeout=20, environment=_minimal_environment(), check=False)
    return result.returncode == 0


def _copy_container_bytes(context: str, container_id: str, container_path: str) -> bytes:
    with tempfile.TemporaryDirectory() as temporary:
        target = Path(temporary) / "evidence"
        _run(["docker", "--context", context, "cp", f"{container_id}:{container_path}", str(target)], timeout=30, environment=_minimal_environment())
        return target.read_bytes()


def _copy_container_json(context: str, container_id: str, container_path: str) -> Mapping[str, object]:
    try:
        value = json.loads(_copy_container_bytes(context, container_id, container_path))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ActivationError("runtime_evidence_invalid", "runtime evidence is not JSON", EXIT_RUNTIME) from exc
    if type(value) is not dict:
        raise ActivationError("runtime_evidence_invalid", "runtime evidence is not an object", EXIT_RUNTIME)
    return value


def _handoff_path(root: Path, run_id: str) -> Path:
    return root / run_id / "resume-handoff.json"


def _load_json_file(path: Path, label: str) -> Mapping[str, object]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError, UnicodeError) as exc:
        raise ActivationError("invalid_handoff", f"{label} cannot be read", EXIT_PRECONDITION) from exc
    if type(value) is not dict:
        raise ActivationError("invalid_handoff", f"{label} is not an object", EXIT_PRECONDITION)
    return value


def _canonical_json(value: object) -> bytes:
    return (json.dumps(value, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")


def _emit_error(error_class: str, message: str) -> None:
    print(json.dumps({"error_class": error_class, "message": message}, sort_keys=True, separators=(",", ":")), file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
