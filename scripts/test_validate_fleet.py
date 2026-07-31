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
                    text = text.replace("Agent(reviewer)", "Agent(does-not-exist)")
                (root / "agents" / source.name).write_text(text, encoding="utf-8")
            _, failures = validate_fleet.validate_agents(root)
        self.assertIn("does not exist", "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
