"""The runbook-frontmatter contract: the template is the shape, the exemplar obeys it.

The runbook template (skills/operational-docs/assets/runbook-template.md) carries machine-linkable YAML
frontmatter so alert->runbook links, KB indexes, and staleness watches can key on a published
shape. A separate `schemas/runbook-frontmatter-v1.schema.json` published that shape until the
2026-09-02 retention pass removed it along with `schemas/catalog-v1.json` (recover either with
`git show e77fc672^:schemas/<name>`). With the schema gone the TEMPLATE is the contract, and the
two ways it silently rots are pinned here:

  * the worked exemplar drifts from the template -- readers copy what they are shown, so a
    demonstrated-but-invalid frontmatter teaches the wrong shape more effectively than the
    template teaches the right one;
  * a date-valued field loses its quotes and decodes as `datetime.date` rather than a string.

The checks the schema owned and nothing now can -- that the published object is closed, that every
property is required, and that a catalog entry matches the file on disk -- were removed with it
rather than reimplemented against a file that no longer exists. Restoring the schema restores them
from git.

Frontmatter shape checks only; these do not establish model behavior. Pure stdlib;
run directly when the template, exemplar, or converter contract changes. Gate A does not run
component tests.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from testkit import frontmatter_block

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "skills" / "operational-docs" / "assets" / "runbook-template.md"
EXPECTED_FRONTMATTER_KEYS = [
    "schema_version",
    "runbook_id",
    "service_id",
    "status",
    "alert_names",
    "owner",
    "severity",
    "source_revision",
    "last_reviewed",
    "last_verified",
    "verification_evidence",
    "version",
]


def frontmatter_keys(path: Path) -> list[str]:
    """Top-level keys between a runbook's first two `---` fences.

    The template's frontmatter is deliberately flat (no nested keys), so a line-anchored key
    match is exact, not an approximation. If nesting is ever introduced, this parser -- and the
    flat contract it guards -- both need to change, and this test failing is the reminder.
    """
    return re.findall(r"(?m)^([a-z_][a-z0-9_]*):", frontmatter_block(path.read_text(encoding="utf-8")))


def template_status_enum() -> list[str]:
    """The allowed `status` values, read from the template's own placeholder line.

    The template writes them as `status: draft | active | retired`. That line is the only
    surviving statement of the enum, so the template enum is checked directly.
    """
    for line in TEMPLATE_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("status:"):
            return [value.strip() for value in line.split(":", 1)[1].split("|")]
    raise AssertionError(f"{TEMPLATE_PATH}: no `status:` line in the frontmatter")


class RunbookFrontmatterContractTest(unittest.TestCase):
    def test_template_carries_expected_frontmatter_contract(self) -> None:
        self.assertEqual(sorted(frontmatter_keys(TEMPLATE_PATH)), sorted(EXPECTED_FRONTMATTER_KEYS))
        self.assertEqual(template_status_enum(), ["draft", "active", "retired"])

    def test_date_valued_frontmatter_is_quoted_in_the_template(self) -> None:
        """`last_reviewed: 2026-02-18` is a date object to a YAML parser, not a string.

        The contract types both fields as a string or null, so an unquoted ISO date decodes to
        `datetime.date`. Checked on the raw line rather than through a parser because
        this suite is pure stdlib, and because the defect IS the representation: a parser would
        hide it by decoding successfully.
        """

        allowed = re.compile(r"^(?:null|\"[^\"]*\"|'[^']*')$")
        iso = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
        lines = TEMPLATE_PATH.read_text(encoding="utf-8").splitlines()
        closing = lines.index("---", 1)
        for line in lines[1:closing]:
            key, _, raw = line.partition(":")
            if key.strip() not in ("last_reviewed", "last_verified"):
                continue
            value = raw.strip()
            with self.subTest(path=TEMPLATE_PATH.name, key=key.strip()):
                self.assertRegex(
                    value,
                    allowed,
                    f"{TEMPLATE_PATH.name}: {key.strip()} must be null or a quoted string; "
                    f"{value!r} decodes as a date, which the contract does not allow",
                )
                if value != "null":
                    self.assertRegex(value.strip("\"'"), iso, "date must be YYYY-MM-DD")


if __name__ == "__main__":
    unittest.main()
