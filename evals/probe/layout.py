"""Where an iteration keeps its saved runs, and how a folder's number reads back.

    <iteration>/eval-<scenario>/<label>/run-N/                  slot N's published attempt
    <iteration>/eval-<scenario>/<label>/attempts/run-N/<k>/     attempt k of slot N, superseded or incomplete
    <iteration>/eval-<scenario>/<label>/.run-N-attempt-<hex>/   an attempt being written
    <iteration>/eval-<scenario>/<label>/.run-N-previous-<hex>/  the run it replaces, while it is published
    <run>/assessments/<k>/                                      regrade k, beside the run's own grade

The runner, the regrade and rescore, the run comparison and the turn-count summary all find runs
through this module, so they agree on what a run is.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from pathlib import Path

CASE_PREFIX = "eval-"
SLOT_PREFIX = "run-"
# A hidden attempt folder names the slot it was written for: `.run-N-attempt-...`, `.run-N-previous-...`.
HIDDEN_SLOT = re.compile(r"^\.run-([1-9][0-9]*)-")
_PUBLISHED = re.compile(r"run-\d+")


def case_dir(iteration: Path, scenario_id: str) -> Path:
    return iteration / f"{CASE_PREFIX}{scenario_id}"


def case_dirs(iteration: Path) -> list[Path]:
    """Every scenario folder in an iteration, in name order."""
    return sorted(iteration.glob(f"{CASE_PREFIX}*"))


def case_id(folder: Path) -> str:
    """The scenario a case folder holds."""
    return folder.name.removeprefix(CASE_PREFIX)


def run_dir(iteration: Path, scenario_id: str, label: str, slot: int) -> Path:
    """Where slot `slot` of a label publishes its attempt."""
    return case_dir(iteration, scenario_id) / label / f"{SLOT_PREFIX}{slot}"


def attempts_dir(label_dir: Path) -> Path:
    """Where a label keeps the attempts that are not its published runs, as attempts/run-N/<k>/."""
    return label_dir / "attempts"


def history_dir(run: Path) -> Path:
    """Where a slot keeps its superseded and incomplete attempts; no run-N glob beside it matches it."""
    return attempts_dir(run.parent) / run.name


def attempt_dir(run: Path, token: str) -> Path:
    """The hidden sibling an attempt is written in before it is published as `run`."""
    return run.with_name(f".{run.name}-attempt-{token}")


def backup_dir(run: Path, token: str) -> Path:
    """The hidden sibling a published run moves to while its replacement is published."""
    return run.with_name(f".{run.name}-previous-{token}")


def hidden_slot(name: str) -> int | None:
    """The slot a hidden attempt folder was written for, or None when its name says none."""
    match = HIDDEN_SLOT.match(name)
    return int(match.group(1)) if match else None


def number(name: str, prefix: str = "") -> int | None:
    """The number in a folder name `<prefix><N>` as the runner writes it (`run-1`, never `run-01` or
    `run-0`, so two folders cannot claim one slot), or None."""
    digits = name.removeprefix(prefix) if name.startswith(prefix) else ""
    return int(digits) if digits.isascii() and digits.isdigit() and digits == str(int(digits)) != "0" else None


def numbered(parent: Path, prefix: str = "") -> list[tuple[Path, int]]:
    """The folders under `parent` named `<prefix><N>`, in numeric order on every host."""
    found = []
    if parent.is_dir():
        for child in parent.iterdir():
            found_number = number(child.name, prefix)
            if child.is_dir() and found_number is not None:
                found.append((child, found_number))
    return sorted(found, key=lambda item: item[1])


def kept_attempts(label_dir: Path) -> Iterator[tuple[Path, int, int]]:
    """Each kept attempt of a label as (folder, slot, attempt number)."""
    for history, slot in numbered(attempts_dir(label_dir), SLOT_PREFIX):
        for kept, attempt in numbered(history):
            yield kept, slot, attempt


def published_slot(name: str) -> int | None:
    """The slot a folder beside the label's published runs holds, or None for any other folder."""
    return int(name.removeprefix(SLOT_PREFIX)) if _PUBLISHED.fullmatch(name) else None


def taken(parent: Path) -> set[int]:
    """The numbers already used under `parent`: kept attempts, or a run's assessments."""
    return {int(child.name) for child in parent.iterdir() if child.name.isdigit()} if parent.is_dir() else set()


def next_number(parent: Path) -> int:
    """The number the next kept attempt or assessment under `parent` takes."""
    return max(taken(parent), default=0) + 1


def live_grade(run: Path) -> Path:
    """The run's live grade: `grading.original.json` where an older runner regraded the run in place."""
    original = run / "grading.original.json"
    return original if original.exists() else run / "grading.json"


def run_key(row: Mapping[str, object]) -> tuple[object, object, object]:
    """What names one run in a summary or rescore row: its scenario, label and slot."""
    return row.get("scenario"), row.get("label"), row.get("run")


def run_name(scenario: object, label: object, slot: object) -> str:
    """A run as the command line reports it."""
    return f"{CASE_PREFIX}{scenario} {label}/{SLOT_PREFIX}{slot}"
