"""Probe-owned check that a design record fills every slot of the principal design-record contract.

Usage: python check_design_record.py <record.md>

The slots and the label rule restate skills/eng-ladder/references/principal.md ("Fill every slot;
write none rather than drop one" and "Label every load-bearing claim") so a candidate's edit to that
file cannot change what this oracle accepts. A slot counts on a structural line: a second-level or
deeper heading, list item, table row, quote, or emphasised label containing the slot's name near its
start, or a plain line that opens with the name followed by a colon. Entries in a Contents list do
not count. A slot must also be filled: text in its section, cell, or label, where "none" counts.
The contracts slot must name consumers. Exit 0 passes, 1 fails, 2 is a usage error.
"""

import re
import sys
from pathlib import Path

SLOTS = {
    "Problem and context": r"(problem|context)",
    "Goals / non-goals": r"goals",
    "Options": r"options",
    "Recommendation": r"(recommend(ation|ed)?|chosen (approach|option)|proposed (approach|design|option))",
    "Contracts and consumers": r"consumers?",
    "Failure modes": r"failure modes?",
    "Rollout and recovery": r"(rollout|recovery|rollback)",
    "Verification": r"verification",
    "Operational cost": r"operational costs?",
    "Decision needed": r"decisions? needed",
    "Assumptions": r"assumptions",
    "Weakest point": r"weakest point",
}
LABELS = ("[verified]", "[sourced]", "[unverified]")
# A level-1 heading is the document's title, not a slot, so matching starts at level 2.
MARKER = re.compile(r"^\s*(#{2,6}\s|\*\*|__|\||>|[-*+]\s|\d+[.)]\s)")
HEADING = re.compile(r"^\s*(#{1,6})\s")
CONTENTS = re.compile(r"^\s*#{2,6}\s+(table of )?contents\b", re.IGNORECASE)
NEAR_START = 60
DECORATION = " \t*_:|>#.-–—"


def _level(line: str) -> int:
    match = HEADING.match(line)
    return len(match.group(1)) if match else 0


def _slot_end(line: str, pattern: str) -> int | None:
    """Where the slot's name ends on a structural line naming it, or None."""
    if MARKER.match(line):
        body = MARKER.sub("", line, count=1).lstrip(" *_#|>")
        match = re.search(rf"\b{pattern}\b", body, re.IGNORECASE)
        if match and match.start() <= NEAR_START:
            return len(line) - len(body) + match.end()
        return None
    match = re.match(rf"^\s*{pattern}\b[^:\n]{{0,30}}:", line, re.IGNORECASE)
    return match.end() if match else None


def _names_a_slot(line: str) -> bool:
    return any(_slot_end(line, pattern) is not None for pattern in SLOTS.values())


def _filled(lines: list[str], index: int, end: int) -> bool:
    if lines[index][end:].strip(DECORATION):
        return True
    level = _level(lines[index])
    for following in lines[index + 1:]:
        following_level = _level(following)
        if following_level and (not level or following_level <= level):
            return False
        if not following.strip() or following_level:
            continue
        if not level and _names_a_slot(following):
            return False
        if following.strip(DECORATION):
            return True
    return False


def _has_slot(lines: list[str], pattern: str) -> bool:
    contents_level = 0
    for index, line in enumerate(lines):
        level = _level(line)
        if contents_level and level and level <= contents_level:
            contents_level = 0
        if CONTENTS.match(line):
            contents_level = level
            continue
        if contents_level:
            continue
        end = _slot_end(line, pattern)
        if end is not None and _filled(lines, index, end):
            return True
    return False


def problems(text: str) -> list[str]:
    lines = text.splitlines()
    found = [f"missing or empty slot: {slot}" for slot, pattern in SLOTS.items()
             if not _has_slot(lines, pattern)]
    if not any(label in text for label in LABELS):
        found.append("no evidence label: [verified], [sourced], or [unverified]")
    return found


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_design_record.py <record.md>")
        return 2
    path = Path(argv[1])
    if not path.is_file():
        print(f"{path}: missing")
        return 1
    found = problems(path.read_text(encoding="utf-8", errors="replace"))
    for problem in found:
        print(problem)
    print("design record: " + ("FAIL" if found else "PASS"))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
