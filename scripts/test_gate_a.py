#!/usr/bin/env python3
"""Tests for Gate A's pooled step runner.

The runner replaced a serial loop, so the properties that must not regress are the ones a green
gate could otherwise hide: a failing step must appear in the failed list, EVERY step must run
even after one fails (the gate's documented no-bisect contract), and the report must print in
roster order regardless of completion order. All pinned against synthetic interpreter steps —
no test here runs the real gate inside itself.
"""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    raise SystemExit(unittest.main())
