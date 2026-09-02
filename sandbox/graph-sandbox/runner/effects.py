from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from runner.models import CONTRACT_VERSION
from runner.events import BoundaryEventStore
from runner.validation import validate_atomic_id, validate_derived_id, validate_sha256


class InvalidEffectTransition(RuntimeError):
    pass


class ReplayRefused(RuntimeError):
    pass


def derive_idempotency_key(effect_id: str) -> str:
    validate_derived_id(effect_id, "effect_id")
    material = f"{CONTRACT_VERSION}\n{effect_id}".encode("ascii")
    return hashlib.sha256(material).hexdigest()


_ALLOWED_TRANSITIONS = {
    "PREPARED": {"DISPATCHED", "UNKNOWN"},
    "DISPATCHED": {"RECEIPT_RECORDED", "UNKNOWN"},
    "UNKNOWN": {"RECONCILED"},
    "RECEIPT_RECORDED": set(),
    "RECONCILED": set(),
}


class EffectLedger:
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
                CREATE TABLE IF NOT EXISTS effect_transitions (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    effect_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    attempt_id TEXT NOT NULL,
                    replay_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    target TEXT NOT NULL,
                    effect_state TEXT NOT NULL CHECK (
                        effect_state IN (
                            'PREPARED', 'DISPATCHED', 'RECEIPT_RECORDED',
                            'UNKNOWN', 'RECONCILED'
                        )
                    ),
                    time_utc TEXT NOT NULL,
                    reason_class TEXT,
                    receipt_json TEXT
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS effect_id_sequence ON effect_transitions(effect_id, sequence)"
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS validate_effect_transition
                BEFORE INSERT ON effect_transitions
                BEGIN
                    SELECT CASE
                        WHEN NOT EXISTS (
                            SELECT 1 FROM effect_transitions WHERE effect_id = NEW.effect_id
                        ) AND NEW.effect_state != 'PREPARED'
                        THEN RAISE(ABORT, 'first effect transition must be PREPARED')
                    END;
                    SELECT CASE
                        WHEN EXISTS (
                            SELECT 1 FROM effect_transitions WHERE effect_id = NEW.effect_id
                        ) AND NOT EXISTS (
                            SELECT 1
                            FROM effect_transitions previous
                            WHERE previous.effect_id = NEW.effect_id
                              AND previous.sequence = (
                                  SELECT MAX(sequence)
                                  FROM effect_transitions
                                  WHERE effect_id = NEW.effect_id
                              )
                              AND (
                                  (previous.effect_state = 'PREPARED'
                                   AND NEW.effect_state IN ('DISPATCHED', 'UNKNOWN'))
                                  OR (previous.effect_state = 'DISPATCHED'
                                      AND NEW.effect_state IN ('RECEIPT_RECORDED', 'UNKNOWN'))
                                  OR (previous.effect_state = 'UNKNOWN'
                                      AND NEW.effect_state = 'RECONCILED')
                              )
                        )
                        THEN RAISE(ABORT, 'invalid effect state transition')
                    END;
                    SELECT CASE
                        WHEN EXISTS (
                            SELECT 1
                            FROM effect_transitions previous
                            WHERE previous.effect_id = NEW.effect_id
                              AND (
                                  previous.idempotency_key != NEW.idempotency_key
                                  OR previous.payload_hash != NEW.payload_hash
                                  OR previous.target != NEW.target
                              )
                        )
                        THEN RAISE(ABORT, 'effect identity fields are immutable')
                    END;
                END
                """
            )

    def prepare(
        self,
        effect_id: str,
        idempotency_key: str,
        payload_hash: str,
        target: str,
        *,
        attempt_id: str | None = None,
        replay_id: str | None = None,
    ) -> dict[str, object]:
        validate_derived_id(effect_id, "effect_id")
        validate_sha256(idempotency_key, "idempotency_key")
        validate_sha256(payload_hash, "payload_hash")
        validate_atomic_id(target, "target")
        expected_key = derive_idempotency_key(effect_id)
        if idempotency_key != expected_key:
            raise ValueError("idempotency_key does not match the contract derivation")

        current = self.current(effect_id)
        if current is not None:
            self._require_stable(current, idempotency_key, payload_hash, target)
            if current["effect_state"] == "PREPARED":
                return current
            raise InvalidEffectTransition(
                f"cannot prepare effect in {current['effect_state']} state"
            )
        return self._append(
            effect_id,
            idempotency_key=idempotency_key,
            payload_hash=payload_hash,
            target=target,
            next_state="PREPARED",
            attempt_id=attempt_id,
            replay_id=replay_id,
        )

    def mark_dispatched(
        self,
        effect_id: str,
        *,
        attempt_id: str | None = None,
        replay_id: str | None = None,
    ) -> dict[str, object]:
        return self._transition(
            effect_id,
            "DISPATCHED",
            attempt_id=attempt_id,
            replay_id=replay_id,
        )

    def record_receipt(
        self,
        effect_id: str,
        receipt: Mapping[str, object],
        *,
        attempt_id: str | None = None,
        replay_id: str | None = None,
    ) -> dict[str, object]:
        self._require_authoritative_receipt(receipt)
        return self._transition(
            effect_id,
            "RECEIPT_RECORDED",
            receipt=receipt,
            attempt_id=attempt_id,
            replay_id=replay_id,
        )

    def mark_unknown(
        self,
        effect_id: str,
        reason_class: str,
        *,
        attempt_id: str | None = None,
        replay_id: str | None = None,
    ) -> dict[str, object]:
        validate_atomic_id(reason_class, "reason_class")
        current = self.current(effect_id)
        if current is not None and current["effect_state"] == "UNKNOWN":
            return current
        return self._transition(
            effect_id,
            "UNKNOWN",
            reason_class=reason_class,
            attempt_id=attempt_id,
            replay_id=replay_id,
        )

    def reconcile(
        self,
        effect_id: str,
        receipt: Mapping[str, object],
        *,
        attempt_id: str | None = None,
        replay_id: str | None = None,
    ) -> dict[str, object]:
        self._require_authoritative_receipt(receipt)
        return self._transition(
            effect_id,
            "RECONCILED",
            receipt=receipt,
            attempt_id=attempt_id,
            replay_id=replay_id,
        )

    def require_replay_safe(self, effect_id: str, *, explicit_replay: bool) -> None:
        current = self.current(effect_id)
        if current is None:
            return
        if current["effect_state"] == "UNKNOWN" and not explicit_replay:
            raise ReplayRefused(f"automatic replay refused for {effect_id}")

    def current(self, effect_id: str) -> dict[str, Any] | None:
        validate_derived_id(effect_id, "effect_id")
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT sequence, effect_id, task_id, attempt_id, replay_id,
                       idempotency_key, payload_hash, target,
                       effect_state, time_utc, reason_class, receipt_json
                FROM effect_transitions
                WHERE effect_id = ?
                ORDER BY sequence DESC
                LIMIT 1
                """,
                (effect_id,),
            ).fetchone()
        return None if row is None else self._project_row(row)

    def project(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT sequence, effect_id, task_id, attempt_id, replay_id,
                       idempotency_key, payload_hash, target,
                       effect_state, time_utc, reason_class, receipt_json
                FROM effect_transitions
                ORDER BY sequence
                """
            ).fetchall()
        return [self._project_row(row) for row in rows]

    def _transition(
        self,
        effect_id: str,
        next_state: str,
        *,
        reason_class: str | None = None,
        receipt: Mapping[str, object] | None = None,
        attempt_id: str | None = None,
        replay_id: str | None = None,
    ) -> dict[str, object]:
        current = self.current(effect_id)
        if current is None:
            if next_state == "DISPATCHED":
                raise InvalidEffectTransition(f"{effect_id} is missing PREPARED")
            raise InvalidEffectTransition(f"{effect_id} has no prepared effect")
        if current["effect_state"] == next_state:
            return current
        allowed = _ALLOWED_TRANSITIONS[current["effect_state"]]
        if next_state not in allowed:
            raise InvalidEffectTransition(
                f"invalid effect transition {current['effect_state']} -> {next_state}"
            )
        return self._append(
            effect_id,
            idempotency_key=current["idempotency_key"],
            payload_hash=current["payload_hash"],
            target=current["target"],
            next_state=next_state,
            reason_class=reason_class,
            receipt=receipt,
            attempt_id=attempt_id or cast(str, current["attempt_id"]),
            replay_id=replay_id or cast(str, current["replay_id"]),
        )

    def _append(
        self,
        effect_id: str,
        *,
        idempotency_key: str,
        payload_hash: str,
        target: str,
        next_state: str,
        reason_class: str | None = None,
        receipt: Mapping[str, object] | None = None,
        attempt_id: str | None = None,
        replay_id: str | None = None,
    ) -> dict[str, object]:
        task_id = effect_id.rsplit(":effect-", 1)[0]
        attempt_id = attempt_id or f"{task_id}:attempt-1"
        replay_id = replay_id or f"{effect_id.split(':', 1)[0]}:replay-0"
        validate_derived_id(task_id, "task_id")
        validate_derived_id(attempt_id, "attempt_id")
        validate_derived_id(replay_id, "replay_id")
        time_utc = self._clock().astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        receipt_json = (
            None
            if receipt is None
            else json.dumps(dict(receipt), sort_keys=True, separators=(",", ":"))
        )
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                cursor = connection.execute(
                    """
                    INSERT INTO effect_transitions(
                        effect_id, task_id, attempt_id, replay_id,
                        idempotency_key, payload_hash, target, effect_state,
                        time_utc, reason_class, receipt_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        effect_id,
                        task_id,
                        attempt_id,
                        replay_id,
                        idempotency_key,
                        payload_hash,
                        target,
                        next_state,
                        time_utc,
                        reason_class,
                        receipt_json,
                    ),
                )
                sequence = cursor.lastrowid
        except sqlite3.IntegrityError as exc:
            raise InvalidEffectTransition(str(exc)) from exc
        return {
            "sequence": sequence,
            "effect_id": effect_id,
            "task_id": task_id,
            "attempt_id": attempt_id,
            "replay_id": replay_id,
            "idempotency_key": idempotency_key,
            "payload_hash": payload_hash,
            "target": target,
            "effect_state": next_state,
            "time_utc": time_utc,
            "reason_class": reason_class,
            "receipt": None if receipt is None else dict(receipt),
        }

    @staticmethod
    def _project_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "sequence": row["sequence"],
            "effect_id": row["effect_id"],
            "task_id": row["task_id"],
            "attempt_id": row["attempt_id"],
            "replay_id": row["replay_id"],
            "idempotency_key": row["idempotency_key"],
            "payload_hash": row["payload_hash"],
            "target": row["target"],
            "effect_state": row["effect_state"],
            "time_utc": row["time_utc"],
            "reason_class": row["reason_class"],
            "receipt": None if row["receipt_json"] is None else json.loads(row["receipt_json"]),
        }

    @staticmethod
    def _require_stable(
        current: Mapping[str, object],
        idempotency_key: str,
        payload_hash: str,
        target: str,
    ) -> None:
        for field, proposed in (
            ("idempotency_key", idempotency_key),
            ("payload_hash", payload_hash),
            ("target", target),
        ):
            if current[field] != proposed:
                raise ValueError(f"conflicting {field} for existing effect")

    @staticmethod
    def _require_authoritative_receipt(receipt: Mapping[str, object]) -> None:
        if not isinstance(receipt.get("authoritative_result_id"), str):
            raise ValueError("receipt requires authoritative_result_id")
        if receipt.get("completion_class") != "COMPLETE":
            raise ValueError("receipt requires completion_class COMPLETE")


def reconcile_effect_transition_events(
    ledger: EffectLedger,
    events: BoundaryEventStore,
    event_state: Mapping[str, object],
) -> None:
    """Reconstruct only crash-missing boundary events from durable ledger rows."""

    event_type_by_state = {
        "PREPARED": "effect.prepared",
        "DISPATCHED": "effect.dispatched",
        "RECEIPT_RECORDED": "effect.receipt_recorded",
        "UNKNOWN": "effect.unknown",
        "RECONCILED": "effect.reconciled",
    }
    existing = events.project()
    for record in ledger.project():
        event_type = event_type_by_state[record["effect_state"]]
        matches = [
            event
            for event in existing
            if event["event_type"] == event_type
            and event["effect_id"] == record["effect_id"]
        ]
        if len(matches) > 1:
            raise RuntimeError("effect transition has duplicate boundary events")
        if matches:
            continue
        state = record["effect_state"]
        data: dict[str, object] = {
            "effect_class": "checkout",
            "effect_state": state,
        }
        failure_plane = None
        error_class = None
        if state == "UNKNOWN":
            data["reason_class"] = record["reason_class"]
            failure_plane = "checkout"
            error_class = cast(str, record["reason_class"])
        elif state in {"RECEIPT_RECORDED", "RECONCILED"}:
            receipt = cast(Mapping[str, object], record["receipt"])
            data["authoritative_result_id"] = receipt["authoritative_result_id"]
        events.emit(
            event_type,
            event_state,
            data,
            node_id=("reconcile_if_ambiguous" if state == "RECONCILED" else "checkout_effect"),
            task_id=cast(str, record["task_id"]),
            attempt_id=cast(str, record["attempt_id"]),
            effect_id=cast(str, record["effect_id"]),
            failure_plane=failure_plane,
            error_class=error_class,
        )
        existing = events.project()
