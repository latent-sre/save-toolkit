#!/usr/bin/env python3
"""Contract tests for the cross-platform fleet-validation workflow."""
from __future__ import annotations

import ast
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "validate.yml"


class ValidateWorkflowTests(unittest.TestCase):
    def test_linux_validate_job_runs_gate_a(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        linux_job, separator, _remainder = workflow.partition("\n  validate-windows:")
        self.assertTrue(separator, "validate workflow has no dedicated validate-windows job")
        self.assertIn("runs-on: ubuntu-latest", linux_job, "the Linux validate job lost its runner")
        self.assertIn(
            "run: python scripts/gate_a.py",
            linux_job,
            "the Linux validate job no longer invokes Gate A",
        )

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

    # --- the dependency contract (ADR 2026-08-23-allow-third-party-dependencies) ---------------
    #
    # Third-party imports are allowed on the Gate A path, but only if CI installs them. Asserting
    # "CI does not install deps" is wrong now, and asserting nothing is worse: the previous version
    # of this test kept its name and checked only that a YAML partition existed, so a gate-path
    # import landing without the install step would have stayed green here and failed both CI jobs
    # with ImportError. The contract is conditional, so it is tested conditionally -- and exercised
    # in BOTH directions below, since the live tree currently satisfies it vacuously.

    @staticmethod
    def _gate_path_scripts() -> list[Path]:
        """Scripts Gate A runs, plus the modules they import from this repository."""
        gate = (ROOT / "scripts" / "gate_a.py").read_text(encoding="utf-8")
        named = {ROOT / name for name in re.findall(r'"(scripts/[a-z_]+\.py)"', gate)}
        named |= {
            ROOT / "scripts" / name
            for name in ("gate_a.py", "validate_fleet.py", "generate_platform_adapters.py")
        }
        return sorted(path for path in named if path.is_file())

    @staticmethod
    def _third_party_imports(path: Path) -> set[str]:
        local = {module.stem for module in (ROOT / "scripts").glob("*.py")}
        found: set[str] = set()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module.split(".")[0]]
            for name in names:
                if name not in sys.stdlib_module_names and name not in local and name != "scripts":
                    found.add(name)
        return found

    @staticmethod
    def _contract_violation(*, imports_third_party: bool, ci_installs: bool) -> bool:
        """The whole rule: importing without installing is the only failing combination."""
        return imports_third_party and not ci_installs

    def test_dependency_contract_rejects_import_without_install(self) -> None:
        """The case the old test could not see -- exercised directly, not hypothetically."""
        self.assertTrue(
            self._contract_violation(imports_third_party=True, ci_installs=False),
            "a gate-path third-party import with no CI install step must be a violation",
        )
        for imports_third_party, ci_installs in ((True, True), (False, False), (False, True)):
            with self.subTest(imports=imports_third_party, installs=ci_installs):
                self.assertFalse(
                    self._contract_violation(
                        imports_third_party=imports_third_party, ci_installs=ci_installs
                    )
                )

    def test_live_tree_satisfies_the_dependency_contract(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        ci_installs = "requirements-dev.txt" in workflow
        offenders = {
            path.relative_to(ROOT).as_posix(): sorted(self._third_party_imports(path))
            for path in self._gate_path_scripts()
            if self._third_party_imports(path)
        }
        self.assertFalse(
            self._contract_violation(
                imports_third_party=bool(offenders), ci_installs=ci_installs
            ),
            f"gate-path scripts import {offenders} but the validate workflow installs no "
            "dependencies; add `pip install -r requirements-dev.txt` to BOTH validate jobs "
            "(and update gate_a.py's docstring) in the same change",
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
