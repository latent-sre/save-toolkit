#!/usr/bin/env python3
"""Gate A -- the mechanical audit. One entrypoint, run by CI and by humans/agents alike.

WHY THIS EXISTS
---------------
The run protocol (CONTRIBUTING.md) used to *transcribe* the CI steps into prose. That broke the repo's
own anti-rot doctrine -- "never transcribe an artifact that lives in the repo, point at it" -- and it
had already drifted on the day it was written: the transcription silently dropped the dependency
install step, so a cold checkout died with ModuleNotFoundError on the eval graders. Two sources of
truth for "what Gate A is" means they disagree, and the one a human reads is the one that rots.

So there is now exactly one: this file. `.github/workflows/validate.yml` calls it; the protocol points
at it. They cannot drift apart, because there is nothing to keep in sync.

It also settles the interpreter question for good. The repo's docs disagreed about how to invoke Python
on Windows (`python` vs `py -3` vs `python3`, the last being the Microsoft Store stub that once silently
disarmed the read-only guard). Sub-steps here run under `sys.executable` -- whichever interpreter you
started this script with, by construction the right one.

WHAT IT DOES NOT DO
-------------------
Gate A is STRUCTURAL. It proves the fleet is well-formed; it never proves the fleet is right. It passes
green over a skill that leaks the production password into argv. The adversarial correctness/security/
conformance reviews required by CONTRIBUTING.md are the ones that catch that.
"""

import glob
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Non-test structural steps that need a fixed position or non-default arguments. Ordered
# cheapest-and-most-foundational first: a broken validator makes every downstream result
# meaningless, so it fails before we spend time on the eval harness. The `test_*.py` suites are
# NOT listed here — they are discovered below, so a new test file can never be silently left
# unrun. (That is not hypothetical: scripts/test_check_links.py was authored, added to no runner,
# and executed by nothing until this list stopped being the second source of truth for "what
# tests exist".)
STRUCTURAL_STEPS = [
    ("Canonical skill and bundle links",
     ["scripts/check_links.py"], None),
    ("Single live roadmap and historical plan status",
     ["scripts/check_plan_status.py"], None),
    ("No stale unit names",
     ["scripts/check_stale_names.py"], None),
    ("Reference-read canary tokens",
     ["scripts/check_canary_tokens.py"], None),
    ("Fleet, plugin, and generated adapter contracts",
     ["scripts/validate_fleet.py"], None),
    ("Fleet-improvement records satisfy their schema",
     ["scripts/validate_improvements.py"], None),
    ("Eval suite parses (shipped fleet)",
     ["evals/run_evals.py", "--validate"], None),
]


def _discover_test_steps():
    """Every scripts/test_*.py and evals/test_*.py, discovered — never a hand-kept roster.

    The label is derived from the path so adding a test file needs no edit here at all; the file's
    mere existence enrolls it in Gate A.
    """
    steps = []
    for pattern in ("scripts/test_*.py", "evals/test_*.py"):
        # Not glob.glob(pattern, root_dir=ROOT): the root_dir kwarg is 3.10+, and this single gate
        # must not raise a TypeError before running a check. Glob absolute, then relativize.
        for abspath in sorted(glob.glob(os.path.join(ROOT, pattern))):
            rel = os.path.relpath(abspath, ROOT).replace(os.sep, "/")
            steps.append((f"Unit: {rel}", [rel], None))
    return steps


STEPS = STRUCTURAL_STEPS + _discover_test_steps()


MINIMUM_PYTHON = (3, 12)


def preflight():
    """Fail loudly on a bad environment, with the exact remedy -- never auto-install or guess.

    Two hard floors, and the same reasoning behind both. The eval graders import yaml and FAIL (not
    skip) without it. An agent that hits a bare ModuleNotFoundError reaches for `pip install
    pyyaml`, unpinned, which requirements-dev.txt explicitly forbids. Hand it the right command
    instead of letting it invent a wrong one.

    The interpreter floor is the same class of problem and used to be checked nowhere. CI pins
    3.12 (.github/workflows/validate.yml, release.yml), and evals/clean_room.py calls
    shutil.rmtree(onexc=...), which is 3.12+. Run this gate on 3.11 and the yaml branch passes, the
    steps start, and one of them dies with a bare `TypeError: rmtree() got an unexpected keyword
    argument 'onexc'` -- precisely the confusing failure this function exists to prevent, for the
    one dependency it never mentioned. Checking the version here turns it into a sentence.
    """
    if sys.version_info < MINIMUM_PYTHON:
        required = ".".join(str(part) for part in MINIMUM_PYTHON)
        running = ".".join(str(part) for part in sys.version_info[:3])
        print("Gate A: FAIL -- this repository requires Python %s or newer; you are on %s.\n"
              "  CI pins %s, and at least one step (evals/clean_room.py) calls a %s-only API,\n"
              "  so an older interpreter fails mid-run with an unrelated-looking TypeError.\n"
              "  Re-run with a %s+ interpreter, for example:\n\n"
              "    python%s scripts/gate_a.py\n\n"
              "  On Windows use `python` or `py -3`, never bare `python3` (the Store stub).\n"
              % (required, running, required, required, required, required),
              file=sys.stderr)
        return False
    try:
        import yaml  # noqa: F401
    except ImportError:
        print("Gate A: FAIL -- eval-harness dependencies are not installed.\n"
              "  The graders import yaml and fail (not skip) without it.\n"
              "  Install the PINNED set (do not `pip install pyyaml` bare):\n\n"
              "    %s -m pip install -r requirements-dev.txt\n" % sys.executable,
              file=sys.stderr)
        return False
    return True


def run_steps(steps):
    """Run every step to completion and return the failed labels, in roster order.

    Steps were always independent interpreter processes; they now run concurrently, which cuts
    the gate's wall-clock from the sum of the step times to roughly the slowest step. Two
    properties of the serial gate are deliberately preserved: every step runs even after one
    fails (an agent fixing the fleet wants the whole list of what is broken, not a bisect), and
    output prints in the roster's order — foundational checks first, logs deterministic —
    regardless of completion order, by buffering each step's output until its turn.
    """
    def run_one(step):
        _label, argv, env_extra = step
        env = dict(os.environ, **env_extra) if env_extra else None
        proc = subprocess.run(
            [sys.executable] + argv, cwd=ROOT, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True,
        )
        return proc.returncode, proc.stdout

    failed = []
    with ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 2)) as pool:
        futures = [pool.submit(run_one, step) for step in steps]
        for (label, _argv, _env), future in zip(steps, futures):
            rc, output = future.result()
            print("\n=== %s ===" % label, flush=True)
            sys.stdout.write(output)
            sys.stdout.flush()
            if rc != 0:
                failed.append(label)
    return failed


def main():
    if not preflight():
        return 1

    failed = run_steps(STEPS)

    print("\n" + "-" * 60)
    if failed:
        print("Gate A: FAIL -- %d of %d step(s) failed:" % (len(failed), len(STEPS)))
        for label in failed:
            print("  - %s" % label)
        print("\nGate A is structural only. Passing it would still not clear the adversarial reviews (CONTRIBUTING.md).")
        return 1

    print("Gate A: PASS -- %d/%d structural steps green." % (len(STEPS), len(STEPS)))
    print("This proves the fleet is WELL-FORMED, not that it is CORRECT.")
    print("The adversarial correctness/security/conformance reviews (CONTRIBUTING.md) are still owed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
