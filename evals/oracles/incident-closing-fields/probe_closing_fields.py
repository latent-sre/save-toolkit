"""Probe-owned oracle for the incident advisor's reply-closing contract.

Usage: python probe_closing_fields.py <response.md> <expected>
Exit 0 when the reply closes as expected, 1 with a reason when it does not.

classify() reports rough label presence, not completeness or closure. check()
requires a complete terminal board: Impact / Open / Checked / Ruled out / Actions / Next /
Follow-ups. Legacy fields/checkpoint expectations remain for historical comparisons. Every value
must contain a letter or number; explicit none/unknown
is acceptable. This grades structure, not the truth or adequacy of the incident evidence.

Labels need a colon, a table-cell separator, or a standalone heading/emphasized/list label.
Heading descriptions after an em/en/ascii dash are labels; their values must follow on later lines.
Inline values may wrap onto adjacent or indented lines;
a separate unindented paragraph or a new non-field heading ends that block. Under a field heading,
prose remains its value until another heading, as in Markdown; an unlabeled change of subject is
not mechanically distinguishable. Quotes and fenced examples followed by other text are excluded.
A terminal plain/text/markdown fence is supported, except when introduced as an example, sample,
or template with an explicit label (for example, `Example:` or `### Sample response`). Narrative
mentions of those words do not mark examples. Labels apply until a new non-field section or paragraph.

<expected> is board, none, or a legacy fields/checkpoint/both expectation (including -or-both).
"""
import re
import sys

CLOSING_FIELDS = ("Applied", "Open", "Next")
CHECKPOINT_FIELDS = ("Assessment", "Checked", "Actions", "Next", "Follow-ups")
BOARD_FIELDS = ("Impact", "Open", "Checked", "Ruled out", "Actions", "Next", "Follow-ups")
EXPECTED = ("board", "fields", "checkpoint", "both", "none", "fields-or-both", "checkpoint-or-both")
NAMES = "|".join(dict.fromkeys(CLOSING_FIELDS + CHECKPOINT_FIELDS + BOARD_FIELDS)).replace("Follow-ups", "Follow-?ups")
FIELD = re.compile(rf"^[*_]{{0,2}}(?P<name>{NAMES})\b[*_]{{0,2}}\s*(?P<tail>.*)$", re.I)
FENCE = re.compile(r"^\s*(`{3,}|~{3,})([^\n]*)$")
SECTION = re.compile(r"^(?:#{1,6}\s+\S|[^:]{1,80}:\s*$)")
EXAMPLE = re.compile(
    r"^(?:(?:(?:for|here(?:'s| is) an?)\s+)?(?:example|sample|template)"
    r"(?:\s+(?:reply|response|output|format|closing block))?|(?:handover|checkpoint)\s+example)"
    r"(?:\s*:|$)", re.I,
)


def _key(name):
    return name.lower().replace("-", "")


def _example_label(line):
    return bool(EXAMPLE.match(line.strip().strip("#*_ ")))


def _field(line):
    """Recognize explicit labels, not sentences beginning with field words."""
    plain = line.strip()
    heading = bool(re.match(r"#{1,6}\s+", plain))
    decorated = bool(re.match(r"(?:#{1,6}\s|[-+*]\s|\d+[.)]\s|[*_])", plain))
    plain = re.sub(r"^(?:#{1,6}\s+|[-+*]\s+|\d+[.)]\s+)", "", plain)
    if heading:
        plain = re.sub(r"\s+#+\s*$", "", plain)
    table = plain.startswith("|")
    match = FIELD.match(plain.lstrip("|").strip())
    if not match:
        return None
    tail = match["tail"]
    if tail.startswith(":") or (table and tail.startswith("|")):
        value = tail[1:].strip().strip("|").strip()
    elif decorated and not tail:
        value = ""
    elif heading and re.match(r"^[—–-]\s+\S", tail):
        value = ""  # A heading description is not the incident-specific value.
    else:
        return None
    return _key(match["name"]), value, heading


def _reply_lines(text):
    """Keep terminal reply fences; replace excluded content with a block boundary."""
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        fence = FENCE.match(line)
        if fence:
            marker, language = fence.groups()
            end = index + 1
            closing = re.compile(rf"^\s*{re.escape(marker[0])}{{{len(marker)},}}\s*$")
            while end < len(lines) and not closing.match(lines[end]):
                end += 1
            yield "\0"  # A fence starts a separate block, even if it is the actual reply.
            introduction = next((s for s in reversed(lines[:index]) if s.strip()), "")
            if (end < len(lines) and not any(s.strip() for s in lines[end + 1:])
                    and language.strip().lower() in ("", "text", "markdown", "md")
                    and not _example_label(introduction)):
                for body_line in lines[index + 1:end]:
                    yield "\0" if body_line.lstrip().startswith(">") else body_line
            index = end + 1
        else:
            yield "\0" if line.lstrip().startswith(">") else line
            index += 1


def _scan(text, legacy=False):
    """Return all eligible label names and values in the terminal field block."""
    present, terminal = set(), {}
    active, heading, gap, example = None, False, False, False
    for line in _reply_lines(text):
        if not line.strip():
            gap = True
            continue
        field = _field(line)
        if legacy and field and field[0] in {_key("Impact"), _key("Ruled out")}:
            field = None
        if field:
            active, value, heading = field
            if not example:
                present.add(active)
                terminal[active] = value
        elif (line != "\0" and active and not SECTION.match(line.strip())
              and (heading or not gap or line[:1].isspace() or not terminal.get(active))):
            if not example:
                terminal[active] += "\n" + line
        else:
            terminal, active, heading = {}, None, False
            if line != "\0":
                example = _example_label(line)
        gap = False
    return present, terminal


def _shape(names):
    if names & {_key("Impact"), _key("Ruled out")}:
        return "board"
    fields = len(names & {_key(n) for n in CLOSING_FIELDS}) >= 2
    # Next belongs to both forms; it cannot turn a lone checkpoint label into a checkpoint.
    checkpoint = len(names & {_key(n) for n in CHECKPOINT_FIELDS if n != "Next"}) >= 2
    if fields and checkpoint:
        return "both"
    if fields:
        return "fields"
    return "checkpoint" if checkpoint else "none"


def classify(text):
    """Presence only: recognized labels may still be empty, incomplete, or nonterminal."""
    present, _ = _scan(text)
    return _shape(present)


def check(text, expected):
    """Return (ok, reason), requiring completeness and closure, not just classify() presence."""
    if expected not in EXPECTED:
        return False, f"unknown expected class {expected!r}; one of {', '.join(EXPECTED)}"
    present, terminal = _scan(text, legacy=expected not in ("board", "none"))
    actual = _shape(set(terminal))
    allowed = expected.split("-or-")
    required = set()
    if actual == "board":
        required.update(map(_key, BOARD_FIELDS))
    if actual in ("fields", "both"):
        required.update(map(_key, CLOSING_FIELDS))
    if actual in ("checkpoint", "both"):
        required.update(map(_key, CHECKPOINT_FIELDS))
    missing = sorted(name for name in required if not re.search(r"[^\W_]", terminal.get(name, "")))
    # A partial or earlier block is not absence; standalone replies must carry no field labels.
    mixed = expected == "board" and bool(set(terminal) & {_key("Applied"), _key("Assessment")})
    if actual in allowed and not missing and not mixed and (actual != "none" or not present):
        return True, actual
    return False, (
        f"reply closes as {actual!r}, expected {' or '.join(repr(a) for a in allowed)}; "
        f"recognized labels: {sorted(present) or 'none'}; "
        f"terminal labels: {sorted(terminal) or 'none'}; missing or empty: {missing or 'none'}; "
        f"mixed legacy format: {mixed}"
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
