#!/usr/bin/env python3
"""Gate A weight totals -- three zero-sum ceilings on repository growth.

Measures three totals against the ceilings in ``scripts/weights.json``: the summed line count of
every ``*.py`` under ``evals/`` (tests included), the summed byte count of every file under
``skills/``, and the summed byte count of ``agents/*.md``. Growing past a ceiling is a reviewed
decision made by raising it in the same diff that earns it -- never a silent side effect of an
unrelated change.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEIGHTS_PATH = ROOT / "scripts" / "weights.json"


def load_weights() -> dict[str, int]:
    return json.loads(WEIGHTS_PATH.read_text(encoding="utf-8"))


def _count_lines(path: Path) -> int:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return sum(1 for _ in handle)


def measure(root: Path = ROOT) -> dict[str, int]:
    evals_lines = sum(_count_lines(path) for path in sorted((root / "evals").rglob("*.py")))
    skills_bytes = sum(
        path.stat().st_size for path in sorted((root / "skills").rglob("*")) if path.is_file()
    )
    agents_bytes = sum(path.stat().st_size for path in sorted((root / "agents").glob("*.md")))
    return {
        "evals_python_lines": evals_lines,
        "skills_bytes": skills_bytes,
        "agents_bytes": agents_bytes,
    }


def evaluate(
    measured: dict[str, int], ceilings: dict[str, int]
) -> tuple[list[tuple[str, int, int, int]], list[str]]:
    """Pure comparison, split out from I/O so it is directly testable."""
    rows: list[tuple[str, int, int, int]] = []
    failed: list[str] = []
    for name, ceiling in ceilings.items():
        value = measured.get(name, 0)
        rows.append((name, value, ceiling, ceiling - value))
        if value > ceiling:
            failed.append(name)
    return rows, failed


def main() -> int:
    ceilings = load_weights()
    rows, failed = evaluate(measure(), ceilings)

    width = max(len(name) for name, *_ in rows)
    print("%-*s  %10s  %10s  %10s" % (width, "Total", "measured", "ceiling", "headroom"))
    for name, value, ceiling, headroom in rows:
        flag = "FAIL" if value > ceiling else "ok"
        print("%-*s  %10d  %10d  %10d  %s" % (width, name, value, ceiling, headroom, flag))

    if failed:
        print(
            "\ncheck_weight: FAIL -- over ceiling: %s\n"
            "Raising a ceiling is a reviewed decision made in the same diff that earns it; "
            "edit scripts/weights.json there, not here." % ", ".join(failed)
        )
        return 1
    print("\ncheck_weight: PASS -- %d/%d totals within ceiling" % (len(rows), len(rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
