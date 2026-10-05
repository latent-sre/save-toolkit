"""Probe-owned check that a design record fills every slot of the principal design-record contract.

Usage: python check_design_record.py <record.md>

The slots and the label rule restate skills/eng-ladder/references/principal.md ("Fill every slot;
write none rather than drop one" and "Label every load-bearing claim") so a candidate's edit to that
file cannot change what this oracle accepts. A slot counts on a structural line: a heading, list
item, table row, quote, or emphasised label containing the slot's name near its start, or a plain
line that opens with the name followed by a colon. Exit 0 passes, 1 fails, 2 is a usage error.
"""

import re
import sys
from pathlib import Path

SLOTS = {
    "Problem and context": r"(problem|context)",
    "Goals / non-goals": r"goals",
    "Options": r"options",
    "Recommendation": r"(recommend(ation|ed)?|chosen (approach|option)|proposed (approach|design|option))",
    "Contracts and consumers": r"(contracts?|consumers)",
    "Failure modes": r"failure modes?",
    "Rollout and recovery": r"(rollout|recovery|rollback)",
    "Verification": r"verification",
    "Operational cost": r"operational costs?",
    "Decision needed": r"decisions? needed",
    "Assumptions": r"assumptions",
    "Weakest point": r"weakest point",
}
LABELS = ("[verified]", "[sourced]", "[unverified]")
MARKER = re.compile(r"^\s*(#{1,6}\s|\*\*|__|\||>|[-*+]\s|\d+[.)]\s)")
NEAR_START = 60


def _has_slot(lines: list[str], pattern: str) -> bool:
    word = re.compile(rf"\b{pattern}\b", re.IGNORECASE)
    plain_label = re.compile(rf"^\s*{pattern}\b[^:\n]{{0,30}}:", re.IGNORECASE)
    for line in lines:
        if MARKER.match(line):
            body = MARKER.sub("", line, count=1).lstrip(" *_#|>")
            match = word.search(body)
            if match and match.start() <= NEAR_START:
                return True
        elif plain_label.match(line):
            return True
    return False


def problems(text: str) -> list[str]:
    lines = text.splitlines()
    found = [f"missing slot: {slot}" for slot, pattern in SLOTS.items()
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
