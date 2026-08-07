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
nothing. Pure stdlib; runs offline in CI via gate_a.py.
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

_KEY_RE = re.compile(r"^([a-z_][a-z0-9_]*):")


def template_frontmatter_keys() -> list[str]:
    """Top-level keys between the template's first two `---` fences.

    The template's frontmatter is deliberately flat (no nested keys), so a line-anchored key
    match is exact, not an approximation. If nesting is ever introduced, this parser — and the
    flat schema it guards — both need to change, and this test failing is the reminder.
    """
    lines = TEMPLATE_PATH.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise AssertionError(f"{TEMPLATE_PATH}: template must open with a `---` frontmatter fence")
    keys: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            return keys
        match = _KEY_RE.match(line)
        if match:
            keys.append(match.group(1))
    raise AssertionError(f"{TEMPLATE_PATH}: frontmatter fence never closes")


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
        self.assertEqual(sorted(template_frontmatter_keys()), sorted(self.schema["properties"]))

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


if __name__ == "__main__":
    unittest.main()
