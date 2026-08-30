from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from runner.models import CONTRACT_VERSION, EVENT_VERSION, SANDBOX_VERSION
from runner.validation import (
    require_closed_mapping,
    validate_atomic_id,
    validate_derived_id,
    validate_sha256,
    validate_source_revision,
)


class EventContractError(ValueError):
    pass


@dataclass(frozen=True)
class DataSchema:
    required: frozenset[str]
    optional: frozenset[str] = frozenset()


def _schema(*required: str, optional: tuple[str, ...] = ()) -> DataSchema:
    return DataSchema(frozenset(required), frozenset(optional))


EVENT_DATA_SCHEMAS: dict[str, DataSchema] = {
    "run.accepted": _schema("result"),
    "run.started": _schema("result"),
    "run.terminal": _schema("result", "outcome", optional=("authoritative_result_id",)),
    "run.cancelled": _schema("result", "outcome"),
    "run.superseded": _schema("result"),
    "run.inconclusive": _schema("result", "outcome"),
    "task.scheduled": _schema("status"),
    "task.started": _schema("status"),
    "task.completed": _schema("status"),
    "task.failed": _schema("status", "disposition"),
    "task.retry_scheduled": _schema("status", "retry_number"),
    "task.retry_exhausted": _schema("status", "attempts"),
    "edge.selected": _schema("edge_id"),
    "edge.fanout_emitted": _schema("targets"),
    "edge.join_satisfied": _schema("branches"),
    "edge.join_starved": _schema("missing_branches"),
    "approval.requested": _schema("request_id", "approval_status"),
    "approval.approved": _schema("request_id", "approval_status", "actor_class"),
    "approval.rejected": _schema("request_id", "approval_status", "actor_class"),
    "approval.timed_out": _schema("request_id", "approval_status"),
    "checkpoint.write_started": _schema("operation"),
    "checkpoint.write_completed": _schema("operation", "result"),
    "checkpoint.write_failed": _schema("operation", "result"),
    "checkpoint.resume_started": _schema("operation"),
    "checkpoint.resume_completed": _schema("operation", "result"),
    "checkpoint.resume_failed": _schema("operation", "result"),
    "checkpoint.rejected": _schema("operation", "result", "mismatches"),
    "effect.prepared": _schema("effect_class", "effect_state"),
    "effect.dispatched": _schema("effect_class", "effect_state"),
    "effect.receipt_recorded": _schema("effect_class", "effect_state", "authoritative_result_id"),
    "effect.unknown": _schema("effect_class", "effect_state", "reason_class"),
    "effect.reconciled": _schema("effect_class", "effect_state", "authoritative_result_id"),
    "effect.replay_refused": _schema("effect_class", "effect_state", "reason_class"),
    "budget.observed": _schema("kind", "limit", "consumed", "remaining"),
    "budget.threshold_reached": _schema("kind", "limit", "consumed", "remaining"),
    "budget.exhausted": _schema("kind", "limit", "consumed", "remaining"),
    "cancellation.requested": _schema("state", "request_id"),
    "cancellation.propagated": _schema("state", "request_id"),
    "cancellation.acknowledged": _schema("state", "request_id", "acknowledgement_ms"),
    "cancellation.unconfirmed": _schema("state", "request_id"),
}


class BoundaryEventStore:
    def __init__(
        self,
        path: Path,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._setup()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        return connection

    def _setup(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS boundary_events (
                    sequence INTEGER PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    record_json TEXT NOT NULL
                )
                """
            )

    def emit(
        self,
        event_type: str,
        state: Mapping[str, object],
        data: Mapping[str, object],
        *,
        node_id: str | None = None,
        task_id: str | None = None,
        attempt_id: str | None = None,
        checkpoint_id: str | None = None,
        effect_id: str | None = None,
        failure_plane: str | None = None,
        error_class: str | None = None,
    ) -> dict[str, object]:
        schema = EVENT_DATA_SCHEMAS.get(event_type)
        if schema is None:
            raise EventContractError(f"unknown event_type: {event_type}")
        try:
            require_closed_mapping(
                data,
                field="event data",
                required=set(schema.required),
                optional=set(schema.optional),
            )
        except ValueError as exc:
            message = str(exc)
            message = message.replace(
                "event data has unexpected fields: ",
                "unexpected data fields: ",
                1,
            )
            raise EventContractError(message) from exc

        run_id = validate_atomic_id(state.get("run_id"), "run_id")
        case_id = validate_atomic_id(state.get("case_id"), "case_id")
        case_digest = validate_sha256(state.get("case_digest"), "case_digest")
        thread_id = validate_derived_id(state.get("thread_id"), "thread_id")
        revision = validate_source_revision(state.get("source_revision"))
        replay_number = state.get("replay_number")
        if not isinstance(replay_number, int) or isinstance(replay_number, bool) or replay_number < 0:
            raise EventContractError("replay_number must be a non-negative integer")
        for field, value in (
            ("node_id", node_id),
            ("failure_plane", failure_plane),
            ("error_class", error_class),
        ):
            if value is not None:
                validate_atomic_id(value, field)
        for field, value in (
            ("task_id", task_id),
            ("attempt_id", attempt_id),
            ("effect_id", effect_id),
        ):
            if value is not None:
                validate_derived_id(value, field)
        if checkpoint_id is not None and (
            not isinstance(checkpoint_id, str)
            or len(checkpoint_id) > 256
            or not checkpoint_id.isprintable()
            or not checkpoint_id.isascii()
        ):
            raise EventContractError("checkpoint_id must be bounded printable ASCII")

        now = self._clock().astimezone(UTC)
        time_utc = now.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT sequence, run_id FROM boundary_events ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            if row is not None and row["run_id"] != run_id:
                raise EventContractError("event database is already bound to another run_id")
            sequence = 1 if row is None else int(row["sequence"]) + 1
            record: dict[str, object] = {
                "event_version": EVENT_VERSION,
                "event_type": event_type,
                "event_id": f"{run_id}:{sequence:08d}",
                "sequence": sequence,
                "time_utc": time_utc,
                "contract_version": CONTRACT_VERSION,
                "sandbox_version": SANDBOX_VERSION,
                "source_revision": revision,
                "run_id": run_id,
                "case_id": case_id,
                "case_digest": case_digest,
                "thread_id": thread_id,
                "node_id": node_id,
                "task_id": task_id,
                "attempt_id": attempt_id,
                "replay_id": f"{run_id}:replay-{replay_number}",
                "checkpoint_id": checkpoint_id,
                "effect_id": effect_id,
                "failure_plane": failure_plane,
                "error_class": error_class,
                "data": dict(data),
            }
            connection.execute(
                "INSERT INTO boundary_events(sequence, run_id, record_json) VALUES (?, ?, ?)",
                (sequence, run_id, json.dumps(record, sort_keys=True, separators=(",", ":"))),
            )
        return record

    def project(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT record_json FROM boundary_events ORDER BY sequence"
            ).fetchall()
        return [json.loads(row["record_json"]) for row in rows]

    def next_attempt_number(self, task_id: str) -> int:
        validate_derived_id(task_id, "task_id")
        starts = sum(
            1
            for event in self.project()
            if event["event_type"] == "task.started" and event["task_id"] == task_id
        )
        return starts + 1
