#!/usr/bin/env python3
"""Run every component test entrypoint and fail on any non-quarantined failure.

Cost, measured 2026-08-26 on the live tree: 26 active tests in ~28 s wall, sequentially. Two files
dominate -- `evals/test_run_evals.py` (~15 s) and `scripts/test_readonly_guard.py` (~8 s) -- so
parallelism would buy little and would make a failure harder to attribute. It needs PyYAML from
`requirements-dev.txt` for the layer-2 half of `evals/test_graders.py`; the layer-1 half degrades
without it, which is why running these tests without the dependency is worse than not running them:
it reports green over a suite that silently skipped its scenario checks.

Gate A is deliberately structural: `scripts/gate_a.py` audits the live tree and explicitly does not
run `test_*.py`, on the reasoning that component tests belong with the implementation that changed
them. That reasoning holds for *authoring*, but it left CI running no test file at all -- and three
test files were failing on `main` with nobody notified. A gate that never runs is the silent-failure
mode this repository already documented once, in the comment at the top of `.github/workflows/`.

This runner is that gate for component tests. It is deliberately separate from Gate A so the
structural audit stays standard-library-only and fast, and so a red test cannot be confused with a
red structural check.

Each test file keeps its bare `python scripts/test_x.py` entrypoint (a hard rule in AGENTS.md);
this only discovers and sequences them.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEST_PATTERNS = ("scripts/test_*.py", "evals/test_*.py")

# Empty, and that is the point: the three tests this runner found failing on `main` on 2026-08-26
# were fixed rather than tolerated (CI-001). Keep the mechanism -- a future red test may need a
# recorded, reasoned quarantine while it is repaired -- but never as a way to make CI green. An
# entry without a reason is indistinguishable from one nobody looked at.
QUARANTINE: dict[str, str] = {}


def discover() -> list[Path]:
    found: list[Path] = []
    for pattern in TEST_PATTERNS:
        found.extend(sorted(ROOT.glob(pattern)))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-quarantined",
        action="store_true",
        help="run the quarantined tests too and report them, without failing the run",
    )
    parser.add_argument("--list", action="store_true", help="list what would run, then exit")
    parser.add_argument(
        "--match",
        default="",
        help="substring filter on the test path, for a fast local subset",
    )
    args = parser.parse_args()

    discovered = discover()
    if not discovered:
        print("run_component_tests: FAIL -- discovered no test files", file=sys.stderr)
        return 1

    # Validate the quarantine against everything on disk, never against a --match subset, or a
    # filter would report every unmatched entry as stale.
    stale = sorted(set(QUARANTINE) - {t.relative_to(ROOT).as_posix() for t in discovered})
    if stale:
        print(f"run_component_tests: FAIL -- quarantine names tests that do not exist: {stale}")
        return 1

    tests = discovered
    if args.match:
        tests = [t for t in tests if args.match in t.relative_to(ROOT).as_posix()]
        if not tests:
            print(f"run_component_tests: FAIL -- --match {args.match!r} selected nothing")
            return 1

    if args.list:
        for test in tests:
            rel = test.relative_to(ROOT).as_posix()
            print(f"{'quarantined' if rel in QUARANTINE else 'active':>12}  {rel}")
        return 0

    failures: list[str] = []
    quarantined_now_passing: list[str] = []
    started = time.monotonic()

    for test in tests:
        rel = test.relative_to(ROOT).as_posix()
        is_quarantined = rel in QUARANTINE
        if is_quarantined and not args.include_quarantined:
            print(f"  QUAR  {rel}  ({QUARANTINE[rel]})")
            continue
        t0 = time.monotonic()
        child_env = dict(os.environ, COMPONENT_TEST_CHILD="1")
        completed = subprocess.run(
            [sys.executable, str(test)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=child_env,
        )
        elapsed = time.monotonic() - t0
        ok = completed.returncode == 0
        if is_quarantined:
            print(f"  {'QPASS' if ok else 'QFAIL'}  {rel}  {elapsed:5.1f}s")
            if ok:
                quarantined_now_passing.append(rel)
            continue
        print(f"  {'ok   ' if ok else 'FAIL '}  {rel}  {elapsed:5.1f}s")
        if not ok:
            failures.append(rel)
            sys.stdout.write(completed.stdout[-2000:])
            sys.stderr.write(completed.stderr[-2000:])

    wall = time.monotonic() - started
    selected_quarantined = sum(
        1 for t in tests if t.relative_to(ROOT).as_posix() in QUARANTINE
    )
    active = len(tests) - (0 if args.include_quarantined else selected_quarantined)
    print(
        f"run_component_tests: {active - len(failures)}/{active} passed, "
        f"{selected_quarantined} quarantined, {wall:.0f}s"
    )
    if quarantined_now_passing:
        print(
            "run_component_tests: quarantined tests now PASS and should be removed from "
            f"QUARANTINE: {quarantined_now_passing}"
        )
    if failures:
        print(f"run_component_tests: FAIL -- {failures}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
