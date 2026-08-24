"""Offline CLI regressions for obs-alerting's error-budget calculator."""

from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CALCULATOR = ROOT / "skills" / "obs-alerting" / "scripts" / "error_budget.py"


def run_calculator(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CALCULATOR), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        timeout=30,
    )


class ErrorBudgetCliTests(unittest.TestCase):
    def test_exactly_exhausted_budget_displays_positive_zero(self) -> None:
        proc = run_calculator("--slo", "99.9", "--bad-minutes", "40.32")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("[EXHAUSTED]", proc.stdout)
        self.assertIn("remaining: 0.0 min", proc.stdout)
        self.assertNotIn("-0.0", proc.stdout)

    def test_time_and_request_units_cannot_be_mixed(self) -> None:
        proc = run_calculator(
            "--slo", "99.9", "--bad-minutes", "1", "--bad-events", "2",
            "--total-events", "1000",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("cannot be combined", proc.stderr)

    def test_both_windows_must_cross_the_bound_threshold_to_page(self) -> None:
        proc = run_calculator(
            "--slo", "99.9", "--sli-long", "98.5", "--sli-short", "98.5",
            "--long-window", "1h", "--short-window", "5m",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("PAGE (fast burn) -- both windows >= 14.4x", proc.stdout)

    def test_one_window_never_emits_a_page_or_ticket(self) -> None:
        proc = run_calculator("--slo", "99.9", "--sli-long", "98.5")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("severity: NOT EVALUATED", proc.stdout)
        self.assertNotIn("severity: PAGE", proc.stdout)
        self.assertNotIn("severity: TICKET", proc.stdout)

    def test_mismatched_window_pair_fails(self) -> None:
        proc = run_calculator(
            "--slo", "99.9", "--sli-long", "99", "--sli-short", "99",
            "--long-window", "1h", "--short-window", "30m",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("must be one of", proc.stderr)


if __name__ == "__main__":
    unittest.main()
