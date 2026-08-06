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
        for rel in sorted(glob.glob(pattern, root_dir=ROOT)):
            steps.append((f"Unit: {rel}", [rel], None))
    return steps


STEPS = STRUCTURAL_STEPS + _discover_test_steps()


def preflight():
    """Fail loudly on missing deps, with the PINNED command -- never auto-install.

    The eval graders import yaml and FAIL (not skip) without it. An agent that hits a bare
    ModuleNotFoundError reaches for `pip install pyyaml`, unpinned, which requirements-dev.txt
    explicitly forbids. Hand it the right command instead of letting it invent a wrong one.
    """
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


def main():
    if not preflight():
        return 1

    failed = []
    for label, argv, env_extra in STEPS:
        print("\n=== %s ===" % label, flush=True)
        # Run every step even after one fails: an agent fixing the fleet wants the whole list of what
        # is broken, not a bisect through one failure at a time.
        env = dict(os.environ, **env_extra) if env_extra else None
        rc = subprocess.call([sys.executable] + argv, cwd=ROOT, env=env)
        if rc != 0:
            failed.append(label)

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
