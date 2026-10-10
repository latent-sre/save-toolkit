"""No-model tests for the grading loop (evals/probe/assessment.py): routing grades, reference reads,
result rules and grading-machinery failures.

Run directly: python evals/test_probe_assessment.py
"""
from __future__ import annotations

import contextlib
import copy
import io
import pickle
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import graders as fleet_graders
import judge
from probe import assessment as probe_assessment
from probe import batches as probe_batches
from probe import catalog as probe_catalog
from probe import checking as probe_checking
from probe import cli as probe_cli
from probe import constants as probe_constants
from probe import fingerprints as probe_fingerprints
from probe import outcomes as probe_outcomes
from probe import rescoring as probe_rescoring
from probe import tracing as probe_tracing
from probe import trials as probe_trials
from probe import workspaces as probe_workspaces
from probe_testkit import STUB_RUNTIME, all_scenarios, context, scenario_file, tiny_spec, trace_measures

ROOT = Path(__file__).resolve().parent.parent


def _trace(*, skills=(), agents=(), text="an answer", plugins=(("save-toolkit",),)) -> probe_tracing.TraceSummary:
    trace = probe_tracing.TraceSummary()
    trace.skills = list(skills)
    trace.agents = list(agents)
    trace.result_text = text
    trace.runtime_plugins = [{"name": name} for (name,) in plugins]
    return trace


class RoutingGradeTests(unittest.TestCase):
    """The one check a routing scenario makes: did the named component complete?"""

    plugin_root = ROOT

    def _fire(self, name: str, kind: str = "skill") -> dict:
        return {"id": "r", "prompt": "p", "target": {"kind": kind, "name": name},
                "routing": {"expect": "fire"}}

    def test_fire_credits_a_completed_namespaced_invocation(self) -> None:
        passed, detail = probe_assessment.grade_routing(
            self._fire("incident-investigation"),
            _trace(skills=["save-toolkit:incident-investigation"]),
            self.plugin_root,
        )
        self.assertTrue(passed, detail)
        self.assertIn("save-toolkit:incident-investigation", detail)

    def test_fire_is_not_satisfied_by_an_inline_answer(self) -> None:
        passed, detail = probe_assessment.grade_routing(
            self._fire("incident-investigation"), _trace(), self.plugin_root
        )
        self.assertFalse(passed)
        self.assertIn("saw []", detail)

    def test_fire_is_not_satisfied_by_a_failed_skill_call(self) -> None:
        """An attempt is not a load: skills_failed must not count."""
        trace = _trace()
        trace.skills_failed = ["save-toolkit:incident-investigation"]
        passed, _ = probe_assessment.grade_routing(self._fire("incident-investigation"), trace, self.plugin_root)
        self.assertFalse(passed)

    def test_fire_on_an_agent_target_reads_completed_dispatches(self) -> None:
        passed, _ = probe_assessment.grade_routing(
            self._fire("reviewer", kind="agent"),
            _trace(agents=["save-toolkit:reviewer"]),
            self.plugin_root,
        )
        self.assertTrue(passed)
        failed = _trace()
        failed.agents_failed = ["save-toolkit:reviewer"]
        passed, _ = probe_assessment.grade_routing(self._fire("reviewer", kind="agent"), failed, self.plugin_root)
        self.assertFalse(passed)

    def test_namespace_comes_from_the_loaded_plugin_not_a_literal(self) -> None:
        spec = self._fire("incident-investigation")
        trace = _trace(skills=["renamed:incident-investigation"], plugins=(("renamed",),))
        passed, _ = probe_assessment.grade_routing(spec, trace, self.plugin_root)
        self.assertTrue(passed)

    def test_not_fire_inline_requires_no_component_and_an_answer(self) -> None:
        spec = {"id": "r", "prompt": "p", "target": {"kind": "skill", "name": "pcf-deploy"},
                "routing": {"expect": "not_fire", "expected_alternative": "inline"}}
        passed, _ = probe_assessment.grade_routing(spec, _trace(), self.plugin_root)
        self.assertTrue(passed)
        fired, detail = probe_assessment.grade_routing(
            spec, _trace(skills=["save-toolkit:pcf-deploy"]), self.plugin_root
        )
        self.assertFalse(fired)
        self.assertIn("unexpectedly fired", detail)
        silent, _ = probe_assessment.grade_routing(spec, _trace(text="  "), self.plugin_root)
        self.assertFalse(silent, "an empty response is not a passing inline answer")

    def test_not_fire_with_a_named_alternative_requires_that_alternative(self) -> None:
        spec = {"id": "r", "prompt": "p", "target": {"kind": "skill", "name": "obs-logs"},
                "routing": {"expect": "not_fire",
                            "expected_alternative": {"kind": "skill", "name": "obs-alerting"}}}
        passed, _ = probe_assessment.grade_routing(
            spec, _trace(skills=["save-toolkit:obs-alerting"]), self.plugin_root
        )
        self.assertTrue(passed)
        # Absence of the forbidden target alone is not a pass.
        missing, detail = probe_assessment.grade_routing(spec, _trace(), self.plugin_root)
        self.assertFalse(missing)
        self.assertIn("expected alternative", detail)

    def test_not_fire_main_session_keeps_the_work_with_skills_but_no_agent(self) -> None:
        """The main session doing the work itself may load craft skills; `inline` forbids them."""
        spec = {"id": "r", "prompt": "p", "target": {"kind": "agent", "name": "reliability-engineer"},
                "routing": {"expect": "not_fire", "expected_alternative": "main_session"}}
        kept, detail = probe_assessment.grade_routing(spec, _trace(skills=["save-toolkit:python-craft"]), self.plugin_root)
        self.assertTrue(kept, detail)
        handed, _ = probe_assessment.grade_routing(spec, _trace(agents=["save-toolkit:principal-engineer"]), self.plugin_root)
        self.assertFalse(handed, "a hand-off to another agent is not the main session keeping the work")
        silent, _ = probe_assessment.grade_routing(spec, _trace(text="  "), self.plugin_root)
        self.assertFalse(silent, "an empty response keeps nothing")
        fired = probe_assessment.grade_routing(spec, _trace(agents=["save-toolkit:reliability-engineer"]), self.plugin_root)
        self.assertEqual(("FAIL", True), (fired.state, fired.forbidden))

    def test_not_fire_with_a_list_accepts_any_listed_alternative(self) -> None:
        spec = {"id": "r", "prompt": "p", "target": {"kind": "agent", "name": "reliability-engineer"},
                "routing": {"expect": "not_fire", "expected_alternative": [
                    "main_session", {"kind": "agent", "name": "software-engineer"}]}}
        for trace in (_trace(), _trace(agents=["save-toolkit:software-engineer"])):
            with self.subTest(agents=trace.agents):
                passed, detail = probe_assessment.grade_routing(spec, trace, self.plugin_root)
                self.assertTrue(passed, detail)
        other, detail = probe_assessment.grade_routing(spec, _trace(agents=["save-toolkit:principal-engineer"]), self.plugin_root)
        self.assertFalse(other)
        self.assertIn("software-engineer", detail)
        fired = probe_assessment.grade_routing(spec, _trace(agents=["save-toolkit:reliability-engineer"]), self.plugin_root)
        self.assertEqual(("FAIL", True), (fired.state, fired.forbidden))

    def test_a_listed_alternative_is_validated_item_by_item(self) -> None:
        base = {"id": "r", "split": "regression", "prompt": "p", "success_criteria": ["x"],
                "target": {"kind": "agent", "name": "reliability-engineer"}}
        valid = ["main_session", ["main_session", {"kind": "agent", "name": "software-engineer"}], ["inline"]]
        invalid = [[], ["sometimes"], [["main_session"]], [{"kind": "agent"}], "sometimes"]
        for alternative in valid + invalid:
            with self.subTest(alternative=alternative):
                spec = {**base, "routing": {"expect": "not_fire", "expected_alternative": alternative}}
                problems = [p for p in probe_catalog.validate_scenario(spec) if "expected_alternative" in p]
                self.assertEqual(alternative in valid, not problems, problems)

    def test_a_negative_routing_cut_fails_only_on_the_forbidden_target(self) -> None:
        negative = {"id": "n", "target": {"kind": "skill", "name": "pcf-deploy"},
                    "routing": {"expect": "not_fire", "expected_alternative": "inline"}}
        fired = probe_assessment.grade_routing(negative, _trace(skills=["save-toolkit:pcf-deploy"]), ROOT)
        missing_alternative = probe_assessment.grade_routing(negative, _trace(skills=["save-toolkit:runbook"]), ROOT)
        self.assertEqual(("FAIL", True), (fired.state, fired.forbidden))
        self.assertEqual(("FAIL", False), (missing_alternative.state, missing_alternative.forbidden))
        self.assertEqual("FAIL", probe_assessment.routing_on_cut(fired, "timed out").state)
        self.assertEqual("INCONCLUSIVE", probe_assessment.routing_on_cut(missing_alternative, "timed out").state)
        self.assertEqual(["both"], probe_catalog.assertion_polarities(negative))


class ReferenceReadTests(unittest.TestCase):
    """Codex review of PR #222: a scenario whose skill contract requires a reference read proves it."""

    SPEC = {
        "id": "ref-contract", "prompt": "p", "skill": "agent-authoring", "max_turns": 20,
        "tools": ["Skill", "Task", "Read"],
        "references": ["skills/agent-authoring/references/agent-security.md"],
        "graders": [{"type": "contains_any", "of": ["x"]}],
    }

    def _trace(self, attempts: list[dict]) -> probe_tracing.TraceSummary:
        return probe_tracing.TraceSummary(read_attempts=attempts)

    def test_a_successful_read_of_the_named_reference_passes(self) -> None:
        passed, detail = probe_assessment.reference_read(self._trace([
            {"tool": "Read", "path": str(ROOT / "skills/agent-authoring/references/agent-security.md"),
             "outcome": "allowed"}]), self.SPEC["references"][0], ROOT)
        self.assertTrue(passed, detail)

    def test_no_read_and_a_denied_read_both_fail(self) -> None:
        never, detail = probe_assessment.reference_read(self._trace([]), self.SPEC["references"][0], ROOT)
        self.assertFalse(never)
        self.assertIn("never read", detail)
        denied, detail = probe_assessment.reference_read(self._trace([
            {"tool": "Read", "path": str(ROOT / self.SPEC["references"][0]),
             "outcome": "denied"}]), self.SPEC["references"][0], ROOT)
        self.assertFalse(denied, detail)

    def test_contract_and_build_grade_only_the_measured_canonical_reference(self) -> None:
        reference = self.SPEC["references"][0]
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            plugin_root = workspace / "candidate"
            ws = probe_workspaces.Workspace(Path(tmp), workspace, Path(tmp) / "bin", Path(tmp) / "state", 0, "main")
            for spec in (self.SPEC, tiny_spec(references=[reference])):
                for path, outcome, expected in (
                    (str(plugin_root / reference), "allowed", True),
                    (f"candidate/{reference}", "allowed", True),
                    (f"candidate/{reference}".replace("/", "\\"), "allowed", True),
                    (str(plugin_root / ".github" / reference), "allowed", False),
                    (str(workspace / reference), "allowed", False),
                    (reference, "allowed", False),
                    (str(ROOT / reference), "allowed", False),
                    (str(plugin_root / reference), "denied", False),
                    (None, None, False),
                ):
                    with self.subTest(kind=probe_catalog.scenario_kind(spec), path=path, outcome=outcome):
                        reads = [] if path is None else [{"tool": "Read", "path": path, "outcome": outcome}]
                        ctx = probe_checking.Context(spec, ws, self._trace(reads),
                                                  probe_workspaces.GitFacts(0, "main", [], ""), plugin_root=plugin_root)
                        verdict = next(e for e in probe_assessment.grade(ctx)["expectations"]
                                       if e["text"] == f"reference {reference} read")
                        self.assertEqual(expected, verdict["passed"], verdict["evidence"])

    def test_relative_reference_without_a_known_workspace_fails_closed(self) -> None:
        reference = self.SPEC["references"][0]
        trace = self._trace([{"tool": "Read", "path": reference, "outcome": "allowed"}])
        verdicts = dict(trace_measures(self.SPEC, trace))
        self.assertEqual("FAIL", verdicts[f"reference {reference} read"]().state)

    def test_references_are_graded_as_their_own_expectation(self) -> None:
        ws = probe_workspaces.Workspace(Path("."), Path("."), Path("."), Path("."), 0, "main")
        ctx = probe_checking.Context(self.SPEC, ws, self._trace([]), probe_workspaces.GitFacts(0, "main", [], ""))
        texts = [e["text"] for e in probe_assessment.grade(ctx)["expectations"]]
        self.assertIn(f"reference {self.SPEC['references'][0]} read", texts)
        self.assertIn(f"reference {self.SPEC['references'][0]} read", probe_assessment.scenario_assertions(self.SPEC))

    def test_references_need_the_read_tool_and_a_relative_path(self) -> None:
        self.assertEqual([], probe_catalog.validate_scenario(self.SPEC))
        without_read = {**self.SPEC, "tools": ["Skill", "Task"]}
        self.assertTrue(any("Read" in p for p in probe_catalog.validate_scenario(without_read)))
        escaping = {**self.SPEC, "references": ["../secrets.md"]}
        self.assertTrue(any("repo-relative" in p for p in probe_catalog.validate_scenario(escaping)))

    def test_build_references_validate_and_require_successful_reads(self) -> None:
        spec = tiny_spec(tools=["Read"], references=self.SPEC["references"])
        self.assertEqual([], probe_catalog.validate_scenario(spec))
        reference = spec["references"][0]
        for outcome, expected in ((None, False), ("denied", False), ("allowed", True)):
            with self.subTest(outcome=outcome):
                attempts = [] if outcome is None else [{"tool": "Read", "path": str(ROOT / reference), "outcome": outcome}]
                verdicts = dict(trace_measures(spec, self._trace(attempts)))
                self.assertEqual(expected, verdicts[f"reference {reference} read"]()[0])

    def test_reference_prompt_uses_supplied_plugin_root(self) -> None:
        alternate = ROOT / "different-plugin-snapshot"
        prompt = probe_catalog.scenario_prompt(self.SPEC, alternate)
        reference = self.SPEC["references"][0]
        self.assertIn((alternate / reference).resolve().as_posix(), prompt)
        self.assertNotIn((ROOT / reference).resolve().as_posix(), prompt)
        self.assertEqual("plain task", probe_catalog.scenario_prompt({"prompt": "plain task"}))

    def test_the_committed_security_review_scenario_requires_its_reference(self) -> None:
        spec = scenario_file(
            probe_constants.CONTRACT_SCENARIO_DIR / "skill-direct-agent-authoring-security-review.yaml")
        self.assertIn("skills/agent-authoring/references/agent-security.md", spec["references"])
        self.assertIn("Read", spec["tools"])

    def test_incident_contracts_require_successful_reference_reads(self) -> None:
        for name, reference in (
            ("explains-pool-wait", "symptom-investigation.md"),
            ("adapts-to-missing-access", "symptom-investigation.md"),
            ("hands-over-unresolved-work", "mitigation-selection.md"),
        ):
            with self.subTest(scenario=name):
                spec = scenario_file(probe_constants.CONTRACT_SCENARIO_DIR /
                    f"incident-companion-{name}.yaml")
                self.assertEqual({"Skill", "Read"}, set(probe_catalog.scenario_tools(spec)))
                path = f"skills/incident-investigation/references/{reference}"
                self.assertIn(path, spec.get("references", []))
                for outcome in (None, "denied", "allowed"):
                    reads = [] if outcome is None else [
                        {"tool": "Read", "path": str(ROOT / path), "outcome": outcome}]
                    checks = dict(trace_measures(spec, self._trace(reads)))
                    self.assertEqual(outcome == "allowed", checks[f"reference {path} read"]()[0])


class ResultRuleTests(unittest.TestCase):
    """The accepted threat-model ADR's result rules: a supported failure is never hidden."""

    @staticmethod
    def _e(text: str, passed: bool, evidence: str = "e") -> dict:
        return {"text": text, "passed": passed, "evidence": evidence}

    @staticmethod
    def _read(checks: list[dict]) -> list:
        """A saved grade's checks as a regrade reads them, from their recorded text."""
        return [probe_outcomes.Outcome.read(c["passed"], c["evidence"]) for c in checks]

    def test_a_supported_failure_beside_an_unmeasured_check_fails(self) -> None:
        checks = [self._e("forbidden write absent", False, "wrote deploy.yaml"),
                  self._e("suite green", False, "INCONCLUSIVE: backing service unavailable: db")]
        read = self._read(checks)
        self.assertEqual(("FAIL", "backing service unavailable: db"), probe_assessment.roll_up(read, None))
        self.assertEqual(["FAIL", "INCONCLUSIVE"], [outcome.state for outcome in read])

    def test_unmeasured_without_a_failure_is_inconclusive_and_all_pass_is_pass(self) -> None:
        self.assertEqual("INCONCLUSIVE", probe_assessment.roll_up(
            self._read([self._e("a", True), self._e("b", False, "INCONCLUSIVE: judge down")]), None)[0])
        self.assertEqual(("PASS", None), probe_assessment.roll_up(self._read([self._e("a", True)]), None))
        self.assertEqual(("INCONCLUSIVE", "timed out"), probe_assessment.roll_up([], "timed out"))

    def test_a_run_level_measurement_failure_voids_every_check(self) -> None:
        """Rule 1: identity and run-level failures mark every check INCONCLUSIVE, FAILs included."""
        spec = tiny_spec(checks=[{"check": "text_contains_any", "of": ["absent"], "text": "says absent"}])
        ctx = context(spec, probe_tracing.TraceSummary(result_text="text"))
        grading = probe_assessment.grade(ctx, inconclusive="plugin source changed during the trial")
        self.assertEqual("INCONCLUSIVE", grading["status"])
        self.assertEqual({"INCONCLUSIVE"}, {e["state"] for e in grading["expectations"]})
        self.assertNotIn("unmeasured", grading)

    def test_a_cleanup_failure_after_assessment_keeps_the_verdict_and_stops_the_batch(self) -> None:
        summary = {"scenario": "s", "label": "l", "run": 1, "status": "PASS", "passed": 1, "total": 1,
                   "models": ["claude-sonnet-5-5"], "after_assessment": "backing service cleanup failed: db"}
        calls = []

        def fake_run_trial(spec, **kwargs):
            calls.append(kwargs["run_number"])
            return {**summary, "scenario": spec["id"], "run": kwargs["run_number"]}

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(probe_trials, "run_trial", side_effect=fake_run_trial), \
                mock.patch.object(probe_batches, "batch_identity_problem", return_value=None), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            code = probe_cli.main(["--scenario", "build-operator-cli-safe-requeue", "--label", "l",
                                     "--trials", "3", "--out", str(Path(tmp) / "it"), "--executable", sys.executable])
        self.assertEqual([1], calls, "no trial reuses an environment whose cleanup failed")
        self.assertEqual(2, code)
        self.assertIn('"trials_not_run": 2', out.getvalue())

    def test_an_instrument_failure_is_unmeasured_not_a_candidate_failure(self) -> None:
        state = probe_outcomes.legacy_state({"passed": False, "evidence": "instrument: a Skill call carried no name"})
        self.assertEqual("INCONCLUSIVE", state)


class GradingMachineryTests(unittest.TestCase):
    """Threat-model ADR rule 5: grading-machinery failures are INCONCLUSIVE and stop their scenario."""

    def test_a_grader_crash_is_inconclusive_and_named(self) -> None:
        spec = tiny_spec(checks=[{"check": "text_contains_any", "of": ["ok"], "text": "says ok"},
                                 {"check": "fleet_grader", "name": "no-such-grader", "text": "broken"}])
        ctx = context(spec, probe_tracing.TraceSummary(result_text="ok"))
        grading = probe_assessment.grade(ctx)
        self.assertEqual(["PASS", "INCONCLUSIVE"], [e["state"] for e in grading["expectations"]])
        self.assertEqual("INCONCLUSIVE", grading["status"])
        self.assertIn("unknown fleet grader", grading["grader_error"])

    def test_a_grader_crash_beside_a_supported_failure_still_fails(self) -> None:
        spec = tiny_spec(checks=[{"check": "text_contains_any", "of": ["absent"], "text": "says absent"},
                                 {"check": "fleet_grader", "name": "no-such-grader", "text": "broken"}])
        ctx = context(spec, probe_tracing.TraceSummary(result_text="ok"))
        self.assertEqual("FAIL", probe_assessment.grade(ctx)["status"])

    def test_validation_rejects_an_unknown_fleet_grader(self) -> None:
        spec = tiny_spec(checks=[{"check": "fleet_grader", "name": "no-such-grader", "text": "x"}])
        self.assertTrue(any("unknown grader" in p for p in probe_catalog.validate_scenario(spec)))

    def test_a_grader_error_stops_only_its_scenarios_remaining_trials(self) -> None:
        specs = [s for s in all_scenarios() if not probe_fingerprints.required_rubrics(s)
                 and not (s.get("fixture") or {}).get("services") and not s.get("followups")][:2]
        calls: list[tuple[str, int]] = []

        def fake_run_trial(spec_arg, **kwargs):
            calls.append((spec_arg["id"], kwargs["run_number"]))
            return {"scenario": spec_arg["id"], "label": "l", "run": kwargs["run_number"], "status": "INCONCLUSIVE",
                    "passed": 0, "total": 1, "models": ["m"], "runtime": STUB_RUNTIME,
                    "plugin_source_sha256": "0" * 64, "scenario_sha256": probe_fingerprints.scenario_digest(spec_arg),
                    **({"grader_error": "boom"} if spec_arg["id"] == specs[0]["id"] else {})}

        with tempfile.TemporaryDirectory() as tmp,                 mock.patch.object(probe_catalog, "load_all_scenarios", return_value=specs),                 mock.patch.object(probe_fingerprints, "plugin_provenance", return_value={"plugin_source_sha256": "0" * 64}),                 mock.patch.object(probe_fingerprints, "runtime_identity", return_value=STUB_RUNTIME),                 mock.patch.object(probe_trials, "run_trial", side_effect=fake_run_trial),                 contextlib.redirect_stdout(io.StringIO()) as out:
            code = probe_cli.main(["--label", "l", "--trials", "3", "--out", str(Path(tmp) / "it")])
        self.assertEqual([(specs[0]["id"], 1), (specs[1]["id"], 1), (specs[1]["id"], 2), (specs[1]["id"], 3)], calls)
        self.assertEqual(2, code)
        self.assertIn('"trials_not_run": 2', out.getvalue())

    def test_an_instrument_failure_stops_its_scenario(self) -> None:
        spec = tiny_spec(checks=[{"check": "skill_not_loaded", "skill": "eng-ladder", "text": "no ladder"}])
        ctx = context(spec, probe_tracing.TraceSummary(skills=["<unnamed-skill>"]))
        grading = probe_assessment.grade(ctx)
        self.assertEqual("INCONCLUSIVE", grading["expectations"][0]["state"])
        self.assertIn("Skill call carried no name", grading["grader_error"])

    def test_a_judge_that_could_not_judge_stops_its_scenario(self) -> None:
        evidence = judge.INCONCLUSIVE_PREFIX + "judge timed out after 120s"
        self.assertTrue(probe_outcomes.Outcome.read(False, evidence).machinery)
        spec = tiny_spec(checks=[{"check": "fleet_grader", "name": "regex", "pattern": "x", "text": "judged"}])
        ctx = context(spec, probe_tracing.TraceSummary(result_text="response"))
        with mock.patch.object(fleet_graders, "run_grader", return_value=(False, evidence)):
            grading = probe_assessment.grade(ctx)
        self.assertEqual(("INCONCLUSIVE", "INCONCLUSIVE"), (grading["status"], grading["expectations"][0]["state"]))
        self.assertIn("judge timed out", grading["grader_error"])


class GradingLoopTests(unittest.TestCase):
    """The one grading loop: what it measures, what it keeps, and what it refuses."""

    @staticmethod
    def _item(measure, polarity: str = "requires", **kwargs: object) -> probe_assessment.Expectation:
        return probe_assessment.Expectation("expectation", measure, probe_outcomes.Polarity(polarity), **kwargs)

    def test_a_regrade_plan_is_never_assessed_without_its_saved_verdicts(self) -> None:
        measured = []
        item = self._item(lambda: measured.append(1) or probe_outcomes.verdict(True, "judged"), kept_as="live-judge")
        with self.assertRaisesRegex(ValueError, "assess it with `kept`"):
            probe_assessment.assess([item], None)
        self.assertEqual([], measured, "a kept expectation is never measured live")

    def test_the_trial_reason_keeps_what_the_record_cuts(self) -> None:
        long = "exit 3: " + "x" * 700
        graded, reason = probe_assessment.assess([self._item(lambda: probe_outcomes.unmeasured(long), names_unmeasured=True)],
                                            None)
        self.assertEqual(long, reason)
        self.assertEqual((600, True), (len(graded[0].outcome.evidence), graded[0].truncated))

    def test_evidence_cut_on_a_run_cut_short_is_flagged(self) -> None:
        # The record keeps 600 characters and flags a cut; a rule that cut first left no flag.
        cut = probe_outcomes.CutShort("claude reported an error result " + "x" * 700, "error_result")
        trace = probe_tracing.TraceSummary(tool_counts={"Read": 1})
        spec = tiny_spec(checks=[{"check": "tool_call_count", "tool": "Read", "minimum": 2, "maximum": 3}])
        cases = {
            "forbidding check": [self._item(lambda: probe_outcomes.verdict(True, "no violation"), "forbids")],
            "negative routing": [self._item(lambda: probe_outcomes.verdict(True, "alternative never fired"), "both",
                                            on_cut=probe_assessment.routing_on_cut)],
            "tool-call floor": probe_assessment.plan(spec, trace, context(spec, trace), ROOT),
        }
        for name, items in cases.items():
            with self.subTest(case=name):
                graded, _ = probe_assessment.assess(items, cut)
                self.assertEqual(("INCONCLUSIVE", 600, True),
                                 (graded[0].outcome.state, len(graded[0].outcome.evidence), graded[0].truncated))

    def test_a_kept_verdict_keeps_its_marker_and_its_truncation_flag(self) -> None:
        item = self._item(lambda: probe_outcomes.verdict(True, "never measured"), kept_as="live-judge")
        for evidence, passed, state, truncated in (("J" * 600, False, "FAIL", True),
                                                   ("judged", True, "PASS", False),
                                                   ("INCONCLUSIVE: " + "u" * 586, False, "INCONCLUSIVE", True)):
            with self.subTest(state=state):
                saved = {"sha:0": {"id": "sha:0", "text": "expectation", "passed": passed, "evidence": evidence}}
                graded, _ = probe_assessment.assess([item], None, kept=probe_rescoring._saved_verdicts(saved, "sha"))
                record = probe_assessment.records(graded)[0]
                self.assertTrue(record["evidence"].startswith("[kept: live-judge] "), record["evidence"])
                self.assertEqual((state, truncated), (record["state"], bool(record.get("evidence_truncated"))))
                self.assertEqual(state, probe_outcomes.legacy_state(record), "the kept text reads back as its state")

    def test_a_crash_on_a_run_cut_short_stays_a_grader_error(self) -> None:
        def crash() -> probe_outcomes.Outcome:
            raise KeyError("target")

        item = self._item(crash, "both", on_cut=probe_assessment.routing_on_cut)
        graded, _ = probe_assessment.assess([item], probe_outcomes.CutShort("timed out after 60s", "wall_clock"))
        outcome = graded[0].outcome
        self.assertEqual(("INCONCLUSIVE", True), (outcome.state, outcome.machinery))
        self.assertTrue(outcome.evidence.startswith("INCONCLUSIVE: grader error: KeyError"))
        self.assertIn("grader error", probe_assessment.machinery_failure(graded)["grader_error"])

    def test_every_failure_of_a_forbidding_expectation_is_marked_a_violation(self) -> None:
        graded, _ = probe_assessment.assess([self._item(lambda: probe_outcomes.verdict(False, "deployed"), "forbids"),
                                        self._item(lambda: probe_outcomes.verdict(False, "no test"))], None)
        self.assertEqual([True, False], [g.outcome.forbidden for g in graded])
        trace = probe_tracing.TraceSummary()
        trace.tool_counts = {"WebFetch": 3}
        ctx = context({}, trace)
        over = probe_checking.check_tool_call_count(ctx, {"tool": "WebFetch", "minimum": 1, "maximum": 2})
        under = probe_checking.check_tool_call_count(ctx, {"tool": "WebFetch", "minimum": 4, "maximum": 9})
        self.assertEqual([("FAIL", True), ("FAIL", False)], [(o.state, o.forbidden) for o in (over, under)])

    def test_an_outcome_copies_pickles_and_compares_with_its_state(self) -> None:
        outcome = probe_outcomes.Outcome(probe_outcomes.State.INCONCLUSIVE, "x", machinery=True, forbidden=True)
        for copied in (pickle.loads(pickle.dumps(outcome)), copy.copy(outcome), copy.deepcopy(outcome)):
            self.assertEqual((outcome, outcome.state, outcome.machinery, outcome.forbidden),
                             (copied, copied.state, copied.machinery, copied.forbidden))
        fail = probe_outcomes.Outcome(probe_outcomes.State.FAIL, "x")
        self.assertNotEqual(probe_outcomes.Outcome(probe_outcomes.State.INCONCLUSIVE, "x"), fail)
        self.assertNotEqual(probe_outcomes.violation("x"), fail)
        self.assertNotEqual((False, "x"), fail)  # a pair has no measurement state
        self.assertEqual((False, "x"), tuple(fail))  # the explicit pair-reading adapter remains
        self.assertEqual(hash(probe_outcomes.Outcome(probe_outcomes.State.FAIL, "x")), hash(fail))


if __name__ == "__main__":
    unittest.main()
