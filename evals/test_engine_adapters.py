"""Offline command and tool-boundary tests for the Claude plugin eval adapter."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_adapters


class BuildCommandTests(unittest.TestCase):
    def test_agent_target_discovery_grants_read_tools_skill_target_does_not(self) -> None:
        """EVAL-008: a tool-minimal agent (Read/Grep/Glob, no Skill/Agent) must not resolve to zero
        tools when Task-dispatched, so agent-target discovery widens the grant; skill-target
        discovery does not need it and stays on the base set."""
        plugin = Path("/tmp/frozen-plugin")
        agent_discovery = {
            "mode": "discovery",
            "target": {"kind": "agent", "name": "reviewer"},
            "prompt": "Review the pending change.",
        }
        skill_discovery = {
            "mode": "discovery",
            "target": {"kind": "skill", "name": "runbook"},
            "prompt": "Write the runbook.",
        }
        agent_command = engine_adapters.build_command(
            scenario=agent_discovery,
            executable="claude",
            plugin_root=plugin,
            qualified_target="save-toolkit:reviewer",
            model="sonnet",
        )
        skill_command = engine_adapters.build_command(
            scenario=skill_discovery,
            executable="claude",
            plugin_root=plugin,
            qualified_target="save-toolkit:runbook",
            model="sonnet",
        )
        self.assertEqual(
            "Glob,Grep,Read,Skill,Task",
            agent_command[agent_command.index("--tools") + 1],
        )
        agent_denied = set(agent_command[agent_command.index("--disallowedTools") + 1].split(","))
        self.assertNotIn("Read", agent_denied)
        self.assertNotIn("Grep", agent_denied)
        self.assertNotIn("Glob", agent_denied)
        self.assertEqual(
            "Skill,Task",
            skill_command[skill_command.index("--tools") + 1],
        )
        skill_denied = set(skill_command[skill_command.index("--disallowedTools") + 1].split(","))
        self.assertIn("Read", skill_denied)
        self.assertIn("Grep", skill_denied)
        self.assertIn("Glob", skill_denied)

    def test_direct_agent_is_pinned_and_the_prompt_is_not_rewritten(self) -> None:
        scenario = {
            "mode": "direct",
            "target": {"kind": "agent", "name": "sre"},
            "prompt": "Checkout latency tripled.",
        }
        command = engine_adapters.build_command(
            scenario=scenario,
            executable="claude",
            plugin_root=Path("/tmp/frozen-plugin"),
            qualified_target="save-toolkit:sre",
            model=None,
        )
        self.assertEqual(command[1:3], ["--agent", "save-toolkit:sre"])
        self.assertEqual(command[command.index("-p") + 1], "Checkout latency tripled.")
        self.assertNotIn("--model", command)


class ToolBoundaryTests(unittest.TestCase):
    def test_unexpected_advertised_tool_is_rejected(self) -> None:
        with self.assertRaisesRegex(engine_adapters.AdapterError, "unexpected advertised tool"):
            engine_adapters.validate_tool_boundary(
                advertised=("Skill", "Task", "Write"),
                expected=("Skill", "Task"),
                attempts=(),
                plugin_root=Path("/tmp/frozen-plugin"),
            )

    def test_successful_out_of_snapshot_read_is_rejected(self) -> None:
        attempt = engine_adapters.ToolAttempt(
            tool="Read",
            path="/etc/passwd",
            outcome="allowed",
        )
        with self.assertRaisesRegex(engine_adapters.AdapterError, "out-of-snapshot"):
            engine_adapters.validate_tool_boundary(
                advertised=("Glob", "Grep", "Read", "Skill", "Task"),
                expected=("Glob", "Grep", "Read", "Skill", "Task"),
                attempts=(attempt,),
                plugin_root=Path("/tmp/frozen-plugin"),
                callable_read_tools=("Read",),
            )

    def test_reads_inside_an_allowed_root_are_in_bounds(self) -> None:
        """HOST-003 (2026-08-28): the harness-owned fixture workspace is an allowed root, so a
        cwd-relative Grep/Glob or a rooted read inside it is in bounds; anything else is not."""
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp)
            relative = engine_adapters.ToolAttempt(tool="Grep", path="CheckoutLatencyHigh", outcome="allowed")
            rooted = engine_adapters.ToolAttempt(tool="Glob", path=str(fixture / "**" / "manifest.yml"), outcome="allowed")
            common = dict(
                advertised=("Glob", "Grep", "Read", "Skill", "Task"),
                expected=("Glob", "Grep", "Read", "Skill", "Task"),
                plugin_root=Path("/tmp/frozen-plugin"),
                callable_read_tools=("Read", "Grep", "Glob"),
            )
            engine_adapters.validate_tool_boundary(
                attempts=(relative, rooted), allowed_roots=(fixture,), **common
            )
            with self.assertRaisesRegex(engine_adapters.AdapterError, "out-of-snapshot"):
                engine_adapters.validate_tool_boundary(attempts=(relative,), **common)
            outside = engine_adapters.ToolAttempt(tool="Read", path="/etc/passwd", outcome="allowed")
            with self.assertRaisesRegex(engine_adapters.AdapterError, "out-of-snapshot"):
                engine_adapters.validate_tool_boundary(
                    attempts=(outside,), allowed_roots=(fixture,), **common
                )

    def test_traversal_attempt_is_rejected_even_when_denied(self) -> None:
        attempt = engine_adapters.ToolAttempt(
            tool="Read",
            path="/tmp/frozen-plugin/skills/../outside",
            outcome="denied",
        )
        with self.assertRaisesRegex(engine_adapters.AdapterError, "traversal"):
            engine_adapters.validate_tool_boundary(
                advertised=("Glob", "Grep", "Read", "Skill", "Task"),
                expected=("Glob", "Grep", "Read", "Skill", "Task"),
                attempts=(attempt,),
                plugin_root=Path("/tmp/frozen-plugin"),
                callable_read_tools=("Read",),
            )

    def test_ambiguous_outcome_is_rejected(self) -> None:
        attempt = engine_adapters.ToolAttempt(tool="Read", path="/tmp/x", outcome="ambiguous")
        with self.assertRaisesRegex(engine_adapters.AdapterError, "ambiguous"):
            engine_adapters.validate_tool_boundary(
                advertised=("Glob", "Grep", "Read", "Skill", "Task"),
                expected=("Glob", "Grep", "Read", "Skill", "Task"),
                attempts=(attempt,),
                plugin_root=Path("/tmp/frozen-plugin"),
                callable_read_tools=("Read",),
            )


if __name__ == "__main__":
    unittest.main()
