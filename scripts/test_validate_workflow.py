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


if __name__ == "__main__":
    unittest.main(verbosity=2)
