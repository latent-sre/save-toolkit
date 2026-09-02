#!/usr/bin/env python3
"""Offline contract tests for the unified direct/discovery eval runner."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clean_room  # noqa: E402
import run_evals  # noqa: E402

REPOSITORY_PLUGIN_VERSION = run_evals.plugin_manifest(run_evals.ROOT)["version"]


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

    def test_suite_and_selected_targets_can_use_distinct_revision_roots(self) -> None:
        scenario = self._scenario()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            evaluator = root / "evaluator"
            candidate = root / "candidate"
            (evaluator / "skills" / "merge-gate").mkdir(parents=True)
            (evaluator / "skills" / "merge-gate" / "SKILL.md").write_text(
                "# evaluator component\n", encoding="utf-8"
            )
            candidate.mkdir()

            self.assertEqual([], run_evals.validate([scenario], component_root=evaluator))
            self.assertTrue(
                any(
                    "not a known component" in problem
                    for problem in run_evals.validate([scenario], component_root=candidate)
                )
            )

    def test_a_required_scenario_cannot_be_silently_deleted(self) -> None:
        """Losing a named routing case must fail, not just shrink the suite.

        This contract used to live in an unarmed prose-sync test. Deleting the scenario left
        `--validate` reporting OK with one fewer case, which is the silent failure it exists to
        prevent.
        """
        required = run_evals.REQUIRED_SCENARIO_IDS[0]
        without = self._scenario(mode="discovery", split="regression")
        problems = run_evals.validate([without], full_suite=True)
        self.assertTrue(
            any(f"required scenario {required!r} is missing" in p for p in problems), problems
        )

        present = self._scenario(id=required, mode="discovery", split="regression")
        problems = run_evals.validate([present], full_suite=True)
        self.assertFalse(
            any("required scenario" in p for p in problems), problems
        )

    def test_every_required_scenario_id_exists_in_the_committed_suite(self) -> None:
        ids = {s.get("id") for s in run_evals.load_scenarios()}
        for required in run_evals.REQUIRED_SCENARIO_IDS:
            with self.subTest(scenario=required):
                self.assertIn(required, ids)

    def test_mode_and_split_are_required(self) -> None:
        missing_mode = self._scenario()
        del missing_mode["mode"]
        missing_split = self._scenario()
        del missing_split["split"]
        problems = run_evals.validate([missing_mode, missing_split])
        self.assertTrue(any("missing 'mode'" in p for p in problems))
        self.assertTrue(any("missing 'split'" in p for p in problems))

    def test_visible_cases_use_calibration_or_regression_splits(self) -> None:
        self.assertEqual({"calibration", "regression"}, run_evals.SPLITS)
        problems = run_evals.validate([self._scenario(split="held_out")])
        self.assertTrue(any("split must be one of" in problem for problem in problems))

    def test_discovery_requires_routing_expectation(self) -> None:
        problems = run_evals.validate([self._scenario(mode="discovery")])
        self.assertTrue(any("routing.expect" in p for p in problems))

    def test_agent_discovery_is_calibration_only(self) -> None:
        scenario = self._scenario(
            mode="discovery",
            split="regression",
            target={"kind": "agent", "name": "sre"},
            routing={"expect": "fire"},
        )
        problems = run_evals.validate([scenario])
        self.assertTrue(any("agent-target discovery is calibration-only" in p for p in problems))

    def test_malformed_grader_configuration_reports_instead_of_raising(self) -> None:
        """A grader spec failing its own pre-response validation is a suite problem, not a crash.

        The probe narrowed on TypeError and re.error only, but several graders raise
        ValueError/AttributeError for values that pass the type check (empty `fields`, a
        non-string member of `of`, out-of-range weights). Those escaped and turned a bad
        scenario file into a raw traceback instead of the EVAL SUITE INVALID report.
        """
        malformed = (
            ({"type": "exact_fields", "fields": {}}, "invalid configuration"),
            ({"type": "exact_fields", "fields": {"a": 123}}, "invalid configuration"),
            (
                {
                    "type": "json_artifact_statuses",
                    "artifacts": [],
                    "allowed_statuses": ["ok"],
                    "allowed_evidence": ["e"],
                },
                "invalid configuration",
            ),
            (
                {
                    "type": "cloud_run_rollback_packet",
                    "required_weight": 150,
                    "required_trailing_flags": {},
                    "required_service": "svc-a",
                    "forward_target": "rev-a",
                    "inverse_target": "rev-b",
                },
                "invalid configuration",
            ),
            (
                {"type": "rubric", "name": "no_production_action_claim", "params": {"bogus": 1}},
                "invalid configuration",
            ),
            ({"type": "embedded_exact_json", "fields": {"v": float("nan")}}, "invalid configuration"),
            ({"type": "contains_all", "of": ["ok", 1]}, "invalid configuration"),
        )
        for spec, expected in malformed:
            with self.subTest(spec=spec):
                problems = run_evals.validate([self._scenario(graders=[spec])])
                self.assertTrue(
                    any(f"grader '{spec['type']}'" in p and expected in p for p in problems),
                    problems,
                )
        self.assertTrue(
            any(
                "invalid regex" in p
                for p in run_evals.validate([self._scenario(graders=[{"type": "regex", "pattern": "("}])])
            )
        )
        self.assertTrue(
            any(
                "bad/missing kwargs" in p
                for p in run_evals.validate([self._scenario(graders=[{"type": "contains_all"}])])
            )
        )

    def test_scenario_id_cannot_escape_artifact_directory(self) -> None:
        problems = run_evals.validate([self._scenario(id="../escape")])
        self.assertTrue(any("safe lowercase slug" in p for p in problems))

    def test_target_name_cannot_traverse_or_change_case(self) -> None:
        traversing = self._scenario(target={"kind": "skill", "name": "../skills/merge-gate"})
        mixed_case = self._scenario(target={"kind": "skill", "name": "Merge-Gate"})
        problems = run_evals.validate([traversing, mixed_case])
        self.assertGreaterEqual(sum("target name must be a canonical lowercase slug" in p for p in problems), 2)

    def test_not_fire_scenario_rejects_sub_full_threshold(self) -> None:
        # A negative routing scenario is zero-tolerance; --threshold applies to positives only, so a
        # declared threshold < 1 is a false-green configuration and must be rejected at validate().
        scenario = self._scenario(
            mode="discovery",
            routing={"expect": "not_fire", "expected_alternative": "inline"},
            threshold=0.66,
        )
        problems = run_evals.validate([scenario])
        self.assertTrue(any("zero-tolerance" in p for p in problems))

    def test_not_fire_scenario_allows_full_threshold(self) -> None:
        scenario = self._scenario(
            mode="discovery",
            routing={"expect": "not_fire", "expected_alternative": "inline"},
            threshold=1,
        )
        problems = run_evals.validate([scenario])
        self.assertFalse(any("zero-tolerance" in p for p in problems))

    def test_not_fire_scenario_allows_root_scope(self) -> None:
        # Unlike its siblings, this test calls validate() against the real repository root with no
        # temp-dir override, so the target must be a real skill; merge-gate no longer exists.
        scenario = self._scenario(
            target={"kind": "skill", "name": "production-change-gate"},
            mode="discovery",
            split="regression",
            routing={
                "expect": "not_fire",
                "scope": "root",
                "expected_alternative": {"kind": "agent", "name": "sre"},
            },
        )
        problems = run_evals.validate([scenario])
        self.assertEqual(problems, [])

    def test_routing_scope_rejects_unknown_value(self) -> None:
        scenario = self._scenario(
            mode="discovery",
            split="regression",
            routing={
                "expect": "not_fire",
                "scope": "nested",
                "expected_alternative": {"kind": "agent", "name": "sre"},
            },
        )
        problems = run_evals.validate([scenario])
        self.assertTrue(any("routing.scope must be 'root'" in problem for problem in problems))

    def test_fire_scenario_rejects_routing_scope(self) -> None:
        scenario = self._scenario(
            mode="discovery",
            split="regression",
            routing={"expect": "fire", "scope": "root"},
        )
        problems = run_evals.validate([scenario])
        self.assertTrue(any("routing.scope is only valid for not_fire" in problem for problem in problems))

    def test_root_scope_rejects_inline_expected_alternative(self) -> None:
        scenario = self._scenario(
            mode="discovery",
            split="regression",
            routing={"expect": "not_fire", "scope": "root", "expected_alternative": "inline"},
        )
        problems = run_evals.validate([scenario])
        self.assertTrue(any("routing.scope root requires a component expected_alternative" in p for p in problems))

    def test_discovery_prompt_cannot_name_the_target(self) -> None:
        scenario = self._scenario(
            mode="discovery",
            routing={"expect": "fire"},
            prompt="Use /save-toolkit:merge-gate for this request.",
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
        self.assertNotIn("save-toolkit:merge-gate", command[command.index("-p") + 1])
        self.assertIn("--strict-mcp-config", command)
        self.assertEqual(json.loads(command[command.index("--mcp-config") + 1]), {"mcpServers": {}})
        self.assertEqual(command[command.index("--tools") + 1], "Skill,Task")

    def test_direct_skill_uses_explicit_plugin_invocation(self) -> None:
        scenario = {"mode": "direct", "target": {"kind": "skill", "name": "merge-gate"}, "prompt": "Assess it."}
        command = run_evals.build_command(scenario, model="sonnet")
        prompt = command[command.index("-p") + 1]
        self.assertEqual(
            prompt,
            "Use the Skill tool to invoke `save-toolkit:merge-gate` before answering. "
            "If the Skill call does not complete successfully, do not answer the task.\n\n"
            "Assess it.",
        )
        self.assertFalse(prompt.startswith("/"))
        self.assertEqual(command[command.index("--model") + 1], "sonnet")

    def test_direct_agent_uses_agent_flag_without_rewriting_prompt(self) -> None:
        scenario = {"mode": "direct", "target": {"kind": "agent", "name": "reviewer"}, "prompt": "Review it."}
        command = run_evals.build_command(scenario, model=None)
        self.assertEqual(command[command.index("-p") + 1], "Review it.")
        self.assertEqual(command[command.index("--agent") + 1], "save-toolkit:reviewer")

    def test_command_forwards_subagent_text_without_reusing_a_session(self) -> None:
        scenario = {
            "mode": "discovery",
            "target": {"kind": "skill", "name": "merge-gate"},
            "prompt": "Assess it.",
        }
        command = run_evals.build_command(scenario, model=None)
        self.assertEqual(command.count("--forward-subagent-text"), 1)
        self.assertEqual(command.count("--no-session-persistence"), 1)
        self.assertNotIn("--resume", command)
        self.assertNotIn("--continue", command)

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
            self.assertTrue((snapshot / "scenarios" / "discovery-agent-authoring-loop-engineering.yaml").is_file())
            self.assertTrue((snapshot.parent / "scripts/fleet_frontmatter.py").is_file())
        self.assertFalse(snapshot.parent.exists())

    def test_eval_suite_digest_changes_when_support_file_changes(self) -> None:
        with run_evals.frozen_eval_snapshot() as snapshot:
            digest_before = run_evals.eval_suite_digest(snapshot)
            support_path = snapshot.parent / "scripts/fleet_frontmatter.py"
            original = support_path.read_bytes()
            try:
                support_path.write_bytes(original + b"\n# mutation-sentinel\n")
                digest_after = run_evals.eval_suite_digest(snapshot)
            finally:
                support_path.write_bytes(original)
        self.assertNotEqual(digest_before, digest_after)

    def test_explicit_plugin_root_is_forwarded_to_the_frozen_evaluator(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            candidate = Path(td) / "candidate"
            candidate.mkdir()
            observed: dict[str, object] = {}

            def child(argv, *, cwd, env, check):
                observed["argv"] = argv
                observed["env"] = env
                return mock.Mock(returncode=0)

            with mock.patch.object(run_evals.subprocess, "run", side_effect=child):
                self.assertEqual(
                    0,
                    run_evals.run_from_frozen_eval(
                        ["--run", "--plugin-root", str(candidate)]
                    ),
                )

            self.assertEqual(str(candidate.resolve()), observed["env"]["FLEET_ROOT"])
            self.assertEqual(
                str(run_evals.EVAL_BUNDLE_ROOT.resolve()),
                observed["env"]["FLEET_EVALUATOR_ROOT"],
            )
            self.assertIn("--plugin-root", observed["argv"])

    def test_forged_snapshot_marker_cannot_bypass_bootstrap(self) -> None:
        with mock.patch.dict(
            run_evals.os.environ,
            {run_evals.EVAL_SNAPSHOT_ROOT_ENV: str(run_evals.EVAL_ROOT)},
            clear=False,
        ):
            self.assertFalse(run_evals.is_frozen_eval_process())


class StreamTraceTests(unittest.TestCase):
    @staticmethod
    def _blob(events: list[dict]) -> str:
        return "\n".join(json.dumps(event) for event in events)

    @staticmethod
    def _init_event(session_id: str = "session-1") -> dict:
        return {
            "type": "system",
            "subtype": "init",
            "session_id": session_id,
            "model": "claude-test",
            "tools": ["Skill", "Task"],
            "plugins": [{
                "name": "save-toolkit",
                "version": REPOSITORY_PLUGIN_VERSION,
                "source": "save-toolkit@inline",
                "path": str(run_evals.ROOT),
            }],
            "mcp_servers": [],
        }

    @staticmethod
    def _result_event(
        response: str,
        *,
        session_id: str = "session-1",
        is_error: bool = False,
        parent_tool_use_id: str | None = None,
        continuation: bool = False,
    ) -> dict:
        event = {
            "type": "result",
            "subtype": "error" if is_error else "success",
            "is_error": is_error,
            "session_id": session_id,
            "result": response,
        }
        if parent_tool_use_id is not None:
            event["parent_tool_use_id"] = parent_tool_use_id
        if continuation:
            event["origin"] = {"kind": "task-notification"}
        return event

    @staticmethod
    def _completed_notification(session_id: str = "session-1") -> dict:
        return {
            "type": "system",
            "subtype": "task_notification",
            "session_id": session_id,
            "status": "completed",
            "task_id": "task-1",
            "tool_use_id": "background-agent-call",
        }

    def _trace(self, *, with_skill: bool = True) -> str:
        events = [
            {
                "type": "system", "subtype": "init", "session_id": "session-1", "model": "claude-test",
                "tools": ["Skill", "Task"],
                "plugins": [{
                    "name": "save-toolkit", "version": REPOSITORY_PLUGIN_VERSION,
                    "source": "save-toolkit@inline",
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
                    "input": {"skill": "save-toolkit:merge-gate"},
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
                    "input": {"subagent_type": "save-toolkit:reviewer"},
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

    def _scoped_routing_trace(
        self,
        *,
        root_skills: tuple[str, ...] = (),
        root_agents: tuple[str, ...] = (),
        nested_skills: tuple[str, ...] = (),
        nested_agents: tuple[str, ...] = (),
        nested_skill_parent: str = "agent-root-0",
        nested_agent_parent: str = "agent-root-0",
    ) -> str:
        events = [self._init_event()]

        def append_completed(kind: str, name: str, ordinal: int, parent: str | None) -> None:
            tool_name = "Skill" if kind == "skill" else "Agent"
            input_key = "skill" if kind == "skill" else "subagent_type"
            tool_id = f"{kind}-{parent or 'root'}-{ordinal}"
            call = {
                "type": "assistant",
                "session_id": "session-1",
                "message": {"content": [{
                    "type": "tool_use",
                    "id": tool_id,
                    "name": tool_name,
                    "input": {input_key: f"save-toolkit:{name}"},
                }]},
            }
            result = {
                "type": "user",
                "session_id": "session-1",
                "message": {"content": [{
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "is_error": False,
                    "content": "completed",
                }]},
            }
            if parent is not None:
                call["parent_tool_use_id"] = parent
                result["parent_tool_use_id"] = parent
            events.extend((call, result))

        for ordinal, name in enumerate(root_skills):
            append_completed("skill", name, ordinal, None)
        for ordinal, name in enumerate(root_agents):
            append_completed("agent", name, ordinal, None)
        for ordinal, name in enumerate(nested_skills):
            append_completed("skill", name, ordinal, nested_skill_parent)
        for ordinal, name in enumerate(nested_agents):
            append_completed("agent", name, ordinal, nested_agent_parent)
        events.append(self._result_event("incident triage completed"))
        return self._blob(events)

    def test_parser_extracts_response_invocations_and_runtime_metadata(self) -> None:
        parsed = run_evals.parse_stream_trace(self._trace())
        self.assertEqual(parsed.response, "MERGE-GATE: BLOCKED")
        self.assertEqual(parsed.skills, ("save-toolkit:merge-gate",))
        self.assertEqual(parsed.agents, ("save-toolkit:reviewer",))
        self.assertEqual(parsed.model, "claude-test")
        self.assertEqual(parsed.session_id, "session-1")
        self.assertEqual(parsed.total_cost_usd, 0.01)
        self.assertEqual(parsed.runtime_plugins[0]["name"], "save-toolkit")
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
                "name": "save-toolkit", "version": REPOSITORY_PLUGIN_VERSION,
                "source": "save-toolkit@inline",
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

    def test_runtime_boundary_tolerates_declared_grep_glob_in_either_state(self) -> None:
        """A pinned agent's declared Grep/Glob may be advertised or not (CLI drift, HOST-003).

        Both inventories grade; an undeclared tool still refuses; a missing required tool still refuses.
        """
        parsed = run_evals.parse_stream_trace(self._trace())
        expected, optional = ("Skill", "Task"), ("Glob", "Grep")
        without = run_evals.ParsedTrace(**{**parsed.__dict__, "available_tools": ("Skill", "Task")})
        run_evals.enforce_runtime_boundary(without, expected_tools=expected, optional_tools=optional)
        with_them = run_evals.ParsedTrace(**{**parsed.__dict__, "available_tools": ("Glob", "Grep", "Skill", "Task")})
        run_evals.enforce_runtime_boundary(with_them, expected_tools=expected, optional_tools=optional)
        one_of_them = run_evals.ParsedTrace(**{**parsed.__dict__, "available_tools": ("Grep", "Skill", "Task")})
        run_evals.enforce_runtime_boundary(one_of_them, expected_tools=expected, optional_tools=optional)
        undeclared = run_evals.ParsedTrace(**{**parsed.__dict__, "available_tools": ("Read", "Skill", "Task")})
        with self.assertRaises(clean_room.RunnerFailed):
            run_evals.enforce_runtime_boundary(undeclared, expected_tools=expected, optional_tools=optional)
        missing_required = run_evals.ParsedTrace(**{**parsed.__dict__, "available_tools": ("Glob", "Grep", "Skill")})
        with self.assertRaises(clean_room.RunnerFailed):
            run_evals.enforce_runtime_boundary(missing_required, expected_tools=expected, optional_tools=optional)

    def test_direct_agent_tools_are_derived_from_frontmatter(self) -> None:
        reviewer = {"mode": "direct", "target": {"kind": "agent", "name": "reviewer"}}
        sre = {"mode": "direct", "target": {"kind": "agent", "name": "sre"}}
        skill = {
            "mode": "direct",
            "target": {"kind": "skill", "name": "incident-command"},
        }
        researcher = {"mode": "direct", "target": {"kind": "agent", "name": "researcher"}}
        repository_investigator = {
            "mode": "direct",
            "target": {"kind": "agent", "name": "repository-investigator"},
        }
        discovery = {"mode": "discovery", "target": {"kind": "agent", "name": "reviewer"}}
        self.assertEqual(run_evals.expected_runtime_tools(reviewer), ())
        # A pinned agent's declared Grep/Glob are optional inventory, not required: CLI
        # 2.1.243-2.1.246 advertised them, 2.1.250 does not, and the same frontmatter must grade on
        # both (HOST-003). Required stays exact.
        self.assertEqual(run_evals.expected_runtime_tools(sre), ("Skill", "Task"))
        self.assertEqual(run_evals.optional_runtime_tools(sre), ("Glob", "Grep"))
        self.assertEqual(
            run_evals.expected_runtime_tools(sre, enable_snapshot_reads=True),
            ("Read", "Skill", "Task"),
        )
        # reviewer declares Read/Grep/Glob with no Skill/Agent: nothing required, Grep/Glob optional.
        self.assertEqual(run_evals.optional_runtime_tools(reviewer), ("Glob", "Grep"))
        self.assertEqual(run_evals.optional_runtime_tools(researcher), ())
        self.assertEqual(run_evals.optional_runtime_tools(discovery), ())
        self.assertEqual(run_evals.expected_runtime_tools(skill), ("Skill", "Task"))
        self.assertEqual(
            run_evals.expected_runtime_tools(skill, enable_snapshot_reads=True),
            ("Glob", "Grep", "Read", "Skill", "Task"),
        )
        self.assertEqual(run_evals.expected_runtime_tools(researcher), ())
        self.assertEqual(run_evals.expected_runtime_tools(repository_investigator), ())
        # Agent-target discovery must include the three read tools (EVAL-008): the CLI refuses to
        # spawn a subagent whose declared tools resolve to nothing, and reviewer's own tools are
        # Read/Grep/Glob with no Skill or Agent grant.
        self.assertEqual(
            run_evals.expected_runtime_tools(discovery), ("Glob", "Grep", "Read", "Skill", "Task")
        )

    def test_agent_target_discovery_includes_read_tools_skill_target_does_not(self) -> None:
        agent_discovery = {"mode": "discovery", "target": {"kind": "agent", "name": "scribe"}}
        skill_discovery = {"mode": "discovery", "target": {"kind": "skill", "name": "runbook"}}
        agent_tools = run_evals.expected_runtime_tools(agent_discovery)
        skill_tools = run_evals.expected_runtime_tools(skill_discovery)
        self.assertIn("Read", agent_tools)
        self.assertIn("Grep", agent_tools)
        self.assertIn("Glob", agent_tools)
        self.assertNotIn("Read", skill_tools)
        self.assertNotIn("Grep", skill_tools)
        self.assertNotIn("Glob", skill_tools)
        self.assertEqual(skill_tools, ("Skill", "Task"))

    def test_agent_target_discovery_reads_are_callable_inside_the_workspace(self) -> None:
        """A granted read that is not callable makes the trial INCONCLUSIVE at the boundary check
        (`unexpected callable read tool`), which would defeat EVAL-008. Agent-target discovery
        registers the three read tools as callable and the harness-owned workspace as the root a
        relative read may resolve into; nothing else gets either."""
        workspace = Path("/tmp/neutral-workspace")
        agent_discovery = {"mode": "discovery", "target": {"kind": "agent", "name": "scribe"}}
        skill_discovery = {"mode": "discovery", "target": {"kind": "skill", "name": "runbook"}}
        direct_agent = {"mode": "direct", "target": {"kind": "agent", "name": "scribe"}}
        self.assertTrue(run_evals.agent_target_discovery(agent_discovery))
        self.assertFalse(run_evals.agent_target_discovery(skill_discovery))
        self.assertFalse(run_evals.agent_target_discovery(direct_agent))
        self.assertEqual(
            run_evals.discovery_boundary_options(agent_discovery, workspace),
            {"callable_read_tools": run_evals.engine_adapters.READ_TOOLS, "allowed_roots": (workspace,)},
        )
        self.assertEqual(run_evals.discovery_boundary_options(skill_discovery, workspace), {})
        self.assertEqual(run_evals.discovery_boundary_options(direct_agent, workspace), {})

    def test_direct_agent_frontmatter_uses_the_snapshotted_shared_strict_parser(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "agents").mkdir()
            (root / "scripts").mkdir()
            shutil.copy2(
                run_evals.ROOT / "scripts/fleet_frontmatter.py",
                root / "scripts/fleet_frontmatter.py",
            )
            (root / "agents/probe.md").write_text(
                "---\nname: probe\ntools:\n  - Skill\n  - Agent(reviewer)\n---\nbody\n",
                encoding="utf-8",
            )
            scenario = {"mode": "direct", "target": {"kind": "agent", "name": "probe"}}
            with mock.patch.object(
                run_evals.yaml,
                "safe_load",
                side_effect=AssertionError("frontmatter must not use PyYAML"),
            ):
                self.assertEqual(
                    run_evals.expected_runtime_tools(scenario, root), ("Skill", "Task")
                )

    def test_direct_agent_frontmatter_rejects_duplicate_tools(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "agents").mkdir()
            (root / "scripts").mkdir()
            shutil.copy2(
                run_evals.ROOT / "scripts/fleet_frontmatter.py",
                root / "scripts/fleet_frontmatter.py",
            )
            (root / "agents/probe.md").write_text(
                "---\nname: probe\ntools: Skill\ntools: Agent(reviewer)\n---\nbody\n",
                encoding="utf-8",
            )
            scenario = {"mode": "direct", "target": {"kind": "agent", "name": "probe"}}
            with self.assertRaisesRegex(clean_room.RunnerFailed, "duplicate frontmatter key"):
                run_evals.expected_runtime_tools(scenario, root)

    def test_direct_agent_frontmatter_never_executes_the_measured_parser(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / "measured-parser-executed"
            (root / "agents").mkdir()
            (root / "scripts").mkdir()
            trusted_parser = run_evals.TRUSTED_FRONTMATTER_PATH
            candidate_source = trusted_parser.read_text(encoding="utf-8")
            candidate_source += (
                f"\nPath({str(marker)!r}).write_text('executed', encoding='utf-8')\n"
            )
            (root / "scripts/fleet_frontmatter.py").write_text(
                candidate_source,
                encoding="utf-8",
            )
            (root / "agents/probe.md").write_text(
                "---\nname: probe\ntools:\n  - Skill\n---\nbody\n",
                encoding="utf-8",
            )
            scenario = {"mode": "direct", "target": {"kind": "agent", "name": "probe"}}

            with self.assertRaisesRegex(
                clean_room.RunnerFailed,
                "differs from the trusted eval harness",
            ):
                run_evals.expected_runtime_tools(scenario, root)
            self.assertFalse(marker.exists())

    def test_direct_agent_tool_boundary_is_frozen_before_child_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "agents").mkdir()
            (root / "scripts").mkdir()
            shutil.copy2(
                run_evals.TRUSTED_FRONTMATTER_PATH,
                root / "scripts/fleet_frontmatter.py",
            )
            agent_path = root / "agents/probe.md"
            agent_path.write_text(
                "---\nname: probe\ntools:\n  - Skill\n---\nbody\n",
                encoding="utf-8",
            )
            scenario = {
                "mode": "direct",
                "target": {"kind": "agent", "name": "probe"},
                "prompt": "probe",
            }
            completed = mock.Mock(returncode=0, stdout="trace", stderr="")
            parsed = mock.Mock()

            def mutate_agent(*args: object, **kwargs: object) -> mock.Mock:
                agent_path.write_text(
                    "---\nname: probe\ntools:\n  - Agent(reviewer)\n---\nbody\n",
                    encoding="utf-8",
                )
                return completed

            with (
                mock.patch.object(run_evals, "build_command", return_value=["claude"]),
                mock.patch.object(run_evals.subprocess, "run", side_effect=mutate_agent),
                mock.patch.object(run_evals, "parse_stream_trace", return_value=parsed),
                mock.patch.object(run_evals, "enforce_runtime_boundary") as enforce,
            ):
                run_evals.run_agent(
                    scenario,
                    env={},
                    cwd=root,
                    timeout=30,
                    model=None,
                    plugin_root=root,
                )

            enforce.assert_called_once_with(parsed, root, expected_tools=("Skill",), optional_tools=())

    def test_parser_mismatch_refuses_discovery_child_before_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "agents").mkdir()
            (root / "scripts").mkdir()
            parser_path = root / "scripts/fleet_frontmatter.py"
            parser_path.write_bytes(run_evals.TRUSTED_FRONTMATTER_PATH.read_bytes() + b"\n# drift\n")
            (root / "agents/probe.md").write_text(
                "---\nname: probe\ntools:\n  - Skill\n---\nbody\n",
                encoding="utf-8",
            )
            scenario = {
                "mode": "discovery",
                "target": {"kind": "skill", "name": "merge-gate"},
                "prompt": "probe",
            }
            completed = mock.Mock(returncode=0, stdout="trace", stderr="")

            with (
                mock.patch.object(run_evals, "build_command", return_value=["claude"]),
                mock.patch.object(run_evals.subprocess, "run", return_value=completed) as child,
                mock.patch.object(run_evals, "parse_stream_trace", return_value=mock.Mock()),
                mock.patch.object(run_evals, "enforce_runtime_boundary"),
            ):
                with self.assertRaisesRegex(
                    clean_room.RunnerFailed,
                    "differs from the trusted eval harness",
                ):
                    run_evals.run_agent(
                        scenario,
                        env={},
                        cwd=root,
                        timeout=30,
                        model=None,
                        plugin_root=root,
                    )

            child.assert_not_called()

    def test_discovery_preloads_trusted_parser_before_cross_trial_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "plugin"
            trusted_path = Path(temporary) / "eval-bundle/scripts/fleet_frontmatter.py"
            (root / "agents").mkdir(parents=True)
            (root / "scripts").mkdir()
            trusted_path.parent.mkdir(parents=True)
            safe_parser = run_evals.TRUSTED_FRONTMATTER_PATH.read_bytes()
            measured_path = root / "scripts/fleet_frontmatter.py"
            measured_path.write_bytes(safe_parser)
            trusted_path.write_bytes(safe_parser)
            (root / "agents/probe.md").write_text(
                "---\nname: probe\ntools:\n  - Skill\n---\nbody\n",
                encoding="utf-8",
            )
            marker = Path(temporary) / "mutated-parser-executed"
            mutated_parser = safe_parser + (
                f"\nPath({str(marker)!r}).write_text('executed', encoding='utf-8')\n"
            ).encode("utf-8")
            discovery = {
                "mode": "discovery",
                "target": {"kind": "skill", "name": "merge-gate"},
                "prompt": "probe",
            }
            direct = {"mode": "direct", "target": {"kind": "agent", "name": "probe"}}
            completed = mock.Mock(returncode=0, stdout="trace", stderr="")

            def mutate_both_copies(*args: object, **kwargs: object) -> mock.Mock:
                measured_path.write_bytes(mutated_parser)
                trusted_path.write_bytes(mutated_parser)
                return completed

            run_evals._load_trusted_frontmatter_parser.cache_clear()
            try:
                with mock.patch.object(run_evals, "TRUSTED_FRONTMATTER_PATH", trusted_path):
                    with (
                        mock.patch.object(run_evals, "build_command", return_value=["claude"]),
                        mock.patch.object(run_evals.subprocess, "run", side_effect=mutate_both_copies),
                        mock.patch.object(run_evals, "parse_stream_trace", return_value=mock.Mock()),
                        mock.patch.object(run_evals, "enforce_runtime_boundary"),
                    ):
                        run_evals.run_agent(
                            discovery,
                            env={},
                            cwd=root,
                            timeout=30,
                            model=None,
                            plugin_root=root,
                        )
                    self.assertEqual(run_evals.expected_runtime_tools(direct, root), ("Skill",))
            finally:
                run_evals._load_trusted_frontmatter_parser.cache_clear()

            self.assertFalse(marker.exists())

    def test_missing_result_event_is_inconclusive_not_a_response(self) -> None:
        incomplete = json.dumps({"type": "system", "subtype": "init"})
        with self.assertRaises(clean_room.RunnerFailed):
            run_evals.parse_stream_trace(incomplete)

    def test_parser_records_read_attempt_path_and_outcome(self) -> None:
        events = [
            self._init_event(),
            {"type": "assistant", "session_id": "session-1", "message": {"content": [{
                "type": "tool_use",
                "id": "read-1",
                "name": "Read",
                "input": {"file_path": "/tmp/frozen/skills/x/references/a.md"},
            }]}},
            {"type": "user", "session_id": "session-1", "message": {"content": [{
                "type": "tool_result",
                "tool_use_id": "read-1",
                "is_error": False,
                "content": "reference body q_probe_1234",
            }]}},
            self._result_event("done"),
        ]
        parsed = run_evals.parse_stream_trace(self._blob(events))
        self.assertEqual(
            parsed.tool_attempts,
            (run_evals.engine_adapters.ToolAttempt(
                tool="Read",
                path="/tmp/frozen/skills/x/references/a.md",
                outcome="allowed",
            ),),
        )
        self.assertEqual(parsed.observed_canaries, ("q_probe_1234",))

    def test_runtime_boundary_rejects_successful_read_outside_snapshot(self) -> None:
        parsed = run_evals.parse_stream_trace(self._trace())
        unsafe = run_evals.ParsedTrace(
            **{
                **parsed.__dict__,
                "tool_attempts": (
                    run_evals.engine_adapters.ToolAttempt(
                        tool="Read", path="/etc/passwd", outcome="allowed"
                    ),
                ),
            }
        )
        with self.assertRaisesRegex(clean_room.RunnerFailed, "out-of-snapshot"):
            run_evals.enforce_runtime_boundary(
                unsafe,
                expected_tools=("Skill", "Task"),
                callable_read_tools=("Read",),
            )

    def test_coherent_task_notification_continuation_uses_final_root_response(self) -> None:
        events = [
            self._init_event(),
            self._completed_notification(),
            self._init_event(),
            self._result_event("intermediate root response"),
            self._result_event("final continued response", continuation=True),
        ]
        parsed = run_evals.parse_stream_trace(self._blob(events))
        self.assertEqual(parsed.response, "final continued response")
        diagnostics = parsed.stream_diagnostics.to_summary()
        self.assertEqual(diagnostics["init_count"], 2)
        self.assertEqual(diagnostics["result_count"], 2)
        self.assertEqual(diagnostics["root_result_count"], 2)
        self.assertEqual(diagnostics["parented_result_count"], 0)
        self.assertEqual(diagnostics["continuation_count"], 1)
        self.assertIs(diagnostics["same_session"], True)
        self.assertEqual(
            diagnostics["intermediate_root_results"],
            [{"ordinal": 1, "subtype": "success", "is_error": False, "origin": None}],
        )
        serialized = json.dumps(diagnostics)
        self.assertNotIn("intermediate root response", serialized)
        self.assertNotIn("final continued response", serialized)

    def test_diagnostics_whitelist_untrusted_result_labels(self) -> None:
        events = [
            self._init_event(),
            self._completed_notification(),
            self._init_event(),
            self._result_event("intermediate root response"),
            self._result_event("final continued response", continuation=True),
        ]
        events[-2]["subtype"] = "private subtype value"
        events[-2]["origin"] = {"kind": "private origin value"}
        with self.assertRaises(clean_room.RunnerFailed) as caught:
            run_evals.parse_stream_trace(self._blob(events))
        serialized = json.dumps(caught.exception.stream_diagnostics)
        self.assertNotIn("private subtype value", serialized)
        self.assertNotIn("private origin value", serialized)
        self.assertEqual(
            caught.exception.stream_diagnostics["intermediate_root_results"],
            [{"ordinal": 1, "subtype": "unknown", "is_error": False, "origin": "unknown"}],
        )

    def test_mixed_session_concatenation_fails_closed(self) -> None:
        events = [
            self._init_event("session-1"),
            self._result_event("first", session_id="session-1"),
            self._init_event("session-2"),
            self._result_event("second", session_id="session-2"),
        ]
        with self.assertRaisesRegex(clean_room.RunnerFailed, "mixed session"):
            run_evals.parse_stream_trace(self._blob(events))

    def test_parented_result_is_diagnostic_not_the_root_response(self) -> None:
        events = [
            self._init_event(),
            self._result_event("nested response", parent_tool_use_id="agent-call"),
            self._result_event("root response"),
        ]
        parsed = run_evals.parse_stream_trace(self._blob(events))
        self.assertEqual(parsed.response, "root response")
        diagnostics = parsed.stream_diagnostics.to_summary()
        self.assertEqual(diagnostics["result_count"], 2)
        self.assertEqual(diagnostics["root_result_count"], 1)
        self.assertEqual(diagnostics["parented_result_count"], 1)

    def test_earlier_root_error_followed_by_success_fails_closed(self) -> None:
        events = [
            self._init_event(),
            self._completed_notification(),
            self._init_event(),
            self._result_event("failed root", is_error=True),
            self._result_event("later success", continuation=True),
        ]
        with self.assertRaisesRegex(clean_room.RunnerFailed, "root result.*error"):
            run_evals.parse_stream_trace(self._blob(events))

    def test_unfinished_epoch_after_a_completed_result_fails_closed(self) -> None:
        events = [
            self._init_event(),
            self._result_event("completed response"),
            self._completed_notification(),
            self._init_event(),
        ]
        with self.assertRaisesRegex(clean_room.RunnerFailed, "unfinished root epoch"):
            run_evals.parse_stream_trace(self._blob(events))

    def test_root_result_before_first_init_fails_closed(self) -> None:
        events = [
            self._result_event("stale response"),
            self._init_event(),
            self._completed_notification(),
            self._init_event(),
            self._result_event("continued response", continuation=True),
        ]
        with self.assertRaisesRegex(clean_room.RunnerFailed, "before the first init"):
            run_evals.parse_stream_trace(self._blob(events))

    def test_reordered_runtime_lists_remain_one_coherent_epoch_contract(self) -> None:
        first_init = self._init_event()
        first_init["skills"] = ["save-toolkit:zeta", "save-toolkit:alpha"]
        first_init["agents"] = ["save-toolkit:zeta", "save-toolkit:alpha"]
        second_init = self._init_event()
        second_init["tools"] = list(reversed(second_init["tools"]))
        second_init["skills"] = list(reversed(first_init["skills"]))
        second_init["agents"] = list(reversed(first_init["agents"]))
        events = [
            first_init,
            self._completed_notification(),
            second_init,
            self._result_event("initial response"),
            self._result_event("continued response", continuation=True),
        ]
        parsed = run_evals.parse_stream_trace(self._blob(events))
        self.assertEqual(parsed.response, "continued response")
        self.assertEqual(parsed.available_tools, ("Skill", "Task"))
        self.assertEqual(
            parsed.available_skills,
            ("save-toolkit:alpha", "save-toolkit:zeta"),
        )

    def test_timeout_after_an_unfinished_epoch_never_accepts_the_prior_result(self) -> None:
        events = [
            self._init_event(),
            self._result_event("completed but stale response"),
            self._completed_notification(),
            self._init_event(),
        ]
        timed_out = run_evals.subprocess.TimeoutExpired(
            ["claude"],
            30,
            output=self._blob(events),
            stderr="",
        )
        scenario = {
            "mode": "discovery",
            "target": {"kind": "skill", "name": "merge-gate"},
            "prompt": "private prompt",
        }
        with mock.patch.object(run_evals.subprocess, "run", side_effect=timed_out):
            with self.assertRaisesRegex(run_evals.InconclusiveTrial, "timed out") as caught:
                run_evals.run_agent(
                    scenario,
                    env={},
                    cwd=run_evals.ROOT,
                    timeout=30,
                    model=None,
                )
        diagnostics = caught.exception.stream_diagnostics
        self.assertEqual(diagnostics["init_count"], 2)
        self.assertEqual(diagnostics["root_result_count"], 1)
        self.assertEqual(diagnostics["continuation_count"], 0)

    def test_duplicate_tool_ids_under_different_parents_do_not_conflate(self) -> None:
        events = [
            self._init_event(),
            {"type": "assistant", "session_id": "session-1", "message": {"content": [{
                "type": "tool_use", "id": "duplicate", "name": "Skill",
                "input": {"skill": "save-toolkit:root-skill"},
            }]}},
            {
                "type": "assistant",
                "session_id": "session-1",
                "parent_tool_use_id": "agent-call",
                "message": {"content": [{
                    "type": "tool_use", "id": "duplicate", "name": "Skill",
                    "input": {"skill": "save-toolkit:nested-skill"},
                }]},
            },
            {"type": "user", "session_id": "session-1", "message": {"content": [{
                "type": "tool_result", "tool_use_id": "duplicate", "is_error": False,
                "content": "loaded",
            }]}},
            self._result_event("done"),
        ]
        parsed = run_evals.parse_stream_trace(self._blob(events))
        self.assertEqual(parsed.skills, ("save-toolkit:root-skill",))
        self.assertEqual(
            parsed.attempted_skills,
            ("save-toolkit:root-skill", "save-toolkit:nested-skill"),
        )

    def test_conflicting_duplicate_tool_id_within_same_parent_fails_closed(self) -> None:
        events = [
            self._init_event(),
            {"type": "assistant", "session_id": "session-1", "message": {"content": [{
                "type": "tool_use", "id": "duplicate", "name": "Agent",
                "input": {"subagent_type": "save-toolkit:sre"},
            }]}},
            {"type": "assistant", "session_id": "session-1", "message": {"content": [{
                "type": "tool_use", "id": "duplicate", "name": "Agent",
                "input": {"subagent_type": "save-toolkit:agent-engineer"},
            }]}},
            {"type": "user", "session_id": "session-1", "message": {"content": [{
                "type": "tool_result", "tool_use_id": "duplicate", "is_error": False,
                "content": "completed",
            }]}},
            self._result_event("done"),
        ]
        with self.assertRaisesRegex(clean_room.RunnerFailed, "duplicate component tool_use"):
            run_evals.parse_stream_trace(self._blob(events))

    def test_duplicate_tool_ids_across_epochs_do_not_conflate(self) -> None:
        events = [
            self._init_event(),
            {"type": "assistant", "session_id": "session-1", "message": {"content": [{
                "type": "tool_use", "id": "duplicate", "name": "Skill",
                "input": {"skill": "save-toolkit:first-epoch"},
            }]}},
            {"type": "user", "session_id": "session-1", "message": {"content": [{
                "type": "tool_result", "tool_use_id": "duplicate", "is_error": False,
                "content": "loaded",
            }]}},
            self._completed_notification(),
            self._init_event(),
            {"type": "assistant", "session_id": "session-1", "message": {"content": [{
                "type": "tool_use", "id": "duplicate", "name": "Skill",
                "input": {"skill": "save-toolkit:second-epoch"},
            }]}},
            self._result_event("initial response"),
            self._result_event("continued response", continuation=True),
        ]
        parsed = run_evals.parse_stream_trace(self._blob(events))
        self.assertEqual(parsed.skills, ("save-toolkit:first-epoch",))

    def test_inconclusive_trial_exposes_only_sanitized_stream_diagnostics(self) -> None:
        events = [
            self._init_event("session-1"),
            self._result_event("private first response", session_id="session-1"),
            self._init_event("session-2"),
            self._result_event("private second response", session_id="session-2"),
        ]
        completed = mock.Mock(returncode=0, stdout=self._blob(events), stderr="")
        scenario = {
            "mode": "discovery",
            "target": {"kind": "skill", "name": "merge-gate"},
            "prompt": "private prompt",
        }
        with mock.patch.object(run_evals.subprocess, "run", return_value=completed):
            with self.assertRaises(run_evals.InconclusiveTrial) as caught:
                run_evals.run_agent(
                    scenario,
                    env={},
                    cwd=run_evals.ROOT,
                    timeout=30,
                    model=None,
                )
        diagnostics = caught.exception.stream_diagnostics
        self.assertEqual(diagnostics["init_count"], 2)
        self.assertEqual(diagnostics["result_count"], 2)
        self.assertIs(diagnostics["same_session"], False)
        serialized = json.dumps(diagnostics)
        self.assertNotIn("private prompt", serialized)
        self.assertNotIn("private first response", serialized)
        self.assertNotIn("private second response", serialized)

    def test_post_parse_canary_failure_retains_proven_model_policy_and_canaries(self) -> None:
        parsed = run_evals.parse_stream_trace(self._trace())
        completed = mock.Mock(returncode=0, stdout=self._trace(), stderr="")
        scenario = {
            "mode": "direct",
            "target": {"kind": "agent", "name": "sre"},
            "prompt": "private prompt",
        }
        with (
            mock.patch.object(run_evals, "build_command", return_value=["claude"]),
            mock.patch.object(run_evals, "expected_runtime_tools", return_value=("Skill", "Task")),
            mock.patch.object(run_evals, "expected_canaries_for_paths", return_value={"ref": "q_probe_1234"}),
            mock.patch.object(run_evals.subprocess, "run", return_value=completed),
            mock.patch.object(run_evals, "parse_stream_trace", return_value=parsed),
            mock.patch.object(run_evals, "enforce_runtime_boundary"),
        ):
            with self.assertRaisesRegex(run_evals.InconclusiveTrial, "canary") as caught:
                run_evals.run_agent(
                    scenario,
                    env={},
                    cwd=run_evals.ROOT,
                    timeout=30,
                    model="sonnet",
                    required_references=("skills/x/references/a.md",),
                    denied_probe_path=run_evals.ROOT.parent / "denied",
                )

        self.assertEqual(caught.exception.resolved_model, "claude-test")
        self.assertIsNotNone(caught.exception.policy_sha256)
        self.assertEqual(caught.exception.expected_canaries, ("q_probe_1234",))
        self.assertEqual(caught.exception.observed_canaries, ())
        self.assertIs(caught.exception.parsed_trace, parsed)
        self.assertTrue(caught.exception.model_executed)

    def test_unmatched_or_errored_tool_calls_do_not_count_as_invocations(self) -> None:
        events = [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "unmatched", "name": "Skill", "input": {"skill": "save-toolkit:merge-gate"}},
                {"type": "tool_use", "id": "errored", "name": "Agent", "input": {"subagent_type": "save-toolkit:reviewer"}},
            ]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "errored", "is_error": True, "content": "denied"},
            ]}},
            {"type": "result", "subtype": "success", "is_error": False, "result": "done"},
        ]
        parsed = run_evals.parse_stream_trace("\n".join(json.dumps(e) for e in events))
        self.assertEqual(parsed.skills, ())
        self.assertEqual(parsed.agents, ())
        self.assertEqual(parsed.attempted_skills, ("save-toolkit:merge-gate",))
        self.assertEqual(parsed.attempted_agents, ("save-toolkit:reviewer",))

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

    def test_root_scope_allows_nested_target_after_root_alternative_owns(self) -> None:
        parsed = run_evals.parse_stream_trace(self._scoped_routing_trace(
            root_agents=("sre",),
            nested_skills=("gcp-ops",),
        ))
        scenario = {
            "target": {"kind": "skill", "name": "gcp-ops"},
            "routing": {
                "expect": "not_fire",
                "scope": "root",
                "expected_alternative": {"kind": "agent", "name": "sre"},
            },
        }
        passed, _ = run_evals.grade_routing(scenario, parsed)
        self.assertTrue(passed)
        self.assertEqual(parsed.root_skills, ())
        self.assertEqual(parsed.root_agents, ("save-toolkit:sre",))
        self.assertEqual(parsed.skills, ("save-toolkit:gcp-ops",))

    def test_root_identity_evidence_excludes_noncanonical_tool_input(self) -> None:
        parsed = run_evals.parse_stream_trace(self._scoped_routing_trace(
            root_skills=("private prompt content",),
        ))
        self.assertEqual(parsed.root_skills, ())

    def test_default_scope_rejects_nested_target(self) -> None:
        parsed = run_evals.parse_stream_trace(self._scoped_routing_trace(
            root_agents=("sre",),
            nested_skills=("gcp-ops",),
        ))
        scenario = {
            "target": {"kind": "skill", "name": "gcp-ops"},
            "routing": {
                "expect": "not_fire",
                "expected_alternative": {"kind": "agent", "name": "sre"},
            },
        }
        passed, _ = run_evals.grade_routing(scenario, parsed)
        self.assertFalse(passed)

    def test_root_scope_rejects_root_target(self) -> None:
        parsed = run_evals.parse_stream_trace(self._scoped_routing_trace(
            root_skills=("gcp-ops",),
            root_agents=("sre",),
        ))
        scenario = {
            "target": {"kind": "skill", "name": "gcp-ops"},
            "routing": {
                "expect": "not_fire",
                "scope": "root",
                "expected_alternative": {"kind": "agent", "name": "sre"},
            },
        }
        passed, _ = run_evals.grade_routing(scenario, parsed)
        self.assertFalse(passed)

    def test_root_scope_requires_root_alternative(self) -> None:
        parsed = run_evals.parse_stream_trace(self._scoped_routing_trace(
            nested_agents=("sre",),
        ))
        scenario = {
            "target": {"kind": "skill", "name": "gcp-ops"},
            "routing": {
                "expect": "not_fire",
                "scope": "root",
                "expected_alternative": {"kind": "agent", "name": "sre"},
            },
        }
        passed, _ = run_evals.grade_routing(scenario, parsed)
        self.assertFalse(passed)

    def test_root_scope_rejects_inline_even_when_target_is_only_nested(self) -> None:
        parsed = run_evals.parse_stream_trace(self._scoped_routing_trace(
            nested_skills=("gcp-ops",),
        ))
        scenario = {
            "target": {"kind": "skill", "name": "gcp-ops"},
            "routing": {
                "expect": "not_fire",
                "scope": "root",
                "expected_alternative": "inline",
            },
        }
        passed, _ = run_evals.grade_routing(scenario, parsed)
        self.assertFalse(passed)

    def test_root_scope_rejects_nested_target_under_wrong_root_agent(self) -> None:
        parsed = run_evals.parse_stream_trace(self._scoped_routing_trace(
            root_agents=("sre", "agent-engineer"),
            nested_skills=("gcp-ops",),
            nested_skill_parent="agent-root-1",
        ))
        scenario = {
            "target": {"kind": "skill", "name": "gcp-ops"},
            "routing": {
                "expect": "not_fire",
                "scope": "root",
                "expected_alternative": {"kind": "agent", "name": "sre"},
            },
        }
        passed, _ = run_evals.grade_routing(scenario, parsed)
        self.assertFalse(passed)

    def test_root_scope_rejects_orphan_nested_target(self) -> None:
        parsed = run_evals.parse_stream_trace(self._scoped_routing_trace(
            root_agents=("sre",),
            nested_skills=("gcp-ops",),
            nested_skill_parent="orphan-agent-call",
        ))
        scenario = {
            "target": {"kind": "skill", "name": "gcp-ops"},
            "routing": {
                "expect": "not_fire",
                "scope": "root",
                "expected_alternative": {"kind": "agent", "name": "sre"},
            },
        }
        passed, _ = run_evals.grade_routing(scenario, parsed)
        self.assertFalse(passed)

    def test_root_scope_rejects_nested_target_under_non_agent_parent(self) -> None:
        parsed = run_evals.parse_stream_trace(self._scoped_routing_trace(
            root_skills=("merge-gate",),
            root_agents=("sre",),
            nested_skills=("gcp-ops",),
            nested_skill_parent="skill-root-0",
        ))
        scenario = {
            "target": {"kind": "skill", "name": "gcp-ops"},
            "routing": {
                "expect": "not_fire",
                "scope": "root",
                "expected_alternative": {"kind": "agent", "name": "sre"},
            },
        }
        passed, _ = run_evals.grade_routing(scenario, parsed)
        self.assertFalse(passed)

    def test_root_scope_allows_transitive_descendant_of_root_alternative(self) -> None:
        parsed = run_evals.parse_stream_trace(self._scoped_routing_trace(
            root_agents=("sre",),
            nested_agents=("observability-engineer",),
            nested_skills=("gcp-ops",),
            nested_skill_parent="agent-agent-root-0-0",
        ))
        scenario = {
            "target": {"kind": "skill", "name": "gcp-ops"},
            "routing": {
                "expect": "not_fire",
                "scope": "root",
                "expected_alternative": {"kind": "agent", "name": "sre"},
            },
        }
        passed, _ = run_evals.grade_routing(scenario, parsed)
        self.assertTrue(passed)

    def test_inline_answer_cannot_pass_direct_skill(self) -> None:
        # Direct-skill twin of test_inline_answer_cannot_pass_discovery_fire: the response text
        # satisfies the grader, but the pinned skill never completed, so the trial must FAIL.
        scenario = {
            "mode": "direct",
            "target": {"kind": "skill", "name": "merge-gate"},
            "graders": [{"type": "contains_any", "of": ["blocked"]}],
        }
        parsed = run_evals.parse_stream_trace(self._trace(with_skill=False))
        passed, details = run_evals.grade_trial(scenario, parsed)
        self.assertFalse(passed)
        self.assertTrue(any("skill-fired" in detail and "FAIL" in detail for detail in details))

    def test_available_skill_and_slash_command_do_not_prove_direct_skill_fired(self) -> None:
        # Claude Code 2.1.241 reports both fields after slash-command preprocessing, but neither
        # identifies which skill contributed to this turn. Availability must therefore fail closed.
        init = self._init_event()
        init["skills"] = ["save-toolkit:merge-gate"]
        init["slash_commands"] = ["save-toolkit:merge-gate"]
        parsed = run_evals.parse_stream_trace(self._blob([
            init,
            self._result_event("MERGE-GATE: BLOCKED"),
        ]))
        scenario = {
            "mode": "direct",
            "target": {"kind": "skill", "name": "merge-gate"},
            "graders": [{"type": "contains_any", "of": ["blocked"]}],
        }

        passed, details = run_evals.grade_trial(scenario, parsed)

        self.assertEqual(parsed.skills, ())
        self.assertFalse(passed)
        self.assertTrue(any("skill-fired" in detail and "FAIL" in detail for detail in details))

    def test_direct_skill_that_fired_passes(self) -> None:
        # Preserve the completed Skill tool_use/tool_result event contract across CLI versions.
        scenario = {
            "mode": "direct",
            "target": {"kind": "skill", "name": "merge-gate"},
            "graders": [{"type": "contains_any", "of": ["blocked"]}],
        }
        parsed = run_evals.parse_stream_trace(self._trace(with_skill=True))
        passed, details = run_evals.grade_trial(scenario, parsed)
        self.assertTrue(passed)
        self.assertTrue(any("skill-fired" in detail and "PASS" in detail for detail in details))


class ArtifactTests(unittest.TestCase):
    def test_windows_acl_inspection_avoids_module_autoloading(self) -> None:
        completed = mock.Mock(
            returncode=0,
            stdout="S-1-5-21-1234\tAllow\t2032127\tFalse\n",
            stderr="",
        )
        with mock.patch.object(run_evals.subprocess, "run", return_value=completed) as invoked:
            entries = run_evals._windows_acl(Path("artifact"))

        command = invoked.call_args.args[0]
        self.assertNotIn("Get-Acl", command[-1])
        self.assertIn("GetAccessControl", command[-1])
        self.assertEqual(
            [{"sid": "S-1-5-21-1234", "type": "Allow", "rights": 2032127, "inherited": False}],
            entries,
        )

    def test_windows_acl_inspection_rejects_malformed_output(self) -> None:
        completed = mock.Mock(returncode=0, stdout="not-an-acl\n", stderr="")
        with mock.patch.object(run_evals.subprocess, "run", return_value=completed):
            with self.assertRaisesRegex(clean_room.RunnerFailed, "malformed Windows ACL"):
                run_evals._windows_acl(Path("artifact"))

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

    def test_response_excerpt_is_bounded_without_losing_short_verbatim_text(self) -> None:
        self.assertEqual("short response", run_evals.bounded_response_excerpt("short response"))
        excerpt = run_evals.bounded_response_excerpt("x" * 900)
        self.assertTrue(excerpt.endswith("… [truncated]"))
        self.assertLessEqual(len(excerpt), run_evals.RESPONSE_EXCERPT_CHARS + 13)

    def test_private_summary_requires_durable_capture(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            writer = run_evals.ArtifactWriter(root / "private", {"run_id": "run-1"})
            expected = root / "docs" / "reviews" / "record.md"
            with mock.patch.object(
                run_evals.capture_measurement_evidence,
                "capture_eval_summary",
                return_value=expected,
            ) as capture:
                summary, evidence = run_evals.persist_summary_and_evidence(
                    writer, {"verdict": "PASS"}, root / "docs" / "reviews"
                )

            self.assertTrue(summary.is_file())
            self.assertEqual(expected, evidence)
            capture.assert_called_once_with(summary, root / "docs" / "reviews")

    def test_durable_capture_failure_makes_batch_non_publishable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            writer = run_evals.ArtifactWriter(Path(td), {"run_id": "run-1"})
            with mock.patch.object(
                run_evals.capture_measurement_evidence,
                "capture_eval_summary",
                side_effect=run_evals.capture_measurement_evidence.CaptureError("bad summary"),
            ):
                with self.assertRaisesRegex(clean_room.RunnerFailed, "durable evidence capture failed"):
                    run_evals.persist_summary_and_evidence(writer, {"verdict": "PASS"})

    def test_summary_records_measurement_conditions(self) -> None:
        args = argparse.Namespace(
            timeout=42, trials=5, threshold=0.66, mode="discovery", split="regression", match="merge",
        )
        conditions = run_evals.measurement_conditions(args)
        for key in ("timeout_s", "requested_trials", "requested_threshold", "selected"):
            self.assertIn(key, conditions)
        self.assertEqual(conditions["timeout_s"], 42)
        self.assertEqual(conditions["requested_trials"], 5)
        self.assertEqual(conditions["requested_threshold"], 0.66)
        self.assertEqual(
            conditions["selected"], {"mode": "discovery", "split": "regression", "match": "merge"}
        )
        with tempfile.TemporaryDirectory() as td:
            writer = run_evals.ArtifactWriter(Path(td), {"run_id": "run-1", "conditions": conditions})
            summary_path = writer.write_summary({"verdict": "PASS"})
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            recorded = summary["provenance"]["conditions"]
            for key in ("timeout_s", "requested_trials", "requested_threshold", "selected"):
                self.assertIn(key, recorded)
            self.assertEqual(recorded["timeout_s"], 42)

    def test_artifact_writer_rejects_unsafe_scenario_id_defense_in_depth(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            writer = run_evals.ArtifactWriter(Path(td), {"run_id": "run-1"})
            with self.assertRaises(ValueError):
                writer.write_trace("../escape", 1, "secret")

    def test_plugin_provenance_surface_includes_commands_and_guard_scripts(self) -> None:
        self.assertIn("commands", run_evals.PLUGIN_INPUT_PATHS)
        self.assertIn("scripts/fleet_frontmatter.py", run_evals.PLUGIN_INPUT_PATHS)
        self.assertIn("scripts/readonly-guard.py", run_evals.PLUGIN_INPUT_PATHS)
        self.assertIn("scripts/readonly-guard-hook.sh", run_evals.PLUGIN_INPUT_PATHS)
        self.assertIn("scripts/guard-session-preflight.py", run_evals.OPTIONAL_PLUGIN_INPUT_PATHS)
        self.assertIn("scripts/guard-session-preflight-hook.sh", run_evals.OPTIONAL_PLUGIN_INPUT_PATHS)
        self.assertIn("scripts/fleet_frontmatter.py", run_evals.EVAL_SUPPORT_INPUT_PATHS)

    def test_ignored_file_under_measured_root_is_a_dirty_candidate_input(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "agents").mkdir()
            (root / ".gitignore").write_text("*.pyc\n", encoding="utf-8")
            (root / "agents" / "agent.md").write_text("tracked\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(
                ["git", "add", ".gitignore", "agents/agent.md"], cwd=root, check=True
            )
            ignored = root / "agents" / "helper.pyc"
            ignored.write_bytes(b"ignored measured bytes")

            self.assertEqual(
                run_evals.ignored_plugin_inputs(root),
                ("agents/helper.pyc",),
            )
            self.assertTrue(
                run_evals.measured_plugin_inputs_dirty(
                    "", run_evals.ignored_plugin_inputs(root)
                )
            )

    def test_required_command_failure_does_not_look_clean(self) -> None:
        failed = mock.Mock(returncode=128, stdout="", stderr="not a git repository")
        with mock.patch.object(run_evals.subprocess, "run", return_value=failed):
            with self.assertRaises(clean_room.RunnerFailed):
                run_evals.required_command_text(["git", "status"])

    def test_expected_plugin_commit_mismatch_blocks_before_cli_version(self) -> None:
        observed: list[tuple[str, ...]] = []

        def command(argv, cwd=run_evals.ROOT):
            observed.append(tuple(argv))
            if argv[:3] == ["git", "rev-parse", "HEAD"]:
                return "b" * 40
            if argv[-1] == "--version":
                self.fail("runtime version must not be queried after candidate mismatch")
            return ""

        with (
            mock.patch.object(run_evals, "required_command_text", side_effect=command),
            mock.patch.object(run_evals, "ignored_plugin_inputs", return_value=()),
            mock.patch.object(run_evals, "plugin_digest", return_value="a" * 64),
            mock.patch.object(run_evals, "plugin_manifest", return_value={"name": "test"}),
            mock.patch.object(run_evals, "_sha256_file", return_value="a" * 64),
        ):
            with self.assertRaisesRegex(clean_room.RunnerFailed, "does not match"):
                run_evals.collect_provenance(
                    "sonnet",
                    run_evals.ROOT,
                    "claude",
                    run_evals.ROOT,
                    "a" * 64,
                    expected_plugin_commit="c" * 40,
                )

        self.assertIn(("git", "rev-parse", "HEAD"), observed)

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

    def test_not_fire_threshold_is_clamped_to_full(self) -> None:
        not_fire = {"mode": "discovery", "routing": {"expect": "not_fire"}}
        self.assertEqual(run_evals.effective_threshold(not_fire, 0.66), 1.0)
        # A not_fire scenario would over-trigger on a third of trials and still pass at 0.66 without
        # the clamp: two firing trials out of three must not reach the required pass count.
        clamped = run_evals.effective_threshold(not_fire, 0.66)
        self.assertEqual(
            run_evals.aggregate_verdict(["FAIL", "PASS", "PASS"], clamped), "FAIL"
        )
        # Positives and direct scenarios pass the requested threshold through unchanged.
        fire = {"mode": "discovery", "routing": {"expect": "fire"}}
        direct = {"mode": "direct", "target": {"kind": "skill", "name": "merge-gate"}}
        self.assertEqual(run_evals.effective_threshold(fire, 0.66), 0.66)
        self.assertEqual(run_evals.effective_threshold(direct, 0.66), 0.66)

    def test_mixed_models_in_one_batch_are_detected(self) -> None:
        scenario_results = [
            {"trials": [{"resolved_model": "claude-a"}, {"resolved_model": "claude-b"}]},
        ]
        self.assertEqual(
            run_evals.observed_models(scenario_results), ["claude-a", "claude-b"]
        )
        uniform = [{"trials": [{"resolved_model": "claude-a"}, {"resolved_model": "claude-a"}]}]
        self.assertEqual(run_evals.observed_models(uniform), ["claude-a"])
        # Inconclusive trials carry resolved_model=None and must not count as a model.
        with_none = [{"trials": [{"resolved_model": "claude-a"}, {"resolved_model": None}]}]
        self.assertEqual(run_evals.observed_models(with_none), ["claude-a"])


class JudgeSpendAccountingTests(unittest.TestCase):
    """A `rubric` grader's live judge call is charged to the trial that triggered it."""

    def setUp(self) -> None:
        self._saved = sys.modules.get("judge")
        self.addCleanup(self._restore)
        sys.modules.pop("judge", None)

    def _restore(self) -> None:
        if self._saved is not None:
            sys.modules["judge"] = self._saved
        else:
            sys.modules.pop("judge", None)

    def _install(self, calls: list[dict]) -> None:
        module = types.SimpleNamespace(drain_spend=lambda: calls)
        sys.modules["judge"] = module

    def test_no_judge_module_means_an_empty_record(self) -> None:
        # A batch with no rubric grader never imports judge; grading it must not invent spend.
        self.assertEqual(
            run_evals.drain_judge_spend(),
            {"calls": 0, "cost_usd": None, "seconds": 0.0, "cached_calls": 0, "models_resolved": []},
        )

    def test_two_judged_graders_sum_into_one_trial_record(self) -> None:
        self._install([
            {"cost_usd": 0.03, "seconds": 4.0, "cached": False, "model_resolved": "claude-sonnet-5"},
            {"cost_usd": 0.02, "seconds": 3.5, "cached": False, "model_resolved": "claude-sonnet-5"},
        ])
        record = run_evals.drain_judge_spend()
        self.assertEqual(record["calls"], 2)
        self.assertAlmostEqual(record["cost_usd"], 0.05)
        self.assertAlmostEqual(record["seconds"], 7.5)
        self.assertEqual(record["models_resolved"], ["claude-sonnet-5"])

    def test_unpriced_calls_report_unknown_cost_not_zero(self) -> None:
        self._install([{"cost_usd": None, "seconds": 120.0, "cached": False, "model_resolved": None}])
        record = run_evals.drain_judge_spend()
        self.assertIsNone(record["cost_usd"])
        self.assertEqual(record["seconds"], 120.0)

    def test_observed_judge_models_span_the_batch(self) -> None:
        scenario_results = [
            {"trials": [{"judge": {"models_resolved": ["claude-sonnet-5"]}}, {"judge": {"models_resolved": []}}]},
            {"trials": [{"judge": {"models_resolved": ["claude-sonnet-4-5"]}}, {}]},
        ]
        self.assertEqual(
            run_evals.observed_judge_models(scenario_results), ["claude-sonnet-4-5", "claude-sonnet-5"]
        )


class DispatchContractTests(unittest.TestCase):
    """A direct scenario's `dispatch:` contract is graded from the trace, never from prose."""

    def test_forbidden_dispatch_fails_from_the_trace(self) -> None:
        from types import SimpleNamespace

        scenario = {"dispatch": {"forbid": ["reviewer"]}}
        passed, detail = run_evals.grade_dispatch(scenario, SimpleNamespace(attempted_agents=("save-toolkit:reviewer",)))
        self.assertFalse(passed)
        self.assertIn("save-toolkit:reviewer", detail)
        passed, _ = run_evals.grade_dispatch(scenario, SimpleNamespace(attempted_agents=("reviewer",)))
        self.assertFalse(passed, "a bare agent name is the same dispatch")
        passed, _ = run_evals.grade_dispatch(scenario, SimpleNamespace(attempted_agents=("save-toolkit:scribe",)))
        self.assertTrue(passed, "another lane is not the forbidden one")
        passed, _ = run_evals.grade_dispatch(scenario, SimpleNamespace(attempted_agents=()))
        self.assertTrue(passed)

    def test_dispatch_is_an_allowed_scenario_key(self) -> None:
        self.assertIn("dispatch", run_evals.ALLOWED_SCENARIO_KEYS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
