#!/usr/bin/env python3
"""Focused tests for Gate A's structural scope, runner, preflight, and output contract."""

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import gate_a


def _step(label, code, marker_file=None):
    body = "import sys"
    if marker_file is not None:
        body += f"; open({str(marker_file)!r}, 'w').write('ran')"
    body += f"; print('step {label} output'); sys.exit({code})"
    return (label, ["-c", body], None)


class StructuralScopeTests(unittest.TestCase):
    def test_gate_runs_live_tree_validators_not_component_test_suites(self) -> None:
        """The push-boundary gate must not silently re-expand into the whole test corpus."""
        self.assertEqual(gate_a.STRUCTURAL_STEPS, gate_a.STEPS)
        commands = [argv[0] for _label, argv, _env in gate_a.STEPS]
        self.assertFalse(
            any(Path(command).name.startswith("test_") for command in commands),
            "component tests belong to the changed implementation, not every push",
        )
        self.assertNotIn(
            "evals/build_probe.py",
            commands,
            "behavioral evals are focused implementation work, never a push-boundary step",
        )

    def test_context_cost_gate_is_the_third_structural_step(self) -> None:
        commands = [argv[0] for _label, argv, _env in gate_a.STEPS]
        self.assertEqual(4, len(gate_a.STEPS))
        self.assertEqual("scripts/check_context_cost.py", commands[2])

    def test_weight_totals_gate_is_the_fourth_structural_step(self) -> None:
        commands = [argv[0] for _label, argv, _env in gate_a.STEPS]
        self.assertEqual("scripts/check_weight.py", commands[3])


class RunStepsTests(unittest.TestCase):

    def _run(self, steps, *, verbose=False):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            failed = gate_a.run_steps(steps, verbose=verbose)
        return failed, out.getvalue()

    def test_all_green_returns_no_failures_and_is_quiet_by_default(self) -> None:
        failed, out = self._run([_step("alpha", 0), _step("beta", 0)])
        self.assertEqual([], failed)
        self.assertEqual("", out)

    def test_failing_step_is_named_and_later_steps_still_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "later-step-ran"
            failed, out = self._run(
                [
                    _step("first", 0),
                    _step("breaks", 3),
                    _step("after-the-failure", 0, marker_file=marker),
                ]
            )
            self.assertEqual(["breaks"], failed)
            self.assertEqual("ran", marker.read_text(encoding="utf-8"))
        self.assertIn("=== breaks ===", out)
        self.assertIn("step breaks output", out)
        self.assertNotIn("step first output", out)
        self.assertNotIn("step after-the-failure output", out)

    def test_verbose_output_stays_in_roster_order(self) -> None:
        failed, out = self._run([_step("one", 0), _step("two", 0)], verbose=True)
        self.assertEqual([], failed)
        self.assertLess(out.index("=== one ==="), out.index("step one output"))
        self.assertLess(out.index("step one output"), out.index("=== two ==="))
        self.assertLess(out.index("=== two ==="), out.index("step two output"))


class PreflightInterpreterFloorTests(unittest.TestCase):
    def test_an_old_interpreter_is_refused_by_name(self) -> None:
        stderr = io.StringIO()
        with mock.patch.object(gate_a.sys, "version_info", (3, 10, 15)):
            with contextlib.redirect_stderr(stderr):
                allowed = gate_a.preflight()
        message = stderr.getvalue()
        self.assertFalse(allowed)
        self.assertIn("3.11", message)
        self.assertIn("3.10.15", message)
        self.assertIn("py -3", message)

    def test_the_running_interpreter_is_accepted(self) -> None:
        self.assertGreaterEqual(sys.version_info[:2], gate_a.MINIMUM_PYTHON)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertTrue(gate_a.preflight())

    def test_structural_gate_does_not_require_the_eval_yaml_dependency(self) -> None:
        with mock.patch.dict(sys.modules, {"yaml": None}):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertTrue(gate_a.preflight())


class MainTests(unittest.TestCase):
    def _main(self, run_steps, argv=None):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(gate_a, "preflight", return_value=True):
            with mock.patch.object(gate_a, "run_steps", side_effect=run_steps):
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    code = gate_a.main([] if argv is None else argv)
        return code, out.getvalue(), err.getvalue()

    def test_verbose_flag_is_forwarded_to_the_step_runner(self) -> None:
        seen = []

        def record(steps, *, verbose=False):
            seen.append(verbose)
            return []

        code, _out, _err = self._main(record, ["--verbose"])
        self.assertEqual(0, code)
        self.assertEqual([True], seen)

    def test_success_main_prints_one_concise_verdict(self) -> None:
        code, out, err = self._main(lambda steps, *, verbose=False: [])
        self.assertEqual(0, code)
        self.assertEqual("", err)
        self.assertEqual(
            [
                "Gate A: PASS -- %d/%d structural steps green "
                "(well-formed only; correctness review remains separate)."
                % (len(gate_a.STEPS), len(gate_a.STEPS))
            ],
            out.strip().splitlines(),
        )

    def test_failure_main_reports_each_failed_step(self) -> None:
        code, out, err = self._main(
            lambda steps, *, verbose=False: ["broken links", "stale adapter"]
        )
        self.assertEqual(1, code)
        self.assertEqual("", err)
        self.assertIn("2 of %d step(s) failed" % len(gate_a.STEPS), out)
        self.assertIn("- broken links", out)
        self.assertIn("- stale adapter", out)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
