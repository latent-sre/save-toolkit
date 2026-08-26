#!/usr/bin/env python3
"""Prove the component-test runner fails for the reasons it claims to.

A guard written to prevent a recurrence has to assert the failing property, not the structural
arrangement that happens to accompany it -- a lesson paid for in PR #170, where a guard checked
pairing, counts, mode, and target and still let the defect it was written for ship a second time.
So these tests make the runner actually go red rather than checking that it looks like it would.

Every case uses `--match` against a tiny subset: the runner takes ~28 s over the full tree, and a
self-test that costs a minute is a self-test people disable.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_component_tests.py"

# The runner discovers this file and runs it, so without this marker the process tree recurses
# forever. The runner sets it for every child it spawns.
IS_CHILD = os.environ.get("COMPONENT_TEST_CHILD") == "1"


def _run(*args: str, script: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script or RUNNER), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def _load_runner():
    spec = importlib.util.spec_from_file_location("_runner", RUNNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RunnerTests(unittest.TestCase):
    @unittest.skipIf(IS_CHILD, "would recurse: the runner is what spawned this process")
    def test_a_failing_test_turns_the_runner_red(self) -> None:
        """The property that matters: a newly failing test fails the run, never tolerated."""
        planted = ROOT / "scripts" / "test_zzplanted_failure.py"
        planted.write_text(
            textwrap.dedent(
                """
                import unittest


                class Planted(unittest.TestCase):
                    def test_fails(self) -> None:
                        self.fail("planted")


                if __name__ == "__main__":
                    unittest.main()
                """
            ).lstrip(),
            encoding="utf-8",
        )
        try:
            result = _run("--match", "zzplanted")
            self.assertEqual(result.returncode, 1, "a failing test must fail the runner")
            self.assertIn("test_zzplanted_failure.py", result.stdout)
        finally:
            planted.unlink()

    @unittest.skipIf(IS_CHILD, "would recurse: the runner is what spawned this process")
    def test_a_passing_subset_is_green(self) -> None:
        result = _run("--match", "test_canary_tokens")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("1/1 passed", result.stdout)

    @unittest.skipIf(IS_CHILD, "would recurse: the runner is what spawned this process")
    def test_a_quarantined_test_does_not_fail_the_run(self) -> None:
        module = _load_runner()
        name = next(iter(module.QUARANTINE))
        result = _run("--match", Path(name).stem)
        self.assertEqual(result.returncode, 0, "a quarantined failure must not fail the run")
        self.assertIn("QUAR", result.stdout)

    @unittest.skipIf(IS_CHILD, "would recurse: the runner is what spawned this process")
    def test_a_stale_quarantine_entry_fails(self) -> None:
        """A quarantine naming a deleted test silently re-arms the gap it made visible."""
        patched = RUNNER.read_text(encoding="utf-8").replace(
            "QUARANTINE: dict[str, str] = {",
            'QUARANTINE: dict[str, str] = {\n    "scripts/test_deleted_long_ago.py": '
            '"a stale entry that names nothing on disk",',
            1,
        ).replace("<= 3", "<= 4", 1)
        scratch = ROOT / "scripts" / "runner_stale_fixture.py"
        scratch.write_text(patched, encoding="utf-8")
        try:
            result = _run("--match", "test_canary_tokens", script=scratch)
            self.assertEqual(result.returncode, 1)
            self.assertIn("do not exist", result.stdout)
        finally:
            scratch.unlink()

    def test_every_quarantined_test_exists_and_names_what_is_broken(self) -> None:
        module = _load_runner()
        self.assertTrue(module.QUARANTINE, "an empty quarantine needs no ratchet")
        for name, reason in module.QUARANTINE.items():
            self.assertTrue((ROOT / name).exists(), f"{name} is quarantined but absent")
            self.assertGreater(
                len(reason), 30, f"{name}: a quarantine reason must say what is broken"
            )

    def test_discovery_covers_both_test_roots(self) -> None:
        module = _load_runner()
        found = {p.relative_to(ROOT).as_posix() for p in module.discover()}
        self.assertTrue(any(n.startswith("scripts/") for n in found))
        self.assertTrue(any(n.startswith("evals/") for n in found))
        self.assertIn("scripts/test_run_component_tests.py", found, "the runner tests itself")


if __name__ == "__main__":
    unittest.main()
