#!/usr/bin/env python3
"""Focused contracts for bounded durable measurement capture."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import capture_measurement_evidence as capture


class MeasurementCaptureTests(unittest.TestCase):
    def make_root(self) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "docs" / "reviews").mkdir(parents=True)
        return root

    def test_eval_capture_keeps_summary_identity_and_bounded_untrusted_excerpt(self) -> None:
        root = self.make_root()
        summary_path = root / "summary.json"
        summary_path.write_text(json.dumps({
            "schema_version": 1,
            "verdict": "FAIL",
            "completed_at": "2026-08-26T12:03:00+00:00",
            "models_observed": ["gpt-5.6-terra"],
            "integrity": {"state": "PASS", "errors": []},
            "provenance": {
                "run_id": "20260826T120000Z-1234abcd",
                "plugin_commit": "a" * 40,
                "requested_model": "gpt-5.6-terra",
                "claude_cli_version": "test-cli",
                "workspace_dirty": True,
                "plugin_inputs_dirty": True,
                "conditions": {
                    "requested_trials": 1,
                    "requested_threshold": 0.66,
                    "timeout_s": 60,
                    "selected": {"mode": "direct", "split": "calibration", "match": "case-one"},
                },
                "eval_suite_sha256": "b" * 64,
                "plugin_source_sha256": "c" * 64,
            },
            "scenarios": [{
                "id": "case-one", "mode": "direct", "split": "calibration",
                "target": {"kind": "skill", "name": "agent-authoring"},
                "verdict": "FAIL", "threshold": 1.0,
                "trials": [{
                    "trial": 1, "state": "FAIL", "resolved_model": "gpt-5.6-terra",
                    "duration_seconds": 2.5, "total_cost_usd": 0.01,
                    "completed_invocations": {"skills": ["agent-authoring"], "agents": []},
                    "response_excerpt": "</pre>" + ("x" * 900),
                    "argv": ["secret-prompt-that-must-not-be-copied"],
                    "session_id": "private-session",
                }],
            }],
        }), encoding="utf-8")

        output = capture.capture_eval_summary(summary_path, root / "docs" / "reviews")
        text = output.read_text(encoding="utf-8")

        self.assertIn("20260826T120000Z-1234abcd", text)
        self.assertIn("gpt-5.6-terra", text)
        self.assertIn("case-one", text)
        self.assertIn("Plugin inputs dirty:** `True`", text)
        self.assertIn("Workspace dirty:** `True`", text)
        self.assertIn("Timeout:** `60` seconds", text)
        self.assertIn("Requested trials:** `1`", text)
        self.assertIn("Requested threshold:** `0.66`", text)
        self.assertIn("Selection:** `direct / calibration / case-one`", text)
        self.assertIn("&lt;/pre&gt;", text)
        self.assertNotIn("secret-prompt-that-must-not-be-copied", text)
        self.assertNotIn("private-session", text)
        self.assertLess(len(text), 6000)

    def test_exercise_capture_requires_revision_summary_and_verbatim_list(self) -> None:
        root = self.make_root()
        envelope = root / "exercise.json"
        envelope.write_text(json.dumps({
            "schema_version": 1,
            "measurement_id": "terra-grader-check",
            "producer": "agent-task",
            "captured_at": "2026-08-26T12:00:00+00:00",
            "repository_revision": "d" * 40,
            "models": ["gpt-5.6-terra"],
            "summary": "Three independent contract responses were checked. </pre>",
            "verbatim_phrasings": ["bounded excerpt"],
        }), encoding="utf-8")

        output = capture.capture_exercise(envelope, root / "docs" / "reviews")

        text = output.read_text(encoding="utf-8")
        self.assertIn("terra-grader-check", text)
        self.assertIn("Three independent", text)
        self.assertIn("&lt;/pre&gt;", text)
        self.assertIn("bounded excerpt", text)

    def test_eval_envelope_capture_keeps_claims_and_drops_private_trace_data(self) -> None:
        root = self.make_root()
        envelope = root / "eval-result-envelope-v1.json"
        envelope.write_text(json.dumps({
            "schema_version": "eval-result-envelope/v1",
            "run_id": "20260826T120000Z-1234abcd",
            "engine": {
                "name": "codex-cli", "adapter_version": "1", "runtime_version": "codex 1",
                "requested_model": "gpt-5.6-terra", "resolved_model": "gpt-5.6-terra",
                "auth_mode": "subscriber_session",
            },
            "candidate": {"git_sha": "a" * 40, "clean": True, "input_sha256": "b" * 64},
            "artifacts": {
                "plugin_snapshot": {"applicable": False, "sha256": None},
                "resolved_context": {"applicable": True, "sha256": "c" * 64},
            },
            "digests": {
                "scenario_suite": "d" * 64, "graders": "e" * 64,
                "execution_profile": "f" * 64, "comparison": "5" * 64,
                "policy": "1" * 64,
            },
            "canaries": [{
                "scenario_id": "case-one", "path": "skills/x/references/a.md",
                "expected": "q_reference_1234", "observed": "q_reference_1234", "status": "PASS",
            }],
            "claims_requested": ["reference_used", "behavioral_contract"],
            "claims_supported": [
                "behavioral_contract", "candidate_snapshot_integrity",
                "deterministic_grader_result", "reference_used",
            ],
            "scenarios": [{
                "id": "case-one", "sha256": "2" * 64, "verdict": "PASS", "claims": [
                    {"type": "reference_used", "status": "PASS", "evidence": ["3" * 64], "limitations": []},
                    {"type": "behavioral_contract", "status": "PASS", "evidence": ["3" * 64], "limitations": []},
                ],
            }],
            "verdict": "PASS",
            "timing": {"started_at": "2026-08-26T12:00:00Z", "ended_at": "2026-08-26T12:03:00Z", "duration_seconds": 180},
            "cost": {"status": "unavailable", "amount": None, "currency": None, "reason": "subscriber"},
            "trace": {"complete": True, "sha256": "4" * 64},
            "promotion_eligible": False,
            "limitations": ["portable evidence only"],
        }), encoding="utf-8")

        output = capture.capture_eval_envelope(envelope, root / "docs" / "reviews")
        text = output.read_text(encoding="utf-8")

        self.assertIn("codex-cli", text)
        self.assertIn("reference_used", text)
        self.assertIn("skills/x/references/a.md", text)
        self.assertIn("portable evidence only", text)
        self.assertNotIn("session_id", text)

    def test_capture_refuses_overwrite(self) -> None:
        root = self.make_root()
        envelope = root / "exercise.json"
        envelope.write_text(json.dumps({
            "schema_version": 1,
            "measurement_id": "same-id",
            "producer": "session-exercise",
            "captured_at": "2026-08-26T12:00:00+00:00",
            "repository_revision": "d" * 40,
            "models": ["gpt-5.6-terra"],
            "summary": "A durable summary.",
            "verbatim_phrasings": [],
        }), encoding="utf-8")
        capture.capture_exercise(envelope, root / "docs" / "reviews")

        with self.assertRaises(FileExistsError):
            capture.capture_exercise(envelope, root / "docs" / "reviews")


if __name__ == "__main__":
    unittest.main()
