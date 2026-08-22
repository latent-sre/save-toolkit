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

ONE RUN PER MACHINE
-------------------
Two gates overlapping on one machine false-red each other. Measured 2026-08-21: with a second python
process running the same file, scripts/test_host_install_probe.py reports 19 failures and
evals/test_codex_trial.py a KeyError, both finishing in a third of their healthy time; alone and in
sequence they pass 6/6. The shared resource was not pinned down, and the common way to overlap is not
deliberate at all: `gate_a.py | head` on Windows leaves the whole gate running orphaned after `head`
exits, so every gate started afterwards collides with it. A false red sends a session into a
debugging spiral that costs far more than the gate, so the gate takes a machine-wide lock in the
temp directory, refuses to start while a live holder has it, reclaims a lock whose holder is dead,
and always releases its own. Covered by scripts/test_gate_a.py.

WHAT IT DOES NOT DO
-------------------
Gate A is STRUCTURAL. It proves the fleet is well-formed; it never proves the fleet is right. It passes
green over a skill that leaks the production password into argv. The adversarial correctness/security/
conformance reviews required by CONTRIBUTING.md are the ones that catch that.

OUTPUT
------
A successful default run prints only Gate A's final verdict. Failed steps always retain their full,
attributed diagnostics. Pass ``--verbose`` when the complete step transcript is useful.
"""

import argparse
import contextlib
import glob
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

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


# Machine-wide on purpose: the overlap failure is per host (shared temp and user directories), not
# per checkout, so two clones running the gate at once must also be refused.
LOCK_PATH = Path(tempfile.gettempdir()) / "save-toolkit-gate_a.lock"


class GateBusy(Exception):
    def __init__(self, lock_path, holder_pid, holder_root):
        super().__init__(lock_path, holder_pid, holder_root)
        self.lock_path, self.holder_pid, self.holder_root = lock_path, holder_pid, holder_root


def _read_holder(lock_path):
    """(pid, root) from a lock file, or None when the file is empty or garbage — a crash artefact."""
    try:
        lines = lock_path.read_text(encoding="utf-8").splitlines()
        return int(lines[0]), (lines[1] if len(lines) > 1 else "?")
    except (OSError, ValueError, IndexError):
        return None


# The Windows lock is MANDATORY, not advisory: a byte range locked with msvcrt.locking cannot be read
# by anyone else, and the whole point of the identity text is that a refused run can read it. So the
# locked byte lives far past the identity (locking beyond EOF is allowed), and the identity at offset
# 0 stays readable. POSIX flock() is whole-file advisory and does not care.
LOCK_BYTE_OFFSET = 1 << 16


def _os_lock_nonblocking(fd):
    """Acquire an exclusive OS lock on *fd* without blocking.

    Returns True on success. Returns False if another process already holds the lock.
    Uses ``fcntl.flock`` on POSIX and ``msvcrt.locking`` on Windows — both are stdlib.
    """
    if os.name == "nt":
        import msvcrt
        os.lseek(fd, LOCK_BYTE_OFFSET, os.SEEK_SET)
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except OSError:
            return False
    else:
        import fcntl
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return False
    return True


def _os_unlock(fd):
    """Release the OS advisory lock on *fd* (Windows only; POSIX releases on close)."""
    if os.name == "nt":
        import msvcrt
        os.lseek(fd, LOCK_BYTE_OFFSET, os.SEEK_SET)
        try:
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass


@contextlib.contextmanager
def gate_lock(lock_path=None):
    lock_path = Path(lock_path or LOCK_PATH)
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
    try:
        if not _os_lock_nonblocking(fd):
            # Another process holds the OS advisory lock; read its identity for the message.
            holder = _read_holder(lock_path)
            raise GateBusy(lock_path, *(holder if holder is not None else ("?", "?")))
        # We hold the lock — record our identity so a future GateBusy message names us.
        os.ftruncate(fd, 0)
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, ("%d\n%s\n" % (os.getpid(), ROOT)).encode("utf-8"))
        try:
            yield
        finally:
            # Release, never delete. Windows cannot unlink an open file at all, and on POSIX deleting
            # a lock file is the classic race: a waiter that already opened the old inode and a
            # newcomer that creates a fresh file both "win". The file is one line in the temp dir;
            # "released" means the next gate_lock() succeeds, not that the file is gone.
            _os_unlock(fd)
    finally:
        os.close(fd)


def run_steps(steps, *, verbose=False):
    """Run every step to completion and return the failed labels, in roster order.

    Steps were always independent interpreter processes; they now run concurrently, which cuts
    the gate's wall-clock from the sum of the step times to roughly the slowest step. Two
    properties of the serial gate are deliberately preserved: every step runs even after one
    fails (an agent fixing the fleet wants the whole list of what is broken, not a bisect), and any
    output that is shown prints in roster order regardless of completion order. Successful output is
    suppressed by default; a failure keeps its complete attributed diagnostics, and ``verbose``
    restores the full deterministic transcript.
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
            if verbose or rc != 0:
                print("\n=== %s ===" % label, flush=True)
                sys.stdout.write(output)
                sys.stdout.flush()
            if rc != 0:
                failed.append(label)
    return failed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="print every step's output; failures are always printed",
    )
    args = parser.parse_args(argv)

    if not preflight():
        return 1

    try:
        with gate_lock():
            failed = run_steps(STEPS, verbose=True) if args.verbose else run_steps(STEPS)
    except GateBusy as busy:
        print("Gate A: REFUSED -- another Gate A is already running (pid %s, started from %s).\n"
              "  Two runs that overlap on one machine false-red each other (test_host_install_probe,\n"
              "  test_codex_trial), so this run did not start. Wait for that one to finish -- or, if it\n"
              "  is an orphan (for example a `gate_a.py | head` whose reader already exited), stop it --\n"
              "  and rerun. Lock: %s" % (busy.holder_pid, busy.holder_root, busy.lock_path),
              file=sys.stderr)
        return 1

    if failed:
        print("\n" + "-" * 60)
        print("Gate A: FAIL -- %d of %d step(s) failed:" % (len(failed), len(STEPS)))
        for label in failed:
            print("  - %s" % label)
        print("\nGate A is structural only. Passing it would still not clear the adversarial reviews (CONTRIBUTING.md).")
        return 1

    print(
        "Gate A: PASS -- %d/%d structural steps green "
        "(well-formed only; correctness review remains separate)."
        % (len(STEPS), len(STEPS))
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
