"""The final-reply judge receives the complete statement case; live calibration proves semantics."""
from __future__ import annotations

import os
import re
import unittest
from pathlib import Path
from unittest import mock

import judge
import yaml
from probe_testkit import judge_envelope, judge_process, judge_verdict

EVALS = Path(__file__).resolve().parent


class StatementContextTests(unittest.TestCase):
    def test_actual_judge_prompt_retains_the_initial_and_corrected_chronology(self) -> None:
        spec = yaml.safe_load((EVALS / "scenarios/native-incident-helper-return-and-resume.yaml").read_text())
        original = spec["prompt"] + spec["fixture"]["files"]["evidence.md"] + spec["followups"][0]
        observed_times = set(re.findall(r"\d{2}:\d{2} UTC|07:00 America/New_York", original))
        response = "The supplied records resolve impact; the cause remains unknown."
        result = judge_process(stdout=judge_envelope(judge_verdict("PASS", evidence=[response])))
        rubrics = yaml.safe_load((EVALS / "rubrics.yaml").read_text())["rubrics"]
        with mock.patch.dict(os.environ, {"EVAL_JUDGE_CACHE": ""}), \
                mock.patch.object(judge, "_run_judge_process", return_value=result) as process:
            judge.judge(response, "incident_companion_response", {"case": "statement_rerun"},
                        model="sonnet", rubrics=rubrics)
        judge.drain_spend()
        prompt = process.call_args.args[0]
        case = prompt.split("statement_rerun:", 1)[1].split("knowledge_card:", 1)[0]
        for observation in observed_times:
            with self.subTest(observation=observation):
                self.assertIn(observation, case, "a final-reply judge must see facts from both turns")
        for fact in ("daily-statement/run-42", "statement-2026-07-14/v3", "Morgan", "job owner"):
            self.assertIn(fact, case)

    def test_new_semantic_controls_are_mandatory_and_have_both_polarities(self) -> None:
        cases = judge._load_calibration(EVALS / "rubrics-calibration.yaml")
        controls = [case for case in cases if case.get("source", "").startswith("EVAL-011 statement_rerun:")]
        self.assertGreaterEqual(len(controls), 6)
        self.assertEqual({"pass", "fail"}, {case["expect"] for case in controls})
        self.assertTrue(all(case.get("required") is True for case in controls))
        self.assertTrue(all(case["rubric"] == "incident_companion_response"
                            and case["params"] == {"case": "statement_rerun"} for case in controls))
        self.assertEqual(len(controls), len({case["response"] for case in controls}))


if __name__ == "__main__":
    unittest.main()
