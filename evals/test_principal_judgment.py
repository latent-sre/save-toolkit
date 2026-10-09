"""Offline contract checks for PRINCIPAL-001's semantic comparison; never call a model."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import graders
import judge
from probe import catalog
from probe_testkit import all_scenarios, scenario_file

ROOT = Path(__file__).resolve().parent
PROPOSAL = ROOT / "proposals" / "principal-judgment"
RUBRIC = "principal_design_judgment"
PAIRS = {
    "maintenance_window_contract": "contract-judgment",
    "certificate_tracker": "new-system-judgment",
}


def proposed_scenario(agent, suffix):
    rubrics = judge.load_rubrics(PROPOSAL / "rubrics.yaml")
    with mock.patch.object(judge, "load_rubrics", return_value=rubrics):
        return catalog.load_scenario(PROPOSAL / "build-scenarios" / f"build-{agent}-{suffix}.yaml")


def context_from_prompt(prompt):
    return json.loads(prompt.split("<case-material-json>\n", 1)[1]
                      .split("\n</case-material-json>", 1)[0])


class PrincipalJudgmentTests(unittest.TestCase):
    def test_unapproved_proposal_is_not_in_the_active_catalog(self):
        self.assertNotIn(RUBRIC, judge.load_rubrics())
        self.assertFalse(any(case["rubric"] == RUBRIC
                             for case in judge._load_calibration(judge.DEFAULT_CALIBRATION_PATH)))
        active_ids = {spec["id"] for spec in all_scenarios()}
        for agent in ("principal-engineer", "software-engineer"):
            for suffix in PAIRS.values():
                self.assertNotIn(f"build-{agent}-{suffix}", active_ids)

    def test_judged_context_contains_complete_prompt_and_every_fixture_file(self):
        rubrics = judge.load_rubrics(PROPOSAL / "rubrics.yaml")
        for case, suffix in PAIRS.items():
            with self.subTest(case=case):
                spec = proposed_scenario("principal-engineer", suffix)
                _, fail_if, _ = judge.prepare(RUBRIC, {"case": case}, "a design", "sonnet", rubrics)
                self.assertIn("<case-material-json>", fail_if)
                material = context_from_prompt(fail_if)
                self.assertEqual({"prompt": spec["prompt"], "files": spec["fixture"]["files"]}, material[case])

    def test_alerting_requirement_is_a_design_readiness_condition(self):
        body = (ROOT.parent / "agents/principal-engineer.md").read_text(encoding="utf-8")
        self.assertIn("Before designing a service that requires", body)
        prerequisite = body.split("Before designing a service that requires", 1)[1].split("\n2.", 1)[0]
        self.assertIn("paging, alert rules, or dashboards", prerequisite)
        self.assertIn("load `obs-alerting` or `obs-dashboards`", prerequisite)
        self.assertIn("not ready to return", prerequisite)

    def test_both_arms_receive_identical_tasks_fixtures_and_checks(self):
        originals = {
            "maintenance_window_contract": "build-principal-engineer-contract-change",
            "certificate_tracker": "build-principal-engineer-new-system",
        }
        for case, suffix in PAIRS.items():
            with self.subTest(case=case):
                principal = proposed_scenario("principal-engineer", suffix)
                builder = proposed_scenario("software-engineer", suffix)
                original = scenario_file(ROOT / f"build-scenarios/{originals[case]}.yaml")
                self.assertEqual("principal-engineer", principal["agent"])
                self.assertEqual("software-engineer", builder["agent"])
                for field in ("prompt", "fixture", "checks", "success_criteria"):
                    self.assertEqual(principal[field], builder[field], field)
                self.assertEqual(original["fixture"], principal["fixture"])
                self.assertIn("Return the complete design record in your final response", principal["prompt"])
                self.assertNotIn("one JSON object", principal["prompt"])
                semantic = [c for c in principal["checks"] if c["check"] == "fleet_grader"]
                self.assertEqual(1, len(semantic))
                self.assertEqual(RUBRIC, semantic[0]["rubric_name"])
                self.assertEqual({"case": case}, semantic[0]["params"])
                self.assertTrue(any(c["check"] == "no_workspace_changes" for c in principal["checks"]))

    def test_existing_written_record_cases_keep_the_alert_load_check(self):
        for agent, suffix in (("principal-engineer", "new-system"),
                              ("software-engineer", "new-system-baseline")):
            with self.subTest(agent=agent):
                spec = scenario_file(ROOT / f"build-scenarios/build-{agent}-{suffix}.yaml")
                self.assertIn({"check": "skill_loaded", "skill": "obs-alerting", "before_effects": True,
                               "text": "obs-alerting loaded before the 14-day paging rule was designed"}, spec["checks"])

    def test_rubric_renders_the_supplied_facts_and_substantive_failure_modes(self):
        for case in PAIRS:
            with self.subTest(case=case):
                with (
                    tempfile.TemporaryDirectory() as directory,
                    mock.patch.object(judge, "claude_executable", return_value="/offline/claude"),
                    mock.patch.object(judge, "_run_judge_process",
                                      side_effect=AssertionError("prompt captured")) as spawn,
                    self.assertRaisesRegex(AssertionError, "prompt captured"),
                ):
                    judge.judge("complete design record", RUBRIC, {"case": case},
                                model="sonnet", cache_dir=Path(directory),
                                rubrics=judge.load_rubrics(PROPOSAL / "rubrics.yaml"))
                spawn.assert_called_once()
                prompt = str(spawn.call_args.args[0])
                spec = proposed_scenario("principal-engineer", PAIRS[case])
                self.assertEqual({"prompt": spec["prompt"], "files": spec["fixture"]["files"]},
                                 context_from_prompt(prompt)[case])
                for text in ("complete design record", "request logs", "90 days", "query errors",
                             "retired endpoints", "human owner", "inventory/endpoints.csv"):
                    self.assertIn(text, prompt)

    def test_corpus_has_reviewable_positive_controls_and_single_fault_counterexamples(self):
        cases = judge._load_calibration(PROPOSAL / "rubrics-calibration.yaml")
        by_id = {c["id"]: c for c in cases}
        required = {
            "principal-migration-owner-evidence": "pass",
            "principal-migration-version-evidence": "pass",
            "principal-migration-access-logs": "fail",
            "principal-migration-producer-detector": "fail",
            "principal-migration-in-place": "fail",
            "principal-tracker-active-inventory": "pass",
            "principal-tracker-latest-run": "pass",
            "principal-tracker-retired-pages": "fail",
            "principal-tracker-db-heartbeat-only": "fail",
            "principal-tracker-no-data-only": "fail",
            "principal-tracker-rescan-history": "fail",
            "principal-tracker-unset-target": "fail",
            "principal-tracker-supplied-inventory": "pass",
            "principal-tracker-markdown-search-absence": "fail",
            "principal-tracker-preservation-prerequisite": "pass",
            "principal-tracker-unconfirmed-restore": "fail",
            "principal-migration-complete-fixture": "pass",
            "principal-tracker-complete-fixture": "pass",
        }
        self.assertEqual(len(cases), len(by_id), "calibration IDs must be unique")
        self.assertEqual(set(required), set(by_id))
        for identity, expected in required.items():
            with self.subTest(identity=identity):
                case = by_id[identity]
                self.assertEqual(expected, case["expect"])
                self.assertIn(case["params"]["case"], PAIRS)
                self.assertTrue(case["response"].strip())
                self.assertTrue(case["source"].strip())
        for case_name in PAIRS:
            self.assertEqual({"pass", "fail"}, {c["expect"] for c in cases if c["params"]["case"] == case_name})

    def test_complete_fixture_positive_controls_cite_supplied_details(self):
        cases = {case["id"]: case for case in judge._load_calibration(PROPOSAL / "rubrics-calibration.yaml")}
        controls = {
            "principal-migration-complete-fixture": (
                "contract-judgment", "grafana/dashboards/maintenance.json",
                ("marcusolsson-json-datasource", "maintenance-api", "YYYY-MM-DD HH:mm")),
            "principal-tracker-complete-fixture": (
                "new-system-judgment", "inventory/endpoints.csv",
                ("md-feed-admin.internal", "8443", "market-data", "md-team")),
        }
        for identity, (suffix, path, facts) in controls.items():
            with self.subTest(identity=identity):
                self.assertEqual("pass", cases[identity]["expect"])
                source = proposed_scenario("principal-engineer", suffix)["fixture"]["files"][path]
                for fact in facts:
                    self.assertIn(fact, source)
                    self.assertIn(fact, cases[identity]["response"])

    def test_semantic_grading_without_calibration_refuses_before_a_model_call(self):
        spec = {"type": "rubric", "name": RUBRIC, "params": {"case": "certificate_tracker"}}
        proposal = judge.load_rubrics(PROPOSAL / "rubrics.yaml")
        with (mock.patch.object(judge, "load_rubrics", return_value=proposal),
              mock.patch.object(judge, "_run_judge_process", side_effect=AssertionError("no model call")),
              self.assertRaisesRegex(judge.JudgeUnavailable, "calibration")):
            graders.run_grader(spec, "a proposed design")

    def test_inactive_rubric_is_refused_before_a_model_call(self):
        spec = {"type": "rubric", "name": RUBRIC, "params": {"case": "certificate_tracker"}}
        with (mock.patch.object(judge, "_run_judge_process", side_effect=AssertionError("no model call")),
              self.assertRaisesRegex(ValueError, "unknown rubric")):
            graders.run_grader(spec, "a proposed design")


if __name__ == "__main__":
    unittest.main()
