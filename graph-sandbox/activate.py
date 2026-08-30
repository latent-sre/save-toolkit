#!/usr/bin/env python
"""Sole build and runtime entrypoint for the GRAPH-002 Docker sandbox."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from typing import Callable, Mapping, Sequence

from build_images import SnapshotError, build_and_lock
from preflight import (
    CommandTimeoutError,
    DockerCLI,
    PreflightError,
    REVISION_RE,
    SandboxCase,
    _load_json,
    _is_link_or_junction,
    _reject_path_indirection,
    assert_no_ambient_docker_authority,
    load_sandbox_case,
    project_scope,
    render_compose,
    run_process,
    scrub_environment,
    trusted_layout,
    validate_local_context,
    validate_preflight,
    validate_resource_mode,
)


class ActivationError(PreflightError):
    """Activation cannot preserve the validated runtime boundary."""


MAX_EVIDENCE_BYTES = 32 * 1024 * 1024
MAX_EVIDENCE_FILES = 1024
ALLOWED_EVIDENCE_FILES = frozenset(
    {
        "checkpoint-lineage.json",
        "checksums.sha256",
        "commands.jsonl",
        "compose-config.json",
        "effects.jsonl",
        "environment.json",
        "events.jsonl",
        "final-state.json",
        "manifest.json",
        "receipts/inventory.json",
        "receipts/payment.json",
        "runtime.json",
        "verification.json",
    }
)
REQUIRED_RUNNER_EVIDENCE = frozenset(
    {
        "checkpoint-lineage.json",
        "checksums.sha256",
        "effects.jsonl",
        "events.jsonl",
        "final-state.json",
        "manifest.json",
        "runtime.json",
    }
)
CHECKSUM_LINE_RE = re.compile(r"^(?P<digest>[0-9a-f]{64})  (?P<path>[^\r\n]+)$")
CONTAINER_ID_RE = re.compile(r"^[0-9a-f]{12,64}$")
TERMINAL_EVIDENCE_EXITS = frozenset({0, 2})
TERMINAL_REJECTION_EXIT = 64
HOST_TIMEOUT_EXIT = 124
HOST_INTERRUPT_EXIT = 130
HOST_PRESERVATION_FAILURE_EXIT = 125
HOST_INCONCLUSIVE_EXIT = 126
CONTRACT_VERSION = "checkout-payments-timeout-drill/v1"
STATE_SCHEMA_VERSION = "graph-state/v2"
THREAD_PREFIX = "checkout-payments-timeout-drill-v1:"
RFC3339_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$")
ATOMIC_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class RunClaim:
    """Persistent identity and lifecycle document; it is not a process lock."""

    path: Path
    run_id: str
    source_revision: str
    context_fingerprint: str
    case_id: str
    case_digest: str
    approval_fixture: str
    compose_digest: str
    phase: str
    runner_existed: bool
    observed_resources: tuple[str, ...]

    def _document(
        self,
        phase: str | None = None,
        *,
        runner_existed: bool | None = None,
        observed_resources: Sequence[str] | None = None,
    ) -> dict[str, object]:
        return {
            "claim_version": "graph-sandbox-run-claim/v2",
            "run_id": self.run_id,
            "case_id": self.case_id,
            "case_digest": self.case_digest,
            "approval_fixture": self.approval_fixture,
            "compose_digest": self.compose_digest,
            "source_revision": self.source_revision,
            "context_fingerprint": self.context_fingerprint,
            "phase": self.phase if phase is None else phase,
            "runner_existed": self.runner_existed if runner_existed is None else runner_existed,
            "observed_resources": list(
                self.observed_resources if observed_resources is None else observed_resources
            ),
        }

    @classmethod
    def acquire(
        cls,
        mode: str,
        evidence_root: Path,
        run_id: str,
        source_revision: str,
        context_fingerprint: str,
        case_id: str,
        case_digest: str,
        approval_fixture: str,
        compose_digest: str,
    ) -> "RunClaim":
        if mode not in {"fresh", "resume"}:
            raise ActivationError("run claim: mode must be fresh or resume")
        if not evidence_root.is_absolute():
            raise ActivationError("evidence-root: absolute canonical path required")
        _reject_path_indirection(evidence_root)
        root = evidence_root.resolve(strict=True)
        if not root.is_dir() or not ATOMIC_ID_RE.fullmatch(run_id):
            raise ActivationError("run claim: invalid evidence root or run identity")
        if approval_fixture not in {"APPROVED", "REJECTED", "TIMEOUT"}:
            raise ActivationError("run claim: invalid approval fixture")
        if not SHA256_RE.fullmatch(compose_digest):
            raise ActivationError("run claim: invalid Compose digest")
        path = root / f".{run_id}.claim.json"
        _reject_path_indirection(path.parent)
        identity = {
            "claim_version": "graph-sandbox-run-claim/v2",
            "run_id": run_id,
            "case_id": case_id,
            "case_digest": case_digest,
            "approval_fixture": approval_fixture,
            "compose_digest": compose_digest,
            "source_revision": source_revision,
            "context_fingerprint": context_fingerprint,
        }
        if mode == "fresh":
            expected = {
                **identity,
                "phase": "PRELAUNCH",
                "runner_existed": False,
                "observed_resources": [],
            }
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
            try:
                descriptor = os.open(path, flags, 0o600)
            except FileExistsError as exc:
                raise ActivationError("run claim: run is already claimed") from exc
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write((json.dumps(expected, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
                    stream.flush()
                    os.fsync(stream.fileno())
            except BaseException:
                path.unlink(missing_ok=True)
                raise
        else:
            if _is_link_or_junction(path) or not path.is_file():
                raise ActivationError("run claim: resume requires an existing regular claim")
            try:
                actual = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise ActivationError("run claim: invalid claim document") from exc
            if (
                not isinstance(actual, dict)
                or {name: actual.get(name) for name in identity} != identity
                or actual.get("phase") not in {"RUNNING", "PRESERVED", "PUBLISHED"}
                or not isinstance(actual.get("runner_existed"), bool)
                or not isinstance(actual.get("observed_resources"), list)
                or not all(
                    isinstance(value, str) and value
                    for value in actual.get("observed_resources", [])
                )
                or actual.get("observed_resources") != sorted(set(actual.get("observed_resources", [])))
                or set(actual) != set(identity) | {"phase", "runner_existed", "observed_resources"}
            ):
                raise ActivationError("run claim: claim identity mismatch")
            expected = actual
        return cls(
            path,
            run_id,
            source_revision,
            context_fingerprint,
            case_id,
            case_digest,
            approval_fixture,
            compose_digest,
            str(expected["phase"]),
            bool(expected["runner_existed"]),
            tuple(expected["observed_resources"]),
        )

    def transition(self, phase: str) -> None:
        allowed = {
            "PRELAUNCH": {"RUNNING"},
            "RUNNING": {"PRESERVED", "PUBLISHED"},
            "PRESERVED": {"RUNNING", "PUBLISHED"},
            "PUBLISHED": set(),
        }
        if phase not in allowed.get(self.phase, set()):
            raise ActivationError(f"run claim: invalid phase transition {self.phase}->{phase}")
        self._verify_document()
        _atomic_write(
            self.path,
            (json.dumps(self._document(phase), sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"),
        )
        object.__setattr__(self, "phase", phase)

    def record_resources(
        self, resource_keys: Sequence[str], *, runner_existed: bool
    ) -> None:
        normalized = tuple(sorted(set(resource_keys)))
        if tuple(resource_keys) != normalized or not all(
            re.fullmatch(r"(?:container|network|volume):[^\r\n]+", key)
            for key in normalized
        ):
            raise ActivationError("run claim: invalid observed resource set")
        if self.runner_existed and not runner_existed:
            raise ActivationError("run claim: runner history cannot be cleared")
        self._verify_document()
        _atomic_write(
            self.path,
            (
                json.dumps(
                    self._document(
                        runner_existed=runner_existed,
                        observed_resources=normalized,
                    ),
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode("utf-8"),
        )
        object.__setattr__(self, "runner_existed", runner_existed)
        object.__setattr__(self, "observed_resources", normalized)

    def _verify_document(self) -> None:
        if _is_link_or_junction(self.path) or not self.path.is_file():
            raise ActivationError("run claim: claim changed")
        try:
            actual = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ActivationError("run claim: invalid claim document") from exc
        if actual != self._document():
            raise ActivationError("run claim: claim identity or phase mismatch")

    def release(self) -> None:
        self._verify_document()
        self.path.unlink()


@dataclass(frozen=True)
class ActivationLease:
    """Kernel-held cross-platform lease preventing concurrent activation."""

    path: Path
    run_id: str
    descriptor: int

    @classmethod
    def acquire(cls, evidence_root: Path, run_id: str) -> "ActivationLease":
        if not evidence_root.is_absolute():
            raise ActivationError("activation lease: absolute evidence root required")
        _reject_path_indirection(evidence_root)
        root = evidence_root.resolve(strict=True)
        if not root.is_dir() or not ATOMIC_ID_RE.fullmatch(run_id):
            raise ActivationError("activation lease: invalid evidence root or run identity")
        path = root / f".{run_id}.activation.lock"
        if path.exists() and _is_link_or_junction(path):
            raise ActivationError("activation lease: link or reparse point rejected")
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, flags, 0o600)
        except OSError as exc:
            raise ActivationError("activation lease: lock file unavailable") from exc
        try:
            if os.fstat(descriptor).st_size == 0:
                os.write(descriptor, b"\0")
                os.fsync(descriptor)
            os.lseek(descriptor, 0, os.SEEK_SET)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            os.close(descriptor)
            raise ActivationError("activation lease: activation already in progress") from exc
        except BaseException:
            os.close(descriptor)
            raise
        return cls(path, run_id, descriptor)

    def release(self) -> None:
        if self.descriptor < 0:
            raise ActivationError("activation lease: already released")
        try:
            os.lseek(self.descriptor, 0, os.SEEK_SET)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.descriptor, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.descriptor, fcntl.LOCK_UN)
        finally:
            os.close(self.descriptor)
            object.__setattr__(self, "descriptor", -1)


def _runtime_revision_is_exact(
    repository_root: Path,
    source_revision: str,
    *,
    runner=run_process,
    environment: Mapping[str, str],
) -> None:
    if not REVISION_RE.fullmatch(source_revision):
        raise ActivationError("source_revision: expected lowercase 40-hex revision")
    head = runner(
        ["git", "-C", str(repository_root), "rev-parse", "HEAD"],
        environment=environment,
        timeout_seconds=30,
        stdin=None,
    )
    if head.returncode != 0 or str(head.stdout).strip() != source_revision:
        raise ActivationError("source_revision: checkout HEAD changed")
    status = runner(
        [
            "git",
            "-C",
            str(repository_root),
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ],
        environment=environment,
        timeout_seconds=30,
        stdin=None,
    )
    if status.returncode != 0:
        raise ActivationError("source_revision: checkout status unavailable")
    dirty = [line for line in str(status.stdout).splitlines() if line.strip()]
    allowed = {" M graph-sandbox/images.lock.json"}
    if set(dirty) - allowed or len(dirty) != len(set(dirty)):
        raise ActivationError("source_revision: checkout changed outside the generated image lock")


def _canonical_compose_bytes(model: Mapping[str, object]) -> bytes:
    return (json.dumps(model, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write(path: Path, payload: bytes) -> None:
    temporary = path.parent / f".{path.name}.{secrets.token_hex(16)}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(temporary, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _evidence_files(run_dir: Path, *, max_bytes: int) -> dict[str, Path]:
    files: dict[str, Path] = {}
    total_bytes = 0
    for path in sorted(run_dir.rglob("*")):
        if _is_link_or_junction(path):
            raise ActivationError("evidence export: symlink or reparse path rejected")
        relative = path.relative_to(run_dir).as_posix()
        if path.is_dir():
            if relative != "receipts":
                raise ActivationError(f"unexpected evidence path: {relative}")
            continue
        if not path.is_file() or relative not in ALLOWED_EVIDENCE_FILES:
            raise ActivationError(f"unexpected evidence path: {relative}")
        total_bytes += path.stat().st_size
        if total_bytes > max_bytes:
            raise ActivationError("evidence export: size limit exceeded")
        if len(files) >= MAX_EVIDENCE_FILES:
            raise ActivationError("evidence export: file count limit exceeded")
        files[relative] = path
    return files


def _verify_existing_checksums(files: Mapping[str, Path]) -> None:
    checksum_path = files["checksums.sha256"]
    try:
        lines = checksum_path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ActivationError("evidence export: invalid runner checksums") from exc
    observed: dict[str, str] = {}
    for line in lines:
        match = CHECKSUM_LINE_RE.fullmatch(line)
        if not match or match.group("path") in observed:
            raise ActivationError("evidence export: invalid runner checksums")
        observed[match.group("path")] = match.group("digest")
    expected_paths = set(files) - {"checksums.sha256"}
    if set(observed) != expected_paths:
        raise ActivationError("evidence export: runner checksum coverage mismatch")
    for relative, expected_digest in observed.items():
        if _sha256_file(files[relative]) != expected_digest:
            raise ActivationError(f"evidence export: checksum mismatch for {relative}")


def _load_evidence_json(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ActivationError(f"evidence export: invalid {label}") from exc
    if not isinstance(value, dict):
        raise ActivationError(f"evidence export: {label} must be an object")
    return value


def _load_evidence_jsonl(path: Path, label: str) -> list[dict[str, object]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        values = [json.loads(line) for line in lines if line]
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ActivationError(f"evidence export: invalid {label}") from exc
    if not all(isinstance(value, dict) for value in values):
        raise ActivationError(f"evidence export: {label} records must be objects")
    return values


def _require_closed(value: object, required: set[str], label: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != required:
        raise ActivationError(f"evidence export: {label} schema mismatch")
    return value


def _validate_target_receipt(
    value: object, effect_class: str, expected_key: str | None = None
) -> dict[str, object]:
    receipt = _require_closed(
        value,
        {
            "receipt_version",
            "effect_class",
            "receipt_id",
            "idempotency_key",
            "request_digest",
            "status",
            "replayed",
        },
        f"{effect_class} receipt",
    )
    if (
        receipt["receipt_version"] != "synthetic-receipt/v1"
        or receipt["effect_class"] != effect_class
        or receipt["status"] != "committed"
        or not isinstance(receipt["replayed"], bool)
        or not isinstance(receipt["receipt_id"], str)
        or not ATOMIC_ID_RE.fullmatch(receipt["receipt_id"])
        or not isinstance(receipt["idempotency_key"], str)
        or not SHA256_RE.fullmatch(receipt["idempotency_key"])
        or not isinstance(receipt["request_digest"], str)
        or not SHA256_RE.fullmatch(receipt["request_digest"])
        or (expected_key is not None and receipt["idempotency_key"] != expected_key)
    ):
        raise ActivationError(f"evidence export: {effect_class} receipt schema mismatch")
    return receipt


def _derive_parent_key(effect_id: str) -> str:
    return hashlib.sha256(f"{CONTRACT_VERSION}\n{effect_id}".encode("ascii")).hexdigest()


def _derive_child_key(parent_key: str, effect_class: str) -> str:
    return hashlib.sha256(
        f"{CONTRACT_VERSION}\n{parent_key}\n{effect_class}".encode("ascii")
    ).hexdigest()


def _validate_success_controls(
    final_state: Mapping[str, object],
    run_id: str,
    *,
    allow_completed_budget_failure: bool = False,
    reconciled_effect: bool = False,
) -> None:
    approval = _require_closed(
        final_state["approval"],
        {"request_id", "status", "actor_class", "decision_time"},
        "approval",
    )
    if (
        approval["request_id"] != f"approval-{run_id}"
        or approval["status"] != "APPROVED"
        or approval["actor_class"] != "fixture-operator"
        or not isinstance(approval["decision_time"], str)
        or not RFC3339_UTC_RE.fullmatch(approval["decision_time"])
    ):
        raise ActivationError("evidence export: approval is not a fixture APPROVED decision")

    required_tasks = {
        f"{run_id}:readiness:0",
        f"{run_id}:readiness:1",
        f"{run_id}:readiness:2",
        f"{run_id}:checkout_effect:0",
    }
    allowed_tasks = required_tasks | {f"{run_id}:reconcile_if_ambiguous:0"}
    tasks = final_state["tasks"]
    if not isinstance(tasks, dict) or not required_tasks.issubset(tasks) or not set(tasks) <= allowed_tasks:
        raise ActivationError("evidence export: tasks do not contain the four required healthy tasks")
    for task_id, task in tasks.items():
        closed = _require_closed(task, {"status", "attempt"}, f"tasks[{task_id}]")
        expected_status = (
            "failed"
            if reconciled_effect and task_id == f"{run_id}:checkout_effect:0"
            else "completed"
        )
        if closed["status"] != expected_status or closed["attempt"] != 1:
            raise ActivationError(f"evidence export: tasks[{task_id}] is not completed once")

    readiness = final_state["readiness"]
    expected_services = {"checkout", "payments", "inventory"}
    if not isinstance(readiness, dict) or set(readiness) != expected_services:
        raise ActivationError("evidence export: readiness must contain exactly three branches")
    for service in sorted(expected_services):
        branch = _require_closed(readiness[service], {"status", "service"}, f"readiness[{service}]")
        if branch != {"status": "ok", "service": service}:
            raise ActivationError(f"evidence export: readiness[{service}] is not healthy")

    budgets = final_state["budgets"]
    expected_limits = {
        "attempts": 8,
        "wall_time_ms": 120_000,
        "model_calls": 1,
        "tokens": 64,
        "spend_micro_usd": 0,
    }
    if not isinstance(budgets, dict) or set(budgets) != set(expected_limits):
        raise ActivationError("evidence export: budgets must contain exactly five counters")
    for kind, limit in expected_limits.items():
        counter = _require_closed(budgets[kind], {"limit", "consumed"}, f"budgets[{kind}]")
        consumed = counter["consumed"]
        if (
            isinstance(counter["limit"], bool)
            or not isinstance(counter["limit"], int)
            or counter["limit"] != limit
            or isinstance(consumed, bool)
            or not isinstance(consumed, int)
            or not 0 <= consumed <= limit
        ):
            raise ActivationError(f"evidence export: budgets[{kind}] is not bounded")
    required_consumption = {
        "attempts": 1,
        "model_calls": 1,
        "tokens": 64,
        "spend_micro_usd": 0,
    }
    if any(budgets[kind]["consumed"] != consumed for kind, consumed in required_consumption.items()):
        raise ActivationError("evidence export: budgets do not prove healthy fixture consumption")

    cancellation = _require_closed(
        final_state["cancellation"],
        {"state", "request_id", "acknowledgement_ms"},
        "cancellation",
    )
    if cancellation != {"state": "NONE", "request_id": None, "acknowledgement_ms": None}:
        raise ActivationError("evidence export: cancellation is not NONE")
    failure = final_state["failure"]
    if allow_completed_budget_failure:
        if failure != {
            "plane": "graph-control",
            "error_class": "budget_exhausted",
            "retryable": False,
            "disposition": "effect-completed-budget-exceeded",
        }:
            raise ActivationError("evidence export: completed budget failure is not exact")
    elif failure is not None:
        raise ActivationError("evidence export: failure must be null for success")


def _validate_runtime_evidence(files: Mapping[str, Path]) -> dict[str, object]:
    runtime = _require_closed(
        _load_evidence_json(files["runtime.json"], "runtime"),
        {"runtime_version", "python_version", "packages"},
        "runtime",
    )
    packages = _require_closed(
        runtime["packages"],
        {"httpx", "langgraph", "langgraph-checkpoint-sqlite"},
        "runtime packages",
    )
    expected_packages = {
        "httpx": "0.28.1",
        "langgraph": "1.0.10",
        "langgraph-checkpoint-sqlite": "3.1.1",
    }
    if runtime["runtime_version"] != "graph-runner-runtime/v1":
        raise ActivationError("evidence export: runtime version mismatch")
    if runtime["python_version"] != "3.12.10":
        raise ActivationError("evidence export: runtime python version mismatch")
    for package, expected in expected_packages.items():
        if packages[package] != expected:
            raise ActivationError(f"evidence export: runtime {package} version mismatch")
    return runtime


EVENT_DATA_SCHEMAS: Mapping[str, tuple[set[str], set[str]]] = {
    "run.accepted": ({"result"}, set()),
    "run.started": ({"result"}, set()),
    "run.terminal": ({"result", "outcome"}, {"authoritative_result_id"}),
    "run.cancelled": ({"result", "outcome"}, set()),
    "run.inconclusive": ({"result", "outcome"}, set()),
    "task.scheduled": ({"status"}, set()),
    "task.started": ({"status"}, set()),
    "task.completed": ({"status"}, set()),
    "task.failed": ({"status", "disposition"}, set()),
    "task.retry_scheduled": ({"status", "retry_number"}, set()),
    "task.retry_exhausted": ({"status", "attempts"}, set()),
    "edge.selected": ({"edge_id"}, set()),
    "edge.fanout_emitted": ({"targets"}, set()),
    "edge.join_satisfied": ({"branches"}, set()),
    "edge.join_starved": ({"missing_branches"}, set()),
    "approval.requested": ({"request_id", "approval_status"}, set()),
    "approval.approved": ({"request_id", "approval_status", "actor_class"}, set()),
    "approval.rejected": ({"request_id", "approval_status", "actor_class"}, set()),
    "approval.timed_out": ({"request_id", "approval_status"}, set()),
    "checkpoint.write_started": ({"operation"}, set()),
    "checkpoint.write_completed": ({"operation", "result"}, set()),
    "checkpoint.write_failed": ({"operation", "result"}, set()),
    "checkpoint.resume_started": ({"operation"}, set()),
    "checkpoint.resume_completed": ({"operation", "result"}, set()),
    "checkpoint.resume_failed": ({"operation", "result"}, set()),
    "checkpoint.rejected": ({"operation", "result", "mismatches"}, set()),
    "effect.prepared": ({"effect_class", "effect_state"}, set()),
    "effect.dispatched": ({"effect_class", "effect_state"}, set()),
    "effect.receipt_recorded": ({"effect_class", "effect_state", "authoritative_result_id"}, set()),
    "effect.unknown": ({"effect_class", "effect_state", "reason_class"}, set()),
    "effect.reconciled": ({"effect_class", "effect_state", "authoritative_result_id"}, set()),
    "effect.replay_refused": ({"effect_class", "effect_state", "reason_class"}, set()),
    "budget.observed": ({"kind", "limit", "consumed", "remaining"}, set()),
    "budget.threshold_reached": ({"kind", "limit", "consumed", "remaining"}, set()),
    "budget.exhausted": ({"kind", "limit", "consumed", "remaining"}, set()),
    "cancellation.requested": ({"state", "request_id"}, set()),
    "cancellation.propagated": ({"state", "request_id"}, set()),
    "cancellation.acknowledged": ({"state", "request_id", "acknowledgement_ms"}, set()),
    "cancellation.unconfirmed": ({"state", "request_id"}, set()),
}


def _validate_boundary_events(
    events: Sequence[Mapping[str, object]],
    *,
    run_id: str,
    case_id: str,
    case_digest: str,
    source_revision: str,
    outcome: object,
) -> list[Mapping[str, object]]:
    if not events:
        raise ActivationError("evidence export: boundary events are empty")
    required = {
        "event_version", "event_type", "event_id", "sequence", "time_utc",
        "contract_version", "sandbox_version", "source_revision", "run_id",
        "case_id", "case_digest", "thread_id", "node_id", "task_id", "attempt_id",
        "replay_id", "checkpoint_id", "effect_id", "failure_plane", "error_class", "data",
    }
    thread_id = f"{THREAD_PREFIX}{run_id}"
    terminals: list[tuple[int, Mapping[str, object]]] = []
    approved_at: int | None = None
    join_at: int | None = None
    effect_at: int | None = None
    for expected_sequence, event in enumerate(events, start=1):
        closed = _require_closed(event, required, f"event[{expected_sequence}]")
        event_type = closed["event_type"]
        schema = EVENT_DATA_SCHEMAS.get(str(event_type))
        if schema is None:
            raise ActivationError("evidence export: unknown boundary event type")
        data = closed["data"]
        if not isinstance(data, dict):
            raise ActivationError("evidence export: boundary event data must be an object")
        required_data, optional_data = schema
        if not required_data.issubset(data) or set(data) - required_data - optional_data:
            raise ActivationError("evidence export: boundary event data schema mismatch")
        if (
            closed["event_version"] != "graph-boundary-event/v2"
            or closed["sequence"] != expected_sequence
            or closed["event_id"] != f"{run_id}:{expected_sequence:08d}"
            or closed["contract_version"] != CONTRACT_VERSION
            or closed["sandbox_version"] != "graph-sandbox/v1"
            or closed["source_revision"] != source_revision
            or closed["run_id"] != run_id
            or closed["case_id"] != case_id
            or closed["case_digest"] != case_digest
            or closed["thread_id"] != thread_id
            or not isinstance(closed["time_utc"], str)
            or not RFC3339_UTC_RE.fullmatch(closed["time_utc"])
        ):
            raise ActivationError("evidence export: boundary event sequence or lineage mismatch")
        if event_type == "approval.approved":
            approved_at = expected_sequence
        if event_type == "edge.join_satisfied":
            if join_at is not None:
                raise ActivationError("evidence export: duplicate readiness join")
            join_at = expected_sequence
        if str(event_type).startswith("effect.") and effect_at is None:
            effect_at = expected_sequence
        if event_type in {"run.terminal", "run.cancelled", "run.inconclusive"}:
            terminals.append((expected_sequence, closed))
    if [event["event_type"] for event in events[:2]] != ["run.accepted", "run.started"]:
        raise ActivationError("evidence export: run start event prefix is missing")
    if len(terminals) != 1 or terminals[0][0] != len(events):
        raise ActivationError("evidence export: exactly one final run terminal event required")
    terminal = terminals[0][1]
    terminal_data = terminal["data"]
    if not isinstance(terminal_data, dict) or terminal_data.get("outcome") != outcome:
        raise ActivationError("evidence export: terminal event outcome mismatch")
    expected_terminal = (
        "run.cancelled" if outcome == "CANCELLED"
        else "run.inconclusive" if outcome == "INCONCLUSIVE"
        else "run.terminal"
    )
    if terminal["event_type"] != expected_terminal:
        raise ActivationError("evidence export: terminal event type mismatch")
    if effect_at is not None and (approved_at is None or approved_at >= effect_at):
        raise ActivationError("evidence export: effect occurred before approval")
    if effect_at is not None and (join_at is None or join_at >= effect_at):
        raise ActivationError("evidence export: effect occurred before readiness join")
    if effect_at is not None:
        fanout_events = [event for event in events if event["event_type"] == "edge.fanout_emitted"]
        join_events = [event for event in events if event["event_type"] == "edge.join_satisfied"]
        approval_requests = [event for event in events if event["event_type"] == "approval.requested"]
        approvals = [event for event in events if event["event_type"] == "approval.approved"]
        if (
            len(fanout_events) != 1
            or fanout_events[0]["data"]
            != {"targets": ["checkout", "payments", "inventory"]}
            or len(join_events) != 1
            or join_events[0]["data"]
            != {"branches": ["checkout", "payments", "inventory"]}
            or len(approval_requests) != 1
            or len(approvals) != 1
            or approved_at is None
            or join_at is None
            or int(fanout_events[0]["sequence"]) >= join_at
            or join_at >= int(approval_requests[0]["sequence"])
            or int(approval_requests[0]["sequence"]) >= approved_at
        ):
            raise ActivationError("evidence export: readiness join does not precede approval")
        for ordinal in range(3):
            task_id = f"{run_id}:readiness:{ordinal}"
            task_events = [
                event
                for event in events
                if event["task_id"] == task_id
                and event["event_type"] in {"task.started", "task.completed", "task.failed"}
            ]
            if (
                [event["event_type"] for event in task_events]
                != ["task.started", "task.completed"]
                or task_events[0]["attempt_id"] != f"{task_id}:attempt-1"
                or task_events[1]["attempt_id"] != f"{task_id}:attempt-1"
                or int(task_events[1]["sequence"]) >= join_at
            ):
                raise ActivationError("evidence export: readiness task evidence is incomplete")
    return list(events)


def _validate_checkpoint_oracle(
    lineage: Mapping[str, object],
    events: Sequence[Mapping[str, object]],
    *,
    run_id: str,
    source_revision: str,
    runtime: Mapping[str, object],
) -> None:
    closed = _require_closed(
        lineage,
        {
            "lineage_version", "contract_version", "state_schema", "source_revision",
            "thread_id", "langgraph_version", "sqlite_saver_version",
            "resume_source_checkpoint_id", "checkpoints", "saver_checkpoint_ids",
        },
        "checkpoint lineage",
    )
    packages = runtime["packages"]
    checkpoints = closed["checkpoints"]
    saver_ids = closed["saver_checkpoint_ids"]
    if (
        closed["lineage_version"] != "graph-checkpoint-lineage/v2"
        or closed["contract_version"] != CONTRACT_VERSION
        or closed["state_schema"] != STATE_SCHEMA_VERSION
        or closed["source_revision"] != source_revision
        or closed["thread_id"] != f"{THREAD_PREFIX}{run_id}"
        or closed["langgraph_version"] != "1.0.10"
        or closed["sqlite_saver_version"] != "3.1.1"
        or closed["langgraph_version"] != packages["langgraph"]
        or closed["sqlite_saver_version"] != packages["langgraph-checkpoint-sqlite"]
        or not isinstance(checkpoints, list)
        or not checkpoints
        or not isinstance(saver_ids, list)
        or not saver_ids
        or not all(isinstance(value, str) and value for value in saver_ids)
        or len(saver_ids) != len(set(saver_ids))
    ):
        raise ActivationError("evidence export: checkpoint lineage mismatch")
    recorded: list[str] = []
    for record in checkpoints:
        item = _require_closed(record, {"checkpoint_id", "operation", "result"}, "checkpoint record")
        if item["operation"] != "write" or item["result"] != "recorded" or item["checkpoint_id"] not in saver_ids:
            raise ActivationError("evidence export: checkpoint ID absent from saver")
        recorded.append(str(item["checkpoint_id"]))
    if len(recorded) != len(set(recorded)):
        raise ActivationError("evidence export: duplicate checkpoint lineage record")
    if recorded != saver_ids:
        raise ActivationError("evidence export: checkpoint lineage does not equal saver IDs")

    pending: dict[str, int] = {}
    completed_write_ids: list[str] = []
    failed_write_ids: list[str] = []
    for event in events:
        event_type = event["event_type"]
        checkpoint_id = event["checkpoint_id"]
        if event_type == "checkpoint.write_started":
            if not isinstance(checkpoint_id, str) or checkpoint_id in pending:
                raise ActivationError("evidence export: invalid checkpoint write start")
            pending[checkpoint_id] = int(event["sequence"])
        elif event_type in {"checkpoint.write_completed", "checkpoint.write_failed"}:
            if checkpoint_id not in pending or pending.pop(str(checkpoint_id)) >= int(event["sequence"]):
                raise ActivationError("evidence export: unpaired checkpoint write")
            if event_type == "checkpoint.write_completed" and checkpoint_id not in saver_ids:
                raise ActivationError("evidence export: checkpoint ID absent from saver")
            if event_type == "checkpoint.write_completed":
                completed_write_ids.append(str(checkpoint_id))
            else:
                failed_write_ids.append(str(checkpoint_id))
    if pending:
        raise ActivationError("evidence export: unpaired checkpoint write")
    if (
        set(completed_write_ids) != set(saver_ids)
        or len(completed_write_ids) != len(set(completed_write_ids))
        or set(failed_write_ids) & set(saver_ids)
    ):
        raise ActivationError("evidence export: checkpoint write events do not equal saver IDs")

    resume_source = closed["resume_source_checkpoint_id"]
    resume_events = [
        event
        for event in events
        if event["event_type"]
        in {
            "checkpoint.resume_started",
            "checkpoint.resume_completed",
            "checkpoint.resume_failed",
        }
    ]
    pending_resume: Mapping[str, object] | None = None
    last_successful_source: object = None
    saver_positions = {checkpoint_id: index for index, checkpoint_id in enumerate(saver_ids)}
    for event in resume_events:
        if event["event_type"] == "checkpoint.resume_started":
            if pending_resume is not None:
                raise ActivationError("evidence export: overlapping checkpoint resume")
            pending_resume = event
            continue
        if pending_resume is None:
            raise ActivationError("evidence export: unpaired checkpoint resume")
        source_id = pending_resume["checkpoint_id"]
        result_id = event["checkpoint_id"]
        if event["event_type"] == "checkpoint.resume_completed":
            if (
                source_id not in saver_positions
                or result_id not in saver_positions
                or saver_positions[result_id] <= saver_positions[source_id]
                or int(pending_resume["sequence"]) >= int(event["sequence"])
            ):
                raise ActivationError("evidence export: wrong checkpoint resume source")
            last_successful_source = source_id
        elif result_id != source_id:
            raise ActivationError("evidence export: wrong failed checkpoint resume source")
        pending_resume = None
    if pending_resume is not None:
        raise ActivationError("evidence export: unpaired checkpoint resume")
    if resume_source != last_successful_source:
        diagnostic = (
            "unexpected checkpoint resume lineage"
            if resume_source is None
            else "wrong checkpoint resume source"
        )
        raise ActivationError(f"evidence export: {diagnostic}")


def _validate_readiness_automaton(
    final_state: Mapping[str, object],
    events: Sequence[Mapping[str, object]],
    *,
    require_healthy: bool,
) -> int:
    run_id = str(final_state["run_id"])
    fanout = [event for event in events if event["event_type"] == "edge.fanout_emitted"]
    if (
        len(fanout) != 1
        or fanout[0]["data"] != {"targets": ["checkout", "payments", "inventory"]}
    ):
        raise ActivationError("evidence export: readiness fanout evidence is incomplete")
    fanout_sequence = int(fanout[0]["sequence"])
    readiness = final_state["readiness"]
    if not isinstance(readiness, dict) or set(readiness) != {"checkout", "payments", "inventory"}:
        raise ActivationError("evidence export: readiness state is incomplete")
    failed_services = sorted(
        service
        for service, result in readiness.items()
        if not isinstance(result, dict) or result.get("status") != "ok"
    )
    if require_healthy and failed_services:
        raise ActivationError("evidence export: healthy readiness path contains a failed branch")
    if not require_healthy and not failed_services:
        raise ActivationError("evidence export: readiness failure path contains no failed branch")
    result_sequences: list[int] = []
    expected_task_ids = {f"{run_id}:readiness:{ordinal}" for ordinal in range(3)}
    observed_task_ids = {
        str(event["task_id"])
        for event in events
        if isinstance(event["task_id"], str) and ":readiness:" in str(event["task_id"])
    }
    if observed_task_ids != expected_task_ids:
        raise ActivationError("evidence export: readiness task identities are incomplete")
    for ordinal, service in enumerate(("checkout", "payments", "inventory")):
        task_id = f"{run_id}:readiness:{ordinal}"
        task_events = [
            event
            for event in events
            if event["task_id"] == task_id
            and event["event_type"] in {"task.started", "task.completed", "task.failed"}
        ]
        expected_result = "task.failed" if service in failed_services else "task.completed"
        if [event["event_type"] for event in task_events] != ["task.started", expected_result]:
            raise ActivationError("evidence export: readiness task result sequence is incomplete")
        attempt_id = f"{task_id}:attempt-1"
        if (
            task_events[0]["attempt_id"] != attempt_id
            or task_events[1]["attempt_id"] != attempt_id
            or int(task_events[0]["sequence"]) <= fanout_sequence
            or int(task_events[1]["sequence"]) <= int(task_events[0]["sequence"])
        ):
            raise ActivationError("evidence export: readiness task lineage is invalid")
        result_state = readiness[service]
        if not isinstance(result_state, dict) or result_state.get("service") != service:
            raise ActivationError("evidence export: readiness state service identity is invalid")
        if expected_result == "task.completed":
            if result_state != {"status": "ok", "service": service}:
                raise ActivationError("evidence export: healthy readiness state is invalid")
        elif (
            result_state.get("status") != "failed"
            or not isinstance(result_state.get("error_class"), str)
            or task_events[1]["failure_plane"] != service
            or task_events[1]["error_class"] != result_state.get("error_class")
            or task_events[1]["data"] != {"status": "failed", "disposition": "stop"}
        ):
            raise ActivationError("evidence export: failed readiness state is invalid")
        result_sequences.append(int(task_events[1]["sequence"]))
    join_type = "edge.join_satisfied" if require_healthy else "edge.join_starved"
    joins = [event for event in events if event["event_type"] == join_type]
    other_join = "edge.join_starved" if require_healthy else "edge.join_satisfied"
    if len(joins) != 1 or any(event["event_type"] == other_join for event in events):
        raise ActivationError("evidence export: readiness join evidence is invalid")
    expected_data = (
        {"branches": ["checkout", "payments", "inventory"]}
        if require_healthy
        else {"missing_branches": failed_services}
    )
    join_sequence = int(joins[0]["sequence"])
    if joins[0]["data"] != expected_data or join_sequence <= max(result_sequences):
        raise ActivationError("evidence export: readiness join result is invalid")
    return join_sequence


def _validate_approval_automaton(
    final_state: Mapping[str, object],
    events: Sequence[Mapping[str, object]],
    *,
    expected_decision: str,
    after_sequence: int,
) -> int:
    approval = final_state["approval"]
    if not isinstance(approval, dict):
        raise ActivationError("evidence export: approval state is invalid")
    request_id = approval.get("request_id")
    requests = [event for event in events if event["event_type"] == "approval.requested"]
    decisions = [
        event
        for event in events
        if event["event_type"]
        in {"approval.approved", "approval.rejected", "approval.timed_out"}
    ]
    if (
        len(requests) != 1
        or len(decisions) != 1
        or decisions[0]["event_type"] != expected_decision
        or requests[0]["data"]
        != {"request_id": request_id, "approval_status": "PENDING"}
        or int(requests[0]["sequence"]) <= after_sequence
        or int(decisions[0]["sequence"]) <= int(requests[0]["sequence"])
    ):
        raise ActivationError("evidence export: approval event sequence is invalid")
    expected_status = {
        "approval.approved": "APPROVED",
        "approval.rejected": "REJECTED",
        "approval.timed_out": "TIMED_OUT",
    }[expected_decision]
    expected_data: dict[str, object] = {
        "request_id": request_id,
        "approval_status": expected_status,
    }
    if expected_decision != "approval.timed_out":
        expected_data["actor_class"] = "fixture-operator"
    if decisions[0]["data"] != expected_data:
        raise ActivationError("evidence export: approval decision data is invalid")
    if (
        approval.get("status") != expected_status
        or approval.get("actor_class") != "fixture-operator"
        or approval.get("decision_time") != decisions[0]["time_utc"]
    ):
        raise ActivationError("evidence export: approval state disagrees with its decision event")
    return int(decisions[0]["sequence"])


def _reject_forbidden_no_effect_events(
    events: Sequence[Mapping[str, object]],
    allowed: set[str],
) -> None:
    run_id = str(events[0]["run_id"])
    allowed_task_ids = {f"{run_id}:readiness:{ordinal}" for ordinal in range(3)}
    for event in events:
        event_type = str(event["event_type"])
        if event_type.startswith("checkpoint."):
            continue
        if event_type not in allowed:
            raise ActivationError(
                f"evidence export: no-effect branch contains forbidden {event_type}"
            )
        if event_type.startswith("task.") and event["task_id"] not in allowed_task_ids:
            raise ActivationError(
                "evidence export: no-effect branch contains a non-readiness task"
            )


def _validate_no_effect_outcome(
    final_state: Mapping[str, object], events: Sequence[Mapping[str, object]]
) -> None:
    event_types = [event["event_type"] for event in events]
    approval = final_state["approval"]
    readiness = final_state["readiness"]
    cancellation = final_state["cancellation"]
    failure = final_state["failure"]
    branches = {
        "approval_rejected": isinstance(approval, dict) and approval.get("status") == "REJECTED",
        "approval_timed_out": isinstance(approval, dict) and approval.get("status") == "TIMED_OUT",
        "readiness_failed": isinstance(readiness, dict)
        and any(isinstance(item, dict) and item.get("status") != "ok" for item in readiness.values()),
        "cancelled": isinstance(cancellation, dict)
        and cancellation.get("state") in {"REQUESTED", "PROPAGATED", "ACKNOWLEDGED", "UNCONFIRMED"},
        "budget_exhausted": isinstance(failure, dict) and failure.get("error_class") == "budget_exhausted",
    }
    selected = [name for name, active in branches.items() if active]
    if len(selected) != 1:
        raise ActivationError("evidence export: exactly one no-effect terminal branch required")
    branch = selected[0]
    expected = {
        "approval_rejected": ("REJECTED", "approval.rejected"),
        "approval_timed_out": ("REJECTED", "approval.timed_out"),
        "readiness_failed": ("FAILED", "task.failed"),
        "cancelled": ("CANCELLED", None),
        "budget_exhausted": ("FAILED", "budget.exhausted"),
    }[branch]
    if final_state["outcome"] != expected[0] or (
        expected[1] is not None and expected[1] not in event_types
    ):
        raise ActivationError(f"evidence export: {branch} branch event or outcome mismatch")
    if branch == "cancelled" and not any(
        event_type in event_types
        for event_type in ("cancellation.acknowledged", "cancellation.unconfirmed")
    ):
        raise ActivationError("evidence export: cancellation terminal acknowledgement missing")
    if branch == "readiness_failed":
        _validate_readiness_automaton(final_state, events, require_healthy=False)
        if any(str(event["event_type"]).startswith("approval.") for event in events):
            raise ActivationError("evidence export: readiness failure contains approval events")
        _reject_forbidden_no_effect_events(
            events,
            {
                "run.accepted", "run.started", "run.terminal", "budget.observed",
                "edge.fanout_emitted", "edge.join_starved",
                "task.started", "task.completed", "task.failed",
            },
        )
    elif branch in {"approval_rejected", "approval_timed_out"}:
        join_sequence = _validate_readiness_automaton(
            final_state,
            events,
            require_healthy=True,
        )
        _validate_approval_automaton(
            final_state,
            events,
            expected_decision=(
                "approval.rejected"
                if branch == "approval_rejected"
                else "approval.timed_out"
            ),
            after_sequence=join_sequence,
        )
        _reject_forbidden_no_effect_events(
            events,
            {
                "run.accepted", "run.started", "run.terminal", "budget.observed",
                "edge.fanout_emitted", "edge.join_satisfied",
                "task.started", "task.completed", "approval.requested",
                (
                    "approval.rejected"
                    if branch == "approval_rejected"
                    else "approval.timed_out"
                ),
            },
        )
    elif branch == "cancelled":
        cancellation_events = [
            event
            for event in events
            if event["event_type"]
            in {
                "cancellation.requested",
                "cancellation.propagated",
                "cancellation.acknowledged",
                "cancellation.unconfirmed",
            }
        ]
        if [event["event_type"] for event in cancellation_events] not in (
            ["cancellation.requested", "cancellation.propagated", "cancellation.acknowledged"],
            ["cancellation.requested", "cancellation.propagated", "cancellation.unconfirmed"],
        ):
            raise ActivationError("evidence export: cancellation event sequence is invalid")
        request_id = cancellation.get("request_id") if isinstance(cancellation, dict) else None
        if (
            any(event["data"].get("request_id") != request_id for event in cancellation_events)
            or any(
                int(later["sequence"]) <= int(earlier["sequence"])
                for earlier, later in zip(cancellation_events, cancellation_events[1:])
            )
        ):
            raise ActivationError("evidence export: cancellation event lineage is invalid")
        expected_states = ["REQUESTED", "PROPAGATED", str(cancellation.get("state"))]
        if [event["data"].get("state") for event in cancellation_events] != expected_states:
            raise ActivationError("evidence export: cancellation event states are contradictory")
        terminal_cancellation = cancellation_events[-1]
        if cancellation.get("state") == "ACKNOWLEDGED":
            if (
                terminal_cancellation["event_type"] != "cancellation.acknowledged"
                or terminal_cancellation["data"].get("acknowledgement_ms")
                != cancellation.get("acknowledgement_ms")
                or not isinstance(cancellation.get("acknowledgement_ms"), int)
            ):
                raise ActivationError("evidence export: cancellation acknowledgement is invalid")
        elif (
            cancellation.get("state") != "UNCONFIRMED"
            or terminal_cancellation["event_type"] != "cancellation.unconfirmed"
            or cancellation.get("acknowledgement_ms") is not None
        ):
            raise ActivationError("evidence export: unconfirmed cancellation state is invalid")
        has_fanout = any(event["event_type"] == "edge.fanout_emitted" for event in events)
        if has_fanout:
            join_sequence = _validate_readiness_automaton(
                final_state,
                events,
                require_healthy=True,
            )
            requests = [event for event in events if event["event_type"] == "approval.requested"]
            if (
                len(requests) != 1
                or int(requests[0]["sequence"]) <= join_sequence
                or int(cancellation_events[0]["sequence"]) <= int(requests[0]["sequence"])
                or any(
                    event["event_type"]
                    in {"approval.approved", "approval.rejected", "approval.timed_out"}
                    for event in events
                )
            ):
                raise ActivationError("evidence export: approval-wait cancellation is invalid")
            allowed = {
                "run.accepted", "run.started", "run.cancelled", "budget.observed",
                "edge.fanout_emitted", "edge.join_satisfied",
                "task.started", "task.completed", "approval.requested",
                "cancellation.requested", "cancellation.propagated",
                str(terminal_cancellation["event_type"]),
            }
        elif any(
            event["event_type"].startswith(("edge.", "task.", "approval."))
            for event in events
        ):
            raise ActivationError("evidence export: admission cancellation contains scheduled work")
        else:
            allowed = {
                "run.accepted", "run.started", "run.cancelled", "budget.observed",
                "cancellation.requested", "cancellation.propagated",
                str(terminal_cancellation["event_type"]),
            }
        _reject_forbidden_no_effect_events(events, allowed)
    else:
        exhausted = [event for event in events if event["event_type"] == "budget.exhausted"]
        if len(exhausted) != 1:
            raise ActivationError("evidence export: budget exhaustion event is missing")
        exhausted_data = exhausted[0]["data"]
        if not isinstance(exhausted_data, dict):
            raise ActivationError("evidence export: budget exhaustion data is invalid")
        kind = exhausted_data.get("kind")
        budgets = final_state["budgets"]
        if not isinstance(kind, str) or not isinstance(budgets, dict) or kind not in budgets:
            raise ActivationError("evidence export: budget exhaustion kind is invalid")
        counter = budgets[kind]
        if (
            not isinstance(counter, dict)
            or set(counter) != {"limit", "consumed"}
            or exhausted_data
            != {
                "kind": kind,
                "limit": counter["limit"],
                "consumed": counter["consumed"],
                "remaining": 0,
            }
            or counter["consumed"] != counter["limit"]
        ):
            raise ActivationError("evidence export: budget exhaustion contradicts final counter")
        has_fanout = any(event["event_type"] == "edge.fanout_emitted" for event in events)
        approval_events = [
            event for event in events if str(event["event_type"]).startswith("approval.")
        ]
        if not has_fanout:
            if (
                kind != "wall_time_ms"
                or approval_events
                or any(":readiness:" in str(event["task_id"]) for event in events)
            ):
                raise ActivationError("evidence export: admission budget sequence is invalid")
            allowed = {
                "run.accepted", "run.started", "run.terminal",
                "budget.observed", "budget.exhausted",
            }
        else:
            join_sequence = _validate_readiness_automaton(
                final_state,
                events,
                require_healthy=True,
            )
            first_exhausted = min(int(event["sequence"]) for event in exhausted)
            if approval_events:
                approved_sequence = _validate_approval_automaton(
                    final_state,
                    events,
                    expected_decision="approval.approved",
                    after_sequence=join_sequence,
                )
                if first_exhausted <= approved_sequence or kind not in {
                    "attempts",
                    "wall_time_ms",
                }:
                    raise ActivationError("evidence export: effect-attempt budget sequence is invalid")
                allowed_approval = {"approval.requested", "approval.approved"}
            elif first_exhausted <= join_sequence or kind not in {"model_calls", "tokens"}:
                raise ActivationError("evidence export: planning budget sequence is invalid")
            else:
                allowed_approval = set()
            allowed = {
                "run.accepted", "run.started", "run.terminal",
                "budget.observed", "budget.exhausted",
                "edge.fanout_emitted", "edge.join_satisfied",
                "task.started", "task.completed",
                *allowed_approval,
            }
        _reject_forbidden_no_effect_events(events, allowed)


def _validate_effect_ledger(
    effects: Sequence[Mapping[str, object]],
    *,
    run_id: str,
) -> list[Mapping[str, object]]:
    if not effects:
        return []
    required = {
        "sequence", "effect_id", "task_id", "attempt_id", "replay_id",
        "idempotency_key", "payload_hash", "target", "effect_state",
        "time_utc", "reason_class", "receipt",
    }
    effect_id = f"{run_id}:checkout_effect:0:effect-checkout"
    task_id = f"{run_id}:checkout_effect:0"
    idempotency_key = _derive_parent_key(effect_id)
    allowed_transitions = {
        "PREPARED": {"DISPATCHED", "UNKNOWN"},
        "DISPATCHED": {"RECEIPT_RECORDED", "UNKNOWN"},
        "UNKNOWN": {"RECONCILED"},
        "RECEIPT_RECORDED": set(),
        "RECONCILED": set(),
    }
    previous_state: str | None = None
    payload_hash: object = None
    validated: list[Mapping[str, object]] = []
    for sequence, record in enumerate(effects, start=1):
        closed = _require_closed(record, required, f"effect ledger record[{sequence}]")
        state = closed["effect_state"]
        reason = closed["reason_class"]
        receipt = closed["receipt"]
        if (
            closed["sequence"] != sequence
            or closed["effect_id"] != effect_id
            or closed["task_id"] != task_id
            or not isinstance(closed["attempt_id"], str)
            or not re.fullmatch(
                rf"{re.escape(task_id)}:attempt-[1-9][0-9]*",
                closed["attempt_id"],
            )
            or closed["replay_id"] != f"{run_id}:replay-0"
            or closed["idempotency_key"] != idempotency_key
            or not isinstance(closed["payload_hash"], str)
            or not SHA256_RE.fullmatch(closed["payload_hash"])
            or closed["target"] != "checkout"
            or not isinstance(closed["time_utc"], str)
            or not RFC3339_UTC_RE.fullmatch(closed["time_utc"])
            or state not in allowed_transitions
        ):
            raise ActivationError("evidence export: effect ledger identity or schema mismatch")
        if payload_hash is None:
            payload_hash = closed["payload_hash"]
        elif closed["payload_hash"] != payload_hash:
            raise ActivationError("evidence export: effect payload identity changed")
        if previous_state is None:
            if state != "PREPARED":
                raise ActivationError("evidence export: effect ledger must start PREPARED")
        elif state not in allowed_transitions[previous_state]:
            raise ActivationError("evidence export: invalid effect ledger transition")
        if state in {"PREPARED", "DISPATCHED"}:
            if reason is not None or receipt is not None:
                raise ActivationError("evidence export: nonterminal effect row carries terminal data")
        elif state == "UNKNOWN":
            if (
                not isinstance(reason, str)
                or not ATOMIC_ID_RE.fullmatch(reason)
                or receipt is not None
            ):
                raise ActivationError("evidence export: UNKNOWN effect row lacks a bounded reason")
        elif reason is not None or not isinstance(receipt, dict):
            raise ActivationError("evidence export: completed effect row lacks its receipt")
        previous_state = str(state)
        validated.append(closed)
    return validated


def _validate_effect_event_agreement(
    effects: Sequence[Mapping[str, object]],
    events: Sequence[Mapping[str, object]],
    *,
    run_id: str,
) -> None:
    effect_id = f"{run_id}:checkout_effect:0:effect-checkout"
    event_type_by_state = {
        "PREPARED": "effect.prepared",
        "DISPATCHED": "effect.dispatched",
        "RECEIPT_RECORDED": "effect.receipt_recorded",
        "UNKNOWN": "effect.unknown",
        "RECONCILED": "effect.reconciled",
    }
    transition_types = set(event_type_by_state.values())
    transition_events = [
        event
        for event in events
        if event["event_type"] in transition_types
    ]
    all_effect_events = [event for event in events if str(event["event_type"]).startswith("effect.")]
    if not effects:
        if all_effect_events:
            raise ActivationError("evidence export: NOT_STARTED run contains effect events")
        return
    if any(event["effect_id"] != effect_id for event in all_effect_events):
        raise ActivationError("evidence export: boundary event names an unknown effect")
    expected_types = [event_type_by_state[str(record["effect_state"])] for record in effects]
    if [event["event_type"] for event in transition_events] != expected_types:
        raise ActivationError("evidence export: effect events disagree with durable ledger")
    for record, event in zip(effects, transition_events, strict=True):
        if (
            event["task_id"] != record["task_id"]
            or event["attempt_id"] != record["attempt_id"]
            or event["replay_id"] != record["replay_id"]
            or event["effect_id"] != record["effect_id"]
            or not isinstance(event["data"], dict)
            or event["data"].get("effect_state") != record["effect_state"]
        ):
            raise ActivationError("evidence export: effect event lineage disagrees with ledger")
        if record["effect_state"] == "UNKNOWN" and (
            event["data"].get("reason_class") != record["reason_class"]
        ):
            raise ActivationError("evidence export: UNKNOWN reason disagrees with ledger")
        if record["effect_state"] in {"RECEIPT_RECORDED", "RECONCILED"}:
            receipt = record["receipt"]
            if (
                not isinstance(receipt, dict)
                or event["data"].get("authoritative_result_id")
                != receipt.get("authoritative_result_id")
            ):
                raise ActivationError("evidence export: effect receipt event disagrees with ledger")


def _validate_runner_semantics(
    files: Mapping[str, Path],
    *,
    run_id: str,
    case_id: str,
    case_digest: str,
    source_revision: str,
    exit_code: int,
    runner_state: Mapping[str, object],
    snapshot_role: str | None = None,
) -> dict[str, object]:
    manifest = _require_closed(
        _load_evidence_json(files["manifest.json"], "manifest"),
        {
            "evidence_version",
            "contract_version",
            "sandbox_version",
            "source_revision",
            "run_id",
            "case_id",
            "case_digest",
            "thread_id",
            "outcome",
            "authoritative_result_id",
            "started_at",
            "ended_at",
            "artifacts",
        },
        "manifest",
    )
    expected_thread = f"{THREAD_PREFIX}{run_id}"
    if (
        manifest["evidence_version"] != "graph-evidence/v2"
        or manifest["contract_version"] != CONTRACT_VERSION
        or manifest["sandbox_version"] != "graph-sandbox/v1"
        or manifest["source_revision"] != source_revision
        or manifest["run_id"] != run_id
        or manifest["case_id"] != case_id
        or manifest["case_digest"] != case_digest
        or manifest["thread_id"] != expected_thread
        or not isinstance(manifest["started_at"], str)
        or not RFC3339_UTC_RE.fullmatch(manifest["started_at"])
        or not isinstance(manifest["ended_at"], str)
        or not RFC3339_UTC_RE.fullmatch(manifest["ended_at"])
        or manifest["started_at"] > manifest["ended_at"]
    ):
        raise ActivationError("evidence export: manifest lineage or timestamp mismatch")
    runner_artifacts = sorted(set(files) - {"manifest.json", "checksums.sha256"})
    if manifest["artifacts"] != runner_artifacts:
        raise ActivationError("evidence export: manifest artifact inventory mismatch")

    final_state = _require_closed(
        _load_evidence_json(files["final-state.json"], "final state"),
        {
            "contract_version",
            "state_schema",
            "run_id",
            "thread_id",
            "source_revision",
            "case_id",
            "case_digest",
            "replay_number",
            "phase",
            "outcome",
            "checkout",
            "checkout_status",
            "approval",
            "tasks",
            "receipts",
            "pending_effects",
            "readiness",
            "budgets",
            "cancellation",
            "failure",
        },
        "final state",
    )
    if (
        final_state["contract_version"] != CONTRACT_VERSION
        or final_state["state_schema"] != STATE_SCHEMA_VERSION
        or final_state["run_id"] != run_id
        or final_state["case_id"] != case_id
        or final_state["case_digest"] != case_digest
        or final_state["thread_id"] != expected_thread
        or final_state["source_revision"] != source_revision
        or final_state["phase"] != "TERMINAL"
        or not isinstance(final_state["pending_effects"], list)
        or manifest["outcome"] != final_state["outcome"]
        or not isinstance(final_state["checkout"], dict)
        or not isinstance(final_state["receipts"], dict)
    ):
        raise ActivationError("evidence export: final state lineage mismatch")
    if snapshot_role is not None and (
        snapshot_role not in {"UNKNOWN", "RECONCILED"}
        or (snapshot_role == "UNKNOWN" and final_state["outcome"] != "UNKNOWN")
        or (snapshot_role == "RECONCILED" and final_state["outcome"] != "SUCCEEDED")
    ):
        raise ActivationError("evidence export: reconciliation snapshot role mismatch")

    runtime = _validate_runtime_evidence(files)

    events = _validate_boundary_events(
        _load_evidence_jsonl(files["events.jsonl"], "boundary events"),
        run_id=run_id,
        case_id=case_id,
        case_digest=case_digest,
        source_revision=source_revision,
        outcome=final_state["outcome"],
    )
    lineage = _load_evidence_json(files["checkpoint-lineage.json"], "checkpoint lineage")
    _validate_checkpoint_oracle(
        lineage,
        events,
        run_id=run_id,
        source_revision=source_revision,
        runtime=runtime,
    )

    expected_runner_exit = 0 if snapshot_role is not None else exit_code
    if (
        set(runner_state) != {"Status", "ExitCode", "OOMKilled"}
        or runner_state["Status"] != "exited"
        or runner_state["ExitCode"] != expected_runner_exit
        or runner_state["OOMKilled"] is not False
    ):
        raise ActivationError("evidence export: runner container exit mismatch")

    effect_id = f"{run_id}:checkout_effect:0:effect-checkout"
    parent_key = _derive_parent_key(effect_id)
    effects = _validate_effect_ledger(
        _load_evidence_jsonl(files["effects.jsonl"], "effect ledger"),
        run_id=run_id,
    )
    _validate_effect_event_agreement(effects, events, run_id=run_id)
    approval = final_state["approval"]
    readiness = final_state["readiness"]
    cancellation = final_state["cancellation"]
    failure = final_state["failure"]
    no_effect_branch = (
        isinstance(approval, dict)
        and approval.get("status") in {"REJECTED", "TIMED_OUT"}
    ) or (
        isinstance(readiness, dict)
        and any(isinstance(item, dict) and item.get("status") != "ok" for item in readiness.values())
    ) or (
        isinstance(cancellation, dict)
        and cancellation.get("state") in {"REQUESTED", "PROPAGATED", "ACKNOWLEDGED", "UNCONFIRMED"}
    ) or (
        final_state["checkout_status"] == "NOT_STARTED"
        and isinstance(failure, dict)
        and failure.get("error_class") == "budget_exhausted"
    )
    if no_effect_branch:
        if (
            exit_code != 2
            or final_state["outcome"] == "SUCCEEDED"
            or final_state["checkout_status"] != "NOT_STARTED"
            or effects
            or final_state["receipts"]
            or final_state["pending_effects"]
            or manifest["authoritative_result_id"] is not None
            or any(name in files for name in ("receipts/payment.json", "receipts/inventory.json"))
        ):
            raise ActivationError("evidence export: no-effect terminal branch is inconsistent")
        _validate_no_effect_outcome(final_state, events)
        return manifest

    checkout_effects = [record for record in effects if record.get("effect_id") == effect_id]
    if not checkout_effects:
        raise ActivationError("evidence export: checkout effect ledger entry missing")
    final_effect = checkout_effects[-1]
    if final_effect["idempotency_key"] != parent_key:
        raise ActivationError("evidence export: checkout idempotency derivation mismatch")

    receipts = final_state["receipts"]
    checkout_receipt = receipts.get(effect_id)
    post_effect_budget_failure = (
        exit_code == 2
        and final_state["outcome"] == "FAILED"
        and final_state["checkout_status"] == "COMPLETE"
        and isinstance(failure, dict)
        and failure.get("error_class") == "budget_exhausted"
    )
    if exit_code == 0 or post_effect_budget_failure:
        _validate_success_controls(
            final_state,
            run_id,
            allow_completed_budget_failure=post_effect_budget_failure,
            reconciled_effect=final_effect["effect_state"] == "RECONCILED",
        )
        expected_outcome = "FAILED" if post_effect_budget_failure else "SUCCEEDED"
        if (
            manifest["outcome"] != expected_outcome
            or final_state["outcome"] != expected_outcome
            or final_state["checkout_status"] != "COMPLETE"
            or final_state["pending_effects"]
            or final_effect["effect_state"] not in {"RECEIPT_RECORDED", "RECONCILED"}
            or not isinstance(checkout_receipt, dict)
            or final_effect["receipt"] != checkout_receipt
            or (
                not post_effect_budget_failure
                and any(event["event_type"] == "budget.exhausted" for event in events)
            )
            or (
                post_effect_budget_failure
                and not any(event["event_type"] == "budget.exhausted" for event in events)
            )
        ):
            raise ActivationError("evidence export: completed checkout receipt missing or inconsistent")
        if snapshot_role == "RECONCILED" and final_effect["effect_state"] != "RECONCILED":
            raise ActivationError("evidence export: final reconciliation snapshot is not RECONCILED")
        checkout_receipt = _require_closed(
            checkout_receipt,
            {
                "authoritative_result_id", "order_id", "completion_class",
                "payment_receipt", "inventory_receipt", "replayed",
            },
            "checkout receipt",
        )
        order_id = final_state["checkout"].get("order_id")
        if (
            checkout_receipt["completion_class"] != "COMPLETE"
            or not isinstance(checkout_receipt["replayed"], bool)
            or not isinstance(checkout_receipt["authoritative_result_id"], str)
            or not ATOMIC_ID_RE.fullmatch(checkout_receipt["authoritative_result_id"])
            or manifest["authoritative_result_id"] != checkout_receipt["authoritative_result_id"]
            or checkout_receipt["order_id"] != order_id
            or not isinstance(order_id, str)
            or not ATOMIC_ID_RE.fullmatch(order_id)
        ):
            raise ActivationError("evidence export: authoritative result or order mismatch")
        for effect_class in ("payment", "inventory"):
            relative = f"receipts/{effect_class}.json"
            if relative not in files:
                raise ActivationError(f"evidence export: completed checkout lacks {relative}")
            nested = _validate_target_receipt(
                checkout_receipt[f"{effect_class}_receipt"],
                effect_class,
                _derive_child_key(parent_key, effect_class),
            )
            exported = _validate_target_receipt(
                _load_evidence_json(files[relative], f"{effect_class} receipt"),
                effect_class,
                _derive_child_key(parent_key, effect_class),
            )
            if exported != nested:
                raise ActivationError(f"evidence export: {effect_class} receipt does not match checkout")
    elif exit_code == 2:
        if (
            manifest["outcome"] not in {"FAILED", "CANCELLED", "REJECTED", "INCONCLUSIVE", "UNKNOWN"}
            or final_state["outcome"] == "SUCCEEDED"
            or manifest["authoritative_result_id"] is not None
            or checkout_receipt is not None
            or (
                final_effect["effect_state"] in {"RECEIPT_RECORDED", "RECONCILED"}
                and isinstance(final_effect["receipt"], dict)
                and final_effect["receipt"].get("completion_class") == "COMPLETE"
            )
        ):
            raise ActivationError("evidence export: non-success contains false-success receipt")
        if final_state["outcome"] == "UNKNOWN" and (
            final_state["checkout_status"] != "UNKNOWN"
            or checkout_receipt is not None
            or final_effect["effect_state"] not in {"UNKNOWN", "REPLAY_REFUSED"}
            or not any(
                event["event_type"] == "effect.replay_refused"
                and event["effect_id"] == effect_id
                for event in events
            )
        ):
            raise ActivationError("evidence export: UNKNOWN effect evidence is unsafe")
        for effect_class in ("payment", "inventory"):
            relative = f"receipts/{effect_class}.json"
            if relative in files:
                exported = _validate_target_receipt(
                    _load_evidence_json(files[relative], f"{effect_class} receipt"),
                    effect_class,
                    _derive_child_key(parent_key, effect_class),
                )
                target_effect_id = f"{run_id}:checkout_effect:0:effect-{effect_class}"
                if receipts.get(target_effect_id) != exported:
                    raise ActivationError(
                        f"evidence export: {effect_class} receipt does not match final state"
                    )
    else:
        raise ActivationError("evidence export: exit is not terminal-with-evidence")
    return manifest


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _command_record(phase: str, command: Sequence[str], exit_status: int) -> dict[str, object]:
    return {
        "command_version": "graph-sandbox-command/v1",
        "phase": phase,
        "command": list(command),
        "time_utc": _utc_now(),
        "exit_status": exit_status,
    }


def _command_is_sanitized(phase: object, command: list[object]) -> bool:
    if phase == "activation":
        return command in (
            ["python", "graph-sandbox/activate.py", "fresh"],
            ["python", "graph-sandbox/activate.py", "resume"],
        )
    if len(command) < 3 or command[:2] != ["docker", "--context"]:
        return False
    context = command[2]
    if not isinstance(context, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}", context):
        return False
    expected = {
        "preflight": ["docker", "--context", context, "compose", "config"],
        "up": ["docker", "--context", context, "compose", "up"],
        "export": ["docker", "--context", context, "container", "cp"],
        "teardown": ["docker", "--context", context, "compose", "down", "--volumes"],
    }
    return command == expected.get(phase)


def _command_payload(records: Sequence[Mapping[str, object]]) -> bytes:
    required = {"command_version", "phase", "command", "time_utc", "exit_status"}
    normalized: list[str] = []
    for record in records:
        closed = _require_closed(dict(record), required, "command record")
        if (
            closed["command_version"] != "graph-sandbox-command/v1"
            or closed["phase"] not in {"activation", "preflight", "up", "export", "teardown"}
            or not isinstance(closed["command"], list)
            or not closed["command"]
            or not all(
                isinstance(part, str)
                and part
                and "=" not in part
                and "\n" not in part
                and "\r" not in part
                for part in closed["command"]
            )
            or not _command_is_sanitized(closed["phase"], closed["command"])
            or not isinstance(closed["time_utc"], str)
            or not RFC3339_UTC_RE.fullmatch(closed["time_utc"])
            or isinstance(closed["exit_status"], bool)
            or not isinstance(closed["exit_status"], int)
        ):
            raise ActivationError("evidence export: command record schema mismatch")
        normalized.append(json.dumps(closed, sort_keys=True, separators=(",", ":")))
    if not normalized:
        raise ActivationError("evidence export: commands journal is empty")
    return ("\n".join(normalized) + "\n").encode("utf-8")


def _write_host_evidence(
    run_dir: Path,
    *,
    manifest: dict[str, object],
    validated_compose: bytes,
    verification: Mapping[str, object],
    exit_code: int,
    source_revision: str,
    run_id: str,
    commands: Sequence[Mapping[str, object]],
    snapshot_role: str | None = None,
) -> None:
    required_verification = {
        "docker_context",
        "docker_context_fingerprint",
        "docker_engine_version",
        "docker_compose_version",
        "docker_platform",
        "project",
        "base_image_digest",
        "runner_image_id",
        "services_image_id",
        "runner_container_exit",
    }
    if set(verification) != required_verification:
        raise ActivationError("evidence export: host verification schema mismatch")
    for field in (
        "docker_context",
        "docker_engine_version",
        "docker_compose_version",
        "docker_platform",
        "project",
    ):
        if not isinstance(verification[field], str) or not verification[field]:
            raise ActivationError(f"evidence export: host verification {field} missing")
    expected_runner_exit = 0 if snapshot_role is not None else exit_code
    if (
        not isinstance(verification["docker_context_fingerprint"], str)
        or not SHA256_RE.fullmatch(verification["docker_context_fingerprint"])
        or not isinstance(verification["base_image_digest"], str)
        or not re.fullmatch(r"sha256:[0-9a-f]{64}", verification["base_image_digest"])
        or not isinstance(verification["runner_image_id"], str)
        or not re.fullmatch(r"sha256:[0-9a-f]{64}", verification["runner_image_id"])
        or not isinstance(verification["services_image_id"], str)
        or not re.fullmatch(r"sha256:[0-9a-f]{64}", verification["services_image_id"])
        or verification["runner_container_exit"]
        != {"Status": "exited", "ExitCode": expected_runner_exit, "OOMKilled": False}
    ):
        raise ActivationError("evidence export: host verification values mismatch")
    if snapshot_role is not None and snapshot_role not in {"UNKNOWN", "RECONCILED"}:
        raise ActivationError("evidence export: invalid reconciliation snapshot role")
    _atomic_write(run_dir / "commands.jsonl", _command_payload(commands))
    _atomic_write(run_dir / "compose-config.json", validated_compose)
    runtime = _validate_runtime_evidence({"runtime.json": run_dir / "runtime.json"})
    packages = runtime["packages"]
    python_runtime_posture = f"observed:{runtime['python_version']}"
    package_posture = {
        name: f"observed:{version}"
        for name, version in packages.items()
    }
    verification_payload = {
        "verification_version": (
            "graph-sandbox-host-verification/v2"
            if snapshot_role is not None
            else "graph-sandbox-host-verification/v1"
        ),
        "run_id": run_id,
        "source_revision": source_revision,
        "exit_code": exit_code,
        "validated_compose_sha256": hashlib.sha256(validated_compose).hexdigest(),
        "python_runtime_posture": python_runtime_posture,
        "package_posture": package_posture,
        **dict(verification),
    }
    if snapshot_role is not None:
        verification_payload["snapshot_role"] = snapshot_role
    _atomic_write(
        run_dir / "verification.json",
        (json.dumps(verification_payload, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    environment_payload = {
        "environment_version": (
            "graph-sandbox-host-environment/v2"
            if snapshot_role is not None
            else "graph-sandbox-host-environment/v1"
        ),
        "run_id": run_id,
        "source_revision": source_revision,
        "python_runtime_posture": python_runtime_posture,
        "package_posture": package_posture,
        **dict(verification),
    }
    if snapshot_role is not None:
        environment_payload["snapshot_role"] = snapshot_role
    _atomic_write(
        run_dir / "environment.json",
        (json.dumps(environment_payload, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    artifacts = sorted(
        path.relative_to(run_dir).as_posix()
        for path in run_dir.rglob("*")
        if path.is_file() and path.name not in {"manifest.json", "checksums.sha256"}
    )
    manifest["artifacts"] = artifacts
    _atomic_write(
        run_dir / "manifest.json",
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    checksum_lines = []
    for path in sorted(run_dir.rglob("*")):
        if path.is_file() and path.name != "checksums.sha256":
            relative = path.relative_to(run_dir).as_posix()
            checksum_lines.append(f"{_sha256_file(path)}  {relative}\n")
    _atomic_write(run_dir / "checksums.sha256", "".join(checksum_lines).encode("ascii"))


def _validated_staged_run(
    staging: Path,
    *,
    evidence_root: Path,
    run_id: str,
    case_id: str,
    case_digest: str,
    source_revision: str,
    exit_code: int,
    runner_state: Mapping[str, object] | None = None,
    max_bytes: int = MAX_EVIDENCE_BYTES,
    directory_name: str | None = None,
    allow_siblings: bool = False,
    snapshot_role: str | None = None,
) -> tuple[Path, Path, Path, dict[str, object]]:

    _reject_path_indirection(evidence_root)
    root = evidence_root.resolve(strict=True)
    staging_absolute = Path(os.path.abspath(staging))
    if staging_absolute.parent != Path(os.path.abspath(root)) or not staging_absolute.name.startswith("."):
        raise ActivationError("evidence export: staging path must be an exclusive root child")
    _reject_path_indirection(staging_absolute)
    run_dir = staging_absolute / (run_id if directory_name is None else directory_name)
    if (
        (not allow_siblings and set(staging_absolute.iterdir()) != {run_dir})
        or not run_dir.is_dir()
    ):
        raise ActivationError("evidence export: unexpected top-level path")
    _reject_path_indirection(run_dir)
    files = _evidence_files(run_dir, max_bytes=max_bytes)
    missing = REQUIRED_RUNNER_EVIDENCE - set(files)
    if missing:
        raise ActivationError(f"evidence export: missing required artifact {sorted(missing)[0]}")
    _verify_existing_checksums(files)
    state = (
        {"Status": "exited", "ExitCode": exit_code, "OOMKilled": False}
        if runner_state is None
        else runner_state
    )
    manifest = _validate_runner_semantics(
        files,
        run_id=run_id,
        case_id=case_id,
        case_digest=case_digest,
        source_revision=source_revision,
        exit_code=exit_code,
        runner_state=state,
        snapshot_role=snapshot_role,
    )
    return root, staging_absolute, run_dir, manifest


def _publish_staged_run(
    root: Path,
    staging: Path,
    run_dir: Path,
    *,
    manifest: dict[str, object],
    validated_compose: bytes,
    verification: Mapping[str, object],
    exit_code: int,
    source_revision: str,
    run_id: str,
    commands: Sequence[Mapping[str, object]],
    max_bytes: int,
) -> Path:
    _write_host_evidence(
        run_dir,
        manifest=manifest,
        validated_compose=validated_compose,
        verification=verification,
        exit_code=exit_code,
        source_revision=source_revision,
        run_id=run_id,
        commands=commands,
    )
    final_files = _evidence_files(run_dir, max_bytes=max_bytes)
    _verify_existing_checksums(final_files)
    final = root / run_id
    if final.exists() or _is_link_or_junction(final):
        raise ActivationError("evidence export: final run path already exists")
    os.replace(run_dir, final)
    staging.rmdir()
    if os.name != "nt":
        descriptor = os.open(root, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    return final


def _publish_staged_timeline(
    root: Path,
    staging: Path,
    *,
    run_id: str,
    source_revision: str,
    validated_compose: bytes,
    verification: Mapping[str, object],
    commands: Sequence[Mapping[str, object]],
    bundles: Mapping[str, tuple[Path, dict[str, object]]],
    max_bytes: int,
) -> tuple[Path, Path]:
    """Atomically publish the verified UNKNOWN and RECONCILED bundle pair."""

    if set(bundles) != {"UNKNOWN", "RECONCILED"}:
        raise ActivationError("evidence export: reconciliation timeline is incomplete")
    semantic_exits = {"UNKNOWN": 2, "RECONCILED": 0}
    published_children: dict[str, Path] = {}
    for role, child_name in (("UNKNOWN", "unknown"), ("RECONCILED", "reconciled")):
        run_dir, manifest = bundles[role]
        _write_host_evidence(
            run_dir,
            manifest=manifest,
            validated_compose=validated_compose,
            verification=verification,
            exit_code=semantic_exits[role],
            source_revision=source_revision,
            run_id=run_id,
            commands=commands,
            snapshot_role=role,
        )
        final_files = _evidence_files(run_dir, max_bytes=max_bytes)
        _verify_existing_checksums(final_files)
        child = staging / child_name
        if child.exists() or _is_link_or_junction(child):
            raise ActivationError("evidence export: timeline child already exists")
        os.replace(run_dir, child)
        published_children[role] = child

    final = root / run_id
    if final.exists() or _is_link_or_junction(final):
        raise ActivationError("evidence export: final run path already exists")
    if set(staging.iterdir()) != set(published_children.values()):
        raise ActivationError("evidence export: unexpected timeline staging content")
    os.replace(staging, final)
    if os.name != "nt":
        descriptor = os.open(root, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    return final / "unknown", final / "reconciled"


def _validate_reconciliation_pair(
    unknown_dir: Path,
    reconciled_dir: Path,
    unknown_manifest: Mapping[str, object],
    reconciled_manifest: Mapping[str, object],
) -> None:
    """Prove that two valid bundles are one monotonic same-effect timeline."""

    immutable = ("run_id", "case_id", "case_digest", "source_revision", "thread_id", "started_at")
    if any(unknown_manifest.get(key) != reconciled_manifest.get(key) for key in immutable):
        raise ActivationError("evidence export: reconciliation snapshots disagree on identity")
    if (
        unknown_manifest.get("outcome") != "UNKNOWN"
        or reconciled_manifest.get("outcome") != "SUCCEEDED"
        or not isinstance(unknown_manifest.get("ended_at"), str)
        or not isinstance(reconciled_manifest.get("ended_at"), str)
        or str(unknown_manifest["ended_at"]) >= str(reconciled_manifest["ended_at"])
    ):
        raise ActivationError("evidence export: reconciliation snapshots are not ordered")

    unknown_events = _load_evidence_jsonl(unknown_dir / "events.jsonl", "UNKNOWN events")
    reconciled_events = _load_evidence_jsonl(
        reconciled_dir / "events.jsonl",
        "RECONCILED events",
    )
    if (
        len(reconciled_events) <= len(unknown_events)
        or unknown_events[:-1] != reconciled_events[: len(unknown_events) - 1]
    ):
        raise ActivationError("evidence export: reconciled event history does not extend UNKNOWN")

    unknown_effects = _load_evidence_jsonl(unknown_dir / "effects.jsonl", "UNKNOWN effects")
    reconciled_effects = _load_evidence_jsonl(
        reconciled_dir / "effects.jsonl",
        "RECONCILED effects",
    )
    if (
        not unknown_effects
        or len(reconciled_effects) <= len(unknown_effects)
        or unknown_effects != reconciled_effects[: len(unknown_effects)]
        or unknown_effects[-1].get("effect_state") != "UNKNOWN"
        or reconciled_effects[-1].get("effect_state") != "RECONCILED"
        or unknown_effects[-1].get("effect_id") != reconciled_effects[-1].get("effect_id")
    ):
        raise ActivationError("evidence export: reconciled effect history does not extend UNKNOWN")


def _requires_reconciliation_timeline(
    sandbox_case: object,
    approval_fixture: str,
) -> bool:
    service_fixtures = getattr(sandbox_case, "service_fixtures", {})
    return (
        approval_fixture == "APPROVED"
        and isinstance(service_fixtures, Mapping)
        and isinstance(service_fixtures.get("checkout"), Mapping)
        and service_fixtures["checkout"].get("effect") == "ambiguous_after_commit"
    )


def verify_and_publish_evidence(
    staging: Path,
    *,
    evidence_root: Path,
    run_id: str,
    source_revision: str,
    case_id: str = "mission-healthy-001",
    case_digest: str = "74266b9c39a7733128e25f7279bb18820664bfbd6c11d8b0a6a3fa5e53a685d1",
    exit_code: int,
    validated_compose: bytes,
    verification: Mapping[str, object],
    commands: Sequence[Mapping[str, object]] | None = None,
    runner_state: Mapping[str, object] | None = None,
    max_bytes: int = MAX_EVIDENCE_BYTES,
) -> Path:
    """Verify a Docker-copied evidence tree and atomically publish its run directory."""

    root, staging_absolute, run_dir, manifest = _validated_staged_run(
        staging,
        evidence_root=evidence_root,
        run_id=run_id,
        case_id=case_id,
        case_digest=case_digest,
        source_revision=source_revision,
        exit_code=exit_code,
        runner_state=runner_state,
        max_bytes=max_bytes,
    )
    if commands is None:
        raise ActivationError("evidence export: observed command journal is required")
    journal = list(commands)

    host_verification = dict(verification)
    host_verification.setdefault(
        "runner_container_exit",
        {"Status": "exited", "ExitCode": exit_code, "OOMKilled": False},
    )
    return _publish_staged_run(
        root,
        staging_absolute,
        run_dir,
        manifest=manifest,
        validated_compose=validated_compose,
        verification=host_verification,
        exit_code=exit_code,
        source_revision=source_revision,
        run_id=run_id,
        commands=journal,
        max_bytes=max_bytes,
    )


def _validate_published_bundle(
    bundle: Path,
    *,
    run_id: str,
    case_id: str,
    case_digest: str,
    source_revision: str,
    compose_digest: str,
    context_fingerprint: str,
    snapshot_role: str | None,
    max_bytes: int,
) -> None:
    _reject_path_indirection(bundle)
    if not bundle.is_dir():
        raise ActivationError("evidence recovery: final bundle is unavailable")
    files = _evidence_files(bundle, max_bytes=max_bytes)
    required_host_files = {
        "commands.jsonl",
        "compose-config.json",
        "environment.json",
        "verification.json",
    }
    missing = (REQUIRED_RUNNER_EVIDENCE | required_host_files) - set(files)
    if missing:
        raise ActivationError(
            f"evidence recovery: missing required artifact {sorted(missing)[0]}"
        )
    _verify_existing_checksums(files)
    if hashlib.sha256(files["compose-config.json"].read_bytes()).hexdigest() != compose_digest:
        raise ActivationError("evidence recovery: validated Compose digest mismatch")

    verification = _load_evidence_json(files["verification.json"], "host verification")
    exit_code = verification.get("exit_code")
    runner_state = verification.get("runner_container_exit")
    expected_verification_version = (
        "graph-sandbox-host-verification/v2"
        if snapshot_role is not None
        else "graph-sandbox-host-verification/v1"
    )
    if (
        verification.get("verification_version") != expected_verification_version
        or verification.get("run_id") != run_id
        or verification.get("source_revision") != source_revision
        or verification.get("validated_compose_sha256") != compose_digest
        or verification.get("docker_context_fingerprint") != context_fingerprint
        or verification.get("snapshot_role") != snapshot_role
        or isinstance(exit_code, bool)
        or not isinstance(exit_code, int)
        or exit_code not in TERMINAL_EVIDENCE_EXITS
        or not isinstance(runner_state, dict)
    ):
        raise ActivationError("evidence recovery: host verification identity mismatch")
    _validate_runner_semantics(
        files,
        run_id=run_id,
        case_id=case_id,
        case_digest=case_digest,
        source_revision=source_revision,
        exit_code=exit_code,
        runner_state=runner_state,
        snapshot_role=snapshot_role,
    )
    commands = _load_evidence_jsonl(files["commands.jsonl"], "commands journal")
    if files["commands.jsonl"].read_bytes() != _command_payload(commands):
        raise ActivationError("evidence recovery: commands journal is not canonical")
    environment = _load_evidence_json(files["environment.json"], "host environment")
    expected_environment_version = (
        "graph-sandbox-host-environment/v2"
        if snapshot_role is not None
        else "graph-sandbox-host-environment/v1"
    )
    if (
        environment.get("environment_version") != expected_environment_version
        or environment.get("run_id") != run_id
        or environment.get("source_revision") != source_revision
        or environment.get("snapshot_role") != snapshot_role
    ):
        raise ActivationError("evidence recovery: host environment identity mismatch")


def _validate_published_run(
    final: Path,
    *,
    evidence_root: Path,
    run_id: str,
    case_id: str,
    case_digest: str,
    source_revision: str,
    compose_digest: str,
    context_fingerprint: str,
    reconciliation_timeline: bool = False,
    max_bytes: int = MAX_EVIDENCE_BYTES,
) -> Path:
    """Validate an already-installed final directory before crash recovery."""

    _reject_path_indirection(evidence_root)
    root = evidence_root.resolve(strict=True)
    expected = root / run_id
    if Path(os.path.abspath(final)) != Path(os.path.abspath(expected)):
        raise ActivationError("evidence recovery: final run path identity mismatch")
    _reject_path_indirection(expected)
    if not expected.is_dir():
        raise ActivationError("evidence recovery: final run directory is unavailable")
    if reconciliation_timeline:
        children = {expected / "unknown", expected / "reconciled"}
        if set(expected.iterdir()) != children:
            raise ActivationError("evidence recovery: reconciliation timeline is incomplete")
        manifests: dict[str, dict[str, object]] = {}
        dirs: dict[str, Path] = {}
        for role, child in (("UNKNOWN", expected / "unknown"), ("RECONCILED", expected / "reconciled")):
            _validate_published_bundle(
                child,
                run_id=run_id,
                case_id=case_id,
                case_digest=case_digest,
                source_revision=source_revision,
                compose_digest=compose_digest,
                context_fingerprint=context_fingerprint,
                snapshot_role=role,
                max_bytes=max_bytes,
            )
            manifests[role] = _load_evidence_json(child / "manifest.json", f"{role} manifest")
            dirs[role] = child
        _validate_reconciliation_pair(
            dirs["UNKNOWN"],
            dirs["RECONCILED"],
            manifests["UNKNOWN"],
            manifests["RECONCILED"],
        )
    else:
        _validate_published_bundle(
            expected,
            run_id=run_id,
            case_id=case_id,
            case_digest=case_digest,
            source_revision=source_revision,
            compose_digest=compose_digest,
            context_fingerprint=context_fingerprint,
            snapshot_role=None,
            max_bytes=max_bytes,
        )
    return expected


def _refresh_published_commands(
    final: Path, commands: Sequence[Mapping[str, object]]
) -> None:
    _atomic_write(final / "commands.jsonl", _command_payload(commands))
    checksum_lines = []
    for path in sorted(final.rglob("*")):
        if path.is_file() and path.name != "checksums.sha256":
            relative = path.relative_to(final).as_posix()
            checksum_lines.append(f"{_sha256_file(path)}  {relative}\n")
    _atomic_write(final / "checksums.sha256", "".join(checksum_lines).encode("ascii"))


def execute_validated_compose(
    validated_bytes: bytes,
    *,
    docker_context: str,
    project_name: str,
    evidence_root: Path,
    run_id: str,
    source_revision: str,
    case_id: str = "mission-healthy-001",
    case_digest: str = "74266b9c39a7733128e25f7279bb18820664bfbd6c11d8b0a6a3fa5e53a685d1",
    verification: Mapping[str, object],
    runner=run_process,
    environment: Mapping[str, str],
    revalidate: Callable[[], None],
    temp_parent: Path | None = None,
    before_launch: Callable[[Path], None] | None = None,
    on_launch: Callable[[], None] | None = None,
    on_publish: Callable[[], None] | None = None,
    on_preserve: Callable[[], None] | None = None,
    commands: Sequence[Mapping[str, object]] | None = None,
    reconciliation_timeline: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Execute one validated model; every post-launch fault enters one preservation funnel."""

    parent = None if temp_parent is None else str(temp_parent)
    temporary_root = Path(tempfile.mkdtemp(prefix="graph-sandbox-activate-", dir=parent))
    os.chmod(temporary_root, 0o700)
    compose_path = temporary_root / f"runtime-{secrets.token_hex(16)}.json"
    expected_digest = hashlib.sha256(validated_bytes).digest()
    command = [
        "docker", "--context", docker_context, "compose", "--file", str(compose_path),
        "--project-name", project_name, "up", "--abort-on-container-exit",
        "--exit-code-from", "graph-runner", "--no-build", "--pull", "never",
    ]
    launch_environment = scrub_environment(environment)
    launched = False
    journal = list(commands or ())

    def assert_exact_compose() -> None:
        if (
            _is_link_or_junction(compose_path)
            or hashlib.sha256(compose_path.read_bytes()).digest() != expected_digest
        ):
            raise ActivationError("validated Compose bytes changed during lifecycle")

    def assert_lifecycle_identity() -> None:
        assert_exact_compose()
        revalidate()
        assert_exact_compose()

    def compose_action(action: str, *, volumes: bool = False) -> subprocess.CompletedProcess[str]:
        assert_lifecycle_identity()
        arguments = [
            "docker", "--context", docker_context, "compose", "--file", str(compose_path),
            "--project-name", project_name, action,
        ]
        if action == "stop":
            arguments.extend(("--timeout", "10"))
        elif action == "down":
            if volumes:
                arguments.append("--volumes")
            arguments.extend(("--remove-orphans", "--timeout", "10"))
        return runner(
            arguments,
            environment=launch_environment,
            timeout_seconds=120,
            stdin=None,
        )

    def preserve(host_exit: int, status: str) -> subprocess.CompletedProcess[str]:
        stop_succeeded = False
        try:
            stopped = compose_action("stop")
            stop_succeeded = stopped.returncode == 0
        except BaseException:
            pass
        try:
            if on_preserve is not None:
                on_preserve()
        except BaseException:
            return subprocess.CompletedProcess(
                command,
                HOST_PRESERVATION_FAILURE_EXIT,
                stdout="",
                stderr="preservation resource subset unverified; resources retained fail-safe",
            )
        if not stop_succeeded:
            return subprocess.CompletedProcess(
                command,
                HOST_PRESERVATION_FAILURE_EXIT,
                stdout="",
                stderr="preservation stop outcome unknown; resources retained fail-safe",
            )
        return subprocess.CompletedProcess(command, host_exit, stdout="", stderr=status)

    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(compose_path, flags, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(validated_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        if before_launch is not None:
            before_launch(compose_path)
        assert_lifecycle_identity()

        try:
            if on_launch is not None:
                on_launch()
            launched = True
            result = runner(
                command,
                environment=launch_environment,
                timeout_seconds=960,
                stdin=None,
            )
        except (CommandTimeoutError, subprocess.TimeoutExpired):
            return preserve(HOST_TIMEOUT_EXIT, "activation timed out; resources preserved")
        except KeyboardInterrupt:
            return preserve(HOST_INTERRUPT_EXIT, "activation interrupted; resources preserved")
        except BaseException:
            return preserve(HOST_INCONCLUSIVE_EXIT, "activation call failed; resources preserved")

        journal.append(
            _command_record("up", ["docker", "--context", docker_context, "compose", "up"], result.returncode)
        )
        if result.returncode not in TERMINAL_EVIDENCE_EXITS | {TERMINAL_REJECTION_EXIT}:
            return preserve(HOST_INCONCLUSIVE_EXIT, "activation exited nonterminal; resources preserved")

        if result.returncode == TERMINAL_REJECTION_EXIT:
            try:
                down = compose_action("down", volumes=True)
            except BaseException:
                return preserve(HOST_INCONCLUSIVE_EXIT, "terminal rejection cleanup failed; resources preserved")
            if down.returncode != 0:
                return preserve(HOST_INCONCLUSIVE_EXIT, "terminal rejection cleanup failed; resources preserved")
            return result

        try:
            assert_lifecycle_identity()
            located = runner(
                [
                    "docker", "--context", docker_context, "compose", "--file", str(compose_path),
                    "--project-name", project_name, "ps", "--all", "-q", "graph-runner",
                ],
                environment=launch_environment,
                timeout_seconds=30,
                stdin=None,
            )
            container_id = str(located.stdout).strip()
            if located.returncode != 0 or not CONTAINER_ID_RE.fullmatch(container_id):
                raise ActivationError("evidence export: graph-runner container identity unavailable")
            assert_lifecycle_identity()
            inspected = runner(
                [
                    "docker", "--context", docker_context, "container", "inspect",
                    "--format", "{{json .State}}", container_id,
                ],
                environment=launch_environment,
                timeout_seconds=30,
                stdin=None,
            )
            raw_runner_state = json.loads(str(inspected.stdout))
            if inspected.returncode != 0 or not isinstance(raw_runner_state, dict):
                raise ActivationError("evidence export: runner container state unavailable")
            runner_state = {
                "Status": raw_runner_state.get("Status"),
                "ExitCode": raw_runner_state.get("ExitCode"),
                "OOMKilled": raw_runner_state.get("OOMKilled"),
            }
            root = evidence_root.resolve(strict=True)
            staging = root / f".{run_id}.{secrets.token_hex(16)}.export"
            staging.mkdir(mode=0o700)
            assert_lifecycle_identity()
            copied = runner(
                [
                    "docker", "--context", docker_context, "container", "cp",
                    f"{container_id}:/evidence/.", str(staging),
                ],
                environment=launch_environment,
                timeout_seconds=120,
                stdin=None,
            )
            if copied.returncode != 0:
                raise ActivationError(f"evidence export failed with exit {copied.returncode}")
            journal.append(
                _command_record("export", ["docker", "--context", docker_context, "container", "cp"], copied.returncode)
            )
            final_verification = {**dict(verification), "runner_container_exit": dict(runner_state)}
            if reconciliation_timeline:
                if result.returncode != 0:
                    raise ActivationError(
                        "evidence export: reconciliation timeline did not complete"
                    )
                names = {
                    "UNKNOWN": f"{run_id}-unknown",
                    "RECONCILED": f"{run_id}-reconciled",
                }
                if set(staging.iterdir()) != {
                    staging / names["UNKNOWN"],
                    staging / names["RECONCILED"],
                }:
                    raise ActivationError(
                        "evidence export: reconciliation timeline top-level paths mismatch"
                    )
                bundles: dict[str, tuple[Path, dict[str, object]]] = {}
                for role, semantic_exit in (("UNKNOWN", 2), ("RECONCILED", 0)):
                    root, staging, run_dir, manifest = _validated_staged_run(
                        staging,
                        evidence_root=root,
                        run_id=run_id,
                        case_id=case_id,
                        case_digest=case_digest,
                        source_revision=source_revision,
                        exit_code=semantic_exit,
                        runner_state=runner_state,
                        directory_name=names[role],
                        allow_siblings=True,
                        snapshot_role=role,
                    )
                    bundles[role] = (run_dir, manifest)
                _validate_reconciliation_pair(
                    bundles["UNKNOWN"][0],
                    bundles["RECONCILED"][0],
                    bundles["UNKNOWN"][1],
                    bundles["RECONCILED"][1],
                )
                published_dirs = _publish_staged_timeline(
                    root,
                    staging,
                    run_id=run_id,
                    source_revision=source_revision,
                    validated_compose=validated_bytes,
                    verification=final_verification,
                    commands=journal,
                    bundles=bundles,
                    max_bytes=MAX_EVIDENCE_BYTES,
                )
                final = root / run_id
            else:
                root, staging, run_dir, manifest = _validated_staged_run(
                    staging,
                    evidence_root=root,
                    run_id=run_id,
                    case_id=case_id,
                    case_digest=case_digest,
                    source_revision=source_revision,
                    exit_code=result.returncode,
                    runner_state=runner_state,
                )
                final = _publish_staged_run(
                    root,
                    staging,
                    run_dir,
                    manifest=manifest,
                    validated_compose=validated_bytes,
                    verification=final_verification,
                    exit_code=result.returncode,
                    source_revision=source_revision,
                    run_id=run_id,
                    commands=journal,
                    max_bytes=MAX_EVIDENCE_BYTES,
                )
                published_dirs = (final,)
            if on_publish is not None:
                on_publish()
        except BaseException:
            return preserve(HOST_INCONCLUSIVE_EXIT, "post-launch evidence fault; resources preserved")

        try:
            down = compose_action("down", volumes=True)
            journal.append(
                _command_record(
                    "teardown",
                    ["docker", "--context", docker_context, "compose", "down", "--volumes"],
                    down.returncode,
                )
            )
            for published_dir in published_dirs:
                _refresh_published_commands(published_dir, journal)
        except BaseException:
            return preserve(HOST_INCONCLUSIVE_EXIT, "published run cleanup failed; resources preserved")
        if down.returncode != 0:
            return preserve(HOST_INCONCLUSIVE_EXIT, "published run cleanup failed; resources preserved")
        return result
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)


def _prepare_evidence_directory(mode: str, evidence_root: Path, run_id: str) -> Path:
    if not evidence_root.is_absolute():
        raise ActivationError("evidence-root: absolute canonical path required")
    _reject_path_indirection(evidence_root)
    if not evidence_root.is_dir():
        raise ActivationError("evidence-root: existing directory required")
    evidence_dir = evidence_root / run_id
    if evidence_dir.exists() or _is_link_or_junction(evidence_dir):
        raise ActivationError("evidence directory: final run path already exists")
    return evidence_dir


def cleanup_published_resources(
    validated_bytes: bytes,
    *,
    docker_context: str,
    project_name: str,
    evidence_root: Path,
    run_id: str,
    runner,
    environment: Mapping[str, str],
    revalidate: Callable[[], None],
    on_preserve: Callable[[], None],
    reconciliation_timeline: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Resume a PUBLISHED claim by cleaning resources only; never rerun the graph."""

    with tempfile.TemporaryDirectory(prefix="graph-sandbox-cleanup-") as temporary:
        compose_path = Path(temporary) / "runtime.json"
        _atomic_write(compose_path, validated_bytes)
        expected_digest = hashlib.sha256(validated_bytes).digest()

        def assert_lifecycle_identity() -> None:
            if hashlib.sha256(compose_path.read_bytes()).digest() != expected_digest:
                raise ActivationError("validated Compose bytes changed during lifecycle")
            revalidate()

        base = [
            "docker", "--context", docker_context, "compose", "--file", str(compose_path),
            "--project-name", project_name,
        ]
        scrubbed = scrub_environment(environment)
        try:
            assert_lifecycle_identity()
            down = runner(
                [*base, "down", "--volumes", "--remove-orphans", "--timeout", "10"],
                environment=scrubbed,
                timeout_seconds=120,
                stdin=None,
            )
        except BaseException:
            down = subprocess.CompletedProcess(base, 1, stdout="", stderr="cleanup call failed")
        if down.returncode != 0:
            try:
                assert_lifecycle_identity()
                stop = runner(
                    [*base, "stop", "--timeout", "10"],
                    environment=scrubbed,
                    timeout_seconds=120,
                    stdin=None,
                )
            except BaseException:
                stop = subprocess.CompletedProcess(base, 1, stdout="", stderr="stop call failed")
            try:
                on_preserve()
            except BaseException:
                return subprocess.CompletedProcess(
                    base,
                    HOST_PRESERVATION_FAILURE_EXIT,
                    stdout="",
                    stderr="published resource subset unverified",
                )
            code = HOST_INCONCLUSIVE_EXIT if stop.returncode == 0 else HOST_PRESERVATION_FAILURE_EXIT
            return subprocess.CompletedProcess(base, code, stdout="", stderr="published cleanup incomplete")
        final = evidence_root.resolve(strict=True) / run_id
        published_dirs = (
            (final / "unknown", final / "reconciled")
            if reconciliation_timeline
            else (final,)
        )
        try:
            for published_dir in published_dirs:
                commands = _load_evidence_jsonl(
                    published_dir / "commands.jsonl",
                    "commands journal",
                )
                commands = [record for record in commands if record.get("phase") != "teardown"]
                commands.append(
                    _command_record(
                        "teardown",
                        ["docker", "--context", docker_context, "compose", "down", "--volumes"],
                        0,
                    )
                )
                _refresh_published_commands(published_dir, commands)
        except BaseException:
            return subprocess.CompletedProcess(base, HOST_INCONCLUSIVE_EXIT, stdout="", stderr="published journal finalization incomplete")
        return subprocess.CompletedProcess(base, 0, stdout="", stderr="")


def _resume_command(args: argparse.Namespace) -> list[str]:
    return [
        "python",
        "graph-sandbox/activate.py",
        "resume",
        "--docker-context",
        args.docker_context,
        "--source-revision",
        args.source_revision,
        "--run-id",
        args.run_id,
        "--evidence-root",
        str(args.evidence_root),
        "--case",
        args.case_id,
        "--approval-fixture",
        args.approval_fixture,
    ]


def activate_runtime(
    args: argparse.Namespace,
    *,
    runner=run_process,
    environ: Mapping[str, str] | None = None,
) -> int:
    ambient = os.environ if environ is None else environ
    assert_no_ambient_docker_authority(ambient)
    layout = trusted_layout(Path(__file__))
    initial_context = validate_local_context(
        args.docker_context, runner=runner, environ=ambient
    )
    git_environment = scrub_environment(ambient)
    _runtime_revision_is_exact(
        layout.repository_root,
        args.source_revision,
        runner=runner,
        environment=git_environment,
    )
    sandbox_case = load_sandbox_case(layout.sandbox_root / "cases", args.case_id)
    reconciliation_timeline = _requires_reconciliation_timeline(
        sandbox_case,
        args.approval_fixture,
    )
    lease = ActivationLease.acquire(args.evidence_root, args.run_id)
    try:
        image_lock = _load_json(layout.images_lock, "images.lock")
        model = render_compose(
            layout.compose_file,
            docker_context=args.docker_context,
            image_lock=image_lock,
            source_revision=args.source_revision,
            run_id=args.run_id,
            sandbox_case=sandbox_case,
            approval_fixture=args.approval_fixture,
            profile="default",
            command_runner=runner,
            environ=ambient,
        )
        docker = DockerCLI(
            args.docker_context,
            runner=runner,
            environ=ambient,
        )
        validate_preflight(
            model,
            image_lock,
            sandbox_root=layout.sandbox_root,
            source_revision=args.source_revision,
            run_id=args.run_id,
            sandbox_case=sandbox_case,
            profile="default",
            docker=docker,
        )
        docker_status = docker.status()
        validated_bytes = _canonical_compose_bytes(model)
        validated_compose_digest = hashlib.sha256(validated_bytes).hexdigest()
        base_reference = str(image_lock["images"]["runner"]["base_reference"])
        base_digest = base_reference.rsplit("@", 1)[-1]
        claim = RunClaim.acquire(
            args.operation,
            args.evidence_root,
            args.run_id,
            args.source_revision,
            initial_context.fingerprint,
            sandbox_case.case_id,
            sandbox_case.digest,
            args.approval_fixture,
            validated_compose_digest,
        )
        try:
            final = args.evidence_root / args.run_id
            if claim.phase == "PUBLISHED" or (
                args.operation == "resume"
                and claim.phase in {"RUNNING", "PRESERVED"}
                and (final.exists() or _is_link_or_junction(final))
            ):
                _validate_published_run(
                    final,
                    evidence_root=args.evidence_root,
                    run_id=args.run_id,
                    case_id=sandbox_case.case_id,
                    case_digest=sandbox_case.digest,
                    source_revision=args.source_revision,
                    compose_digest=validated_compose_digest,
                    context_fingerprint=initial_context.fingerprint,
                    reconciliation_timeline=reconciliation_timeline,
                )
                if claim.phase != "PUBLISHED":
                    claim.transition("PUBLISHED")
            else:
                _prepare_evidence_directory(args.operation, args.evidence_root, args.run_id)
            resource_validation = validate_resource_mode(
                args.operation,
                docker.resource_state(args.run_id, args.source_revision),
                run_id=args.run_id,
                source_revision=args.source_revision,
                claim_phase=claim.phase,
                runner_existed=claim.runner_existed,
            )
            claim.record_resources(
                resource_validation.resource_keys,
                runner_existed=resource_validation.runner_existed,
            )
        except BaseException:
            if args.operation == "fresh":
                claim.release()
            raise

        def inspect_resources() -> None:
            resource_validation = validate_resource_mode(
                args.operation,
                docker.resource_state(args.run_id, args.source_revision),
                run_id=args.run_id,
                source_revision=args.source_revision,
                claim_phase=claim.phase,
                runner_existed=claim.runner_existed,
            )
            claim.record_resources(
                resource_validation.resource_keys,
                runner_existed=resource_validation.runner_existed,
            )

        def revalidate() -> None:
            current_context = validate_local_context(
                args.docker_context, runner=runner, environ=ambient
            )
            if current_context != initial_context:
                raise ActivationError("context.endpoint: Docker context changed during lifecycle")
            _runtime_revision_is_exact(
                layout.repository_root,
                args.source_revision,
                runner=runner,
                environment=git_environment,
            )
            inspect_resources()

        if claim.phase == "PUBLISHED":
            cleanup = cleanup_published_resources(
                validated_bytes,
                docker_context=args.docker_context,
                project_name=project_scope(args.run_id),
                evidence_root=args.evidence_root,
                run_id=args.run_id,
                runner=runner,
                environment=ambient,
                revalidate=revalidate,
                on_preserve=inspect_resources,
                reconciliation_timeline=reconciliation_timeline,
            )
            if cleanup.returncode == 0:
                claim.release()
            else:
                print(
                    json.dumps(
                        {
                            "event": "activation_resume_required",
                            "exit_code": cleanup.returncode,
                            "resume_command": _resume_command(args),
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                )
            return cleanup.returncode

        launch_attempted = False

        def note_launch_attempt() -> None:
            nonlocal launch_attempted
            if claim.phase != "RUNNING":
                claim.transition("RUNNING")
            launch_attempted = True

        def note_publication() -> None:
            claim.transition("PUBLISHED")

        try:
            result = execute_validated_compose(
                validated_bytes,
                docker_context=args.docker_context,
                project_name=project_scope(args.run_id),
                evidence_root=args.evidence_root,
                run_id=args.run_id,
                case_id=sandbox_case.case_id,
                case_digest=sandbox_case.digest,
                source_revision=args.source_revision,
                verification={
                    "docker_context": initial_context.name,
                    "docker_context_fingerprint": initial_context.fingerprint,
                    "docker_engine_version": docker_status.engine_version,
                    "docker_compose_version": docker_status.compose_version,
                    "docker_platform": docker_status.os_type,
                    "project": project_scope(args.run_id),
                    "base_image_digest": base_digest,
                    "runner_image_id": image_lock["images"]["runner"]["image_id"],
                    "services_image_id": image_lock["images"]["services"]["image_id"],
                },
                runner=runner,
                environment=ambient,
                revalidate=revalidate,
                on_launch=note_launch_attempt,
                on_publish=note_publication,
                on_preserve=inspect_resources,
                commands=(
                    _command_record(
                        "activation",
                        ["python", "graph-sandbox/activate.py", args.operation],
                        0,
                    ),
                    _command_record(
                        "preflight",
                        ["docker", "--context", args.docker_context, "compose", "config"],
                        0,
                    ),
                ),
                reconciliation_timeline=reconciliation_timeline,
            )
        except BaseException:
            if args.operation == "fresh" and not launch_attempted:
                claim.release()
            raise
        if result.returncode in {0, 2, 64}:
            claim.release()
        if result.returncode not in {0, 2, 64}:
            if claim.phase == "RUNNING":
                claim.transition("PRESERVED")
            print(
                json.dumps(
                    {
                        "event": "activation_resume_required",
                        "exit_code": result.returncode,
                        "resume_command": _resume_command(args),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
        elif result.returncode == 64:
            print('{"error_class":"runner_rejected","event":"activation_terminal_rejection"}')
        return result.returncode
    finally:
        lease.release()


def parse_args(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="operation", required=True)

    build = subparsers.add_parser("build", help="build immutable images from a clean Git snapshot")
    build.add_argument("--docker-context", required=True)
    build.add_argument("--source-revision", required=True)

    for operation in ("fresh", "resume"):
        runtime = subparsers.add_parser(operation, help=f"{operation} the run-scoped sandbox")
        runtime.add_argument("--docker-context", required=True)
        runtime.add_argument("--source-revision", required=True)
        runtime.add_argument("--run-id", required=True)
        runtime.add_argument("--evidence-root", required=True, type=Path)
        runtime.add_argument(
            "--case",
            dest="case_id",
            required=True,
        )
        runtime.add_argument(
            "--approval-fixture",
            choices=("APPROVED", "REJECTED", "TIMEOUT"),
            default="APPROVED",
        )
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    args = parse_args(arguments)
    try:
        ambient = os.environ
        assert_no_ambient_docker_authority(ambient)
        layout = trusted_layout(Path(__file__))
        if args.operation == "build":
            build_and_lock(
                layout=layout,
                source_revision=args.source_revision,
                docker_context=args.docker_context,
                runner=run_process,
                environ=ambient,
            )
            print(f"images locked for {args.source_revision}")
            return 0
        return activate_runtime(args, runner=run_process, environ=ambient)
    except (ActivationError, SnapshotError, PreflightError) as exc:
        print(f"activation rejected: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
