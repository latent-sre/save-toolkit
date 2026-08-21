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

    def test_windows_gate_is_off_the_pull_request_path(self) -> None:
        """Windows is the PR long pole (Gate A ~44 s there vs ~19 s on Linux) and the owner runs the
        full gate on Windows locally before every push, so PRs do not wait for it. It still runs on
        pushes to main, on a weekly schedule, and on dispatch, so a Linux-authored change that breaks
        Windows is caught on merge or within the week rather than never."""
        workflow = WORKFLOW.read_text(encoding="utf-8")
        matrix_job, separator, remainder = workflow.partition("\n  validate-windows:")
        self.assertTrue(separator, "validate workflow has no dedicated validate-windows job")
        self.assertNotIn("windows-latest", matrix_job, "the PR matrix must not carry a Windows entry")
        windows_job = remainder.partition("\n  claude-plugin-contract:")[0]
        self.assertIn("runs-on: windows-latest", windows_job)
        self.assertRegex(windows_job, re.compile(r"^    if: github\.event_name != 'pull_request'$", re.MULTILINE))
        self.assertIn("run: python scripts/gate_a.py", windows_job, "Windows must invoke `python`, never the Store-stub `python3`")

    def test_windows_gate_still_has_a_schedule(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        triggers = workflow.partition("\npermissions:")[0]
        self.assertRegex(triggers, re.compile(r"^  schedule:\n    - cron: ", re.MULTILINE))
        self.assertIn("workflow_dispatch:", triggers)


if __name__ == "__main__":
    unittest.main(verbosity=2)
