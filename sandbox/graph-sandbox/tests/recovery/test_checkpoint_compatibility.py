from __future__ import annotations

import tempfile
import unittest
from unittest import mock
from pathlib import Path

from runner.checkpoints import (
    CheckpointFingerprint,
    CheckpointIncompatible,
    CheckpointStore,
    ObservedCheckpointSaver,
    reconcile_interrupted_checkpoint_events,
)
from runner.events import BoundaryEventStore


REVISION = "1" * 40
CASE_DIGEST = "7" * 64


class CheckpointCompatibilityTests(unittest.TestCase):
    @staticmethod
    def _event_state() -> dict[str, object]:
        return {
            "run_id": "run-healthy-001",
            "case_id": "mission-healthy-001",
            "case_digest": CASE_DIGEST,
            "thread_id": "checkout-payments-timeout-drill-v1:run-healthy-001",
            "source_revision": REVISION,
            "replay_number": 0,
        }

    @staticmethod
    def _checkpoint(checkpoint_id: str) -> dict[str, object]:
        return {
            "v": 4,
            "ts": "2026-08-29T12:00:00.000Z",
            "id": checkpoint_id,
            "channel_values": {},
            "channel_versions": {},
            "versions_seen": {},
        }

    def test_observed_saver_pairs_real_sqlite_checkpoint_write_events(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            events = BoundaryEventStore(root / "events.sqlite3")
            event_state = self._event_state()
            checkpoint = self._checkpoint("checkpoint-001")
            config = {
                "configurable": {
                    "thread_id": event_state["thread_id"],
                    "checkpoint_ns": "",
                }
            }

            with CheckpointStore(
                root / "checkpoints.sqlite3",
                CheckpointFingerprint.current(REVISION),
            ) as delegate:
                observed = ObservedCheckpointSaver(delegate, events, event_state)
                returned = observed.put(config, checkpoint, {}, {})

            self.assertEqual(
                returned["configurable"]["checkpoint_id"],
                "checkpoint-001",
            )
            projected = events.project()
            self.assertEqual(
                [event["event_type"] for event in projected],
                ["checkpoint.write_started", "checkpoint.write_completed"],
            )
            self.assertTrue(
                all(event["checkpoint_id"] == "checkpoint-001" for event in projected)
            )

    def test_recovery_completes_interrupted_write_only_when_saver_has_the_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            events = BoundaryEventStore(root / "events.sqlite3")
            event_state = self._event_state()
            config = {
                "configurable": {
                    "thread_id": event_state["thread_id"],
                    "checkpoint_ns": "",
                }
            }
            events.emit(
                "checkpoint.write_started",
                event_state,
                {"operation": "write"},
                checkpoint_id="checkpoint-001",
            )

            with CheckpointStore(
                root / "checkpoints.sqlite3",
                CheckpointFingerprint.current(REVISION),
            ) as saver:
                saver.put(config, self._checkpoint("checkpoint-001"), {}, {})
                recovered = reconcile_interrupted_checkpoint_events(
                    saver,
                    events,
                    event_state,
                )

            self.assertIsNone(recovered)
            self.assertEqual(
                [event["event_type"] for event in events.project()],
                ["checkpoint.write_started", "checkpoint.write_completed"],
            )

    def test_recovery_completes_interrupted_resume_on_later_saver_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            events = BoundaryEventStore(root / "events.sqlite3")
            event_state = self._event_state()
            config = {
                "configurable": {
                    "thread_id": event_state["thread_id"],
                    "checkpoint_ns": "",
                }
            }

            with CheckpointStore(
                root / "checkpoints.sqlite3",
                CheckpointFingerprint.current(REVISION),
            ) as saver:
                source_config = saver.put(
                    config,
                    self._checkpoint("checkpoint-001"),
                    {},
                    {},
                )
                events.emit(
                    "checkpoint.resume_started",
                    event_state,
                    {"operation": "resume"},
                    checkpoint_id="checkpoint-001",
                )
                saver.put(
                    source_config,
                    self._checkpoint("checkpoint-002"),
                    {},
                    {},
                )
                recovered = reconcile_interrupted_checkpoint_events(
                    saver,
                    events,
                    event_state,
                )

            self.assertEqual(recovered, "checkpoint-001")
            self.assertEqual(
                [event["event_type"] for event in events.project()],
                ["checkpoint.resume_started", "checkpoint.resume_completed"],
            )
            self.assertEqual(events.project()[-1]["checkpoint_id"], "checkpoint-002")

    def test_observer_reports_completed_when_delegate_raises_after_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            events = BoundaryEventStore(root / "events.sqlite3")
            event_state = self._event_state()
            config = {
                "configurable": {
                    "thread_id": event_state["thread_id"],
                    "checkpoint_ns": "",
                }
            }
            with CheckpointStore(
                root / "checkpoints.sqlite3",
                CheckpointFingerprint.current(REVISION),
            ) as delegate:
                original_put = delegate.put

                def commit_then_raise(*args, **kwargs):
                    original_put(*args, **kwargs)
                    raise RuntimeError("after-commit interruption")

                observed = ObservedCheckpointSaver(delegate, events, event_state)
                with mock.patch.object(delegate, "put", side_effect=commit_then_raise):
                    with self.assertRaisesRegex(RuntimeError, "after-commit"):
                        observed.put(config, self._checkpoint("checkpoint-001"), {}, {})

            self.assertEqual(
                [event["event_type"] for event in events.project()],
                ["checkpoint.write_started", "checkpoint.write_completed"],
            )

    def test_observer_leaves_start_pending_when_commit_query_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            events = BoundaryEventStore(root / "events.sqlite3")
            event_state = self._event_state()
            config = {
                "configurable": {
                    "thread_id": event_state["thread_id"],
                    "checkpoint_ns": "",
                }
            }
            with CheckpointStore(
                root / "checkpoints.sqlite3",
                CheckpointFingerprint.current(REVISION),
            ) as delegate:
                observed = ObservedCheckpointSaver(delegate, events, event_state)
                with mock.patch.object(delegate, "put", side_effect=RuntimeError("write failed")):
                    with mock.patch.object(
                        delegate,
                        "get_tuple",
                        side_effect=RuntimeError("query unavailable"),
                    ):
                        with self.assertRaisesRegex(RuntimeError, "write failed"):
                            observed.put(config, self._checkpoint("checkpoint-001"), {}, {})

            self.assertEqual(
                [event["event_type"] for event in events.project()],
                ["checkpoint.write_started"],
            )

    def test_same_fingerprint_can_reopen_checkpoint_store(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "checkpoints.sqlite3"
            fingerprint = CheckpointFingerprint.current(REVISION)

            with CheckpointStore(path, fingerprint):
                pass
            with CheckpointStore(path, fingerprint):
                pass

    def test_source_revision_mismatch_fails_closed_without_replacing_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "checkpoints.sqlite3"
            original = CheckpointFingerprint.current(REVISION)
            with CheckpointStore(path, original):
                pass

            changed = CheckpointFingerprint.current("2" * 40)
            with self.assertRaises(CheckpointIncompatible) as caught:
                with CheckpointStore(path, changed):
                    pass

            self.assertIn("source_revision", caught.exception.mismatches)
            self.assertEqual(CheckpointStore.read_fingerprint(path), original)

    def test_contract_version_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "checkpoints.sqlite3"
            original = CheckpointFingerprint.current(REVISION)
            with CheckpointStore(path, original):
                pass

            changed = CheckpointFingerprint(
                contract_version="checkout-payments-timeout-drill/v2",
                state_schema=original.state_schema,
                source_revision=original.source_revision,
                langgraph_version=original.langgraph_version,
                sqlite_saver_version=original.sqlite_saver_version,
            )
            with self.assertRaises(CheckpointIncompatible):
                with CheckpointStore(path, changed):
                    pass


if __name__ == "__main__":
    unittest.main()
