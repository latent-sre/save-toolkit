"""Offline CLI regressions for obs-alerting's error-budget calculator."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import unittest
from decimal import Decimal
from pathlib import Path

from testkit import load_path

ROOT = Path(__file__).resolve().parents[1]
CALCULATOR = ROOT / "skills" / "obs-alerting" / "scripts" / "error_budget.py"


def run_calculator(*args: str, **env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CALCULATOR), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8", **env},
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

    def test_decimal_thresholds_are_inclusive_without_rounding_lower_burns_up(self) -> None:
        # For a 99.99% SLO, these are the independent 14.4x, 6x and 1x SLI boundaries.
        pairs = (
            ("1h", "5m", "99.856", "99.8559", "99.8561", "PAGE (fast burn)"),
            ("6h", "30m", "99.94", "99.9399", "99.9401", "PAGE (slow burn)"),
            ("3d", "6h", "99.99", "99.9899", "99.9901", "TICKET (slow leak)"),
        )
        for long_window, short_window, boundary, higher, lower, action in pairs:
            cases = (
                ("exact", boundary, action), ("above", higher, action),
                ("below", lower, "below the"),
                ("below beyond float precision", boundary + "000000000000000000001", "below the"),
            )
            for name, sli, expected in cases:
                with self.subTest(pair=(long_window, short_window), case=name):
                    proc = run_calculator("--slo", "99.99", "--sli-long", sli,
                                          "--sli-short", sli, "--long-window", long_window,
                                          "--short-window", short_window)
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    self.assertIn("severity: " + expected, proc.stdout)

    def test_decimal_boundary_still_requires_both_windows(self) -> None:
        for long_window, short_window, boundary, lower_burn in (
            ("1h", "5m", "99.856", "99.8561"),
            ("6h", "30m", "99.94", "99.9401"),
            ("3d", "6h", "99.99", "99.9901"),
        ):
            for long_sli, short_sli, expected in (
                (boundary, lower_burn, "has recovered"),
                (lower_burn, boundary, "short-window spike"),
            ):
                with self.subTest(pair=(long_window, short_window), long=long_sli, short=short_sli):
                    proc = run_calculator("--slo", "99.99", "--sli-long", long_sli,
                                          "--sli-short", short_sli, "--long-window", long_window,
                                          "--short-window", short_window)
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    self.assertIn(expected, proc.stdout)
                    self.assertNotIn("severity: PAGE", proc.stdout)
                    self.assertNotIn("severity: TICKET", proc.stdout)

    def test_long_decimal_slo_and_scientific_spelling_keep_the_exact_boundary(self) -> None:
        for slo, sli, expected in (
            ("9.999e1", "9.9856e1", "PAGE (fast burn)"),
            ("99.990000000000000000000000001", "99.8560000000000000000000000144", "PAGE (fast burn)"),
            ("99.990000000000000000000000001", "99.8560000000000000000000000145", "below the"),
        ):
            with self.subTest(slo=slo, sli=sli):
                proc = run_calculator("--slo", slo, "--sli-long", sli, "--sli-short", sli)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIn("severity: " + expected, proc.stdout)

    def test_invalid_percentages_remain_usage_errors_without_tracebacks(self) -> None:
        for options in (("--slo", "bad"), ("--slo", "nan"), ("--slo", "inf"),
                        ("--slo", "1e999"), ("--slo", "0"), ("--slo", "100"),
                        ("--slo", "99.9", "--sli-long", "nan"),
                        ("--slo", "99.9", "--sli-long", "101")):
            with self.subTest(options=options):
                proc = run_calculator(*options)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertNotIn("Traceback", proc.stderr)

    def test_status_horizon_does_not_rescale_fixed_alert_policy(self) -> None:
        for horizon, remaining in (("7", "10.1 min"), ("28", "40.3 min")):
            with self.subTest(horizon=horizon):
                proc = run_calculator(
                    "--slo", "99.9", "--window-days", horizon, "--bad-minutes", "0",
                    "--sli-long", "98.5", "--sli-short", "98.5",
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIn("remaining: " + remaining, proc.stdout)
                self.assertIn("PAGE (fast burn) -- both windows >= 14.4x", proc.stdout)

    def test_help_keeps_its_description_whole_on_a_narrow_terminal(self) -> None:
        proc = run_calculator("--help", COLUMNS="40")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("\nSLO error-budget and burn-rate calculator\n", proc.stdout)

    def test_mismatched_window_pair_fails(self) -> None:
        proc = run_calculator(
            "--slo", "99.9", "--sli-long", "99", "--sli-short", "99",
            "--long-window", "1h", "--short-window", "30m",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("must be one of", proc.stderr)


class StructuredResultTests(unittest.TestCase):
    """The records main renders are the seam a product adapter reads instead of scraping text."""

    calculator = load_path(CALCULATOR, "error_budget")

    def test_burn_verdict_names_each_boundary_of_the_pair(self) -> None:
        # For a 99.99% SLO the 1h/5m pair's 14.4x boundary is an SLI of exactly 99.856.
        for sli_long, sli_short, outcome in (("99.856", "99.856", "both"), ("99.856", "99.8561", "long only"),
                                             ("99.8561", "99.856", "short only"),
                                             ("99.8561", "99.8561", "neither")):
            with self.subTest(long=sli_long, short=sli_short):
                verdict = self.calculator.burn_verdict(Decimal("99.99"), Decimal(sli_long), Decimal(sli_short),
                                                       "1h", "5m")
                self.assertEqual(outcome, verdict.outcome)
                self.assertEqual("PAGE (fast burn)", verdict.action)

    def test_invalid_inputs_raise_with_the_flag_named(self) -> None:
        fields = dict(slo=Decimal("99.9"), window_days=28.0, bad_minutes=1.0, bad_events=2.0, total_events=10.0,
                      sli_long=None, sli_short=None, long_window="1h", short_window="5m")
        with self.assertRaisesRegex(ValueError, "^--bad-minutes .*cannot be combined"):
            self.calculator.Inputs(**fields)

    def test_a_plain_file_path_import_needs_no_module_registration(self) -> None:
        # The bare spec_from_file_location recipe an adapter might copy; nothing enters sys.modules.
        spec = importlib.util.spec_from_file_location("error_budget_unregistered", CALCULATOR)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertNotIn("error_budget_unregistered", sys.modules)
        verdict = module.burn_verdict(Decimal("99.99"), Decimal("99.856"), Decimal("99.856"), "1h", "5m")
        self.assertEqual("both", verdict.outcome)

    def test_time_status_reports_an_exhausted_budget_as_exactly_zero(self) -> None:
        status = self.calculator.time_status(Decimal("99.9"), 28.0, 40.32)
        self.assertEqual(("EXHAUSTED", 0.0), (status.state, status.remaining))


if __name__ == "__main__":
    unittest.main()
