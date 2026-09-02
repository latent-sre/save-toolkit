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

    def test_eval_capture_records_the_judge_that_decided_rubric_verdicts(self) -> None:
        """A rubric-backed verdict is one model judging another; the durable record must name it.

        The private batch may be reclaimed once this file is committed, so a judge identity that
        lives only there cannot afterwards attribute or compare a rubric PASS/FAIL.
        """
        root = self.make_root()
        summary_path = root / "summary.json"
        summary_path.write_text(json.dumps({
            "schema_version": 1,
            "verdict": "PASS",
            "completed_at": "2026-09-01T12:03:00+00:00",
            "models_observed": ["claude-opus-5"],
            "judge_model_requested": "sonnet",
            "judge_models_observed": ["claude-sonnet-5"],
            "integrity": {"state": "PASS", "errors": []},
            "provenance": {
                "run_id": "20260901T120000Z-1234abcd",
                "plugin_commit": "a" * 40,
                "requested_model": "opus",
                "judge_model": "sonnet",
                "rubrics_sha256": "d" * 64,
                "conditions": {"selected": {"mode": "direct", "split": None, "match": None}},
            },
            "scenarios": [{
                "id": "case-one", "mode": "direct", "split": "calibration",
                "target": {"kind": "skill", "name": "agent-authoring"},
                "verdict": "PASS", "threshold": 1.0,
                "trials": [{
                    "trial": 1, "state": "PASS", "resolved_model": "claude-opus-5",
                    "duration_seconds": 20.0, "total_cost_usd": 0.40,
                    "judge": {"calls": 2, "cost_usd": 0.06, "seconds": 8.0,
                              "cached_calls": 0, "models_resolved": ["claude-sonnet-5"]},
                    "completed_invocations": {"skills": [], "agents": []},
                    "response_excerpt": "a response",
                }],
            }],
        }), encoding="utf-8")

        text = capture.capture_eval_summary(summary_path, root / "docs" / "reviews").read_text(encoding="utf-8")

        self.assertIn("Requested judge model:** `sonnet`", text)
        self.assertIn("Observed judge models:** `claude-sonnet-5`", text)
        self.assertIn("Rubrics SHA-256:** `" + "d" * 64 + "`", text)
        # The judge's spend is named, not folded into the evaluated agent's totals.
        self.assertIn("USD 0.4000.", text)
        self.assertIn("Rubric judge: 2 calls; 8.0 seconds; USD 0.0600.", text)

    def test_eval_capture_of_a_batch_with_no_judge_says_none(self) -> None:
        root = self.make_root()
        summary_path = root / "summary.json"
        summary_path.write_text(json.dumps({
            "schema_version": 1,
            "verdict": "PASS",
            "completed_at": "2026-09-01T12:03:00+00:00",
            "integrity": {"state": "PASS", "errors": []},
            "provenance": {
                "run_id": "20260901T130000Z-1234abcd",
                "plugin_commit": "a" * 40,
                "conditions": {"selected": {}},
            },
            "scenarios": [],
        }), encoding="utf-8")

        text = capture.capture_eval_summary(summary_path, root / "docs" / "reviews").read_text(encoding="utf-8")

        self.assertIn("Requested judge model:** `none`", text)
        self.assertIn("Observed judge models:** `none`", text)
        self.assertNotIn("Rubric judge:", text)

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

    def test_exercise_capture_rejects_an_envelope_that_cannot_be_attributed(self) -> None:
        """Each field the validator demands is the one that makes the record attributable later."""
        root = self.make_root()
        envelope = root / "exercise.json"
        valid = {
            "schema_version": 1,
            "measurement_id": "attribution-check",
            "producer": "session-exercise",
            "captured_at": "2026-08-26T12:00:00+00:00",
            "repository_revision": "d" * 40,
            "models": ["gpt-5.6-terra"],
            "summary": "A durable summary.",
            "verbatim_phrasings": [],
        }
        broken = {
            "no schema_version": {"schema_version": 2},
            "unsafe id": {"measurement_id": "../escape"},
            "unknown producer": {"producer": "anonymous"},
            "short revision": {"repository_revision": "d" * 7},
            "empty summary": {"summary": "   "},
            "no models": {"models": []},
            "phrasings not a list": {"verbatim_phrasings": "one"},
            "too many phrasings": {"verbatim_phrasings": ["x"] * 9},
        }
        for label, override in broken.items():
            with self.subTest(case=label):
                envelope.write_text(json.dumps({**valid, **override}), encoding="utf-8")
                with self.assertRaises(capture.CaptureError):
                    capture.capture_exercise(envelope, root / "docs" / "reviews")

        envelope.write_text(json.dumps(valid), encoding="utf-8")
        capture.capture_exercise(envelope, root / "docs" / "reviews")
        with self.assertRaises(FileExistsError):
            capture.capture_exercise(envelope, root / "docs" / "reviews")

    def test_the_documented_exercise_subcommand_exists(self) -> None:
        """`evals/README.md` tells an operator to run this before transient host output is gone."""
        root = self.make_root()
        envelope = root / "exercise.json"
        envelope.write_text(json.dumps({
            "schema_version": 1,
            "measurement_id": "cli-path-check",
            "producer": "manual-exercise",
            "captured_at": "2026-08-26T12:00:00+00:00",
            "repository_revision": "d" * 40,
            "models": ["gpt-5.6-terra"],
            "summary": "Captured through the CLI.",
            "verbatim_phrasings": [],
        }), encoding="utf-8")

        code = capture.main(["--reviews-dir", str(root / "docs" / "reviews"), "exercise", str(envelope)])

        self.assertEqual(code, 0)
        self.assertTrue((root / "docs" / "reviews" / "2026-08-26-exercise-cli-path-check.md").is_file())

    def test_capture_refuses_overwrite(self) -> None:
        root = self.make_root()
        summary_path = root / "summary.json"
        summary_path.write_text(json.dumps({
            "schema_version": 1,
            "verdict": "PASS",
            "completed_at": "2026-08-26T12:03:00+00:00",
            "models_observed": ["gpt-5.6-terra"],
            "integrity": {"state": "PASS", "errors": []},
            "provenance": {
                "run_id": "20260826T120000Z-1234abcd",
                "plugin_commit": "a" * 40,
                "requested_model": "gpt-5.6-terra",
                "claude_cli_version": "test-cli",
                "workspace_dirty": False,
                "plugin_inputs_dirty": False,
                "conditions": {
                    "requested_trials": 1,
                    "requested_threshold": 0.66,
                    "timeout_s": 60,
                    "selected": {"mode": "direct", "split": "calibration", "match": "case-one"},
                },
                "eval_suite_sha256": "b" * 64,
                "plugin_source_sha256": "c" * 64,
            },
            "scenarios": [],
        }), encoding="utf-8")
        capture.capture_eval_summary(summary_path, root / "docs" / "reviews")

        with self.assertRaises(FileExistsError):
            capture.capture_eval_summary(summary_path, root / "docs" / "reviews")


if __name__ == "__main__":
    unittest.main()
