#!/usr/bin/env python3
"""Red-first contract for the Gate A weight-totals check."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_weight


class WeightEvaluationTests(unittest.TestCase):
    def test_measured_at_ceiling_passes(self) -> None:
        rows, failed = check_weight.evaluate({"x": 100}, {"x": 100})
        self.assertEqual([], failed)
        self.assertEqual([("x", 100, 100, 0)], rows)

    def test_measured_over_ceiling_fails(self) -> None:
        rows, failed = check_weight.evaluate({"x": 101}, {"x": 100})
        self.assertEqual(["x"], failed)
        self.assertEqual([("x", 101, 100, -1)], rows)

    def test_measured_under_ceiling_passes_with_headroom(self) -> None:
        rows, failed = check_weight.evaluate({"x": 90}, {"x": 100})
        self.assertEqual([], failed)
        self.assertEqual(10, rows[0][3])

    def test_one_over_ceiling_total_fails_the_whole_check_even_when_others_are_fine(self) -> None:
        rows, failed = check_weight.evaluate(
            {"a": 1, "b": 999}, {"a": 100, "b": 100}
        )
        self.assertEqual(["b"], failed)
        self.assertEqual(2, len(rows))

    def test_measure_returns_the_three_named_totals_the_real_ceilings_expect(self) -> None:
        weights = check_weight.load_weights()
        measured = check_weight.measure()
        self.assertEqual(set(weights), set(measured))


if __name__ == "__main__":
    unittest.main()
