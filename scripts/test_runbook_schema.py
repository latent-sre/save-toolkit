"""The runbook-frontmatter contract: schema, catalog entry, and template stay in lockstep.

The runbook template (skills/runbook/assets/runbook-template.md) has carried machine-linkable YAML
frontmatter since before the schema existed; schemas/runbook-frontmatter-v1.schema.json is that
contract made explicit so alert→runbook links, KB indexes, and staleness watches can key on a
published shape. Three ways this silently rots, each pinned here:

  * the schema file or its catalog entry goes missing or unparseable — every consumer falls back
    to guessing the shape (this test fails on the pre-schema tree, satisfying the
    fails-without-the-change rule);
  * the template grows or renames a frontmatter key without the schema following — generated
    runbooks validate against a contract that no longer describes them;
  * the schema drifts open (additionalProperties) or optional — the compatibility policy's
    closed-object rule (docs/schema-compatibility.md) stops holding for this entry.

Shape-sync only, per the policy: this partial check is NOT the catalog validator and upgrades
nothing. Pure stdlib; run directly when this schema/catalog/template contract changes. Gate A does
not run component tests.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "runbook-frontmatter-v1.schema.json"
CATALOG_PATH = ROOT / "schemas" / "catalog-v1.json"
TEMPLATE_PATH = ROOT / "skills" / "runbook" / "assets" / "runbook-template.md"
EXAMPLE_PATH = ROOT / "skills" / "runbook" / "assets" / "runbook-example.md"

_KEY_RE = re.compile(r"^([a-z_][a-z0-9_]*):")


def frontmatter_keys(path: Path) -> list[str]:
    """Top-level keys between a runbook's first two `---` fences.

    The template's frontmatter is deliberately flat (no nested keys), so a line-anchored key
    match is exact, not an approximation. If nesting is ever introduced, this parser — and the
    flat schema it guards — both need to change, and this test failing is the reminder.
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


class RunbookSchemaTest(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    def test_schema_is_a_closed_required_object(self) -> None:
        # The compatibility policy's closed-object rule: adding a field is a new version, so the
        # published shape must actually be closed, and every property must be required — an
        # optional field would let two "valid" runbooks disagree about what the KB can key on.
        self.assertEqual(self.schema["type"], "object")
        self.assertIs(self.schema["additionalProperties"], False)
        self.assertEqual(sorted(self.schema["required"]), sorted(self.schema["properties"]))
        self.assertEqual(self.schema["properties"]["schema_version"], {"const": 1})

    def test_template_and_schema_carry_the_same_keys(self) -> None:
        # The template is what humans copy; the schema is what machines trust. A key present in
        # one and absent from the other means generated runbooks and the published contract have
        # already diverged — the exact drift this file exists to catch.
        self.assertEqual(sorted(frontmatter_keys(TEMPLATE_PATH)), sorted(self.schema["properties"]))

    def test_example_carries_the_same_frontmatter_contract_as_the_template(self) -> None:
        """The worked exemplar is a runbook, so it is bound by the runbook contract.

        An example that drifts is worse than no example: readers copy what they are shown, and a
        demonstrated-but-invalid frontmatter teaches the wrong shape more effectively than the
        schema teaches the right one. Same keys as the template and the schema, and `status` inside
        the published enum.
        """
        self.assertEqual(sorted(frontmatter_keys(EXAMPLE_PATH)), sorted(self.schema["properties"]))
        status = next(
            line.split(":", 1)[1].strip()
            for line in EXAMPLE_PATH.read_text(encoding="utf-8").splitlines()
            if line.startswith("status:")
        )
        self.assertIn(status, self.schema["properties"]["status"]["enum"])

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

    def test_catalog_entry_matches_the_file_on_disk(self) -> None:
        entries = [e for e in self.catalog["schemas"] if e["id"] == "runbook-frontmatter-v1"]
        self.assertEqual(len(entries), 1, "exactly one catalog entry for runbook-frontmatter-v1")
        entry = entries[0]
        self.assertEqual(entry["version"], 1)
        # No contract-grade semantic validator ships for this schema, so per the policy the
        # lifecycle is contract-only, and this shape check must not masquerade as one.
        self.assertEqual(entry["status"], "contract-only")
        self.assertIsNone(entry["validator"])
        self.assertEqual(entry["canonical_path"], "schemas/runbook-frontmatter-v1.schema.json")
        self.assertTrue((ROOT / entry["canonical_path"]).is_file())
        self.assertEqual(entry["uri"], self.schema["$id"])
        self.assertEqual(entry["generated_projections"], [])

    def test_date_valued_frontmatter_is_quoted_in_the_template_and_the_example(self) -> None:
        """`last_reviewed: 2026-02-18` is a date object to a YAML parser, not a string.

        The schema types both fields `["string", "null"]`, so an unquoted ISO date decodes to
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
                        f"{value!r} decodes as a date, which the schema does not allow",
                    )
                    if value != "null":
                        self.assertRegex(value.strip("\"'"), iso, "date must be YYYY-MM-DD")


if __name__ == "__main__":
    unittest.main()
