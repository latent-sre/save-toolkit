from __future__ import annotations

import hashlib
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from runner.effects import (
    EffectLedger,
    InvalidEffectTransition,
    ReplayRefused,
    derive_idempotency_key,
    reconcile_effect_transition_events,
)
from runner.events import BoundaryEventStore


EFFECT_ID = "mission-healthy-001:checkout_effect:0:effect-checkout"
PAYLOAD_HASH = hashlib.sha256(b"synthetic-payload").hexdigest()
FIXED_TIME = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)


class EffectLedgerRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.ledger_path = Path(self.temp_dir.name) / "effects.sqlite3"
        self.ledger = EffectLedger(self.ledger_path, clock=lambda: FIXED_TIME)

    def test_happy_effect_transitions_are_append_only(self) -> None:
        key = derive_idempotency_key(EFFECT_ID)

        self.ledger.prepare(EFFECT_ID, key, PAYLOAD_HASH, "checkout")
        self.ledger.mark_dispatched(EFFECT_ID)
        self.ledger.record_receipt(
            EFFECT_ID,
            {
                "authoritative_result_id": "checkout-result-001",
                "completion_class": "COMPLETE",
            },
        )

        projection = self.ledger.project()
        self.assertEqual(
            [entry["effect_state"] for entry in projection],
            ["PREPARED", "DISPATCHED", "RECEIPT_RECORDED"],
        )
        self.assertTrue(all(entry["idempotency_key"] == key for entry in projection))
        self.assertTrue(all("payload" not in entry for entry in projection))

    def test_dispatch_without_receipt_becomes_unknown_and_replay_is_refused(self) -> None:
        key = derive_idempotency_key(EFFECT_ID)
        self.ledger.prepare(EFFECT_ID, key, PAYLOAD_HASH, "checkout")
        self.ledger.mark_dispatched(EFFECT_ID)
        self.ledger.mark_unknown(EFFECT_ID, "transport_ambiguous")

        with self.assertRaises(ReplayRefused):
            self.ledger.require_replay_safe(EFFECT_ID, explicit_replay=False)

        self.assertEqual(self.ledger.current(EFFECT_ID)["effect_state"], "UNKNOWN")

    def test_unknown_can_only_reconcile_with_authoritative_receipt(self) -> None:
        key = derive_idempotency_key(EFFECT_ID)
        self.ledger.prepare(EFFECT_ID, key, PAYLOAD_HASH, "checkout")
        self.ledger.mark_dispatched(EFFECT_ID)
        self.ledger.mark_unknown(EFFECT_ID, "runner_restart_after_dispatch")

        with self.assertRaisesRegex(ValueError, "authoritative_result_id"):
            self.ledger.reconcile(EFFECT_ID, {"completion_class": "COMPLETE"})

        self.ledger.reconcile(
            EFFECT_ID,
            {
                "authoritative_result_id": "checkout-result-001",
                "completion_class": "COMPLETE",
            },
        )
        self.assertEqual(self.ledger.current(EFFECT_ID)["effect_state"], "RECONCILED")

    def test_transition_cannot_skip_prepared(self) -> None:
        with self.assertRaisesRegex(InvalidEffectTransition, "missing PREPARED"):
            self.ledger.mark_dispatched(EFFECT_ID)

    def test_database_trigger_rejects_transition_bypass_in_same_transaction(self) -> None:
        key = derive_idempotency_key(EFFECT_ID)
        self.ledger.prepare(EFFECT_ID, key, PAYLOAD_HASH, "checkout")

        with sqlite3.connect(self.ledger_path) as connection:
            with self.assertRaisesRegex(sqlite3.IntegrityError, "invalid effect state transition"):
                connection.execute(
                    """
                    INSERT INTO effect_transitions(
                        effect_id, task_id, attempt_id, replay_id,
                        idempotency_key, payload_hash, target, effect_state,
                        time_utc, reason_class, receipt_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        EFFECT_ID,
                        "mission-healthy-001:checkout_effect:0",
                        "mission-healthy-001:checkout_effect:0:attempt-2",
                        "mission-healthy-001:replay-0",
                        key,
                        PAYLOAD_HASH,
                        "checkout",
                        "RECONCILED",
                        "2026-08-29T12:00:00.000Z",
                        None,
                        "{}",
                    ),
                )

    def test_reopening_database_preserves_unknown_state(self) -> None:
        key = derive_idempotency_key(EFFECT_ID)
        self.ledger.prepare(EFFECT_ID, key, PAYLOAD_HASH, "checkout")
        self.ledger.mark_dispatched(EFFECT_ID)
        self.ledger.mark_unknown(EFFECT_ID, "runner_restart_after_dispatch")

        reopened = EffectLedger(self.ledger_path, clock=lambda: FIXED_TIME)

        self.assertEqual(reopened.current(EFFECT_ID)["effect_state"], "UNKNOWN")
        with self.assertRaises(ReplayRefused):
            reopened.require_replay_safe(EFFECT_ID, explicit_replay=False)

    def test_recovery_reconstructs_one_crash_missing_event_per_durable_transition(self) -> None:
        key = derive_idempotency_key(EFFECT_ID)
        self.ledger.prepare(EFFECT_ID, key, PAYLOAD_HASH, "checkout")
        self.ledger.mark_dispatched(EFFECT_ID)
        events = BoundaryEventStore(Path(self.temp_dir.name) / "events.sqlite3")
        state = {
            "run_id": "mission-healthy-001",
            "case_id": "mission-healthy-001",
            "case_digest": "7" * 64,
            "thread_id": "checkout-payments-timeout-drill-v1:mission-healthy-001",
            "source_revision": "1" * 40,
            "replay_number": 0,
        }

        reconcile_effect_transition_events(self.ledger, events, state)
        reconcile_effect_transition_events(self.ledger, events, state)

        self.assertEqual(
            [event["event_type"] for event in events.project()],
            ["effect.prepared", "effect.dispatched"],
        )


if __name__ == "__main__":
    unittest.main()
