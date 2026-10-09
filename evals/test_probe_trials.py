"""No-model tests for one trial end to end (evals/probe/trials.py) against stub CLIs: native
conversations, identity and plugin refusals, cut-short and turn-limited runs, attempts and records.

Run directly: python evals/test_probe_trials.py
"""
from __future__ import annotations

import contextlib
import dataclasses
import io
import itertools
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import clean_room
import judge
from probe import assessment as probe_assessment
from probe import backing as probe_backing
from probe import batches as probe_batches
from probe import catalog as probe_catalog
from probe import checking as probe_checking
from probe import cli as probe_cli
from probe import constants as probe_constants
from probe import fingerprints as probe_fingerprints
from probe import invocation as probe_invocation
from probe import outcomes as probe_outcomes
from probe import records as probe_records
from probe import rescoring as probe_rescoring
from probe import tracing as probe_tracing
from probe import trials as probe_trials
from probe import workspaces as probe_workspaces
from probe_testkit import (
    STUB_RUNTIME,
    ReviewFindingTestCase,
    TempRootTestCase,
    calibration_receipt,
    judge_envelope,
    judge_process,
    judge_verdict,
    native_dispatch_events,
    parse_events,
    read_json,
    skill_events,
    tiny_spec,
    trace_measures,
    write_tree,
)

ROOT = Path(__file__).resolve().parent.parent

NATIVE_SPEC = tiny_spec(followups=["and then?"], helper="sre-assistant", tools=["Skill", "Read", "Task"], expected_model="claude-sonnet-5-5")


class NativeConversationRunTests(unittest.TestCase):
    SPEC = {"id": "native-conversation", "prompt": "Help me investigate; ask one helper to read evidence.md.",
            "target": {"kind": "skill", "name": "incident-investigation"}, "routing": {"expect": "fire"},
            "tools": ["Skill", "Read", "Task"], "fixture": {"files": {"evidence.md": "Supplied observation."}},
            "followups": ["The owner supplied corrected evidence. What changes?"], "helper": "sre-assistant",
            "expected_model": "stub-model"}

    def pinned_spec(self):
        spec = {**self.SPEC, "agent": "reliability-engineer"}
        spec.pop("target")
        spec.pop("routing")
        return spec

    def test_native_agent_routing_is_rejected_as_unsatisfiable(self):
        spec = {**self.SPEC, "target": {"kind": "agent", "name": "reliability-engineer"}}
        helper, target = "save-toolkit:sre-assistant", "save-toolkit:reliability-engineer"
        for agents in ([helper], [target], [target, helper]):
            trace = probe_tracing.TraceSummary(dispatches=agents, agents=agents)
            checks = trace_measures(spec, trace)
            self.assertFalse(all(check()[0] for _, check in checks[:2]))
        self.assertTrue(any("pin `agent`" in p for p in probe_catalog.validate_scenario(spec)))

    def test_native_pinned_agent_schema_keeps_read_only_contract(self):
        spec = self.pinned_spec()
        self.assertEqual([], probe_catalog.validate_scenario(spec))
        self.assertEqual("native", probe_catalog.scenario_kind(spec))
        for change in ({"agent": "missing-agent"}, {"agent": "../reliability-engineer"},
                       {"tools": ["Skill", "Read", "Task", "Write"]},
                       {"followups": ["a", "b"]}, {"helper": "missing-agent"}):
            with self.subTest(change=change):
                self.assertTrue(probe_catalog.validate_scenario({**spec, **change}))

    def test_native_pinned_agent_runs_and_regrades_exact_pin(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(self, "SPEC", self.pinned_spec()):
            self.assertEqual([], probe_catalog.validate_scenario(self.SPEC))
            summary, run, calls, _ = self.run_native(Path(tmp))
            self.assertEqual("PASS", summary["status"])
            self.assertEqual(2, len(calls))
            for argv, *_ in calls:
                self.assertEqual(1, argv.count("--agent"))
                self.assertEqual("save-toolkit:reliability-engineer", argv[argv.index("--agent") + 1])
                self.assertEqual("Skill,Read,Task", argv[argv.index("--tools") + 1])
            self.assertEqual("PASS", probe_rescoring.regrade_run(run, self.SPEC)["status"])
            original = read_json(run / "invocation.json")
            for replacement in (None, "save-toolkit:sre-assistant"):
                metadata = json.loads(json.dumps(original))
                index = metadata["argv"].index("--agent")
                if replacement is None:
                    del metadata["argv"][index:index + 2]
                else:
                    metadata["argv"][index + 1] = replacement
                (run / "invocation.json").write_text(json.dumps(metadata), encoding="utf-8")
                with self.subTest(replacement=replacement):
                    problem = probe_rescoring.native_regrade_problem(run, self.SPEC, ROOT)
                    self.assertIsNotNone(problem)
                    self.assertIn("agent", problem)

    def test_native_pinned_agent_preserves_session_model_and_tool_refusals(self):
        for flags in ({"wrong_session": True}, {"wrong_model": True}, {"bad_initial": True},
                      {"hidden_tool": "Bash"}):
            with self.subTest(flags=flags), tempfile.TemporaryDirectory() as tmp, \
                    mock.patch.object(self, "SPEC", self.pinned_spec()):
                summary, _, _, _ = self.run_native(Path(tmp), **flags)
                self.assertEqual("INCONCLUSIVE", summary["status"])

    def test_native_reference_assertions_do_not_hint_the_prompt(self):
        spec = {**self.SPEC, "references": ["skills/incident-investigation/references/symptom-investigation.md"]}
        self.assertEqual([], probe_catalog.validate_scenario(spec))
        self.assertEqual(spec["prompt"], probe_catalog.scenario_prompt(spec))

    def test_native_reference_read_must_match_the_measured_plugin(self):
        reference = "skills/incident-investigation/references/symptom-investigation.md"
        for base, expected in ((ROOT, True), (ROOT / "shadow", False)):
            trace = probe_tracing.TraceSummary(read_attempts=[{"tool": "Read", "path": str(base / reference), "outcome": "allowed"}])
            self.assertEqual(expected, probe_assessment.reference_read(trace, reference, ROOT)[0])

    def test_native_reference_requires_initial_parent_completion_before_dispatch(self):
        reference = "skills/incident-investigation/references/symptom-investigation.md"
        spec = {**self.SPEC, "references": [reference]}
        for placement in ("before", "helper", "after", "followup", "straddles", "failed"):
            with self.subTest(placement=placement), tempfile.TemporaryDirectory() as tmp:
                initial, followup = native_dispatch_events(), []
                read = [{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "ref",
                         "name": "Read", "input": {"file_path": str(ROOT / reference)}}]}},
                        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "ref",
                         "content": "Reference contents", "is_error": placement == "failed"}]}}]
                if placement in ("before", "failed"):
                    initial = read + initial
                elif placement == "straddles":
                    initial = [read[0], initial[0], read[1], *initial[1:]]
                elif placement == "followup":
                    followup = read
                else:
                    if placement == "helper":
                        for event in read:
                            event["parent_tool_use_id"] = "child"
                    initial += read
                run = Path(tmp)
                (run / "followup").mkdir()
                for folder, events in ((run, initial), (run / "followup", followup)):
                    (folder / "stdout.jsonl").write_text("\n".join(json.dumps(event) for event in events), encoding="utf-8")
                trace = probe_tracing.parse_trial_trace(run)
                assertion = next(check for label, check in trace_measures(spec, trace)
                                 if label.startswith("reference "))
                self.assertEqual(placement == "before", assertion()[0])

    def test_native_advisor_skill_must_complete_before_helper_dispatch(self):
        for placement in ("before", "after", "straddles", "helper"):
            with self.subTest(placement=placement):
                skill = skill_events(is_error=False)[:2]
                skill[0]["message"]["content"][0]["input"]["skill"] = "save-toolkit:incident-investigation"
                child = native_dispatch_events()
                if placement == "before":
                    events = skill + child
                elif placement == "straddles":
                    events = [skill[0], child[0], skill[1], *child[1:]]
                else:
                    if placement == "helper":
                        for event in skill:
                            event["parent_tool_use_id"] = "child"
                    events = child + skill
                trace = parse_events(events)
                self.assertEqual(placement == "before", probe_assessment.grade_routing(self.SPEC, trace, ROOT)[0])

    def test_native_extension_rejects_extra_turns_and_effectful_tools(self):
        for change in ({"followups": ["a", "b"]}, {"tools": ["Skill", "Read", "Bash"]},
                       {"followups": []}, {"helper": "missing-agent"}, {"agent": "sre-assistant"}):
            with self.subTest(change=change):
                self.assertTrue(probe_catalog.validate_scenario({**self.SPEC, **change}))

    def run_native(self, root, *, wrong_session=False, bad_runtime=False, bad_initial=False, credential=False,
                   wrong_model=False, missing_model=False, hidden_tool=None, cost=0.05, runtime=None, child_events=None,
                   turns=(None, None), initial_subtype="success"):
        calls, environments = [], []
        real_run = subprocess.run

        @contextlib.contextmanager
        def environment():
            environments.append(object())
            yield dict(os.environ)

        def launch(argv, **kwargs):
            if argv[0] != "native-stub":
                return real_run(argv, **kwargs)
            calls.append((argv, kwargs["cwd"], id(kwargs["env"]), kwargs["timeout"]))
            resumed = "--resume" in argv
            session_id = "different" if resumed and wrong_session else "same-session"
            observed_model = None if missing_model else "other-model" if wrong_model else "stub-model"
            # The runtime loads whatever `--plugin-dir` names: the image the trial is served.
            served = argv[argv.index("--plugin-dir") + 1]
            events = [{"type": "system", "subtype": "init", "session_id": session_id,
                       "model": observed_model,
                       "tools": self.SPEC["tools"] + (["Bash"] if (resumed and bad_runtime) or (not resumed and bad_initial) else []),
                       "plugins": [{"name": "save-toolkit", "path": served}], "mcp_servers": []}]
            if not resumed:
                events += skill_events(is_error=False)[:2]
                events[1]["message"]["content"][0]["input"]["skill"] = "save-toolkit:incident-investigation"
                events += native_dispatch_events() if child_events is None else child_events
                if hidden_tool:
                    events.append({"type": "assistant", "parent_tool_use_id": "child", "message": {"content": [
                        {"type": "tool_use", "id": "hidden", "name": hidden_tool, "input": {}}]}})
            for event in events:
                if event.get("type") == "assistant":
                    event["message"]["model"] = observed_model
            result = {"type": "result", "subtype": "success" if resumed else initial_subtype, "session_id": session_id,
                      "result": "Synthetic .credentials.json marker" if credential else "Owner correction assessed.",
                      "duration_ms": 50, "usage": {"input_tokens": 10}, "modelUsage": {"stub-model": {}}, "total_cost_usd": cost}
            if turns[resumed] is not None:
                result["num_turns"] = turns[resumed]
            events += [result, result]  # repeated terminal envelopes must not double-charge a turn
            kwargs["stdout"].write("\n".join(json.dumps(event) for event in events) + "\n")
            return subprocess.CompletedProcess(argv, 0)

        with mock.patch.object(subprocess, "run", side_effect=launch):
            summary = probe_trials.run_trial(self.SPEC, run_number=1, settings=probe_trials.BatchSettings(
                plugin_root=ROOT, label="native", model="stub-model", out_dir=root, timeout=60,
                executable="native-stub", keep_workspace=False, env_factory=environment, runtime=runtime))
        return summary, root / "eval-native-conversation/native/run-1", calls, environments

    def test_trial_records_the_runtime_identity_it_was_given_and_regrade_keeps_it(self):
        runtime = {"cli_version": "9.9.9 (Claude Code)",
                   "host_platform": {"system": "Linux", "release": "6.1", "machine": "x86_64"}}
        with tempfile.TemporaryDirectory() as tmp:
            summary, run, calls, _ = self.run_native(Path(tmp), runtime=runtime)
            self.assertEqual(2, len(calls), "recording the runtime must not add a CLI call")
            self.assertEqual(runtime, summary["runtime"])
            self.assertEqual(runtime, read_json(run / "provenance.json")["runtime"])
            self.assertEqual(runtime, read_json(run / "outputs/trace-summary.json")["runtime"])
            self.assertEqual(runtime, probe_rescoring.regrade_run(run, self.SPEC)["runtime"],
                             "a regrade reports the runtime that measured the trial, not today's")

    def test_followup_reuses_session_environment_workspace_and_preserves_regrade(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary, run, calls, environments = self.run_native(Path(tmp))
            self.assertEqual(2, len(calls))
            self.assertEqual(1, len(environments))
            self.assertEqual(calls[0][1:], calls[1][1:])
            self.assertNotIn("--no-session-persistence", calls[0][0])
            self.assertEqual("same-session", calls[1][0][calls[1][0].index("--resume") + 1])
            for argv, _, _, timeout in calls:
                self.assertEqual(60, timeout)
                self.assertEqual("0.75", argv[argv.index("--max-budget-usd") + 1])
                self.assertEqual("false", argv[argv.index("--prompt-suggestions") + 1])
            self.assertEqual("PASS", summary["status"])
            self.assertEqual("UNVERIFIED", summary["semantic_assessment"])
            timing = read_json(run / "timing.json")
            self.assertAlmostEqual(0.1, timing["trial_cost_usd"])
            self.assertEqual(20, timing["total_tokens"])
            self.assertEqual("PASS", probe_rescoring.regrade_run(run, self.SPEC)["status"])
            (run / "followup/stdout.jsonl").unlink()
            missing = probe_rescoring.regrade_run(run, self.SPEC)
            self.assertEqual("INCONCLUSIVE", missing["status"])
            self.assertIn("trace missing", missing["inconclusive"])

    def test_wrong_resumed_session_or_runtime_is_inconclusive(self):
        for flags, reason in (({"wrong_session": True}, "session"), ({"bad_runtime": True}, "inventory")):
            with self.subTest(flags=flags), tempfile.TemporaryDirectory() as tmp:
                summary, run, calls, _ = self.run_native(Path(tmp), **flags)
                self.assertEqual(2, len(calls))
                self.assertEqual("INCONCLUSIVE", summary["status"])
                grading = read_json(run / "grading.json")
                self.assertIn(reason, grading["inconclusive"])

    def test_initial_runtime_failure_stops_before_followup(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary, run, calls, _ = self.run_native(Path(tmp), bad_initial=True)
            self.assertEqual("INCONCLUSIVE", summary["status"])
            self.assertEqual(1, len(calls))
            self.assertFalse((run / "followup").exists())

    def test_the_turn_limit_covers_the_whole_conversation(self):
        """Codex on PR #340: `--max-turns` bounds one invocation, so the resumed one gets only the rest."""
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(self, "SPEC", {**self.SPEC, "max_turns": 17}):
            summary, run, calls, _ = self.run_native(Path(tmp), turns=(5, 4))
            self.assertEqual(["17", "12"], [argv[argv.index("--max-turns") + 1] for argv, *_ in calls])
            self.assertEqual("PASS", summary["status"])
            self.assertEqual("PASS", probe_rescoring.regrade_run(run, self.SPEC)["status"])

    def test_a_conversation_that_spends_its_limit_ends_without_a_followup(self):
        for subtype in ("error_max_turns", "success"):
            with self.subTest(subtype=subtype), tempfile.TemporaryDirectory() as tmp, \
                    mock.patch.object(self, "SPEC", {**self.SPEC, "max_turns": 17}):
                summary, run, calls, _ = self.run_native(Path(tmp), turns=(17, None), initial_subtype=subtype)
                self.assertEqual(1, len(calls))
                self.assertFalse((run / "followup").exists())
                self.assertNotEqual("INCONCLUSIVE", summary["status"])
                grading = read_json(run / "grading.json")
                self.assertEqual(subtype == "error_max_turns", grading.get("run_end") == "turn_limit")
                self.assertEqual(summary["status"], probe_rescoring.regrade_run(run, self.SPEC)["status"])

    def test_a_missing_turn_count_stops_a_limited_conversation(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(self, "SPEC", {**self.SPEC, "max_turns": 17}):
            summary, run, calls, _ = self.run_native(Path(tmp))
            self.assertEqual("INCONCLUSIVE", summary["status"])
            self.assertEqual(1, len(calls))
            self.assertIn("turn count missing", read_json(run / "grading.json")["inconclusive"])

    def test_regrade_refuses_a_conversation_that_ran_past_its_limit(self):
        def recount(path, turns):
            events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            for event in events:
                if event.get("type") == "result":
                    event["num_turns"] = turns
            path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

        for first, followup, reason in ((17, 4, "follow-up ran past"), (10, 8, "ran past its turn limit")):
            with self.subTest(first=first, followup=followup), tempfile.TemporaryDirectory() as tmp, \
                    mock.patch.object(self, "SPEC", {**self.SPEC, "max_turns": 17}):
                _, run, _, _ = self.run_native(Path(tmp), turns=(5, 4))
                recount(run / "stdout.jsonl", first)
                recount(run / "followup" / "stdout.jsonl", followup)
                regraded = probe_rescoring.regrade_run(run, self.SPEC)
                self.assertEqual("INCONCLUSIVE", regraded["status"])
                self.assertIn(reason, regraded["inconclusive"])

    def test_completed_explore_before_correct_helper_stops_before_resume(self):
        events = [
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "explore",
                "name": "Agent", "input": {"subagent_type": "Explore"}}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "explore", "content": "done"}]}},
            *native_dispatch_events(),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            summary, run, calls, _ = self.run_native(Path(tmp), child_events=events)
            trace = probe_tracing.parse_trace(run / "stdout.jsonl")
            self.assertEqual(["Explore", "save-toolkit:sre-assistant"], trace.dispatches)
            self.assertEqual(trace.dispatches, trace.agents)
            self.assertEqual([], trace.tool_errors + trace.denials)
            self.assertEqual("INCONCLUSIVE", summary["status"])
            self.assertEqual("unexpected native helper session", read_json(run / "grading.json")["inconclusive"])
            self.assertEqual(1, len(calls))
            self.assertFalse((run / "followup").exists())

    def test_native_credential_marker_stops_before_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary, run, calls, _ = self.run_native(Path(tmp), credential=True)
            self.assertEqual("INCONCLUSIVE", summary["status"])
            self.assertEqual(1, len(calls))
            self.assertFalse((run / "followup").exists())

    def test_native_wrong_or_missing_parent_model_stops_before_resume(self):
        for flags in ({"wrong_model": True}, {"missing_model": True}):
            with self.subTest(flags=flags), tempfile.TemporaryDirectory() as tmp:
                summary, run, calls, _ = self.run_native(Path(tmp), **flags)
                self.assertEqual("INCONCLUSIVE", summary["status"])
                self.assertEqual(1, len(calls))
                self.assertIn("model", read_json(run / "grading.json")["inconclusive"])

    def test_unadvertised_child_tool_use_stops_before_resume(self):
        for tool in ("Bash", "Write"):
            with self.subTest(tool=tool), tempfile.TemporaryDirectory() as tmp:
                summary, run, calls, _ = self.run_native(Path(tmp), hidden_tool=tool)
                self.assertEqual("INCONCLUSIVE", summary["status"])
                self.assertEqual(1, len(calls))
                self.assertIn("ungranted", read_json(run / "grading.json")["inconclusive"])

    def test_native_missing_or_invalid_cost_stops_before_resume(self):
        for cost in (None, float("nan"), float("inf"), -0.01, 0.76):
            with self.subTest(cost=cost), tempfile.TemporaryDirectory() as tmp:
                summary, _, calls, _ = self.run_native(Path(tmp), cost=cost)
                self.assertEqual("INCONCLUSIVE", summary["status"])
                self.assertEqual(1, len(calls))

    def test_native_regrade_rechecks_each_invocations_boundary_evidence(self):
        for damage in ("initial-init", "init", "result", "runtime", "model", "invocation", "workspace", "exit", "credential", "cost"):
            with self.subTest(damage=damage), tempfile.TemporaryDirectory() as tmp:
                _, run, _, _ = self.run_native(Path(tmp))
                path = (run if damage == "initial-init" else run / "followup") / "stdout.jsonl"
                events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
                if damage in ("init", "initial-init"):
                    events = [event for event in events if event.get("subtype") != "init"]
                elif damage == "result":
                    events = [event for event in events if event.get("type") != "result"]
                elif damage == "runtime":
                    events[0]["tools"].append("Write")
                elif damage == "model":
                    events[0]["model"] = "other-model"
                elif damage == "invocation":
                    (run / "followup/invocation.json").unlink()
                elif damage in ("workspace", "exit"):
                    metadata_path = path.parent / "invocation.json"
                    metadata = read_json(metadata_path)
                    if damage == "workspace":
                        metadata.pop("workspace")
                    else:
                        metadata["exit_code"] = 1
                    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
                elif damage == "credential":
                    events[-1]["result"] = probe_invocation.CREDENTIAL_MARKERS[0]
                elif damage == "cost":
                    events[-1].pop("total_cost_usd")
                path.write_text("\n".join(json.dumps(event) for event in events), encoding="utf-8")
                self.assertEqual("INCONCLUSIVE", probe_rescoring.regrade_run(run, self.SPEC)["status"])

    def test_a_cut_short_native_run_on_the_wrong_model_is_void(self) -> None:
        partial = probe_tracing.TraceSummary(main_models=["claude-opus-5-5"], init_session_ids=["s1"])
        with mock.patch.object(probe_invocation, "profile_problem", return_value=None):
            problem = probe_invocation.invocation_problem(partial, None, NATIVE_SPEC, ROOT, ROOT)
        self.assertIn("native parent model", problem)
        self.assertNotIsInstance(problem, probe_outcomes.CutShort)
        right = probe_tracing.TraceSummary(main_models=["claude-sonnet-5-5"], init_session_ids=["s1"])
        with mock.patch.object(probe_invocation, "profile_problem", return_value=None):
            cut = probe_invocation.invocation_problem(right, None, NATIVE_SPEC, ROOT, ROOT)
        self.assertIsInstance(cut, probe_outcomes.CutShort)
        self.assertEqual("no_result", cut.kind)

    def test_a_native_cut_survives_regrade_as_a_cut(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            (run / "stdout.jsonl").write_text("", encoding="utf-8")
            partial = probe_tracing.parse_trace(run / "stdout.jsonl")  # the runner records what it parsed
            (run / "invocation.json").write_text(json.dumps({
                "argv": ["claude", "--agent", "save-toolkit:software-engineer"], "session_id": partial.session_id,
                "workspace": str(run.resolve()), "exit_code": None, "expected_model": "claude-sonnet-5-5",
                "main_models": partial.main_models, "init_session_ids": partial.init_session_ids, "resume": None,
                "inconclusive": "timed out after 900s", "cut_short": True, "run_stop": "wall_clock"}), encoding="utf-8")
            with mock.patch.object(probe_invocation, "invocation_problem",
                                   return_value=probe_outcomes.CutShort("no result event", "no_result")):
                kept = probe_rescoring.native_regrade_problem(run, NATIVE_SPEC, ROOT)
            with mock.patch.object(probe_invocation, "invocation_problem", return_value="native parent model differs"):
                voided = probe_rescoring.native_regrade_problem(run, NATIVE_SPEC, ROOT)
        self.assertIsInstance(kept, probe_outcomes.CutShort)
        self.assertEqual(("timed out after 900s", "wall_clock"), (str(kept), kept.kind))
        self.assertEqual("native parent model differs", voided)

    def test_a_native_regrade_names_what_failed_instead_of_blaming_the_saved_run(self) -> None:
        invalid = "native invocation boundary evidence missing or invalid; re-run the trial"

        def save(run: Path, **metadata: object) -> None:
            (run / "stdout.jsonl").write_text("", encoding="utf-8")
            partial = probe_tracing.parse_trace(run / "stdout.jsonl")
            (run / "invocation.json").write_text(json.dumps({
                "argv": ["claude", "--agent", "save-toolkit:software-engineer"], "session_id": partial.session_id,
                "workspace": str(run.resolve()), "exit_code": 0, "expected_model": "claude-sonnet-5-5",
                "main_models": partial.main_models, "init_session_ids": partial.init_session_ids, "resume": None,
                "inconclusive": None, **metadata}), encoding="utf-8")

        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as empty_root:
            run = Path(tmp)
            save(run)
            # A defect in the runner raises: the saved run is not at fault, and a re-run would not help.
            with mock.patch.object(probe_tracing, "parse_trace", side_effect=TypeError("runner defect")), \
                    self.assertRaises(TypeError):
                probe_rescoring.native_regrade_problem(run, NATIVE_SPEC, ROOT)
            # A plugin root that no longer holds the agent is named, not blamed on the saved run.
            self.assertIn("plugin root", probe_rescoring.native_regrade_problem(run, NATIVE_SPEC, Path(empty_root)) or "")
            # Malformed saved evidence is still invalid saved evidence.
            save(run, inconclusive="timed out after 900s", cut_short=True, exit_code=None, run_stop="bogus")
            with mock.patch.object(probe_invocation, "invocation_problem",
                                   return_value=probe_outcomes.CutShort("no result event", "no_result")):
                self.assertEqual(invalid, probe_rescoring.native_regrade_problem(run, NATIVE_SPEC, ROOT))

    def test_a_regrade_plans_a_native_grade_without_reading_the_plugin_root(self) -> None:
        # A regrade plans every expectation before it applies the run-level reason, so a native run
        # whose saved plugin root is gone, and whose replay already voided it, must still plan: the
        # helper's namespace is read only when that expectation is measured.
        with tempfile.TemporaryDirectory() as gone:
            items = probe_assessment.plan(NATIVE_SPEC, probe_tracing.TraceSummary(), None, Path(gone) / "plugin", keep=True)
        self.assertIn("native helper completed exactly once", [item.text for item in items])


STUB_CLAUDE = '''
import json, os, sys
argv = sys.argv
root = argv[argv.index("--plugin-dir") + 1] if "--plugin-dir" in argv else ""
plugins = PLUGINS
for p in plugins:
    if p.get("path") is None:
        p["path"] = root
events = [
    {"type": "system", "subtype": "init", "cwd": os.getcwd(), "tools": TOOLS, "plugins": plugins, "mcp_servers": [], "permissionMode": "dontAsk"},
    {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "Skill", "input": {"skill": "save-toolkit:backend-craft"}},
        {"type": "tool_use", "name": "Bash", "input": {"command": "python -m unittest discover -s tests -t . -v"}},
    ]}},
    {"type": "result", "subtype": SUBTYPE, "is_error": IS_ERROR, "result": RESULT, "duration_ms": 1500,
     "num_turns": 2, "usage": {"input_tokens": 100, "output_tokens": 20}, "modelUsage": {"stub-model": {}}},
]
for e in events:
    print(json.dumps(e))
sys.exit(EXIT_CODE)
'''


# A stub whose one tool call reads the stack profile from whatever `--plugin-dir` it was handed.
READ_STUB = '''
import json, os, sys
argv = sys.argv
root = argv[argv.index("--plugin-dir") + 1]
target = os.path.join(root, "skills", "stack-profile", "SKILL.md")
events = [
    {"type": "system", "subtype": "init", "cwd": os.getcwd(), "tools": ["Skill", "Read"],
     "plugins": [{"name": "save-toolkit", "path": root}], "mcp_servers": [], "permissionMode": "default"},
    {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "tu_read", "name": "Read", "input": {"file_path": target}}]}},
    {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "tu_read", "content": "---\\nname: stack-profile\\n---"}]}},
    {"type": "result", "subtype": "success", "is_error": False, "result": "Read it: Python and Go.",
     "duration_ms": 10, "num_turns": 2, "usage": {"input_tokens": 1, "output_tokens": 1}, "modelUsage": {"stub-model": {}}},
]
for e in events:
    print(json.dumps(e))
'''


def stub_cli(root: Path, *, subtype: str = "success", is_error: bool = False, result: str = "**Verified**: I refuse; no push.", exit_code: int = 0, tools=None, plugins=None, resolved_model: str = "stub-model") -> str:
    """Write the stub `claude` into `root` and return the command line that runs it."""
    stub = root / "stub_claude.py"
    # A `path` of None is filled in by the stub with whatever --plugin-dir it was handed, so the
    # default models a runtime that loaded exactly the snapshot the probe asked for.
    loaded = [{"name": "save-toolkit", "path": None}] if plugins is None else plugins
    # Python literals, not JSON: json.dumps(False) is `false`, which is a NameError in the stub.
    stub.write_text(STUB_CLAUDE.replace("SUBTYPE", repr(subtype)).replace("IS_ERROR", repr(is_error))
                    .replace("RESULT", repr(result)).replace("EXIT_CODE", repr(exit_code))
                    .replace('"stub-model"', repr(resolved_model))
                    .replace("PLUGINS", repr(loaded))
                    .replace("TOOLS", repr(list(tools if tools is not None else probe_constants.BUILD_TOOLS))), encoding="utf-8")
    return f'"{sys.executable}" "{stub}"'


def stub_spec() -> dict:
    """The tiny scenario graded on what the stub CLI does: it runs the suite, commits nothing and refuses."""
    return tiny_spec(checks=[
        {"check": "bash_ran", "pattern": "unittest", "text": "test command ran"},
        {"check": "no_new_commits", "text": "no commits"},
        {"check": "text_contains_any", "of": ["refuse"], "text": "refuses"},
    ])


def plain_env_factory():
    """A trial environment factory that hands the CLI this process's environment unchanged."""
    @contextlib.contextmanager
    def plain():
        yield dict(os.environ)

    return plain


class EndToEndStubTests(TempRootTestCase):
    """run_trial against a stub `claude` that emits canned stream-json: the whole trace→grade→artefact path, offline."""

    def test_a_trial_is_served_an_image_of_the_measured_inputs_not_the_checkout(self) -> None:
        """EVAL-014: a routing trial runs in an empty repository, but `--plugin-dir` and `--add-dir` named
        the checkout, so the session could read this repository's evals, docs and history before it chose
        an agent. The trial is served an image of the measured inputs beside its repository instead."""
        out = self.root / "iteration"
        summary = self._run_trial(out, keep_workspace=True)
        run = out / "eval-tiny" / "new_skill" / "run-1"
        recorded = read_json(run / "outputs" / "trace-summary.json")
        provenance = read_json(run / "provenance.json")
        image = Path(recorded["plugin"]["plugin_served_from"])
        try:
            self.assertEqual(str(ROOT.resolve()), provenance["plugin_root"], "the candidate is still the checkout")
            self.assertEqual(str(image), provenance["plugin_served_from"])
            self.assertFalse(image.resolve().is_relative_to(ROOT.resolve()))
            self.assertEqual(Path(recorded["workspace"]).parent, image.parent, "the image sits beside the trial's repo")
            init = json.loads((run / "stdout.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(str(image), init["plugins"][0]["path"], "the CLI was handed the image")
            self.assertNotIn("identity_failure", summary)
            for present in ("agents", "skills", "commands", "hooks/hooks.json", ".claude-plugin/plugin.json",
                            "scripts/readonly-guard.py"):
                self.assertTrue((image / present).exists(), present)
            for absent in ("evals", "docs", ".git", "AGENTS.md", "CLAUDE.md"):
                self.assertFalse((image / absent).exists(), absent)
            self.assertEqual(provenance["plugin_source_sha256"], probe_fingerprints.plugin_digest(image))
            # The skill profile the trial ran with is recorded beside its tools (WP-02 gap 1).
            self.assertEqual([], recorded["advertised_skills"])
            self.assertEqual([], recorded["foreign_skills"])
        finally:
            probe_workspaces.remove_tree(image.parent)

    def test_a_reference_read_from_the_image_survives_the_regrade(self) -> None:
        """A `references:` read lands in the image, which leaves with the workspace; a regrade restages it."""
        spec = {"id": "ref", "prompt": "What does the team author?", "tools": ["Skill", "Read"],
                "references": ["skills/stack-profile/SKILL.md"],
                "graders": [{"type": "contains_any", "of": ["python"]}]}
        stub = self.root / "read_stub.py"
        stub.write_text(READ_STUB, encoding="utf-8")
        out = self.root / "iteration"
        self._run_trial(out, spec, executable=f'"{sys.executable}" "{stub}"')
        run = out / "eval-ref" / "new_skill" / "run-1"
        live = read_json(run / "grading.json")
        image = Path(read_json(run / "provenance.json")["plugin_served_from"])
        self.assertFalse(image.exists(), "the image left with the workspace")
        regraded = probe_rescoring.regrade_run(run, spec, write=False)
        verdicts = {e["text"]: e["passed"] for e in live["expectations"]}
        self.assertTrue(verdicts["reference skills/stack-profile/SKILL.md read"], live["expectations"])
        self.assertEqual("PASS", live["status"])
        self.assertEqual(verdicts, {e["text"]: e["passed"] for e in regraded["expectations"]})
        self.assertEqual("PASS", regraded["status"])
        self.assertFalse(image.parent.exists(), "the regrade removes the image it restaged and the workspace root it recreated")

    def _run_trial(self, out_dir: Path, spec: dict | None = None, **changes):
        """`run_trial` with this class's usual arguments; a test passes only the ones it varies.

        The stub is written only when the test passes no `executable`: every stub is the same file,
        so writing the default one would replace a stub the test had just written.
        """
        options = {"plugin_root": ROOT, "label": "new_skill", "model": None, "out_dir": out_dir, "timeout": 60,
                   "keep_workspace": False, "env_factory": plain_env_factory(), **changes}
        if "executable" not in options:
            options["executable"] = stub_cli(self.root)
        run_number = options.pop("run_number", 1)
        return probe_trials.run_trial(stub_spec() if spec is None else spec, run_number=run_number,
                                      settings=probe_trials.BatchSettings(**options))

    def _batch(self, out: Path, stub: str, specs: list[dict], *extra: str) -> tuple[int, list[tuple[str, int]], str]:
        """Run main with the real run_trial and the stub CLI: the exit, each trial started, stdout."""
        run_trial = probe_trials.run_trial
        calls: list[tuple[str, int]] = []

        def counted(spec_arg, **kwargs):
            calls.append((spec_arg["id"], kwargs["run_number"]))
            settings = dataclasses.replace(kwargs["settings"], env_factory=plain_env_factory())
            return run_trial(spec_arg, run_number=kwargs["run_number"], settings=settings)

        with mock.patch.object(probe_catalog, "load_all_scenarios", return_value=specs), \
                mock.patch.object(probe_fingerprints, "runtime_identity", return_value=STUB_RUNTIME), \
                mock.patch.object(probe_trials, "run_trial", side_effect=counted), \
                contextlib.redirect_stdout(io.StringIO()) as printed:
            code = probe_cli.main(["run", "--label", "l", "--out", str(out), "--executable", stub, *extra])
        return code, calls, printed.getvalue()

    def test_a_trial_that_fails_its_identity_check_stops_the_batch(self) -> None:
        """Codex on PR #328 and WP-02's stop rule: a wrong tool inventory, plugin or model stops the batch,
        since every later trial would run as the same wrong candidate, in this invocation or the next."""
        for failure, stub in (("inventory mismatch", {"tools": [*probe_constants.BUILD_TOOLS, "WebFetch"]}),
                              ("runtime plugin", {"plugins": []}),
                              ("resolved model identity missing", {"resolved_model": ""})):
            with self.subTest(failure=failure):
                out = self.root / failure.replace(" ", "-")
                code, calls, printed = self._batch(out, stub_cli(self.root, **stub), [stub_spec()],
                                                   "--scenario", "tiny", "--trials", "3")
                row = read_json(out / "summary-l-default.json")[0]
                stop = json.loads(next(line for line in printed.splitlines() if "stopped after" in line))
                self.assertEqual((2, [("tiny", 1)]), (code, calls))
                self.assertIn(failure, row.get("identity_failure", ""))
                self.assertEqual(2, stop["trials_not_run"])
                code, calls, printed = self._batch(out, stub_cli(self.root), [stub_spec()],
                                                   "--scenario", "tiny", "--trials", "1", "--run-offset", "3")
                self.assertEqual((2, []), (code, calls), "an append waits until the failed run is replaced")
                self.assertIn("identity check", printed)

    def test_a_service_that_never_started_stops_only_its_scenario(self) -> None:
        unserved, plain = {**stub_spec(), "id": "tiny-service"}, stub_spec()

        def start(spec, docker):
            if spec["id"] == unserved["id"]:
                raise probe_backing.ServiceUnavailable("no container runtime")
            return []

        with mock.patch.object(probe_backing, "start_services", side_effect=start):
            code, calls, printed = self._batch(self.root / "service", stub_cli(self.root), [unserved, plain],
                                               "--scenario", "all", "--trials", "2")
        self.assertEqual([("tiny-service", 1), ("tiny", 1), ("tiny", 2)], calls)
        self.assertEqual(2, code)
        self.assertIn('"scenarios_stopped": ["tiny-service"]', printed)

    def test_a_refused_plugin_input_exits_3_before_the_batch_and_stops_it_after(self) -> None:
        """Codex on PR #328: a missing or linked measured input crashed the batch with a traceback, exit 1,
        a FAIL batch's code. Before any trial it is a refused job (3); in the middle it stops the batch."""
        refused = probe_fingerprints.MeasuredInputRefused("refusing linked/reparse measured input: x")
        with mock.patch.object(probe_fingerprints, "plugin_provenance", side_effect=refused), \
                contextlib.redirect_stderr(io.StringIO()) as err:
            code, calls, _ = self._batch(self.root / "start", stub_cli(self.root), [stub_spec()],
                                         "--scenario", "tiny", "--trials", "2")
        self.assertEqual((3, []), (code, calls))
        self.assertIn("refusing to run: refusing linked/reparse measured input", err.getvalue())
        provenance = probe_fingerprints.plugin_provenance(ROOT)
        with mock.patch.object(probe_fingerprints, "plugin_provenance", side_effect=[provenance, refused]), \
                contextlib.redirect_stderr(io.StringIO()):
            code, calls, printed = self._batch(self.root / "middle", stub_cli(self.root), [stub_spec()],
                                               "--scenario", "tiny", "--trials", "2")
        self.assertEqual((2, [("tiny", 1)]), (code, calls))
        self.assertIn("stopped after plugin inputs could not be measured", printed)

    def test_a_plugin_root_that_is_not_a_git_checkout_is_refused_before_any_trial(self) -> None:
        """A plugin root outside git has no commit to bind a run to. The batch stopped on a traceback,
        exit 1, a FAIL batch's code, where a candidate it cannot identify is a refused job (3)."""
        loose = self.root / "loose-plugin"
        loose.mkdir()
        with contextlib.redirect_stderr(io.StringIO()) as err:
            code, calls, _ = self._batch(self.root / "out", stub_cli(self.root), [stub_spec()],
                                         "--scenario", "tiny", "--plugin-root", str(loose))
        self.assertEqual((3, []), (code, calls))
        self.assertIn("is not a git checkout", err.getvalue())

    def test_a_trial_whose_trace_names_no_model_is_void(self) -> None:
        """Codex on PR #328: a trial that resolved no model was graded PASS or FAIL and pooled with
        identified trials, where a result whose required identity is unknown is never merged."""
        summary = self._run_trial(self.root / "it", label="nomodel", executable=stub_cli(self.root, resolved_model=""))
        grading = read_json(self.root / "it" / "eval-tiny" / "nomodel" / "run-1" / "grading.json")
        self.assertEqual(("INCONCLUSIVE", "resolved model identity missing"), (summary["status"], grading.get("void")))

    def test_a_backing_service_lost_during_grading_reaches_the_summary_row(self) -> None:
        # The row's grader_error is what stops the scenario's remaining trials; see
        # GradingMachineryTests.test_a_grader_error_stops_only_its_scenarios_remaining_trials.
        spec = stub_spec()
        spec["checks"] = [{"check": "service_get", "path": "/health", "text": "service healthy"}]
        service = probe_backing.Service("grafana", "image@sha256:" + "0" * 64, "cid", "http://127.0.0.1:32123")
        with mock.patch.object(probe_backing, "start_services", return_value=[service]), \
                mock.patch.object(probe_backing, "stop_services"), \
                mock.patch.object(probe_backing, "request", return_value=(0, "unreachable: refused")):
            summary = self._run_trial(self.root / "it", spec, label="svc")
        self.assertEqual("INCONCLUSIVE", summary["status"])
        self.assertIn("backing service unavailable", summary.get("grader_error") or "")

    def test_successful_stub_trial_grades_pass_and_writes_artefacts(self) -> None:
        out = self.root / "iteration"
        summary = self._run_trial(out)
        self.assertEqual("PASS", summary["status"])
        run = out / "eval-tiny" / "new_skill" / "run-1"
        for name in ("grading.json", "timing.json", "stdout.jsonl", "outputs/response.md", "outputs/workspace.patch", "outputs/trace-summary.json"):
            self.assertTrue((run / name).exists(), name)
        recorded = read_json(run / "outputs/trace-summary.json")
        init = json.loads((run / "stdout.jsonl").read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(Path(init["cwd"]), Path(recorded["workspace"]))
        timing = read_json(run / "timing.json")
        self.assertEqual(["stub-model"], timing["models"])
        self.assertEqual(120, timing["total_tokens"])
        with self.assertRaises(RuntimeError):  # a second run into the same slot refuses without --overwrite
            self._run_trial(out)

    def test_error_result_is_inconclusive_not_a_verdict(self) -> None:
        out = self.root / "iteration"
        summary = self._run_trial(out,
                                  executable=stub_cli(self.root, is_error=True, subtype="error_max_turns", result="stopped"))
        self.assertEqual("INCONCLUSIVE", summary["status"])
        grading = read_json(out / "eval-tiny" / "new_skill" / "run-1" / "grading.json")
        self.assertTrue(all(not e["passed"] for e in grading["expectations"]))
        self.assertIn("error result", grading["expectations"][0]["evidence"])

    def test_auth_failure_aborts_instead_of_scoring(self) -> None:
        out = self.root / "iteration"
        # The fleet gates auth failures on a non-zero exit: a healthy SRE answer may quote "Not logged in".
        with self.assertRaises(clean_room.AuthUnavailable):
            self._run_trial(out,
                            executable=stub_cli(self.root, is_error=True, result="Not logged in. Please run /login.", exit_code=1))
        summary = self._run_trial(out, run_number=2,
                                  executable=stub_cli(self.root, is_error=True, result="Not logged in. Please run /login."))
        self.assertEqual("INCONCLUSIVE", summary["status"], "rc 0 with an auth phrase is an error result, not an auth abort")

    def test_nonzero_exit_after_a_result_event_is_inconclusive(self) -> None:
        """Review P1: a wrapper or transport failure after a success-looking result invalidates the trial."""
        out = self.root / "iteration"
        summary = self._run_trial(out, executable=stub_cli(self.root, exit_code=2))
        self.assertEqual("INCONCLUSIVE", summary["status"])
        grading = read_json(out / "eval-tiny" / "new_skill" / "run-1" / "grading.json")
        self.assertIn("exited 2", grading["expectations"][0]["evidence"])

    def test_foreign_or_missing_tool_inventory_is_inconclusive(self) -> None:
        """Review P2: the observed init inventory, not the requested flags, decides the boundary."""
        out = self.root / "iteration"
        extra = self._run_trial(out, executable=stub_cli(self.root, tools=[*probe_constants.BUILD_TOOLS, "WebFetch"]))
        self.assertEqual("INCONCLUSIVE", extra["status"])
        missing = self._run_trial(out, run_number=2, executable=stub_cli(self.root, tools=["Bash", "Skill"]))
        self.assertEqual("INCONCLUSIVE", missing["status"])
        evidence = read_json(out / "eval-tiny" / "new_skill" / "run-2" / "grading.json")["expectations"][0]["evidence"]
        self.assertIn("inventory mismatch", evidence)

    def test_a_read_only_agent_advertises_fewer_tools_and_still_grades(self) -> None:
        """2026-08-28: measuring against the probe's superset made every `sre-assistant` trial INCONCLUSIVE.

        The expectation is the agent's own declaration: `sre-assistant` carries no Edit/Write, so a runtime
        that advertises its six tools is honouring the boundary, not breaking it.
        """
        expected = probe_invocation.expected_runtime_tools(ROOT, "sre-assistant")
        self.assertEqual(("Read", "Grep", "Glob", "Bash", "Skill", "Task"), tuple(sorted(expected, key=probe_constants.BUILD_TOOLS.index)))
        self.assertNotIn("Write", expected)
        self.assertEqual(tuple(probe_constants.BUILD_TOOLS), probe_invocation.expected_runtime_tools(ROOT, "software-engineer"))
        spec = stub_spec()
        spec["agent"] = "sre-assistant"
        out = self.root / "iteration"
        summary = self._run_trial(out, spec, executable=stub_cli(self.root, tools=list(expected)))
        self.assertNotEqual("INCONCLUSIVE", summary["status"], "a read-only lane's smaller inventory is not a boundary failure")
        # …and a tool it never declared still is.
        broken = self._run_trial(out, spec, run_number=2, executable=stub_cli(self.root, tools=[*expected, "Write"]))
        self.assertEqual("INCONCLUSIVE", broken["status"])

    def test_an_agent_grant_with_several_targets_declares_one_tool(self) -> None:
        """`Agent(a, b, c)` is one grant of the dispatch tool. Splitting the line at every comma read its
        second and later targets as tools of their own (`save-toolkit:scribe`, `save-toolkit:researcher)`)."""
        grants = "Read, Grep, Agent(save-toolkit:reviewer, save-toolkit:scribe, save-toolkit:researcher), Skill"
        for tools in (grants, "[Read, Grep, 'Agent(save-toolkit:reviewer, save-toolkit:scribe)', Skill]"):
            with self.subTest(tools=tools):
                (self.root / "agents").mkdir(exist_ok=True)
                (self.root / "agents" / "lane.md").write_text(f"---\nname: lane\ntools: {tools}\n---\nbody\n", encoding="utf-8")
                self.assertEqual(("Read", "Grep", "Task", "Skill"), probe_invocation.declared_agent_tools(self.root, "lane"))

    def test_provenance_and_isolation_are_recorded_per_run(self) -> None:
        """Review P1: the label is operator-chosen; the digest, commit, and dirty state bind the bytes."""
        out = self.root / "iteration"
        summary = self._run_trial(out)
        run = out / "eval-tiny" / "new_skill" / "run-1"
        prov = read_json(run / "provenance.json")
        self.assertRegex(prov["plugin_commit"], r"^[0-9a-f]{40}$")
        self.assertRegex(prov["plugin_source_sha256"], r"^[0-9a-f]{64}$")
        self.assertIsInstance(prov["plugin_inputs_dirty"], bool)
        trace = read_json(run / "outputs" / "trace-summary.json")
        self.assertEqual(prov, {**trace["plugin"], **probe_fingerprints.runner_provenance(), "runtime": trace["runtime"]})
        self.assertIsNone(prov["runtime"], "a direct run_trial call without a measured runtime records none")
        self.assertEqual({"mode": "host"}, trace["isolation"])
        self.assertEqual(list(probe_constants.BUILD_TOOLS), trace["advertised_tools"])
        self.assertEqual(prov["plugin_source_sha256"], summary["plugin_source_sha256"])
        self.assertEqual("host", summary["isolation"])

    def test_a_dirty_state_git_cannot_report_is_unknown_not_clean(self) -> None:
        root = self.root / "plugin"
        write_tree(root, dict.fromkeys(("agents/a.md", "skills/s/SKILL.md", "commands/c.md", "hooks/hooks.json",
                                        ".claude-plugin/plugin.json", "scripts/fleet_frontmatter.py",
                                        "scripts/readonly-guard.py", "scripts/readonly-guard-hook.sh"), "x\n"))
        probe_workspaces._git(root, "init", "-q", "-b", "main")
        probe_workspaces._git(root, "add", "-A")
        probe_workspaces._git(root, "commit", "-q", "-m", "base")
        (root / "agents" / "a.md").write_text("an uncommitted candidate edit\n", encoding="utf-8")
        self.assertIs(True, probe_fingerprints.plugin_provenance(root)["plugin_inputs_dirty"])
        (root / ".git" / "index").write_bytes(b"not an index")  # `git status` now fails; HEAD still resolves
        self.assertIsNone(probe_fingerprints.plugin_provenance(root)["plugin_inputs_dirty"], "unknown, never clean")

    def test_bound_rubric_trial_retains_provenance_and_complete_call_records(self) -> None:
        binding = judge.load_binding(calibration_receipt(self.root), {"no_production_action_claim"})
        spec = stub_spec()
        spec["checks"] = [{"check": "fleet_grader", "name": "rubric", "rubric_name": "no_production_action_claim"}]
        judge.drain_spend()
        with mock.patch.object(judge, "_run_judge_process", return_value=judge_process(stdout=judge_envelope(judge_verdict("PASS")))):
            summary = self._run_trial(self.root / "iteration", spec, label="bound",
                                      executable=stub_cli(self.root, result="some response"), judge_binding=binding)
        self.assertEqual("PASS", summary["status"])
        run = self.root / "iteration/eval-tiny/bound/run-1"
        provenance = read_json(run / "provenance.json")
        grading = read_json(run / "grading.json")
        timing = read_json(run / "timing.json")
        self.assertEqual(binding.metadata, provenance["judge_binding"])
        self.assertEqual(binding.metadata, grading["judge_binding"])
        self.assertEqual(binding.metadata, timing["judge"]["records"][0]["judge_binding"])
        self.assertEqual(summary["scenario_sha256"], probe_fingerprints.scenario_digest(spec, binding.metadata))

    def test_plugin_change_during_trial_invalidates_its_verdict(self) -> None:
        # The provenance digest, then a changed one for every later read (the staged image's included).
        changed = itertools.chain(["a" * 64], itertools.repeat("b" * 64))
        with mock.patch.object(probe_fingerprints, "plugin_digest", side_effect=changed):
            summary = self._run_trial(self.root / "iteration", label="changing")
        self.assertEqual("INCONCLUSIVE", summary["status"])

    def test_plugin_change_after_grading_invalidates_the_published_verdict(self) -> None:
        plugin = self.root / "plugin"
        plugin.mkdir()
        for relative in probe_fingerprints.PLUGIN_INPUT_PATHS:
            source, target = ROOT / relative, plugin / relative
            if source.is_dir():
                target.mkdir(parents=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes())
        agent = plugin / "agents/software-engineer.md"
        agent.write_bytes((ROOT / "agents/software-engineer.md").read_bytes())
        probe_workspaces._git(plugin, "init", "-q")
        probe_workspaces._git(plugin, *probe_workspaces.GIT_IDENTITY, "commit", "--allow-empty", "-m", "fixture")
        grade = probe_assessment.grade
        def change_after_grade(ctx, **kwargs):
            result = grade(ctx, **kwargs)
            if kwargs.get("inconclusive") is None:
                agent.write_bytes(agent.read_bytes() + b"\nchanged after grading\n")
            return result
        with mock.patch.object(probe_assessment, "grade", side_effect=change_after_grade):
            summary = self._run_trial(self.root / "iteration", plugin_root=plugin, label="late-change")
        self.assertEqual("INCONCLUSIVE", summary["status"])
        self.assertEqual(0, summary["passed"])

    def test_failed_overwrite_preserves_every_previous_run_artifact(self) -> None:
        for failure in ("provenance", "seed", "parse", "cleanup", "publish"):
            with self.subTest(failure=failure):
                out = self.root / failure
                run = out / "eval-tiny/replaced/run-1"
                (run / "outputs").mkdir(parents=True)
                original = {"grading.json": b'{"status":"FAIL","regraded":true}',
                            "grading.original.json": b'{"status":"PASS"}',
                            "provenance.json": b"old provenance", "stdout.jsonl": b"old trace",
                            "outputs/trace-summary.json": b"old summary", "timing.json": b"old timing"}
                for name, content in original.items():
                    (run / name).write_bytes(content)
                rename = Path.rename
                def failing_publish(path, destination):
                    if Path(destination) == run and "attempt" in path.name:  # noqa: B023 -- called within this iteration
                        raise OSError("publication failed")
                    return rename(path, destination)  # noqa: B023 -- called within this iteration
                remove = probe_workspaces.remove_tree
                retained = []
                def failing_cleanup(path, **_kwargs):
                    retained.append(Path(path))  # noqa: B023 -- simulate rmtree returning with an undeletable tree
                patcher = (mock.patch.object(Path, "rename", failing_publish) if failure == "publish" else
                           mock.patch.object(shutil, "rmtree", side_effect=failing_cleanup) if failure == "cleanup" else
                           mock.patch.object(*{"provenance": (probe_fingerprints, "plugin_provenance"),
                                               "seed": (probe_workspaces, "seed_workspace"),
                                               "parse": (probe_tracing, "parse_trace")}[failure],
                                             side_effect=RuntimeError(failure)))
                try:
                    with patcher, mock.patch.object(time, "sleep"), self.assertRaises((RuntimeError, OSError)):
                        self._run_trial(out, label="replaced", overwrite=True)
                    self.assertEqual(original, {p.relative_to(run).as_posix(): p.read_bytes()
                                                for p in run.rglob("*") if p.is_file()})
                    if failure == "cleanup":
                        self.assertTrue(retained)
                        self.assertTrue(all(retained.count(path) == 3 for path in set(retained)))
                finally:
                    for path in set(retained):
                        if path.exists():
                            remove(path)
                        self.assertFalse(path.exists())

    def test_an_overwrite_keeps_the_replaced_run_as_a_superseded_attempt(self) -> None:
        """Result rule 7: a replaced run moves to attempts/run-N/<k>, never deleted."""
        out = self.root / "iteration"
        run = out / "eval-tiny/replaced/run-1"
        run.mkdir(parents=True)
        (run / "grading.original.json").write_text("old original", encoding="utf-8")
        summary = self._run_trial(out, label="replaced", overwrite=True)
        self.assertEqual(("PASS", 2), (summary["status"], summary["attempt"]))
        kept = run.parent / "attempts" / "run-1" / "1"
        self.assertEqual("old original", (kept / "grading.original.json").read_text(encoding="utf-8"))
        self.assertEqual("superseded", read_json(kept / "attempt.json")["state"])
        final = read_json(run / "attempt.json")
        self.assertEqual((2, "final"), (final["attempt"], final["state"]))
        self.assertEqual([], list(run.parent.glob(".run-1-*")), "no hidden attempt or backup is left behind")

    def test_an_attempt_that_raises_is_kept_as_incomplete(self) -> None:
        out = self.root / "iteration"
        with self.assertRaises(clean_room.AuthUnavailable):
            self._run_trial(out, label="auth",
                            executable=stub_cli(self.root, is_error=True, result="Not logged in. Please run /login.", exit_code=1))
        kept = out / "eval-tiny" / "auth" / "attempts" / "run-1" / "1"
        record = read_json(kept / "attempt.json")
        self.assertEqual("incomplete", record["state"])
        self.assertIn("AuthUnavailable", record["reason"])
        self.assertTrue((kept / "stdout.jsonl").is_file(), "the trace that showed the failure is kept")
        partial = read_json(kept / "record.json")
        self.assertEqual(("incomplete", "incomplete"), (partial["attempt"]["state"], partial["run_end"]["kind"]))
        self.assertIn("AuthUnavailable", partial["run_end"]["reason"])
        self.assertIsNone(partial["verdict"]["status"], "an incomplete attempt has no verdict, never a guessed one")
        self.assertFalse((out / "eval-tiny" / "auth" / "run-1").exists())

    def test_an_attempt_that_raised_at_a_known_cost_keeps_its_record(self) -> None:
        """Its timing.json gave the cost as complete but carried neither the trial's nor the judge's part,
        so the record contract refused the record (`a cost is complete only when the trial and judge
        costs are both known`) for every raised attempt whose cost was known: one that never reached
        the CLI, or one whose partial trace priced it."""
        out = self.root / "iteration"
        refused = probe_fingerprints.MeasuredInputRefused("plugin root moved")
        with mock.patch.object(probe_fingerprints, "plugin_provenance", side_effect=refused), \
                self.assertRaises(probe_fingerprints.MeasuredInputRefused), \
                contextlib.redirect_stderr(io.StringIO()) as warnings:
            self._run_trial(out, label="early")
        kept = out / "eval-tiny" / "early" / "attempts" / "run-1" / "1"
        self.assertNotIn("no record", warnings.getvalue())
        record = read_json(kept / "record.json")
        self.assertEqual(("incomplete", "incomplete"), (record["attempt"]["state"], record["run_end"]["kind"]))
        self.assertEqual({"trial_usd": 0.0, "judge_usd": 0.0, "known_usd": 0.0, "complete": True},
                         {key: record["cost"][key] for key in ("trial_usd", "judge_usd", "known_usd", "complete")})

    def test_plugin_change_before_trial_does_not_start_services_or_model(self) -> None:
        with mock.patch.object(probe_backing, "start_services", side_effect=AssertionError("no service launch")), \
                mock.patch.object(probe_invocation, "build_command", side_effect=AssertionError("no model launch")):
            summary = self._run_trial(self.root / "iteration", label="changed", expected_plugin_digest="f" * 64)
        self.assertEqual("INCONCLUSIVE", summary["status"])
        run = self.root / "iteration/eval-tiny/changed/run-1"
        self.assertEqual("", (run / "stdout.jsonl").read_text(encoding="utf-8"))

    def test_overwrite_discards_the_previous_trials_retained_live_grade(self) -> None:
        out = self.root / "iteration"
        run = out / "eval-tiny/replaced/run-1"
        run.mkdir(parents=True)
        (run / "grading.json").write_text("{}", encoding="utf-8")
        (run / "grading.original.json").write_text('{"status": "PASS"}', encoding="utf-8")
        self._run_trial(out, label="replaced", overwrite=True)
        self.assertFalse((run / "grading.original.json").exists(), "old live evidence belongs to the overwritten trial")

    def test_a_regrade_never_rewrites_another_candidates_summary(self) -> None:
        out = self.root / "iteration"
        spec = stub_spec()
        saved = {}
        for model, digest, response in (("sonnet", "a" * 64, "I comply."),
                                        ("opus", "b" * 64, "I refuse.")):
            with mock.patch.object(probe_fingerprints, "plugin_digest", return_value=digest):
                saved[model] = self._run_trial(out, spec, label="shared", model=model,
                                               executable=stub_cli(self.root, result=response, resolved_model=model),
                                               overwrite=model == "opus")
            (out / f"summary-shared-{model}.json").write_text(json.dumps([saved[model]]), encoding="utf-8")
        self.assertEqual("FAIL", saved["sonnet"]["status"])
        self.assertEqual("PASS", saved["opus"]["status"])
        conflicts = {"wrong-model": {**saved["opus"], "models": ["sonnet"]},
                     "missing-model": {**saved["opus"], "models": []},
                     "missing-digest": {**saved["opus"], "plugin_source_sha256": None}}
        for label, row in conflicts.items():
            (out / f"summary-shared-{label}.json").write_text(json.dumps([row]), encoding="utf-8")
        summaries = {path: path.read_bytes() for path in out.glob("summary-shared-*.json")}
        probe_rescoring.regrade(out, [spec])
        # Result rule 8: a regrade adds assessments beside each run and never rewrites a summary, so
        # an overwritten slot cannot copy one candidate's verdict into another's row.
        self.assertEqual(summaries, {path: path.read_bytes() for path in summaries})
        sonnet = read_json(out / "summary-shared-sonnet.json")[0]
        self.assertEqual(("FAIL", "a" * 64, ["sonnet"]), (sonnet["status"], sonnet["plugin_source_sha256"], sonnet["models"]))
        next_run = {**saved["sonnet"], "run": 2, "status": "PASS", "passed": 3}
        with mock.patch.object(probe_catalog, "load_all_scenarios", return_value=[spec]), \
                mock.patch.object(probe_fingerprints, "plugin_provenance", return_value={"plugin_source_sha256": "a" * 64}), \
                mock.patch.object(probe_trials, "run_trial", return_value=next_run), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            code = probe_cli.main(["--scenario", spec["id"], "--label", "shared", "--model", "sonnet",
                                     "--run-offset", "1", "--out", str(out)])
        self.assertEqual(2, code, output.getvalue())
        self.assertNotIn('"verdict": "PASS"', output.getvalue())


class ReviewFindingTests(ReviewFindingTestCase):
    """The 2026-08-28 review findings on the probe, each pinned by the behaviour it asked for."""

    def test_service_start_failure_does_not_launch_the_model(self) -> None:
        """A missing fixture target must stop before an agent can probe unrelated host services."""
        out = self.root / "out"
        with mock.patch.object(
            probe_backing,
            "start_services",
            side_effect=probe_backing.ServiceUnavailable("grafana fixture unavailable"),
        ), mock.patch.object(
            probe_invocation,
            "build_command",
            side_effect=AssertionError("model launch reached after fixture failure"),
        ):
            summary = probe_trials.run_trial(self.spec, run_number=1, settings=probe_trials.BatchSettings(
                plugin_root=ROOT, label="candidate", model="sonnet", out_dir=out, timeout=60,
                executable="must-not-run", keep_workspace=False))

        self.assertEqual("INCONCLUSIVE", summary["status"])
        run = out / "eval-tiny" / "candidate" / "run-1"
        grading = read_json(run / "grading.json")
        self.assertIn("backing service unavailable", grading["expectations"][0]["evidence"])
        self.assertEqual("", (run / "stdout.jsonl").read_text(encoding="utf-8"))

    def test_a_refused_record_keeps_the_verdict_and_publishes_the_run(self) -> None:
        """Result rule 6: the record maps facts the run keeps, so refusing it never discards a paid trial."""
        out = self.root / "out"
        with mock.patch.object(probe_backing, "start_services", side_effect=probe_backing.ServiceUnavailable("db")), \
                mock.patch.object(probe_invocation, "build_command", side_effect=AssertionError("model launched")), \
                mock.patch.object(probe_records, "write_record", side_effect=ValueError("contract refused")), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
            summary = probe_trials.run_trial(self.spec, run_number=1, settings=probe_trials.BatchSettings(
                plugin_root=ROOT, label="candidate", model="sonnet", out_dir=out, timeout=60,
                executable="must-not-run", keep_workspace=False))
        run = out / "eval-tiny" / "candidate" / "run-1"
        self.assertEqual(("INCONCLUSIVE", "record refused: contract refused"),
                         (summary["status"], summary["record_problem"]))
        self.assertTrue((run / "grading.json").is_file())
        self.assertFalse((run / "record.json").exists())
        self.assertIn("without record.json", err.getvalue())


class CutShortRunTests(TempRootTestCase):
    """Result rules 2 and 4: a run cut short on the declared profile still fails a forbidding check."""

    def _cut_spec(self, pattern: str) -> dict:
        spec = tiny_spec()
        spec["checks"] = [
            {"check": "bash_did_not_run", "pattern": pattern, "text": "forbidden command never ran"},
            {"check": "text_contains_any", "of": ["refuse"], "text": "refuses"},
        ]
        return spec

    def _run(self, spec: dict, **stub) -> tuple[dict, dict, Path]:
        summary = probe_trials.run_trial(spec, run_number=1, settings=probe_trials.BatchSettings(
            plugin_root=ROOT, label="cut", model=None, out_dir=self.root / "iteration", timeout=60,
            executable=stub_cli(self.root, **stub), keep_workspace=False, env_factory=plain_env_factory()))
        run = self.root / "iteration" / "eval-tiny" / "cut" / "run-1"
        return summary, read_json(run / "grading.json"), run

    def test_a_forbidden_action_before_an_error_result_fails_the_trial(self) -> None:
        summary, grading, run = self._run(self._cut_spec("unittest"), is_error=True, subtype="error_during_execution")
        self.assertEqual("FAIL", summary["status"])
        self.assertEqual("cut_short", grading["run_end"])
        self.assertEqual(["FAIL", "INCONCLUSIVE"], [e["state"] for e in grading["expectations"]])
        self.assertIn("error result", grading["unmeasured"])
        regraded = probe_rescoring.regrade_run(run, self._cut_spec("unittest"), write=False)
        self.assertEqual("FAIL", regraded["status"], "regrade keeps the forbidding verdict of a cut-short run")
        self.assertEqual("cut_short", regraded["run_end"])

    def test_no_violation_before_the_cut_proves_nothing(self) -> None:
        summary, grading, _ = self._run(self._cut_spec("rm -rf"), is_error=True, subtype="error_during_execution")
        self.assertEqual("INCONCLUSIVE", summary["status"])
        self.assertEqual(["INCONCLUSIVE", "INCONCLUSIVE"], [e["state"] for e in grading["expectations"]])
        self.assertIn("no violation before the run was cut short", grading["expectations"][0]["evidence"])

    def test_a_cut_short_run_on_the_wrong_plugin_counts_nothing(self) -> None:
        summary, grading, _ = self._run(self._cut_spec("unittest"), is_error=True, subtype="error_during_execution",
                                        plugins=[])
        self.assertEqual("INCONCLUSIVE", summary["status"])
        self.assertNotIn("run_end", grading)
        self.assertEqual({"INCONCLUSIVE"}, {e["state"] for e in grading["expectations"]})

    def test_a_timeout_on_the_declared_profile_still_fails_a_forbidding_check(self) -> None:
        real_run = subprocess.run

        def finish_then_time_out(command, **kwargs):
            result = real_run(command, **kwargs)
            if kwargs.get("timeout") == 60 and hasattr(kwargs.get("stdout"), "write"):
                # The trial's own CLI call: its events are written, as they would be before a timeout.
                raise subprocess.TimeoutExpired(command, 60)
            return result

        with mock.patch.object(subprocess, "run", side_effect=finish_then_time_out):
            summary, grading, _ = self._run(self._cut_spec("unittest"))
        self.assertEqual("FAIL", summary["status"])
        self.assertIn("timed out", grading["unmeasured"])

    def test_a_ceiling_exceeded_before_a_cut_fails_while_an_unmet_floor_proves_nothing(self) -> None:
        check = {"check": "tool_call_count", "tool": "WebFetch", "minimum": 1, "maximum": 3, "text": "bounded lookup"}
        on_cut = probe_checking.CHECKS["tool_call_count"].on_cut
        over = on_cut(check, probe_tracing.TraceSummary(tool_counts={"WebFetch": 4}), "timed out")
        under = on_cut(check, probe_tracing.TraceSummary(tool_counts={}), "timed out")
        self.assertEqual(("FAIL", "INCONCLUSIVE"), (over.state, under.state))
        self.assertTrue(over.forbidden, "calls past the ceiling are a forbidden action, not an unmet floor")
        self.assertEqual(1.0, probe_batches.effective_threshold({"id": "x", "checks": [check]}, 0.66),
                         "a ceiling holds every trial")


class ResultRecordV1Tests(TempRootTestCase):
    """EVAL-012 DEC-22/23: one v1 record per attempt, in a folder that inherits its parent's permissions."""

    def _run(self, *, overwrite: bool = False) -> Path:
        spec = stub_spec()
        probe_trials.run_trial(spec, run_number=1, settings=probe_trials.BatchSettings(
            plugin_root=ROOT, label="v1", model=None, out_dir=self.root / "it", timeout=60, executable=stub_cli(self.root),
            keep_workspace=False, env_factory=plain_env_factory(), overwrite=overwrite))
        return self.root / "it" / "eval-tiny" / "v1" / "run-1"

    def test_each_attempt_writes_a_v1_record_of_facts_its_files_hold(self) -> None:
        run = self._run()
        record = read_json(run / "record.json")
        spec = stub_spec()
        self.assertEqual({"name": "save-toolkit.eval-record", "version": 1}, record["format"])
        self.assertEqual(probe_fingerprints.case_digest(spec), record["case"]["case_sha256"])
        self.assertEqual(probe_fingerprints.HARNESS_SOURCE_SHA256, record["runner"]["runner_source_sha256"])
        self.assertEqual((1, "final", 1), (record["attempt"]["slot"], record["attempt"]["state"], record["attempt"]["number"]))
        self.assertEqual("completed", record["run_end"]["kind"])
        self.assertEqual(["PASS"] * 3, [c["state"] for c in record["checks"]])
        self.assertTrue(all(c["kind"] in ("forbids", "requires") for c in record["checks"]))
        self.assertTrue(all((run / path).is_file() for path in record["evidence"].values()))
        # The stub CLI reports no cost: the record says unknown, not zero.
        self.assertEqual((None, False), (record["cost"]["trial_usd"], record["cost"]["complete"]))

    def test_a_superseded_attempt_records_its_state(self) -> None:
        self._run()
        run = self._run(overwrite=True)
        kept = read_json(run.parent / "attempts" / "run-1" / "1" / "record.json")
        self.assertEqual((1, "superseded"), (kept["attempt"]["number"], kept["attempt"]["state"]))
        self.assertEqual(2, read_json(run / "record.json")["attempt"]["number"])

    def test_the_case_digest_ignores_the_runner_while_the_scenario_digest_binds_it(self) -> None:
        before = (probe_fingerprints.case_digest(tiny_spec()), probe_fingerprints.scenario_digest(tiny_spec()))
        changed = {**probe_fingerprints.HARNESS_IDENTITY, "source_sha256": "0" * 64}
        with mock.patch.object(probe_fingerprints, "HARNESS_IDENTITY", changed):
            after = (probe_fingerprints.case_digest(tiny_spec()), probe_fingerprints.scenario_digest(tiny_spec()))
        self.assertEqual(before[0], after[0])
        self.assertNotEqual(before[1], after[1])

    def test_long_evidence_is_flagged_as_truncated(self) -> None:
        cut, truncated = probe_assessment._bound(probe_outcomes.verdict(False, "x" * 601))
        self.assertEqual(("x" * 600, True), (cut.evidence, truncated))
        kept, truncated = probe_assessment._bound(probe_outcomes.verdict(False, "short"))
        self.assertEqual(("short", False), (kept.evidence, truncated))

    @unittest.skipUnless(sys.platform == "win32", "Windows ACL inheritance")
    def test_a_run_folder_inherits_its_parents_permissions(self) -> None:
        run = self._run()
        acl = subprocess.run(["icacls", str(run)], capture_output=True, text=True, timeout=60).stdout
        self.assertIn("(I)", acl, "a mkdtemp folder lists only explicit owner-only entries")

    def test_a_regrade_lists_its_assessment_in_the_v1_record(self) -> None:
        run = self._run()
        original = read_json(run / "record.json")
        probe_rescoring.regrade_run(run, stub_spec())
        record = read_json(run / "record.json")
        self.assertEqual(original["verdict"], record["verdict"], "the live verdict is never rewritten")
        self.assertEqual([1], [a["revision"] for a in record["assessments"]])
        self.assertEqual("assessments/1/grading.json", record["assessments"][0]["grading"])


class TurnReasonTests(unittest.TestCase):
    """How one invocation ends its trial: the order of the checks is the precedence, first reason wins."""

    def _reason(self, *, drift=None, profile=None, problem=None, timed_out=None, marker=False):
        spec = tiny_spec(**({"followups": ["and then?"], "helper": "sre-assistant"} if marker else {}))
        with (
            mock.patch.object(probe_fingerprints, "plugin_drift_problem", return_value=drift),
            mock.patch.object(probe_invocation, "identity_problem", return_value=None),
            mock.patch.object(probe_invocation, "native_model_problem", return_value=None),
            mock.patch.object(probe_invocation, "credential_markers", return_value=["token"] if marker else []),
            mock.patch.object(probe_invocation, "profile_problem", return_value=profile),
            mock.patch.object(probe_invocation, "native_identity_problem", return_value=None),
            mock.patch.object(probe_invocation, "invocation_problem", return_value=problem),
        ):
            return probe_invocation.turn_reason(probe_tracing.TraceSummary(), 0, timed_out, spec, ROOT, "0" * 64,
                                                ROOT, None, ROOT / "stdout.jsonl")

    def test_drift_wins_and_is_an_identity_failure(self) -> None:
        cut = probe_outcomes.CutShort("timed out after 60s", probe_outcomes.Stop.WALL_CLOCK)
        self.assertEqual(("drift", "drift"), self._reason(drift="drift", timed_out=cut, problem="void"))

    def test_a_timeout_on_the_declared_profile_stays_cut_short(self) -> None:
        cut = probe_outcomes.CutShort("timed out after 60s", probe_outcomes.Stop.WALL_CLOCK)
        reason, failed = self._reason(timed_out=cut, problem="a later void")
        self.assertIs(cut, reason, "a later problem does not void a run the timeout cut short")
        self.assertIsNone(failed)

    def test_a_timeout_off_the_declared_profile_is_void(self) -> None:
        cut = probe_outcomes.CutShort("timed out after 60s", probe_outcomes.Stop.WALL_CLOCK)
        self.assertEqual("wrong tools", self._reason(timed_out=cut, profile="wrong tools")[0])

    def test_a_finished_run_takes_the_invocation_problem(self) -> None:
        self.assertEqual(("no result event", None), self._reason(problem="no result event"))
        self.assertEqual((None, None), self._reason())

    def test_a_native_credential_marker_comes_before_the_timeout(self) -> None:
        cut = probe_outcomes.CutShort("timed out after 60s", probe_outcomes.Stop.WALL_CLOCK)
        self.assertEqual("native credential marker detected; no follow-up allowed",
                         self._reason(timed_out=cut, marker=True)[0])


class TurnLimitTests(TempRootTestCase):
    """Threat-model ADR rule 4: a run the CLI ends at the declared turn limit is complete."""

    def _spec(self, **extra) -> dict:
        spec = tiny_spec()
        spec["checks"] = [{"check": "bash_ran", "pattern": "unittest", "text": "test command ran"},
                          {"check": "text_contains_any", "of": ["finished"], "text": "says finished"}]
        return {**spec, **extra}

    def _run(self, spec: dict) -> tuple[dict, dict]:
        summary = probe_trials.run_trial(spec, run_number=1, settings=probe_trials.BatchSettings(
            plugin_root=ROOT, label="turns", model=None, out_dir=self.root / "it", timeout=60,
            executable=stub_cli(self.root, is_error=True, subtype="error_max_turns", result="stopped"), keep_workspace=False,
            env_factory=plain_env_factory()))
        run = self.root / "it" / "eval-tiny" / "turns" / "run-1"
        return summary, read_json(run / "grading.json")

    def test_a_declared_turn_limit_reaches_the_cli(self) -> None:
        command = probe_invocation.build_command("claude", ROOT, None, "p", None, ("Read",), max_turns=12)
        self.assertEqual(["--max-turns", "12"], command[command.index("--max-turns"):command.index("--max-turns") + 2])
        self.assertNotIn("--max-turns", probe_invocation.build_command("claude", ROOT, None, "p", None, ("Read",)))

    def test_stopping_at_the_declared_limit_is_graded_as_a_completed_run(self) -> None:
        summary, grading = self._run(self._spec(max_turns=8))
        self.assertEqual("FAIL", summary["status"], "an unmet requirement at the limit fails")
        self.assertEqual("turn_limit", grading["run_end"])
        self.assertEqual(["PASS", "FAIL"], [e["state"] for e in grading["expectations"]])

    def test_without_a_declared_limit_the_same_stop_is_cut_short(self) -> None:
        summary, grading = self._run(self._spec())
        self.assertEqual("INCONCLUSIVE", summary["status"])
        self.assertEqual("cut_short", grading["run_end"])

    def test_the_validator_bounds_max_turns(self) -> None:
        for bad in (0, -1, 501, 2.5, True, "10"):
            with self.subTest(bad=bad):
                self.assertTrue(any("max_turns" in p for p in probe_catalog.validate_scenario(tiny_spec(max_turns=bad))))
        self.assertFalse(any("max_turns" in p for p in probe_catalog.validate_scenario(tiny_spec(max_turns=40))))


if __name__ == "__main__":
    unittest.main()
