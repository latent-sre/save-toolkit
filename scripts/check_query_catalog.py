#!/usr/bin/env python3
"""Check team query-catalog entries for shape and for content that must never be committed.

WHY THIS EXISTS. The catalog is the one place the fleet invites people to paste real searches, and a
real search is exactly where a token, a session id, or a customer identifier rides along by accident.
A reviewer reading a 40-line diff of SPL will not reliably catch `token=abc123` in the middle of it;
a validator will. The shape rules matter for a different reason: an entry missing "healthy looks
like" is unusable by the `sre` lane, which cannot run the query and can only interpret pasted output
against a stated expectation.

Standard library only -- this runs on the Gate A path.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


ROOT = Path(os.environ.get("FLEET_ROOT") or Path(__file__).resolve().parents[1]).resolve()
CATALOGS = ("skills/obs-logs/references/query-catalog.md",)

REQUIRED_FIELDS = ("Applies to:", "Reads as:", "Healthy looks like:", "Owner:", "Verified:")

# Content that must never be committed. Three classes, because the catalog's own rule names three:
# credentials, session/user identifiers, and raw payloads.
#
# Each pattern matches the ASSIGNMENT, not the bare word: `token` and `user` appear legitimately in
# prose ("canary token", "user impact"), while `token=abc123` in a query is the thing that must never
# land. The placeholder forms stay legal or the catalog would be unfillable -- an author has to be
# able to write `user_id=<user_field>`.
_PLACEHOLDER = r"(?:<[^>\n]*>|\$[^$\n]*\$|\"<[^>\n]*>\"|'<[^>\n]*>')"
_SECRET_KEYS = (
    r"token|api[_-]?key|apikey|password|passwd|secret|bearer|authorization|cookie|credential"
)
_IDENTITY_KEYS = (
    r"session[_-]?id|user[_-]?id|username|user[_-]?name|customer[_-]?id|account[_-]?id"
    r"|member[_-]?id|client[_-]?id|email|e[_-]?mail|ssn|phone"
)
_PAYLOAD_KEYS = r"payload|body|request[_-]?body|response[_-]?body|raw"

# DOTALL is deliberate on the value side: a key, separator, and value split across lines would
# otherwise slip past a line-at-a-time scan, and the catalog is hand-edited Markdown where that
# wrapping happens naturally.
def _assignment(keys: str) -> re.Pattern[str]:
    return re.compile(
        r"(?is)\b(?:" + keys + r")\b\s*[:=]\s*(?!" + _PLACEHOLDER + r")(?P<value>\S)"
    )


SECRET_ASSIGNMENT = _assignment(_SECRET_KEYS)
IDENTITY_ASSIGNMENT = _assignment(_IDENTITY_KEYS)
PAYLOAD_ASSIGNMENT = _assignment(_PAYLOAD_KEYS)
SCANNERS = (
    (SECRET_ASSIGNMENT, "credential"),
    (IDENTITY_ASSIGNMENT, "session or user identifier"),
    (PAYLOAD_ASSIGNMENT, "raw payload"),
)

# A bare high-entropy literal that looks like a credential even without a key name.
SECRET_LITERAL = re.compile(r"\b(?:eyJ[A-Za-z0-9_-]{10,}|xox[abps]-[A-Za-z0-9-]{10,}|gh[pousr]_[A-Za-z0-9]{20,})")

# A required field whose label is present but whose value is empty is operationally identical to a
# missing one: the recommending lane cannot interpret a result it has no expectation for.
def _field_value(body: str, field: str) -> str | None:
    match = re.search(r"\*\*" + re.escape(field) + r"\*\*(?P<value>[^\n]*)", body)
    return None if match is None else match.group("value").strip()


ENTRY_RE = re.compile(r"^### (?P<question>.+)$", re.M)
FENCE_RE = re.compile(r"```(?P<lang>[a-z]*)\n(?P<body>.*?)```", re.S)


def _entries(text: str) -> list[tuple[str, int, str]]:
    """Return (question, line_number, body) for each `###` entry below a dialect heading."""

    entries = []
    matches = list(ENTRY_RE.finditer(text))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        line = text.count("\n", 0, match.start()) + 1
        entries.append((match.group("question").strip(), line, text[match.end():end]))
    return entries


def check(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    for relative in CATALOGS:
        path = root / relative
        if not path.is_file():
            failures.append(f"{relative}: catalog file is missing")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:  # unreadable file is a finding, never a silent skip
            failures.append(f"{relative}: cannot read: {exc}")
            continue

        # Scan the WHOLE text, not line by line: prose around an entry is just as committable, and a
        # key/separator/value split across a line break would evade a per-line scan.
        for pattern, label in SCANNERS:
            for match in pattern.finditer(text):
                number = text.count("\n", 0, match.start()) + 1
                failures.append(
                    f"{relative}:{number}: possible {label}; catalogs carry names, locators, and "
                    "query text only"
                )
        for match in SECRET_LITERAL.finditer(text):
            number = text.count("\n", 0, match.start()) + 1
            failures.append(
                f"{relative}:{number}: possible credential; catalogs carry names, locators, and "
                "query text only"
            )

        for question, line, body in _entries(text):
            # The contribution template is an example, not an entry: it lives above the first
            # dialect heading and its own fields are the thing being demonstrated.
            if question.startswith("<"):
                continue
            missing = [field for field in REQUIRED_FIELDS if f"**{field}**" not in body]
            if missing:
                failures.append(
                    f"{relative}:{line}: entry {question!r} is missing {', '.join(missing)}"
                )
            empty = [
                field
                for field in REQUIRED_FIELDS
                if field not in missing and not _field_value(body, field)
            ]
            if empty:
                failures.append(
                    f"{relative}:{line}: entry {question!r} has an empty {', '.join(empty)} — a "
                    "label with no value cannot be acted on"
                )
            fences = FENCE_RE.findall(body)
            if not fences:
                failures.append(f"{relative}:{line}: entry {question!r} carries no query block")
            for lang, _ in fences:
                if not lang:
                    failures.append(
                        f"{relative}:{line}: entry {question!r} has an unlabelled query fence; "
                        "label it with its dialect so the reader knows what they are running"
                    )
    return failures


def main() -> int:
    failures = check(ROOT)
    if failures:
        print("check_query_catalog: FAIL")
        for failure in failures:
            print("  " + failure)
        return 1
    print("check_query_catalog: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
