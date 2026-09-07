#!/usr/bin/env python3
"""Contract tests for the cross-platform fleet-validation workflow."""
from __future__ import annotations

import ast
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "validate.yml"


class ValidateWorkflowTests(unittest.TestCase):
    def test_linux_validate_job_runs_gate_a(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        validate_job, separator, _remainder = workflow.partition("\n  component-tests:")
        self.assertTrue(separator, "validate workflow has no component-tests job")
        self.assertIn("runs-on: ubuntu-latest", validate_job, "the Linux validate job lost its runner")
        self.assertIn(
            "run: python scripts/gate_a.py",
            validate_job,
            "the Linux validate job no longer invokes Gate A",
        )

    def test_linux_and_windows_are_the_only_gate_platforms(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("runs-on: ubuntu-latest", workflow)
        self.assertIn("windows-latest", workflow, "Windows must still run somewhere in the gate")
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

    @classmethod
    def _gate_path_scripts(cls) -> list[Path]:
        """Scripts Gate A runs, plus the modules they import from this repository."""
        gate = (ROOT / "scripts" / "gate_a.py").read_text(encoding="utf-8")
        named = {ROOT / name for name in re.findall(r'"(scripts/[a-z_]+\.py)"', gate)}
        pending = [ROOT / "scripts/gate_a.py", *named]
        visited: set[Path] = set()
        while pending:
            path = pending.pop()
            if path in visited or not path.is_file():
                continue
            visited.add(path)
            pending.extend(ROOT / "scripts" / f"{name}.py" for name in cls._imports(path))
        return sorted(visited)

    @staticmethod
    def _imports(path: Path) -> set[str]:
        found: set[str] = set()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module.split(".")[0]]
            found.update(names)
        return found

    @classmethod
    def _third_party_imports(cls, path: Path) -> set[str]:
        local = {module.stem for module in (ROOT / "scripts").glob("*.py")}
        return cls._imports(path) - sys.stdlib_module_names - local - {"scripts"}

    def test_dependency_install_in_another_job_does_not_satisfy_gate_a(self) -> None:
        workflow = (
            "jobs:\n"
            "  validate:\n"
            "    steps:\n"
            "      - run: python scripts/gate_a.py\n"
            "  component-tests:\n"
            "    steps:\n"
            "      - run: python -m pip install -r requirements-dev.txt\n"
        )
        for indirect in (False, True):
            with self.subTest(indirect=indirect), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / "scripts").mkdir()
                (root / "scripts/gate_a.py").write_text(
                    'STEPS = ["scripts/validate_fleet.py"]\n', encoding="utf-8",
                )
                (root / "scripts/validate_fleet.py").write_text(
                    "import fleet_frontmatter\n" if indirect else "import yaml\n", encoding="utf-8",
                )
                (root / "scripts/fleet_frontmatter.py").write_text("import yaml\n", encoding="utf-8")
                workflow_path = root / "validate.yml"
                workflow_path.write_text(workflow, encoding="utf-8")
                with mock.patch.multiple(sys.modules[__name__], ROOT=root, WORKFLOW=workflow_path):
                    with self.assertRaisesRegex(AssertionError, "gate-path scripts import"):
                        self.test_live_tree_satisfies_the_dependency_contract()
                    workflow_path.write_text(
                        workflow.replace(
                            "      - run: python scripts/gate_a.py",
                            "      - run: python -m pip install -r requirements-dev.txt\n"
                            "      - run: python scripts/gate_a.py",
                        ),
                        encoding="utf-8",
                    )
                    self.test_live_tree_satisfies_the_dependency_contract()

    def test_live_tree_satisfies_the_dependency_contract(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        steps = yaml.safe_load(workflow)["jobs"]["validate"]["steps"]
        gate_index = next(
            index for index, step in enumerate(steps)
            if "python scripts/gate_a.py" in step.get("run", "").splitlines()
        )
        ci_installs = any(
            "python -m pip install -r requirements-dev.txt" in step.get("run", "").splitlines()
            and "if" not in step
            for step in steps[:gate_index]
        )
        offenders = {
            path.relative_to(ROOT).as_posix(): sorted(self._third_party_imports(path))
            for path in self._gate_path_scripts()
            if self._third_party_imports(path)
        }
        self.assertFalse(
            offenders and not ci_installs,
            f"gate-path scripts import {offenders} but the validate job installs no "
            "dependencies before Gate A; add `python -m pip install -r requirements-dev.txt` "
            "to that job (and update gate_a.py's docstring) in the same change",
        )

    def test_readonly_guard_is_standard_library_only(self) -> None:
        """The guard is exempt from the dependency allowance, permanently.

        The session hook runs it as `python -I -S`: no user environment, no `site`. An installed
        plugin never pip-installs anything, so a third-party import raises before the guard can
        return 42/43, the launcher falls through to its blanket deny, and every guarded Bash
        command dies. CI installing the package would not help -- CI is not where the guard runs.
        """
        guard = ROOT / "scripts" / "readonly-guard.py"
        self.assertEqual(set(), self._third_party_imports(guard))
        hook = (ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8")
        self.assertIn("-I -S", hook, "the guard's isolated invocation is what makes this binding")

    def test_component_tests_run_on_windows_as_well_as_linux(self) -> None:
        """Windows coverage lives where it can actually catch something: the tests.

        The retired `validate-windows` job ran `gate_a.py` only, which runs no `test_*.py` at all.
        The one Windows-only defect this repository has had -- 8.3 short paths defeating the
        link-containment check, fixed at `scripts/check_links.py` by resolving the root -- was
        caught by test fixtures under an OS matrix, not by the structural gate. A Windows job that
        runs no tests could not have caught it.
        """
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn(
            "\n  validate-windows:",
            workflow,
            "the test-less Windows gate is retired; Windows coverage belongs on component-tests",
        )
        job = workflow.partition("\n  component-tests:")[2].partition("\n  claude-plugin-contract:")[0]
        self.assertTrue(job, "validate workflow has no component-tests job")
        self.assertIn("windows-latest", job, "component tests must run on Windows")
        self.assertIn("ubuntu-latest", job, "component tests must still run on Linux")
        self.assertIn("matrix:", job, "the two operating systems are one matrix, not two jobs")
        self.assertIn("${{ matrix.os }}", job)
        self.assertIn(
            "run: python -m pytest -q", job,
            "invoke `python`, never the Store-stub `python3`, so Windows resolves the real interpreter",
        )
        self.assertIn(
            "run: python -m pip install -r requirements-test.txt", job,
            "PyYAML is required on both runners or layered grader checks silently SKIP",
        )

    def test_the_gate_still_has_a_schedule_and_manual_dispatch(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        triggers = workflow.partition("\npermissions:")[0]
        self.assertRegex(triggers, re.compile(r"^  schedule:\n    - cron: ", re.MULTILINE))
        self.assertIn("workflow_dispatch:", triggers)


if __name__ == "__main__":
    unittest.main(verbosity=2)
