"""Offline contract checks for PRINCIPAL-001's semantic comparison; never call a model."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import graders
import judge
from probe import catalog

ROOT = Path(__file__).resolve().parent
RUBRIC = "principal_design_judgment"
PAIRS = {
    "maintenance_window_contract": "contract-judgment",
    "certificate_tracker": "new-system-judgment",
}


class PrincipalJudgmentTests(unittest.TestCase):
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
                principal = catalog.load_scenario(ROOT / f"build-scenarios/build-principal-engineer-{suffix}.yaml")
                builder = catalog.load_scenario(ROOT / f"build-scenarios/build-software-engineer-{suffix}.yaml")
                original = catalog.load_scenario(ROOT / f"build-scenarios/{originals[case]}.yaml")
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
                spec = catalog.load_scenario(ROOT / f"build-scenarios/build-{agent}-{suffix}.yaml")
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
                                model="sonnet", cache_dir=Path(directory))
                spawn.assert_called_once()
                prompt = str(spawn.call_args.args[0])
                self.assertIn("complete design record", prompt)
                self.assertIn("request logs", prompt)
                self.assertIn("90 days", prompt)
                self.assertIn("query errors", prompt)
                self.assertIn("retired endpoints", prompt)
                self.assertIn("human owner", prompt)
                self.assertIn("inventory/endpoints.csv", prompt)

    def test_corpus_has_reviewable_positive_controls_and_single_fault_counterexamples(self):
        cases = [c for c in judge._load_calibration(judge.DEFAULT_CALIBRATION_PATH) if c["rubric"] == RUBRIC]
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

    def test_semantic_grading_without_calibration_refuses_before_a_model_call(self):
        spec = {"type": "rubric", "name": RUBRIC, "params": {"case": "certificate_tracker"}}
        with (mock.patch.object(judge, "_run_judge_process", side_effect=AssertionError("no model call")),
              self.assertRaisesRegex(judge.JudgeUnavailable, "calibration")):
            graders.run_grader(spec, "a proposed design")


if __name__ == "__main__":
    unittest.main()
