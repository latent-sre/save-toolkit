#!/usr/bin/env python3
"""Fail when historical plans can masquerade as the fleet's live backlog."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


ROOT = Path(os.environ.get("FLEET_ROOT") or Path(__file__).resolve().parents[1]).resolve()
ROADMAP = Path("docs/fleet-roadmap.md")
PLAN_ROOT = Path("docs/superpowers/plans")
SPEC_ROOT = Path("docs/superpowers/specs")
ROOT_POINTERS = (Path("AGENTS.md"), Path("README.md"), Path("CONTRIBUTING.md"))
HISTORICAL_MARKERS = ("implemented", "superseded", "historical")


def _read(root: Path, relative: Path) -> tuple[str | None, str | None]:
    path = root / relative
    try:
        return path.read_text(encoding="utf-8"), None
    except OSError as exc:
        return None, f"{relative.as_posix()}: cannot read: {exc}"


def _front(text: str, lines: int = 14) -> str:
    return "\n".join(text.splitlines()[:lines]).lower()


def _status_value(text: str, lines: int = 14) -> str | None:
    """Return only the value attached to a top-of-file Status field."""

    for raw_line in text.splitlines()[:lines]:
        line = raw_line.strip()
        if line.startswith(">"):
            line = line[1:].strip()
        line = line.replace("**", "").strip()
        match = re.fullmatch(r"(?i)status\s*:\s*(.+)", line)
        if match:
            return match.group(1).strip()
    return None


def _status_state(value: str) -> str:
    normalized = value.strip().strip("`*_ .").lower()
    return re.split(r"\s*(?:,|;|\(|—|–|\s-\s)\s*", normalized, maxsplit=1)[0].strip()


def check(root: Path = ROOT) -> list[str]:
    """Return every planning-governance failure under *root*."""

    failures: list[str] = []
    roadmap, error = _read(root, ROADMAP)
    if error:
        failures.append(error)
    elif roadmap is not None:
        front = _front(roadmap, 10)
        status = _status_value(roadmap, 10)
        if status is None or _status_state(status) != "live":
            failures.append("docs/fleet-roadmap.md: must declare 'Status: live' near the top")
        if "only document" not in front or "unfinished" not in front:
            failures.append(
                "docs/fleet-roadmap.md: must declare itself the only unfinished-work registry"
            )

    plan_dir = root / PLAN_ROOT
    if not plan_dir.is_dir():
        failures.append(f"{PLAN_ROOT.as_posix()}: missing plan archive")
    else:
        for path in sorted(plan_dir.glob("*.md")):
            relative = path.relative_to(root)
            text, read_error = _read(root, relative)
            if read_error:
                failures.append(read_error)
                continue
            assert text is not None
            front = _front(text)
            status = _status_value(text)
            if status is None:
                failures.append(
                    f"{relative.as_posix()}: historical plan lacks a top-of-file Status banner"
                )
                continue
            if _status_state(status) not in HISTORICAL_MARKERS:
                failures.append(
                    f"{relative.as_posix()}: plan status must mark it implemented, superseded, "
                    "or historical; live work belongs in docs/fleet-roadmap.md"
                )
            if "docs/fleet-roadmap.md" not in front:
                failures.append(
                    f"{relative.as_posix()}: plan status must point to docs/fleet-roadmap.md"
                )

    spec_dir = root / SPEC_ROOT
    if not spec_dir.is_dir():
        failures.append(f"{SPEC_ROOT.as_posix()}: missing specification archive")
    else:
        for path in sorted(spec_dir.glob("*.md")):
            relative = path.relative_to(root)
            text, read_error = _read(root, relative)
            if read_error:
                failures.append(read_error)
                continue
            assert text is not None
            front = _front(text)
            status = _status_value(text)
            if status is None:
                failures.append(f"{relative.as_posix()}: specification lacks a status")
            elif _status_state(status) not in HISTORICAL_MARKERS:
                failures.append(
                    f"{relative.as_posix()}: specification status must mark it implemented, "
                    "superseded, or historical; live work belongs in docs/fleet-roadmap.md"
                )

    for relative in ROOT_POINTERS:
        text, read_error = _read(root, relative)
        if read_error:
            failures.append(read_error)
        elif text is not None and "docs/fleet-roadmap.md" not in text:
            failures.append(f"{relative.as_posix()}: must point to docs/fleet-roadmap.md")

    audit, audit_error = _read(root, Path("docs/AUDIT-2026-07-12.md"))
    if audit_error:
        failures.append(audit_error)
    elif audit is not None and "historical snapshot" not in _front(audit, 12):
        failures.append(
            "docs/AUDIT-2026-07-12.md: dated OPEN labels need a Historical snapshot banner"
        )

    return failures


def main() -> int:
    failures = check()
    if failures:
        for failure in failures:
            print(f"PLAN STATUS: {failure}", file=sys.stderr)
        return 1
    print("check_plan_status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
