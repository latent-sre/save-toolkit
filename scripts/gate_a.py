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

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (label, argv-after-the-interpreter, environment additions). Ordered cheapest-and-most-foundational
# first: a broken validator
# makes every downstream result meaningless, so it fails before we spend time on the eval harness.
STEPS = [
    ("Canonical skill and bundle links",
     ["scripts/check_links.py"], None),
    ("Single live roadmap and historical plan status",
     ["scripts/check_plan_status.py"], None),
    ("Planning-status regression tests",
     ["scripts/test_plan_status.py"], None),
    ("No stale unit names",
     ["scripts/check_stale_names.py"], None),
    ("Fleet, plugin, and generated adapter contracts",
     ["scripts/validate_fleet.py"], None),
    ("Fleet validator mutation tests",
     ["scripts/test_validate_fleet.py"], None),
    ("Typed evidence envelope contracts",
     ["scripts/test_evidence_envelope.py"], None),
    ("Operational knowledge update contracts",
     ["scripts/test_operational_learning.py"], None),
    ("Bounded fleet improvement lifecycle contracts",
     ["scripts/test_fleet_improvement.py"], None),
    ("Fleet improvement ledger history and evidence corpus",
     ["scripts/validate_improvement_ledger.py"], None),
    ("Fleet improvement ledger corpus mutation tests",
     ["scripts/test_improvement_ledger.py"], None),
    ("Read-only fleet doctor contracts",
     ["scripts/test_fleet_doctor.py"], None),
    ("Digest-bound verification sandbox contracts",
     ["scripts/test_verification_sandbox.py"], None),
    ("Platform adapter contract tests",
     ["scripts/test_platform_adapters.py"], None),
    ("Codex agent installer safety tests",
     ["scripts/test_install_codex_agents.py"], None),
    ("Protected-main canary workflow contract",
     ["scripts/test_canary_workflow.py"], None),
    ("Brokered Codex/Sol workflow contract",
     ["scripts/test_codex_conformance_workflow.py"], None),
    ("Credential-free raw Git materialization",
     ["scripts/test_materialize_git_tree.py"], None),
    ("Reduced Codex/Sol report contracts",
     ["scripts/test_reduce_codex_conformance_reports.py"], None),
    ("Plugin hook wiring",
     ["scripts/test_hook_wiring.py"], None),
    ("Read-only guard",
     ["scripts/test_readonly_guard.py"], None),
    ("Eval graders",
     ["evals/test_graders.py"], None),
    ("Direct/discovery eval runner contracts",
     ["evals/test_run_evals.py"], None),
    ("Clean-room rig",
     ["evals/test_clean_room.py"], None),
    ("Codex/Sol conformance contracts",
     ["evals/test_run_codex_conformance.py"], None),
    ("Codex/Sol conformance manifest",
     ["evals/run_codex_conformance.py", "--validate"], None),
    ("Codex/Sol agent conformance contracts",
     ["evals/test_run_codex_agent_conformance.py"], None),
    ("Codex/Sol agent conformance manifest",
     ["evals/run_codex_agent_conformance.py", "--validate"], None),
    ("Eval suite parses (shipped fleet)",
     ["evals/run_evals.py", "--validate"], None),
]


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
