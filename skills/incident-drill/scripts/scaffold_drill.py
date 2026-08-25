#!/usr/bin/env python3
"""Materialize a drill working directory from a scenario's packed documents.

A scenario ships as three parseable Markdown documents — ``service.md``, ``evidence.md``, and
``packets.md`` — each a sequence of ``## <relative path>`` sections with a fenced payload. This
script writes them back out as files, builds the two-release git history the scenario's
``_previous-release.json`` section specifies, and creates the directories, prod-state file, and
runbook copy a drill needs.

Usage::

    python scaffold_drill.py <scenario-dir> <drill-dir> [--python <interpreter>] [--no-git]

Then follow the scenario's setup notes for the virtualenv and the preflight lane.

Standard library only. Python 3.11+.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

SECTION = re.compile(r"^## (?P<path>\S.*?)\s*$")
FENCE = re.compile(r"^(?P<ticks>`{3,})(?P<lang>[A-Za-z0-9_+-]*)\s*$")


def parse_pack(path: pathlib.Path) -> dict[str, str]:
    """Return {relative path: payload} for one packed document.

    Fence-aware: a ``## `` line inside a fenced payload is content, not a new section, and payloads
    are fenced with a run longer than anything they contain.
    """
    sections: dict[str, str] = {}
    current: str | None = None
    ticks: str | None = None
    buffer: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if ticks is None:
            match = SECTION.match(line)
            if match:
                current = match.group("path")
                continue
            fence = FENCE.match(line)
            if fence and current is not None:
                ticks = fence.group("ticks")
                buffer = []
                continue
        else:
            if line.strip() == ticks:
                sections[current] = "\n".join(buffer) + "\n"
                current, ticks, buffer = None, None, []
                continue
            buffer.append(line)
    if ticks is not None:
        raise SystemExit(f"{path.name}: unterminated fence in section {current!r}")
    return sections


def write_files(files: dict[str, str], root: pathlib.Path) -> int:
    for relative, payload in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8")
    return len(files)


def apply_edits(root: pathlib.Path, edits: list[dict]) -> None:
    for edit in edits:
        target = root / edit["path"]
        text = target.read_text(encoding="utf-8")
        if "find" in edit:
            if edit["find"] not in text:
                raise SystemExit(f"{edit['path']}: previous-release edit did not match; the pack and the spec disagree")
            text = text.replace(edit["find"], edit["replace"])
        elif "drop_from" in edit:
            lines = text.splitlines(keepends=True)
            start = next((i for i, l in enumerate(lines) if l.startswith(edit["drop_from"])), None)
            stop = next((i for i, l in enumerate(lines) if l.startswith(edit["drop_until"])), None)
            if start is None or stop is None or stop < start:
                raise SystemExit(f"{edit['path']}: drop_from/drop_until did not bracket a section")
            text = "".join(lines[:start] + lines[stop:])
        target.write_text(text, encoding="utf-8")


def git(root: pathlib.Path, *args: str, date: str | None = None) -> None:
    env = None
    if date:
        import os
        env = dict(os.environ, GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True, env=env)


def build_history(service: pathlib.Path, files: dict[str, str], spec: dict) -> None:
    previous, current = spec["previous"], spec["current"]
    git(service, "init", "-q", "-b", "main")
    git(service, "config", "user.email", "drill@example.internal")
    git(service, "config", "user.name", "drill fixture")
    apply_edits(service, previous["edits"])
    git(service, "add", "-A")
    git(service, "commit", "-q", "-m", previous["message"], date=previous["date"])
    git(service, "tag", previous["tag"])
    write_files(files, service)          # restore the shipped pack: that restoration is the release
    git(service, "add", "-A")
    git(service, "commit", "-q", "-m", current["message"], date=current["date"])
    git(service, "tag", current["tag"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scenario_dir", type=pathlib.Path)
    parser.add_argument("drill_dir", type=pathlib.Path)
    parser.add_argument("--python", default="{{PYTHON}}", help="interpreter path substituted into packets")
    parser.add_argument("--no-git", action="store_true", help="write files without building the release history")
    args = parser.parse_args(argv)

    if args.drill_dir.exists() and any(args.drill_dir.iterdir()):
        raise SystemExit(f"{args.drill_dir} is not empty — a drill needs a fresh directory")

    service_pack = parse_pack(args.scenario_dir / "service.md")
    spec_raw = service_pack.pop("_previous-release.json", None)
    evidence = parse_pack(args.scenario_dir / "evidence.md")
    packets = parse_pack(args.scenario_dir / "packets.md")

    service = args.drill_dir / "service"
    count = write_files(service_pack, service)
    write_files(evidence, args.drill_dir / "evidence")
    write_files({name: text.replace("{{PYTHON}}", args.python) for name, text in packets.items()},
                args.drill_dir / "prompts")
    for sub in ("runs", "docs-out/postmortems", "docs-out/runbooks", "docs-out/observability"):
        (args.drill_dir / sub).mkdir(parents=True, exist_ok=True)

    runbook = service / "docs/runbook.md"
    if runbook.exists():
        (args.drill_dir / "docs-out/runbooks" / runbook.name).write_text(
            runbook.read_text(encoding="utf-8"), encoding="utf-8")

    prod_state = args.drill_dir / "prod-state.json"
    if not prod_state.exists():
        prod_state.write_text(json.dumps({
            "_note": "Synthetic production state. ONLY the human executor edits this file, and only "
                     "after an approved production-change-gate packet. Agents never write it.",
            "changes": [],
        }, indent=2) + "\n", encoding="utf-8")

    if not args.no_git:
        if spec_raw is None:
            print("service.md has no _previous-release.json section — skipping history", file=sys.stderr)
        else:
            build_history(service, service_pack, json.loads(spec_raw))

    print(f"drill directory ready: {args.drill_dir}")
    print(f"  service files: {count}   evidence: {len(evidence)}   packets: {len(packets)}")
    if args.python == "{{PYTHON}}":
        print("  NOTE: packets still contain {{PYTHON}} — pass --python <interpreter> or substitute before dispatch")
    print("  next: create the scratch virtualenv, install service requirements, run the preflight smoke lane")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
