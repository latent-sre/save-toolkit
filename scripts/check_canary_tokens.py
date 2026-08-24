#!/usr/bin/env python3
"""Validate reference-read canary tokens: unique everywhere, present where the convention is used.

WHAT A CANARY TOKEN IS FOR. A bundled reference ends with a short token (`q_omwql_7b31`). An agent
that actually read the file can quote it, so a reviewer can tell a sourced answer from a plausible
one reconstructed from model memory. The whole mechanism rests on one property: a token identifies
exactly ONE file. Two files sharing a token — the obvious copy-paste when a reference is cloned as
the starting point for a sibling — silently degrades the proof to "read one of these two", and
nothing else in this repository notices. That is the failure this validator exists to catch.

SCOPE, DELIBERATELY NARROW. The convention is adopted bundle by bundle, not fleet-wide: 24 of the
repository's reference files carry a token today, and the obs and akamai bundles are at 100%. So
uniqueness is enforced EVERYWHERE the convention appears, while presence is required only where it
is already universal (`REQUIRED_GLOBS`). Mandating presence fleet-wide would fail ~49 existing
files that never adopted it — a churn decision for a human, not something a validator should force.
When another bundle adopts the convention, add its glob here and the requirement starts applying.

Standard library only — this script needs nothing more.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The token grammar: `q_` then lowercase alphanumerics and underscores. Tokens are meant to be
# meaningless to a model that never read the file, so this deliberately does not encode the
# per-bundle prefix habit (`q_om…` for obs-metrics) — that is a readability nicety, not a rule
# worth failing a build over.
TOKEN = re.compile(r"\bq_[a-z0-9_]{3,}\b")

# Bundles where every reference file carries a token today; presence is enforced only here.
REQUIRED_GLOBS = ("obs-*/references/*.md", "akamai-edge/references/*.md")


def tokens_by_file(skills: Path) -> dict[Path, set[str]]:
    """Every canary token found under *skills*, keyed by the file carrying it."""

    found: dict[Path, set[str]] = {}
    for path in sorted(skills.rglob("*.md")):
        try:
            matches = set(TOKEN.findall(path.read_text(encoding="utf-8")))
        except OSError as exc:  # unreadable file is a finding, never a silent skip
            found[path] = set()
            print(f"CANARY: cannot read {path}: {exc}", file=sys.stderr)
            continue
        if matches:
            found[path] = matches
    return found


def check(root: Path = ROOT) -> list[str]:
    """Return a list of failure strings; empty means the tree satisfies both rules."""

    skills = root / "skills"
    failures: list[str] = []

    owners: dict[str, list[str]] = defaultdict(list)
    for path, tokens in tokens_by_file(skills).items():
        for token in tokens:
            owners[token].append(path.relative_to(root).as_posix())
    for token, files in sorted(owners.items()):
        if len(files) > 1:
            failures.append(
                f"token {token} appears in {len(files)} files, so it proves nothing about which "
                f"was read: {', '.join(sorted(files))}"
            )

    for glob in REQUIRED_GLOBS:
        matched = sorted(skills.glob(glob))
        if not matched:
            # A typo'd glob would make the presence rule vacuous — fail loudly instead.
            failures.append(f"REQUIRED_GLOBS entry matches no files: {glob}")
            continue
        for path in matched:
            if not TOKEN.search(path.read_text(encoding="utf-8")):
                failures.append(
                    f"{path.relative_to(root).as_posix()}: in a bundle that requires a canary "
                    "token but carries none"
                )

    return failures


def main() -> int:
    failures = check()
    if failures:
        for failure in failures:
            print(f"CANARY: {failure}", file=sys.stderr)
        return 1
    print("check_canary_tokens: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
