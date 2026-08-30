from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from runner.controls import CancellationError, transition_cancellation
from runner.evidence import EvidenceExporter
from runner.runtime import runtime_evidence


class CancellationContractTests(unittest.TestCase):
    def test_requested_cancellation_requires_positive_acknowledgement(self) -> None:
        requested = {
            "state": "REQUESTED",
            "request_id": "cancel-001",
            "acknowledgement_ms": None,
        }

        propagated = transition_cancellation(requested, "PROPAGATED")
        acknowledged = transition_cancellation(
            propagated,
            "ACKNOWLEDGED",
            acknowledgement_ms=17,
        )

        self.assertEqual(acknowledged["state"], "ACKNOWLEDGED")
        self.assertEqual(acknowledged["acknowledgement_ms"], 17)
        self.assertEqual(requested["state"], "REQUESTED")

    def test_cancellation_cannot_skip_propagation(self) -> None:
        with self.assertRaisesRegex(CancellationError, "REQUESTED -> ACKNOWLEDGED"):
            transition_cancellation(
                {
                    "state": "REQUESTED",
                    "request_id": "cancel-001",
                    "acknowledgement_ms": None,
                },
                "ACKNOWLEDGED",
                acknowledgement_ms=1,
            )

    def test_unconfirmed_cancellation_has_no_acknowledgement(self) -> None:
        result = transition_cancellation(
            {
                "state": "PROPAGATED",
                "request_id": "cancel-001",
                "acknowledgement_ms": None,
            },
            "UNCONFIRMED",
        )
        self.assertEqual(result["state"], "UNCONFIRMED")
        self.assertIsNone(result["acknowledgement_ms"])


class RuntimeEvidenceTests(unittest.TestCase):
    def test_runtime_evidence_records_observed_versions(self) -> None:
        evidence = runtime_evidence()

        self.assertEqual(evidence["runtime_version"], "graph-runner-runtime/v1")
        self.assertEqual(evidence["python_version"], "3.12.10")
        self.assertEqual(
            evidence["packages"],
            {
                "httpx": "0.28.1",
                "langgraph": "1.0.10",
                "langgraph-checkpoint-sqlite": "3.1.1",
            },
        )


class EvidenceExportTests(unittest.TestCase):
    def test_atomic_json_export_leaves_no_temporary_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            exporter = EvidenceExporter(Path(temp_dir), "mission-healthy-001")

            exporter.write_json("final-state.json", {"outcome": "INCONCLUSIVE"})

            output = Path(temp_dir) / "mission-healthy-001" / "final-state.json"
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), {"outcome": "INCONCLUSIVE"})
            self.assertEqual(list(output.parent.glob("*.tmp")), [])

    def test_export_rejects_escape_from_run_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            exporter = EvidenceExporter(Path(temp_dir), "mission-healthy-001")
            with self.assertRaisesRegex(ValueError, "relative evidence path"):
                exporter.write_json("../escaped.json", {})

    def test_checksums_cover_every_existing_regular_artifact_except_checksum_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            exporter = EvidenceExporter(Path(temp_dir), "mission-healthy-001")
            exporter.write_json("final-state.json", {"outcome": "SUCCEEDED"})
            exporter.write_json("receipts/payment.json", {"receipt_id": "pay-001"})

            checksums = exporter.write_checksums()

            self.assertEqual(
                {entry["path"] for entry in checksums},
                {"final-state.json", "receipts/payment.json"},
            )
            checksum_text = (exporter.run_dir / "checksums.sha256").read_text(encoding="utf-8")
            self.assertNotIn("checksums.sha256", checksum_text)


if __name__ == "__main__":
    unittest.main()
