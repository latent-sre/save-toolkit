#!/usr/bin/env python3
"""Summarize a drill's lane runs: cost, turns, duration, and missing outputs.

Reads every ``*.meta.json`` under a single run directory and prints the Markdown table the retro
template expects, plus the gaps a reader should not have to notice for themselves — a lane that
timed out, exited non-zero, or produced no result text.

Usage::

    python drill_report.py runs/ --run-id drill-20260825    # table + gaps
    python drill_report.py runs/ --run-id drill-20260825 --json  # same data as JSON

Pass exactly one ``--run-id`` to scope the report to that run and avoid silently merging
evidence across separate runs.  Standard library only.  Python 3.11+.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys


def load(run_dir: pathlib.Path) -> list[dict]:
    rows = []
    for meta_path in sorted(run_dir.rglob("*.meta.json")):
        try:
            row = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            rows.append({"step": meta_path.stem, "lane": "UNREADABLE", "error": str(exc)})
            continue
        row["has_result"] = meta_path.with_suffix("").with_suffix(".md").exists()
        # Preserve attempt context from the directory layout when the meta doesn't carry it.
        if "attempt_id" not in row:
            row["attempt_id"] = meta_path.parent.name
        rows.append(row)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("runs_dir", type=pathlib.Path)
    parser.add_argument("--run-id", required=True, help="run directory name under runs_dir (e.g. drill-20260825)")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of the Markdown table")
    args = parser.parse_args(argv)

    run_dir = args.runs_dir / args.run_id
    if not run_dir.is_dir():
        print(f"run directory not found: {run_dir}", file=sys.stderr)
        return 1

    rows = load(run_dir)
    if not rows:
        print(f"no lane metadata found under {run_dir}", file=sys.stderr)
        return 1

    total_cost = sum(r.get("total_cost_usd") or 0.0 for r in rows)
    total_turns = sum(r.get("num_turns") or 0 for r in rows)
    total_s = sum(r.get("duration_s") or 0.0 for r in rows)

    if args.json:
        print(json.dumps({"run_id": args.run_id, "runs": rows, "totals": {"cost_usd": round(total_cost, 2), "turns": total_turns, "duration_s": round(total_s, 1)}}, indent=2))
        return 0

    print("| Run | Attempt | Step | Lane | Agent / skill | Turns | Time | Cost |")
    print("|---|---|---|---|---|---|---|---|")
    for row in rows:
        agent = row.get("agent") or "main session + skill"
        turns = row.get("num_turns") or 0
        seconds = row.get("duration_s") or 0.0
        cost = row.get("total_cost_usd") or 0.0
        run_id = row.get("run_id", args.run_id)
        attempt_id = row.get("attempt_id", "?")
        print(f"| {run_id} | {attempt_id} | {row.get('step', '?')} | {row.get('lane', '?')} | {agent} | {turns} | {seconds:.0f} s | ${cost:.2f} |")
    print(f"| — | — | — | **total** | {len(rows)} runs | {total_turns} | {total_s / 60:.0f} min | **${total_cost:.2f}** |")

    gaps = []
    for row in rows:
        label = f"{row.get('step', '?')}-{row.get('lane', '?')}"
        if row.get("exit_code") not in (0, None):
            gaps.append(f"{label}: exit {row['exit_code']}")
        if row.get("is_error"):
            gaps.append(f"{label}: the CLI reported is_error")
        if not row.get("has_result"):
            gaps.append(f"{label}: no result text saved — the lane returned nothing (record it, do not silently drop it)")
    if gaps:
        print("\n**Gaps to carry into the retro** (a lane that returns nothing is a finding, not a rerun):")
        for gap in gaps:
            print(f"- {gap}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
