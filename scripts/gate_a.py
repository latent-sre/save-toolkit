#!/usr/bin/env python3
"""Gate A -- the fast live-tree structural audit used by CI and before a push.

WHY THIS EXISTS
---------------
The contributor protocol once copied CI's command list into prose. The copies drifted, so this file
became the one executable source of truth for the repository's push-boundary structural checks.

SCOPE
-----
Gate A runs validators against the checked-out repository. It deliberately does not discover or run
``test_*.py``, the eval harness, release tests, guard tests, or other component suites. Those checks
belong to the implementation that changed their owning code. Re-running every component suite at
the push boundary contradicted the repository's focused-test and owner-trigger rules and made a
nominally structural check require eval dependencies and Git history.

The remaining checks are read-only, standard-library processes. They do not need a clean tree, a
full clone or a machine-wide lock. Today no gate step imports a third-party package; the first
one that does must ship the CI `pip install -r requirements-dev.txt` steps in the same change
(see the dependency rule in AGENTS.md Hard rules). Every step still runs after a failure so one invocation
reports the complete structural defect set.

OUTPUT
------
A successful default run prints one verdict. Failures retain their complete attributed diagnostics.
Pass ``--verbose`` when the complete step transcript is useful.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# The single roster of live-tree structural checks. Unit and component suites are intentionally
# absent; their owners run them while implementing the relevant change.
STRUCTURAL_STEPS = [
    (
        "Canonical skill and bundle links",
        ["scripts/check_links.py"],
        None,
    ),
    (
        "Fleet, plugin, and generated adapter contracts",
        ["scripts/validate_fleet.py"],
        None,
    ),
    (
        "Context-cost budgets for canonical tasks",
        ["scripts/check_context_cost.py"],
        None,
    ),
    (
        "Weight totals: evals lines, skills bytes, agents bytes",
        ["scripts/check_weight.py"],
        None,
    ),
]

STEPS = STRUCTURAL_STEPS
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
    for label, argv, env_extra in steps:
        env = dict(os.environ, **env_extra) if env_extra else None
        proc = subprocess.run(
            [sys.executable, *argv],
            cwd=ROOT,
            env=env,
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
