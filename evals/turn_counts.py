"""Summarize the turns saved trials took, per scenario, to set each scenario's `max_turns`.

    python evals/turn_counts.py RUNS_ROOT [--scenario ID ...]

Reads `timing.json` from every published trial under RUNS_ROOT (`<iteration>/eval-<scenario>/<label>/run-N/`)
and every retained attempt (`<label>/attempts/run-N/<k>/`): a replaced or unpublished attempt can hold
the highest count or the longest run. Folders are read as the runner's layout names them
(probe/layout.py), so an operator's copy such as `run-1-old` is not a trial. It prints, per scenario,
how many records gave a turn count, their minimum, median and maximum, how many gave none, how many
were retained attempts, and the longest trial in seconds. A native conversation's count sums its
invocations and its stream's last count is not an exact provider-turn count, so read it as an upper
estimate. A named scenario with no saved trial is listed with zero trials rather than left out.

Exit 0 once the report is printed and 3 when RUNS_ROOT is not a directory. It reads and grades
nothing else, so, like the run comparison, it sits outside the runner's identity.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path

from probe import layout


@dataclass
class Observed:
    turns: list[int] = field(default_factory=list)
    unknown: int = 0
    retained: int = 0
    longest_seconds: float | None = None


def _number(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None


def _timings(root: Path) -> list[tuple[str, bool, Path]]:
    """(scenario, retained, timing.json) for every published run and every retained attempt, as the
    runner's layout names them."""
    found = []
    for case_dir in (path for path in root.glob(f"**/{layout.CASE_PREFIX}*") if path.is_dir()):
        scenario = layout.case_id(case_dir)
        for label_dir in (child for child in case_dir.iterdir() if child.is_dir()):
            found += [(scenario, False, run) for run, _ in layout.numbered(label_dir, layout.SLOT_PREFIX)]
            found += [(scenario, True, kept) for kept, _, _ in layout.kept_attempts(label_dir)]
    return sorted(
        (scenario, kept, folder / "timing.json")
        for scenario, kept, folder in found
        if (folder / "timing.json").exists()
    )


def collect(root: Path, wanted: set[str]) -> dict[str, Observed]:
    """Turn counts per scenario from every saved trial under root, limited to `wanted` when given."""
    observed: dict[str, Observed] = {name: Observed() for name in wanted}
    for scenario, retained, timing in _timings(root):
        if wanted and scenario not in wanted:
            continue
        entry = observed.setdefault(scenario, Observed())
        entry.retained += retained
        try:
            data = json.loads(timing.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = None
        record = data if isinstance(data, dict) else {}
        turns = record.get("num_turns")
        if type(turns) is int and turns >= 0:
            entry.turns.append(turns)
        else:
            entry.unknown += 1
        seconds = _number(record.get("trial_duration_seconds"))
        if seconds is not None:
            entry.longest_seconds = max(seconds, entry.longest_seconds or 0.0)
    return observed


def report(observed: dict[str, Observed]) -> str:
    rows = [("scenario", "trials", "min", "median", "max", "no count", "retained", "longest s")]
    for scenario, entry in sorted(observed.items()):
        counts = entry.turns
        rows.append(
            (
                scenario,
                str(len(counts)),
                str(min(counts)) if counts else "-",
                f"{statistics.median(counts):g}" if counts else "-",
                str(max(counts)) if counts else "-",
                str(entry.unknown),
                str(entry.retained),
                f"{entry.longest_seconds:g}" if entry.longest_seconds is not None else "-",
            )
        )
    widths = [max(len(row[column]) for row in rows) for column in range(len(rows[0]))]
    return "\n".join(
        "  ".join(cell.ljust(width) for cell, width in zip(row, widths, strict=True)).rstrip() for row in rows
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize saved trials' turn counts per scenario.")
    parser.add_argument("runs_root", type=Path, help="a run folder or the whole .eval-runs tree")
    parser.add_argument("--scenario", action="append", default=[], help="limit to this scenario id (repeatable)")
    args = parser.parse_args(argv)
    if not args.runs_root.is_dir():
        print(f"{args.runs_root}: not a directory", file=sys.stderr)
        return 3
    print(report(collect(args.runs_root, set(args.scenario))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
