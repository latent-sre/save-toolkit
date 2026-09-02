#!/usr/bin/env python3
"""Focused tests for the GRAPH-003 sandbox indicator and alert evaluator."""

from __future__ import annotations

import importlib.util
import hashlib
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/graph_sandbox_alerts.py"
AUTHORITATIVE_RESULT_ID = "result-001"


def _load_module():
    spec = importlib.util.spec_from_file_location("graph_sandbox_alerts", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, values: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(value, sort_keys=True) + "\n" for value in values),
        encoding="utf-8",
    )


def _write_checksums(directory: Path, names: list[str]) -> None:
    lines = []
    for name in sorted(names):
        digest = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}\n")
    (directory / "checksums.sha256").write_text("".join(lines), encoding="utf-8")


def _event(
    run_id: str,
    sequence: int,
    event_type: str,
    time_utc: str,
    *,
    failure_plane: str | None = None,
    error_class: str | None = None,
    effect_id: str | None = None,
    data: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "attempt_id": None,
        "case_id": "synthetic-case-001",
        "checkpoint_id": None,
        "contract_version": "checkout-payments-timeout-drill/v1",
        "data": data or {},
        "effect_id": effect_id,
        "error_class": error_class,
        "event_type": event_type,
        "event_version": "graph-boundary-event/v2",
        "failure_plane": failure_plane,
        "node_id": "test-node",
        "replay_id": f"{run_id}:replay-0",
        "run_id": run_id,
        "sandbox_version": "graph-sandbox/v1",
        "sequence": sequence,
        "source_revision": "a" * 40,
        "task_id": None,
        "time_utc": time_utc,
    }


def _effect_fixture(
    run_id: str,
    *,
    started_at: str,
    ended_at: str,
    final_state: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    effect_id = f"{run_id}:checkout_effect:0:effect-checkout"
    states = ["PREPARED", "DISPATCHED"]
    if final_state in {"UNKNOWN", "RECONCILED"}:
        states.append("UNKNOWN")
    if final_state == "RECONCILED":
        states.append("RECONCILED")
    elif final_state == "RECEIPT_RECORDED":
        states.append("RECEIPT_RECORDED")

    event_type_by_state = {
        "PREPARED": "effect.prepared",
        "DISPATCHED": "effect.dispatched",
        "UNKNOWN": "effect.unknown",
        "RECEIPT_RECORDED": "effect.receipt_recorded",
        "RECONCILED": "effect.reconciled",
    }
    events = [
        _event(run_id, 1, "run.accepted", started_at),
        _event(run_id, 2, "run.started", started_at),
    ]
    effects: list[dict[str, object]] = []
    for sequence, state in enumerate(states, start=1):
        data: dict[str, object] = {
            "effect_class": "checkout",
            "effect_state": state,
        }
        receipt = None
        if state == "UNKNOWN":
            data["reason_class"] = "checkout_target_reported_unknown"
        if state in {"RECEIPT_RECORDED", "RECONCILED"}:
            data["authoritative_result_id"] = AUTHORITATIVE_RESULT_ID
            receipt = {
                "authoritative_result_id": AUTHORITATIVE_RESULT_ID,
                "completion_class": "COMPLETE",
            }
        events.append(
            _event(
                run_id,
                sequence + 2,
                event_type_by_state[state],
                started_at,
                effect_id=effect_id,
                data=data,
            )
        )
        effects.append(
            {
                "effect_id": effect_id,
                "effect_state": state,
                "receipt": receipt,
                "sequence": sequence,
                "target": "checkout",
                "time_utc": started_at,
            }
        )

    outcome = "SUCCEEDED" if final_state in {"RECEIPT_RECORDED", "RECONCILED"} else "UNKNOWN"
    terminal_data: dict[str, object] = {"outcome": outcome, "result": "terminal"}
    if outcome == "SUCCEEDED":
        terminal_data["authoritative_result_id"] = AUTHORITATIVE_RESULT_ID
    events.append(
        _event(
            run_id,
            len(events) + 1,
            "run.terminal",
            ended_at,
            data=terminal_data,
        )
    )
    return events, effects


def _bundle(
    root: Path,
    run_id: str,
    *,
    started_at: str,
    ended_at: str,
    outcome: str,
    events: list[dict[str, object]],
    effects: list[dict[str, object]] | None = None,
    bundle_name: str | None = None,
    snapshot_role: str | None = None,
) -> Path:
    bundle = root / (bundle_name or run_id)
    bundle.mkdir()
    _write_json(
        bundle / "manifest.json",
        {
            "artifacts": ["effects.jsonl", "events.jsonl", "verification.json"],
            "authoritative_result_id": AUTHORITATIVE_RESULT_ID if outcome == "SUCCEEDED" else None,
            "case_id": "synthetic-case-001",
            "contract_version": "checkout-payments-timeout-drill/v1",
            "ended_at": ended_at,
            "evidence_version": "graph-evidence/v2",
            "outcome": outcome,
            "run_id": run_id,
            "sandbox_version": "graph-sandbox/v1",
            "source_revision": "a" * 40,
            "started_at": started_at,
        },
    )
    verification = {
        "exit_code": 0 if outcome == "SUCCEEDED" else 2,
        "run_id": run_id,
        "source_revision": "a" * 40,
        "verification_version": (
            "graph-sandbox-host-verification/v2"
            if snapshot_role is not None
            else "graph-sandbox-host-verification/v1"
        ),
    }
    if snapshot_role is not None:
        verification["snapshot_role"] = snapshot_role
        verification["runner_container_exit"] = {
            "Status": "exited",
            "ExitCode": 0,
            "OOMKilled": False,
        }
    _write_json(
        bundle / "verification.json",
        verification,
    )
    _write_jsonl(bundle / "events.jsonl", events)
    _write_jsonl(bundle / "effects.jsonl", effects or [])
    _write_checksums(
        bundle,
        ["effects.jsonl", "events.jsonl", "manifest.json", "verification.json"],
    )
    return bundle


class GraphSandboxAlertsTest(unittest.TestCase):
    def test_v2_snapshot_rejects_a_semantic_exit_as_the_runner_exit(self) -> None:
        module = _load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            events, effects = _effect_fixture(
                "reconcile-exit-001",
                started_at="2026-08-30T11:00:00.000Z",
                ended_at="2026-08-30T11:00:01.000Z",
                final_state="UNKNOWN",
            )
            bundle = _bundle(
                root,
                "reconcile-exit-001",
                started_at="2026-08-30T11:00:00.000Z",
                ended_at="2026-08-30T11:00:01.000Z",
                outcome="UNKNOWN",
                events=events,
                effects=effects,
                snapshot_role="UNKNOWN",
            )
            verification_path = bundle / "verification.json"
            verification = json.loads(verification_path.read_text(encoding="utf-8"))
            verification["runner_container_exit"]["ExitCode"] = 2
            _write_json(verification_path, verification)
            _write_checksums(
                bundle,
                ["effects.jsonl", "events.jsonl", "manifest.json", "verification.json"],
            )

            with self.assertRaisesRegex(module.EvidenceError, "snapshot role"):
                module.evaluate_timeline([bundle])

    def test_failed_run_then_clean_recovery_fires_and_resolves(self) -> None:
        module = _load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            failed = _bundle(
                root,
                "failed-001",
                started_at="2026-08-30T10:00:00.000Z",
                ended_at="2026-08-30T10:00:01.000Z",
                outcome="FAILED",
                events=[
                    _event("failed-001", 1, "run.accepted", "2026-08-30T10:00:00.000Z"),
                    _event("failed-001", 2, "run.started", "2026-08-30T10:00:00.000Z"),
                    _event(
                        "failed-001",
                        3,
                        "edge.join_starved",
                        "2026-08-30T10:00:00.500Z",
                        failure_plane="checkout",
                        error_class="readiness_join_incomplete",
                    ),
                    _event(
                        "failed-001",
                        4,
                        "run.terminal",
                        "2026-08-30T10:00:01.000Z",
                        data={"outcome": "FAILED", "result": "terminal"},
                    ),
                ],
            )
            recovered_events, recovered_effects = _effect_fixture(
                "healthy-002",
                started_at="2026-08-30T10:05:00.000Z",
                ended_at="2026-08-30T10:05:01.000Z",
                final_state="RECEIPT_RECORDED",
            )
            recovered = _bundle(
                root,
                "healthy-002",
                started_at="2026-08-30T10:05:00.000Z",
                ended_at="2026-08-30T10:05:01.000Z",
                outcome="SUCCEEDED",
                events=recovered_events,
                effects=recovered_effects,
            )

            result = module.evaluate_timeline([recovered, failed])

        self.assertEqual(
            [observation["alert_state"] for observation in result["observations"]],
            ["FIRING", "RESOLVED"],
        )
        self.assertEqual(result["transitions"][-1]["transition"], "FIRING->RESOLVED")
        self.assertEqual(result["final_alert"]["state"], "RESOLVED")

    def test_unknown_effect_is_sticky_across_an_unrelated_success(self) -> None:
        module = _load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            effect_id = "unknown-001:checkout_effect:0:effect-checkout"
            unknown_events, unknown_effects = _effect_fixture(
                "unknown-001",
                started_at="2026-08-30T11:00:00.000Z",
                ended_at="2026-08-30T11:00:01.000Z",
                final_state="UNKNOWN",
            )
            unknown = _bundle(
                root,
                "unknown-001",
                started_at="2026-08-30T11:00:00.000Z",
                ended_at="2026-08-30T11:00:01.000Z",
                outcome="UNKNOWN",
                events=unknown_events,
                effects=unknown_effects,
            )
            healthy_events, healthy_effects = _effect_fixture(
                "healthy-003",
                started_at="2026-08-30T11:05:00.000Z",
                ended_at="2026-08-30T11:05:01.000Z",
                final_state="RECEIPT_RECORDED",
            )
            healthy = _bundle(
                root,
                "healthy-003",
                started_at="2026-08-30T11:05:00.000Z",
                ended_at="2026-08-30T11:05:01.000Z",
                outcome="SUCCEEDED",
                events=healthy_events,
                effects=healthy_effects,
            )

            result = module.evaluate_timeline([unknown, healthy])

        self.assertEqual(result["observations"][-1]["alert_state"], "FIRING")
        self.assertEqual(result["final_alert"]["unresolved_unknown_effects"], 1)
        self.assertEqual(result["final_alert"]["unresolved_effect_ids"], [effect_id])

    def test_same_run_unknown_snapshot_resolves_after_reconciliation(self) -> None:
        module = _load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            unknown_events, unknown_effects = _effect_fixture(
                "reconcile-001",
                started_at="2026-08-30T11:30:00.000Z",
                ended_at="2026-08-30T11:30:01.000Z",
                final_state="UNKNOWN",
            )
            unknown = _bundle(
                root,
                "reconcile-001",
                started_at="2026-08-30T11:30:00.000Z",
                ended_at="2026-08-30T11:30:01.000Z",
                outcome="UNKNOWN",
                events=unknown_events,
                effects=unknown_effects,
                bundle_name="reconcile-001-unknown",
                snapshot_role="UNKNOWN",
            )
            reconciled_events, reconciled_effects = _effect_fixture(
                "reconcile-001",
                started_at="2026-08-30T11:30:00.000Z",
                ended_at="2026-08-30T11:35:01.000Z",
                final_state="RECONCILED",
            )
            reconciled = _bundle(
                root,
                "reconcile-001",
                started_at="2026-08-30T11:30:00.000Z",
                ended_at="2026-08-30T11:35:01.000Z",
                outcome="SUCCEEDED",
                events=reconciled_events,
                effects=reconciled_effects,
                bundle_name="reconcile-001-reconciled",
                snapshot_role="RECONCILED",
            )

            result = module.evaluate_timeline([reconciled, unknown])

        self.assertEqual(
            [observation["alert_state"] for observation in result["observations"]],
            ["FIRING", "RESOLVED"],
        )
        self.assertEqual(result["transitions"][-1]["transition"], "FIRING->RESOLVED")

    def test_duplicate_run_without_reconciliation_is_rejected(self) -> None:
        module = _load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first_events, first_effects = _effect_fixture(
                "duplicate-001",
                started_at="2026-08-30T11:40:00.000Z",
                ended_at="2026-08-30T11:40:01.000Z",
                final_state="UNKNOWN",
            )
            first = _bundle(
                root,
                "duplicate-001",
                started_at="2026-08-30T11:40:00.000Z",
                ended_at="2026-08-30T11:40:01.000Z",
                outcome="UNKNOWN",
                events=first_events,
                effects=first_effects,
                bundle_name="duplicate-001-first",
            )
            second_events, second_effects = _effect_fixture(
                "duplicate-001",
                started_at="2026-08-30T11:40:00.000Z",
                ended_at="2026-08-30T11:41:01.000Z",
                final_state="UNKNOWN",
            )
            second = _bundle(
                root,
                "duplicate-001",
                started_at="2026-08-30T11:40:00.000Z",
                ended_at="2026-08-30T11:41:01.000Z",
                outcome="UNKNOWN",
                events=second_events,
                effects=second_effects,
                bundle_name="duplicate-001-second",
            )

            with self.assertRaisesRegex(module.EvidenceError, "unsupported snapshot"):
                module.evaluate_timeline([first, second])

    def test_succeeded_bundle_without_start_or_receipt_is_rejected(self) -> None:
        module = _load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            malformed = _bundle(
                root,
                "false-success-001",
                started_at="2026-08-30T11:45:00.000Z",
                ended_at="2026-08-30T11:45:01.000Z",
                outcome="SUCCEEDED",
                events=[
                    _event("false-success-001", 1, "run.accepted", "2026-08-30T11:45:00.000Z"),
                    _event(
                        "false-success-001",
                        2,
                        "run.terminal",
                        "2026-08-30T11:45:01.000Z",
                        data={
                            "authoritative_result_id": AUTHORITATIVE_RESULT_ID,
                            "outcome": "SUCCEEDED",
                            "result": "terminal",
                        },
                    ),
                ],
            )

            with self.assertRaisesRegex(module.EvidenceError, "run start|authoritative effect"):
                module.evaluate_timeline([malformed])

    def test_non_contiguous_event_sequence_is_rejected(self) -> None:
        module = _load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            malformed = _bundle(
                root,
                "malformed-001",
                started_at="2026-08-30T12:00:00.000Z",
                ended_at="2026-08-30T12:00:01.000Z",
                outcome="FAILED",
                events=[
                    _event("malformed-001", 1, "run.accepted", "2026-08-30T12:00:00.000Z"),
                    _event("malformed-001", 2, "run.started", "2026-08-30T12:00:00.000Z"),
                    _event(
                        "malformed-001",
                        4,
                        "run.terminal",
                        "2026-08-30T12:00:01.000Z",
                        data={"outcome": "FAILED", "result": "terminal"},
                    ),
                ],
            )
            with self.assertRaisesRegex(module.EvidenceError, "contiguous"):
                module.evaluate_timeline([malformed])

    def test_checksum_mismatch_is_rejected(self) -> None:
        module = _load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = _bundle(
                root,
                "tampered-001",
                started_at="2026-08-30T13:00:00.000Z",
                ended_at="2026-08-30T13:00:01.000Z",
                outcome="FAILED",
                events=[
                    _event("tampered-001", 1, "run.accepted", "2026-08-30T13:00:00.000Z"),
                    _event("tampered-001", 2, "run.started", "2026-08-30T13:00:00.000Z"),
                    _event(
                        "tampered-001",
                        3,
                        "run.terminal",
                        "2026-08-30T13:00:01.000Z",
                        data={"outcome": "FAILED", "result": "terminal"},
                    ),
                ],
            )
            event_lines = (bundle / "events.jsonl").read_text(encoding="utf-8").splitlines()
            first_event = json.loads(event_lines[0])
            first_event["data"] = {"tampered": True}
            event_lines[0] = json.dumps(first_event, sort_keys=True)
            (bundle / "events.jsonl").write_text(
                "\n".join(event_lines) + "\n", encoding="utf-8"
            )

            with self.assertRaisesRegex(module.EvidenceError, "checksum"):
                module.evaluate_timeline([bundle])


if __name__ == "__main__":
    unittest.main(verbosity=2)
