#!/usr/bin/env python3
"""Contract tests for the cross-platform fleet-validation workflow."""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "validate.yml"


class ValidateWorkflowTests(unittest.TestCase):
    def test_linux_and_windows_are_the_only_gate_platforms(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("runs-on: ubuntu-latest", workflow)
        self.assertIn("runs-on: windows-latest", workflow)
        self.assertNotIn(
            "macos-latest",
            workflow,
            "macOS duplicated Linux or Windows in the measured workflow history",
        )

    def test_gate_a_jobs_do_not_fetch_history_for_focused_component_tests(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        validate_job, separator, _remainder = workflow.partition(
            "\n  claude-plugin-contract:"
        )
        self.assertTrue(separator, "validate workflow lost the plugin-contract job boundary")
        self.assertNotIn(
            "fetch-depth: 0",
            validate_job,
            "the structural gate reads the checked-out tree; focused snapshot tests own history",
        )

    def test_gate_a_jobs_do_not_install_eval_harness_dependencies(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        validate_job, separator, _remainder = workflow.partition(
            "\n  claude-plugin-contract:"
        )
        self.assertTrue(separator, "validate workflow lost the plugin-contract job boundary")
        self.assertNotIn(
            "requirements-dev.txt",
            validate_job,
            "PyYAML belongs to focused eval work, not every structural CI run",
        )

    def test_windows_gate_runs_on_pull_requests(self) -> None:
        """Windows keeps native path and generated-byte validation on every pull request."""
        workflow = WORKFLOW.read_text(encoding="utf-8")
        linux_job, separator, remainder = workflow.partition("\n  validate-windows:")
        self.assertTrue(separator, "validate workflow has no dedicated validate-windows job")
        self.assertNotIn("windows-latest", linux_job, "Windows runs as its own job")
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
