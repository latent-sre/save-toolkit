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
MODULE_PATH = ROOT / "skills/obs-alerting/scripts/graph_sandbox_alerts.py"


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


def _bundle(
    root: Path,
    run_id: str,
    *,
    started_at: str,
    ended_at: str,
    outcome: str,
    events: list[dict[str, object]],
    effects: list[dict[str, object]] | None = None,
) -> Path:
    bundle = root / run_id
    bundle.mkdir()
    _write_json(
        bundle / "manifest.json",
        {
            "artifacts": ["effects.jsonl", "events.jsonl", "verification.json"],
            "authoritative_result_id": "result-001" if outcome == "SUCCEEDED" else None,
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
    _write_json(
        bundle / "verification.json",
        {
            "exit_code": 0 if outcome == "SUCCEEDED" else 2,
            "run_id": run_id,
            "source_revision": "a" * 40,
            "verification_version": "graph-sandbox-host-verification/v1",
        },
    )
    _write_jsonl(bundle / "events.jsonl", events)
    _write_jsonl(bundle / "effects.jsonl", effects or [])
    _write_checksums(
        bundle,
        ["effects.jsonl", "events.jsonl", "manifest.json", "verification.json"],
    )
    return bundle


class GraphSandboxAlertsTest(unittest.TestCase):
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
                    _event(
                        "failed-001",
                        2,
                        "edge.join_starved",
                        "2026-08-30T10:00:00.500Z",
                        failure_plane="checkout",
                        error_class="readiness_join_incomplete",
                    ),
                    _event("failed-001", 3, "run.terminal", "2026-08-30T10:00:01.000Z"),
                ],
            )
            recovered = _bundle(
                root,
                "healthy-002",
                started_at="2026-08-30T10:05:00.000Z",
                ended_at="2026-08-30T10:05:01.000Z",
                outcome="SUCCEEDED",
                events=[
                    _event("healthy-002", 1, "run.accepted", "2026-08-30T10:05:00.000Z"),
                    _event("healthy-002", 2, "run.terminal", "2026-08-30T10:05:01.000Z"),
                ],
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
            effect_id = "unknown-001:checkout:effect-1"
            unknown = _bundle(
                root,
                "unknown-001",
                started_at="2026-08-30T11:00:00.000Z",
                ended_at="2026-08-30T11:00:01.000Z",
                outcome="UNKNOWN",
                events=[
                    _event("unknown-001", 1, "run.accepted", "2026-08-30T11:00:00.000Z"),
                    _event(
                        "unknown-001",
                        2,
                        "effect.unknown",
                        "2026-08-30T11:00:00.500Z",
                        effect_id=effect_id,
                        failure_plane="checkout",
                        error_class="checkout_target_reported_unknown",
                    ),
                    _event("unknown-001", 3, "run.terminal", "2026-08-30T11:00:01.000Z"),
                ],
                effects=[
                    {
                        "effect_id": effect_id,
                        "effect_state": "UNKNOWN",
                        "sequence": 1,
                        "target": "checkout",
                        "time_utc": "2026-08-30T11:00:00.500Z",
                    }
                ],
            )
            healthy = _bundle(
                root,
                "healthy-003",
                started_at="2026-08-30T11:05:00.000Z",
                ended_at="2026-08-30T11:05:01.000Z",
                outcome="SUCCEEDED",
                events=[
                    _event("healthy-003", 1, "run.accepted", "2026-08-30T11:05:00.000Z"),
                    _event("healthy-003", 2, "run.terminal", "2026-08-30T11:05:01.000Z"),
                ],
            )

            result = module.evaluate_timeline([unknown, healthy])

        self.assertEqual(result["observations"][-1]["alert_state"], "FIRING")
        self.assertEqual(result["final_alert"]["unresolved_unknown_effects"], 1)
        self.assertEqual(result["final_alert"]["unresolved_effect_ids"], [effect_id])

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
                    _event("malformed-001", 3, "run.terminal", "2026-08-30T12:00:01.000Z"),
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
                    _event("tampered-001", 2, "run.terminal", "2026-08-30T13:00:01.000Z"),
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
