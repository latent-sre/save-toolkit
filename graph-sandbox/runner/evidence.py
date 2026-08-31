from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Iterable, Mapping
from pathlib import Path

from runner.effects import derive_idempotency_key
from runner.events import EVENT_DATA_SCHEMAS
from runner.models import (
    CHECKPOINT_LINEAGE_VERSION,
    CONTRACT_VERSION,
    EVIDENCE_VERSION,
    EVENT_VERSION,
    SANDBOX_VERSION,
    STATE_SCHEMA_VERSION,
)
from runner.runtime import runtime_evidence
from runner.validation import RFC3339_UTC_PATTERN, validate_atomic_id


RUNNER_EVIDENCE_FILES = frozenset(
    {
        "checkpoint-lineage.json",
        "checksums.sha256",
        "effects.jsonl",
        "events.jsonl",
        "final-state.json",
        "manifest.json",
        "receipts/inventory.json",
        "receipts/payment.json",
        "runtime.json",
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
CHECKSUM_LINE_PATTERN = re.compile(r"(?P<digest>[0-9a-f]{64})  (?P<path>[^\r\n]+)\Z")
MAX_EVIDENCE_BYTES = 32 * 1024 * 1024
MAX_EVIDENCE_FILES = 1024


class ExistingSnapshotInvalid(RuntimeError):
    pass


def _load_snapshot_json(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExistingSnapshotInvalid(
            f"existing UNKNOWN snapshot has invalid {label}"
        ) from exc
    if not isinstance(value, dict):
        raise ExistingSnapshotInvalid(
            f"existing UNKNOWN snapshot {label} must be an object"
        )
    return value


def _load_snapshot_jsonl(path: Path, label: str) -> list[dict[str, object]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        values = [json.loads(line) for line in lines if line]
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExistingSnapshotInvalid(
            f"existing UNKNOWN snapshot has invalid {label}"
        ) from exc
    if not values or not all(isinstance(value, dict) for value in values):
        raise ExistingSnapshotInvalid(
            f"existing UNKNOWN snapshot {label} must contain objects"
        )
    return values


EVENT_FIELDS = frozenset(
    {
        "event_version",
        "event_type",
        "event_id",
        "sequence",
        "time_utc",
        "contract_version",
        "sandbox_version",
        "source_revision",
        "run_id",
        "case_id",
        "case_digest",
        "thread_id",
        "node_id",
        "task_id",
        "attempt_id",
        "replay_id",
        "checkpoint_id",
        "effect_id",
        "failure_plane",
        "error_class",
        "data",
    }
)
EFFECT_FIELDS = frozenset(
    {
        "sequence",
        "effect_id",
        "task_id",
        "attempt_id",
        "replay_id",
        "idempotency_key",
        "payload_hash",
        "target",
        "effect_state",
        "time_utc",
        "reason_class",
        "receipt",
    }
)


def _validate_unknown_events(
    events: list[dict[str, object]],
    *,
    run_id: str,
    case_id: str,
    case_digest: str,
    source_revision: str,
    thread_id: str,
    checkout_effect_id: str,
) -> None:
    expected_identity = {
        "contract_version": CONTRACT_VERSION,
        "sandbox_version": SANDBOX_VERSION,
        "source_revision": source_revision,
        "run_id": run_id,
        "case_id": case_id,
        "case_digest": case_digest,
        "thread_id": thread_id,
    }
    replay_id = f"{run_id}:replay-0"
    for expected_sequence, event in enumerate(events, start=1):
        event_type = event.get("event_type")
        schema = EVENT_DATA_SCHEMAS.get(str(event_type))
        data = event.get("data")
        if (
            set(event) != EVENT_FIELDS
            or event.get("event_version") != EVENT_VERSION
            or event.get("sequence") != expected_sequence
            or event.get("event_id") != f"{run_id}:{expected_sequence:08d}"
            or any(event.get(key) != value for key, value in expected_identity.items())
            or event.get("replay_id") != replay_id
            or not isinstance(event.get("time_utc"), str)
            or RFC3339_UTC_PATTERN.fullmatch(str(event["time_utc"])) is None
            or schema is None
            or not isinstance(data, dict)
            or not set(schema.required) <= set(data)
            or set(data) - set(schema.required) - set(schema.optional)
        ):
            raise ExistingSnapshotInvalid(
                "existing UNKNOWN snapshot event identity or schema mismatch"
            )
    run_events = [
        event for event in events if str(event["event_type"]).startswith("run.")
    ]
    if (
        [event["event_type"] for event in run_events]
        != ["run.accepted", "run.started", "run.terminal"]
        or run_events != [events[0], events[1], events[-1]]
        or run_events[0]["data"] != {"result": "accepted"}
        or run_events[1]["data"] != {"result": "started"}
        or run_events[-1]["data"]
        != {"result": "terminal", "outcome": "UNKNOWN"}
        or any(
            event["node_id"] != expected_node
            or any(
                event[field] is not None
                for field in (
                    "task_id",
                    "attempt_id",
                    "checkpoint_id",
                    "effect_id",
                    "failure_plane",
                    "error_class",
                )
            )
            for event, expected_node in zip(
                run_events,
                ("admit_run", "admit_run", "terminal"),
                strict=True,
            )
        )
        or any(
            event["event_type"]
            in {"effect.receipt_recorded", "effect.reconciled"}
            for event in events
        )
    ):
        raise ExistingSnapshotInvalid(
            "existing UNKNOWN snapshot has a false terminal event history"
        )
    effect_events = [
        event for event in events if str(event["event_type"]).startswith("effect.")
    ]
    checkout_task_id = f"{run_id}:checkout_effect:0"
    checkout_attempt_id = f"{checkout_task_id}:attempt-1"
    if (
        [event["event_type"] for event in effect_events]
        != [
            "effect.prepared",
            "effect.dispatched",
            "effect.unknown",
            "effect.replay_refused",
        ]
        or any(event["effect_id"] != checkout_effect_id for event in effect_events)
        or any(
            event["node_id"] != "checkout_effect"
            or event["task_id"] != checkout_task_id
            or event["attempt_id"] != checkout_attempt_id
            or event["replay_id"] != replay_id
            or event["checkpoint_id"] is not None
            for event in effect_events
        )
        or [event["data"].get("effect_state") for event in effect_events]
        != ["PREPARED", "DISPATCHED", "UNKNOWN", "UNKNOWN"]
        or any(event["data"].get("effect_class") != "checkout" for event in effect_events)
        or effect_events[0]["failure_plane"] is not None
        or effect_events[0]["error_class"] is not None
        or effect_events[1]["failure_plane"] is not None
        or effect_events[1]["error_class"] is not None
        or effect_events[2]["failure_plane"] != "checkout"
        or effect_events[2]["error_class"]
        != effect_events[2]["data"].get("reason_class")
        or effect_events[3]["failure_plane"] != "graph-control"
        or effect_events[3]["error_class"] != "automatic_replay_forbidden"
        or effect_events[3]["data"].get("reason_class")
        != "reconciliation_snapshot_required"
    ):
        raise ExistingSnapshotInvalid(
            "existing UNKNOWN snapshot effect events are not the UNKNOWN progression"
        )
    allowed_task_ids = {
        checkout_task_id,
        *(f"{run_id}:readiness:{ordinal}" for ordinal in range(3)),
    }
    if any(
        str(event["event_type"]).startswith("task.")
        and event["task_id"] not in allowed_task_ids
        for event in events
    ):
        raise ExistingSnapshotInvalid(
            "existing UNKNOWN snapshot contains an unrelated task history"
        )
    for ordinal in range(3):
        readiness_task_id = f"{run_id}:readiness:{ordinal}"
        readiness_events = [
            event for event in events if event.get("task_id") == readiness_task_id
        ]
        if (
            [event["event_type"] for event in readiness_events]
            != ["task.started", "task.completed"]
            or [event["data"] for event in readiness_events]
            != [{"status": "started"}, {"status": "completed"}]
            or any(
                event["node_id"] != "readiness"
                or event["attempt_id"] != f"{readiness_task_id}:attempt-1"
                or event["effect_id"] is not None
                or event["failure_plane"] is not None
                or event["error_class"] is not None
                for event in readiness_events
            )
        ):
            raise ExistingSnapshotInvalid(
                "existing UNKNOWN snapshot readiness task history is inconsistent"
            )
    checkout_events = [
        event
        for event in events
        if event.get("task_id") == checkout_task_id
        and event["event_type"] in {"task.started", "task.failed", "task.completed"}
    ]
    if (
        [event["event_type"] for event in checkout_events]
        != ["task.started", "task.failed"]
        or [event["data"] for event in checkout_events]
        != [
            {"status": "started"},
            {"status": "failed", "disposition": "reconcile"},
        ]
        or any(
            event["node_id"] != "checkout_effect"
            or event["attempt_id"] != checkout_attempt_id
            or event["effect_id"] != checkout_effect_id
            for event in checkout_events
        )
        or checkout_events[0]["failure_plane"] is not None
        or checkout_events[0]["error_class"] is not None
        or checkout_events[1]["failure_plane"] != "checkout"
        or checkout_events[1]["error_class"]
        != effect_events[2]["data"].get("reason_class")
        or any(
            event.get("task_id") == f"{run_id}:reconcile_if_ambiguous:0"
            for event in events
        )
    ):
        raise ExistingSnapshotInvalid(
            "existing UNKNOWN snapshot checkout task history is inconsistent"
        )


def _validate_unknown_effects(
    effects: list[dict[str, object]],
    trusted_checkout: Mapping[str, object],
    *,
    run_id: str,
    checkout_effect_id: str,
) -> None:
    payload = {
        "order_id": trusted_checkout.get("order_id"),
        "amount_cents": trusted_checkout.get("amount_cents"),
        "items": trusted_checkout.get("items"),
    }
    payload_hash = hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
    ).hexdigest()
    checkout_task_id = f"{run_id}:checkout_effect:0"
    if len(effects) != 3:
        raise ExistingSnapshotInvalid(
            "existing UNKNOWN snapshot effect ledger is not the UNKNOWN progression"
        )
    for sequence, (effect, effect_state) in enumerate(
        zip(effects, ("PREPARED", "DISPATCHED", "UNKNOWN"), strict=True),
        start=1,
    ):
        if (
            set(effect) != EFFECT_FIELDS
            or effect.get("sequence") != sequence
            or effect.get("effect_id") != checkout_effect_id
            or effect.get("task_id") != checkout_task_id
            or effect.get("attempt_id") != f"{checkout_task_id}:attempt-1"
            or effect.get("replay_id") != f"{run_id}:replay-0"
            or effect.get("idempotency_key")
            != derive_idempotency_key(checkout_effect_id)
            or effect.get("payload_hash") != payload_hash
            or effect.get("target") != "checkout"
            or effect.get("effect_state") != effect_state
            or not isinstance(effect.get("time_utc"), str)
            or RFC3339_UTC_PATTERN.fullmatch(str(effect["time_utc"])) is None
            or effect.get("receipt") is not None
        ):
            raise ExistingSnapshotInvalid(
                "existing UNKNOWN snapshot effect ledger is not the UNKNOWN progression"
            )
    if effects[-1].get("reason_class") is None:
        raise ExistingSnapshotInvalid(
            "existing UNKNOWN snapshot effect ledger lacks its UNKNOWN reason"
        )


def _validate_unknown_lineage(
    lineage: Mapping[str, object],
    runtime: Mapping[str, object],
    events: list[dict[str, object]],
    *,
    source_revision: str,
    thread_id: str,
) -> None:
    lineage_fields = {
        "lineage_version",
        "contract_version",
        "state_schema",
        "source_revision",
        "thread_id",
        "langgraph_version",
        "sqlite_saver_version",
        "resume_source_checkpoint_id",
        "checkpoints",
        "saver_checkpoint_ids",
    }
    packages = runtime.get("packages")
    checkpoints = lineage.get("checkpoints")
    saver_ids = lineage.get("saver_checkpoint_ids")
    if (
        set(lineage) != lineage_fields
        or lineage.get("lineage_version") != CHECKPOINT_LINEAGE_VERSION
        or lineage.get("contract_version") != CONTRACT_VERSION
        or lineage.get("state_schema") != STATE_SCHEMA_VERSION
        or lineage.get("source_revision") != source_revision
        or lineage.get("thread_id") != thread_id
        or not isinstance(packages, Mapping)
        or lineage.get("langgraph_version") != packages.get("langgraph")
        or lineage.get("sqlite_saver_version")
        != packages.get("langgraph-checkpoint-sqlite")
        or not isinstance(checkpoints, list)
        or not checkpoints
        or not isinstance(saver_ids, list)
        or not saver_ids
    ):
        raise ExistingSnapshotInvalid(
            "existing UNKNOWN snapshot checkpoint lineage is invalid"
        )
    checkpoint_ids: list[str] = []
    for checkpoint in checkpoints:
        if (
            not isinstance(checkpoint, Mapping)
            or set(checkpoint) != {"checkpoint_id", "operation", "result"}
            or not isinstance(checkpoint.get("checkpoint_id"), str)
            or checkpoint.get("operation") != "write"
            or checkpoint.get("result") != "recorded"
        ):
            raise ExistingSnapshotInvalid(
                "existing UNKNOWN snapshot checkpoint lineage is invalid"
            )
        checkpoint_ids.append(str(checkpoint["checkpoint_id"]))
    resume_source = lineage.get("resume_source_checkpoint_id")
    if (
        len(checkpoint_ids) != len(set(checkpoint_ids))
        or saver_ids != checkpoint_ids
        or not isinstance(resume_source, str)
        or resume_source not in checkpoint_ids
    ):
        raise ExistingSnapshotInvalid(
            "existing UNKNOWN snapshot checkpoint lineage is inconsistent"
        )
    recorded_ids: list[str] = []
    checkpoint_positions = {
        checkpoint_id: position
        for position, checkpoint_id in enumerate(checkpoint_ids)
    }
    pending_writes: set[str] = set()
    pending_resume_source: str | None = None
    latest_resume_source: str | None = None
    for event in events:
        event_type = event["event_type"]
        checkpoint_id = event.get("checkpoint_id")
        if event_type == "checkpoint.write_started":
            if (
                not isinstance(checkpoint_id, str)
                or checkpoint_id in pending_writes
                or event["data"] != {"operation": "write"}
            ):
                raise ExistingSnapshotInvalid(
                    "existing UNKNOWN snapshot checkpoint events are inconsistent"
                )
            pending_writes.add(checkpoint_id)
        elif event_type in {
            "checkpoint.write_completed",
            "checkpoint.write_failed",
        }:
            expected_result = (
                "recorded"
                if event_type == "checkpoint.write_completed"
                else "failed"
            )
            if (
                not isinstance(checkpoint_id, str)
                or checkpoint_id not in pending_writes
                or event["data"]
                != {"operation": "write", "result": expected_result}
            ):
                raise ExistingSnapshotInvalid(
                    "existing UNKNOWN snapshot checkpoint events are inconsistent"
                )
            pending_writes.remove(checkpoint_id)
            if event_type == "checkpoint.write_completed":
                recorded_ids.append(checkpoint_id)
            elif checkpoint_id in checkpoint_ids:
                raise ExistingSnapshotInvalid(
                    "existing UNKNOWN snapshot failed checkpoint is in saver lineage"
                )
        elif event_type == "checkpoint.resume_started":
            if (
                not isinstance(checkpoint_id, str)
                or checkpoint_id not in checkpoint_ids
                or pending_resume_source is not None
                or event["data"] != {"operation": "resume"}
            ):
                raise ExistingSnapshotInvalid(
                    "existing UNKNOWN snapshot checkpoint resume is inconsistent"
                )
            pending_resume_source = checkpoint_id
        elif event_type in {
            "checkpoint.resume_completed",
            "checkpoint.resume_failed",
        }:
            expected_result = (
                "completed"
                if event_type == "checkpoint.resume_completed"
                else "failed"
            )
            if (
                pending_resume_source is None
                or not isinstance(checkpoint_id, str)
                or checkpoint_id not in checkpoint_ids
                or event["data"]
                != {"operation": "resume", "result": expected_result}
                or (
                    event_type == "checkpoint.resume_completed"
                    and checkpoint_positions[checkpoint_id]
                    <= checkpoint_positions[pending_resume_source]
                )
            ):
                raise ExistingSnapshotInvalid(
                    "existing UNKNOWN snapshot checkpoint resume is inconsistent"
                )
            if event_type == "checkpoint.resume_completed":
                latest_resume_source = pending_resume_source
            pending_resume_source = None
    if (
        pending_writes
        or pending_resume_source is not None
        or recorded_ids != checkpoint_ids
        or latest_resume_source != resume_source
    ):
        raise ExistingSnapshotInvalid(
            "existing UNKNOWN snapshot checkpoint events are inconsistent"
        )


def validate_unknown_snapshot(
    run_dir: Path,
    *,
    run_id: str,
    case_id: str,
    case_digest: str,
    source_revision: str,
    thread_id: str,
    trusted_checkout: Mapping[str, object],
) -> None:
    """Fail closed before resuming from an already-exported UNKNOWN snapshot."""

    if run_dir.is_symlink() or not run_dir.is_dir():
        raise ExistingSnapshotInvalid(
            "existing UNKNOWN snapshot is not a regular directory"
        )
    files: dict[str, Path] = {}
    total_bytes = 0
    for path in sorted(run_dir.rglob("*")):
        if path.is_symlink():
            raise ExistingSnapshotInvalid(
                "existing UNKNOWN snapshot contains a symlink"
            )
        relative = path.relative_to(run_dir).as_posix()
        if path.is_dir():
            if relative != "receipts":
                raise ExistingSnapshotInvalid(
                    f"existing UNKNOWN snapshot has unexpected path {relative}"
                )
            continue
        if (
            not path.is_file()
            or relative not in RUNNER_EVIDENCE_FILES
            or path.name.endswith(".tmp")
        ):
            raise ExistingSnapshotInvalid(
                f"existing UNKNOWN snapshot has unexpected path {relative}"
            )
        total_bytes += path.stat().st_size
        if total_bytes > MAX_EVIDENCE_BYTES or len(files) >= MAX_EVIDENCE_FILES:
            raise ExistingSnapshotInvalid(
                "existing UNKNOWN snapshot exceeds evidence bounds"
            )
        files[relative] = path

    missing = REQUIRED_RUNNER_EVIDENCE - set(files)
    if missing:
        raise ExistingSnapshotInvalid(
            f"existing UNKNOWN snapshot is missing {sorted(missing)[0]}"
        )
    try:
        checksum_lines = files["checksums.sha256"].read_text(
            encoding="ascii"
        ).splitlines()
    except (OSError, UnicodeError) as exc:
        raise ExistingSnapshotInvalid(
            "existing UNKNOWN snapshot has invalid checksums"
        ) from exc
    observed_checksums: dict[str, str] = {}
    for line in checksum_lines:
        match = CHECKSUM_LINE_PATTERN.fullmatch(line)
        if match is None or match.group("path") in observed_checksums:
            raise ExistingSnapshotInvalid(
                "existing UNKNOWN snapshot has invalid checksums"
            )
        observed_checksums[match.group("path")] = match.group("digest")
    expected_checksum_paths = set(files) - {"checksums.sha256"}
    if set(observed_checksums) != expected_checksum_paths:
        raise ExistingSnapshotInvalid(
            "existing UNKNOWN snapshot checksum coverage mismatch"
        )
    for relative, expected_digest in observed_checksums.items():
        if hashlib.sha256(files[relative].read_bytes()).hexdigest() != expected_digest:
            raise ExistingSnapshotInvalid(
                f"existing UNKNOWN snapshot checksum mismatch for {relative}"
            )

    manifest = _load_snapshot_json(files["manifest.json"], "manifest")
    manifest_fields = {
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
    }
    expected_identity = {
        "source_revision": source_revision,
        "run_id": run_id,
        "case_id": case_id,
        "case_digest": case_digest,
        "thread_id": thread_id,
        "outcome": "UNKNOWN",
    }
    expected_artifacts = sorted(
        set(files) - {"manifest.json", "checksums.sha256"}
    )
    if (
        set(manifest) != manifest_fields
        or manifest.get("evidence_version") != EVIDENCE_VERSION
        or manifest.get("contract_version") != CONTRACT_VERSION
        or manifest.get("sandbox_version") != SANDBOX_VERSION
        or any(manifest.get(key) != value for key, value in expected_identity.items())
        or manifest.get("authoritative_result_id") is not None
        or not isinstance(manifest.get("started_at"), str)
        or RFC3339_UTC_PATTERN.fullmatch(str(manifest["started_at"])) is None
        or not isinstance(manifest.get("ended_at"), str)
        or RFC3339_UTC_PATTERN.fullmatch(str(manifest["ended_at"])) is None
        or str(manifest["started_at"]) > str(manifest["ended_at"])
        or manifest.get("artifacts") != expected_artifacts
    ):
        raise ExistingSnapshotInvalid(
            "existing UNKNOWN snapshot manifest identity or inventory mismatch"
        )

    final_state = _load_snapshot_json(files["final-state.json"], "final state")
    checkout_effect_id = f"{run_id}:checkout_effect:0:effect-checkout"
    expected_state_fields = {
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
    }
    if (
        set(final_state) != expected_state_fields
        or final_state.get("contract_version") != CONTRACT_VERSION
        or final_state.get("state_schema") != STATE_SCHEMA_VERSION
        or any(final_state.get(key) != value for key, value in expected_identity.items())
        or final_state.get("phase") != "TERMINAL"
        or final_state.get("replay_number") != 0
        or final_state.get("checkout_status") != "UNKNOWN"
        or final_state.get("checkout") != trusted_checkout
        or final_state.get("pending_effects") != [checkout_effect_id]
        or not isinstance(final_state.get("receipts"), dict)
        or checkout_effect_id in final_state["receipts"]
    ):
        raise ExistingSnapshotInvalid(
            "existing UNKNOWN snapshot final state identity or effect mismatch"
        )

    required_tasks = {
        f"{run_id}:readiness:0": {"status": "completed", "attempt": 1},
        f"{run_id}:readiness:1": {"status": "completed", "attempt": 1},
        f"{run_id}:readiness:2": {"status": "completed", "attempt": 1},
        f"{run_id}:checkout_effect:0": {"status": "failed", "attempt": 1},
    }
    readiness = final_state.get("readiness")
    budgets = final_state.get("budgets")
    approval = final_state.get("approval")
    checkout = final_state.get("checkout")
    cancellation = final_state.get("cancellation")
    items = checkout.get("items") if isinstance(checkout, Mapping) else None
    if (
        final_state.get("tasks") != required_tasks
        or final_state.get("receipts") != {}
        or final_state.get("failure") is not None
        or not isinstance(checkout, Mapping)
        or set(checkout) != {
            "order_id",
            "amount_cents",
            "currency",
            "items",
        }
        or not isinstance(checkout.get("order_id"), str)
        or not checkout["order_id"]
        or isinstance(checkout.get("amount_cents"), bool)
        or not isinstance(checkout.get("amount_cents"), int)
        or checkout["amount_cents"] <= 0
        or checkout.get("currency") != "USD"
        or not isinstance(items, list)
        or not items
        or any(
            not isinstance(item, Mapping)
            or set(item) != {"sku", "quantity"}
            or not isinstance(item.get("sku"), str)
            or not item["sku"]
            or isinstance(item.get("quantity"), bool)
            or not isinstance(item.get("quantity"), int)
            or item["quantity"] <= 0
            for item in items
        )
        or not isinstance(readiness, Mapping)
        or set(readiness) != {"checkout", "payments", "inventory"}
        or any(
            readiness[service] != {"status": "ok", "service": service}
            for service in readiness
        )
        or not isinstance(approval, Mapping)
        or set(approval)
        != {"request_id", "status", "actor_class", "decision_time"}
        or approval.get("request_id") != f"approval-{run_id}"
        or approval.get("status") != "APPROVED"
        or approval.get("actor_class") != "fixture-operator"
        or not isinstance(approval.get("decision_time"), str)
        or RFC3339_UTC_PATTERN.fullmatch(str(approval["decision_time"])) is None
        or not isinstance(budgets, Mapping)
        or budgets
        != {
            "attempts": {"limit": 8, "consumed": 1},
            "model_calls": {"limit": 1, "consumed": 1},
            "tokens": {"limit": 64, "consumed": 64},
            "spend_micro_usd": {"limit": 0, "consumed": 0},
            "wall_time_ms": {"limit": 120000, "consumed": 0},
        }
        or cancellation
        != {
            "state": "NONE",
            "request_id": None,
            "acknowledgement_ms": None,
        }
    ):
        raise ExistingSnapshotInvalid(
            "existing UNKNOWN snapshot final control state is invalid"
        )
    if any(path.startswith("receipts/") for path in files):
        raise ExistingSnapshotInvalid(
            "existing UNKNOWN snapshot contains false-success receipt evidence"
        )

    runtime = _load_snapshot_json(files["runtime.json"], "runtime")
    if runtime != runtime_evidence():
        raise ExistingSnapshotInvalid(
            "existing UNKNOWN snapshot runtime contract mismatch"
        )
    events = _load_snapshot_jsonl(files["events.jsonl"], "events")
    _validate_unknown_events(
        events,
        run_id=run_id,
        case_id=case_id,
        case_digest=case_digest,
        source_revision=source_revision,
        thread_id=thread_id,
        checkout_effect_id=checkout_effect_id,
    )
    effects = _load_snapshot_jsonl(files["effects.jsonl"], "effects")
    _validate_unknown_effects(
        effects,
        trusted_checkout,
        run_id=run_id,
        checkout_effect_id=checkout_effect_id,
    )
    effect_unknown = next(
        event for event in events if event["event_type"] == "effect.unknown"
    )
    if effect_unknown["data"].get("reason_class") != effects[-1].get(
        "reason_class"
    ):
        raise ExistingSnapshotInvalid(
            "existing UNKNOWN snapshot effect event and ledger disagree"
        )
    lineage = _load_snapshot_json(
        files["checkpoint-lineage.json"],
        "checkpoint lineage",
    )
    _validate_unknown_lineage(
        lineage,
        runtime,
        events,
        source_revision=source_revision,
        thread_id=thread_id,
    )


class EvidenceExporter:
    def __init__(
        self,
        evidence_root: Path,
        run_id: str,
        *,
        directory_name: str | None = None,
    ) -> None:
        validate_atomic_id(run_id, "run_id")
        selected_name = run_id if directory_name is None else directory_name
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,159}", selected_name):
            raise ValueError("evidence directory name must be bounded lowercase ASCII")
        self.evidence_root = evidence_root.resolve()
        self.run_dir = self.evidence_root / selected_name
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def write_json(self, relative_path: str, value: object) -> Path:
        payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
        return self._atomic_write(relative_path, payload.encode("utf-8"))

    def write_jsonl(
        self,
        relative_path: str,
        records: Iterable[Mapping[str, object]],
    ) -> Path:
        lines = [json.dumps(dict(record), sort_keys=True, separators=(",", ":")) for record in records]
        payload = ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")
        return self._atomic_write(relative_path, payload)

    def write_checksums(self) -> list[dict[str, str]]:
        entries: list[dict[str, str]] = []
        for path in sorted(self.run_dir.rglob("*")):
            if not path.is_file() or path.name == "checksums.sha256" or path.name.endswith(".tmp"):
                continue
            relative = path.relative_to(self.run_dir).as_posix()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            entries.append({"sha256": digest, "path": relative})
        text = "".join(f"{entry['sha256']}  {entry['path']}\n" for entry in entries)
        self._atomic_write("checksums.sha256", text.encode("ascii"))
        return entries

    def _atomic_write(self, relative_path: str, payload: bytes) -> Path:
        target = self._resolve_relative(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary.write(payload)
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            os.replace(temporary_path, target)
            self._sync_directory(target.parent)
            return target
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    def _resolve_relative(self, relative_path: str) -> Path:
        relative = Path(relative_path)
        if relative.is_absolute() or not relative.parts or ".." in relative.parts:
            raise ValueError("relative evidence path must remain inside the run directory")
        candidate = (self.run_dir / relative).resolve()
        if not candidate.is_relative_to(self.run_dir.resolve()):
            raise ValueError("relative evidence path must remain inside the run directory")
        return candidate

    @staticmethod
    def _sync_directory(directory: Path) -> None:
        descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
