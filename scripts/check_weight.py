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
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEIGHTS_PATH = ROOT / "scripts" / "weights.json"


def load_weights() -> dict[str, int]:
    return json.loads(WEIGHTS_PATH.read_text(encoding="utf-8"))


def _count_lines(path: Path) -> int:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return sum(1 for _ in handle)


def _tracked_files(root: Path, prefix: str) -> list[Path]:
    """Files git tracks under *prefix* and still present on disk; without git, every file except
    bytecode caches.

    The first recorded ceilings were measured over `rglob`, which counted 40 KB of untracked
    `__pycache__` bytecode that tests leave beside skill scripts -- a total that moved with whether
    the suite had run, and that a `git clean` could lower without touching a skill.

    `git ls-files` only works if *root* is the toplevel of the repository it resolves to; a
    Git-less copy of the toolkit sitting untracked inside another repository would otherwise get
    that enclosing repository's `ls-files`, which lists none of these paths and measures zero. And
    `ls-files` lists the index, not the working tree, so a tracked file deleted or renamed without
    `git rm`/`git add` is filtered out here rather than raising when `measure` tries to stat it.
    """
    same_repo = False
    try:
        toplevel = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, encoding="utf-8", check=True,
        )
        same_repo = Path(toplevel.stdout.strip()).resolve() == root.resolve()
        if same_repo:
            proc = subprocess.run(
                ["git", "-C", str(root), "ls-files", "-z", "--", prefix],
                capture_output=True, text=True, encoding="utf-8", check=True,
            )
    except (OSError, subprocess.CalledProcessError):
        same_repo = False
    if not same_repo:
        return [
            path for path in sorted((root / prefix).rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts
        ]
    tracked = []
    for name in proc.stdout.split("\0"):
        if not name:
            continue
        path = root / name
        if path.is_file():
            tracked.append(path)
    return tracked


def measure(root: Path = ROOT) -> dict[str, int]:
    evals_lines = sum(
        _count_lines(path) for path in _tracked_files(root, "evals") if path.suffix == ".py"
    )
    skills_bytes = sum(path.stat().st_size for path in _tracked_files(root, "skills"))
    agents_dir = root / "agents"
    agents_bytes = sum(
        path.stat().st_size
        for path in _tracked_files(root, "agents")
        if path.suffix == ".md" and path.parent == agents_dir
    )
    return {
        "evals_python_lines": evals_lines,
        "skills_bytes": skills_bytes,
        "agents_bytes": agents_bytes,
    }


def ceiling_problem(measured: dict[str, int], ceilings: dict[str, int]) -> str | None:
    """Why the configured ceilings are not the measured totals, or None.

    ``evaluate`` iterates the ceilings and treats an absent measured name as zero, so deleting or
    misspelling one key silently retires that ceiling while the report still says every configured
    total is within bounds -- a green Gate A measuring less than it claims to.
    """
    unmeasured = sorted(set(ceilings) - set(measured))
    unbounded = sorted(set(measured) - set(ceilings))
    if not unmeasured and not unbounded:
        return None
    return (
        "scripts/weights.json must name exactly the measured totals (%s)" % ", ".join(sorted(measured))
        + ("; no ceiling for: %s" % ", ".join(unbounded) if unbounded else "")
        + ("; not a measured total: %s" % ", ".join(unmeasured) if unmeasured else "")
    )


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
    measured = measure()
    problem = ceiling_problem(measured, ceilings)
    if problem:
        print("check_weight: FAIL -- " + problem)
        return 1
    rows, failed = evaluate(measured, ceilings)

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
