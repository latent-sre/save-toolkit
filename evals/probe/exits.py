"""How the evals command lines end: one exit-code vocabulary, and a parser that refuses with it.

The runner (`build_probe.py`), the run comparison and the turn-count summary share these codes, so a
script that calls any of them reads a refused command line the same way.
"""

from __future__ import annotations

import argparse
import enum
import sys
from typing import NoReturn


class ExitCode(enum.IntEnum):
    """How a job ends; the order of a batch's exits is decided in `cli._conclude`."""

    OK = 0  # a passing batch or a clean job
    FAIL = 1  # a FAIL verdict
    DIFFERENT = 1  # a rescore diff that lists a difference
    INCONCLUSIVE = 2
    REFUSED = 3  # bad input or scenario: the job did not run
    AUTH_LOST = 4  # authentication lost mid-batch


class UsageParser(argparse.ArgumentParser):
    """argparse exits 2 on a usage error, which the runner reads as an INCONCLUSIVE batch; a refused
    command line is `ExitCode.REFUSED`."""

    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(ExitCode.REFUSED, f"{self.prog}: error: {message}\n")
