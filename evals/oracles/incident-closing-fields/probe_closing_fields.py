"""Probe-owned oracle for the incident advisor's reply-closing contract.

Usage: python probe_closing_fields.py <response.md> <expected>
Exit 0 when the reply closes as expected, 1 with a reason when it does not.

The rule, made mechanical: once an incident is being worked the reply ends with the three fields
Applied / Open / Next; a checkpoint trigger — a transition, handover or requested recap, a change of
direction, an attempted or applied mitigation, or accumulated branches — replaces them with the
checkpoint's fields; a question with no live incident carries neither. Two distinct field names are
required so that a reply merely using the word "Next" in prose does not read as the fields.

Field names are matched at line start under any markdown dress — heading, bold, list marker, table
cell — with or without a trailing colon. A checkpoint written as `### Follow-ups` is a checkpoint;
requiring a colon undercounts it, which is how a real handover regression was once read as an
absence.

<expected> is one of: fields, checkpoint, both, none, fields-or-both, checkpoint-or-both.
"""
import re
import sys

CLOSING_FIELDS = ("Applied", "Open", "Next")
CHECKPOINT_FIELDS = ("Assessment", "Checked", "Actions", "Follow-ups")
# Leading markdown dress: heading hashes, bold/italic stars, list markers, table pipes, quotes.
DRESS = r"[#*_\-+>|\s]{0,8}"
EXPECTED = ("fields", "checkpoint", "both", "none", "fields-or-both", "checkpoint-or-both")


def _pattern(fields):
    names = "|".join(f.replace("-", "-?") for f in fields)
    return re.compile(rf"^{DRESS}(?P<name>{names})\b[*_]{{0,2}}\s*:?", re.M | re.I)


def _present(text, fields):
    """Distinct field names found at line start. Two or more means the block is really there."""
    found = set()
    for m in _pattern(fields).finditer(text):
        found.add(m.group("name").lower().replace("-", ""))
    return found


def classify(text):
    fields = len(_present(text, CLOSING_FIELDS)) >= 2
    checkpoint = len(_present(text, CHECKPOINT_FIELDS)) >= 2
    if fields and checkpoint:
        return "both"
    if fields:
        return "fields"
    if checkpoint:
        return "checkpoint"
    return "none"


def check(text, expected):
    """Return (ok, reason). `expected` may name one class or an allowed pair."""
    if expected not in EXPECTED:
        return False, f"unknown expected class {expected!r}; one of {', '.join(EXPECTED)}"
    actual = classify(text)
    allowed = expected.split("-or-")
    if actual in allowed:
        return True, actual
    return False, (
        f"reply closes as {actual!r}, expected {' or '.join(repr(a) for a in allowed)}; "
        f"closing fields present: {sorted(_present(text, CLOSING_FIELDS)) or 'none'}; "
        f"checkpoint fields present: {sorted(_present(text, CHECKPOINT_FIELDS)) or 'none'}"
    )


def main():
    if len(sys.argv) != 3:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    text = open(sys.argv[1], "rb").read().decode("utf-8", "replace")
    ok, reason = check(text, sys.argv[2])
    print(("ok: " if ok else "FAIL: ") + reason)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
