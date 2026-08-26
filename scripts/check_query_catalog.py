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

# Secret-shaped content. Deliberately matches the ASSIGNMENT, not the bare word: `token` appears
# legitimately in prose ("canary token"), while `token=<value>` in a query is the thing that must
# never land. The placeholder forms `<...>` and `$...$` stay legal so entries remain fillable.
_PLACEHOLDER = r"(?:<[^>\n]*>|\$[^$\n]*\$|\"<[^>\n]*>\")"
SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(token|api[_-]?key|apikey|password|passwd|secret|bearer|authorization|session[_-]?id"
    r"|cookie|credential)\b\s*[:=]\s*(?!" + _PLACEHOLDER + r")\S+"
)
# A bare high-entropy literal that looks like a credential even without a key name.
SECRET_LITERAL = re.compile(r"\b(?:eyJ[A-Za-z0-9_-]{10,}|xox[abps]-[A-Za-z0-9-]{10,}|gh[pousr]_[A-Za-z0-9]{20,})")

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

        # Secret scan covers the WHOLE file: prose around an entry is just as committable.
        for number, line in enumerate(text.splitlines(), start=1):
            if SECRET_ASSIGNMENT.search(line) or SECRET_LITERAL.search(line):
                failures.append(
                    f"{relative}:{number}: possible credential or session value; catalogs carry "
                    "names, locators, and query text only"
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
