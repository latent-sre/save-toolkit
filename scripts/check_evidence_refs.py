#!/usr/bin/env python3
"""Require every eval batch cited by the live roadmap to resolve to durable evidence."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


ROOT = Path(os.environ.get("FLEET_ROOT") or Path(__file__).resolve().parents[1]).resolve()
ROADMAP = Path("docs/fleet-roadmap.md")
REVIEWS = Path("docs/reviews")
BATCH_ID_RE = re.compile(r"\b\d{8}T\d{6}Z-[0-9a-f]{8}\b")


def _read(path: Path) -> tuple[str | None, str | None]:
    try:
        return path.read_text(encoding="utf-8"), None
    except OSError as exc:
        return None, str(exc)


def check(root: Path = ROOT) -> list[str]:
    """Return unresolved live-roadmap batch references below *root*."""

    failures: list[str] = []
    roadmap_path = root / ROADMAP
    roadmap, error = _read(roadmap_path)
    if error:
        return [f"{ROADMAP.as_posix()}: cannot read: {error}"]
    assert roadmap is not None

    cited = sorted(set(BATCH_ID_RE.findall(roadmap)))
    if not cited:
        return []

    reviews_root = root / REVIEWS
    if not reviews_root.is_dir():
        return [f"{REVIEWS.as_posix()}: missing durable evidence directory"]

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
