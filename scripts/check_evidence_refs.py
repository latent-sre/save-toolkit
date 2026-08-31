#!/usr/bin/env python3
"""Validate durable eval evidence references and the folded historical index."""

from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path


ROOT = Path(os.environ.get("FLEET_ROOT") or Path(__file__).resolve().parents[1]).resolve()
ROADMAP = Path("docs/fleet-roadmap.md")
REVIEWS = Path("docs/reviews")
FOLDED_INDEX = REVIEWS / "2026-08-30-folded-eval-index.md"
BATCH_ID_RE = re.compile(r"\b\d{8}T\d{6}Z-[0-9a-f]{8}\b")
FULL_OBJECT_ID_RE = re.compile(r"`([0-9a-f]{40})`")
INPUT_SHA256_RE = re.compile(r"`([0-9a-f]{64})`")
INPUT_STATE_RE = re.compile(r"(plugin dirty|candidate clean): (true|false)")
FOLDED_COUNT_RE = re.compile(r"(?m)^(\d+) sealed packets folded\.")
FOLDED_HEADER = (
    "| Batch | Verdict | Model | Candidate | Input state | Workspace dirty | Input SHA-256 | "
    "Scenario count | Scenarios |"
)
# SHA-256 over the 69 source-derived rows, each normalized as nine tab-separated cells plus LF,
# in historical packet order. The source tree is 91a4e92aacda8508ed03173eebe62138520b4cbc.
FOLDED_SOURCE_ROWS_SHA256 = "b0a2d73745e564963a7b1ac0cc539e30de6423e3d555dae7fc20ab22b4867cf2"


def _read(path: Path) -> tuple[str | None, str | None]:
    try:
        return path.read_text(encoding="utf-8"), None
    except OSError as exc:
        return None, str(exc)


def _folded_rows_digest(rows: list[list[str]]) -> str:
    payload = "".join("\t".join(row) + "\n" for row in rows).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _check_folded_index(root: Path, *, expected_rows_sha256: str | None = None) -> list[str]:
    """Require every folded row to retain exact identity and its declared scenarios."""

    path = root / FOLDED_INDEX
    if not path.is_file():
        if expected_rows_sha256 is not None:
            return [f"{FOLDED_INDEX.as_posix()}: missing folded historical index"]
        return []
    text, error = _read(path)
    if error:
        return [f"{FOLDED_INDEX.as_posix()}: cannot read: {error}"]
    assert text is not None

    failures: list[str] = []
    declared_match = FOLDED_COUNT_RE.search(text)
    declared = int(declared_match.group(1)) if declared_match else None
    if declared is None:
        failures.append(
            f"{FOLDED_INDEX.as_posix()}: missing '<count> sealed packets folded.' declaration"
        )
    if FOLDED_HEADER not in text:
        failures.append(
            f"{FOLDED_INDEX.as_posix()}: table must retain candidate, input identity, and scenario "
            "columns"
        )

    seen: set[str] = set()
    normalized_rows: list[list[str]] = []
    row_count = 0
    for number, line in enumerate(text.splitlines(), start=1):
        batch_match = BATCH_ID_RE.search(line)
        if not line.startswith("| `") or batch_match is None:
            continue
        row_count += 1
        batch = batch_match.group(0)
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 9:
            failures.append(
                f"{FOLDED_INDEX.as_posix()}:{number}: folded row {batch} must have 9 columns; "
                f"found {len(cells)}"
            )
            continue
        normalized_rows.append(cells)
        if batch in seen:
            failures.append(f"{FOLDED_INDEX.as_posix()}:{number}: duplicate folded batch {batch}")
        seen.add(batch)

        if FULL_OBJECT_ID_RE.fullmatch(cells[3]) is None:
            failures.append(
                f"{FOLDED_INDEX.as_posix()}:{number}: folded batch {batch} candidate must be a "
                "full 40-character Git object ID"
            )
        input_state = INPUT_STATE_RE.fullmatch(cells[4])
        if input_state is None:
            failures.append(
                f"{FOLDED_INDEX.as_posix()}:{number}: folded batch {batch} Input state must be "
                "'plugin dirty: true|false' or 'candidate clean: true|false'"
            )
        elif input_state.group(1) == "plugin dirty":
            if cells[5] not in {"true", "false"}:
                failures.append(
                    f"{FOLDED_INDEX.as_posix()}:{number}: folded batch {batch} Workspace dirty "
                    "must be true or false for a plugin packet"
                )
        elif cells[5] != "n/a":
            failures.append(
                f"{FOLDED_INDEX.as_posix()}:{number}: folded batch {batch} Workspace dirty must "
                "be n/a when the claim envelope did not record it"
            )
        if INPUT_SHA256_RE.fullmatch(cells[6]) is None:
            failures.append(
                f"{FOLDED_INDEX.as_posix()}:{number}: folded batch {batch} input digest must be a "
                "full 64-character SHA-256"
            )
        try:
            scenario_count = int(cells[7])
        except ValueError:
            failures.append(
                f"{FOLDED_INDEX.as_posix()}:{number}: folded batch {batch} has invalid scenario count "
                f"{cells[7]!r}"
            )
            continue
        scenarios = [scenario.strip() for scenario in cells[8].split(",") if scenario.strip()]
        if len(scenarios) != scenario_count:
            failures.append(
                f"{FOLDED_INDEX.as_posix()}:{number}: folded batch {batch} declares "
                f"{scenario_count} scenarios but lists {len(scenarios)}"
            )
        if len(set(scenarios)) != len(scenarios):
            failures.append(
                f"{FOLDED_INDEX.as_posix()}:{number}: folded batch {batch} repeats a scenario"
            )

    if declared is not None and row_count != declared:
        failures.append(
            f"{FOLDED_INDEX.as_posix()}: declares {declared} folded packets but contains "
            f"{row_count} rows"
        )
    if expected_rows_sha256 is not None and len(normalized_rows) == row_count:
        observed = _folded_rows_digest(normalized_rows)
        if observed != expected_rows_sha256:
            failures.append(
                f"{FOLDED_INDEX.as_posix()}: normalized rows do not match the source-derived "
                f"SHA-256; expected {expected_rows_sha256}, observed {observed}"
            )
    return failures


def check(root: Path = ROOT) -> list[str]:
    """Return folded-index defects and unresolved live-roadmap batches below *root*."""

    expected_rows_sha256 = FOLDED_SOURCE_ROWS_SHA256 if root.resolve() == ROOT else None
    failures = _check_folded_index(root, expected_rows_sha256=expected_rows_sha256)
    roadmap_path = root / ROADMAP
    roadmap, error = _read(roadmap_path)
    if error:
        return failures + [f"{ROADMAP.as_posix()}: cannot read: {error}"]
    assert roadmap is not None

    cited = sorted(set(BATCH_ID_RE.findall(roadmap)))
    if not cited:
        return failures

    reviews_root = root / REVIEWS
    if not reviews_root.is_dir():
        return failures + [f"{REVIEWS.as_posix()}: missing durable evidence directory"]

    resolved: set[str] = set()
    for path in sorted(reviews_root.rglob("*.md")):
        text, read_error = _read(path)
        if read_error:
            failures.append(f"{path.relative_to(root).as_posix()}: cannot read: {read_error}")
            continue
        assert text is not None
        resolved.update(BATCH_ID_RE.findall(text))

    for batch_id in cited:
        if batch_id not in resolved:
            failures.append(
                f"{ROADMAP.as_posix()}: batch {batch_id} has no durable Markdown record under "
                f"{REVIEWS.as_posix()}"
            )
    return failures


def main() -> int:
    failures = check()
    if failures:
        for failure in failures:
            print(f"EVIDENCE REFS: {failure}", file=sys.stderr)
        return 1
    print("check_evidence_refs: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
