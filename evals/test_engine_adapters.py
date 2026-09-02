"""Offline command, trace, and tool-boundary tests for eval engine adapters."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_adapters


class ClaudeNativeAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = engine_adapters.ClaudeNativeAdapter()

    def test_reference_command_scopes_reads_to_frozen_snapshot(self) -> None:
        plugin = Path("/tmp/frozen-plugin")
        scenario = {
            "mode": "direct",
            "target": {"kind": "agent", "name": "sre"},
            "prompt": "Triage the alert.",
        }
        command = self.adapter.build_command(
            scenario=scenario,
            executable="claude",
            plugin_root=plugin,
            qualified_target="save-toolkit:sre",
            model="sonnet",
            enable_snapshot_reads=True,
            required_reference_paths=("skills/incident/references/first.md",),
            denied_probe_path=Path("/tmp/denied-boundary.txt"),
        )
        self.assertIn("--permission-mode", command)
        self.assertEqual("dontAsk", command[command.index("--permission-mode") + 1])
        self.assertEqual(
            "Glob,Grep,Read,Skill,Task",
            command[command.index("--tools") + 1],
        )
        allowed = command[command.index("--allowedTools") + 1]
        for tool in ("Read", "Grep", "Glob"):
            self.assertIn(f"{tool}({plugin.resolve().as_posix()}/**)", allowed)
        denied = set(command[command.index("--disallowedTools") + 1].split(","))
        self.assertNotIn("Read", denied)
        self.assertNotIn("Grep", denied)
        self.assertNotIn("Glob", denied)
        self.assertIn("Bash", denied)
        prompt = command[command.index("-p") + 1]
        self.assertIn("skills/incident/references/first.md", prompt)
        self.assertIn("/tmp/denied-boundary.txt", prompt)

    def test_unexpected_advertised_tool_is_rejected(self) -> None:
        with self.assertRaisesRegex(engine_adapters.AdapterError, "unexpected advertised tool"):
            self.adapter.validate_tool_boundary(
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
            self.adapter.validate_tool_boundary(
                advertised=("Glob", "Grep", "Read", "Skill", "Task"),
                expected=("Glob", "Grep", "Read", "Skill", "Task"),
                attempts=(attempt,),
                plugin_root=Path("/tmp/frozen-plugin"),
                callable_read_tools=("Read",),
            )

    def test_reads_inside_an_allowed_root_are_in_bounds(self) -> None:
        """HOST-003 (2026-08-28): the harness-owned fixture workspace is an allowed root, so a
        cwd-relative Grep/Glob or a rooted read inside it is in bounds; anything else is not."""
        import tempfile

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
            self.adapter.validate_tool_boundary(attempts=(relative, rooted), allowed_roots=(fixture,), **common)
            with self.assertRaisesRegex(engine_adapters.AdapterError, "out-of-snapshot"):
                self.adapter.validate_tool_boundary(attempts=(relative,), **common)
            outside = engine_adapters.ToolAttempt(tool="Read", path="/etc/passwd", outcome="allowed")
            with self.assertRaisesRegex(engine_adapters.AdapterError, "out-of-snapshot"):
                self.adapter.validate_tool_boundary(attempts=(outside,), allowed_roots=(fixture,), **common)

    def test_traversal_attempt_is_rejected_even_when_denied(self) -> None:
        attempt = engine_adapters.ToolAttempt(
            tool="Read",
            path="/tmp/frozen-plugin/skills/../outside",
            outcome="denied",
        )
        with self.assertRaisesRegex(engine_adapters.AdapterError, "traversal"):
            self.adapter.validate_tool_boundary(
                advertised=("Glob", "Grep", "Read", "Skill", "Task"),
                expected=("Glob", "Grep", "Read", "Skill", "Task"),
                attempts=(attempt,),
                plugin_root=Path("/tmp/frozen-plugin"),
                callable_read_tools=("Read",),
            )

    def test_reference_boundary_requires_positive_and_negative_probes(self) -> None:
        plugin = Path("/tmp/frozen-plugin")
        allowed = plugin / "skills/incident/references/first.md"
        denied = Path("/tmp/denied-boundary.txt")
        attempts = (
            engine_adapters.ToolAttempt("Read", str(allowed), "allowed"),
            engine_adapters.ToolAttempt("Read", str(denied), "denied"),
        )
        options = {
            "advertised": ("Glob", "Grep", "Read", "Skill", "Task"),
            "expected": ("Glob", "Grep", "Read", "Skill", "Task"),
            "plugin_root": plugin,
            "callable_read_tools": ("Read", "Grep", "Glob"),
            "required_allowed_paths": (allowed,),
            "required_denied_path": denied,
        }
        self.adapter.validate_tool_boundary(attempts=attempts, **options)
        with self.assertRaisesRegex(engine_adapters.AdapterError, "missing denied"):
            self.adapter.validate_tool_boundary(attempts=attempts[:1], **options)
        with self.assertRaisesRegex(engine_adapters.AdapterError, "missing successful"):
            self.adapter.validate_tool_boundary(attempts=attempts[1:], **options)


if __name__ == "__main__":
    unittest.main()
