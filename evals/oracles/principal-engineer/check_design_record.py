"""Probe-owned check that a design record fills every slot of the principal design-record contract.

Usage: python check_design_record.py <record.md>

The slots and the label rule restate skills/eng-ladder/references/principal.md ("Fill every slot;
write none rather than drop one" and "Label every load-bearing claim") so a candidate's edit to that
file cannot change what this oracle accepts. A slot is named by a label: a second-level or deeper
heading, the first cell of a table row, an emphasised label, or a list item or plain line that
starts with the slot's name. The label itself is never content: a heading is filled by the lines
under it, a table row by its other cells, and any other label by the text after it or the lines
that follow before the next slot. "none" counts as content. Entries in a Contents list are ignored,
and the contracts slot must name consumers. Exit 0 passes, 1 fails, 2 is a usage error.
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
HEADING = re.compile(r"^\s*(#{1,6})\s+(.*)$")
CONTENTS = re.compile(r"^\s*#{2,6}\s+(table of )?contents\b", re.IGNORECASE)
MARKERS = re.compile(r"^\s*(?:>\s*)*(?:[-*+]\s+|\d+[.)]\s+)?")
EMPHASIS = re.compile(r"^(\*\*|__)(.+?)\1(.*)$")
NUMBERING = re.compile(r"^\d+[.)]\s+")
NEAR_START = 60
DECORATION = " \t*_:|>#.-–—"


def _level(line: str) -> int:
    match = HEADING.match(line)
    return len(match.group(1)) if match else 0


def _near_start(text: str, pattern: str) -> bool:
    match = re.search(rf"\b{pattern}\b", text, re.IGNORECASE)
    return bool(match) and match.start() <= NEAR_START


def _at_start(text: str, pattern: str) -> bool:
    return re.match(rf"\s*{pattern}\b", text, re.IGNORECASE) is not None


def _label(line: str, pattern: str) -> tuple[str, str] | None:
    """(kind, same-line content) when this line labels the slot, else None. Never returns the label."""
    heading = HEADING.match(line)
    if heading:
        text = NUMBERING.sub("", heading.group(2))
        return ("heading", "") if len(heading.group(1)) >= 2 and _near_start(text, pattern) else None
    stripped = line.strip()
    if stripped.startswith("|"):
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if cells and _near_start(cells[0].strip("*_ "), pattern):
            return "table", " ".join(cells[1:]).strip(DECORATION)
        return None
    body = MARKERS.sub("", line, count=1)
    marked = body != line.lstrip()
    emphasis = EMPHASIS.match(body.strip())
    if emphasis:
        return ("label", emphasis.group(3).strip(DECORATION)) if _near_start(emphasis.group(2), pattern) else None
    colon = body.find(":")
    if 0 < colon <= NEAR_START + 30 and _at_start(body[:colon], pattern):
        return "label", body[colon + 1:].strip(DECORATION)
    if marked and _at_start(body, pattern):
        return "label", ""
    return None


def _names_a_slot(line: str) -> bool:
    return any(_label(line, pattern) is not None for pattern in SLOTS.values())


def _filled(lines: list[str], index: int, kind: str, content: str) -> bool:
    if content:
        return True
    if kind == "table":
        return False
    level = _level(lines[index])
    for following in lines[index + 1:]:
        following_level = _level(following)
        if following_level and (kind != "heading" or following_level <= level):
            return False
        if not following.strip() or following_level:
            continue
        if kind != "heading" and _names_a_slot(following):
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
        found = _label(line, pattern)
        if found and _filled(lines, index, *found):
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
