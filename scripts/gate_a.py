#!/usr/bin/env python3
"""Run the live-tree structural checks used by CI and before a push.

This is the executable roster; CONTRIBUTING.md defines when component suites must also run.
No gate-path script imports a third-party package, so the gate runs on a bare interpreter and
the validate job installs nothing. The first such import must add
`python -m pip install -r requirements-dev.txt` to that job in the same change;
test_validate_workflow.py fails until it does. Checks need neither a clean tree nor full Git
history.
All checks run even after a failure. Default output is one verdict plus failure diagnostics;
--verbose includes successful step output. Structural success is not behavioral acceptance.
"""

# Postponed annotations keep this module importable on interpreters below the floor, so
# preflight() can name the floor instead of the interpreter failing on an annotation.
from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

STEPS = [
    ("Canonical skill and bundle links", ["scripts/check_links.py"]),
    ("Fleet, plugin, and generated adapter contracts", ["scripts/validate_fleet.py"]),
]

MINIMUM_PYTHON = (3, 11)


def preflight() -> bool:
    """Name the interpreter floor before a sub-step fails with a misleading import error."""
    if sys.version_info >= MINIMUM_PYTHON:
        return True

    required = ".".join(str(part) for part in MINIMUM_PYTHON)
    running = ".".join(str(part) for part in sys.version_info[:3])
    print(
        f"Gate A: FAIL -- this repository requires Python {required} or newer; you are on {running}.\n"
        f"  Re-run with a {required}+ interpreter. On Windows use `python` or `py -3`, never bare\n"
        "  `python3` (the Microsoft Store stub).",
        file=sys.stderr,
    )
    return False


def run_steps(steps: Sequence[tuple[str, list[str]]], *, verbose: bool = False) -> list[str]:
    """Run every step and return failed labels in roster order."""
    failed: list[str] = []
    for label, argv in steps:
        proc = subprocess.run(
            [sys.executable, *argv],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if verbose or proc.returncode != 0:
            print(f"\n=== {label} ===", flush=True)
            sys.stdout.write(proc.stdout)
            sys.stdout.flush()
        if proc.returncode != 0:
            failed.append(label)
    return failed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="print every step's output; failures are always printed",
    )
    args = parser.parse_args(argv)

    if not preflight():
        return 1

    failed = run_steps(STEPS, verbose=args.verbose)
    if failed:
        print("\n" + "-" * 60)
        print(f"Gate A: FAIL -- {len(failed)} of {len(STEPS)} step(s) failed:")
        for label in failed:
            print(f"  - {label}")
        print(
            "\nGate A is structural only. Passing it would still not clear the "
            "verification table in CONTRIBUTING.md."
        )
        return 1

    print(
        f"Gate A: PASS -- {len(STEPS)}/{len(STEPS)} structural steps green "
        "(well-formed only; correctness review remains separate)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
