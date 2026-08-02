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
ROADMAP_ITEM_STATUSES = {"ready", "active", "blocked", "deferred", "decision-needed"}
ROADMAP_REQUIRED_FIELDS = (
    "Status",
    "Outcome",
    "Source",
    "Prerequisites",
    "Acceptance",
    "Next action",
)
ROADMAP_ITEM_RE = re.compile(r"^###\s+([A-Z][A-Z0-9]*-\d{3})\b")
ROADMAP_FIELD_RE = re.compile(r"^\*\*([A-Za-z][A-Za-z ]+):\*\*\s*(.*)$")
ROADMAP_ITEM_ID_RE = re.compile(r"\b[A-Z][A-Z0-9]*-\d{3}\b")
VOLATILE_PASS_COUNT_RE = re.compile(
    r"(?ix)(?:"
    r"\bpasses?\s+\d+(?:/\d+)?(?:\s+focused)?\s+(?:tests?|scenarios?|cases?|steps?)\b"
    r"|\bpasses?\s+\d+/\d+\b"
    r"|\b(?:reports?|reported)\s+\d+\s+passed\b"
    r"|\b\d+/\d+(?:\s+focused)?\s+(?:tests?|scenarios?|cases?|steps?)\s+passed?\b"
    r"|\b(?:gate\s+[a-z0-9-]+|suite)\s+is\s+\d+\s*/\s*\d+\b"
    r"|\b\d+\s+(?:test\s+)?pass(?:es)?\b"
    r"|\ball\s+\d+\s+(?:offline\s+)?(?:tests?|scenarios?|cases?|steps?)\s+"
    r"(?:pass|parse|succeed)\b"
    r"|\ball\s+(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|"
    r"forty|fifty|sixty|seventy|eighty|ninety)(?:-(?:one|two|three|four|five|six|"
    r"seven|eight|nine))?\s+(?:tests?|scenarios?|cases?|steps?)\s+"
    r"(?:pass|parse|succeed)\b"
    r")"
)


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
    state = re.split(r"\s*(?:,|;|\(|—|–|\s-\s)\s*", normalized, maxsplit=1)[0]
    return state.strip().strip("`*_ .")


def _volatile_current_evidence_lines(text: str) -> list[int]:
    """Find transcribed result counts inside live ``Current evidence`` blocks."""

    matches: list[int] = []
    start_line: int | None = None
    block_lines: list[str] = []

    def finish() -> None:
        nonlocal start_line, block_lines
        if start_line is not None:
            normalized = " ".join(" ".join(block_lines).split())
            if VOLATILE_PASS_COUNT_RE.search(normalized):
                matches.append(start_line)
        start_line = None
        block_lines = []

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if stripped.startswith("**Current evidence:**"):
            finish()
            start_line = line_number
            block_lines.append(stripped)
        elif start_line is not None and (
            stripped.startswith("**") or stripped.startswith("#")
        ):
            finish()
        elif start_line is not None:
            block_lines.append(stripped)
    finish()
    return matches


def _roadmap_items(text: str) -> list[dict[str, object]]:
    """Parse live roadmap item headings and their bold field blocks."""

    lines = text.splitlines()
    starts: list[tuple[int, str]] = []
    for index, raw_line in enumerate(lines):
        match = ROADMAP_ITEM_RE.match(raw_line.strip())
        if match:
            starts.append((index, match.group(1)))

    items: list[dict[str, object]] = []
    for position, (start, item_id) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        fields: dict[str, str] = {}
        duplicate_fields: set[str] = set()
        current_field: str | None = None
        for raw_line in lines[start + 1 : end]:
            stripped = raw_line.strip()
            field_match = ROADMAP_FIELD_RE.match(stripped)
            if field_match:
                current_field = field_match.group(1)
                if current_field in fields:
                    duplicate_fields.add(current_field)
                fields[current_field] = field_match.group(2).strip()
            elif current_field is not None and stripped and not stripped.startswith("##"):
                fields[current_field] = (fields[current_field] + " " + stripped).strip()
        items.append(
            {
                "id": item_id,
                "line": start + 1,
                "fields": fields,
                "duplicate_fields": duplicate_fields,
            }
        )
    return items


def _roadmap_item_failures(text: str) -> list[str]:
    failures: list[str] = []
    items = _roadmap_items(text)
    ids = [str(item["id"]) for item in items]
    known_ids = set(ids)

    seen: set[str] = set()
    for item in items:
        item_id = str(item["id"])
        line = int(item["line"])
        fields = item["fields"]
        assert isinstance(fields, dict)
        duplicate_fields = item["duplicate_fields"]
        assert isinstance(duplicate_fields, set)

        if item_id in seen:
            failures.append(
                f"docs/fleet-roadmap.md:{line}: duplicate roadmap item ID {item_id}"
            )
        seen.add(item_id)

        for field in sorted(duplicate_fields):
            failures.append(
                f"docs/fleet-roadmap.md:{line}: {item_id} repeats field '{field}'"
            )
        for field in ROADMAP_REQUIRED_FIELDS:
            if not str(fields.get(field, "")).strip():
                failures.append(
                    f"docs/fleet-roadmap.md:{line}: {item_id} missing field '{field}'"
                )

        status_value = str(fields.get("Status", ""))
        status = _status_state(status_value) if status_value else ""
        if status and status not in ROADMAP_ITEM_STATUSES:
            failures.append(
                f"docs/fleet-roadmap.md:{line}: {item_id} has unsupported status {status!r}"
            )
        if status == "deferred" and not str(fields.get("Reopen trigger", "")).strip():
            failures.append(
                f"docs/fleet-roadmap.md:{line}: {item_id} deferred item lacks 'Reopen trigger'"
            )

        prerequisites = str(fields.get("Prerequisites", ""))
        for prerequisite_id in sorted(set(ROADMAP_ITEM_ID_RE.findall(prerequisites))):
            if prerequisite_id == item_id:
                failures.append(
                    f"docs/fleet-roadmap.md:{line}: {item_id} cannot depend on itself"
                )
            elif prerequisite_id not in known_ids:
                failures.append(
                    f"docs/fleet-roadmap.md:{line}: {item_id} references unknown prerequisite "
                    f"{prerequisite_id}"
                )
    return failures


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
        for line_number in _volatile_current_evidence_lines(roadmap):
            failures.append(
                f"docs/fleet-roadmap.md:{line_number}: Current evidence contains a volatile "
                "numeric pass count; cite an immutable report, CI run, or exact revision instead"
            )
        failures.extend(_roadmap_item_failures(roadmap))

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
