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


class CodexResolvedContextAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = engine_adapters.CodexResolvedContextAdapter()

    def test_command_is_ephemeral_read_only_and_uses_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            schema = root / "response-schema.json"
            schema.write_text("{}", encoding="utf-8")
            command = self.adapter.build_command(
                executable="codex",
                bundle_root=root,
                response_schema=schema,
                model="gpt-5.6-terra",
            )
        for flag in (
            "--ephemeral", "--ignore-user-config", "--ignore-rules", "--strict-config", "--json"
        ):
            self.assertIn(flag, command)
        self.assertEqual("read-only", command[command.index("--sandbox") + 1])
        self.assertIn('approval_policy="never"', command)
        self.assertIn("shell_environment_policy.inherit=none", command)
        self.assertEqual("-", command[-1])
        self.assertNotIn("--add-dir", command)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)

    def test_environment_removes_api_keys_but_keeps_subscriber_home(self) -> None:
        environment = self.adapter.sanitized_environment(
            {
                "PATH": "/bin",
                "HOME": "/home/test",
                "CODEX_HOME": "/home/test/.codex",
                "OPENAI_API_KEY": "must disappear",
                "OPENAI_BASE_URL": "https://must-disappear.invalid",
                "ANTHROPIC_API_KEY": "must disappear",
            }
        )
        self.assertEqual("/home/test/.codex", environment["CODEX_HOME"])
        self.assertNotIn("OPENAI_API_KEY", environment)
        self.assertNotIn("OPENAI_BASE_URL", environment)
        self.assertNotIn("ANTHROPIC_API_KEY", environment)

    def test_complete_jsonl_trace_returns_last_agent_message(self) -> None:
        events = [
            {
                "type": "thread.started",
                "thread_id": "private",
                "model": "gpt-5.6-terra-20260801",
                "effective_policy": engine_adapters.CODEX_EFFECTIVE_POLICY,
            },
            {"type": "turn.started"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "first"}},
            {"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps({
                "response": "final", "reference_canaries": []
            })}},
            {"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 4}},
        ]
        trace = self.adapter.parse_trace(
            "\n".join(json.dumps(event) for event in events),
            requested_model="gpt-5.6-terra",
        )
        self.assertTrue(trace.complete)
        self.assertEqual("final", trace.response)
        self.assertEqual("gpt-5.6-terra-20260801", trace.resolved_model)
        self.assertRegex(trace.policy_sha256, r"^[0-9a-f]{64}$")
        self.assertEqual({"input_tokens": 10, "output_tokens": 4}, trace.usage)

    def test_complete_trace_without_the_bound_response_shape_is_rejected(self) -> None:
        events = [
            {
                "type": "thread.started",
                "thread_id": "private",
                "model": "gpt-5.6-terra-20260801",
                "effective_policy": engine_adapters.CODEX_EFFECTIVE_POLICY,
            },
            {"type": "item.completed", "item": {"type": "agent_message", "text": "plain text"}},
            {"type": "turn.completed", "usage": {}},
        ]
        with self.assertRaisesRegex(engine_adapters.AdapterError, "structured response"):
            self.adapter.parse_trace(
                "\n".join(json.dumps(event) for event in events),
                requested_model="gpt-5.6-terra",
            )

    def test_trace_without_observed_model_or_policy_is_rejected(self) -> None:
        final = {
            "type": "item.completed",
            "item": {
                "type": "agent_message",
                "text": json.dumps({"response": "final", "reference_canaries": []}),
            },
        }
        completed = {"type": "turn.completed", "usage": {}}
        for started, expected in (
            (
                {"type": "thread.started", "effective_policy": engine_adapters.CODEX_EFFECTIVE_POLICY},
                "resolved model",
            ),
            (
                {"type": "thread.started", "model": "gpt-5.6-terra-20260801"},
                "effective ambient policy",
            ),
        ):
            with self.subTest(expected=expected), self.assertRaisesRegex(
                engine_adapters.AdapterError, expected
            ):
                self.adapter.parse_trace(
                    "\n".join(json.dumps(event) for event in (started, final, completed)),
                    requested_model="gpt-5.6-terra",
                )

    def test_incomplete_or_failed_trace_is_rejected(self) -> None:
        for events in (
            [{"type": "thread.started"}],
            [{"type": "thread.started"}, {"type": "turn.failed", "error": "private"}],
        ):
            with self.subTest(events=events), self.assertRaisesRegex(
                engine_adapters.AdapterError,
                "incomplete|failed",
            ):
                self.adapter.parse_trace(
                    "\n".join(json.dumps(event) for event in events),
                    requested_model="gpt-5.6-terra",
                )


if __name__ == "__main__":
    unittest.main()
