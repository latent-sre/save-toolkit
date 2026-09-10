#!/usr/bin/env python3
"""Run the live-tree structural checks used by CI and before a push.

This is the executable roster; CONTRIBUTING.md defines when component suites must also run.
Checks use the standard library and need neither a clean tree nor full Git history. If a check
adds a third-party dependency, CI must install it in the validate job before invoking this gate.
All checks run even after a failure. Default output is one verdict plus failure diagnostics;
--verbose includes successful step output. Structural success is not behavioral acceptance.
"""

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

STEPS = [
    ("Canonical skill and bundle links", ["scripts/check_links.py"]),
    ("Fleet, plugin, and generated adapter contracts", ["scripts/validate_fleet.py"]),
    ("Context-cost budgets for canonical tasks", ["scripts/check_context_cost.py"]),
    ("Weight totals: evals lines, skills bytes, agents bytes", ["scripts/check_weight.py"]),
]

MINIMUM_PYTHON = (3, 11)


def preflight() -> bool:
    """Name the interpreter floor before a sub-step fails with a misleading import error."""
    if sys.version_info >= MINIMUM_PYTHON:
        return True

    required = ".".join(str(part) for part in MINIMUM_PYTHON)
    running = ".".join(str(part) for part in sys.version_info[:3])
    print(
        "Gate A: FAIL -- this repository requires Python %s or newer; you are on %s.\n"
        "  Re-run with a %s+ interpreter. On Windows use `python` or `py -3`, never bare\n"
        "  `python3` (the Microsoft Store stub)." % (required, running, required),
        file=sys.stderr,
    )
    return False


def run_steps(steps, *, verbose: bool = False) -> list[str]:
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
            print("\n=== %s ===" % label, flush=True)
            sys.stdout.write(proc.stdout)
            sys.stdout.flush()
        if proc.returncode != 0:
            failed.append(label)
    return failed


def main(argv=None) -> int:
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
        print("Gate A: FAIL -- %d of %d step(s) failed:" % (len(failed), len(STEPS)))
        for label in failed:
            print("  - %s" % label)
        print(
            "\nGate A is structural only. Passing it would still not clear the "
            "verification table in CONTRIBUTING.md."
        )
        return 1

    print(
        "Gate A: PASS -- %d/%d structural steps green "
        "(well-formed only; correctness review remains separate)."
        % (len(STEPS), len(STEPS))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
