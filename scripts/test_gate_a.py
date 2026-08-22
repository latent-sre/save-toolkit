#!/usr/bin/env python3
"""Tests for Gate A's pooled step runner.

The runner replaced a serial loop, so the properties that must not regress are the ones a green
gate could otherwise hide: a failing step must appear in the failed list, EVERY step must run
even after one fails (the gate's documented no-bisect contract), successful output is quiet by
default, failed output remains attributed, and verbose output prints in roster order regardless of
completion order. All pinned against synthetic interpreter steps — no test here runs the real gate
inside itself.
"""
import ast
import contextlib
import os
import subprocess
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
    def _run(self, steps, *, verbose=False):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            if verbose:
                failed = gate_a.run_steps(steps, verbose=True)
            else:
                failed = gate_a.run_steps(steps)
        return failed, out.getvalue()

    def test_all_green_returns_no_failures_and_is_quiet_by_default(self) -> None:
        failed, out = self._run([_step("alpha", 0), _step("beta", 0), _step("gamma", 0)])
        self.assertEqual([], failed)
        self.assertEqual("", out)

    def test_successful_skips_keep_one_compact_qualification(self) -> None:
        step = (
            "platform adapters",
            ["-c", "print('Ran 38 tests'); print('OK (skipped=2)')"],
            None,
        )

        failed, out = self._run([step])

        self.assertEqual([], failed)
        self.assertEqual(
            "Gate A: QUALIFIED -- platform adapters: 2 tests skipped\n",
            out,
        )

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
        self.assertIn("=== breaks ===", out)
        self.assertIn("step breaks output", out)
        self.assertNotIn("step first output", out)
        self.assertNotIn("step after-the-failure output", out)

    def test_verbose_step_output_is_attributed_to_its_own_header(self) -> None:
        # Buffered concurrency must not interleave: each step's output appears after its own
        # header and before the next one, or a failure's traceback would be blamed on the
        # wrong step.
        failed, out = self._run([_step("one", 0), _step("two", 0)], verbose=True)
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
            failed, out = self._run(steps, verbose=True)

        self.assertEqual([], failed)
        self.assertLess(out.index("=== slow ==="), out.index("=== fast ==="))
        self.assertLess(out.index("slow output"), out.index("=== fast ==="))
        self.assertLess(out.index("=== fast ==="), out.index("fast output"))


class UnreachableTestClassTests(unittest.TestCase):
    """No test file may define a TestCase after its `unittest.main()` entrypoint.

    Gate A executes each `test_*.py` as a script, so `unittest.main()` runs at the point it appears
    and the interpreter never reaches anything below it. A class defined after that block is dead:
    it is collected by `python -m unittest` but NOT by the gate, so the gate reports OK over a
    smaller suite than the file appears to contain, and says nothing about the difference.

    This shipped. Fourteen contract tests were appended below the entrypoint in three files and
    silently did not run -- `test_check_links.py` reported 21 tests directly and 28 under
    discovery, and two of the missing ones were erroring on an undefined name. That is exactly the
    proves-nothing failure mode this repository's own tooling exists to catch, so it gets a
    structural check rather than a resolution to be careful.

    Detection is AST-based, not textual: every `if __name__ == "__main__":` in this repo's test
    corpus is matched textually by fixtures that embed that same line inside a string literal, and
    a grep-based version of this check reported the wrong line for four files.
    """

    @staticmethod
    def _entrypoint_line(tree: ast.Module) -> int | None:
        for node in tree.body:
            if not isinstance(node, ast.If):
                continue
            test = node.test
            if (
                isinstance(test, ast.Compare)
                and isinstance(test.left, ast.Name)
                and test.left.id == "__name__"
            ):
                return node.lineno
        return None

    def test_no_test_class_is_defined_below_the_entrypoint(self) -> None:
        offenders: list[str] = []
        checked = 0
        for pattern in ("scripts/test_*.py", "evals/test_*.py"):
            for path in sorted(Path(gate_a.ROOT).glob(pattern)):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                entrypoint = self._entrypoint_line(tree)
                if entrypoint is None:
                    continue
                checked += 1
                for node in tree.body:
                    if isinstance(node, ast.ClassDef) and node.lineno > entrypoint:
                        offenders.append(f"{path.name}:{node.lineno} class {node.name}")
        # Without this the loop could silently match no files and the assertion below would be
        # vacuous -- the precise bug class this test exists for.
        self.assertGreater(checked, 20, "test corpus not found; this check would prove nothing")
        self.assertEqual([], offenders, "unreachable when run as a script (Gate A runs it that way)")


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


class GateLockTests(unittest.TestCase):
    """Two Gate A runs on one machine must not overlap.

    Measured 2026-08-21: subprocess-heavy suites pass alone and false-red, while finishing in a
    third of their normal time, whenever a second Python process is running the same file. The usual
    way that happens is `gate_a.py | head`, which on Windows leaves the whole gate running orphaned
    after `head` exits. A false red costs far more than the gate, so the gate refuses to start while
    another run holds the machine-wide lock, and the OS drops the lock when its holder dies.

    Stale-lock reclamation is now ownership-preserving: the lock is an OS advisory lock
    (``fcntl.flock`` on POSIX, ``msvcrt.locking`` on Windows) so the OS releases it when the
    holder dies — no file-content race between a reclaimer and a just-acquired lock.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.lock = Path(self._tmp.name) / "gate_a.lock"
        patcher = mock.patch.object(gate_a, "LOCK_PATH", self.lock)
        patcher.start()
        self.addCleanup(patcher.stop)
        # Preflight is proven elsewhere; here it must not decide the outcome.
        pre = mock.patch.object(gate_a, "preflight", return_value=True)
        pre.start()
        self.addCleanup(pre.stop)

    def _main(self, run_steps, argv=None):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(gate_a, "run_steps", side_effect=run_steps):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = gate_a.main([] if argv is None else argv)
        return code, out.getvalue(), err.getvalue()

    def _child_script_that_holds_lock(self):
        """A script that takes the OS lock on self.lock exactly the way gate_a does, prints
        'ready', and holds it until stdin delivers a line -- a live concurrent gate in miniature.
        """
        return (
            "import os, sys\n"
            f"sys.path.insert(0, {str(Path(gate_a.__file__).parent)!r})\n"
            "import gate_a\n"
            f"fd = os.open({str(self.lock)!r}, os.O_CREAT | os.O_RDWR)\n"
            "assert gate_a._os_lock_nonblocking(fd), 'child could not take the lock'\n"
            "os.ftruncate(fd, 0); os.lseek(fd, 0, os.SEEK_SET)\n"
            "os.write(fd, (str(os.getpid()) + '\\n/child\\n').encode())\n"
            "sys.stdout.write('ready\\n'); sys.stdout.flush()\n"
            "sys.stdin.readline()\n"
            "gate_a._os_unlock(fd); os.close(fd)\n"
        )

    def _assert_released(self) -> None:
        """Released means re-acquirable. The file itself stays: deleting a lock file is a race."""
        with gate_a.gate_lock(self.lock):
            pass

    def test_refuses_while_a_live_gate_holds_the_lock(self) -> None:
        # A subprocess holds the OS advisory lock; this process must get GateBusy.
        child = subprocess.Popen(
            [sys.executable, "-c", self._child_script_that_holds_lock()],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
        )
        try:
            line = child.stdout.readline()
            self.assertEqual("ready\n", line, "child subprocess did not acquire the lock")

            def must_not_run(steps):
                raise AssertionError("run_steps executed under a held lock")

            code, _out, err = self._main(must_not_run)
            self.assertNotEqual(0, code)
            self.assertIn(str(child.pid), err)
            self.assertIn(str(self.lock), err)
            self.assertIn("overlap", err.lower())
            # The child's lock file is left untouched (we must not unlink a held lock).
            self.assertTrue(self.lock.exists())
        finally:
            child.stdin.write("\n")
            child.stdin.flush()
            child.wait(timeout=5)

    def test_stale_lock_from_a_dead_holder_is_reclaimed(self) -> None:
        # Write a stale lock file (dead process, no OS lock held).  The new run must succeed.
        self.lock.write_text("999999\n/gone\n", encoding="utf-8")
        ran = []
        code, _out, _err = self._main(lambda steps: ran.append(True) or [])
        self.assertEqual(0, code)
        self.assertEqual([True], ran)
        self._assert_released()

    def test_concurrent_acquisition_is_refused(self) -> None:
        # Directly exercise gate_lock in a cross-process scenario: a subprocess holds the OS
        # advisory lock while this process tries to acquire the same lock; GateBusy must be raised.
        child = subprocess.Popen(
            [sys.executable, "-c", self._child_script_that_holds_lock()],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
        )
        try:
            line = child.stdout.readline()
            self.assertEqual("ready\n", line, "child subprocess did not acquire the lock")
            with self.assertRaises(gate_a.GateBusy) as cm:
                with gate_a.gate_lock():
                    pass
            self.assertEqual(str(child.pid), str(cm.exception.holder_pid))
        finally:
            child.stdin.write("\n")
            child.stdin.flush()
            child.wait(timeout=5)

    def test_lock_names_this_run_and_is_released_after_success(self) -> None:
        seen = {}

        def record(steps):
            seen["holder"] = self.lock.read_text(encoding="utf-8")
            return []

        code, _out, _err = self._main(record)
        self.assertEqual(0, code)
        self.assertTrue(seen["holder"].startswith(f"{os.getpid()}\n"))
        self._assert_released()

    def test_verbose_flag_is_forwarded_to_the_step_runner(self) -> None:
        seen = []

        def record(steps, *, verbose=False):
            seen.append(verbose)
            return []

        code, _out, _err = self._main(record, ["--verbose"])
        self.assertEqual(0, code)
        self.assertEqual([True], seen)

    def test_success_main_prints_one_concise_verdict(self) -> None:
        code, out, err = self._main(lambda steps: [])

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

    def test_lock_is_released_when_the_run_raises(self) -> None:
        def explode(steps):
            raise RuntimeError("step runner died")

        with mock.patch.object(gate_a, "preflight", return_value=True):
            with self.assertRaises(RuntimeError):
                with contextlib.redirect_stdout(io.StringIO()):
                    with mock.patch.object(gate_a, "run_steps", side_effect=explode):
                        gate_a.main([])
        self._assert_released()

    def test_unreadable_lock_is_treated_as_stale(self) -> None:
        # A crash can leave an empty or garbage file; that must not wedge every future gate.
        self.lock.write_text("", encoding="utf-8")
        code, _out, _err = self._main(lambda steps: [])
        self.assertEqual(0, code)
        self._assert_released()


if __name__ == "__main__":
    raise SystemExit(unittest.main())
