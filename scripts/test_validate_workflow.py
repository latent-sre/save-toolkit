#!/usr/bin/env python3
"""Contract tests for the cross-platform fleet-validation workflow."""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "validate.yml"


class ValidateWorkflowTests(unittest.TestCase):
    def test_gate_a_checkout_includes_the_full_history_used_by_snapshot_tests(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        validate_job, separator, _remainder = workflow.partition(
            "\n  claude-plugin-contract:"
        )
        self.assertTrue(separator, "validate workflow lost the plugin-contract job boundary")
        self.assertRegex(
            validate_job,
            re.compile(
                r"^      - name: Check out repository\n"
                r"        uses: actions/checkout@[^\n]+\n"
                r"        with:\n"
                r"          fetch-depth: 0(?:\n|$)",
                re.MULTILINE,
            ),
            "Gate A materializes fixed historical SHAs and requires a full checkout",
        )

    def test_every_gate_a_job_checks_out_full_history(self) -> None:
        """The full-history requirement belongs to every job that runs the gate, not the first one."""
        workflow = WORKFLOW.read_text(encoding="utf-8")
        gate_runs = workflow.count("scripts/gate_a.py\n")
        full_checkouts = len(re.findall(r"^          fetch-depth: 0$", workflow, re.MULTILINE))
        self.assertGreaterEqual(gate_runs, 2, "expected at least the matrix job and the Windows job to run the gate")
        self.assertEqual(gate_runs, full_checkouts, "a Gate A job without fetch-depth: 0 cannot materialize the pinned historical SHAs")

    def test_windows_gate_runs_on_pull_requests(self) -> None:
        """Windows is its own job rather than a matrix entry so its ~44 s gate does not hold the
        Linux/macOS fail-fast matrix -- but it runs on every pull request. The guard, the gate lock,
        the adapters, and the host-install probes all have Windows-only behavior the other OSes
        cannot exercise, and `Protect main` has no required status check, so catching a Windows
        break on merge or on the weekly schedule is too late. A local owner run is not enforceable
        evidence. The schedule and dispatch remain as the floor for quiet weeks."""
        workflow = WORKFLOW.read_text(encoding="utf-8")
        matrix_job, separator, remainder = workflow.partition("\n  validate-windows:")
        self.assertTrue(separator, "validate workflow has no dedicated validate-windows job")
        self.assertNotIn("windows-latest", matrix_job, "Windows runs as its own job, not a matrix entry")
        windows_job = remainder.partition("\n  claude-plugin-contract:")[0]
        self.assertIn("runs-on: windows-latest", windows_job)
        self.assertNotRegex(
            windows_job,
            re.compile(r"^    if: .*pull_request", re.MULTILINE),
            "the Windows gate must not be skipped on pull requests",
        )
        self.assertIn("run: python scripts/gate_a.py", windows_job, "Windows must invoke `python`, never the Store-stub `python3`")

    def test_windows_gate_still_has_a_schedule(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        triggers = workflow.partition("\npermissions:")[0]
        self.assertRegex(triggers, re.compile(r"^  schedule:\n    - cron: ", re.MULTILINE))
        self.assertIn("workflow_dispatch:", triggers)


if __name__ == "__main__":
    unittest.main(verbosity=2)
