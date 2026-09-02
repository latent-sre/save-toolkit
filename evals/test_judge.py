#!/usr/bin/env python3
"""Tests for evals/judge.py. The spawn is always monkeypatched -- no test here may call a model.

Runnable:
    python evals/test_judge.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import judge  # noqa: E402


def _proc(*, returncode: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=["claude"], returncode=returncode, stdout=stdout, stderr=stderr)


def _envelope(result: str, *, is_error: bool = False, model: str = "claude-sonnet-5", cost: float = 0.01) -> str:
    return json.dumps(
        {
            "result": result,
            "is_error": is_error,
            "modelUsage": {model: {}},
            "total_cost_usd": cost,
        }
    )


def _verdict(verdict: str, reason: str = "because", evidence: list | None = None) -> str:
    return json.dumps({"verdict": verdict, "reason": reason, "evidence": evidence or ["a quote"]})


class LoadRubricsTests(unittest.TestCase):
    def test_load_rubrics_reads_the_real_file(self) -> None:
        judge.load_rubrics.cache_clear()
        rubrics = judge.load_rubrics()
        self.assertIn("no_production_action_claim", rubrics)
        self.assertIn("gate_blocks_action", rubrics)
        for name, rubric in rubrics.items():
            with self.subTest(rubric=name):
                self.assertIn("fail_if", rubric)
                self.assertIn("pass_if", rubric)


class ValidateParamsTests(unittest.TestCase):
    def setUp(self) -> None:
        judge.load_rubrics.cache_clear()
        self.rubrics = judge.load_rubrics()

    def test_missing_param_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, r"missing=\['owner'|'query'"):
            judge.validate_params("unknown_outcome_reconcile_first", self.rubrics, {"query": "cf app checkout"})

    def test_extra_param_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, r"extra=\['bogus'\]"):
            judge.validate_params("no_production_action_claim", self.rubrics, {"bogus": 1})

    def test_unknown_rubric_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown rubric"):
            judge.validate_params("not-a-real-rubric", self.rubrics, {})

    def test_exact_params_pass(self) -> None:
        rubric = judge.validate_params(
            "unknown_outcome_reconcile_first", self.rubrics, {"owner": "Riley Chen", "query": "cf app checkout"}
        )
        self.assertIn("fail_if", rubric)


class RunGraderEmptyResponseTests(unittest.TestCase):
    """graders.run_grader(spec, "") must validate the spec and never spawn."""

    def setUp(self) -> None:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import graders  # noqa: PLC0415

        self.graders = graders
        judge.load_rubrics.cache_clear()

    def test_empty_response_short_circuits_without_spawning(self) -> None:
        with mock.patch.object(judge, "_run_judge_process", side_effect=AssertionError("must not spawn")):
            passed, detail = self.graders.run_grader(
                {"type": "rubric", "name": "no_production_action_claim", "params": {}}, ""
            )
        self.assertFalse(passed)
        self.assertEqual(detail, "empty response")

    def test_missing_params_raises_before_any_spawn(self) -> None:
        with mock.patch.object(judge, "_run_judge_process", side_effect=AssertionError("must not spawn")):
            with self.assertRaises(ValueError):
                self.graders.run_grader(
                    {
                        "type": "rubric",
                        "name": "unknown_outcome_reconcile_first",
                        "params": {"owner": "Riley Chen"},
                    },
                    "",
                )

    def test_extra_params_raises_before_any_spawn(self) -> None:
        with mock.patch.object(judge, "_run_judge_process", side_effect=AssertionError("must not spawn")):
            with self.assertRaises(ValueError):
                self.graders.run_grader(
                    {"type": "rubric", "name": "no_production_action_claim", "params": {"bogus": 1}}, ""
                )

    def test_unknown_rubric_raises_before_any_spawn(self) -> None:
        with mock.patch.object(judge, "_run_judge_process", side_effect=AssertionError("must not spawn")):
            with self.assertRaises(ValueError):
                self.graders.run_grader({"type": "rubric", "name": "not-a-real-rubric", "params": {}}, "")


class PromptRenderingTests(unittest.TestCase):
    def setUp(self) -> None:
        judge.load_rubrics.cache_clear()
        self.captured_prompt = None

    def _capture(self, prompt: str, model: str) -> subprocess.CompletedProcess:
        self.captured_prompt = prompt
        return _proc(stdout=_envelope(_verdict("PASS")))

    def test_prompt_carries_rubric_name_rendered_text_and_response(self) -> None:
        with mock.patch.object(judge, "_run_judge_process", side_effect=self._capture):
            judge.judge(
                "the response text goes here",
                "unknown_outcome_reconcile_first",
                {"owner": "Riley Chen", "query": "cf app checkout"},
                model="sonnet",
            )
        self.assertIsNotNone(self.captured_prompt)
        self.assertIn("RUBRIC: unknown_outcome_reconcile_first", self.captured_prompt)
        # The rendered fail_if/pass_if text substitutes the params in place of the placeholders.
        self.assertIn("Riley Chen", self.captured_prompt)
        self.assertIn("cf app checkout", self.captured_prompt)
        self.assertNotIn("{owner}", self.captured_prompt)
        self.assertNotIn("{query}", self.captured_prompt)
        self.assertIn("<<<BEGIN RESPONSE>>>", self.captured_prompt)
        self.assertIn("the response text goes here", self.captured_prompt)
        self.assertIn("<<<END RESPONSE>>>", self.captured_prompt)


class ParseVerdictTests(unittest.TestCase):
    def setUp(self) -> None:
        judge.load_rubrics.cache_clear()

    def _judge(self, result_text: str, **envelope_kwargs) -> tuple[bool, str]:
        with mock.patch.object(
            judge, "_run_judge_process", return_value=_proc(stdout=_envelope(result_text, **envelope_kwargs))
        ):
            return judge.judge("some response", "no_production_action_claim", {}, model="sonnet")

    def test_bare_json_object(self) -> None:
        passed, detail = self._judge(_verdict("PASS"))
        self.assertTrue(passed)

    def test_fenced_json_object(self) -> None:
        fenced = "```json\n" + _verdict("PASS") + "\n```"
        passed, _ = self._judge(fenced)
        self.assertTrue(passed)

    def test_object_followed_by_prose(self) -> None:
        trailing = _verdict("FAIL", reason="it claims to act") + "\n\nThat's my verdict, let me know if you need more."
        passed, detail = self._judge(trailing)
        self.assertFalse(passed)
        self.assertIn("it claims to act", detail)

    def test_fail_verdict_returns_false_with_reason_in_detail(self) -> None:
        passed, detail = self._judge(_verdict("FAIL", reason="the assistant said it would restart checkout"))
        self.assertFalse(passed)
        self.assertIn("the assistant said it would restart checkout", detail)


class FailClosedTests(unittest.TestCase):
    def setUp(self) -> None:
        judge.load_rubrics.cache_clear()

    def _judge_with_proc(self, proc: subprocess.CompletedProcess) -> tuple[bool, str]:
        with mock.patch.object(judge, "_run_judge_process", return_value=proc):
            return judge.judge("some response", "no_production_action_claim", {}, model="sonnet")

    def test_malformed_json_fails_closed(self) -> None:
        passed, detail = self._judge_with_proc(_proc(stdout="not json at all"))
        self.assertFalse(passed)
        self.assertIn("judge inconclusive", detail)

    def test_nonzero_exit_fails_closed(self) -> None:
        passed, detail = self._judge_with_proc(
            _proc(returncode=1, stdout=_envelope(_verdict("PASS")))
        )
        self.assertFalse(passed)
        self.assertIn("judge inconclusive", detail)

    def test_auth_marker_fails_closed(self) -> None:
        passed, detail = self._judge_with_proc(
            _proc(returncode=1, stdout="", stderr="Not logged in")
        )
        self.assertFalse(passed)
        self.assertIn("judge inconclusive", detail)

    def test_unknown_verdict_fails_closed(self) -> None:
        malformed_verdict = json.dumps({"verdict": "MAYBE", "reason": "unsure", "evidence": []})
        passed, detail = self._judge_with_proc(_proc(stdout=_envelope(malformed_verdict)))
        self.assertFalse(passed)
        self.assertIn("judge inconclusive", detail)

    def test_timeout_fails_closed(self) -> None:
        with mock.patch.object(
            judge, "_run_judge_process", side_effect=subprocess.TimeoutExpired(cmd="claude", timeout=120)
        ):
            passed, detail = judge.judge("some response", "no_production_action_claim", {}, model="sonnet")
        self.assertFalse(passed)
        self.assertIn("judge inconclusive", detail)

    def test_auth_unavailable_fails_closed(self) -> None:
        import clean_room  # noqa: PLC0415

        with mock.patch.object(judge, "_run_judge_process", side_effect=clean_room.AuthUnavailable("no creds")):
            passed, detail = judge.judge("some response", "no_production_action_claim", {}, model="sonnet")
        self.assertFalse(passed)
        self.assertIn("judge inconclusive", detail)


class CacheTests(unittest.TestCase):
    def setUp(self) -> None:
        judge.load_rubrics.cache_clear()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cache_dir = Path(self._tmp.name)

    def test_cache_hit_does_not_spawn_and_marks_cached_true(self) -> None:
        with mock.patch.object(
            judge, "_run_judge_process", return_value=_proc(stdout=_envelope(_verdict("PASS")))
        ) as spawn:
            passed1, detail1 = judge.judge(
                "some response", "no_production_action_claim", {}, model="sonnet", cache_dir=self.cache_dir
            )
        self.assertTrue(passed1)
        self.assertEqual(spawn.call_count, 1)
        self.assertIn('"cached": false', detail1)

        with mock.patch.object(judge, "_run_judge_process", side_effect=AssertionError("must not spawn")):
            passed2, detail2 = judge.judge(
                "some response", "no_production_action_claim", {}, model="sonnet", cache_dir=self.cache_dir
            )
        self.assertEqual(passed1, passed2)
        self.assertIn('"cached": true', detail2)

    def test_different_response_is_a_cache_miss(self) -> None:
        with mock.patch.object(
            judge, "_run_judge_process", return_value=_proc(stdout=_envelope(_verdict("PASS")))
        ) as spawn:
            judge.judge("response A", "no_production_action_claim", {}, model="sonnet", cache_dir=self.cache_dir)
            judge.judge("response B", "no_production_action_claim", {}, model="sonnet", cache_dir=self.cache_dir)
        self.assertEqual(spawn.call_count, 2)


if __name__ == "__main__":
    unittest.main()
