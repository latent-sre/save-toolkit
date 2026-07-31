#!/usr/bin/env python3
"""Offline contract tests for the unified direct/discovery eval runner."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clean_room  # noqa: E402
import run_evals  # noqa: E402


class ScenarioValidationTests(unittest.TestCase):
    def _scenario(self, **updates: object) -> dict:
        scenario = {
            "schema_version": 1,
            "_file": "case.yaml",
            "id": "case",
            "mode": "direct",
            "split": "calibration",
            "target": {"kind": "skill", "name": "merge-gate"},
            "prompt": "Assess whether this change is ready.",
            "success_criteria": ["Returns a verdict"],
            "graders": [{"type": "contains_any", "of": ["pass", "block"]}],
        }
        scenario.update(updates)
        return scenario

    def test_mode_and_split_are_required(self) -> None:
        missing_mode = self._scenario()
        del missing_mode["mode"]
        missing_split = self._scenario()
        del missing_split["split"]
        problems = run_evals.validate([missing_mode, missing_split])
        self.assertTrue(any("missing 'mode'" in p for p in problems))
        self.assertTrue(any("missing 'split'" in p for p in problems))

    def test_discovery_requires_routing_expectation(self) -> None:
        problems = run_evals.validate([self._scenario(mode="discovery")])
        self.assertTrue(any("routing.expect" in p for p in problems))

    def test_scenario_id_cannot_escape_artifact_directory(self) -> None:
        problems = run_evals.validate([self._scenario(id="../escape")])
        self.assertTrue(any("safe lowercase slug" in p for p in problems))

    def test_target_name_cannot_traverse_or_change_case(self) -> None:
        traversing = self._scenario(target={"kind": "skill", "name": "../skills/merge-gate"})
        mixed_case = self._scenario(target={"kind": "skill", "name": "Merge-Gate"})
        problems = run_evals.validate([traversing, mixed_case])
        self.assertGreaterEqual(sum("target name must be a canonical lowercase slug" in p for p in problems), 2)

    def test_discovery_prompt_cannot_name_the_target(self) -> None:
        scenario = self._scenario(
            mode="discovery",
            routing={"expect": "fire"},
            prompt="Use /sre-agents:merge-gate for this request.",
        )
        problems = run_evals.validate([scenario])
        self.assertTrue(any("names its target" in p for p in problems))


class InvocationPlanTests(unittest.TestCase):
    def test_discovery_prompt_is_byte_for_byte_unhinted(self) -> None:
        scenario = {
            "mode": "discovery",
            "target": {"kind": "skill", "name": "merge-gate"},
            "prompt": "raw prompt\nwith exact spacing\n",
        }
        command = run_evals.build_command(scenario, model=None)
        self.assertEqual(command[command.index("-p") + 1], scenario["prompt"])
        self.assertNotIn("sre-agents:merge-gate", command[command.index("-p") + 1])
        self.assertIn("--strict-mcp-config", command)
        self.assertEqual(json.loads(command[command.index("--mcp-config") + 1]), {"mcpServers": {}})
        self.assertEqual(command[command.index("--tools") + 1], "Skill,Task")

    def test_direct_skill_uses_explicit_plugin_invocation(self) -> None:
        scenario = {"mode": "direct", "target": {"kind": "skill", "name": "merge-gate"}, "prompt": "Assess it."}
        command = run_evals.build_command(scenario, model="sonnet")
        prompt = command[command.index("-p") + 1]
        self.assertEqual(prompt, "/sre-agents:merge-gate\n\nAssess it.")
        self.assertEqual(command[command.index("--model") + 1], "sonnet")

    def test_direct_agent_uses_agent_flag_without_rewriting_prompt(self) -> None:
        scenario = {"mode": "direct", "target": {"kind": "agent", "name": "reviewer"}, "prompt": "Review it."}
        command = run_evals.build_command(scenario, model=None)
        self.assertEqual(command[command.index("-p") + 1], "Review it.")
        self.assertEqual(command[command.index("--agent") + 1], "sre-agents:reviewer")

    def test_command_can_bind_an_isolated_plugin_snapshot(self) -> None:
        scenario = {"mode": "direct", "target": {"kind": "skill", "name": "merge-gate"}, "prompt": "Assess it."}
        with run_evals.frozen_plugin_snapshot() as snapshot:
            command = run_evals.build_command(scenario, model=None, plugin_root=snapshot)
            self.assertEqual(Path(command[command.index("--plugin-dir") + 1]), snapshot)
            self.assertEqual(run_evals.plugin_digest(snapshot), run_evals.plugin_digest(run_evals.ROOT))
        self.assertFalse(snapshot.exists())

    def test_live_suite_can_bind_an_isolated_eval_snapshot(self) -> None:
        with run_evals.frozen_eval_snapshot() as snapshot:
            self.assertNotEqual(snapshot, run_evals.EVAL_ROOT)
            self.assertEqual(
                run_evals.eval_suite_digest(snapshot),
                run_evals.eval_suite_digest(run_evals.EVAL_ROOT),
            )
            self.assertTrue((snapshot / "scenarios" / "discovery-merge-readiness.yaml").is_file())
        self.assertFalse(snapshot.exists())

    def test_forged_snapshot_marker_cannot_bypass_bootstrap(self) -> None:
        with mock.patch.dict(
            run_evals.os.environ,
            {run_evals.EVAL_SNAPSHOT_ROOT_ENV: str(run_evals.EVAL_ROOT)},
            clear=False,
        ):
            self.assertFalse(run_evals.is_frozen_eval_process())


class StreamTraceTests(unittest.TestCase):
    def _trace(self, *, with_skill: bool = True) -> str:
        events = [
            {
                "type": "system", "subtype": "init", "session_id": "session-1", "model": "claude-test",
                "tools": ["Skill", "Task"],
                "plugins": [{
                    "name": "sre-agents", "version": "1.0.0", "source": "sre-agents@inline",
                    "path": str(run_evals.ROOT),
                }],
                "mcp_servers": [],
            },
        ]
        if with_skill:
            events.append({
                "type": "assistant",
                "message": {"content": [{
                    "type": "tool_use",
                    "id": "skill-call-1",
                    "name": "Skill",
                    "input": {"skill": "sre-agents:merge-gate"},
                }]},
            })
            events.append({
                "type": "user",
                "message": {"content": [{
                    "type": "tool_result",
                    "tool_use_id": "skill-call-1",
                    "is_error": False,
                    "content": "skill loaded",
                }]},
            })
        events.extend([
            {
                "type": "assistant",
                "message": {"content": [{
                    "type": "tool_use",
                    "id": "agent-call-1",
                    "name": "Agent",
                    "input": {"subagent_type": "sre-agents:reviewer"},
                }]},
            },
            {
                "type": "user",
                "message": {"content": [{
                    "type": "tool_result",
                    "tool_use_id": "agent-call-1",
                    "is_error": False,
                    "content": "review complete",
                }]},
            },
            {
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "session_id": "session-1",
                "result": "MERGE-GATE: BLOCKED",
                "total_cost_usd": 0.01,
            },
        ])
        return "\n".join(json.dumps(e) for e in events)

    def test_parser_extracts_response_invocations_and_runtime_metadata(self) -> None:
        parsed = run_evals.parse_stream_trace(self._trace())
        self.assertEqual(parsed.response, "MERGE-GATE: BLOCKED")
        self.assertEqual(parsed.skills, ("sre-agents:merge-gate",))
        self.assertEqual(parsed.agents, ("sre-agents:reviewer",))
        self.assertEqual(parsed.model, "claude-test")
        self.assertEqual(parsed.session_id, "session-1")
        self.assertEqual(parsed.total_cost_usd, 0.01)
        self.assertEqual(parsed.runtime_plugins[0]["name"], "sre-agents")
        self.assertEqual(parsed.mcp_servers, ())
        self.assertEqual(parsed.available_tools, ("Skill", "Task"))
        run_evals.enforce_runtime_boundary(parsed)

    def test_runtime_boundary_rejects_extra_tools_or_mcp_servers(self) -> None:
        parsed = run_evals.parse_stream_trace(self._trace())
        bad_tools = run_evals.ParsedTrace(**{**parsed.__dict__, "available_tools": ("Skill", "Task", "Bash")})
        with self.assertRaises(clean_room.RunnerFailed):
            run_evals.enforce_runtime_boundary(bad_tools)
        bad_mcp = run_evals.ParsedTrace(**{**parsed.__dict__, "mcp_servers": ({"name": "account-connector"},)})
        with self.assertRaises(clean_room.RunnerFailed):
            run_evals.enforce_runtime_boundary(bad_mcp)
        duplicate_plugin = run_evals.ParsedTrace(
            **{**parsed.__dict__, "runtime_plugins": parsed.runtime_plugins + parsed.runtime_plugins}
        )
        with self.assertRaises(clean_room.RunnerFailed):
            run_evals.enforce_runtime_boundary(duplicate_plugin)
        substituted_plugin = run_evals.ParsedTrace(
            **{**parsed.__dict__, "runtime_plugins": ({
                "name": "sre-agents", "version": "1.0.0", "source": "sre-agents@inline",
                "path": str(run_evals.ROOT.parent / "substitute"),
            },)}
        )
        with self.assertRaises(clean_room.RunnerFailed):
            run_evals.enforce_runtime_boundary(substituted_plugin)

    def test_runtime_boundary_uses_exact_direct_agent_tools(self) -> None:
        parsed = run_evals.parse_stream_trace(self._trace())
        reduced_tools = run_evals.ParsedTrace(**{**parsed.__dict__, "available_tools": ("Skill",)})
        run_evals.enforce_runtime_boundary(reduced_tools, expected_tools=("Skill",))
        with self.assertRaises(clean_room.RunnerFailed):
            run_evals.enforce_runtime_boundary(reduced_tools)

        missing_tools = run_evals.ParsedTrace(**{**parsed.__dict__, "available_tools": ()})
        with self.assertRaises(clean_room.RunnerFailed):
            run_evals.enforce_runtime_boundary(missing_tools, expected_tools=("Skill",))

        extra_tool = run_evals.ParsedTrace(
            **{**parsed.__dict__, "available_tools": ("Skill", "Bash")}
        )
        with self.assertRaises(clean_room.RunnerFailed):
            run_evals.enforce_runtime_boundary(extra_tool, expected_tools=("Skill",))

    def test_direct_agent_tools_are_derived_from_frontmatter(self) -> None:
        reviewer = {"mode": "direct", "target": {"kind": "agent", "name": "reviewer"}}
        sre = {"mode": "direct", "target": {"kind": "agent", "name": "sre"}}
        researcher = {"mode": "direct", "target": {"kind": "agent", "name": "researcher"}}
        discovery = {"mode": "discovery", "target": {"kind": "agent", "name": "reviewer"}}
        self.assertEqual(run_evals.expected_runtime_tools(reviewer), ("Skill",))
        self.assertEqual(run_evals.expected_runtime_tools(sre), ("Skill", "Task"))
        self.assertEqual(run_evals.expected_runtime_tools(researcher), ("Skill",))
        self.assertEqual(run_evals.expected_runtime_tools(discovery), ("Skill", "Task"))

    def test_missing_result_event_is_inconclusive_not_a_response(self) -> None:
        incomplete = json.dumps({"type": "system", "subtype": "init"})
        with self.assertRaises(clean_room.RunnerFailed):
            run_evals.parse_stream_trace(incomplete)

    def test_unmatched_or_errored_tool_calls_do_not_count_as_invocations(self) -> None:
        events = [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "unmatched", "name": "Skill", "input": {"skill": "sre-agents:merge-gate"}},
                {"type": "tool_use", "id": "errored", "name": "Agent", "input": {"subagent_type": "sre-agents:reviewer"}},
            ]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "errored", "is_error": True, "content": "denied"},
            ]}},
            {"type": "result", "subtype": "success", "is_error": False, "result": "done"},
        ]
        parsed = run_evals.parse_stream_trace("\n".join(json.dumps(e) for e in events))
        self.assertEqual(parsed.skills, ())
        self.assertEqual(parsed.agents, ())
        self.assertEqual(parsed.attempted_skills, ("sre-agents:merge-gate",))
        self.assertEqual(parsed.attempted_agents, ("sre-agents:reviewer",))

    def test_inline_answer_cannot_pass_discovery_fire(self) -> None:
        scenario = {
            "mode": "discovery",
            "target": {"kind": "skill", "name": "merge-gate"},
            "routing": {"expect": "fire"},
            "graders": [{"type": "contains_any", "of": ["blocked"]}],
        }
        parsed = run_evals.parse_stream_trace(self._trace(with_skill=False))
        passed, details = run_evals.grade_trial(scenario, parsed)
        self.assertFalse(passed)
        self.assertTrue(any("routing" in detail and "FAIL" in detail for detail in details))

    def test_expected_invocation_and_behavior_both_pass(self) -> None:
        scenario = {
            "mode": "discovery",
            "target": {"kind": "skill", "name": "merge-gate"},
            "routing": {"expect": "fire"},
            "graders": [{"type": "contains_any", "of": ["blocked"]}],
        }
        parsed = run_evals.parse_stream_trace(self._trace())
        passed, _ = run_evals.grade_trial(scenario, parsed)
        self.assertTrue(passed)


class ArtifactTests(unittest.TestCase):
    def test_raw_trace_and_summary_are_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            provenance = {
                "run_id": "run-1",
                "claude_cli_version": "2.1.220",
                "requested_model": "sonnet",
                "plugin_commit": "a" * 40,
                "fixture_sha256": "b" * 64,
            }
            writer = run_evals.ArtifactWriter(root, provenance)
            trace_path = writer.write_trace("scenario", 1, "{\"type\":\"result\"}\n")
            summary_path = writer.write_summary({"verdict": "INCONCLUSIVE"})
            self.assertEqual(trace_path.read_text(encoding="utf-8"), '{"type":"result"}\n')
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["verdict"], "INCONCLUSIVE")
            self.assertEqual(summary["provenance"]["claude_cli_version"], "2.1.220")
            self.assertEqual(summary["provenance"]["requested_model"], "sonnet")
            self.assertEqual(summary["provenance"]["plugin_commit"], "a" * 40)
            self.assertEqual(summary["provenance"]["fixture_sha256"], "b" * 64)
            if sys.platform != "win32":
                self.assertEqual(trace_path.stat().st_mode & 0o077, 0)
            run_evals.assert_private_path(trace_path)

    def test_artifact_writer_rejects_unsafe_scenario_id_defense_in_depth(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            writer = run_evals.ArtifactWriter(Path(td), {"run_id": "run-1"})
            with self.assertRaises(ValueError):
                writer.write_trace("../escape", 1, "secret")

    def test_plugin_provenance_surface_includes_commands_and_guard_scripts(self) -> None:
        self.assertIn("commands", run_evals.PLUGIN_INPUT_PATHS)
        self.assertIn("scripts/readonly-guard.py", run_evals.PLUGIN_INPUT_PATHS)
        self.assertIn("scripts/readonly-guard-hook.sh", run_evals.PLUGIN_INPUT_PATHS)

    def test_required_command_failure_does_not_look_clean(self) -> None:
        failed = mock.Mock(returncode=128, stdout="", stderr="not a git repository")
        with mock.patch.object(run_evals.subprocess, "run", return_value=failed):
            with self.assertRaises(clean_room.RunnerFailed):
                run_evals.required_command_text(["git", "status"])

    def test_storage_failure_is_an_instrument_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "result.json"
            with mock.patch.object(run_evals.os, "open", side_effect=OSError("disk full")):
                with self.assertRaises(clean_room.RunnerFailed):
                    run_evals._private_write(path, "payload")

    def test_results_root_rejects_repository_and_ancestor_without_chmod(self) -> None:
        with self.assertRaises(clean_room.RunnerFailed):
            run_evals.resolve_results_root(run_evals.ROOT)
        with self.assertRaises(clean_room.RunnerFailed):
            run_evals.resolve_results_root(run_evals.ROOT.parent)
        self.assertEqual(
            run_evals.resolve_results_root(run_evals.ROOT / ".eval-runs"),
            (run_evals.ROOT / ".eval-runs").resolve(),
        )

    def test_loaded_scenario_hash_is_bound_to_loaded_bytes(self) -> None:
        scenario = run_evals.load_scenarios()[0]
        source = (run_evals.SCENARIOS_DIR / scenario["_file"]).read_bytes()
        self.assertEqual(scenario["_source_sha256"], hashlib.sha256(source).hexdigest())

    def test_suite_load_refuses_digest_drift(self) -> None:
        with mock.patch.object(run_evals, "eval_suite_digest", side_effect=["before", "after"]):
            with self.assertRaises(clean_room.RunnerFailed):
                run_evals.load_stable_suite()


class AggregateVerdictTests(unittest.TestCase):
    def test_pass_fail_and_inconclusive_are_distinct(self) -> None:
        self.assertEqual(run_evals.aggregate_verdict(["PASS", "PASS"], 1.0), "PASS")
        self.assertEqual(run_evals.aggregate_verdict(["PASS", "FAIL"], 1.0), "FAIL")
        self.assertEqual(run_evals.aggregate_verdict(["PASS", "INCONCLUSIVE"], 0.5), "PASS")
        self.assertEqual(run_evals.aggregate_verdict(["FAIL", "INCONCLUSIVE"], 0.5), "INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
