#!/usr/bin/env python
"""Sole host entrypoint for the offline AutoGen/A2A sandbox."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime
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
_DAEMON_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_PYTHON_VERSION = re.compile(r"^3\.12\.\d+$")
_HOST_PYTHON_VERSION = re.compile(r"^3\.\d+\.\d+$")
_COMPOSE_VERSION = re.compile(r"^v?\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?$")
_PINNED_PACKAGES = {
    "a2a-sdk": "1.1.2",
    "agent-framework-a2a": "1.0.0b260821",
    "agent-framework-core": "1.16.0",
    "autogen-agentchat": "0.7.5",
}
_STAGE_MANIFEST_VERSION = "autogen-a2a-final-stage/v2"
_RECEIPT_VERSION = "autogen-a2a-host-receipt/v1"
_FINAL_CLAIM_AUTHENTICATION_FIELD = "final_claim_hmac_sha256"
_FINAL_CLAIM_DOMAIN = b"autogen-a2a-final-claim/v1\0"
_RECEIPT_FIELDS = frozenset({
    "receipt_version", "receipt_nonce", "handoff_sha256", "run_id",
    "source_revision", "case_id", "artifact_digest", "checkpoint_id",
    "daemon_id", "image_id", "project", "state_volume", "evidence_volume",
})
_STAGED_DATA_FILES = frozenset(
    {
        "artifact.json",
        "case-manifest.json",
        "case.json",
        "compose-model.json",
        "decision.json",
        "environment.json",
        "graphflow-state.json",
        "graphflow-checkpoint.json",
        "runtime-final.json",
    }
)
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
        "daemon_id",
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
    _validate_mounts(name, service.get("volumes"), expectation)
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


def _validate_mounts(
    name: str, value: object, expectation: ComposeExpectation
) -> None:
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
        read_only = mount.get("read_only", False)
        expected_read_only = (
            name == "worker" and source == "state" and expectation.mode == "resume"
        )
        if read_only is not expected_read_only:
            label = "read-only" if expected_read_only else "writable"
            _model_error(label, f"{name} state mount mode does not match {expectation.mode}")
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
    daemon_id: str,
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
        "daemon_id": daemon_id,
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


def _private_receipt_root() -> Path:
    """Return a per-user state directory without trusting process path variables."""

    if os.name == "nt":
        import ctypes

        buffer = ctypes.create_unicode_buffer(32768)
        result = ctypes.windll.shell32.SHGetFolderPathW(  # type: ignore[attr-defined]
            None, 0x001C, None, 0, buffer
        )
        if result != 0 or not buffer.value:
            raise ActivationError(
                "receipt_unavailable", "cannot resolve the private host state directory", EXIT_PRECONDITION
            )
        base = Path(buffer.value)
    else:
        import pwd

        base = Path(pwd.getpwuid(os.getuid()).pw_dir) / ".local" / "state"
    return base / "autogen-a2a-sandbox" / "receipts"


def _receipt_path(handoff: Mapping[str, object]) -> Path:
    key = "\0".join(
        str(handoff.get(field, ""))
        for field in ("source_revision", "run_id", "project")
    )
    return _private_receipt_root() / f"{hashlib.sha256(key.encode()).hexdigest()}.json"


def _create_or_load_receipt(handoff: Mapping[str, object]) -> Mapping[str, object]:
    root = _private_receipt_root()
    root.mkdir(parents=True, mode=0o700, exist_ok=True)
    _require_safe_directory(root, private=True)
    path = _receipt_path(handoff)
    if path.exists():
        return _load_trusted_receipt(handoff)
    receipt = {
        "receipt_version": _RECEIPT_VERSION,
        "receipt_nonce": secrets.token_hex(32),
        "handoff_sha256": hashlib.sha256(_canonical_json(handoff)).hexdigest(),
        **{
            field: handoff[field]
            for field in (
                "run_id", "source_revision", "case_id", "artifact_digest",
                "checkpoint_id", "daemon_id", "image_id", "project",
                "state_volume", "evidence_volume",
            )
        },
    }
    data = _canonical_json(receipt)
    try:
        _atomic_create_file(path, data, mode=0o600)
    except FileExistsError:
        return _load_trusted_receipt(handoff)
    return _validate_receipt(receipt, handoff)


def _load_trusted_receipt(handoff: Mapping[str, object]) -> Mapping[str, object]:
    path = _receipt_path(handoff)
    try:
        data = _read_regular_file(path, "host receipt")
        receipt = json.loads(data)
    except ActivationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ActivationError(
            "invalid_receipt", "trusted host receipt is missing or unsafe", EXIT_PRECONDITION
        ) from exc
    if data != _canonical_json(receipt):
        raise ActivationError("invalid_receipt", "trusted host receipt is not canonical", EXIT_PRECONDITION)
    return _validate_receipt(receipt, handoff)


def _validate_receipt(
    receipt: object, handoff: Mapping[str, object]
) -> Mapping[str, object]:
    if type(receipt) is not dict or set(receipt) != _RECEIPT_FIELDS:
        raise ActivationError("invalid_receipt", "trusted host receipt is not closed", EXIT_PRECONDITION)
    expected = {
        "receipt_version": _RECEIPT_VERSION,
        "handoff_sha256": hashlib.sha256(_canonical_json(handoff)).hexdigest(),
        **{
            field: handoff[field]
            for field in (
                "run_id", "source_revision", "case_id", "artifact_digest",
                "checkpoint_id", "daemon_id", "image_id", "project",
                "state_volume", "evidence_volume",
            )
        },
    }
    if any(receipt.get(field) != value for field, value in expected.items()):
        raise ActivationError("invalid_receipt", "trusted host receipt binding mismatch", EXIT_PRECONDITION)
    nonce = receipt.get("receipt_nonce")
    if type(nonce) is not str or re.fullmatch(r"[0-9a-f]{64}", nonce) is None:
        raise ActivationError("invalid_receipt", "trusted host receipt nonce is malformed", EXIT_PRECONDITION)
    return receipt


def _final_claim_hmac(
    claim: Mapping[str, object], receipt: Mapping[str, object]
) -> str:
    """Authenticate one closed final-claim preimage with the private receipt secret."""

    nonce = receipt.get("receipt_nonce")
    if type(nonce) is not str or re.fullmatch(r"[0-9a-f]{64}", nonce) is None:
        raise ActivationError(
            "invalid_receipt", "trusted host receipt nonce is malformed", EXIT_PRECONDITION
        )
    return hmac.new(
        bytes.fromhex(nonce),
        _FINAL_CLAIM_DOMAIN + _canonical_json(claim),
        hashlib.sha256,
    ).hexdigest()


def _require_safe_directory(path: Path, *, private: bool = False) -> None:
    try:
        details = os.lstat(path)
    except OSError as exc:
        raise ActivationError("unsafe_path", "required directory is unavailable", EXIT_PRECONDITION) from exc
    if not stat.S_ISDIR(details.st_mode) or _is_link_or_reparse(details):
        raise ActivationError("unsafe_path", "directory is a link or reparse substitution", EXIT_PRECONDITION)
    if private and os.name != "nt":
        if details.st_uid != os.getuid() or stat.S_IMODE(details.st_mode) & 0o077:
            raise ActivationError("unsafe_path", "private receipt directory permissions are unsafe", EXIT_PRECONDITION)


def _is_link_or_reparse(details: os.stat_result) -> bool:
    return stat.S_ISLNK(details.st_mode) or bool(
        getattr(details, "st_file_attributes", 0) & 0x400
    )


def _read_regular_file(path: Path, label: str) -> bytes:
    try:
        before = os.lstat(path)
        if (
            not stat.S_ISREG(before.st_mode)
            or _is_link_or_reparse(before)
            or before.st_nlink != 1
            or before.st_size > 4 * 1024 * 1024
        ):
            raise ActivationError(
                "unsafe_path",
                f"{label} is a link or non-regular file",
                EXIT_PRECONDITION,
            )
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        try:
            opened = os.fstat(descriptor)
            if (
                not stat.S_ISREG(opened.st_mode)
                or _is_link_or_reparse(opened)
                or opened.st_nlink != 1
                or (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino)
                or opened.st_size > 4 * 1024 * 1024
            ):
                raise ActivationError("unsafe_path", f"{label} is a link or non-regular file", EXIT_PRECONDITION)
            with os.fdopen(descriptor, "rb", closefd=False) as stream:
                return stream.read()
        finally:
            os.close(descriptor)
    except ActivationError:
        raise
    except OSError as exc:
        raise ActivationError("unsafe_path", f"{label} cannot be read safely", EXIT_PRECONDITION) from exc


def _atomic_create_file(path: Path, data: bytes, *, mode: int = 0o600) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, mode)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(descriptor)
    _sync_directory(path.parent)


def _sync_directory(path: Path) -> None:
    """Persist directory metadata where the host exposes a directory fsync API."""

    if os.name == "nt":
        # Windows stdlib cannot open a directory for fsync. Individual files
        # are flushed and final publication uses MoveFileExW WRITE_THROUGH.
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish_file_once(path: Path, data: bytes) -> None:
    """Atomically create evidence, accepting only an exact idempotent replay."""

    path.parent.mkdir(parents=True, exist_ok=True)
    _require_safe_directory(path.parent)
    if os.path.lexists(path):
        if _read_regular_file(path, path.name) == data:
            return
        raise ActivationError("evidence_conflict", f"refusing to overwrite changed evidence: {path.name}", EXIT_PRECONDITION)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if _read_regular_file(path, path.name) == data:
                return
            raise ActivationError("evidence_conflict", f"refusing to overwrite changed evidence: {path.name}", EXIT_PRECONDITION)
        _sync_directory(path.parent)
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
        daemon_id = _validate_docker_context(context)
        if args.command == "build":
            return _build(root, context, revision, daemon_id)
        evidence_root = _existing_evidence_root(args.evidence_root, repo)
        run_id = _validated_run_id(args.run_id)
        if args.command == "fresh":
            return _fresh(
                root, context, revision, run_id, args.case, evidence_root, daemon_id
            )
        return _resume(
            root, context, revision, run_id, evidence_root, args.decision, daemon_id
        )
    except ActivationError as exc:
        _emit_error(exc.error_class, str(exc))
        return exc.exit_code
    except KeyboardInterrupt:
        _emit_error("interrupted", "activation interrupted before success")
        return 130
    except Exception as exc:  # process boundary: bounded diagnostic, never false success
        _emit_error("activation_failure", f"activation failed ({type(exc).__name__})")
        return EXIT_RUNTIME


def _build(root: Path, context: str, revision: str, daemon_id: str) -> int:
    tag = _image_tag(revision)
    command = [
        "docker", "--context", context, "build", "--no-cache", "--platform", "linux/amd64",
        "--build-arg", f"SANDBOX_SOURCE_REVISION={revision}", "--file", str(root / "Dockerfile"),
        "--tag", tag, str(root),
    ]
    _run(command, timeout=900, capture=False)
    image_id = _resolve_image(context, tag, revision)
    print(json.dumps({"daemon_id": daemon_id, "event": "image_built", "image_id": image_id, "source_revision": revision, "tag": tag}, sort_keys=True, separators=(",", ":")))
    return 0


def _fresh(root: Path, context: str, revision: str, run_id: str, case_id: str, evidence_root: Path, daemon_id: str) -> int:
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
            host_handoff.update({"daemon_id": daemon_id, "image_id": image_id, "project": identity.project, "state_volume": identity.state_volume, "evidence_volume": identity.evidence_volume})
            host_handoff = validate_resume_handoff(host_handoff, source_revision=revision, run_id=run_id, image_id=image_id, project=identity.project, state_volume=identity.state_volume, evidence_volume=identity.evidence_volume, daemon_id=daemon_id)
            handoff_bytes = _canonical_json(host_handoff)
            _create_or_load_receipt(host_handoff)
            authentic_pending = True
            publish_file_once(_handoff_path(evidence_root, run_id), handoff_bytes)
        elif exit_code == EXIT_TERMINAL:
            terminal = _copy_container_bytes(context, container_id, "/evidence/runtime-terminal.json")
            case_object = _decode_json_object_bytes(
                (root / "cases" / f"{case_id}.json").read_bytes(), "case"
            )
            _validate_runtime_terminal(
                terminal,
                run_id=run_id,
                source_revision=revision,
                case_id=case_id,
                case_object=case_object,
            )
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


def _resume(root: Path, context: str, revision: str, run_id: str, evidence_root: Path, decision: str, daemon_id: str) -> int:
    image_id = _resolve_image(context, _image_tag(revision), revision)
    identity = _run_identity(run_id, revision)
    handoff = _load_json_file(_handoff_path(evidence_root, run_id), "resume handoff")
    handoff = validate_resume_handoff(handoff, source_revision=revision, run_id=run_id, image_id=image_id, project=identity.project, state_volume=identity.state_volume, evidence_volume=identity.evidence_volume, daemon_id=daemon_id)
    receipt = _load_trusted_receipt(handoff)
    case_id = str(handoff["case_id"])
    final_target = evidence_root / run_id / "final-bundle"
    expectation = ComposeExpectation(image_id, identity.project, identity.state_volume, identity.evidence_volume, identity.network, "resume", revision, run_id, case_id, decision)
    compose_env = _compose_environment(expectation)
    model_bytes = _render_compose(root, context, compose_env, expectation)
    if os.path.lexists(final_target):
        _verify_full_cleanup(context, identity)
        final_claim = _validate_final_bundle(
            final_target, run_id=run_id, source_revision=revision, case_id=case_id,
            image_id=image_id, daemon_id=daemon_id, requested_decision=decision,
            handoff=handoff, receipt=receipt,
        )
        print(json.dumps({"event": "decision_published_replay", "bundle": str(final_target), "final_claim_hmac_sha256": final_claim[_FINAL_CLAIM_AUTHENTICATION_FIELD], "run_id": run_id}, sort_keys=True, separators=(",", ":")))
        return 0
    durable_stage = _pending_stage_path(final_target)
    if (durable_stage / "stage-manifest.json").is_file():
        validate_staged_bundle(
            durable_stage,
            run_id=run_id,
            source_revision=revision,
            case_id=case_id,
            image_id=image_id,
            daemon_id=daemon_id,
            requested_decision=decision,
            handoff=handoff,
            receipt=receipt,
        )
        _compose_down(root, context, compose_env, remove_volumes=True)
        _verify_full_cleanup(context, identity)
        final_claim = _finalize_bundle(
            durable_stage,
            final_target,
            run_id=run_id,
            revision=revision,
            case_id=case_id,
            image_id=image_id,
            daemon_id=daemon_id,
            requested_decision=decision,
            handoff=handoff,
            receipt=receipt,
        )
        print(json.dumps({"event": "decision_published_from_stage", "bundle": str(final_target), "final_claim_hmac_sha256": final_claim[_FINAL_CLAIM_AUTHENTICATION_FIELD], "run_id": run_id}, sort_keys=True, separators=(",", ":")))
        return 0
    _require_pending_resources(context, identity)
    staged: tuple[Path, Path] | None = None
    failure: BaseException | None = None
    try:
        result = _compose_up(root, context, compose_env)
        if result.returncode != 0:
            raise ActivationError("resume_failed", f"resume orchestrator exited {result.returncode}", EXIT_RUNTIME)
        container_id = _orchestrator_container(context, identity.project)
        runtime_final = _copy_container_bytes(context, container_id, "/evidence/runtime-final.json")
        graph_state = _copy_container_bytes(context, container_id, f"/state/{run_id}.graphflow-state.json")
        graph_checkpoint = _copy_container_bytes(context, container_id, f"/state/{run_id}.graphflow-checkpoint.json")
        case_object = _decode_json_object_bytes(
            (root / "cases" / f"{case_id}.json").read_bytes(), "case"
        )
        runtime_object = _validate_runtime_final(
            runtime_final,
            run_id=run_id,
            source_revision=revision,
            case_id=case_id,
            case_object=case_object,
            requested_decision=decision,
            handoff=handoff,
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
            graph_checkpoint,
            daemon_id,
            handoff,
            receipt,
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
        final_claim = _finalize_bundle(
            *staged,
            run_id=run_id,
            revision=revision,
            case_id=case_id,
            image_id=image_id,
            daemon_id=daemon_id,
            requested_decision=decision,
            handoff=handoff,
            receipt=receipt,
        )
    except BaseException:
        raise
    print(json.dumps({"event": "decision_published", "bundle": str(evidence_root / run_id / "final-bundle"), "final_claim_hmac_sha256": final_claim[_FINAL_CLAIM_AUTHENTICATION_FIELD], "run_id": run_id}, sort_keys=True, separators=(",", ":")))
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
    graph_checkpoint: bytes,
    daemon_id: str,
    handoff: Mapping[str, object],
    receipt: Mapping[str, object],
) -> tuple[Path, Path]:
    target.parent.mkdir(parents=True, exist_ok=True)
    _require_safe_directory(target.parent)
    stage = _pending_stage_path(target)
    stage.mkdir(parents=False, exist_ok=True)
    _require_safe_directory(stage)
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
    _validate_graphflow_checkpoint(
        graph_checkpoint, runtime_object=runtime_object, handoff=handoff
    )
    docker_version = _run(["docker", "--context", context, "version", "--format", "{{json .Server}}"], timeout=20).stdout
    compose_version = _run(["docker", "--context", context, "compose", "version", "--short"], timeout=20).stdout.strip()
    docker_server_raw = json.loads(docker_version)
    if type(docker_server_raw) is not dict:
        raise ActivationError("runtime_evidence_invalid", "Docker server identity is malformed", EXIT_RUNTIME)
    docker_server = {
        field: docker_server_raw.get(field)
        for field in ("Version", "ApiVersion", "Os", "Arch")
    }
    identity_object = {"daemon_id": daemon_id, "evidence_version": "autogen-a2a-environment/v1", "source_revision": revision, "run_id": runtime_object["run_id"], "case_id": case_id, "image_id": image_id, "docker_context": context, "docker_server": docker_server, "docker_compose": compose_version, "host_python": sys.version.split()[0], "runtime_python": runtime_object["python"], "packages": runtime_object["packages"]}
    values = {
        "case.json": (root / "cases" / f"{case_id}.json").read_bytes(),
        "case-manifest.json": (root / "cases" / "manifest.json").read_bytes(),
        "compose-model.json": model_bytes,
        "runtime-final.json": runtime_final,
        "graphflow-state.json": graph_state,
        "graphflow-checkpoint.json": graph_checkpoint,
        "artifact.json": _canonical_json(runtime_object["artifact"]),
        "decision.json": _canonical_json(runtime_object["decision"]),
        "environment.json": _canonical_json(identity_object),
    }
    for name, value in values.items():
        publish_file_once(stage / name, value)
    claim = {
        "case_id": case_id,
        "artifact_digest": handoff["artifact_digest"],
        "checkpoint_id": handoff["checkpoint_id"],
        "daemon_id": daemon_id,
        "handoff_sha256": hashlib.sha256(_canonical_json(handoff)).hexdigest(),
        "files": {
            name: hashlib.sha256(value).hexdigest()
            for name, value in sorted(values.items())
        },
        "image_id": image_id,
        "run_id": runtime_object["run_id"],
        "source_revision": revision,
        "receipt_sha256": hashlib.sha256(_canonical_json(receipt)).hexdigest(),
        "stage_version": _STAGE_MANIFEST_VERSION,
    }
    manifest = {
        **claim,
        _FINAL_CLAIM_AUTHENTICATION_FIELD: _final_claim_hmac(claim, receipt),
    }
    publish_file_once(stage / "stage-manifest.json", _canonical_json(manifest))
    validate_staged_bundle(
        stage,
        run_id=runtime_object["run_id"],
        source_revision=revision,
        case_id=case_id,
        image_id=image_id,
        daemon_id=daemon_id,
        requested_decision=runtime_object["decision"]["decision"],
        handoff=handoff,
        receipt=receipt,
    )
    return stage, target


def _pending_stage_path(target: Path) -> Path:
    return target.parent / ".final-bundle.pending"


def _snapshot_stage_files(
    stage: Path, *, require_final: bool
) -> Mapping[str, bytes]:
    _require_safe_directory(stage)
    allowed = {
        *_STAGED_DATA_FILES,
        "stage-manifest.json",
        "verification.json",
        "checksums.json",
    }
    required = {*_STAGED_DATA_FILES, "stage-manifest.json"}
    if require_final:
        required = allowed
    actual_names = {path.name for path in stage.iterdir()}
    invalid_names = (
        actual_names != required
        if require_final
        else not (required <= actual_names <= allowed)
    )
    if invalid_names:
        raise ActivationError(
            "invalid_stage",
            "final bundle file set is not exact"
            if require_final
            else "pending final stage contains unknown or missing files",
            EXIT_PRECONDITION,
        )
    return {
        name: _read_regular_file(stage / name, f"staged {name}")
        for name in sorted(actual_names)
    }


def validate_staged_bundle(
    stage: Path,
    *,
    run_id: str,
    source_revision: str,
    case_id: str,
    image_id: str,
    daemon_id: str,
    requested_decision: str,
    handoff: Mapping[str, object],
    receipt: Mapping[str, object],
    require_final: bool = False,
) -> Mapping[str, object]:
    receipt = _validate_receipt(receipt, handoff)
    snapshot = _snapshot_stage_files(stage, require_final=require_final)
    try:
        manifest_bytes = snapshot["stage-manifest.json"]
        manifest = json.loads(manifest_bytes)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ActivationError("invalid_stage", "pending final stage is unreadable", EXIT_PRECONDITION) from exc
    fields = {"stage_version", "run_id", "source_revision", "case_id", "image_id", "daemon_id", "artifact_digest", "checkpoint_id", "handoff_sha256", "receipt_sha256", "files", _FINAL_CLAIM_AUTHENTICATION_FIELD}
    if type(manifest) is not dict or set(manifest) != fields:
        raise ActivationError("invalid_stage", "pending final stage manifest is not closed", EXIT_PRECONDITION)
    if manifest_bytes != _canonical_json(manifest):
        raise ActivationError("invalid_stage", "pending final stage manifest is not canonical", EXIT_PRECONDITION)
    expected = {
        "stage_version": _STAGE_MANIFEST_VERSION,
        "run_id": run_id,
        "source_revision": source_revision,
        "case_id": case_id,
        "image_id": image_id,
        "daemon_id": daemon_id,
        "artifact_digest": handoff.get("artifact_digest"),
        "checkpoint_id": handoff.get("checkpoint_id"),
        "handoff_sha256": hashlib.sha256(_canonical_json(handoff)).hexdigest(),
        "receipt_sha256": hashlib.sha256(_canonical_json(receipt)).hexdigest(),
    }
    for field, value in expected.items():
        if manifest.get(field) != value:
            raise ActivationError("invalid_stage", f"pending final stage {field} mismatch", EXIT_PRECONDITION)
    authentication = manifest.get(_FINAL_CLAIM_AUTHENTICATION_FIELD)
    claim = {
        field: value
        for field, value in manifest.items()
        if field != _FINAL_CLAIM_AUTHENTICATION_FIELD
    }
    if (
        type(authentication) is not str
        or re.fullmatch(r"[0-9a-f]{64}", authentication) is None
        or not hmac.compare_digest(authentication, _final_claim_hmac(claim, receipt))
    ):
        raise ActivationError(
            "invalid_stage",
            "pending final stage authentication mismatch",
            EXIT_PRECONDITION,
        )
    digests = manifest.get("files")
    if type(digests) is not dict or set(digests) != _STAGED_DATA_FILES:
        raise ActivationError("invalid_stage", "pending final stage file set mismatch", EXIT_PRECONDITION)
    for name, expected_digest in digests.items():
        if type(expected_digest) is not str or hashlib.sha256(snapshot[name]).hexdigest() != expected_digest:
            raise ActivationError("invalid_stage", f"pending final stage {name} digest mismatch", EXIT_PRECONDITION)
    _validate_staged_contents(
        snapshot,
        run_id=run_id,
        source_revision=source_revision,
        case_id=case_id,
        image_id=image_id,
        daemon_id=daemon_id,
        requested_decision=requested_decision,
        handoff=handoff,
        receipt=receipt,
    )
    if _snapshot_stage_files(stage, require_final=require_final) != snapshot:
        raise ActivationError(
            "invalid_stage",
            "pending final stage changed during validation",
            EXIT_PRECONDITION,
        )
    return manifest


def _validate_staged_contents(
    snapshot: Mapping[str, bytes],
    *,
    run_id: str,
    source_revision: str,
    case_id: str,
    image_id: str,
    daemon_id: str,
    requested_decision: str,
    handoff: Mapping[str, object],
    receipt: Mapping[str, object],
) -> None:
    _validate_receipt(receipt, handoff)
    contracts, _runtime_validation = _validation_modules()
    case_bytes = snapshot["case.json"]
    case_object = _decode_json_object_bytes(case_bytes, "staged case")
    manifest_object = _decode_json_object_bytes(
        snapshot["case-manifest.json"], "staged case manifest"
    )
    if set(manifest_object) != {"manifest_version", "cases"} or manifest_object.get(
        "manifest_version"
    ) != "canary-evidence-case-manifest/v1":
        raise ActivationError("invalid_stage", "staged case manifest is not closed", EXIT_PRECONDITION)
    entries = manifest_object.get("cases")
    if type(entries) is not list or len(entries) != len(_CASE_IDS):
        raise ActivationError("invalid_stage", "staged case manifest is incomplete", EXIT_PRECONDITION)
    ordered_ids = (
        "mission-healthy-001", "confirmed-regression-001",
        "stale-evidence-reconciled-001", "unresolved-contradiction-001",
        "slow-analysis-cancel-001", "checkpoint-resume-001",
    )
    selected_entry = None
    for expected_id, entry in zip(ordered_ids, entries):
        if (
            type(entry) is not dict
            or set(entry) != {"case_id", "file", "sha256"}
            or entry.get("case_id") != expected_id
            or entry.get("file") != f"{expected_id}.json"
            or type(entry.get("sha256")) is not str
            or re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]) is None
        ):
            raise ActivationError("invalid_stage", "staged case manifest entry is invalid", EXIT_PRECONDITION)
        if expected_id == case_id:
            selected_entry = entry
    if selected_entry is None or hashlib.sha256(case_bytes).hexdigest() != selected_entry["sha256"]:
        raise ActivationError("invalid_stage", "staged case bytes do not match the manifest", EXIT_PRECONDITION)
    try:
        case = contracts.validate_case(case_object)
    except contracts.ContractViolation as exc:
        raise ActivationError("invalid_stage", "staged case contract is invalid", EXIT_PRECONDITION) from exc
    if case.case_id != case_id:
        raise ActivationError("invalid_stage", "staged case identity mismatch", EXIT_PRECONDITION)

    runtime_bytes = snapshot["runtime-final.json"]
    runtime_object = _validate_runtime_final(
        runtime_bytes,
        run_id=run_id,
        source_revision=source_revision,
        case_id=case_id,
        case_object=case_object,
        requested_decision=requested_decision,
        handoff=handoff,
    )
    for name, field in (("artifact.json", "artifact"), ("decision.json", "decision")):
        if snapshot[name] != _canonical_json(runtime_object[field]):
            raise ActivationError("invalid_stage", f"staged {name} differs from runtime evidence", EXIT_PRECONDITION)
    graph_bytes = snapshot["graphflow-state.json"]
    graph_object = _decode_json_object_bytes(graph_bytes, "staged GraphFlow state")
    if graph_bytes != contracts.canonical_json_bytes(graph_object):
        raise ActivationError(
            "invalid_stage", "staged GraphFlow state is not canonical", EXIT_PRECONDITION
        )
    if graph_object != runtime_object["graphflow"]["terminal_state"]:
        raise ActivationError("invalid_stage", "staged GraphFlow state differs from runtime evidence", EXIT_PRECONDITION)
    _validate_graphflow_checkpoint(
        snapshot["graphflow-checkpoint.json"],
        runtime_object=runtime_object,
        handoff=handoff,
    )

    environment = _load_canonical_json_bytes(
        snapshot["environment.json"], "staged environment"
    )
    environment_fields = {
        "evidence_version", "source_revision", "run_id", "case_id", "image_id",
        "daemon_id", "docker_context", "docker_server", "docker_compose",
        "host_python", "runtime_python", "packages",
    }
    expected_environment = {
        "evidence_version": "autogen-a2a-environment/v1",
        "source_revision": source_revision,
        "run_id": run_id,
        "case_id": case_id,
        "image_id": image_id,
        "daemon_id": daemon_id,
        "docker_context": "desktop-linux",
        "runtime_python": runtime_object["python"],
        "packages": _PINNED_PACKAGES,
    }
    if set(environment) != environment_fields or any(
        environment.get(field) != expected for field, expected in expected_environment.items()
    ):
        raise ActivationError("invalid_stage", "staged environment binding mismatch", EXIT_PRECONDITION)
    docker_server = environment.get("docker_server")
    if (
        type(docker_server) is not dict
        or set(docker_server) != {"Version", "ApiVersion", "Os", "Arch"}
        or not all(type(value) is str and value for value in docker_server.values())
        or docker_server.get("Os") != "linux"
        or type(environment.get("docker_compose")) is not str
        or _COMPOSE_VERSION.fullmatch(environment["docker_compose"]) is None
        or type(environment.get("host_python")) is not str
        or _HOST_PYTHON_VERSION.fullmatch(environment["host_python"]) is None
    ):
        raise ActivationError("invalid_stage", "staged Docker or Python identity is malformed", EXIT_PRECONDITION)

    compose_model = _load_canonical_json_bytes(
        snapshot["compose-model.json"], "staged Compose model"
    )
    identity = _run_identity(run_id, source_revision)
    validate_compose_model(
        compose_model,
        ComposeExpectation(
            image_id, identity.project, identity.state_volume, identity.evidence_volume,
            identity.network, "resume", source_revision, run_id, case_id,
            requested_decision,
        ),
    )

    if "verification.json" in snapshot:
        verification = _load_canonical_json_bytes(
            snapshot["verification.json"], "staged verification"
        )
        expected_verification = {
            "daemon_id": daemon_id,
            "verification_version": "autogen-a2a-verification/v1",
            "result": "PASS",
            "run_id": run_id,
            "source_revision": source_revision,
            "image_id": image_id,
            "release_effect_executed": False,
            "resource_cleanup_verified": True,
        }
        if verification != expected_verification:
            raise ActivationError("invalid_stage", "staged verification is invalid", EXIT_PRECONDITION)
    if "checksums.json" in snapshot:
        checksums = _load_canonical_json_bytes(snapshot["checksums.json"], "staged checksums")
        expected_checksums = {
            name: hashlib.sha256(value).hexdigest()
            for name, value in sorted(snapshot.items())
            if name != "checksums.json"
        }
        if checksums != {
            "checksums_version": "autogen-a2a-checksums/v1",
            "files": expected_checksums,
        }:
            raise ActivationError("invalid_stage", "staged checksums are invalid", EXIT_PRECONDITION)


def _validate_graphflow_checkpoint(
    value: bytes,
    *,
    runtime_object: Mapping[str, object],
    handoff: Mapping[str, object],
) -> Mapping[str, object]:
    contracts, _runtime_validation = _validation_modules()
    try:
        checkpoint = json.loads(value)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ActivationError("runtime_evidence_invalid", "GraphFlow checkpoint is not JSON", EXIT_RUNTIME) from exc
    fields = {
        "checkpoint_version", "run_id", "source_revision", "case_id",
        "case_digest", "candidate_revision", "team_state",
    }
    if type(checkpoint) is not dict or set(checkpoint) != fields:
        raise ActivationError("runtime_evidence_invalid", "GraphFlow checkpoint is not closed", EXIT_RUNTIME)
    if value != contracts.canonical_json_bytes(checkpoint):
        raise ActivationError("runtime_evidence_invalid", "GraphFlow checkpoint is not canonical", EXIT_RUNTIME)
    expected = {
        "checkpoint_version": "canary-analysis-checkpoint/v1",
        **{
            field: runtime_object[field]
            for field in (
                "run_id", "source_revision", "case_id", "case_digest",
                "candidate_revision",
            )
        },
    }
    if any(checkpoint.get(field) != expected_value for field, expected_value in expected.items()):
        raise ActivationError("runtime_evidence_invalid", "GraphFlow checkpoint lineage mismatch", EXIT_RUNTIME)
    if type(checkpoint.get("team_state")) is not dict:
        raise ActivationError("runtime_evidence_invalid", "GraphFlow checkpoint team state is malformed", EXIT_RUNTIME)
    digest = contracts.canonical_sha256(checkpoint)
    graphflow = runtime_object.get("graphflow")
    artifact = runtime_object.get("artifact")
    approval = runtime_object.get("approval")
    if (
        type(graphflow) is not dict
        or type(artifact) is not dict
        or type(approval) is not dict
        or digest != graphflow.get("initial_checkpoint_sha256")
        or digest != graphflow.get("terminal_state", {}).get("initial_checkpoint_sha256")
        or handoff.get("artifact_digest") != artifact.get("artifact_digest")
        or handoff.get("checkpoint_id") != approval.get("checkpoint_id")
    ):
        raise ActivationError("runtime_evidence_invalid", "GraphFlow checkpoint or handoff binding mismatch", EXIT_RUNTIME)
    return checkpoint


def _finalize_bundle(
    stage: Path,
    target: Path,
    *,
    run_id: str,
    revision: str,
    case_id: str,
    image_id: str,
    daemon_id: str,
    requested_decision: str,
    handoff: Mapping[str, object],
    receipt: Mapping[str, object],
) -> Mapping[str, object]:
    validate_staged_bundle(
        stage,
        run_id=run_id,
        source_revision=revision,
        case_id=case_id,
        image_id=image_id,
        daemon_id=daemon_id,
        requested_decision=requested_decision,
        handoff=handoff,
        receipt=receipt,
    )
    if os.path.lexists(target):
        raise ActivationError("evidence_conflict", "refusing to overwrite an existing final bundle", EXIT_PRECONDITION)
    verification = {"daemon_id": daemon_id, "verification_version": "autogen-a2a-verification/v1", "result": "PASS", "run_id": run_id, "source_revision": revision, "image_id": image_id, "release_effect_executed": False, "resource_cleanup_verified": True}
    publish_file_once(stage / "verification.json", _canonical_json(verification))
    checksums = {path.name: hashlib.sha256(_read_regular_file(path, f"staged {path.name}")).hexdigest() for path in sorted(stage.iterdir()) if path.name != "checksums.json"}
    publish_file_once(stage / "checksums.json", _canonical_json({"checksums_version": "autogen-a2a-checksums/v1", "files": checksums}))
    _sync_directory(stage)
    _durable_publish_directory(stage, target)
    return _validate_final_bundle(
        target,
        run_id=run_id,
        source_revision=revision,
        case_id=case_id,
        image_id=image_id,
        daemon_id=daemon_id,
        requested_decision=requested_decision,
        handoff=handoff,
        receipt=receipt,
    )


def _durable_publish_directory(stage: Path, target: Path) -> None:
    """Atomically publish the final directory with the strongest host flush available."""

    _require_safe_directory(stage)
    if os.path.lexists(target):
        raise ActivationError("evidence_conflict", "final evidence target already exists", EXIT_PRECONDITION)
    if os.name == "nt":
        import ctypes

        if not ctypes.windll.kernel32.MoveFileExW(  # type: ignore[attr-defined]
            str(stage), str(target), 0x00000008
        ):
            raise ctypes.WinError()
    else:
        os.rename(stage, target)
        _sync_directory(target.parent)
    _require_safe_directory(target)


def _validate_final_bundle(
    target: Path,
    *,
    run_id: str,
    source_revision: str,
    case_id: str,
    image_id: str,
    daemon_id: str,
    requested_decision: str,
    handoff: Mapping[str, object],
    receipt: Mapping[str, object],
) -> Mapping[str, object]:
    return validate_staged_bundle(
        target, run_id=run_id, source_revision=source_revision, case_id=case_id,
        image_id=image_id, daemon_id=daemon_id,
        requested_decision=requested_decision, handoff=handoff, receipt=receipt,
        require_final=True,
    )


def _validate_runtime_terminal(
    value: bytes,
    *,
    run_id: str,
    source_revision: str,
    case_id: str,
    case_object: object,
) -> Mapping[str, object]:
    contracts, runtime_validation = _validation_modules()
    root = _load_canonical_json_bytes(value, "terminal runtime evidence")
    fields = {
        "runtime_evidence_version", "status", "run_id", "source_revision",
        "case_id", "case_digest", "candidate_revision", "python", "packages",
        "analysis_invocations", "remote_request_info_count",
        "approval_request_info_count", "artifact", "a2a", "graphflow",
        "release_effect_executed",
    }
    if set(root) != fields:
        raise ActivationError("runtime_evidence_invalid", "terminal runtime evidence is not closed", EXIT_RUNTIME)
    try:
        case = contracts.validate_case(case_object)
    except contracts.ContractViolation as exc:
        raise ActivationError("runtime_evidence_invalid", "terminal case is invalid", EXIT_RUNTIME) from exc
    expected_state = case.expected.a2a_state
    expected_remote_requests = {"input-required": 1, "canceled": 0, "failed": 0}
    expected = {
        "runtime_evidence_version": "autogen-a2a-runtime-evidence/v1",
        "status": expected_state,
        "run_id": run_id,
        "source_revision": source_revision,
        "case_id": case_id,
        "case_digest": contracts.canonical_sha256(case),
        "candidate_revision": case.candidate.candidate_revision,
        "packages": _PINNED_PACKAGES,
        "analysis_invocations": 1,
        "remote_request_info_count": expected_remote_requests.get(expected_state),
        "approval_request_info_count": 0,
        "artifact": None,
        "release_effect_executed": False,
    }
    if expected_state not in expected_remote_requests or any(
        root.get(field) != expected_value for field, expected_value in expected.items()
    ):
        raise ActivationError("runtime_evidence_invalid", "terminal runtime binding mismatch", EXIT_RUNTIME)
    if type(root.get("python")) is not str or _PYTHON_VERSION.fullmatch(root["python"]) is None:
        raise ActivationError("runtime_evidence_invalid", "terminal Python identity is malformed", EXIT_RUNTIME)
    a2a = root.get("a2a")
    if type(a2a) is not dict or set(a2a) != {
        "state", "task_id", "context_id", "artifact_id", "transport_mode",
        "used_streaming_workflow", "event_timeline", "recovery",
    }:
        raise ActivationError("runtime_evidence_invalid", "terminal A2A proof is not closed", EXIT_RUNTIME)
    if (
        a2a.get("state") != expected_state
        or type(a2a.get("task_id")) is not str
        or not a2a["task_id"]
        or type(a2a.get("context_id")) is not str
        or not a2a["context_id"]
        or a2a.get("artifact_id") is not None
    ):
        raise ActivationError("runtime_evidence_invalid", "terminal A2A binding mismatch", EXIT_RUNTIME)
    expected_transport = (
        ("raw-a2a-cancel", False)
        if expected_state == "canceled"
        else ("maf-workflow", True)
    )
    if (
        a2a.get("transport_mode"), a2a.get("used_streaming_workflow")
    ) != expected_transport:
        raise ActivationError("runtime_evidence_invalid", "terminal A2A transport mode mismatch", EXIT_RUNTIME)
    try:
        runtime_validation.validate_persisted_event_timeline(
            a2a.get("event_timeline"),
            task_id=a2a["task_id"],
            context_id=a2a["context_id"],
            terminal_state=expected_state,
            artifact_id=None,
        )
    except runtime_validation.RuntimeBoundaryError as exc:
        raise ActivationError("runtime_evidence_invalid", "terminal A2A timeline is invalid", EXIT_RUNTIME) from exc
    recovery = a2a.get("recovery")
    if type(recovery) is not dict or recovery.get("same_task") is not True:
        raise ActivationError("runtime_evidence_invalid", "terminal A2A recovery proof is invalid", EXIT_RUNTIME)
    if expected_state == "canceled":
        if set(recovery) != {"same_task", "cancel_sent_task_id", "initial_task_id", "observed_task_ids"}:
            raise ActivationError("runtime_evidence_invalid", "cancellation proof is not closed", EXIT_RUNTIME)
        observed = recovery.get("observed_task_ids")
        if (
            recovery.get("cancel_sent_task_id") != a2a["task_id"]
            or recovery.get("initial_task_id") != a2a["task_id"]
            or type(observed) is not list
            or not observed
            or any(task_id != a2a["task_id"] for task_id in observed)
        ):
            raise ActivationError("runtime_evidence_invalid", "cancellation crossed task lineage", EXIT_RUNTIME)
    elif set(recovery) != {"same_task"}:
        raise ActivationError("runtime_evidence_invalid", "terminal recovery proof is not closed", EXIT_RUNTIME)
    graphflow = root.get("graphflow")
    if type(graphflow) is not dict or set(graphflow) != {
        "state_sha256", "initial_checkpoint_sha256", "terminal_state"
    }:
        raise ActivationError("runtime_evidence_invalid", "terminal GraphFlow proof is not closed", EXIT_RUNTIME)
    if expected_state == "input-required":
        state_sha256 = graphflow.get("state_sha256")
        if type(state_sha256) is not str:
            raise ActivationError("runtime_evidence_invalid", "terminal GraphFlow digest is malformed", EXIT_RUNTIME)
        try:
            terminal_state = runtime_validation.validate_persisted_graphflow_state(
                graphflow.get("terminal_state"),
                run_id=run_id,
                source_revision=source_revision,
                case_id=case_id,
                case_digest=root["case_digest"],
                candidate_revision=root["candidate_revision"],
                task_id=a2a["task_id"],
                context_id=a2a["context_id"],
                state_sha256=state_sha256,
            )
        except runtime_validation.RuntimeBoundaryError as exc:
            raise ActivationError("runtime_evidence_invalid", "terminal GraphFlow state is invalid", EXIT_RUNTIME) from exc
        if (
            terminal_state["status"] != "INPUT_REQUIRED"
            or terminal_state["recommendation"] is not None
            or terminal_state["reconciliation_attempts"] != case.expected.reconciliation_attempts
            or graphflow.get("initial_checkpoint_sha256")
            != terminal_state["initial_checkpoint_sha256"]
        ):
            raise ActivationError("runtime_evidence_invalid", "input-required GraphFlow proof mismatch", EXIT_RUNTIME)
    elif any(graphflow.get(field) is not None for field in graphflow):
        raise ActivationError("runtime_evidence_invalid", "canceled or failed run persisted GraphFlow state", EXIT_RUNTIME)
    return root


def _validate_runtime_final(
    value: bytes,
    *,
    run_id: str,
    source_revision: str,
    case_id: str,
    case_object: object,
    requested_decision: str,
    handoff: Mapping[str, object],
) -> Mapping[str, object]:
    contracts, runtime_validation = _validation_modules()
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
    if value != _canonical_json(root):
        raise ActivationError("runtime_evidence_invalid", "final runtime evidence is not canonical", EXIT_RUNTIME)
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
    artifact_object = root.get("artifact")
    decision_object = root.get("decision")
    a2a = root.get("a2a")
    graphflow = root.get("graphflow")
    approval = root.get("approval")
    if not all(type(item) is dict for item in (artifact_object, decision_object, a2a, graphflow, approval)):
        raise ActivationError("runtime_evidence_invalid", "final runtime proof sections are malformed", EXIT_RUNTIME)
    try:
        case = contracts.validate_case(case_object)
        artifact = contracts.validate_recommendation_artifact(artifact_object)
        decided_at_value = decision_object.get("decided_at")
        if type(decided_at_value) is not str or not decided_at_value.endswith("Z"):
            raise ValueError("decision time is malformed")
        decided_at = datetime.fromisoformat(decided_at_value[:-1] + "+00:00")
        decision = contracts.validate_release_decision(
            decision_object, artifact=artifact, at_time=decided_at
        )
    except (contracts.ContractViolation, TypeError, ValueError) as exc:
        raise ActivationError("runtime_evidence_invalid", "artifact, decision, or case contract is invalid", EXIT_RUNTIME) from exc
    if (
        contracts.to_plain_object(artifact) != artifact_object
        or contracts.to_plain_object(decision) != decision_object
    ):
        raise ActivationError("runtime_evidence_invalid", "artifact or decision is not canonical", EXIT_RUNTIME)
    bindings = ("run_id", "source_revision", "case_id", "case_digest", "candidate_revision", "artifact_digest")
    for field in bindings:
        expected_value = getattr(artifact, field)
        if field != "artifact_digest" and root.get(field) != expected_value:
            raise ActivationError("runtime_evidence_invalid", f"artifact {field} mismatch", EXIT_RUNTIME)
        if getattr(decision, field) != expected_value:
            raise ActivationError("runtime_evidence_invalid", f"decision {field} mismatch", EXIT_RUNTIME)
    if (
        case.case_id != case_id
        or contracts.canonical_sha256(case) != artifact.case_digest
        or case.candidate.candidate_revision != artifact.candidate_revision
        or case.expected.a2a_state != "completed"
        or case.expected.recommendation != artifact.recommendation
        or case.expected.reconciliation_attempts != artifact.reconciliation_attempts
        or decision.decision != requested_decision
        or decision.approver != "human-release-owner"
        or handoff.get("artifact_digest") != artifact.artifact_digest
    ):
        raise ActivationError("runtime_evidence_invalid", "case or requested decision binding mismatch", EXIT_RUNTIME)
    if set(a2a) != {
        "state", "task_id", "context_id", "artifact_id", "authoritative_content",
        "transport_mode", "used_streaming_workflow", "event_timeline",
    }:
        raise ActivationError("runtime_evidence_invalid", "A2A proof is not closed", EXIT_RUNTIME)
    if (
        a2a.get("state") != "completed"
        or a2a.get("authoritative_content") != "data"
        or a2a.get("transport_mode") != "maf-workflow"
        or a2a.get("used_streaming_workflow") is not True
        or a2a.get("task_id") != artifact.a2a_task_id
        or a2a.get("context_id") != artifact.a2a_context_id
        or a2a.get("artifact_id") != artifact.artifact_id
    ):
        raise ActivationError("runtime_evidence_invalid", "A2A proof does not bind the artifact", EXIT_RUNTIME)
    try:
        runtime_validation.validate_persisted_event_timeline(
            a2a.get("event_timeline"),
            task_id=artifact.a2a_task_id,
            context_id=artifact.a2a_context_id,
            terminal_state="completed",
            artifact_id=artifact.artifact_id,
        )
    except runtime_validation.RuntimeBoundaryError as exc:
        raise ActivationError("runtime_evidence_invalid", "A2A event timeline is invalid", EXIT_RUNTIME) from exc
    if set(graphflow) != {
        "state_sha256", "initial_checkpoint_sha256", "terminal_state",
        "state_loaded_for_analysis", "analysis_rerun_on_approval_resume",
    }:
        raise ActivationError("runtime_evidence_invalid", "GraphFlow proof is not closed", EXIT_RUNTIME)
    try:
        terminal_state = runtime_validation.validate_persisted_graphflow_state(
            graphflow.get("terminal_state"),
            run_id=artifact.run_id,
            source_revision=artifact.source_revision,
            case_id=artifact.case_id,
            case_digest=artifact.case_digest,
            candidate_revision=artifact.candidate_revision,
            task_id=artifact.a2a_task_id,
            context_id=artifact.a2a_context_id,
            state_sha256=artifact.graph_state_sha256,
        )
    except runtime_validation.RuntimeBoundaryError as exc:
        raise ActivationError("runtime_evidence_invalid", "GraphFlow terminal proof is invalid", EXIT_RUNTIME) from exc
    if (
        graphflow.get("analysis_rerun_on_approval_resume") is not False
        or graphflow.get("state_loaded_for_analysis") is not True
        or graphflow.get("state_sha256") != artifact.graph_state_sha256
        or graphflow.get("initial_checkpoint_sha256") != terminal_state["initial_checkpoint_sha256"]
        or terminal_state["recommendation"] != artifact.recommendation
        or terminal_state["basis"] != list(artifact.basis)
        or terminal_state["resolved_contradictions"] != list(artifact.resolved_contradictions)
        or terminal_state["unresolved_contradictions"] != list(artifact.unresolved_contradictions)
        or terminal_state["reconciliation_attempts"] != artifact.reconciliation_attempts
        or approval.get("checkpoint_id") != approval.get("restored_checkpoint_id")
        or approval.get("checkpoint_id") != handoff.get("checkpoint_id")
        or approval.get("initial_request_info_count") != 1
        or approval.get("resume_request_info_count") != 0
        or type(approval.get("decision_replayed")) is not bool
        or set(approval) != {
            "checkpoint_id", "restored_checkpoint_id", "initial_request_info_count",
            "resume_request_info_count", "decision_replayed",
        }
    ):
        raise ActivationError("runtime_evidence_invalid", "resume proof does not bind one analysis and checkpoint", EXIT_RUNTIME)
    packages = root.get("packages")
    if (
        packages != _PINNED_PACKAGES
        or contracts.to_plain_object(artifact.packages) != _PINNED_PACKAGES
    ):
        raise ActivationError("runtime_evidence_invalid", "runtime package identity is not pinned", EXIT_RUNTIME)
    if type(root.get("python")) is not str or _PYTHON_VERSION.fullmatch(root["python"]) is None:
        raise ActivationError("runtime_evidence_invalid", "runtime Python identity is malformed", EXIT_RUNTIME)
    return root


def _validation_modules():
    sandbox_root = Path(__file__).resolve().parent
    sandbox_text = str(sandbox_root)
    if sandbox_text not in sys.path:
        sys.path.insert(0, sandbox_text)
    from interop_sandbox import contracts, runtime_cli

    return contracts, runtime_cli


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
    environment.update({"SANDBOX_PROJECT": expectation.project, "SANDBOX_IMAGE": expectation.image, "SANDBOX_MODE": expectation.mode, "SANDBOX_SOURCE_REVISION": expectation.source_revision, "SANDBOX_RUN_ID": expectation.run_id, "SANDBOX_CASE_ID": expectation.case_id, "SANDBOX_DECISION": expectation.decision, "SANDBOX_NETWORK": expectation.network, "SANDBOX_STATE_VOLUME": expectation.state_volume, "SANDBOX_EVIDENCE_VOLUME": expectation.evidence_volume, "SANDBOX_WORKER_STATE_READ_ONLY": "true" if expectation.mode == "resume" else "false"})
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
    if value != "desktop-linux":
        raise ActivationError(
            "invalid_context",
            "docker context must be the approved desktop-linux context",
            EXIT_USAGE,
        )
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


def validate_docker_context_record(value: object, context: str) -> None:
    """Require one approved context with a local-only Docker endpoint."""

    if context != "desktop-linux":
        raise ActivationError(
            "invalid_context", "docker context is not approved", EXIT_PRECONDITION
        )
    if type(value) is not list or len(value) != 1 or type(value[0]) is not dict:
        raise ActivationError(
            "invalid_context", "docker context inspection shape mismatch", EXIT_PRECONDITION
        )
    record = value[0]
    endpoints = record.get("Endpoints")
    if record.get("Name") != context or type(endpoints) is not dict:
        raise ActivationError(
            "invalid_context", "docker context identity mismatch", EXIT_PRECONDITION
        )
    docker_endpoint = endpoints.get("docker")
    if type(docker_endpoint) is not dict:
        raise ActivationError(
            "invalid_context", "docker context endpoint is unavailable", EXIT_PRECONDITION
        )
    endpoint = docker_endpoint.get("Host")
    if type(endpoint) is not str or docker_endpoint.get("SkipTLSVerify") is not False:
        raise ActivationError(
            "invalid_context", "docker context endpoint is not local", EXIT_PRECONDITION
        )
    local_npipe = endpoint == "npipe:////./pipe/dockerDesktopLinuxEngine"
    local_unix = endpoint.startswith("unix:///") and (
        endpoint[7:].startswith("/")
        and ".." not in Path(endpoint[7:]).parts
        and not any(ord(character) < 0x20 for character in endpoint)
    )
    if not (local_npipe or local_unix):
        raise ActivationError(
            "invalid_context", "docker context endpoint is not local", EXIT_PRECONDITION
        )


def validate_daemon_id(value: str) -> str:
    try:
        daemon_id = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ActivationError(
            "invalid_daemon", "docker daemon identity is malformed", EXIT_PRECONDITION
        ) from exc
    if type(daemon_id) is not str or _DAEMON_ID.fullmatch(daemon_id) is None:
        raise ActivationError(
            "invalid_daemon", "docker daemon identity is malformed", EXIT_PRECONDITION
        )
    return daemon_id


def _validate_docker_context(context: str) -> str:
    result = _run(["docker", "context", "inspect", context], timeout=20, environment=_minimal_environment())
    try:
        contexts = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ActivationError("invalid_context", "docker context inspection was not JSON", EXIT_PRECONDITION) from exc
    validate_docker_context_record(contexts, context)
    daemon = _run(
        ["docker", "--context", context, "info", "--format", "{{json .ID}}"],
        timeout=30,
        environment=_minimal_environment(),
    )
    return validate_daemon_id(daemon.stdout.strip())


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
        data = _read_regular_file(path, label)
        value = json.loads(data)
    except (OSError, json.JSONDecodeError, UnicodeError, ActivationError) as exc:
        raise ActivationError("invalid_handoff", f"{label} cannot be read", EXIT_PRECONDITION) from exc
    if type(value) is not dict:
        raise ActivationError("invalid_handoff", f"{label} is not an object", EXIT_PRECONDITION)
    if data != _canonical_json(value):
        raise ActivationError("invalid_handoff", f"{label} is not canonical", EXIT_PRECONDITION)
    return value


def _load_canonical_json_bytes(value: bytes, label: str) -> Mapping[str, object]:
    decoded = _decode_json_object_bytes(value, label)
    if value != _canonical_json(decoded):
        raise ActivationError(
            "runtime_evidence_invalid", f"{label} is not canonical JSON", EXIT_RUNTIME
        )
    return decoded


def _decode_json_object_bytes(value: bytes, label: str) -> Mapping[str, object]:
    try:
        decoded = json.loads(value)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ActivationError(
            "runtime_evidence_invalid", f"{label} is not JSON", EXIT_RUNTIME
        ) from exc
    if type(decoded) is not dict:
        raise ActivationError(
            "runtime_evidence_invalid", f"{label} is not an object", EXIT_RUNTIME
        )
    return decoded


def _canonical_json(value: object) -> bytes:
    return (json.dumps(value, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")


def _emit_error(error_class: str, message: str) -> None:
    print(json.dumps({"error_class": error_class, "message": message}, sort_keys=True, separators=(",", ":")), file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
