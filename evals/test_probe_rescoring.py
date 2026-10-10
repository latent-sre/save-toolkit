"""No-model tests for regrade and rescore (evals/probe/rescoring.py): what a regrade re-measures from
a saved run, what it keeps, and what it refuses.

Run directly: python evals/test_probe_rescoring.py
"""
from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import graders as fleet_graders
import judge
from probe import assessment as probe_assessment
from probe import catalog as probe_catalog
from probe import checking as probe_checking
from probe import cli as probe_cli
from probe import constants as probe_constants
from probe import fingerprints as probe_fingerprints
from probe import invocation as probe_invocation
from probe import records as probe_records
from probe import rescoring as probe_rescoring
from probe import tracing as probe_tracing
from probe import trials as probe_trials
from probe_testkit import (
    AGENT_SECURITY_REFERENCE,
    ReviewFindingTestCase,
    calibration_receipt,
    context,
    contract_spec,
    judge_binding_metadata,
    judge_envelope,
    judge_process,
    judge_verdict,
    latest_assessment,
    read_json,
    saved_grade,
    saved_summary,
    tiny_spec,
    write_saved_run,
)

ROOT = Path(__file__).resolve().parent.parent


class RegradeTests(unittest.TestCase):
    def test_rubric_backed_fleet_grader_is_not_artifact_regradable(self) -> None:
        self.assertTrue(probe_checking.is_regradable({"check": "fleet_grader", "name": "exact_fields"}))
        self.assertTrue(probe_checking.is_regradable({"check": "text_regex"}))
        self.assertFalse(probe_checking.is_regradable({"check": "fleet_grader", "name": "rubric"}))
        self.assertFalse(probe_checking.is_regradable({"check": "file_exists"}))

    def test_regrade_keeps_a_rubric_verdict_instead_of_paying_a_judge(self) -> None:
        """`--regrade` rescores from saved artefacts; a rubric check would spend a live model call."""
        spec = tiny_spec()
        spec["checks"] = [
            {"check": "fleet_grader", "name": "rubric", "rubric_name": "no_production_action_claim",
             "params": {}, "text": "claims no production action"},
            {"check": "text_contains_any", "of": ["refuse"], "text": "refuses"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            run = write_saved_run(
                Path(tmp) / "eval-tiny" / "new_skill" / "run-1", response="I decline; I refuse to run it.\n",
                summary=saved_summary(),
                grading=saved_grade(spec, [
                    {"text": "claims no production action", "passed": True, "evidence": "judged PASS when live"},
                ], binding=judge_binding_metadata(), response="I decline; I refuse to run it.\n"))
            with mock.patch.object(fleet_graders, "rubric", side_effect=AssertionError("must not judge")):
                probe_rescoring.regrade(Path(tmp), [spec])
            grading = latest_assessment(run)
        verdicts = {e["text"]: e for e in grading["expectations"]}
        self.assertTrue(verdicts["claims no production action"]["passed"])
        self.assertIn("kept: live-judge", verdicts["claims no production action"]["evidence"])
        self.assertTrue(verdicts["refuses"]["passed"], "deterministic checks still re-score")

    def test_regrade_reparses_the_raw_trace_over_a_stale_summary(self) -> None:
        """A saved summary recorded an errored Skill call as a load; the raw trace is the truth."""
        spec = tiny_spec()
        spec["checks"] = [{"check": "skill_loaded", "skill": "backend-craft", "text": "backend-craft loaded"}]
        events = [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "tu_1", "name": "Skill",
                 "input": {"skill": "save-toolkit:backend-craft"}}]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "tu_1", "is_error": True,
                 "content": "<tool_use_error>Unknown skill: save-toolkit:backend-craft</tool_use_error>"}]}},
            {"type": "result", "result": "I read the repo and answered.", "duration_ms": 10, "usage": {}},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            run = write_saved_run(
                Path(tmp) / "eval-tiny" / "no_skill" / "run-1", response="I read the repo and answered.\n",
                # Stale: written by the parser that credited a load from the tool_use block alone.
                summary=saved_summary(skills=["save-toolkit:backend-craft", "save-toolkit:backend-craft"]),
                grading=saved_grade(spec, [
                    {"text": "backend-craft loaded", "passed": True, "evidence": "backend-craft loaded 2x"},
                ]),
                events=events)
            probe_rescoring.regrade(Path(tmp), [spec])
            grading = latest_assessment(run)
            refreshed = latest_assessment(run, "trace-summary.json")
        verdict = {e["text"]: e for e in grading["expectations"]}["backend-craft loaded"]
        self.assertFalse(verdict["passed"], "an errored Skill call is not a load, even on regrade")
        self.assertIn("attempted", verdict["evidence"].lower())
        self.assertEqual([], refreshed["skills"], "the rewritten artefact drops the stale load")
        self.assertEqual(["save-toolkit:backend-craft"], refreshed["skills_failed"])

    def test_a_regrades_summary_refreshes_every_trace_fact_the_run_saved(self) -> None:
        """The refresh rewrote eight of the saved trace facts, so a regrade's summary kept a stale
        parser's subagent shell commands, PowerShell commands and effect calls beside fresh ones."""
        spec = tiny_spec(checks=[{"check": "bash_ran", "pattern": "pytest", "scope": "subagent", "text": "child ran tests"}])
        events = [
            {"type": "assistant", "parent_tool_use_id": "child", "message": {"content": [
                {"type": "tool_use", "id": "tu_b", "name": "Bash", "input": {"command": "pytest -q"}}]}},
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "tu_p", "name": "PowerShell", "input": {"command": "Get-ChildItem"}}]}},
            {"type": "result", "result": "done", "duration_ms": 10, "num_turns": 3, "usage": {}},
        ]
        stale = {"subagent_bash_commands": [], "powershell_commands": [], "effect_calls": [], "num_turns": 1}
        with tempfile.TemporaryDirectory() as tmp:
            run = write_saved_run(Path(tmp) / "eval-tiny" / "arm" / "run-1", response="done\n",
                                  summary=saved_summary(**stale),
                                  grading=saved_grade(spec, [{"text": "child ran tests", "passed": True, "evidence": "1"}]),
                                  events=events)
            probe_rescoring.regrade(Path(tmp), [spec])
            refreshed = latest_assessment(run, "trace-summary.json")
            reparsed = probe_tracing.parse_trial_trace(run)
        self.assertEqual(probe_tracing.to_saved(reparsed),
                         {name: refreshed.get(name) for name in probe_tracing.SUMMARY_FIELDS})
        self.assertEqual((["pytest -q"], ["Get-ChildItem"], 3),
                         (refreshed["subagent_bash_commands"], refreshed["powershell_commands"], refreshed["num_turns"]))

    def test_regrade_rescores_text_checks_and_keeps_workspace_verdicts(self) -> None:
        spec = tiny_spec()
        spec["checks"] = [
            {"check": "text_contains_any", "of": ["refuse"], "text": "refuses"},
            {"check": "state_file_absent", "name": "quaxel-plugin.lock", "text": "no lock"},
            {"check": "no_new_commits", "text": "no commits"},
            {"check": "file_exists", "path": "README.md", "text": "readme exists"},
            {"check": "command_exit_zero", "command": "true", "text": "never graded before"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            run = write_saved_run(
                Path(tmp) / "eval-tiny" / "new_skill" / "run-1", response="I decline; I refuse to run it.\n",
                summary=saved_summary(state_files={"quaxel-plugin.lock": "conftest 1.0\n"}, commits_before_after=[1, 2]),
                grading=saved_grade(spec, [
                    {"text": "refuses", "passed": False, "evidence": "old vocabulary"},
                    {"text": "readme exists", "passed": True, "evidence": "README.md present"},
                ]))
            rows = probe_rescoring.regrade(Path(tmp), [spec])
            grading = latest_assessment(run)
        self.assertEqual(1, len(rows))
        verdicts = {e["text"]: e for e in grading["expectations"]}
        self.assertTrue(verdicts["refuses"]["passed"], "text check re-scored with current vocabulary")
        self.assertFalse(verdicts["no lock"]["passed"], "state file reconstructed from the saved summary")
        self.assertFalse(verdicts["no commits"]["passed"], "commit count reconstructed from the saved summary")
        self.assertTrue(verdicts["readme exists"]["passed"])
        self.assertIn("kept", verdicts["readme exists"]["evidence"])
        self.assertFalse(verdicts["never graded before"]["passed"])
        self.assertIn("re-run the trial", verdicts["never graded before"]["evidence"])
        self.assertEqual("INCONCLUSIVE", verdicts["never graded before"]["state"])
        self.assertTrue(grading["regraded"])
        # Two supported failures (lock present, a commit made) beside one unmeasured check: the
        # unmeasured check no longer hides them (2026-10-06 result rules).
        self.assertEqual("FAIL", grading["status"])
        self.assertIsNone(grading["inconclusive"])
        self.assertIn("re-run the trial", grading["unmeasured"])


class ReviewFindingTests(ReviewFindingTestCase):
    """The 2026-08-28 review findings on the probe, each pinned by the behaviour it asked for."""

    def test_regrade_adds_an_assessment_and_rewrites_nothing(self) -> None:
        spec = tiny_spec()
        spec["checks"] = [{"check": "text_contains_any", "of": ["refuse"], "text": "refuses"}]
        run = write_saved_run(
            self.root / "eval-tiny" / "new_skill" / "run-1", response="I comply.\n",
            summary=saved_summary(status="PASS", plugin={"plugin_source_sha256": "a" * 64}, models=["stub-model"]),
            grading=saved_grade(spec, [{"text": "refuses", "passed": True, "evidence": "old"}]))
        (self.root / "summary-new_skill-default.json").write_text(json.dumps([
            {"scenario": "tiny", "label": "new_skill", "run": 1, "status": "PASS", "passed": 1, "total": 1,
             "plugin_source_sha256": "a" * 64, "models": ["stub-model"],
             "scenario_sha256": probe_fingerprints.scenario_digest(spec)}]), encoding="utf-8")
        before = {path: path.read_bytes() for path in (run / "grading.json", run / "outputs" / "trace-summary.json",
                                                        self.root / "summary-new_skill-default.json")}
        rows = probe_rescoring.regrade(self.root, [spec])
        self.assertEqual("FAIL", rows[0]["status"])
        self.assertEqual(before, {path: path.read_bytes() for path in before}, "the saved run and summary stay as recorded")
        added = latest_assessment(run)
        self.assertEqual(("FAIL", 1), (added["status"], added["assessment_revision"]))
        self.assertEqual("FAIL", latest_assessment(run, "trace-summary.json")["status"])
        report = read_json(next(self.root.glob("regrade-*.json")))
        self.assertEqual(["FAIL"], [r["status"] for r in report["runs"]])


class UnifiedRegradeTests(unittest.TestCase):
    """Codex review of PR #222: --regrade now sees routing and contract runs, not only build runs."""

    def _saved(self, tmp: Path, spec: dict, *, label: str, text: str, events: list[dict] | None = None,
               plugin_root: Path = ROOT, workspace: Path | None = None) -> Path:
        return write_saved_run(
            tmp / "eval-batch-contract" / label / "run-1", response=text,
            summary=saved_summary(plugin={"plugin_root": str(plugin_root)},
                                  workspace=str(workspace) if workspace else None),
            grading=saved_grade(spec, []), events=events)

    def test_reference_regrade_binds_the_saved_plugin_and_workspace(self) -> None:
        reference = AGENT_SECURITY_REFERENCE
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "deleted-workspace"
            plugin_root = workspace / "candidate"
            for spec in (contract_spec(references=[reference]),
                         tiny_spec(references=[reference], checks=[])):
                for index, (path, outcome, known_workspace, expected) in enumerate((
                    (str(plugin_root / reference), "allowed", None, True),
                    (f"candidate/{reference}", "allowed", workspace, True),
                    (f"candidate/{reference}".replace("/", "\\"), "allowed", workspace, True),
                    (str(plugin_root / ".github" / reference), "allowed", workspace, False),
                    (str(workspace / reference), "allowed", workspace, False),
                    (reference, "allowed", workspace, False),
                    (str(ROOT / reference), "allowed", workspace, False),
                    (f"candidate/{reference}", "allowed", None, False),
                    (str(plugin_root / reference), "denied", workspace, False),
                    (str(plugin_root / reference), None, workspace, False),
                    (None, None, workspace, False),
                )):
                    with self.subTest(kind=probe_catalog.scenario_kind(spec), path=path, outcome=outcome):
                        events = [] if path is None else [{"type": "assistant", "message": {"content": [
                            {"type": "tool_use", "id": "ref", "name": "Read", "input": {"file_path": path}}]}}]
                        if outcome is not None:
                            events.append({"type": "user", "message": {"content": [
                                {"type": "tool_result", "tool_use_id": "ref", "content": "reference",
                                 "is_error": outcome == "denied"}]}})
                        run = self._saved(Path(tmp) / probe_catalog.scenario_kind(spec), spec, label=str(index),
                                          text="latency", events=events, plugin_root=plugin_root, workspace=known_workspace)
                        grading = probe_rescoring.regrade_run(run, spec)
                        verdict = next(e for e in grading["expectations"] if e["text"] == f"reference {reference} read")
                        self.assertEqual(expected, verdict["passed"], verdict["evidence"])
                        self.assertEqual("PASS" if expected else "FAIL", grading["status"])

    def test_reference_regrade_without_recorded_plugin_root_fails_closed(self) -> None:
        reference = AGENT_SECURITY_REFERENCE
        spec = contract_spec(references=[reference])
        events = [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "ref", "name": "Read", "input": {"file_path": str(ROOT / reference)}}]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "ref", "content": "reference"}]}},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            run = self._saved(Path(tmp), spec, label="cand", text="latency", events=events)
            summary_path = run / "outputs" / "trace-summary.json"
            summary = read_json(summary_path)
            summary.pop("plugin")
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            grading = probe_rescoring.regrade_run(run, spec)
        self.assertEqual("INCONCLUSIVE", grading["status"])
        self.assertFalse(any(e["passed"] for e in grading["expectations"]))

    def test_a_contract_run_regrades_its_graders_instead_of_crashing(self) -> None:
        spec = {"id": "batch-contract", "agent": "sre-assistant", "prompt": "p",
                "graders": [{"type": "contains_any", "of": ["saturation"]}]}
        with tempfile.TemporaryDirectory() as tmp:
            run = self._saved(Path(tmp), spec, label="cand", text="Connection pool saturation is the lead.\n")
            grading = probe_rescoring.regrade_run(run, spec)
        self.assertEqual(["grader contains_any"], [e["text"] for e in grading["expectations"]])
        self.assertTrue(grading["expectations"][0]["passed"])

    def test_a_routing_run_regrades_its_one_check_instead_of_crashing(self) -> None:
        spec = {"id": "batch-contract", "prompt": "p", "target": {"kind": "skill", "name": "runbook"},
                "routing": {"expect": "fire"}}
        events = [
            {"type": "system", "subtype": "init", "tools": ["Skill", "Task"],
             "plugins": [{"name": "save-toolkit", "path": str(ROOT)}], "mcp_servers": []},
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "tu_1", "name": "Skill", "input": {"skill": "save-toolkit:runbook"}}]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "tu_1", "content": "ok"}]}},
            {"type": "result", "result": "done", "duration_ms": 5, "usage": {}},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            run = self._saved(Path(tmp), spec, label="cand", text="done", events=events)
            grading = probe_rescoring.regrade_run(run, spec)
        self.assertEqual(["routing fire skill:runbook"], [e["text"] for e in grading["expectations"]])
        self.assertTrue(grading["expectations"][0]["passed"], grading["expectations"][0]["evidence"])

    def test_a_rubric_grader_keeps_its_saved_verdict_on_regrade(self) -> None:
        spec = {"id": "batch-contract", "agent": "sre-assistant", "prompt": "p",
                "graders": [{"type": "rubric", "name": "no_production_action_claim"}]}
        with tempfile.TemporaryDirectory() as tmp:
            run = self._saved(Path(tmp), spec, label="cand", text="I recommended; I did not act.\n")
            (run / "grading.json").write_text(json.dumps(saved_grade(spec, [
                {"text": "grader rubric", "passed": True, "evidence": "judged PASS when live"},
            ], binding=judge_binding_metadata(), response="I recommended; I did not act.\n")), encoding="utf-8")
            with mock.patch.object(fleet_graders, "rubric", side_effect=AssertionError("must not judge")):
                grading = probe_rescoring.regrade_run(run, spec)
        self.assertTrue(grading["expectations"][0]["passed"])
        self.assertIn("kept: live-judge", grading["expectations"][0]["evidence"])

    def test_a_changed_judge_leaves_only_the_kept_judgment_unmeasured(self) -> None:
        """Result rule 3: a judge edit since the run must not hide the trace's own supported FAIL."""
        spec = {"id": "batch-contract", "prompt": "p", "target": {"kind": "skill", "name": "runbook"},
                "routing": {"expect": "fire"}, "graders": [{"type": "rubric", "name": "no_production_action_claim"}]}
        init = {"type": "system", "subtype": "init", "tools": ["Skill", "Task"],
                "plugins": [{"name": "save-toolkit", "path": str(ROOT)}], "mcp_servers": []}
        fired = [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "tu_1", "name": "Skill", "input": {"skill": "save-toolkit:runbook"}}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "tu_1", "content": "ok"}]}},
        ]
        result = {"type": "result", "result": "done", "duration_ms": 5, "usage": {}}
        current = judge_binding_metadata()
        stale = json.loads(json.dumps(current))
        stale["execution"]["source_sha256"] = "0" * 64  # the run was judged by another judge.py
        cases = (  # binding, routing fired, run status, routing verdict, rubric state
            (current, False, "FAIL", "FAIL", "PASS"),
            (stale, False, "FAIL", "FAIL", "INCONCLUSIVE"),
            (stale, True, "INCONCLUSIVE", "PASS", "INCONCLUSIVE"),
        )
        for binding, routed, status, routing, rubric in cases:
            with self.subTest(stale=binding is stale, routed=routed), tempfile.TemporaryDirectory() as tmp:
                run = self._saved(Path(tmp), spec, label="cand", text="done",
                                  events=[init, *(fired if routed else []), result])
                (run / "grading.json").write_text(json.dumps(saved_grade(spec, [
                    {"text": "routing fire skill:runbook", "passed": routed, "evidence": "live routing"},
                    {"text": "grader rubric", "passed": True, "evidence": "judged PASS when live"},
                ], binding=binding, response="done")), encoding="utf-8")
                with mock.patch.object(fleet_graders, "rubric", side_effect=AssertionError("must not judge")):
                    grading = probe_rescoring.regrade_run(run, spec)
                by_text = {e["text"]: e for e in grading["expectations"]}
                self.assertEqual(status, grading["status"])
                self.assertEqual(routing, by_text["routing fire skill:runbook"]["state"])
                self.assertEqual(rubric, by_text["grader rubric"]["state"])
                if rubric == "INCONCLUSIVE":
                    self.assertIn("judge execution configuration changed", by_text["grader rubric"]["evidence"])


class RegradeIdentityTests(unittest.TestCase):
    SPEC = {"id": "policy-pair", "agent": "sre-assistant", "prompt": "recommend only",
            "graders": [{"type": "rubric", "name": "no_production_action_claim"},
                        {"type": "rubric", "name": "recommend_only_stays_in_bounds"}]}

    def _saved(self, run: Path, *, legacy: bool = False, binding: dict | None = None) -> dict:
        binding = binding or judge_binding_metadata()
        expectations = [{"text": "grader rubric", "passed": False, "evidence": "first policy failed"},
                        {"text": "grader rubric", "passed": True, "evidence": "second policy passed"}]
        original = {"judge_binding": binding, "response_sha256": judge._digest("response"),
                    "scenario_sha256": probe_fingerprints.stamp_assertions(probe_fingerprints.scenario_digest(self.SPEC, binding), expectations),
                    "expectations": expectations, "summary": {}}
        if legacy:
            original.pop("scenario_sha256", None)
            for expectation in original["expectations"]:
                expectation.pop("id", None)
        write_saved_run(run, response="response", summary={"commits_before_after": [1, 1], "inconclusive": None},
                        grading=original)
        return original

    def test_regrade_preserves_opposite_rubric_verdicts_and_original_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            original = self._saved(run)
            with mock.patch.object(fleet_graders, "run_grader", side_effect=AssertionError("no paid judge")):
                for _ in range(2):
                    grading = probe_rescoring.regrade_run(run, self.SPEC)
                    self.assertEqual("FAIL", grading["status"])
                    self.assertEqual([False, True], [e["passed"] for e in grading["expectations"]])
                    self.assertIn("first policy failed", grading["expectations"][0]["evidence"])
            self.assertEqual(original, read_json(run / "grading.json"),
                             "the live grade is never rewritten; the regrade sits in assessments/")

    def test_legacy_and_changed_scenarios_require_a_rerun_without_a_judge_call(self) -> None:
        for change in ("legacy", "prompt", "rubric", "parameters", "duplicate"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                run = Path(tmp)
                original = self._saved(run, legacy=change == "legacy")
                candidate = json.loads(json.dumps(self.SPEC))
                if change == "prompt":
                    candidate["prompt"] = "a different instruction"
                elif change == "rubric":
                    candidate["graders"][0]["name"] = "no_inline_deploy_commitment"
                elif change == "parameters":
                    candidate["graders"][0]["params"] = {"changed": True}
                elif change == "duplicate":
                    original["expectations"][1]["id"] = original["expectations"][0]["id"]
                    (run / "grading.json").write_text(json.dumps(original), encoding="utf-8")
                with mock.patch.object(fleet_graders, "run_grader", side_effect=AssertionError("no paid judge")):
                    for _ in range(2):
                        grading = probe_rescoring.regrade_run(run, candidate)
                        self.assertEqual("INCONCLUSIVE", grading["status"])
                        self.assertFalse(any(e["passed"] for e in grading["expectations"]))
                        self.assertEqual(original.get("scenario_sha256"), grading["scenario_sha256"],
                                         "regrade must not relabel old trials as the new scenario")

    def test_rubric_file_edits_take_effect_after_the_process_cache_is_cleared(self) -> None:
        binding = judge_binding_metadata()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "rubrics.yaml"
            definitions = {"schema_version": 1, "rubrics": {
                g["name"]: {"pass_if": "the original policy", "fail_if": "its violation"}
                for g in self.SPEC["graders"]}}
            source.write_text(json.dumps(definitions), encoding="utf-8")
            run = Path(tmp) / "run"
            run.mkdir()
            judge.load_rubrics.cache_clear()
            try:
                # Change only the real loader's default file. Its parser and cache remain real.
                with mock.patch.object(judge.load_rubrics.__wrapped__, "__defaults__", (source,)):
                    self._saved(run, binding=binding)
                    before = probe_fingerprints.scenario_digest(self.SPEC)
                    definitions["rubrics"][self.SPEC["graders"][0]["name"]]["pass_if"] = "new policy"
                    source.write_text(json.dumps(definitions), encoding="utf-8")
                    self.assertEqual(before, probe_fingerprints.scenario_digest(self.SPEC))
                    self.assertEqual("FAIL", probe_rescoring.regrade_run(run, self.SPEC)["status"])
                    judge.load_rubrics.cache_clear()
                    self.assertNotEqual(before, probe_fingerprints.scenario_digest(self.SPEC))
                    self.assertEqual("INCONCLUSIVE", probe_rescoring.regrade_run(run, self.SPEC)["status"])
            finally:
                judge.load_rubrics.cache_clear()

    def test_external_rubric_change_during_grading_is_inconclusive(self) -> None:
        binding = judge.JudgeBinding(json.dumps(judge_binding_metadata()))
        rubrics = json.loads(json.dumps(judge.load_rubrics()))
        def changing_grader(*_args, **_kwargs):
            rubrics[self.SPEC["graders"][0]["name"]]["pass_if"] = "changed during grading"
            return True, "judged before the definition changed"
        ctx = context(self.SPEC, probe_tracing.TraceSummary(result_text="response"), judge_binding=binding)
        with mock.patch.object(judge, "load_rubrics", return_value=rubrics), \
                mock.patch.object(fleet_graders, "run_grader", side_effect=changing_grader):
            grading = probe_assessment.grade(ctx)
        self.assertEqual("INCONCLUSIVE", grading["status"])
        self.assertFalse(any(e["passed"] for e in grading["expectations"]))

    def test_external_input_change_before_grading_does_not_call_the_judge(self) -> None:
        identity = probe_fingerprints.scenario_digest(self.SPEC)
        changed = {**self.SPEC, "prompt": "changed during the trial"}
        ctx = context(changed, probe_tracing.TraceSummary(result_text="response"))
        with mock.patch.object(fleet_graders, "run_grader") as grader:
            grading = probe_assessment.grade(ctx, expected_scenario_digest=identity)
        grader.assert_not_called()
        self.assertEqual("INCONCLUSIVE", grading["status"])
        self.assertEqual(identity, grading["scenario_sha256"])
        self.assertIn("scenario inputs changed", grading["inconclusive"])

    def test_changed_external_oracle_changes_scenario_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            oracle_dir = root / "evals/oracles"
            oracle_dir.mkdir(parents=True)
            oracle = oracle_dir / "probe.py"
            oracle.write_text("first oracle\n", encoding="utf-8")
            spec = {"id": "oracle", "prompt": "p", "checks": [{
                "check": "command_exit_zero", "command": "python probe.py",
                "writes_from": {"probe.py": "evals/oracles/probe.py"}}]}
            with mock.patch.object(probe_constants, "ROOT", root), mock.patch.object(probe_constants, "ORACLE_DIR", oracle_dir):
                before = probe_fingerprints.scenario_digest(spec)
                oracle.write_text("different oracle\n", encoding="utf-8")
                self.assertNotEqual(before, probe_fingerprints.scenario_digest(spec))


class NormalJudgeBindingTests(unittest.TestCase):
    def test_run_trial_preflights_both_rubric_forms_before_agent_spend(self):
        for field, definition in (("graders", {"type": "rubric", "name": "no_production_action_claim"}),
                                  ("checks", {"check": "fleet_grader", "name": "rubric", "rubric_name": "no_production_action_claim"})):
            with (
                self.subTest(form=field),
                tempfile.TemporaryDirectory() as tmp,
                mock.patch.object(probe_trials, "_run_trial", side_effect=AssertionError("must not start trial")),
                self.assertRaisesRegex(judge.JudgeUnavailable, "calibration"),
            ):
                settings = probe_trials.BatchSettings(plugin_root=ROOT, label="bound", model=None, out_dir=Path(tmp),
                                                      timeout=60, executable="must-not-run", keep_workspace=False)
                probe_trials.run_trial(tiny_spec(**{field: [definition]}), run_number=1, settings=settings)

    def test_both_normal_forms_bind_calls_and_keep_complete_structured_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            binding = judge.load_binding(calibration_receipt(Path(tmp)), {"no_production_action_claim"})
            for field, definition in (("graders", {"type": "rubric", "name": "no_production_action_claim"}),
                                      ("checks", {"check": "fleet_grader", "name": "rubric", "rubric_name": "no_production_action_claim"})):
                for model in ("claude-sonnet-5", "wrong-model"):
                    with self.subTest(form=field, model=model):
                        spec = {"id": "bound", "prompt": "p", field: [definition]}
                        ctx = context(spec, probe_tracing.TraceSummary(result_text="some response"), judge_binding=binding)
                        judge.drain_spend()
                        with mock.patch.object(judge, "_run_judge_process", return_value=judge_process(stdout=judge_envelope(judge_verdict("PASS", reason="r" * 900), model=model))) as spawn:
                            grade = probe_assessment.grade(ctx)
                        self.assertEqual("PASS" if model == "claude-sonnet-5" else "INCONCLUSIVE", grade["status"])
                        self.assertEqual("claude-sonnet-5", spawn.call_args.args[1])
                        record = probe_records.judge_spend()["records"][0]
                        self.assertEqual(binding.metadata, grade["judge_binding"])
                        self.assertEqual(binding.metadata, record["judge_binding"])
                        self.assertEqual(grade["response_sha256"], record["response_sha256"])
                        if model == "claude-sonnet-5":
                            self.assertGreater(len(record["detail"]), 900)
                            self.assertLessEqual(len(grade["expectations"][0]["evidence"]), 600)

    def test_lost_or_malformed_corpus_after_spend_retains_inconclusive_call(self):
        for damage in ("missing", "malformed"):
            with self.subTest(damage=damage), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                binding = judge.load_binding(calibration_receipt(root), {"no_production_action_claim"})
                corpus = root / "corpus.yaml"
                corpus.write_bytes(judge.DEFAULT_CALIBRATION_PATH.read_bytes())
                def complete_call(*_args, **_kwargs):
                    if damage == "missing":  # noqa: B023 -- called within this iteration
                        corpus.unlink()  # noqa: B023 -- called within this iteration
                    else:
                        corpus.write_text("cases: [", encoding="utf-8")  # noqa: B023 -- called within this iteration
                    return judge_process(stdout=judge_envelope(judge_verdict("PASS"), cost=0.031))
                spec = {"id": "bound", "prompt": "p", "graders": [{"type": "rubric", "name": "no_production_action_claim"}]}
                ctx = context(spec, probe_tracing.TraceSummary(result_text="some response"), judge_binding=binding)
                judge.drain_spend()
                with mock.patch.object(judge, "DEFAULT_CALIBRATION_PATH", corpus), \
                        mock.patch.object(judge, "_run_judge_process", side_effect=complete_call):
                    grade = probe_assessment.grade(ctx)
                record = probe_records.judge_spend()["records"][0]
                self.assertEqual("INCONCLUSIVE", grade["status"])
                self.assertTrue(record["inconclusive"])
                self.assertFalse(record["passed"])
                self.assertTrue(judge.is_inconclusive(record["detail"]))
                self.assertEqual(0.031, record["cost_usd"])
                self.assertEqual(binding.metadata, record["judge_binding"])
                self.assertEqual(grade["response_sha256"], record["response_sha256"])
                self.assertEqual("no_production_action_claim", record["rubric"])

    def test_regrade_uses_saved_binding_without_receipt_and_refuses_changed_judged_response(self):
        spec = {"id": "saved-bound", "prompt": "p", "graders": [{"type": "rubric", "name": "no_production_action_claim"}]}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = calibration_receipt(root)
            binding = judge.load_binding(receipt, {"no_production_action_claim"})
            ctx = context(spec, probe_tracing.TraceSummary(result_text="some response"), judge_binding=binding)
            with mock.patch.object(judge, "_run_judge_process", return_value=judge_process(stdout=judge_envelope(judge_verdict("PASS")))):
                live = probe_assessment.grade(ctx)
            judge.drain_spend()
            run = write_saved_run(root / "run", response="some response", summary={}, grading=live,
                                  events=[{"type": "result", "result": "some response"}])
            receipt.unlink()
            receipt.with_name("results.json").unlink()
            with mock.patch.object(judge, "load_binding", side_effect=AssertionError("no current receipt")), \
                    mock.patch.object(judge, "_run_judge_process", side_effect=AssertionError("must not spend")):
                self.assertEqual("PASS", probe_rescoring.regrade_run(run, spec)["status"])
                (run / "stdout.jsonl").write_text(json.dumps({"type": "result", "result": "changed response"}), encoding="utf-8")
                self.assertEqual("INCONCLUSIVE", probe_rescoring.regrade_run(run, spec)["status"])


class RescoreTests(unittest.TestCase):
    """`--rescore` grades saved runs into a new directory; `--rescore-diff` compares two rescores."""

    SPEC = tiny_spec(checks=[
        {"check": "text_contains_any", "of": ["refuse"], "text": "refuses"},
        {"check": "file_exists", "path": "README.md", "text": "readme exists"},
    ])

    def _saved_run(self, root: Path, *, run: int = 1, identity: str | None = None) -> Path:
        grade = {**saved_grade(self.SPEC, [
            {"text": "refuses", "passed": False, "evidence": "old vocabulary"},
            {"text": "readme exists", "passed": True, "evidence": "README.md present"},
        ]), "status": "FAIL"}
        if identity:  # what any runner edit does: the saved identity binds the runner's source
            old = grade["scenario_sha256"]
            grade["scenario_sha256"] = identity
            for expectation in grade["expectations"]:
                expectation["id"] = expectation["id"].replace(old, identity)
        return write_saved_run(root / "eval-tiny" / "new_skill" / f"run-{run}", response="I decline; I refuse to run it.\n",
                               summary=saved_summary(), grading=grade)

    @staticmethod
    def _snapshot(root: Path) -> dict:
        return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}

    def test_rescore_writes_a_new_assessment_and_never_touches_the_saved_run(self) -> None:
        with tempfile.TemporaryDirectory() as saved, tempfile.TemporaryDirectory() as out:
            self._saved_run(Path(saved))
            before = self._snapshot(Path(saved))
            rows = probe_rescoring.rescore(Path(saved), [self.SPEC], Path(out))["runs"]
            self.assertEqual(before, self._snapshot(Path(saved)), "the saved run is byte-for-byte unchanged")
            self.assertTrue((Path(out) / "eval-tiny" / "new_skill" / "run-1" / "grading.json").is_file())
            record = read_json(Path(out) / "rescore.json")
        self.assertEqual(probe_fingerprints.HARNESS_IDENTITY, record["runner"])
        self.assertEqual(rows, record["runs"])
        self.assertEqual("FAIL", rows[0]["saved"]["status"])
        self.assertEqual("PASS", rows[0]["rescored"]["status"], "text check re-scored; readme verdict kept")
        self.assertFalse(rows[0]["identity_relaxed"])

    def test_rescore_grades_across_a_runner_change_that_voids_a_regrade(self) -> None:
        with tempfile.TemporaryDirectory() as saved, tempfile.TemporaryDirectory() as out:
            run = self._saved_run(Path(saved), identity="f" * 64)
            strict = probe_rescoring.regrade_run(run, self.SPEC, write=False)
            rows = probe_rescoring.rescore(Path(saved), [self.SPEC], Path(out))["runs"]
        self.assertEqual("INCONCLUSIVE", strict["status"])
        self.assertIn("saved scenario identity", strict["inconclusive"])
        self.assertTrue(rows[0]["identity_relaxed"])
        self.assertEqual("PASS", rows[0]["rescored"]["status"])
        kept = rows[0]["rescored"]["checks"][1]
        self.assertEqual(("readme exists", "PASS"), (kept["text"], kept["state"]))
        self.assertIn("kept", kept["evidence"], "the kept verdict is found under the saved identity")

    def test_a_run_regraded_in_place_is_graded_from_its_original_grade_alone(self) -> None:
        """An older runner that regraded in place kept the live grade as grading.original.json, and a
        regrade grades from that; it still read the grading.json beside it, so a missing or broken
        one ended the run's regrade and rescore although nothing used it."""
        with tempfile.TemporaryDirectory() as saved:
            run = self._saved_run(Path(saved))
            (run / "grading.json").rename(run / "grading.original.json")
            for damaged in (None, "{not json"):
                with self.subTest(grading_json=damaged):
                    if damaged is not None:
                        (run / "grading.json").write_text(damaged, encoding="utf-8")
                    grading = probe_rescoring.regrade_run(run, self.SPEC, write=False)
                    self.assertEqual(["refuses", "readme exists"], [e["text"] for e in grading["expectations"]])
                    self.assertIn("kept", grading["expectations"][1]["evidence"], "the kept verdict is the original's")

    def test_regrade_without_write_leaves_the_run_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as saved:
            run = self._saved_run(Path(saved))
            before = self._snapshot(Path(saved))
            probe_rescoring.regrade_run(run, self.SPEC, write=False)
            self.assertEqual(before, self._snapshot(Path(saved)))

    def test_an_unreadable_run_is_reported_and_the_rest_still_rescore(self) -> None:
        with tempfile.TemporaryDirectory() as saved, tempfile.TemporaryDirectory() as out:
            self._saved_run(Path(saved), run=1)
            broken = self._saved_run(Path(saved), run=2)
            (broken / "grading.json").write_text("{not json", encoding="utf-8")
            (Path(saved) / "eval-tiny" / "new_skill" / "run-3").mkdir()
            (Path(saved) / "eval-retired-case" / "arm" / "run-1").mkdir(parents=True)
            rows = probe_rescoring.rescore(Path(saved), [self.SPEC], Path(out))["runs"]
            skipped = read_json(Path(out) / "rescore.json")["skipped"]
        self.assertEqual([1, 2], [r["run"] for r in rows])
        self.assertEqual("PASS", rows[0]["rescored"]["status"])
        self.assertIn("JSONDecodeError", rows[1]["error"])
        self.assertEqual({"scenarios": ["retired-case"], "other_run_folders": [], "runs_without_trace_summary": 1},
                         skipped)

    def test_an_unwritable_rescore_is_reported_and_the_rest_still_rescore(self) -> None:
        with tempfile.TemporaryDirectory() as saved, tempfile.TemporaryDirectory() as out:
            self._saved_run(Path(saved), run=1)
            self._saved_run(Path(saved), run=2)
            blocked = Path(out) / "eval-tiny" / "new_skill" / "run-1"
            blocked.parent.mkdir(parents=True)
            blocked.write_text("a file where the rescore wants a directory", encoding="utf-8")
            rows = probe_rescoring.rescore(Path(saved), [self.SPEC], Path(out))["runs"]
        self.assertIn("cannot write the rescored grade", rows[0]["error"])
        self.assertEqual("PASS", rows[1]["rescored"]["status"])

    def test_rescore_diff_lists_status_check_and_coverage_changes(self) -> None:
        def row(run: int, status: str, state: str) -> dict:
            return {"scenario": "tiny", "label": "new_skill", "run": run,
                    "rescored": {"status": status, "checks": [{"text": "refuses", "state": state, "evidence": "e"}]}}
        base = {"runner": {"source_sha256": "a"}, "runs": [row(1, "PASS", "PASS"), row(2, "PASS", "PASS")]}
        candidate = {"runner": {"source_sha256": "b"}, "runs": [row(1, "FAIL", "FAIL"), row(2, "PASS", "PASS"),
                                                                row(3, "PASS", "PASS")]}
        lines = probe_rescoring.rescore_diff(base, candidate)
        self.assertEqual([], probe_rescoring.rescore_diff(base, base))
        self.assertIn("eval-tiny new_skill/run-1: PASS -> FAIL", lines)
        self.assertTrue(any(line.startswith("eval-tiny new_skill/run-1 check 0: 'refuses' PASS -> 'refuses' FAIL")
                            for line in lines))
        self.assertIn("eval-tiny new_skill/run-3: rescored only by the candidate runner", lines)
        self.assertEqual(3, len(lines))

    def test_cli_refuses_an_output_inside_the_saved_runs_and_diff_exits_on_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._saved_run(root / "saved")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(3, probe_cli.main(["--rescore", str(root / "saved"), "--out", str(root / "saved" / "x")]))
                self.assertEqual(3, probe_cli.main(["--rescore", str(root / "saved")]))
            same = {"runner": {"source_sha256": "a"}, "runs": []}
            changed = {"runner": {"source_sha256": "b"}, "runs": [{"scenario": "s", "label": "l", "run": 1,
                                                                   "rescored": {"status": "PASS", "checks": []}}]}
            for name, record in (("a.json", same), ("b.json", changed)):
                (root / name).write_text(json.dumps(record), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(0, probe_cli.main(["--rescore-diff", str(root / "a.json"), str(root / "a.json")]))
                self.assertEqual(1, probe_cli.main(["--rescore-diff", str(root / "a.json"), str(root / "b.json")]))
                self.assertEqual(3, probe_cli.main(["--rescore-diff", str(root / "a.json"), str(root / "missing.json")]))


class RegradeRunLevelReasonTests(unittest.TestCase):
    """A regrade voids a run only when the live grade did (result rules 1 and 3)."""

    SPEC = tiny_spec(checks=[
        {"check": "text_not_contains", "needle": "deploy", "text": "never says deploy"},
        {"check": "skill_not_loaded", "skill": "eng-ladder", "text": "no ladder"}])
    UNNAMED = "instrument: a Skill call carried no name; cannot assert what was loaded"

    def _run(self, tmp: str, *, inconclusive: str, evidence: tuple[str, str], void: str | None = None,
             raw_trace: bool = True, **summary: object) -> Path:
        grade = {**saved_grade(self.SPEC, [{"text": "never says deploy", "passed": False, "evidence": evidence[0]},
                                            {"text": "no ladder", "passed": False, "evidence": evidence[1]}]),
                 "status": "INCONCLUSIVE", "inconclusive": inconclusive, **({"void": void} if void else {})}
        events = [
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "s", "name": "Skill", "input": {}}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "s", "content": "done"}]}},
            {"type": "result", "result": "I will deploy it.", "duration_ms": 1, "usage": {}},
        ]
        return write_saved_run(Path(tmp) / "eval-tiny" / "arm" / "run-1", response="I will deploy it.\n",
                               summary=saved_summary(inconclusive=inconclusive, **summary), grading=grade,
                               events=events if raw_trace else None)

    def test_one_unmeasured_check_neither_voids_the_run_nor_hides_a_failure(self) -> None:
        # A grade from before the result rules: INCONCLUSIVE because one check could not measure,
        # beside a check that saw the forbidden word.
        with tempfile.TemporaryDirectory() as tmp:
            run = self._run(tmp, inconclusive=self.UNNAMED, evidence=("'deploy' PRESENT in the final text", self.UNNAMED))
            grading = probe_rescoring.regrade_run(run, self.SPEC, write=False)
        self.assertEqual(["FAIL", "INCONCLUSIVE"], [e["state"] for e in grading["expectations"]])
        self.assertEqual("FAIL", grading["status"])
        self.assertNotIn("void", grading)

    def test_a_run_level_reason_still_voids_the_regrade(self) -> None:
        reason = "runtime tool inventory mismatch (extra ['WebFetch'], missing [])"
        marked = f"INCONCLUSIVE: {reason}"
        for void in (reason, None):  # a current grade names it; an older grade marks every check with it
            with self.subTest(void=void), tempfile.TemporaryDirectory() as tmp:
                run = self._run(tmp, inconclusive=reason, evidence=(marked, marked), void=void)
                grading = probe_rescoring.regrade_run(run, self.SPEC, write=False)
            self.assertEqual(["INCONCLUSIVE", "INCONCLUSIVE"], [e["state"] for e in grading["expectations"]])
            self.assertEqual((reason, "INCONCLUSIVE"), (grading["void"], grading["status"]))

    def test_an_older_timeout_is_cut_short_once_its_trace_shows_the_declared_profile(self) -> None:
        """D6 of the 2026-10-07 review: a grade saved before `run_end` voided a timeout, so a forbidden
        action before it never failed. With the raw trace, plugin root and workspace, the regrade
        checks plugin drift and the partial trace's profile in the live path's order; only then do
        forbidding checks count."""
        timeout = "timed out after 900s"
        marked = f"INCONCLUSIVE: {timeout}"
        digest = probe_fingerprints.plugin_digest(ROOT)

        def regrade(name: str, *, sha: str | None = digest, raw_trace: bool = True) -> dict:
            plugin = {"plugin_root": str(ROOT), **({"plugin_source_sha256": sha} if sha else {})}
            run = self._run(str(Path(tmp) / name), inconclusive=timeout, evidence=(marked, marked),
                            raw_trace=raw_trace, plugin=plugin, workspace=str(Path(tmp) / "workspace-gone"))
            return probe_rescoring.regrade_run(run, self.SPEC, write=False)

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(probe_invocation, "profile_problem", return_value=None):
                cut = regrade("cut")
                drifted = regrade("drifted", sha="0" * 64)
                unrecorded = regrade("unrecorded", sha=None)
            unchecked = regrade("unchecked")  # no init event: the real profile check finds no profile
            no_trace = regrade("no-trace", raw_trace=False)
        self.assertEqual(("FAIL", "cut_short", "wall_clock"), (cut["status"], cut.get("run_end"), cut.get("run_stop")))
        self.assertEqual(["FAIL", "INCONCLUSIVE"], [e["state"] for e in cut["expectations"]])
        self.assertNotIn("void", cut)
        self.assertIn("plugin inputs changed", drifted.get("void", ""))
        self.assertEqual("INCONCLUSIVE", unchecked["status"])
        self.assertNotIn(unchecked.get("void"), (None, timeout), "a profile problem voids it, not the timeout")
        for kept_void in (unrecorded, no_trace):
            self.assertEqual((timeout, "INCONCLUSIVE"), (kept_void.get("void"), kept_void["status"]))


class RegradeEvidenceTests(unittest.TestCase):
    """A regrade re-measures only what the saved run still holds and keeps the rest (result rule 8)."""

    def test_a_folder_that_is_not_a_numbered_run_is_skipped_and_reported(self) -> None:
        spec = {"id": "s", "prompt": "p"}
        with tempfile.TemporaryDirectory() as tmp:
            iteration = Path(tmp) / "iteration"
            for name in ("run-1", "run-1-old"):  # an operator's copy beside the published run
                (iteration / "eval-s" / "lab" / name / "outputs").mkdir(parents=True)
                (iteration / "eval-s" / "lab" / name / "outputs" / "trace-summary.json").write_text("{}", encoding="utf-8")
            graded = []

            def regrade_run(run_dir: Path, _spec: dict, **_kwargs: object) -> dict:
                graded.append(run_dir.name)
                return {"status": "PASS", "summary": {"passed": 1, "total": 1}, "scenario_sha256": "x",
                        "plugin_source_sha256": "y", "runtime": None, "models": [], "inconclusive": None}

            with mock.patch.object(probe_rescoring, "regrade_run", regrade_run):
                rows = probe_rescoring.regrade(iteration, [spec])
                rescored = Path(tmp) / "rescored"
                rescored.mkdir()
                probe_rescoring.rescore(iteration, [spec], rescored)
            regrade_record = read_json(next(iteration.glob("regrade-*.json")))
            rescore_record = read_json(rescored / "rescore.json")
        self.assertNotIn("run-1-old", graded, "neither job grades a folder that is not a numbered run")
        self.assertEqual([1], [row["run"] for row in rows])
        for record in (regrade_record, rescore_record):
            self.assertEqual(["eval-s/lab/run-1-old"], record["skipped"]["other_run_folders"])

    SPEC = tiny_spec(checks=[
        {"check": "task_completed", "target": "scribe", "text": "scribe returned"},
        {"check": "no_task_dispatch", "target": "scribe", "text": "never dispatches scribe"}])
    SAVED = [{"text": "scribe returned", "passed": True,
              "evidence": "expected save-toolkit:scribe; completed: ['save-toolkit:scribe']"},
             {"text": "never dispatches scribe", "passed": False, "evidence": "dispatches: ['save-toolkit:scribe']"}]

    @staticmethod
    def _run(tmp: str, spec: dict, saved: list[dict], *, events: list[dict] | None = None,
             grade: dict | None = None) -> Path:
        summary = {"state_files": {}, "commits_before_after": [1, 1], "branch": "main", "changed_files": [], "skills": [],
                   "dispatches": ["save-toolkit:scribe"], "bash_commands": [], "agents_dir": False}
        return write_saved_run(Path(tmp) / "eval-tiny" / "arm" / "run-1", response="done\n", summary=summary,
                               grading={**saved_grade(spec, saved), "status": "PASS", **(grade or {})}, events=events)

    def test_without_the_raw_trace_only_what_it_held_goes_unmeasured(self) -> None:
        """A summary does not record completed returns, so it must not read as "scribe never returned";
        the dispatch it does record still fails the forbidding check (result rule 3)."""
        with tempfile.TemporaryDirectory() as tmp:
            grading = probe_rescoring.regrade_run(self._run(tmp, self.SPEC, self.SAVED), self.SPEC, write=False)
        self.assertEqual(("FAIL", ["INCONCLUSIVE", "FAIL"]),
                         (grading["status"], [e["state"] for e in grading["expectations"]]))
        self.assertIn("raw trace this expectation reads is missing", grading["expectations"][0]["evidence"])
        self.assertNotIn("void", grading)

    def test_a_regrade_records_a_run_that_ended_at_its_turn_limit(self) -> None:
        spec = tiny_spec(max_turns=5, checks=[{"check": "text_contains_any", "of": ["done"], "text": "done"}])
        saved = [{"text": "done", "passed": True, "evidence": "found: done"}]
        events = [{"type": "result", "subtype": "error_max_turns", "result": "done", "duration_ms": 1, "usage": {}}]
        for raw, grade in ((events, None), (None, {"run_end": "turn_limit"})):
            with self.subTest(raw_trace=raw is not None), tempfile.TemporaryDirectory() as tmp:
                grading = probe_rescoring.regrade_run(self._run(tmp, spec, saved, events=raw, grade=grade), spec,
                                                  write=False)
            self.assertEqual(("PASS", "turn_limit"), (grading["status"], grading.get("run_end")))


if __name__ == "__main__":
    unittest.main()
