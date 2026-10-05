"""Authority and design-record regressions for the principal design lane; no model calls."""

import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest

import generate_platform_adapters as adapters
import validate_fleet


ROOT = Path(__file__).resolve().parents[1]
NAME = "principal-engineer"
PRINCIPAL = ROOT / "skills/eng-ladder/references/principal.md"


def _section(text: str, heading: str) -> str:
    start = text.index(heading)
    end = text.find("\n## ", start + len(heading))
    return text[start:] if end == -1 else text[start:end]


class PrincipalContractTests(unittest.TestCase):
    def test_canonical_and_projected_authority(self):
        fields, _, _ = adapters.parse_frontmatter(ROOT / "agents" / f"{NAME}.md")
        specs = validate_fleet._tool_specs(fields["tools"])
        self.assertEqual(
            {"Read", "Grep", "Glob", "Write", "Edit", "Skill", "Agent"},
            validate_fleet._tool_bases(specs),
        )
        self.assertEqual(
            {"repository-investigator", "sre-assistant", "researcher"},
            validate_fleet._delegates(specs, Path(NAME)),
        )
        projected, _, _ = adapters.parse_frontmatter(
            ROOT / ".github/agents" / f"{NAME}.agent.md")
        self.assertEqual(["read", "search", "edit", "agent"], json.loads(projected["tools"]))
        self.assertEqual(
            ["repository-investigator", "sre-assistant", "researcher"],
            json.loads(projected["agents"]))

    def test_validator_rejects_execution_egress_and_implementation_delegation(self):
        for grant in ("Bash", "PowerShell", "WebFetch", "EnterWorktree", "NotebookEdit",
                      "Agent(save-toolkit:software-engineer)"):
            with self.subTest(grant=grant), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                shutil.copytree(ROOT / "agents", root / "agents")
                path = root / "agents" / f"{NAME}.md"
                lines = path.read_text(encoding="utf-8").splitlines()
                index = next(i for i, line in enumerate(lines) if line.startswith("tools:"))
                if grant.startswith("Agent("):
                    lines[index] = lines[index].replace(
                        "save-toolkit:researcher)",
                        "save-toolkit:researcher, save-toolkit:software-engineer)")
                else:
                    lines[index] += ", " + grant
                path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                _, failures = validate_fleet.validate_agents(root)
                self.assertTrue(any(NAME in failure and (
                    "forbidden tool" in failure or "delegation mismatch" in failure
                ) for failure in failures), failures)

    def test_worked_example_carries_every_design_record_slot_and_label(self):
        # A worked example is copied as a shape: a slot it omits is a slot the output drops.
        record = _section(PRINCIPAL.read_text(encoding="utf-8"), "## Design record")
        slots = [slot for slot in re.findall(r"^\| ([A-Z][^|]*?) \|", record, re.MULTILINE)
                 if slot != "Slot"]
        example = [line for line in record.splitlines() if line.startswith("> **")]
        shown = [re.match(r"> \*\*([^*]+)\*\*", line).group(1) for line in example]
        self.assertEqual(slots, shown)
        for required in ("Contracts and consumers", "Verification", "Decision needed"):
            self.assertIn(required, slots)
        for label in validate_fleet.EVIDENCE_TRIAD:
            self.assertIn(label, "\n".join(example))


if __name__ == "__main__":
    unittest.main()
