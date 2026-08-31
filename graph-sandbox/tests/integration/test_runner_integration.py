from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from contextlib import nullcontext
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

from langgraph.types import Command

from runner.budgets import DurableWallTimeBudget
from runner.checkpoints import (
    CheckpointFingerprint,
    CheckpointStore,
    ObservedCheckpointSaver,
)
from runner.effects import EffectLedger
from runner.evidence import (
    EvidenceExporter,
    ExistingSnapshotInvalid,
    validate_unknown_snapshot,
)
from runner.events import BoundaryEventStore
from runner.fixtures import load_case
from runner.gateway import (
    AmbiguousDispatch,
    CheckoutFailure,
    GatewayUnavailable,
    derive_child_idempotency_key,
)
from runner.graph import (
    RunnerDependencies,
    build_graph,
    emit_terminal_event,
    ensure_run_started_events,
)
from runner.main import (
    RunnerConfig,
    _checkpoint_lineage,
    _execute_graph,
    _export_evidence,
    _latest_completed_resume_source,
    _snapshot_terminal_event,
    run,
)
from runner.models import GraphState, new_run_state


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


class ReconciledAfterLostResponseGateway(FakeGateway):
    def __init__(self) -> None:
        super().__init__()
        self.receipt: dict[str, object] | None = None
        self.receipt_lookups = 0

    def dispatch_checkout(
        self,
        checkout: dict[str, object],
        *,
        idempotency_key: str,
        case_id: str,
        request_id: str,
    ) -> dict[str, object]:
        self.receipt = super().dispatch_checkout(
            checkout,
            idempotency_key=idempotency_key,
            case_id=case_id,
            request_id=request_id,
        )
        raise AmbiguousDispatch("checkout_transport_ambiguous")

    def get_checkout_receipt(
        self, idempotency_key: str, *, case_id: str
    ) -> dict[str, object] | None:
        self.receipt_lookups += 1
        return self.receipt


class TransientReconciliationFailureGateway(ReconciledAfterLostResponseGateway):
    def get_checkout_receipt(
        self, idempotency_key: str, *, case_id: str
    ) -> dict[str, object] | None:
        self.receipt_lookups += 1
        if self.receipt_lookups == 1:
            raise GatewayUnavailable("checkout", "receipt_transport_failure")
        return self.receipt


class SimulatedProcessCrash(BaseException):
    pass


class CrashAfterDurableUnknownGateway(ReconciledAfterLostResponseGateway):
    def __init__(self, ledger: EffectLedger) -> None:
        super().__init__()
        self.ledger = ledger
        self.crash_reconciliation_once = True

    def dispatch_checkout(
        self,
        checkout: dict[str, object],
        *,
        idempotency_key: str,
        case_id: str,
        request_id: str,
    ) -> dict[str, object]:
        self.receipt = FakeGateway.dispatch_checkout(
            self,
            checkout,
            idempotency_key=idempotency_key,
            case_id=case_id,
            request_id=request_id,
        )
        current = self.ledger.project()[-1]
        self.ledger.mark_unknown(
            current["effect_id"],
            "checkout_transport_ambiguous",
            attempt_id=current["attempt_id"],
            replay_id=current["replay_id"],
        )
        raise SimulatedProcessCrash("after durable UNKNOWN")

    def get_checkout_receipt(
        self, idempotency_key: str, *, case_id: str
    ) -> dict[str, object] | None:
        self.receipt_lookups += 1
        if self.crash_reconciliation_once:
            self.crash_reconciliation_once = False
            raise SimulatedProcessCrash("after UNKNOWN snapshot export")
        return self.receipt


class UnavailableAfterLostResponseGateway(ReconciledAfterLostResponseGateway):
    def get_checkout_receipt(
        self, idempotency_key: str, *, case_id: str
    ) -> dict[str, object] | None:
        self.receipt_lookups += 1
        raise GatewayUnavailable("checkout", "receipt_transport_failure")


class UnavailableReconciliationGateway(FakeGateway):
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

    def get_checkout_receipt(
        self, idempotency_key: str, *, case_id: str
    ) -> dict[str, object] | None:
        raise GatewayUnavailable("checkout", "receipt_transport_failure")


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
    @staticmethod
    def runner_config(root: Path, case_path: Path, run_id: str) -> RunnerConfig:
        case_bytes = case_path.read_bytes()
        sandbox_case = load_case(case_path)
        return RunnerConfig(
            checkout_url="http://checkout:8080",
            payments_url="http://payments:8081",
            inventory_url="http://inventory:8082",
            checkpoint_db=root / "checkpoints.sqlite3",
            effect_ledger_db=root / "effects.sqlite3",
            evidence_dir=root / "evidence",
            run_id=run_id,
            source_revision=REVISION,
            case_id=sandbox_case["case_id"],
            case_digest=hashlib.sha256(case_bytes).hexdigest(),
            run_timeout_seconds=30,
            approval_fixture="APPROVED",
            case_path=case_path,
        )

    def prepare_unknown_snapshot(
        self,
        root: Path,
        run_id: str,
    ) -> tuple[
        RunnerConfig,
        GraphState,
        ReconciledAfterLostResponseGateway,
        EffectLedger,
        BoundaryEventStore,
        dict[str, dict[str, str]],
        CheckpointFingerprint,
    ]:
        case_path = Path("/app/cases/checkout-ambiguous-after-commit-001.json")
        config = self.runner_config(root, case_path, run_id)
        case = load_case(case_path)
        state = new_run_state(
            case,
            run_id=config.run_id,
            source_revision=REVISION,
            case_digest=config.case_digest,
        )
        wall_budget = DurableWallTimeBudget.acquire(
            config.checkpoint_db.with_name("wall-time-budget.sqlite3"),
            run_id=config.run_id,
            thread_id=state["thread_id"],
            source_revision=REVISION,
            case_digest=config.case_digest,
            limit_ms=state["budgets"]["wall_time_ms"]["limit"],
        )
        started_at = datetime.fromtimestamp(
            wall_budget.started_epoch_ms / 1000,
            UTC,
        ).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        gateway = ReconciledAfterLostResponseGateway()
        ledger = EffectLedger(config.effect_ledger_db)
        events = BoundaryEventStore(
            config.effect_ledger_db.with_name("events.sqlite3")
        )
        dependencies = RunnerDependencies(
            gateway=gateway,
            ledger=ledger,
            events=events,
            case=case,
        )
        graph_config = {"configurable": {"thread_id": state["thread_id"]}}
        fingerprint = CheckpointFingerprint.current(REVISION)
        ensure_run_started_events(events, state)

        with CheckpointStore(config.checkpoint_db, fingerprint) as checkpointer:
            observed_checkpointer = ObservedCheckpointSaver(checkpointer, events, state)
            graph = build_graph(dependencies, observed_checkpointer)
            self.assertIn("__interrupt__", graph.invoke(state, graph_config))
            pending = _execute_graph(graph, state, events, "APPROVED")
            self.assertTrue(pending.reconciliation_snapshot_pending)
            provisional_state = dict(pending.state)
            provisional_state.update(
                {
                    "phase": "TERMINAL",
                    "outcome": "UNKNOWN",
                    "checkout_status": "UNKNOWN",
                }
            )
            provisional_ended_at = (
                datetime.now(UTC)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z")
            )
            _export_evidence(
                config,
                state=provisional_state,
                events=events,
                ledger=ledger,
                checkpoint_lineage=_checkpoint_lineage(
                    checkpointer,
                    state["thread_id"],
                    fingerprint,
                    pending.resume_source_checkpoint_id,
                ),
                started_at=started_at,
                ended_at=provisional_ended_at,
                directory_name=f"{config.run_id}-unknown",
                event_records=[
                    *events.project(),
                    _snapshot_terminal_event(
                        events,
                        provisional_state,
                        provisional_ended_at,
                    ),
                ],
            )
        return (
            config,
            state,
            gateway,
            ledger,
            events,
            graph_config,
            fingerprint,
        )

    @staticmethod
    def emit_reconciliation_task_event(
        events: BoundaryEventStore,
        state: GraphState,
        event_type: str,
        attempt: int,
    ) -> None:
        task_id = f"{state['run_id']}:reconcile_if_ambiguous:0"
        effect_id = f"{state['run_id']}:checkout_effect:0:effect-checkout"
        if event_type == "task.started":
            data = {"status": "started"}
            failure_plane = None
            error_class = None
        elif event_type == "task.failed":
            data = {"status": "failed", "disposition": "stop"}
            failure_plane = "checkout"
            error_class = "receipt_transport_failure"
        elif event_type == "task.completed":
            data = {"status": "completed"}
            failure_plane = None
            error_class = None
        else:
            raise AssertionError(f"unexpected reconciliation task event {event_type}")
        events.emit(
            event_type,
            state,
            data,
            node_id="reconcile_if_ambiguous",
            task_id=task_id,
            attempt_id=f"{task_id}:attempt-{attempt}",
            effect_id=effect_id,
            failure_plane=failure_plane,
            error_class=error_class,
        )

    def prepare_attempt_eight_reconciled_crash(
        self,
        root: Path,
        run_id: str,
        *,
        recovery_phase: str,
    ) -> tuple[
        RunnerConfig,
        GraphState,
        ReconciledAfterLostResponseGateway,
        EffectLedger,
        BoundaryEventStore,
    ]:
        (
            config,
            state,
            gateway,
            ledger,
            events,
            _graph_config,
            _fingerprint,
        ) = self.prepare_unknown_snapshot(root, run_id)
        for attempt in range(1, state["budgets"]["attempts"]["limit"]):
            self.emit_reconciliation_task_event(events, state, "task.started", attempt)
            self.emit_reconciliation_task_event(events, state, "task.failed", attempt)
        final_attempt = state["budgets"]["attempts"]["limit"]
        self.emit_reconciliation_task_event(
            events,
            state,
            "task.started",
            final_attempt,
        )
        effect_id = f"{run_id}:checkout_effect:0:effect-checkout"
        current = ledger.current(effect_id)
        self.assertIsNotNone(current)
        self.assertIsNotNone(gateway.receipt)
        reconciled = ledger.reconcile(
            effect_id,
            gateway.receipt,
            attempt_id=current["attempt_id"],
            replay_id=current["replay_id"],
        )
        if recovery_phase in {"effect_recorded", "completion_recorded"}:
            events.emit(
                "effect.reconciled",
                state,
                {
                    "effect_class": "checkout",
                    "effect_state": "RECONCILED",
                    "authoritative_result_id": gateway.receipt[
                        "authoritative_result_id"
                    ],
                },
                node_id="reconcile_if_ambiguous",
                task_id=reconciled["task_id"],
                attempt_id=reconciled["attempt_id"],
                effect_id=effect_id,
            )
        if recovery_phase == "completion_recorded":
            self.emit_reconciliation_task_event(
                events,
                state,
                "task.completed",
                final_attempt,
            )
        return config, state, gateway, ledger, events

    @staticmethod
    def validate_unknown_bundle(config: RunnerConfig, state: GraphState) -> None:
        validate_unknown_snapshot(
            config.evidence_dir / f"{config.run_id}-unknown",
            run_id=config.run_id,
            case_id=config.case_id,
            case_digest=config.case_digest,
            source_revision=config.source_revision,
            thread_id=state["thread_id"],
            trusted_checkout=state["checkout"],
        )

    def test_checkout_unknown_snapshot_resumes_to_reconciled_without_redispatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            case = copy.deepcopy(load_case(Path("/app/cases/mission-healthy-001.json")))
            case["service_fixtures"]["checkout"]["effect"] = "ambiguous_after_commit"
            state = new_run_state(
                case,
                run_id="checkout-reconciliation-001",
                source_revision=REVISION,
                case_digest=CASE_DIGEST,
            )
            gateway = ReconciledAfterLostResponseGateway()
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
                pending = _execute_graph(graph, state, events, "APPROVED")
                self.assertTrue(pending.reconciliation_snapshot_pending)
                self.assertIsNotNone(pending.resume_source_checkpoint_id)
                snapshot = graph.get_state(config)
                self.assertEqual(snapshot.next, ("reconcile_after_snapshot",))
                effect_id = "checkout-reconciliation-001:checkout_effect:0:effect-checkout"
                self.assertEqual(ledger.current(effect_id)["effect_state"], "UNKNOWN")
                self.assertEqual(gateway.checkout_calls, 1)
                self.assertNotIn(
                    "effect.reconciled",
                    [event["event_type"] for event in events.project()],
                )

                recreated = _execute_graph(graph, state, events, "APPROVED")
                self.assertTrue(recreated.reconciliation_snapshot_pending)
                self.assertEqual(gateway.receipt_lookups, 0)
                self.assertEqual(
                    _latest_completed_resume_source(events),
                    pending.resume_source_checkpoint_id,
                )
                completed = _execute_graph(
                    graph,
                    state,
                    events,
                    "APPROVED",
                    advance_reconciliation_snapshot=True,
                ).state

            emit_terminal_event(events, completed)
            self.assertEqual(completed["outcome"], "SUCCEEDED")
            self.assertEqual(ledger.current(effect_id)["effect_state"], "RECONCILED")
            self.assertEqual(gateway.checkout_calls, 1)
            self.assertEqual(gateway.receipt_lookups, 1)
            effect_states = [
                record["effect_state"] for record in ledger.project()
            ]
            self.assertEqual(
                effect_states,
                ["PREPARED", "DISPATCHED", "UNKNOWN", "RECONCILED"],
            )

    def test_existing_unknown_snapshot_rejects_rechecksummed_semantic_drift(
        self,
    ) -> None:
        drift_cases = (
            ("events", "event identity|false terminal"),
            ("effects", "effect ledger"),
            ("payload", "final state identity"),
            ("lineage", "checkpoint lineage"),
            ("resume_same", "checkpoint resume"),
            ("resume_ancestor", "checkpoint resume"),
            ("runtime", "runtime contract"),
            ("receipts", "receipt evidence"),
        )
        for artifact, diagnostic in drift_cases:
            with self.subTest(artifact=artifact), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                config, state, *_ = self.prepare_unknown_snapshot(
                    root,
                    f"semantic-{artifact}-drift-001",
                )
                self.validate_unknown_bundle(config, state)
                unknown_dir = config.evidence_dir / f"{config.run_id}-unknown"
                exporter = EvidenceExporter(
                    config.evidence_dir,
                    config.run_id,
                    directory_name=f"{config.run_id}-unknown",
                )
                if artifact == "events":
                    events = [
                        json.loads(line)
                        for line in (unknown_dir / "events.jsonl")
                        .read_text(encoding="utf-8")
                        .splitlines()
                    ]
                    events[-1]["data"] = {
                        "result": "terminal",
                        "outcome": "SUCCEEDED",
                    }
                    exporter.write_jsonl("events.jsonl", events)
                elif artifact == "effects":
                    effects = [
                        json.loads(line)
                        for line in (unknown_dir / "effects.jsonl")
                        .read_text(encoding="utf-8")
                        .splitlines()
                    ]
                    effects[-1]["effect_state"] = "RECONCILED"
                    exporter.write_jsonl("effects.jsonl", effects)
                elif artifact == "payload":
                    final_state_path = unknown_dir / "final-state.json"
                    final_state = json.loads(
                        final_state_path.read_text(encoding="utf-8")
                    )
                    final_state["checkout"]["amount_cents"] += 1
                    exporter.write_json("final-state.json", final_state)
                    payload = {
                        "order_id": final_state["checkout"]["order_id"],
                        "amount_cents": final_state["checkout"]["amount_cents"],
                        "items": final_state["checkout"]["items"],
                    }
                    payload_hash = hashlib.sha256(
                        json.dumps(
                            payload,
                            ensure_ascii=True,
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode("ascii")
                    ).hexdigest()
                    effects = [
                        json.loads(line)
                        for line in (unknown_dir / "effects.jsonl")
                        .read_text(encoding="utf-8")
                        .splitlines()
                    ]
                    for effect in effects:
                        effect["payload_hash"] = payload_hash
                    exporter.write_jsonl("effects.jsonl", effects)
                elif artifact == "lineage":
                    lineage_path = unknown_dir / "checkpoint-lineage.json"
                    lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
                    lineage["resume_source_checkpoint_id"] = "missing-checkpoint"
                    exporter.write_json("checkpoint-lineage.json", lineage)
                elif artifact in {"resume_same", "resume_ancestor"}:
                    lineage = json.loads(
                        (unknown_dir / "checkpoint-lineage.json").read_text(
                            encoding="utf-8"
                        )
                    )
                    events = [
                        json.loads(line)
                        for line in (unknown_dir / "events.jsonl")
                        .read_text(encoding="utf-8")
                        .splitlines()
                    ]
                    resume_started = next(
                        event
                        for event in events
                        if event["event_type"] == "checkpoint.resume_started"
                    )
                    resume_completed = next(
                        event
                        for event in events
                        if event["event_type"] == "checkpoint.resume_completed"
                    )
                    if artifact == "resume_same":
                        resume_completed["checkpoint_id"] = resume_started[
                            "checkpoint_id"
                        ]
                    else:
                        source_position = lineage["saver_checkpoint_ids"].index(
                            resume_started["checkpoint_id"]
                        )
                        self.assertGreater(source_position, 0)
                        resume_completed["checkpoint_id"] = lineage[
                            "saver_checkpoint_ids"
                        ][source_position - 1]
                    exporter.write_jsonl("events.jsonl", events)
                elif artifact == "runtime":
                    runtime_path = unknown_dir / "runtime.json"
                    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
                    runtime["packages"]["langgraph"] = "0.0.0"
                    exporter.write_json("runtime.json", runtime)
                else:
                    exporter.write_json(
                        "receipts/payment.json",
                        {"receipt_id": "false-success-receipt"},
                    )
                    manifest_path = unknown_dir / "manifest.json"
                    manifest = json.loads(
                        manifest_path.read_text(encoding="utf-8")
                    )
                    manifest["artifacts"] = sorted(
                        [*manifest["artifacts"], "receipts/payment.json"]
                    )
                    exporter.write_json("manifest.json", manifest)
                exporter.write_checksums()

                with self.assertRaisesRegex(
                    ExistingSnapshotInvalid,
                    diagnostic,
                ):
                    self.validate_unknown_bundle(config, state)

    def test_temporary_reconciliation_failure_remains_resumable_without_redispatch(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            case = load_case(Path("/app/cases/checkout-ambiguous-after-commit-001.json"))
            state = new_run_state(
                case,
                run_id="checkout-reconciliation-retry-001",
                source_revision=REVISION,
                case_digest=CASE_DIGEST,
            )
            gateway = TransientReconciliationFailureGateway()
            ledger = EffectLedger(root / "effects.sqlite3")
            events = BoundaryEventStore(root / "events.sqlite3")
            dependencies = RunnerDependencies(
                gateway=gateway,
                ledger=ledger,
                events=events,
                case=case,
            )
            checkpoint_path = root / "checkpoints.sqlite3"
            config = {"configurable": {"thread_id": state["thread_id"]}}

            with CheckpointStore(
                checkpoint_path,
                CheckpointFingerprint.current(REVISION),
            ) as checkpointer:
                graph = build_graph(dependencies, checkpointer)
                self.assertIn("__interrupt__", graph.invoke(state, config))
                pending = _execute_graph(graph, state, events, "APPROVED")
                self.assertTrue(pending.reconciliation_snapshot_pending)
                failed_lookup = _execute_graph(
                    graph,
                    state,
                    events,
                    "APPROVED",
                    advance_reconciliation_snapshot=True,
                )
                self.assertTrue(failed_lookup.reconciliation_snapshot_pending)
                self.assertEqual(
                    graph.get_state(config).next,
                    ("reconcile_after_snapshot",),
                )

            with CheckpointStore(
                checkpoint_path,
                CheckpointFingerprint.current(REVISION),
            ) as checkpointer:
                resumed_graph = build_graph(dependencies, checkpointer)
                recreated = _execute_graph(
                    resumed_graph,
                    state,
                    events,
                    "APPROVED",
                )
                self.assertTrue(recreated.reconciliation_snapshot_pending)
                completed = _execute_graph(
                    resumed_graph,
                    state,
                    events,
                    "APPROVED",
                    advance_reconciliation_snapshot=True,
                ).state

            effect_id = (
                "checkout-reconciliation-retry-001:checkout_effect:0:effect-checkout"
            )
            self.assertEqual(completed["outcome"], "SUCCEEDED")
            self.assertEqual(ledger.current(effect_id)["effect_state"], "RECONCILED")
            self.assertEqual(gateway.checkout_calls, 1)
            self.assertEqual(gateway.receipt_lookups, 2)

    def test_non_timeline_reconciliation_failure_remains_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self.runner_config(
                root,
                Path("/app/cases/mission-healthy-001.json"),
                "ordinary-reconciliation-unavailable-001",
            )
            gateway = UnavailableReconciliationGateway()
            with (
                mock.patch(
                    "runner.main.RunnerConfig.from_environment",
                    return_value=config,
                ),
                mock.patch("runner.main.HttpGateway", return_value=gateway),
                mock.patch(
                    "runner.main._run_deadline",
                    side_effect=lambda _seconds: nullcontext(),
                ),
            ):
                self.assertEqual(run({}), 2)

            evidence_dirs = sorted(
                path.name for path in config.evidence_dir.iterdir() if path.is_dir()
            )
            self.assertEqual(evidence_dirs, [config.run_id])
            final_state = json.loads(
                (config.evidence_dir / config.run_id / "final-state.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(final_state["outcome"], "UNKNOWN")
            self.assertEqual(gateway.checkout_calls, 1)
            task_id = f"{config.run_id}:reconcile_if_ambiguous:0"
            self.assertEqual(
                final_state["tasks"][task_id],
                {"status": "failed", "attempt": 1},
            )
            events = BoundaryEventStore(
                config.effect_ledger_db.with_name("events.sqlite3")
            )
            task_events = [
                event
                for event in events.project()
                if event["task_id"] == task_id
            ]
            self.assertEqual(
                [event["event_type"] for event in task_events],
                ["task.started", "task.failed"],
            )
            self.assertEqual(
                task_events[-1]["data"],
                {"status": "failed", "disposition": "stop"},
            )

    def test_reconciliation_lookup_attempts_stop_at_declared_attempt_ceiling(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            case = load_case(Path("/app/cases/checkout-ambiguous-after-commit-001.json"))
            state = new_run_state(
                case,
                run_id="reconciliation-attempt-ceiling-001",
                source_revision=REVISION,
                case_digest=CASE_DIGEST,
            )
            gateway = UnavailableAfterLostResponseGateway()
            events = BoundaryEventStore(root / "events.sqlite3")
            dependencies = RunnerDependencies(
                gateway=gateway,
                ledger=EffectLedger(root / "effects.sqlite3"),
                events=events,
                case=case,
            )
            graph_config = {"configurable": {"thread_id": state["thread_id"]}}

            with CheckpointStore(
                root / "checkpoints.sqlite3",
                CheckpointFingerprint.current(REVISION),
            ) as checkpointer:
                graph = build_graph(dependencies, checkpointer)
                self.assertIn("__interrupt__", graph.invoke(state, graph_config))
                pending = _execute_graph(graph, state, events, "APPROVED")
                self.assertTrue(pending.reconciliation_snapshot_pending)
                attempt_limit = state["budgets"]["attempts"]["limit"]
                for _attempt in range(attempt_limit):
                    pending = _execute_graph(
                        graph,
                        state,
                        events,
                        "APPROVED",
                        advance_reconciliation_snapshot=True,
                    )
                    self.assertTrue(pending.reconciliation_snapshot_pending)
                exhausted = _execute_graph(
                    graph,
                    state,
                    events,
                    "APPROVED",
                    advance_reconciliation_snapshot=True,
                )

            self.assertFalse(exhausted.reconciliation_snapshot_pending)
            self.assertEqual(exhausted.state["outcome"], "UNKNOWN")
            self.assertEqual(
                exhausted.state["budgets"]["attempts"],
                {"limit": attempt_limit, "consumed": 1},
            )
            self.assertEqual(gateway.checkout_calls, 1)
            self.assertEqual(gateway.receipt_lookups, attempt_limit)
            retry_exhausted = [
                event
                for event in events.project()
                if event["event_type"] == "task.retry_exhausted"
            ]
            self.assertEqual(len(retry_exhausted), 1)
            self.assertEqual(
                retry_exhausted[0]["data"],
                {"status": "exhausted", "attempts": attempt_limit},
            )

    def test_partial_existing_unknown_snapshot_blocks_checkpoint_advancement(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (
                config,
                state,
                gateway,
                ledger,
                events,
                graph_config,
                fingerprint,
            ) = self.prepare_unknown_snapshot(
                root,
                "partial-unknown-snapshot-001",
            )
            unknown_dir = config.evidence_dir / f"{config.run_id}-unknown"
            (unknown_dir / "manifest.json").unlink()

            with (
                mock.patch(
                    "runner.main.RunnerConfig.from_environment",
                    return_value=config,
                ),
                mock.patch("runner.main.HttpGateway", return_value=gateway),
                mock.patch(
                    "runner.main._run_deadline",
                    side_effect=lambda _seconds: nullcontext(),
                ),
                self.assertRaisesRegex(RuntimeError, "existing UNKNOWN snapshot"),
            ):
                run({})

            case = load_case(config.case_path)
            with CheckpointStore(config.checkpoint_db, fingerprint) as checkpointer:
                graph = build_graph(
                    RunnerDependencies(
                        gateway=gateway,
                        ledger=ledger,
                        events=events,
                        case=case,
                    ),
                    checkpointer,
                )
                self.assertEqual(
                    graph.get_state(graph_config).next,
                    ("reconcile_after_snapshot",),
                )
            self.assertEqual(gateway.receipt_lookups, 0)

    def test_terminal_restart_validates_unknown_before_final_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (
                config,
                state,
                gateway,
                ledger,
                events,
                graph_config,
                fingerprint,
            ) = self.prepare_unknown_snapshot(
                root,
                "terminal-restart-corrupt-unknown-001",
            )
            case = load_case(config.case_path)
            with CheckpointStore(config.checkpoint_db, fingerprint) as checkpointer:
                graph = build_graph(
                    RunnerDependencies(
                        gateway=gateway,
                        ledger=ledger,
                        events=events,
                        case=case,
                    ),
                    checkpointer,
                )
                completed = _execute_graph(
                    graph,
                    state,
                    events,
                    "APPROVED",
                    advance_reconciliation_snapshot=True,
                )
                self.assertFalse(completed.reconciliation_snapshot_pending)
                self.assertEqual(completed.state["outcome"], "SUCCEEDED")
                self.assertEqual(graph.get_state(graph_config).next, ())

            unknown_dir = config.evidence_dir / f"{config.run_id}-unknown"
            (unknown_dir / "manifest.json").unlink()

            def evidence_bytes() -> dict[str, bytes]:
                return {
                    path.relative_to(config.evidence_dir).as_posix(): path.read_bytes()
                    for path in config.evidence_dir.rglob("*")
                    if path.is_file()
                }

            before_restart = evidence_bytes()
            with (
                mock.patch(
                    "runner.main.RunnerConfig.from_environment",
                    return_value=config,
                ),
                mock.patch("runner.main.HttpGateway", return_value=gateway),
                mock.patch(
                    "runner.main._run_deadline",
                    side_effect=lambda _seconds: nullcontext(),
                ),
                self.assertRaisesRegex(RuntimeError, "existing UNKNOWN snapshot"),
            ):
                run({})

            self.assertEqual(evidence_bytes(), before_restart)
            self.assertFalse(
                (config.evidence_dir / f"{config.run_id}-reconciled").exists()
            )

    def test_attempt_eight_reconciled_crash_reuses_durable_task_attempt(self) -> None:
        for recovery_phase in (
            "ledger_recorded",
            "effect_recorded",
            "completion_recorded",
        ):
            with self.subTest(recovery_phase=recovery_phase), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                config, state, gateway, _ledger, events = (
                    self.prepare_attempt_eight_reconciled_crash(
                        root,
                        f"attempt-eight-crash-{recovery_phase.replace('_', '-')}-001",
                        recovery_phase=recovery_phase,
                    )
                )
                with (
                    mock.patch(
                        "runner.main.RunnerConfig.from_environment",
                        return_value=config,
                    ),
                    mock.patch("runner.main.HttpGateway", return_value=gateway),
                    mock.patch(
                        "runner.main._run_deadline",
                        side_effect=lambda _seconds: nullcontext(),
                    ),
                ):
                    self.assertEqual(run({}), 0)

                task_id = f"{state['run_id']}:reconcile_if_ambiguous:0"
                task_events = [
                    event
                    for event in events.project()
                    if event["task_id"] == task_id
                ]
                self.assertEqual(
                    [event["event_type"] for event in task_events].count(
                        "task.started"
                    ),
                    8,
                )
                self.assertEqual(
                    [event["event_type"] for event in task_events].count(
                        "task.completed"
                    ),
                    1,
                )
                reconciled_events = [
                    event
                    for event in events.project()
                    if event["event_type"] == "effect.reconciled"
                ]
                self.assertEqual(len(reconciled_events), 1)
                final_started = next(
                    event
                    for event in task_events
                    if event["event_type"] == "task.started"
                    and event["attempt_id"] == f"{task_id}:attempt-8"
                )
                final_completed = next(
                    event
                    for event in task_events
                    if event["event_type"] == "task.completed"
                )
                self.assertLess(
                    final_started["sequence"],
                    reconciled_events[0]["sequence"],
                )
                self.assertLess(
                    reconciled_events[0]["sequence"],
                    final_completed["sequence"],
                )
                self.assertEqual(
                    reconciled_events[0]["task_id"],
                    f"{state['run_id']}:checkout_effect:0",
                )
                self.assertEqual(
                    reconciled_events[0]["attempt_id"],
                    f"{state['run_id']}:checkout_effect:0:attempt-1",
                )
                self.assertFalse(
                    any(
                        event["attempt_id"] == f"{task_id}:attempt-9"
                        for event in task_events
                    )
                )
                self.assertNotIn(
                    "task.retry_exhausted",
                    [event["event_type"] for event in task_events],
                )
                final_state = json.loads(
                    (
                        config.evidence_dir
                        / f"{config.run_id}-reconciled"
                        / "final-state.json"
                    ).read_text(encoding="utf-8")
                )
                self.assertEqual(
                    final_state["tasks"][task_id],
                    {"status": "completed", "attempt": 8},
                )
                self.assertEqual(gateway.receipt_lookups, 0)

    def test_reconciliation_rejects_duplicate_completed_task_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (
                _config,
                state,
                gateway,
                ledger,
                events,
                graph_config,
                fingerprint,
            ) = self.prepare_unknown_snapshot(
                root,
                "duplicate-reconciliation-completion-001",
            )
            self.emit_reconciliation_task_event(events, state, "task.started", 1)
            self.emit_reconciliation_task_event(events, state, "task.completed", 1)
            self.emit_reconciliation_task_event(events, state, "task.completed", 1)
            case = load_case(Path("/app/cases/checkout-ambiguous-after-commit-001.json"))
            with CheckpointStore(
                root / "checkpoints.sqlite3",
                fingerprint,
            ) as checkpointer:
                graph = build_graph(
                    RunnerDependencies(
                        gateway=gateway,
                        ledger=ledger,
                        events=events,
                        case=case,
                    ),
                    checkpointer,
                )
                with self.assertRaisesRegex(RuntimeError, "reconciliation task history"):
                    _execute_graph(
                        graph,
                        state,
                        events,
                        "APPROVED",
                        advance_reconciliation_snapshot=True,
                    )
                self.assertEqual(
                    graph.get_state(graph_config).next,
                    ("reconcile_after_snapshot",),
                )
            self.assertEqual(gateway.receipt_lookups, 0)

    def test_durable_unknown_checkout_crash_hydrates_original_attempt_and_publishes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self.runner_config(
                root,
                Path("/app/cases/checkout-ambiguous-after-commit-001.json"),
                "durable-unknown-checkout-crash-001",
            )
            case = load_case(config.case_path)
            state = new_run_state(
                case,
                run_id=config.run_id,
                source_revision=config.source_revision,
                case_digest=config.case_digest,
            )
            ledger = EffectLedger(config.effect_ledger_db)
            events = BoundaryEventStore(
                config.effect_ledger_db.with_name("events.sqlite3")
            )
            gateway = CrashAfterDurableUnknownGateway(ledger)
            dependencies = RunnerDependencies(
                gateway=gateway,
                ledger=ledger,
                events=events,
                case=case,
            )
            fingerprint = CheckpointFingerprint.current(REVISION)
            graph_config = {"configurable": {"thread_id": state["thread_id"]}}
            ensure_run_started_events(events, state)
            with CheckpointStore(config.checkpoint_db, fingerprint) as checkpointer:
                graph = build_graph(
                    dependencies,
                    ObservedCheckpointSaver(checkpointer, events, state),
                )
                self.assertIn("__interrupt__", graph.invoke(state, graph_config))
                with self.assertRaisesRegex(
                    SimulatedProcessCrash,
                    "after durable UNKNOWN",
                ):
                    _execute_graph(graph, state, events, "APPROVED")

            effect_id = f"{config.run_id}:checkout_effect:0:effect-checkout"
            self.assertEqual(ledger.current(effect_id)["effect_state"], "UNKNOWN")
            checkout_task_id = f"{config.run_id}:checkout_effect:0"
            self.assertEqual(
                len(
                    [
                        event
                        for event in events.project()
                        if event["event_type"] == "task.started"
                        and event["task_id"] == checkout_task_id
                    ]
                ),
                1,
            )

            patches = (
                mock.patch(
                    "runner.main.RunnerConfig.from_environment",
                    return_value=config,
                ),
                mock.patch("runner.main.HttpGateway", return_value=gateway),
                mock.patch(
                    "runner.main._run_deadline",
                    side_effect=lambda _seconds: nullcontext(),
                ),
            )
            with patches[0], patches[1], patches[2], self.assertRaisesRegex(
                SimulatedProcessCrash,
                "after UNKNOWN snapshot export",
            ):
                run({})

            unknown_dir = config.evidence_dir / f"{config.run_id}-unknown"
            self.assertTrue(unknown_dir.is_dir())
            self.validate_unknown_bundle(config, state)
            unknown_bytes = {
                path.relative_to(unknown_dir).as_posix(): path.read_bytes()
                for path in unknown_dir.rglob("*")
                if path.is_file()
            }

            with (
                mock.patch(
                    "runner.main.RunnerConfig.from_environment",
                    return_value=config,
                ),
                mock.patch("runner.main.HttpGateway", return_value=gateway),
                mock.patch(
                    "runner.main._run_deadline",
                    side_effect=lambda _seconds: nullcontext(),
                ),
            ):
                self.assertEqual(run({}), 0)

            self.assertEqual(
                {
                    path.relative_to(unknown_dir).as_posix(): path.read_bytes()
                    for path in unknown_dir.rglob("*")
                    if path.is_file()
                },
                unknown_bytes,
            )
            self.assertEqual(gateway.checkout_calls, 1)
            self.assertEqual(gateway.receipt_lookups, 2)
            checkout_events = [
                event
                for event in events.project()
                if event["task_id"] == checkout_task_id
                and str(event["event_type"]).startswith("task.")
            ]
            self.assertEqual(
                [event["event_type"] for event in checkout_events],
                ["task.started", "task.failed"],
            )
            final_state = json.loads(
                (
                    config.evidence_dir
                    / f"{config.run_id}-reconciled"
                    / "final-state.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(
                final_state["tasks"][checkout_task_id],
                {"status": "failed", "attempt": 1},
            )
            self.assertEqual(
                final_state["budgets"]["attempts"],
                {"limit": 8, "consumed": 1},
            )

    def test_reconciled_ledger_crash_window_preserves_unknown_snapshot_bytes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (
                config,
                _state,
                gateway,
                ledger,
                _events,
                _graph_config,
                _fingerprint,
            ) = self.prepare_unknown_snapshot(
                root,
                "checkout-reconciled-crash-window-001",
            )
            effect_id = f"{config.run_id}:checkout_effect:0:effect-checkout"
            current = ledger.current(effect_id)
            self.assertIsNotNone(current)
            self.assertIsNotNone(gateway.receipt)
            self.emit_reconciliation_task_event(
                _events,
                _state,
                "task.started",
                1,
            )
            ledger.reconcile(
                effect_id,
                gateway.receipt,
                attempt_id=current["attempt_id"],
                replay_id=current["replay_id"],
            )

            unknown_dir = config.evidence_dir / f"{config.run_id}-unknown"

            def snapshot_bytes() -> dict[str, bytes]:
                return {
                    path.relative_to(unknown_dir).as_posix(): path.read_bytes()
                    for path in unknown_dir.rglob("*")
                    if path.is_file()
                }

            before_resume = snapshot_bytes()
            resume_gateway = FakeGateway()
            result: int | None = None
            try:
                with (
                    mock.patch(
                        "runner.main.RunnerConfig.from_environment",
                        return_value=config,
                    ),
                    mock.patch("runner.main.HttpGateway", return_value=resume_gateway),
                    mock.patch(
                        "runner.main._run_deadline",
                        side_effect=lambda _seconds: nullcontext(),
                    ),
                ):
                    result = run({})
            finally:
                self.assertEqual(snapshot_bytes(), before_resume)

            self.assertEqual(result, 0)
            self.assertTrue(
                (config.evidence_dir / f"{config.run_id}-reconciled").is_dir()
            )
            self.assertEqual(ledger.current(effect_id)["effect_state"], "RECONCILED")
            self.assertEqual(gateway.checkout_calls, 1)
            self.assertEqual(resume_gateway.checkout_calls, 0)

    def test_restart_after_resume_completed_preserves_final_lineage_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            case_path = Path("/app/cases/mission-healthy-001.json")
            config = self.runner_config(
                root,
                case_path,
                "resume-completed-export-crash-001",
            )
            case = load_case(case_path)
            state = new_run_state(
                case,
                run_id=config.run_id,
                source_revision=REVISION,
                case_digest=config.case_digest,
            )
            events = BoundaryEventStore(
                config.effect_ledger_db.with_name("events.sqlite3")
            )
            ledger = EffectLedger(config.effect_ledger_db)
            dependencies = RunnerDependencies(
                gateway=FakeGateway(),
                ledger=ledger,
                events=events,
                case=case,
            )
            graph_config = {"configurable": {"thread_id": state["thread_id"]}}
            ensure_run_started_events(events, state)

            with CheckpointStore(
                config.checkpoint_db,
                CheckpointFingerprint.current(REVISION),
            ) as checkpointer:
                graph = build_graph(dependencies, checkpointer)
                self.assertIn("__interrupt__", graph.invoke(state, graph_config))
                execution = _execute_graph(graph, state, events, "APPROVED")
                self.assertEqual(execution.state["outcome"], "SUCCEEDED")
                resume_source = execution.resume_source_checkpoint_id
                self.assertIsNotNone(resume_source)

            restart_gateway = FakeGateway()
            with (
                mock.patch(
                    "runner.main.RunnerConfig.from_environment",
                    return_value=config,
                ),
                mock.patch("runner.main.HttpGateway", return_value=restart_gateway),
                mock.patch(
                    "runner.main.reconcile_interrupted_checkpoint_events",
                    return_value=None,
                ),
                mock.patch(
                    "runner.main._run_deadline",
                    side_effect=lambda _seconds: nullcontext(),
                ),
            ):
                self.assertEqual(run({}), 0)

            lineage = json.loads(
                (
                    config.evidence_dir
                    / config.run_id
                    / "checkpoint-lineage.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(lineage["resume_source_checkpoint_id"], resume_source)
            self.assertEqual(restart_gateway.checkout_calls, 0)

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
            observed_times = iter((1.0, 1.0, 121.0))
            dependencies = RunnerDependencies(
                gateway=gateway,
                ledger=EffectLedger(root / "effects.sqlite3"),
                events=events,
                case=case,
                monotonic_clock=lambda: next(observed_times),
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
