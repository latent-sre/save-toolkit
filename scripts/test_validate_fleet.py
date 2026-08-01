"""Mutation-oriented tests for the canonical fleet validator."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import validate_fleet


ROOT = Path(__file__).resolve().parents[1]


class FleetValidatorTests(unittest.TestCase):
    def test_current_agents_pass(self) -> None:
        names, failures = validate_fleet.validate_agents(ROOT)
        self.assertEqual(sorted(validate_fleet.EXPECTED_AUTHORITY), sorted(names))
        self.assertEqual([], failures)

    def test_scribe_is_a_non_executing_document_writer(self) -> None:
        path = ROOT / "agents" / "scribe.md"
        fields, body, _ = validate_fleet.adapters.parse_frontmatter(path)
        self.assertEqual(
            {"Read", "Grep", "Glob", "Edit", "Write", "Skill"},
            validate_fleet._tool_bases(fields["tools"]),
        )
        self.assertIn("Do not execute anything", body)
        self.assertIn("## Pick exactly one mode", body)

    def test_sre_steward_no_longer_owns_operational_documentation(self) -> None:
        fields, body, _ = validate_fleet.adapters.parse_frontmatter(
            ROOT / "agents" / "sre-steward.md"
        )
        description = str(fields["description"]).lower()
        self.assertIn("for runbooks or postmortems use sre-agents:scribe", description)
        self.assertNotIn("operational documentation", description)
        self.assertNotIn("## Documentation lane", body)
        self.assertNotIn("- `runbook` —", body)
        self.assertNotIn("- `postmortem` —", body)
        self.assertNotIn("documentation output, filled", body)
        self.assertIn("→ `scribe`", body)

    def test_scribe_execute_egress_and_delegation_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "agents").mkdir()
            for source in (ROOT / "agents").glob("*.md"):
                text = source.read_text(encoding="utf-8")
                if source.name == "scribe.md":
                    text = text.replace(
                        "tools: Read, Grep, Glob, Edit, Write, Skill",
                        "tools: Read, Grep, Glob, Edit, Write, Skill, Bash, WebSearch, Agent(researcher)",
                    )
                (root / "agents" / source.name).write_text(text, encoding="utf-8")
            _, failures = validate_fleet.validate_agents(root)
        rendered = "\n".join(failures)
        self.assertIn("forbidden tool(s): Agent, Bash, WebSearch", rendered)
        self.assertIn("delegation mismatch", rendered)

    def test_scribe_loaded_bundle_cannot_execute_or_route_docs_to_steward(self) -> None:
        self.assertEqual([], validate_fleet.validate_scribe_bundle(ROOT))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in (
                Path("skills/runbook/SKILL.md"),
                Path("skills/postmortem/SKILL.md"),
                Path("skills/runbook/assets/runbook-template.md"),
            ):
                source = ROOT / relative
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                text = source.read_text(encoding="utf-8")
                text = text.replace(
                    "never execute from\n  this documentation lane, including a read-only command",
                    "run read-only ones to confirm syntax",
                )
                text = text.replace(
                    "operating documentation → typed `scribe`",
                    "operating documentation → typed `sre-steward`",
                )
                text = text.replace(
                    "hand the timeline and evidence to the `scribe` agent for retrospective documentation",
                    "hand the timeline and evidence to the `sre-steward` agent for retrospective documentation",
                )
                target.write_text(text, encoding="utf-8")
            failures = validate_fleet.validate_scribe_bundle(root)
        rendered = "\n".join(failures)
        self.assertIn("run read-only ones to confirm syntax", rendered)
        self.assertIn("operating documentation → typed `sre-steward`", rendered)
        self.assertIn("timeline and evidence to the `sre-steward` agent", rendered)

    def test_inert_plugin_hook_and_missing_tools_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "agents").mkdir()
            for source in (ROOT / "agents").glob("*.md"):
                text = source.read_text(encoding="utf-8")
                if source.name == "reviewer.md":
                    text = text.replace("tools: Read, Grep, Glob, Skill", "hooks: ignored\ntools: Read")
                (root / "agents" / source.name).write_text(text, encoding="utf-8")
            _, failures = validate_fleet.validate_agents(root)
        rendered = "\n".join(failures)
        self.assertIn("unsupported plugin agent field", rendered)
        self.assertIn("missing required tool", rendered)

    def test_mcp_server_wildcard_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "agents").mkdir()
            for source in (ROOT / "agents").glob("*.md"):
                text = source.read_text(encoding="utf-8")
                if source.name == "researcher.md":
                    text = text.replace("  - mcp__plugin_githits_githits__search\n", "  - mcp__plugin_githits_githits__*\n")
                (root / "agents" / source.name).write_text(text, encoding="utf-8")
            _, failures = validate_fleet.validate_agents(root)
        self.assertIn("MCP authority is not exact-approved", "\n".join(failures))

    def test_unknown_delegation_target_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "agents").mkdir()
            for source in (ROOT / "agents").glob("*.md"):
                text = source.read_text(encoding="utf-8")
                if source.name == "sde.md":
                    text = text.replace(
                        "Agent(reviewer, scribe, researcher)", "Agent(does-not-exist)"
                    )
                (root / "agents" / source.name).write_text(text, encoding="utf-8")
            _, failures = validate_fleet.validate_agents(root)
        self.assertIn("does not exist", "\n".join(failures))

    def test_local_investigator_external_egress_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "agents").mkdir()
            for source in (ROOT / "agents").glob("*.md"):
                text = source.read_text(encoding="utf-8")
                if source.name == "repository-investigator.md":
                    text = text.replace("tools: Read, Grep, Glob", "tools: Read, Grep, Glob, WebSearch")
                (root / "agents" / source.name).write_text(text, encoding="utf-8")
            _, failures = validate_fleet.validate_agents(root)
        self.assertIn("forbidden tool(s): WebSearch", "\n".join(failures))

    def test_external_researcher_local_read_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "agents").mkdir()
            for source in (ROOT / "agents").glob("*.md"):
                text = source.read_text(encoding="utf-8")
                if source.name == "researcher.md":
                    text = text.replace("  - WebSearch\n", "  - Read\n  - WebSearch\n")
                (root / "agents" / source.name).write_text(text, encoding="utf-8")
            _, failures = validate_fleet.validate_agents(root)
        self.assertIn("forbidden tool(s): Read", "\n".join(failures))

    def test_local_agent_direct_web_access_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "agents").mkdir()
            for source in (ROOT / "agents").glob("*.md"):
                text = source.read_text(encoding="utf-8")
                if source.name == "sde.md":
                    text = text.replace("Write, Skill", "Write, WebFetch, Skill")
                (root / "agents" / source.name).write_text(text, encoding="utf-8")
            _, failures = validate_fleet.validate_agents(root)
        self.assertIn("forbidden tool(s): WebFetch", "\n".join(failures))

    def test_delegation_contract_is_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "agents").mkdir()
            for source in (ROOT / "agents").glob("*.md"):
                text = source.read_text(encoding="utf-8")
                if source.name == "sde.md":
                    text = text.replace(
                        "Agent(reviewer, scribe, researcher)", "Agent(reviewer)"
                    )
                (root / "agents" / source.name).write_text(text, encoding="utf-8")
            _, failures = validate_fleet.validate_agents(root)
        self.assertIn("delegation mismatch", "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
