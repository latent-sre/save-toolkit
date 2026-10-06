"""Probe-owned check that a design record fills every slot of the principal design-record contract.

Usage: python check_design_record.py <record.md>

The slots and the label rule restate skills/eng-ladder/references/principal.md ("Fill every slot;
write none rather than drop one" and "Label every load-bearing claim") so a candidate's edit to that
file cannot change what this oracle accepts. One matcher reads every label format: a second-level or
deeper heading, the first cell of a table row, an emphasised label, or a list item or plain line up
to its first colon (a list item may also be the label alone). After numbering, markup, and
parenthesised or bracketed asides are removed, a label names each slot for which one of its parts,
split at "and", "from", "for", commas, slashes, colons and semicolons, is exactly the slot's name or
an alias below, so "Decisions needed from the owner" names a slot and "Consumers ignore JSON" does not.
A label is never content: a heading is filled by the lines under it, a table row by its other cells,
and any other label by the text after it or the lines that follow. Counting stops at the next label
of any slot or at a heading that ends the label's section, and table header and separator rows are
not content. "none" counts as content. Entries in a Contents list are ignored. Exit 0 passes, 1
fails, 2 is a usage error.
"""

import re
import sys
from pathlib import Path

SLOTS = {
    "Problem and context": ("problem", "context"),
    "Goals / non-goals": ("goals", "non-goals"),
    "Options": ("options", "options considered"),
    "Recommendation": ("recommendation", "recommended", "recommended design", "chosen approach"),
    "Contracts and consumers": ("consumers",),
    "Failure modes": ("failure modes",),
    "Rollout and recovery": ("rollout", "recovery", "rollback"),
    "Verification": ("verification", "verification plan", "verification summary"),
    "Operational cost": ("operational cost",),
    "Decision needed": ("decision needed", "decisions needed"),
    "Assumptions": ("assumptions",),
    "Weakest point": ("weakest point",),
}
ALIASES = {alias: slot for slot, names in SLOTS.items() for alias in names}
LABELS = ("[verified]", "[sourced]", "[unverified]")
HEADING = re.compile(r"^\s*(#{1,6})\s+(.*)$")
CONTENTS = re.compile(r"^\s*#{2,6}\s+(table of )?contents\b", re.IGNORECASE)
MARKER = re.compile(r"^\s*(?:>\s*)*([-*+]\s+|\d+[.)]\s+)?")
EMPHASIS = re.compile(r"^(\*\*|__)(.+?)\1(.*)$")
COLON = re.compile(r"^((?:[^:(]|\([^)]*\))*):(.*)$")
ASIDES = re.compile(r"\([^()]*\)|\[[^\]]*\]|`")
NUMBERING = re.compile(r"^(?:\d+(?:\.\d+)*|[a-z])[.)]\s+")
PARTS = re.compile(r"\s*(?:[,;:/&]|\b(?:and|from|for)\b)\s*")
LONGEST_LABEL = 60
DECORATION = " \t*_:|>#.-–—"


def _level(line: str) -> int:
    match = HEADING.match(line)
    return len(match.group(1)) if match else 0


def _slots(label: str) -> set[str]:
    text = ASIDES.sub(" ", label.replace("**", "").replace("__", "")).strip(" *_:").lower()
    text = re.sub(r"\s+", " ", NUMBERING.sub("", text))
    if len(text) > LONGEST_LABEL:
        return set()
    return {ALIASES[part] for part in PARTS.split(text) if part in ALIASES}


def _header(lines: list[str], index: int) -> bool:
    following = lines[index + 1].strip() if index + 1 < len(lines) else ""
    return (lines[index].strip().startswith("|") and "-" in following
            and set(following) <= set("|-: "))


def _label(lines: list[str], index: int) -> tuple[set[str], str, str] | None:
    """(slots, kind, same-line content) when this line labels a slot, else None."""
    line = lines[index]
    heading = HEADING.match(line)
    if heading:
        slots = _slots(heading.group(2)) if len(heading.group(1)) >= 2 else set()
        return (slots, "heading", "") if slots else None
    if line.strip().startswith("|"):
        if _header(lines, index):
            return None
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        slots = _slots(cells[0])
        return (slots, "table", " ".join(cells[1:]).strip(DECORATION)) if slots else None
    marker = MARKER.match(line)
    body = line[marker.end():].strip()
    emphasis = EMPHASIS.match(body)
    colon = COLON.match(body)
    if emphasis:
        text, rest = emphasis.group(2), emphasis.group(3)
    elif colon:
        text, rest = colon.group(1), colon.group(2)
    elif marker.group(1):
        text, rest = body, ""
    else:
        return None
    slots = _slots(text)
    return (slots, "label", rest.strip(DECORATION)) if slots else None


def _filled(lines: list[str], index: int, kind: str, content: str) -> bool:
    if content:
        return True
    if kind == "table":
        return False
    level = _level(lines[index])
    for following in range(index + 1, len(lines)):
        following_level = _level(lines[following])
        if following_level and (not level or following_level <= level):
            return False
        if _label(lines, following):
            return False
        if following_level or _header(lines, following) or not lines[following].strip(DECORATION):
            continue
        return True
    return False


def _filled_slots(lines: list[str]) -> set[str]:
    filled, contents_level = set(), 0
    for index, line in enumerate(lines):
        level = _level(line)
        if contents_level and level and level <= contents_level:
            contents_level = 0
        if CONTENTS.match(line):
            contents_level = level
            continue
        found = None if contents_level else _label(lines, index)
        if found and _filled(lines, index, found[1], found[2]):
            filled |= found[0]
    return filled


def problems(text: str) -> list[str]:
    filled = _filled_slots(text.splitlines())
    found = [f"missing or empty slot: {slot}" for slot in SLOTS if slot not in filled]
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
