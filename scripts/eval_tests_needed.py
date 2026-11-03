#!/usr/bin/env python3
"""Decide whether a pull request's changed paths require the eval-machinery test job.

The heavy `evals/test_*.py` files exercise the eval runner, oracles, fixtures and scenarios, the
scripts and hooks they import, and the test configuration. A change confined to documentation or
to agent and skill prose cannot change their outcome, so CI skips that job for it. Prints `true`
or `false` for the paths read from stdin; any path under a trigger root prints `true`.
"""

from __future__ import annotations

import re
import sys

TRIGGER = re.compile(
    r"^(?:evals/|scripts/|hooks/|skills/[^/]+/scripts/"
    r"|conftest\.py$|pytest\.ini$|pyproject\.toml$|uv\.lock$"
    r"|\.github/workflows/validate\.yml$)"
)


def needed(paths: list[str]) -> bool:
    return any(TRIGGER.match(path.strip()) for path in paths if path.strip())


def main() -> int:
    print("true" if needed(sys.stdin.read().splitlines()) else "false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
