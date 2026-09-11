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


class CraftPathTests(unittest.TestCase):
    def test_craft_profiles_include_their_required_context(self) -> None:
        common = {
            "agents/software-engineer.md",
            "skills/stack-profile/SKILL.md",
            "skills/stack-profile/references/application-and-data-stack.md",
        }
        expected = {
            "FastAPI upstream change": {
                "skills/backend-craft/SKILL.md",
                "skills/backend-craft/references/fastapi.md",
                "skills/backend-craft/references/consuming-apis.md",
                "skills/python-craft/SKILL.md",
                "skills/python-craft/references/writing-python.md",
            },
            "Python automated refactor": {
                "skills/python-craft/SKILL.md",
                "skills/python-craft/references/writing-python.md",
                "skills/python-craft/references/refactoring.md",
                "skills/python-craft/references/refactoring-tools.md",
            },
            "Python library migration": {
                "skills/python-craft/SKILL.md",
                "skills/python-craft/references/writing-python.md",
                "skills/python-craft/references/libraries-and-modernization.md",
                "skills/python-craft/references/refactoring-tools.md",
            },
            "Existing UI change": {"skills/frontend-craft/SKILL.md"},
            "Greenfield UI": {
                "skills/frontend-craft/SKILL.md",
                "skills/frontend-craft/references/stack.md",
                "skills/frontend-craft/references/design-language.md",
            },
        }
        for task, required in expected.items():
            with self.subTest(task=task):
                paths = check_context_cost.TASK_FILES.get(task, [])
                self.assertTrue(common | required <= set(paths), "required task context omitted")
                self.assertNotIn("skills/production-change-gate/SKILL.md", paths)
                self.assertEqual(len(paths), len(set(paths)), "shared files counted twice")
                self.assertIn(task, check_context_cost.TASK_BUDGETS)

    def test_python_depth_stays_conditional_and_every_reference_is_measured(self) -> None:
        for task in ("Existing UI change", "Greenfield UI"):
            with self.subTest(task=task):
                self.assertFalse(any("python-craft" in path
                                     for path in check_context_cost.TASK_FILES[task]))
        measured = {path for paths in check_context_cost.TASK_FILES.values() for path in paths}
        references = {
            path.relative_to(check_context_cost.ROOT).as_posix()
            for path in (check_context_cost.ROOT / "skills/python-craft/references").glob("*.md")
        }
        self.assertTrue(references)
        self.assertTrue(references <= measured, "Python reference omitted from context budgets")
        for task in ("Python automated refactor", "Python library migration"):
            self.assertNotIn("skills/backend-craft/SKILL.md", check_context_cost.TASK_FILES[task])

    def test_release_preparation_adds_context_to_the_same_code_task(self) -> None:
        code = set(check_context_cost.TASK_FILES.get("FastAPI upstream change", []))
        release = set(check_context_cost.TASK_FILES.get("Prepare FastAPI release", []))
        self.assertTrue(code, "missing implementation profile")
        self.assertEqual(release - code, {
            "skills/production-change-gate/SKILL.md",
            "skills/production-change-gate/references/release-readiness.md",
            "skills/production-change-gate/references/release-artifact-evidence.md",
        })
        self.assertTrue(code <= release)

    def test_framework_reference_growth_can_fail_its_task(self) -> None:
        task = "FastAPI upstream change"
        original = check_context_cost.task_bytes

        def inflated_reference(paths):
            return original(paths) + (
                100_000 if "skills/backend-craft/references/fastapi.md" in paths else 0
            )

        out = io.StringIO()
        with mock.patch.object(check_context_cost, "task_bytes", inflated_reference):
            with contextlib.redirect_stdout(out):
                code = check_context_cost.main([])
        self.assertEqual(1, code)
        self.assertIn(task, out.getvalue())


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
