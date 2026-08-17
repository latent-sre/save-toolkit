#!/usr/bin/env python3
"""Tests for Gate A's pooled step runner.

The runner replaced a serial loop, so the properties that must not regress are the ones a green
gate could otherwise hide: a failing step must appear in the failed list, EVERY step must run
even after one fails (the gate's documented no-bisect contract), and the report must print in
roster order regardless of completion order. All pinned against synthetic interpreter steps —
no test here runs the real gate inside itself.
"""
import contextlib
import sys
import io
import tempfile
import threading
import unittest
import unittest.mock
from pathlib import Path
from unittest import mock

import gate_a


def _step(label, code, marker_file=None):
    body = "import sys"
    if marker_file is not None:
        body += f"; open({str(marker_file)!r}, 'w').write('ran')"
    body += f"; print('step {label} output'); sys.exit({code})"
    return (label, ["-c", body], None)


class RunStepsTests(unittest.TestCase):
    def _run(self, steps):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            failed = gate_a.run_steps(steps)
        return failed, out.getvalue()

    def test_all_green_returns_no_failures_and_prints_in_roster_order(self) -> None:
        failed, out = self._run([_step("alpha", 0), _step("beta", 0), _step("gamma", 0)])
        self.assertEqual([], failed)
        self.assertLess(out.index("=== alpha ==="), out.index("=== beta ==="))
        self.assertLess(out.index("=== beta ==="), out.index("=== gamma ==="))
        self.assertIn("step alpha output", out)

    def test_failing_step_is_named_and_later_steps_still_run(self) -> None:
        # The no-bisect contract: one failure must not stop the roster. The marker file proves
        # the step after the failure genuinely executed, not merely appeared in the report.
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "later-step-ran"
            failed, out = self._run([
                _step("first", 0),
                _step("breaks", 3),
                _step("after-the-failure", 0, marker_file=marker),
            ])
            self.assertEqual(["breaks"], failed)
            self.assertEqual("ran", marker.read_text(encoding="utf-8"))
        self.assertIn("=== after-the-failure ===", out)

    def test_step_output_is_attributed_to_its_own_header(self) -> None:
        # Buffered concurrency must not interleave: each step's output appears after its own
        # header and before the next one, or a failure's traceback would be blamed on the
        # wrong step.
        failed, out = self._run([_step("one", 0), _step("two", 0)])
        self.assertEqual([], failed)
        section = out[out.index("=== one ==="):out.index("=== two ===")]
        self.assertIn("step one output", section)
        self.assertNotIn("step two output", section)

    def test_roster_order_stays_deterministic_when_later_step_finishes_first(self) -> None:
        slow_started = threading.Event()
        fast_started = threading.Event()
        fast_finished = threading.Event()

        def fake_run(argv, cwd, env, stdout, stderr, text):
            label = argv[-1]
            if label == "slow":
                slow_started.set()
                if not fast_started.wait(timeout=1):
                    raise AssertionError("run_steps stopped overlapping independent steps")
                if not fast_finished.wait(timeout=1):
                    raise AssertionError("later step did not finish first")
                return mock.Mock(returncode=0, stdout="slow output\n")
            if label == "fast":
                fast_started.set()
                fast_finished.set()
                return mock.Mock(returncode=0, stdout="fast output\n")
            raise AssertionError(f"unexpected step: {label!r}")

        steps = [
            ("slow", ["-c", "slow"], None),
            ("fast", ["-c", "fast"], None),
        ]
        with mock.patch.object(gate_a.subprocess, "run", side_effect=fake_run):
            failed, out = self._run(steps)

        self.assertEqual([], failed)
        self.assertLess(out.index("=== slow ==="), out.index("=== fast ==="))
        self.assertLess(out.index("slow output"), out.index("=== fast ==="))
        self.assertLess(out.index("=== fast ==="), out.index("fast output"))


class PreflightInterpreterFloorTests(unittest.TestCase):
    """The interpreter floor must be named by preflight, not discovered mid-run.

    Before this, preflight checked for a missing `yaml` and handed back the exact pinned install
    command, but never checked the Python version -- so running the gate on 3.11 got past preflight
    and died several steps later with a bare `TypeError: rmtree() got an unexpected keyword
    argument 'onexc'` from evals/clean_room.py. That is precisely the confusing failure preflight
    exists to prevent, for the one hard dependency it did not mention.
    """

    def test_an_old_interpreter_is_refused_by_name(self) -> None:
        stderr = io.StringIO()
        with unittest.mock.patch.object(gate_a.sys, "version_info", (3, 11, 15)):
            with contextlib.redirect_stderr(stderr):
                allowed = gate_a.preflight()
        message = stderr.getvalue()
        self.assertFalse(allowed)
        # The remedy has to be actionable, not just a refusal: name the floor, what is running, and
        # the Windows caveat that bare `python3` is a Store stub.
        self.assertIn("3.12", message)
        self.assertIn("3.11.15", message)
        self.assertIn("py -3", message)

    def test_the_running_interpreter_is_accepted(self) -> None:
        """Guards the obvious way to break the check: a floor nobody can satisfy."""
        self.assertGreaterEqual(sys.version_info[:2], gate_a.MINIMUM_PYTHON)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertTrue(gate_a.preflight())


if __name__ == "__main__":
    raise SystemExit(unittest.main())
