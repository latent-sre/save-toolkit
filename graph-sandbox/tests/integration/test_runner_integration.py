from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from langgraph.types import Command

from runner.checkpoints import (
    CheckpointFingerprint,
    CheckpointStore,
    ObservedCheckpointSaver,
)
from runner.effects import EffectLedger
from runner.events import BoundaryEventStore
from runner.fixtures import load_case
from runner.gateway import AmbiguousDispatch, CheckoutFailure, derive_child_idempotency_key
from runner.graph import RunnerDependencies, build_graph, emit_terminal_event
from runner.models import new_run_state


REVISION = "1" * 40
CASE_DIGEST = "7" * 64


class FakeGateway:
    def __init__(self) -> None:
        self.checkout_calls = 0

    def health(self, service: str, *, case_id: str) -> dict[str, str]:
        self.last_case_id = case_id
        return {"status": "ok", "service": service}

    def dispatch_checkout(
        self,
        checkout: dict[str, object],
        *,
        idempotency_key: str,
        case_id: str,
        request_id: str,
    ) -> dict[str, object]:
        self.checkout_calls += 1
        return {
            "authoritative_result_id": "checkout-result-001",
            "order_id": checkout["order_id"],
            "completion_class": "COMPLETE",
            "replayed": False,
            "payment_receipt": {
                "receipt_version": "synthetic-receipt/v1",
                "effect_class": "payment",
                "receipt_id": "payment-receipt-001",
                "idempotency_key": "a" * 64,
                "request_digest": "b" * 64,
                "status": "committed",
                "replayed": False,
            },
            "inventory_receipt": {
                "receipt_version": "synthetic-receipt/v1",
                "effect_class": "inventory",
                "receipt_id": "inventory-receipt-001",
                "idempotency_key": "c" * 64,
                "request_digest": "d" * 64,
                "status": "committed",
                "replayed": False,
            },
        }

    def get_checkout_receipt(
        self, idempotency_key: str, *, case_id: str
    ) -> dict[str, object] | None:
        return None

    def get_target_receipt(
        self,
        effect_class: str,
        checkout_idempotency_key: str,
        *,
        case_id: str,
    ) -> dict[str, object] | None:
        return None


class AmbiguousGateway(FakeGateway):
    def __init__(self) -> None:
        super().__init__()
        self.target_receipt_calls: list[str] = []

    def dispatch_checkout(
        self,
        checkout: dict[str, object],
        *,
        idempotency_key: str,
        case_id: str,
        request_id: str,
    ) -> dict[str, object]:
        self.checkout_calls += 1
        raise AmbiguousDispatch("checkout_transport_ambiguous")

    def get_target_receipt(
        self,
        effect_class: str,
        checkout_idempotency_key: str,
        *,
        case_id: str,
    ) -> dict[str, object] | None:
        self.target_receipt_calls.append(effect_class)
        key = derive_child_idempotency_key(checkout_idempotency_key, effect_class)
        return {
            "receipt_version": "synthetic-receipt/v1",
            "effect_class": effect_class,
            "receipt_id": f"{effect_class}-receipt-001",
            "idempotency_key": key,
            "request_digest": "f" * 64,
            "status": "committed",
            "replayed": False,
        }


class NotCommittedGateway(FakeGateway):
    @staticmethod
    def _failure() -> CheckoutFailure:
        return CheckoutFailure(
            "payment_unavailable",
            outcome="not_committed",
            known_receipts={},
        )

    def dispatch_checkout(
        self,
        checkout: dict[str, object],
        *,
        idempotency_key: str,
        case_id: str,
        request_id: str,
    ) -> dict[str, object]:
        self.checkout_calls += 1
        raise self._failure()

    def get_checkout_receipt(
        self, idempotency_key: str, *, case_id: str
    ) -> dict[str, object] | None:
        raise self._failure()

class RunnerGraphIntegrationTests(unittest.TestCase):
    def test_readiness_fanout_interrupt_resume_and_effect_complete_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            case = load_case(Path("/app/cases/mission-healthy-001.json"))
            state = new_run_state(
                case,
                run_id="mission-healthy-001",
                source_revision=REVISION,
                case_digest=CASE_DIGEST,
            )
            gateway = FakeGateway()
            ledger = EffectLedger(root / "effects.sqlite3")
            events = BoundaryEventStore(root / "events.sqlite3")
            dependencies = RunnerDependencies(
                gateway=gateway,
                ledger=ledger,
                events=events,
                case=case,
            )
            config = {"configurable": {"thread_id": state["thread_id"]}}

            with CheckpointStore(
                root / "checkpoints.sqlite3",
                CheckpointFingerprint.current(REVISION),
            ) as checkpointer:
                graph = build_graph(
                    dependencies,
                    ObservedCheckpointSaver(checkpointer, events, state),
                )
                paused = graph.invoke(state, config)
                self.assertIn("__interrupt__", paused)

                completed = graph.invoke(
                    Command(
                        resume={
                            "decision": "APPROVED",
                            "actor_class": "fixture-operator",
                            "decision_time": "2026-08-29T12:00:01.000Z",
                        }
                    ),
                    config,
                )

            emit_terminal_event(events, completed)
            self.assertEqual(completed["outcome"], "SUCCEEDED")
            self.assertEqual(gateway.checkout_calls, 1)
            self.assertEqual(set(completed["readiness"]), {"checkout", "payments", "inventory"})
            self.assertTrue(all(item["status"] == "ok" for item in completed["readiness"].values()))
            self.assertEqual(ledger.current(
                "mission-healthy-001:checkout_effect:0:effect-checkout"
            )["effect_state"], "RECEIPT_RECORDED")
            event_types = [event["event_type"] for event in events.project()]
            self.assertIn("edge.fanout_emitted", event_types)
            self.assertIn("edge.join_satisfied", event_types)
            self.assertIn("approval.requested", event_types)
            self.assertIn("approval.approved", event_types)
            self.assertIn("effect.receipt_recorded", event_types)
            self.assertIn("checkpoint.write_completed", event_types)
            self.assertEqual(event_types[-1], "run.terminal")

    def test_timeout_fixture_never_resumes_or_dispatches_effect(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            case = load_case(Path("/app/cases/mission-healthy-001.json"))
            state = new_run_state(
                case,
                run_id="mission-healthy-001",
                source_revision=REVISION,
                case_digest=CASE_DIGEST,
            )
            gateway = FakeGateway()
            ledger = EffectLedger(root / "effects.sqlite3")
            events = BoundaryEventStore(root / "events.sqlite3")
            dependencies = RunnerDependencies(
                gateway=gateway,
                ledger=ledger,
                events=events,
                case=case,
                approval_fixture="TIMEOUT",
            )
            config = {"configurable": {"thread_id": state["thread_id"]}}

            with CheckpointStore(
                root / "checkpoints.sqlite3",
                CheckpointFingerprint.current(REVISION),
            ) as checkpointer:
                graph = build_graph(dependencies, checkpointer)
                completed = graph.invoke(state, config)

            emit_terminal_event(events, completed)
            self.assertNotIn("__interrupt__", completed)
            self.assertEqual(completed["outcome"], "REJECTED")
            self.assertEqual(gateway.checkout_calls, 0)
            event_types = [event["event_type"] for event in events.project()]
            self.assertIn("approval.requested", event_types)
            self.assertIn("approval.timed_out", event_types)
            self.assertNotIn("approval.approved", event_types)

    def test_completed_effect_with_exhausted_wall_budget_is_not_run_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            case = load_case(Path("/app/cases/mission-healthy-001.json"))
            state = new_run_state(
                case,
                run_id="run-wall-budget-001",
                source_revision=REVISION,
                case_digest=CASE_DIGEST,
            )
            gateway = FakeGateway()
            events = BoundaryEventStore(root / "events.sqlite3")
            dependencies = RunnerDependencies(
                gateway=gateway,
                ledger=EffectLedger(root / "effects.sqlite3"),
                events=events,
                case=case,
                monotonic_clock=lambda: 121.0,
                started_monotonic=0.0,
            )
            config = {"configurable": {"thread_id": state["thread_id"]}}

            with CheckpointStore(
                root / "checkpoints.sqlite3",
                CheckpointFingerprint.current(REVISION),
            ) as checkpointer:
                graph = build_graph(dependencies, checkpointer)
                self.assertIn("__interrupt__", graph.invoke(state, config))
                completed = graph.invoke(
                    Command(
                        resume={
                            "decision": "APPROVED",
                            "actor_class": "fixture-operator",
                        }
                    ),
                    config,
                )

            emit_terminal_event(events, completed)
            self.assertEqual(completed["outcome"], "FAILED")
            self.assertEqual(completed["checkout_status"], "COMPLETE")
            self.assertEqual(completed["budgets"]["wall_time_ms"]["consumed"], 120000)
            self.assertEqual(completed["failure"]["error_class"], "budget_exhausted")
            self.assertEqual(gateway.checkout_calls, 1)
            self.assertIn("budget.exhausted", [event["event_type"] for event in events.project()])

    def test_resumed_process_cannot_reset_wall_budget_before_checkout_effect(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            case = load_case(Path("/app/cases/mission-healthy-001.json"))
            state = new_run_state(
                case,
                run_id="run-wall-resume-001",
                source_revision=REVISION,
                case_digest=CASE_DIGEST,
            )
            gateway = FakeGateway()
            ledger = EffectLedger(root / "effects.sqlite3")
            events = BoundaryEventStore(root / "events.sqlite3")
            config = {"configurable": {"thread_id": state["thread_id"]}}

            with CheckpointStore(
                root / "checkpoints.sqlite3",
                CheckpointFingerprint.current(REVISION),
            ) as checkpointer:
                first_process = RunnerDependencies(
                    gateway=gateway,
                    ledger=ledger,
                    events=events,
                    case=case,
                    wall_time_elapsed_ms=lambda: 1_000,
                )
                paused = build_graph(first_process, checkpointer).invoke(state, config)
                self.assertIn("__interrupt__", paused)

                resumed_process = RunnerDependencies(
                    gateway=gateway,
                    ledger=ledger,
                    events=events,
                    case=case,
                    wall_time_elapsed_ms=lambda: 121_000,
                )
                completed = build_graph(resumed_process, checkpointer).invoke(
                    Command(
                        resume={
                            "decision": "APPROVED",
                            "actor_class": "fixture-operator",
                        }
                    ),
                    config,
                )

            self.assertEqual(completed["outcome"], "FAILED")
            self.assertEqual(completed["checkout_status"], "NOT_STARTED")
            self.assertEqual(completed["budgets"]["wall_time_ms"]["consumed"], 120_000)
            self.assertEqual(completed["failure"]["error_class"], "budget_exhausted")
            self.assertEqual(gateway.checkout_calls, 0)
            exhausted = [
                event for event in events.project() if event["event_type"] == "budget.exhausted"
            ]
            self.assertEqual(len(exhausted), 1)
            self.assertEqual(exhausted[0]["node_id"], "checkout_effect")

    def test_exhausted_model_budget_stops_before_approval_and_effect(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            case = copy.deepcopy(load_case(Path("/app/cases/mission-healthy-001.json")))
            case["budgets"]["model_calls"]["limit"] = 0
            state = new_run_state(
                case,
                run_id="mission-healthy-001",
                source_revision=REVISION,
                case_digest=CASE_DIGEST,
            )
            gateway = FakeGateway()
            events = BoundaryEventStore(root / "events.sqlite3")
            dependencies = RunnerDependencies(
                gateway=gateway,
                ledger=EffectLedger(root / "effects.sqlite3"),
                events=events,
                case=case,
            )
            config = {"configurable": {"thread_id": state["thread_id"]}}

            with CheckpointStore(
                root / "checkpoints.sqlite3",
                CheckpointFingerprint.current(REVISION),
            ) as checkpointer:
                completed = build_graph(dependencies, checkpointer).invoke(state, config)

            emit_terminal_event(events, completed)
            self.assertEqual(completed["outcome"], "FAILED")
            self.assertEqual(gateway.checkout_calls, 0)
            event_types = [event["event_type"] for event in events.project()]
            self.assertIn("budget.exhausted", event_types)
            self.assertNotIn("approval.requested", event_types)
            self.assertNotIn("effect.prepared", event_types)

    def test_pre_admission_cancellation_is_acknowledged_without_scheduling(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            case = load_case(Path("/app/cases/mission-healthy-001.json"))
            state = new_run_state(
                case,
                run_id="mission-healthy-001",
                source_revision=REVISION,
                case_digest=CASE_DIGEST,
            )
            state["cancellation"] = {
                "state": "REQUESTED",
                "request_id": "cancel-001",
                "acknowledgement_ms": None,
            }
            gateway = FakeGateway()
            events = BoundaryEventStore(root / "events.sqlite3")
            dependencies = RunnerDependencies(
                gateway=gateway,
                ledger=EffectLedger(root / "effects.sqlite3"),
                events=events,
                case=case,
            )
            config = {"configurable": {"thread_id": state["thread_id"]}}

            with CheckpointStore(
                root / "checkpoints.sqlite3",
                CheckpointFingerprint.current(REVISION),
            ) as checkpointer:
                completed = build_graph(dependencies, checkpointer).invoke(state, config)

            emit_terminal_event(events, completed)
            self.assertEqual(completed["outcome"], "CANCELLED")
            self.assertEqual(completed["cancellation"]["state"], "ACKNOWLEDGED")
            self.assertEqual(gateway.checkout_calls, 0)
            event_types = [event["event_type"] for event in events.project()]
            self.assertIn("cancellation.propagated", event_types)
            self.assertIn("cancellation.acknowledged", event_types)
            self.assertNotIn("edge.fanout_emitted", event_types)

    def test_ambiguous_checkout_refuses_replay_and_preserves_target_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            case = load_case(Path("/app/cases/mission-healthy-001.json"))
            state = new_run_state(
                case,
                run_id="mission-healthy-001",
                source_revision=REVISION,
                case_digest=CASE_DIGEST,
            )
            gateway = AmbiguousGateway()
            ledger = EffectLedger(root / "effects.sqlite3")
            events = BoundaryEventStore(root / "events.sqlite3")
            dependencies = RunnerDependencies(
                gateway=gateway,
                ledger=ledger,
                events=events,
                case=case,
            )
            config = {"configurable": {"thread_id": state["thread_id"]}}

            with CheckpointStore(
                root / "checkpoints.sqlite3",
                CheckpointFingerprint.current(REVISION),
            ) as checkpointer:
                graph = build_graph(dependencies, checkpointer)
                paused = graph.invoke(state, config)
                self.assertIn("__interrupt__", paused)
                completed = graph.invoke(
                    Command(
                        resume={
                            "decision": "APPROVED",
                            "actor_class": "fixture-operator",
                        }
                    ),
                    config,
                )

            emit_terminal_event(events, completed)
            self.assertEqual(completed["outcome"], "UNKNOWN")
            self.assertEqual(gateway.checkout_calls, 1)
            self.assertEqual(gateway.target_receipt_calls, ["payment", "inventory"])
            self.assertIn(
                "mission-healthy-001:checkout_effect:0:effect-payment",
                completed["receipts"],
            )
            self.assertIn(
                "mission-healthy-001:checkout_effect:0:effect-inventory",
                completed["receipts"],
            )
            self.assertEqual(
                ledger.current("mission-healthy-001:checkout_effect:0:effect-checkout")[
                    "effect_state"
                ],
                "UNKNOWN",
            )
            event_types = [event["event_type"] for event in events.project()]
            self.assertIn("effect.unknown", event_types)
            self.assertIn("effect.replay_refused", event_types)
            self.assertNotIn("effect.reconciled", event_types)

    def test_cancellation_during_approval_wait_quarantines_late_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            case = load_case(Path("/app/cases/mission-healthy-001.json"))
            state = new_run_state(
                case,
                run_id="mission-healthy-001",
                source_revision=REVISION,
                case_digest=CASE_DIGEST,
            )
            gateway = FakeGateway()
            events = BoundaryEventStore(root / "events.sqlite3")
            dependencies = RunnerDependencies(
                gateway=gateway,
                ledger=EffectLedger(root / "effects.sqlite3"),
                events=events,
                case=case,
            )
            config = {"configurable": {"thread_id": state["thread_id"]}}

            with CheckpointStore(
                root / "checkpoints.sqlite3",
                CheckpointFingerprint.current(REVISION),
            ) as checkpointer:
                graph = build_graph(dependencies, checkpointer)
                paused = graph.invoke(state, config)
                self.assertIn("__interrupt__", paused)
                graph.update_state(
                    config,
                    {
                        "cancellation": {
                            "state": "REQUESTED",
                            "request_id": "cancel-approval-001",
                            "acknowledgement_ms": None,
                        }
                    },
                )
                completed = graph.invoke(
                    Command(
                        resume={
                            "decision": "APPROVED",
                            "actor_class": "fixture-operator",
                        }
                    ),
                    config,
                )

            emit_terminal_event(events, completed)
            self.assertEqual(completed["outcome"], "CANCELLED")
            self.assertEqual(completed["cancellation"]["state"], "ACKNOWLEDGED")
            self.assertEqual(gateway.checkout_calls, 0)
            event_types = [event["event_type"] for event in events.project()]
            self.assertIn("cancellation.requested", event_types)
            self.assertIn("cancellation.propagated", event_types)
            self.assertIn("cancellation.acknowledged", event_types)
            self.assertNotIn("approval.approved", event_types)
            self.assertNotIn("effect.prepared", event_types)

    def test_authoritative_not_committed_failure_is_failed_without_replay(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            case = load_case(Path("/app/cases/payments-http-error-001.json"))
            state = new_run_state(
                case,
                run_id="run-payment-error-001",
                source_revision=REVISION,
                case_digest=CASE_DIGEST,
            )
            gateway = NotCommittedGateway()
            ledger = EffectLedger(root / "effects.sqlite3")
            events = BoundaryEventStore(root / "events.sqlite3")
            dependencies = RunnerDependencies(
                gateway=gateway,
                ledger=ledger,
                events=events,
                case=case,
            )
            config = {"configurable": {"thread_id": state["thread_id"]}}

            with CheckpointStore(
                root / "checkpoints.sqlite3",
                CheckpointFingerprint.current(REVISION),
            ) as checkpointer:
                graph = build_graph(dependencies, checkpointer)
                self.assertIn("__interrupt__", graph.invoke(state, config))
                completed = graph.invoke(
                    Command(
                        resume={
                            "decision": "APPROVED",
                            "actor_class": "fixture-operator",
                        }
                    ),
                    config,
                )

            emit_terminal_event(events, completed)
            self.assertEqual(completed["outcome"], "FAILED")
            self.assertEqual(completed["checkout_status"], "FAILED")
            self.assertEqual(completed["pending_effects"], [])
            self.assertEqual(gateway.checkout_calls, 1)
            self.assertEqual(
                ledger.current(
                    "run-payment-error-001:checkout_effect:0:effect-checkout"
                )["effect_state"],
                "UNKNOWN",
            )
            event_types = [event["event_type"] for event in events.project()]
            self.assertIn("effect.replay_refused", event_types)
            self.assertEqual(event_types[-1], "run.terminal")


if __name__ == "__main__":
    unittest.main()
