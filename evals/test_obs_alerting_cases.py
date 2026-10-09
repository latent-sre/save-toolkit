"""Calibrate the partial-helper alert predicate without a model or Prometheus."""

import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml
from probe_testkit import scenario_file

ROOT = Path(__file__).resolve().parent
LONG = "checkout:availability:error_ratio_rate1h"
SHORT = "checkout:availability:error_ratio_rate5m"


class AlertPredicateCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = scenario_file(
            ROOT / "build-scenarios/build-observability-engineer-resumes-after-partial-helper.yaml"
        )
        cls.seed = spec["fixture"]["files"]["alerts/checkout.rules.yml"]
        check = next(check for check in spec["checks"] if check["check"] == "command_exit_zero")
        command = shlex.split(check["command"])
        assert command[:2] == ["python", "-c"] and len(command) == 3
        cls.code = command[2]

    def check_expression(self, expression):
        document = yaml.safe_load(self.seed)
        document["groups"][0]["rules"].append({
            "alert": "CheckoutAvailabilityFastBurn",
            "expr": expression,
            "for": "2m",
            "labels": {"severity": "page"},
            "annotations": {"runbook_url": "docs/runbooks/checkout-availability.md"},
        })
        with tempfile.TemporaryDirectory(prefix="obs-alerting-case-") as directory:
            root = Path(directory)
            target = root / "alerts/checkout.rules.yml"
            target.parent.mkdir()
            target.write_text(yaml.safe_dump(document), encoding="utf-8", newline="")
            return subprocess.run(
                [sys.executable, "-I", "-B", "-c", self.code],
                cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=15,
            )

    def test_supported_two_window_filters_pass(self):
        expressions = (
            f"({LONG} > 0.0144) and ({SHORT} > 0.0144)",
            f"({LONG} > 14.4 * 0.001) and ({SHORT} > 14.4 * 0.001)",
            f"({LONG} / 0.001 > 14.4)\nand\n({SHORT} / 0.001 > 14.4)",
        )
        for expression in expressions:
            with self.subTest(expression=expression):
                result = self.check_expression(expression)
                self.assertEqual(0, result.returncode, result.stderr)

    def test_semantic_modifiers_are_rejected_instead_of_erased(self):
        expressions = (
            f"({LONG} > bool 0.0144) and ({SHORT} > bool 0.0144)",
            f"({LONG} > bool 0.0144) and ({SHORT} > 0.0144)",
            f"({LONG} > 0.0144) and on() ({SHORT} > 0.0144)",
            f"({LONG} > 0.0144) and ignoring(job) ({SHORT} > 0.0144)",
        )
        for expression in expressions:
            with self.subTest(expression=expression):
                result = self.check_expression(expression)
                self.assertNotEqual(0, result.returncode, expression)
                self.assertIn("unsupported expression form", result.stderr)

    def test_wrong_predicates_still_fail(self):
        expressions = (
            f"({LONG} > 0.0144) or ({SHORT} > 0.0144)",
            f"({LONG} > 14.4) and ({SHORT} > 14.4)",
            f"{LONG} > 0.0144",
            f"({LONG} < 0.0144) and ({SHORT} < 0.0144)",
        )
        for expression in expressions:
            with self.subTest(expression=expression):
                result = self.check_expression(expression)
                self.assertNotEqual(0, result.returncode, expression)
                self.assertIn("AssertionError", result.stderr)


if __name__ == "__main__":
    unittest.main()
