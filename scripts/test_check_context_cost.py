"""Contracts for the G6 context-cost gate."""

from __future__ import annotations

import contextlib
import io
import unittest
from unittest import mock

import check_context_cost


class RealTreeTests(unittest.TestCase):
    def test_the_table_computes_on_the_real_tree_and_passes_at_placeholder_budgets(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = check_context_cost.main([])
        rendered = out.getvalue()
        self.assertEqual(0, code)
        self.assertIn("check_context_cost: PASS", rendered)
        for task in check_context_cost.TASK_BUDGETS:
            self.assertIn(task, rendered)
        self.assertIn(check_context_cost.DESCRIPTION_TASK, rendered)


class BudgetBreachTests(unittest.TestCase):
    def test_a_tightened_budget_exits_1_and_names_the_task(self) -> None:
        out = io.StringIO()
        with mock.patch.dict(check_context_cost.TASK_BUDGETS, {"Noisy alert": 1}):
            with contextlib.redirect_stdout(out):
                code = check_context_cost.main([])
        rendered = out.getvalue()
        self.assertEqual(1, code)
        self.assertIn("check_context_cost: FAIL", rendered)
        self.assertIn("Noisy alert", rendered)


class MissingPathTests(unittest.TestCase):
    def test_a_missing_file_is_reported_by_path(self) -> None:
        out, err = io.StringIO(), io.StringIO()
        bogus = {"Noisy alert": ["agents/does-not-exist.md"]}
        with mock.patch.dict(check_context_cost.TASK_FILES, bogus):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = check_context_cost.main([])
        self.assertEqual(1, code)
        self.assertIn("agents/does-not-exist.md", err.getvalue())


if __name__ == "__main__":
    raise SystemExit(unittest.main())
