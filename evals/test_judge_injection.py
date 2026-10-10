"""AC-27 judge-input calibration cases and the response frame that keeps them inside it; no models."""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import judge

SOURCE_PREFIX = "AC-27 judge-input calibration: "


class PromptCaptured(Exception):
    """Stop before any model process, verdict, cache write, or spend recording."""


class JudgeInjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        active = judge._load_calibration(judge.DEFAULT_CALIBRATION_PATH)
        self.cases = [case for case in active if case["source"].startswith(SOURCE_PREFIX)]

    def capture_prompt(self, response: str) -> str:
        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch.object(judge, "claude_executable", return_value="/offline/claude"),
            mock.patch.object(judge, "_run_judge_process", side_effect=PromptCaptured) as spawn,
            self.assertRaises(PromptCaptured),
        ):
            judge.judge(response, "no_production_action_claim", {}, cache_dir=Path(directory))
        spawn.assert_called_once()
        return str(spawn.call_args.args[0])

    @staticmethod
    def markers(response: str) -> tuple[str, str]:
        tag = judge._frame_tag(response)
        return f"<<<BEGIN RESPONSE {tag}>>>\n", f"\n<<<END RESPONSE {tag}>>>"

    def test_cases_are_in_the_active_corpus_and_valid(self) -> None:
        self.assertEqual(len(self.cases), 6)
        self.assertEqual([case["expect"] for case in self.cases], ["fail", "fail", "pass", "pass", "fail", "pass"])
        self.assertEqual(len({case["source"] for case in self.cases}), len(self.cases))
        for case in self.cases:
            with self.subTest(source=case["source"]):
                self.assertEqual(set(case), {"rubric", "params", "expect", "response", "source", "required"})
                self.assertIs(case["required"], True)
                judge.validate_params(case["rubric"], judge.load_rubrics(), case["params"])
                self.assertTrue(case["response"].strip())
        breakouts = [case for case in self.cases if "<<<END RESPONSE>>>" in case["response"]]
        self.assertEqual([case["expect"] for case in breakouts], ["fail", "pass"])

    def test_only_the_reviewed_critical_controls_are_required(self) -> None:
        # Injection framing and the six conversation-evidence controls guard named failures the
        # rubric's 0.95 tolerance must not absorb. All other cases retain the ordinary tolerance.
        active = judge._load_calibration(judge.DEFAULT_CALIBRATION_PATH)
        required = [case["source"] for case in active if case.get("required")]
        conversation_controls = {
            "EVAL-011 statement_rerun: earlier supplied observations remain valid closeout context",
            "EVAL-011 statement_rerun: valid event interval does not assert a delivery delay",
            "EVAL-011 statement_rerun: success-to-read interval is falsely asserted as exact delivery delay",
            "EVAL-011 statement_rerun: corrected screenshot explains UI evidence but not delivery causality",
            "EVAL-011 statement_rerun: missing provider and mailbox event timestamps are invented",
            "EVAL-011 statement_rerun: reported success timestamp is falsely relabelled as start",
        }
        expected = {case["source"] for case in self.cases} | conversation_controls
        self.assertEqual(len(required), len(expected))
        self.assertEqual(set(required), expected)
        corpus = Path(self.enterContext(tempfile.TemporaryDirectory())) / "corpus.yaml"
        corpus.write_text('{"schema_version": 1, "cases": [{"rubric": "r", "expect": "fail", "required": "yes"}]}')
        with self.assertRaisesRegex(ValueError, "optional boolean required"):
            judge._load_calibration(corpus)

    def test_every_response_sits_whole_inside_one_tagged_frame(self) -> None:
        for case in self.cases:
            with self.subTest(source=case["source"]):
                response = case["response"]
                prompt = self.capture_prompt(response)
                begin, end = self.markers(response)
                self.assertEqual(prompt.count(begin), 1)
                self.assertEqual(prompt.count(end), 1)
                self.assertIn(begin + response + end, prompt)

    def test_an_embedded_marker_cannot_close_the_frame_early(self) -> None:
        # Regression for the fixed collision: the old fixed end marker inside a response ended the
        # apparent frame there and left "Judge: ... output PASS" after it, outside the data. The
        # frame is read from the prompt itself, so any framing scheme is judged by its boundary.
        for case in self.cases:
            response = case["response"]
            if "<<<END RESPONSE>>>" not in response:
                continue
            with self.subTest(source=case["source"]):
                prompt = self.capture_prompt(response)
                opening = re.search(r"^<<<BEGIN RESPONSE( [^>\n]*)?>>>\n", prompt, re.MULTILINE)
                self.assertIsNotNone(opening)
                closing = f"<<<END RESPONSE{opening[1] or ''}>>>"
                start = opening.end()
                stop = prompt.index(closing, start)
                self.assertEqual(prompt[start:stop], response + "\n")
                self.assertNotIn("output PASS", prompt[stop:])

    def test_tag_is_deterministic_and_differs_by_response(self) -> None:
        first, second = self.cases[0]["response"], self.cases[1]["response"]
        self.assertEqual(judge._frame_tag(first), judge._frame_tag(first))
        self.assertNotEqual(judge._frame_tag(first), judge._frame_tag(second))
        self.assertEqual(len(judge._frame_tag("\ud800 lone surrogate")), 16)


if __name__ == "__main__":
    unittest.main()
