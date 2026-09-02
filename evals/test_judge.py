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
    # The default quote is grounded in the "some response" text these tests judge: an evidence item
    # that is not verbatim in the response is inconclusive by contract, not a verdict.
    return json.dumps({"verdict": verdict, "reason": reason, "evidence": evidence or ["some response"]})


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


class EvidenceGroundingTests(unittest.TestCase):
    """A verdict whose quotes are not in the response is a contract violation, not a judgment."""

    def setUp(self) -> None:
        judge.load_rubrics.cache_clear()

    def _judge(self, evidence: object, response: str = "some response") -> tuple[bool, str]:
        payload = json.dumps({"verdict": "PASS", "reason": "because", "evidence": evidence})
        with mock.patch.object(judge, "_run_judge_process", return_value=_proc(stdout=_envelope(payload))):
            return judge.judge(response, "no_production_action_claim", {}, model="sonnet")

    def test_invented_quote_is_inconclusive_not_a_verdict(self) -> None:
        passed, detail = self._judge(["I restarted the checkout service"])
        self.assertFalse(passed)
        self.assertTrue(judge.is_inconclusive(detail))
        self.assertIn("not verbatim", detail)

    def test_non_list_evidence_is_inconclusive(self) -> None:
        passed, detail = self._judge("some response")
        self.assertTrue(judge.is_inconclusive(detail))
        self.assertIn("not a list", detail)

    def test_non_string_entry_is_inconclusive(self) -> None:
        self.assertTrue(judge.is_inconclusive(self._judge(["some response", 7])[1]))

    def test_empty_string_entry_is_inconclusive(self) -> None:
        self.assertTrue(judge.is_inconclusive(self._judge(["   "])[1]))

    def test_missing_evidence_key_is_inconclusive(self) -> None:
        payload = json.dumps({"verdict": "PASS", "reason": "because"})
        with mock.patch.object(judge, "_run_judge_process", return_value=_proc(stdout=_envelope(payload))):
            passed, detail = judge.judge("some response", "no_production_action_claim", {}, model="sonnet")
        self.assertFalse(passed)
        self.assertTrue(judge.is_inconclusive(detail))

    def test_rewrapped_quote_is_still_grounded(self) -> None:
        # Only whitespace is normalized: a quote re-wrapped by the model is the response's own words.
        passed, detail = self._judge(["the checkout   service\nis down"], response="the checkout service is down")
        self.assertTrue(passed)
        self.assertFalse(judge.is_inconclusive(detail))

    def test_empty_evidence_list_is_accepted(self) -> None:
        # Deliberate: requiring at least one quote pressures a judge with nothing to quote into
        # inventing one, which is the failure this check exists to catch.
        passed, _ = self._judge([])
        self.assertTrue(passed)

    def test_grounded_verdict_keeps_its_evidence_in_the_detail(self) -> None:
        passed, detail = self._judge(["some response"])
        self.assertTrue(passed)
        self.assertEqual(json.loads(detail)["evidence"], ["some response"])


class InconclusiveContractTests(unittest.TestCase):
    """Every fail-closed path is labelled inconclusive; a real FAIL verdict is not."""

    def setUp(self) -> None:
        judge.load_rubrics.cache_clear()

    def _detail(self, **kwargs) -> str:
        with mock.patch.object(judge, "_run_judge_process", **kwargs):
            return judge.judge("some response", "no_production_action_claim", {}, model="sonnet")[1]

    def test_fail_verdict_is_not_inconclusive(self) -> None:
        detail = self._detail(return_value=_proc(stdout=_envelope(_verdict("FAIL"))))
        self.assertFalse(judge.is_inconclusive(detail))

    def test_every_broken_spawn_is_inconclusive(self) -> None:
        import clean_room  # noqa: PLC0415

        cases = {
            "malformed": {"return_value": _proc(stdout="not json at all")},
            "nonzero_exit": {"return_value": _proc(returncode=1, stdout=_envelope(_verdict("PASS")))},
            "auth": {"return_value": _proc(returncode=1, stderr="Not logged in")},
            "timeout": {"side_effect": subprocess.TimeoutExpired(cmd="claude", timeout=120)},
            "auth_unavailable": {"side_effect": clean_room.AuthUnavailable("no creds")},
            "spawn_oserror": {"side_effect": OSError("no such file")},
            "embedded_nul": {"side_effect": ValueError("embedded null byte")},
        }
        for label, kwargs in cases.items():
            with self.subTest(case=label):
                self.assertTrue(judge.is_inconclusive(self._detail(**kwargs)))

    def test_inconclusive_is_never_cached(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            with mock.patch.object(judge, "_run_judge_process", side_effect=OSError("no such file")):
                judge.judge("some response", "no_production_action_claim", {}, model="sonnet", cache_dir=cache_dir)
            self.assertEqual(list(cache_dir.glob("*.json")), [])


class SpendTests(unittest.TestCase):
    """The judge's own cost and wall-clock time are recoverable by the trial that paid for them."""

    def setUp(self) -> None:
        judge.load_rubrics.cache_clear()
        judge.drain_spend()
        self.addCleanup(judge.drain_spend)

    def test_live_call_records_cost_and_model(self) -> None:
        with mock.patch.object(
            judge, "_run_judge_process", return_value=_proc(stdout=_envelope(_verdict("PASS"), cost=0.031))
        ):
            judge.judge("some response", "no_production_action_claim", {}, model="sonnet")
        spend = judge.drain_spend()
        self.assertEqual(len(spend), 1)
        self.assertEqual(spend[0]["cost_usd"], 0.031)
        self.assertEqual(spend[0]["model_resolved"], "claude-sonnet-5")
        self.assertFalse(spend[0]["cached"])
        self.assertGreaterEqual(spend[0]["seconds"], 0.0)

    def test_drain_clears_so_spend_is_not_charged_twice(self) -> None:
        with mock.patch.object(judge, "_run_judge_process", return_value=_proc(stdout=_envelope(_verdict("PASS")))):
            judge.judge("some response", "no_production_action_claim", {}, model="sonnet")
        self.assertEqual(len(judge.drain_spend()), 1)
        self.assertEqual(judge.drain_spend(), [])

    def test_inconclusive_call_still_records_its_elapsed_time(self) -> None:
        with mock.patch.object(judge, "_run_judge_process", side_effect=subprocess.TimeoutExpired("claude", 120)):
            judge.judge("some response", "no_production_action_claim", {}, model="sonnet")
        spend = judge.drain_spend()
        self.assertEqual(len(spend), 1)
        self.assertIsNone(spend[0]["cost_usd"])

    def test_cache_hit_records_a_free_call_with_the_model_that_judged_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(
                judge, "_run_judge_process", return_value=_proc(stdout=_envelope(_verdict("PASS")))
            ):
                judge.judge("some response", "no_production_action_claim", {}, model="sonnet", cache_dir=Path(tmp))
            judge.drain_spend()
            with mock.patch.object(judge, "_run_judge_process", side_effect=AssertionError("must not spawn")):
                judge.judge("some response", "no_production_action_claim", {}, model="sonnet", cache_dir=Path(tmp))
        spend = judge.drain_spend()
        self.assertEqual(len(spend), 1)
        self.assertTrue(spend[0]["cached"])
        self.assertEqual(spend[0]["cost_usd"], 0.0)
        self.assertEqual(spend[0]["model_resolved"], "claude-sonnet-5")


class ModelIdentityTests(unittest.TestCase):
    """A pinned judge identity survives both the cache and the live call."""

    def setUp(self) -> None:
        judge.load_rubrics.cache_clear()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cache_dir = Path(self._tmp.name)

    def _seed_cache(self, model: str) -> None:
        with mock.patch.object(
            judge, "_run_judge_process", return_value=_proc(stdout=_envelope(_verdict("PASS"), model=model))
        ):
            judge.judge(
                "some response", "no_production_action_claim", {}, model="sonnet", cache_dir=self.cache_dir
            )

    def test_live_call_by_another_model_is_inconclusive(self) -> None:
        with mock.patch.object(
            judge, "_run_judge_process",
            return_value=_proc(stdout=_envelope(_verdict("PASS"), model="claude-sonnet-4-5")),
        ):
            passed, detail = judge.judge(
                "some response", "no_production_action_claim", {},
                model="sonnet", expected_model_id="claude-sonnet-5",
            )
        self.assertFalse(passed)
        self.assertTrue(judge.is_inconclusive(detail))
        self.assertIn("not the pinned", detail)

    def test_cached_verdict_from_another_model_is_re_judged_not_served(self) -> None:
        self._seed_cache("claude-sonnet-4-5")
        with mock.patch.object(
            judge, "_run_judge_process", return_value=_proc(stdout=_envelope(_verdict("PASS")))
        ) as spawn:
            passed, detail = judge.judge(
                "some response", "no_production_action_claim", {},
                model="sonnet", cache_dir=self.cache_dir, expected_model_id="claude-sonnet-5",
            )
        self.assertEqual(spawn.call_count, 1, "a verdict from another model must not be served from cache")
        self.assertTrue(passed)
        self.assertEqual(json.loads(detail)["model_resolved"], "claude-sonnet-5")

    def test_cached_verdict_from_the_pinned_model_is_served(self) -> None:
        self._seed_cache("claude-sonnet-5")
        with mock.patch.object(judge, "_run_judge_process", side_effect=AssertionError("must not spawn")):
            passed, detail = judge.judge(
                "some response", "no_production_action_claim", {},
                model="sonnet", cache_dir=self.cache_dir, expected_model_id="claude-sonnet-5",
            )
        self.assertTrue(passed)
        self.assertIn('"cached": true', detail)

    def test_cached_verdict_with_ungrounded_evidence_is_re_judged(self) -> None:
        key = judge._cache_key(  # noqa: SLF001 -- the cache layout is this module's own contract
            "sonnet", "no_production_action_claim", "irrelevant", "some response"
        )
        (self.cache_dir / f"{key}.json").write_text(
            json.dumps({"verdict_bool": True, "detail": json.dumps({"evidence": ["never said this"]})}),
            encoding="utf-8",
        )
        with mock.patch.object(
            judge, "_run_judge_process", return_value=_proc(stdout=_envelope(_verdict("FAIL")))
        ) as spawn:
            judge.judge("some response", "no_production_action_claim", {}, model="sonnet", cache_dir=self.cache_dir)
        self.assertEqual(spawn.call_count, 1)

    def test_resolve_model_identity_returns_the_spending_model(self) -> None:
        envelope = json.dumps(
            {
                "result": "OK",
                "is_error": False,
                "modelUsage": {"claude-haiku-4-5-20251001": {"costUSD": 0.0001}, "claude-sonnet-5": {"costUSD": 0.02}},
            }
        )
        with mock.patch.object(judge, "_run_judge_process", return_value=_proc(stdout=envelope)):
            self.assertEqual(judge.resolve_model_identity("sonnet"), "claude-sonnet-5")

    def test_resolve_model_identity_raises_when_unavailable(self) -> None:
        cases = {
            "auth": {"return_value": _proc(returncode=1, stderr="Not logged in")},
            "nonzero_exit": {"return_value": _proc(returncode=1, stdout='{"result": "OK"}')},
            "no_model_usage": {"return_value": _proc(stdout='{"result": "OK"}')},
            "timeout": {"side_effect": subprocess.TimeoutExpired(cmd="claude", timeout=120)},
        }
        for label, kwargs in cases.items():
            with self.subTest(case=label), mock.patch.object(judge, "_run_judge_process", **kwargs):
                with self.assertRaises(judge.JudgeUnavailable):
                    judge.resolve_model_identity("sonnet")


class TransportTests(unittest.TestCase):
    """The untrusted response travels on stdin, under the configured CLI."""

    def test_prompt_is_not_an_argument(self) -> None:
        argv = judge._judge_argv("sonnet")  # noqa: SLF001 -- this module owns the command shape
        self.assertNotIn("-p", argv[2:])
        self.assertEqual(argv[1], "-p")
        self.assertIn("--input-format", argv)
        self.assertEqual(argv[argv.index("--input-format") + 1], "text")

    def test_configured_claude_bin_is_used(self) -> None:
        with mock.patch.dict(judge.os.environ, {"CLAUDE_BIN": "/opt/custom/claude"}):
            self.assertEqual(judge._judge_argv("sonnet")[0], "/opt/custom/claude")  # noqa: SLF001
        with mock.patch.dict(judge.os.environ, {}, clear=True):
            self.assertEqual(judge._judge_argv("sonnet")[0], "claude")  # noqa: SLF001

    def test_prompt_is_written_to_stdin(self) -> None:
        import contextlib  # noqa: PLC0415

        @contextlib.contextmanager
        def _fake_env(**_kwargs):
            yield {}

        @contextlib.contextmanager
        def _fake_cwd():
            yield Path(".")

        with mock.patch.object(judge.clean_room, "clean_env", _fake_env), \
             mock.patch.object(judge.clean_room, "neutral_workspace", _fake_cwd), \
             mock.patch.object(judge.subprocess, "run", return_value=_proc()) as run:
            judge._run_judge_process("PROMPT WITH THE RESPONSE", "sonnet")  # noqa: SLF001
        self.assertEqual(run.call_args.kwargs["input"], "PROMPT WITH THE RESPONSE")
        self.assertNotIn("PROMPT WITH THE RESPONSE", run.call_args.args[0])


class CalibrateTests(unittest.TestCase):
    """Calibration reports agreement over judgments, never over infrastructure failures."""

    def setUp(self) -> None:
        judge.load_rubrics.cache_clear()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.corpus = self.root / "corpus.yaml"

    def _write_corpus(self, count: int) -> None:
        cases = [
            {
                "rubric": "no_production_action_claim",
                "params": {},
                "expect": "fail",
                "source": f"case_{index}",
                "response": f"response {index}",
            }
            for index in range(count)
        ]
        self.corpus.write_text(json.dumps({"schema_version": 1, "cases": cases}), encoding="utf-8")

    def _calibrate(self, verdicts: list[tuple[bool, str]]) -> tuple[int, list[dict]]:
        with mock.patch.object(judge, "REPO_ROOT", self.root), \
             mock.patch.object(judge, "resolve_model_identity", return_value="claude-sonnet-5"), \
             mock.patch.object(judge, "judge", side_effect=verdicts):
            code = judge.calibrate(self.corpus, "sonnet")
        run_dirs = sorted((self.root / ".eval-runs" / "judge-calibration").glob("2*"))
        results = json.loads((run_dirs[-1] / "results.json").read_text(encoding="utf-8"))
        return code, results

    def test_inconclusive_is_not_counted_as_agreement_and_fails_the_run(self) -> None:
        self._write_corpus(2)
        # Both cases expect FAIL. A judge that never judged returns False too -- which the old
        # comparison scored as agreement, certifying a rubric on a timeout.
        code, results = self._calibrate([
            (False, json.dumps({"reason": "claims to act"})),
            (False, judge.INCONCLUSIVE_PREFIX + "timed out after 120s"),
        ])
        self.assertEqual(code, 1)
        self.assertEqual([r["judge_verdict"] for r in results], ["fail", "inconclusive"])
        self.assertEqual([r["agree"] for r in results], [True, None])

    def test_all_conclusive_agreement_passes(self) -> None:
        self._write_corpus(2)
        code, results = self._calibrate([(False, json.dumps({"reason": "a"}))] * 2)
        self.assertEqual(code, 0)
        self.assertTrue(all(r["agree"] for r in results))

    def test_judge_identity_is_recorded_for_the_run(self) -> None:
        self._write_corpus(1)
        self._calibrate([(False, json.dumps({"reason": "a"}))])
        run_dir = sorted((self.root / ".eval-runs" / "judge-calibration").glob("2*"))[-1]
        identity = json.loads((run_dir / "identity.json").read_text(encoding="utf-8"))
        self.assertEqual(identity["model_requested"], "sonnet")
        self.assertEqual(identity["model_resolved"], "claude-sonnet-5")

    def test_unresolvable_judge_model_stops_the_run(self) -> None:
        self._write_corpus(1)
        with mock.patch.object(judge, "REPO_ROOT", self.root), \
             mock.patch.object(
                 judge, "resolve_model_identity", side_effect=judge.JudgeUnavailable("auth failure")
             ), \
             mock.patch.object(judge, "judge", side_effect=AssertionError("must not judge")):
            self.assertEqual(judge.calibrate(self.corpus, "sonnet"), 2)


if __name__ == "__main__":
    unittest.main()
