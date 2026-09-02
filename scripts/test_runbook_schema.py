"""The runbook-frontmatter contract: the template is the shape, the exemplar obeys it.

The runbook template (skills/runbook/assets/runbook-template.md) carries machine-linkable YAML
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

Shape-sync only. Pure stdlib; run directly when the template, the exemplar, or the converter's
frontmatter contract changes. Gate A does not run component tests.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "skills" / "runbook" / "assets" / "runbook-template.md"
EXAMPLE_PATH = ROOT / "skills" / "runbook" / "assets" / "runbook-example.md"

_KEY_RE = re.compile(r"^([a-z_][a-z0-9_]*):")


def frontmatter_keys(path: Path) -> list[str]:
    """Top-level keys between a runbook's first two `---` fences.

    The template's frontmatter is deliberately flat (no nested keys), so a line-anchored key
    match is exact, not an approximation. If nesting is ever introduced, this parser -- and the
    flat contract it guards -- both need to change, and this test failing is the reminder.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise AssertionError(f"{path}: must open with a `---` frontmatter fence")
    keys: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            return keys
        match = _KEY_RE.match(line)
        if match:
            keys.append(match.group(1))
    raise AssertionError(f"{path}: frontmatter fence never closes")


def template_status_enum() -> list[str]:
    """The allowed `status` values, read from the template's own placeholder line.

    The template writes them as `status: draft | active | retired`. That line is the only
    surviving statement of the enum, so the exemplar is checked against it rather than against a
    list copied into this file, which would drift the moment the template gained a state.
    """
    for line in TEMPLATE_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("status:"):
            return [value.strip() for value in line.split(":", 1)[1].split("|")]
    raise AssertionError(f"{TEMPLATE_PATH}: no `status:` line in the frontmatter")


class RunbookFrontmatterContractTest(unittest.TestCase):
    def test_exemplar_carries_the_same_frontmatter_contract_as_the_template(self) -> None:
        """The worked exemplar is a runbook, so it is bound by the runbook contract.

        An example that drifts is worse than no example: readers copy what they are shown, and a
        demonstrated-but-invalid frontmatter teaches the wrong shape more effectively than the
        template teaches the right one. Same keys as the template, and `status` inside the enum
        the template publishes.
        """
        self.assertEqual(sorted(frontmatter_keys(EXAMPLE_PATH)), sorted(frontmatter_keys(TEMPLATE_PATH)))
        status = next(
            line.split(":", 1)[1].strip()
            for line in EXAMPLE_PATH.read_text(encoding="utf-8").splitlines()
            if line.startswith("status:")
        )
        self.assertIn(status, template_status_enum())

    def test_example_is_marked_as_an_exemplar_before_its_first_procedure(self) -> None:
        """Its dates and evidence ids are illustrative, and a copier must learn that first.

        The frontmatter shows a matured runbook -- non-null `last_verified`, populated
        `verification_evidence`, three history rows. That is the point: the blank template cannot
        show it. It is also exactly what someone would inherit unnoticed by copying the file, so
        the disclaimer has to land above the first thing anyone acts on.
        """
        text = EXAMPLE_PATH.read_text(encoding="utf-8")
        self.assertIn("teaching exemplar, not a live runbook", text)
        self.assertLess(
            text.index("teaching exemplar"),
            text.index("## Procedure"),
            "the exemplar disclaimer must precede the procedure a reader would follow",
        )

    def test_date_valued_frontmatter_is_quoted_in_the_template_and_the_example(self) -> None:
        """`last_reviewed: 2026-02-18` is a date object to a YAML parser, not a string.

        The contract types both fields as a string or null, so an unquoted ISO date decodes to
        `datetime.date` and fails the very contract the exemplar exists to demonstrate -- and
        teaches every copied runbook the wrong representation. The template escaped this only
        because it ships `null`. Checked on the raw line rather than through a parser because
        this suite is pure stdlib, and because the defect IS the representation: a parser would
        hide it by decoding successfully.
        """

        allowed = re.compile(r"^(?:null|\"[^\"]*\"|'[^']*')$")
        iso = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
        for path in (TEMPLATE_PATH, EXAMPLE_PATH):
            lines = path.read_text(encoding="utf-8").splitlines()
            closing = lines.index("---", 1)
            for line in lines[1:closing]:
                key, _, raw = line.partition(":")
                if key.strip() not in ("last_reviewed", "last_verified"):
                    continue
                value = raw.strip()
                with self.subTest(path=path.name, key=key.strip()):
                    self.assertRegex(
                        value,
                        allowed,
                        f"{path.name}: {key.strip()} must be null or a quoted string; "
                        f"{value!r} decodes as a date, which the contract does not allow",
                    )
                    if value != "null":
                        self.assertRegex(value.strip("\"'"), iso, "date must be YYYY-MM-DD")


if __name__ == "__main__":
    unittest.main()
