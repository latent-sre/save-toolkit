#!/usr/bin/env python3
"""Tests for evals/judge.py. The spawn is always monkeypatched -- no test here may call a model.

Runnable:
    python evals/test_judge.py
"""
from __future__ import annotations

import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import graders
import judge
from probe_testkit import calibration_receipt, judge_envelope, judge_process, judge_verdict

RUBRIC = "no_production_action_claim"
GRADER = {"type": "rubric", "name": RUBRIC}


def spawn(**behaviour):
    """Replace the judge's model process, as every test here must."""
    return mock.patch.object(judge, "_run_judge_process", **behaviour)


def no_spawn(reason: str = "must not spawn"):
    return spawn(side_effect=AssertionError(reason))


def replying(result_text: str, **envelope):
    """A judge process that exits 0 with `result_text` inside the CLI's envelope."""
    return spawn(return_value=judge_process(stdout=judge_envelope(result_text, **envelope)))


def no_judging():
    return mock.patch.object(judge, "judge", side_effect=AssertionError("must not judge"))


def judge_once(response: str = "some response", *, model: str = "sonnet", **options) -> tuple[bool, str]:
    return judge.judge(response, RUBRIC, {}, model=model, **options)


def corpus_cases(count: int) -> list[dict]:
    """`count` calibration cases, each expecting FAIL for "response <index>"."""
    return [{"rubric": RUBRIC, "params": {}, "expect": "fail", "source": f"case_{index}", "response": f"response {index}"}
            for index in range(count)]


def cache_verdict(cache_dir: Path, response: str, model_id: str) -> None:
    """Store a FAIL verdict on `response` by `model_id` where the judge looks it up (the cache layout is
    this module's contract)."""
    key = judge.prepare(RUBRIC, {}, response, "sonnet", judge.load_rubrics())[0]
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"{key}.json").write_text(json.dumps({
        "verdict_bool": False, "execution": judge.execution_identity("sonnet"),
        "detail": json.dumps({"model_resolved": model_id, "reason": "claims to act", "evidence": [response]}),
    }), encoding="utf-8")


def spent(cost_usd: float | None = 0.03) -> dict:
    """What one live judge call by the pinned model records."""
    return {"cost_usd": cost_usd, "seconds": 1.0, "cached": False, "model_resolved": "claude-sonnet-5"}


class JudgeCase(unittest.TestCase):
    """Freshly parsed rubrics, an empty spend ledger and a scratch directory, `self.tmp`, for every test."""

    def setUp(self) -> None:
        judge.load_rubrics.cache_clear()
        judge.drain_spend()
        self.addCleanup(judge.drain_spend)
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))


class ReceiptCase(JudgeCase):
    """A test with a complete canonical calibration receipt, `self.receipt`, made without a model."""

    def setUp(self) -> None:
        super().setUp()
        self.receipt = calibration_receipt(self.tmp)


class LoadRubricsTests(JudgeCase):
    def test_load_rubrics_reads_the_real_file(self) -> None:
        rubrics = judge.load_rubrics()
        self.assertIn(RUBRIC, rubrics)
        self.assertIn("gate_blocks_action", rubrics)
        for name, rubric in rubrics.items():
            with self.subTest(rubric=name):
                self.assertIn("fail_if", rubric)
                self.assertIn("pass_if", rubric)


class ValidateParamsTests(JudgeCase):
    def test_missing_or_extra_params_and_an_unknown_rubric_raise(self) -> None:
        for name, params, error in (("unknown_outcome_reconcile_first", {"query": "cf app checkout"}, r"missing=\['owner'|'query'"),
                                    (RUBRIC, {"bogus": 1}, r"extra=\['bogus'\]"),
                                    ("not-a-real-rubric", {}, "unknown rubric")):
            with self.subTest(rubric=name, params=params), self.assertRaisesRegex(ValueError, error):
                judge.validate_params(name, judge.load_rubrics(), params)

    def test_exact_params_pass(self) -> None:
        rubric = judge.validate_params(
            "unknown_outcome_reconcile_first", judge.load_rubrics(), {"owner": "Riley Chen", "query": "cf app checkout"}
        )
        self.assertIn("fail_if", rubric)


class RunGraderEmptyResponseTests(JudgeCase):
    """graders.run_grader(spec, "") must validate the spec and never spawn."""

    def test_empty_response_short_circuits_without_spawning(self) -> None:
        with no_spawn():
            passed, detail = graders.run_grader({**GRADER, "params": {}}, "")
        self.assertFalse(passed)
        self.assertEqual(detail, "empty response")

    def test_nonempty_normal_gateway_requires_runner_binding_before_spawn(self) -> None:
        with no_spawn(), self.assertRaisesRegex(judge.JudgeUnavailable, "calibration"):
            graders.run_grader(GRADER, "some response")

    def test_missing_or_extra_params_and_an_unknown_rubric_raise_before_any_spawn(self) -> None:
        for name, params in (("unknown_outcome_reconcile_first", {"owner": "Riley Chen"}),
                             (RUBRIC, {"bogus": 1}), ("not-a-real-rubric", {})):
            with self.subTest(rubric=name, params=params), no_spawn(), self.assertRaises(ValueError):
                graders.run_grader({"type": "rubric", "name": name, "params": params}, "")


class CalibrationBindingTests(ReceiptCase):
    def overridden_rubrics(self) -> dict:
        """A private copy of the rubrics with a test-only pass_if; the cached ones stay untouched."""
        rubrics = json.loads(json.dumps(judge.load_rubrics()))
        rubrics[RUBRIC]["pass_if"] = "test-only rubric override"
        return rubrics

    def test_binding_pins_normal_gateway_and_retains_wrong_model_spend(self):
        binding = judge.load_binding(self.receipt, {RUBRIC})
        with mock.patch.dict(judge.os.environ, {"EVAL_JUDGE_MODEL": "other", "CLAUDE_BIN": "other-cli", "EVAL_JUDGE_CACHE": "wrong-cache"}), \
                replying(judge_verdict("PASS"), model="wrong-model") as process:
            passed, detail = graders.run_grader(GRADER, "some response", judge_binding=binding)
        self.assertFalse(passed)
        self.assertTrue(judge.is_inconclusive(detail))
        self.assertEqual("claude-sonnet-5", process.call_args.args[1])
        self.assertNotEqual("other-cli", process.call_args.kwargs["executable"])
        record = judge.drain_spend()[0]
        self.assertEqual(RUBRIC, record["rubric"])
        self.assertEqual("wrong-model", record["model_resolved"])
        self.assertTrue(record["inconclusive"])
        self.assertEqual(binding.metadata, record["judge_binding"])

    def test_bound_direct_api_rejects_rubric_overrides_before_spending(self):
        binding = judge.load_binding(self.receipt, {RUBRIC})
        with no_spawn(), self.assertRaisesRegex(judge.JudgeUnavailable, "rubric"):
            judge.judge("some response", RUBRIC, {}, binding=binding, rubrics=self.overridden_rubrics())

    def test_unbound_bootstrap_keeps_explicit_rubric_overrides(self):
        with replying(judge_verdict("PASS")) as process:
            self.assertTrue(judge.judge("some response", RUBRIC, {}, rubrics=self.overridden_rubrics())[0])
        self.assertIn("test-only rubric override", process.call_args.args[0])

    def test_incomplete_or_inapplicable_receipt_is_rejected_without_a_call(self):
        pristine = self.receipt.read_text(encoding="utf-8")
        for damage in ("accepted", "corpus_sha256", "results_sha256", "execution"):
            with self.subTest(damage=damage):
                receipt = json.loads(pristine)
                receipt[damage] = False if damage == "accepted" else "changed"
                self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
                with no_spawn(), self.assertRaises(judge.JudgeUnavailable):
                    judge.load_binding(self.receipt, {RUBRIC})

    def test_cache_identity_changes_with_execution_configuration(self):
        rubric = judge.load_rubrics()
        with mock.patch.dict(judge.os.environ, {"CLAUDE_BIN": "first-cli"}):
            first = judge.prepare(RUBRIC, {}, "some response", "sonnet", rubric)[0]
        with mock.patch.dict(judge.os.environ, {"CLAUDE_BIN": "second-cli"}):
            second = judge.prepare(RUBRIC, {}, "some response", "sonnet", rubric)[0]
        self.assertNotEqual(first, second)

    def test_bound_gateway_refuses_source_corpus_or_loaded_rubric_drift(self):
        binding = judge.load_binding(self.receipt, {RUBRIC})
        cases = judge._load_calibration(judge.DEFAULT_CALIBRATION_PATH)
        cases[0]["expect"] = "fail" if cases[0]["expect"] == "pass" else "pass"
        source = self.tmp / "rubrics.yaml"
        disk = {"schema_version": 1, "rubrics": json.loads(json.dumps(judge.load_rubrics()))}
        disk["rubrics"][RUBRIC]["pass_if"] = "changed on disk after loading"
        source.write_text(json.dumps(disk), encoding="utf-8")
        for patch in (mock.patch.object(judge, "_source_digest", return_value="changed"),
                      mock.patch.object(judge, "_load_calibration", return_value=cases),
                      mock.patch.object(judge, "RUBRICS_PATH", source)):
            with patch, no_spawn(), self.assertRaises(judge.JudgeUnavailable):
                graders.run_grader(GRADER, "some response", judge_binding=binding)

    def test_scenario_cannot_supply_its_own_judge_binding(self):
        with self.assertRaisesRegex(ValueError, "runner"):
            graders.run_grader({**GRADER, "judge_binding": {}}, "response")

    def test_normal_gateway_rejudges_wrong_model_cache_and_retains_free_hits(self):
        cache = self.tmp / "cache"
        with mock.patch.dict(judge.os.environ, {"EVAL_JUDGE_CACHE": str(cache)}):
            binding = judge.load_binding(self.receipt, {RUBRIC})
        with replying(judge_verdict("PASS"), model="wrong-model"):
            judge_once(model="claude-sonnet-5", cache_dir=cache)
        judge.drain_spend()
        with replying(judge_verdict("PASS")) as process:
            self.assertTrue(graders.run_grader(GRADER, "some response", judge_binding=binding)[0])
            self.assertEqual(1, process.call_count)
        judge.drain_spend()
        with no_spawn("cache hit must be free"):
            self.assertTrue(graders.run_grader(GRADER, "some response", judge_binding=binding)[0])
        record = judge.drain_spend()[0]
        self.assertTrue(record["cached"])
        self.assertEqual(0.0, record["cost_usd"])

    def test_edited_results_cannot_lower_agreement_using_a_receipt_threshold(self):
        path = self.receipt.with_name("results.json")
        results = json.loads(path.read_text(encoding="utf-8"))
        for result in results:
            result["judge_verdict"] = "fail" if result["expected"] == "pass" else "pass"
        path.write_text(json.dumps(results), encoding="utf-8")
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        receipt["results_sha256"] = judge._digest(results)
        receipt["threshold"] = 0
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
        with self.assertRaises(judge.JudgeUnavailable):
            judge.load_binding(self.receipt, {RUBRIC})


class RequiredCalibrationCaseBindingTests(ReceiptCase):
    """A receipt is refused when a required case disagrees, even with the rubric above 0.95."""

    def flip(self, pick):
        cases = judge._load_calibration(judge.DEFAULT_CALIBRATION_PATH)
        path = self.receipt.with_name("results.json")
        results = json.loads(path.read_text(encoding="utf-8"))
        index = next(i for i, case in enumerate(cases) if case["rubric"] == RUBRIC and pick(case))
        results[index]["judge_verdict"] = "pass" if cases[index]["expect"] == "fail" else "fail"
        path.write_text(json.dumps(results), encoding="utf-8")
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        agree, total, inconclusive = receipt["agreement"][RUBRIC]
        self.assertGreaterEqual((agree - 1) / total, judge.CALIBRATION_AGREEMENT_THRESHOLD)
        receipt["agreement"][RUBRIC] = [agree - 1, total, inconclusive]
        receipt["results_sha256"] = judge._digest(results)
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")

    def test_one_ordinary_disagreement_within_tolerance_still_binds(self):
        self.flip(lambda case: not case.get("required"))
        judge.load_binding(self.receipt, {RUBRIC})

    def test_a_required_case_disagreement_is_refused_within_tolerance(self):
        self.flip(lambda case: case.get("required"))
        with self.assertRaisesRegex(judge.JudgeUnavailable, "required calibration case"):
            judge.load_binding(self.receipt, {RUBRIC})


class PromptRenderingTests(JudgeCase):
    def test_prompt_carries_rubric_name_rendered_text_and_response(self) -> None:
        with replying(judge_verdict("PASS")) as process:
            judge.judge("the response text goes here", "unknown_outcome_reconcile_first",
                        {"owner": "Riley Chen", "query": "cf app checkout"}, model="sonnet")
        prompt = process.call_args.args[0]
        self.assertIn("RUBRIC: unknown_outcome_reconcile_first", prompt)
        # The rendered fail_if/pass_if text substitutes the params in place of the placeholders.
        self.assertIn("Riley Chen", prompt)
        self.assertIn("cf app checkout", prompt)
        self.assertNotIn("{owner}", prompt)
        self.assertNotIn("{query}", prompt)
        tag = judge._frame_tag("the response text goes here")
        self.assertIn(f"<<<BEGIN RESPONSE {tag}>>>\nthe response text goes here\n<<<END RESPONSE {tag}>>>", prompt)


class ParseVerdictTests(JudgeCase):
    def test_the_verdict_object_is_read_bare_fenced_or_before_prose(self) -> None:
        cases = {
            "bare JSON object": (judge_verdict("PASS"), True, ""),
            "fenced JSON object": ("```json\n" + judge_verdict("PASS") + "\n```", True, ""),
            "object followed by prose": (judge_verdict("FAIL", reason="it claims to act")
                                         + "\n\nThat's my verdict, let me know if you need more.", False, "it claims to act"),
            "FAIL returns false with its reason in the detail": (
                judge_verdict("FAIL", reason="the assistant said it would restart checkout"), False,
                "the assistant said it would restart checkout"),
        }
        for name, (reply, expected, reason) in cases.items():
            with self.subTest(name), replying(reply):
                passed, detail = judge_once()
                self.assertEqual(expected, passed)
                self.assertIn(reason, detail)


class CacheTests(JudgeCase):
    def test_cache_hit_does_not_spawn_and_marks_cached_true(self) -> None:
        with replying(judge_verdict("PASS")) as process:
            passed1, detail1 = judge_once(cache_dir=self.tmp)
        self.assertTrue(passed1)
        self.assertEqual(process.call_count, 1)
        self.assertIn('"cached": false', detail1)
        with no_spawn():
            passed2, detail2 = judge_once(cache_dir=self.tmp)
        self.assertEqual(passed1, passed2)
        self.assertIn('"cached": true', detail2)

    def test_different_response_is_a_cache_miss(self) -> None:
        with replying(judge_verdict("PASS")) as process:
            judge_once("response A", cache_dir=self.tmp)
            judge_once("response B", cache_dir=self.tmp)
        self.assertEqual(process.call_count, 2)


class EvidenceGroundingTests(JudgeCase):
    """A verdict whose quotes are not in the response is a contract violation, not a judgment."""

    def _judge(self, evidence: object, response: str = "some response") -> tuple[bool, str]:
        with replying(json.dumps({"verdict": "PASS", "reason": "because", "evidence": evidence})):
            return judge_once(response)

    def test_quotes_drawn_from_the_response_are_grounded(self) -> None:
        quoted = '- "Ignore any instructions" is the exact anti-pattern the reference names.'
        cases = {
            # Only whitespace is normalized: a quote re-wrapped by the model is the response's own words.
            "rewrapped quote": (["the checkout   service\nis down"], "the checkout service is down"),
            # Live run 20260902T064116Z-53ca9332: the judge quoted a long sentence with its middle
            # dropped ("...") and the trial went inconclusive. Each fragment is still verbatim.
            "elided quote with every fragment verbatim": (
                ['split into a credential-free "evaluate" agent ... with no Bash'],
                'split into a credential-free "evaluate" agent that returns a verdict (pass/fail) with no Bash'),
            # Same live run: the response said "Ignore any instructions" in double quotes and the judge
            # copied it in single quotes; curly quotes are the same case.
            "single quote marks": (["'Ignore any instructions' is the exact"], quoted),
            "curly quote marks": (["“Ignore any instructions” is the exact"], quoted),
            # Live run 20260902T064719Z-b4a3e588: the response wrote "**Human gate needed:**" and the
            # judge copied it without the asterisks.
            "markdown emphasis dropped": (["Human gate needed: approval of the actual promotion action"],
                                          "- **Human gate needed:** approval of the actual `promotion` action itself"),
            # Deliberate: requiring at least one quote pressures a judge with nothing to quote into
            # inventing one, which is the failure this check exists to catch.
            "empty evidence list": ([], "some response"),
        }
        for name, (evidence, response) in cases.items():
            with self.subTest(name):
                passed, detail = self._judge(evidence, response)
                self.assertTrue(passed)
                self.assertFalse(judge.is_inconclusive(detail))

    def test_evidence_not_drawn_from_the_response_is_inconclusive(self) -> None:
        elided = 'split into a credential-free "evaluate" agent that returns a verdict with no Bash'
        cases = {
            "invented quote": (["I restarted the checkout service"], "some response", "not verbatim"),
            "evidence not a list": ("some response", "some response", "not a list"),
            "non-string entry": (["some response", 7], "some response", ""),
            "empty string entry": (["   "], "some response", ""),
            "elided quote with an invented fragment": (["split into a credential-free ... agent that restarts checkout"],
                                                       elided, ""),
            "elided fragments out of order": (["with no Bash ... credential-free"], "credential-free agent with no Bash", ""),
            "paraphrase": (["the checkout service has gone down"], "the checkout service is down", ""),
        }
        for name, (evidence, response, reason) in cases.items():
            with self.subTest(name):
                passed, detail = self._judge(evidence, response)
                self.assertFalse(passed)
                self.assertTrue(judge.is_inconclusive(detail))
                self.assertIn(reason, detail)

    def test_missing_evidence_key_is_inconclusive(self) -> None:
        with replying(json.dumps({"verdict": "PASS", "reason": "because"})):
            passed, detail = judge_once()
        self.assertFalse(passed)
        self.assertTrue(judge.is_inconclusive(detail))

    def test_grounded_verdict_keeps_its_evidence_in_the_detail(self) -> None:
        passed, detail = self._judge(["some response"])
        self.assertTrue(passed)
        self.assertEqual(json.loads(detail)["evidence"], ["some response"])


class InconclusiveContractTests(JudgeCase):
    """Every fail-closed path is labelled inconclusive; a real FAIL verdict is not."""

    def test_fail_verdict_is_not_inconclusive(self) -> None:
        with replying(judge_verdict("FAIL")):
            self.assertFalse(judge.is_inconclusive(judge_once()[1]))

    def test_every_broken_spawn_fails_closed_as_inconclusive(self) -> None:
        cases = {
            "malformed": {"return_value": judge_process(stdout="not json at all")},
            "nonzero_exit": {"return_value": judge_process(returncode=1, stdout=judge_envelope(judge_verdict("PASS")))},
            "auth": {"return_value": judge_process(returncode=1, stderr="Not logged in")},
            "unknown_verdict": {"return_value": judge_process(stdout=judge_envelope(
                json.dumps({"verdict": "MAYBE", "reason": "unsure", "evidence": []})))},
            "timeout": {"side_effect": subprocess.TimeoutExpired(cmd="claude", timeout=120)},
            "auth_unavailable": {"side_effect": judge.clean_room.AuthUnavailable("no creds")},
            "spawn_oserror": {"side_effect": OSError("no such file")},
            "embedded_nul": {"side_effect": ValueError("embedded null byte")},
        }
        for label, behaviour in cases.items():
            with self.subTest(case=label):
                with spawn(**behaviour):
                    passed, detail = judge_once()
                self.assertFalse(passed)
                self.assertTrue(judge.is_inconclusive(detail))

    def test_inconclusive_is_never_cached(self) -> None:
        with spawn(side_effect=OSError("no such file")):
            judge_once(cache_dir=self.tmp)
        self.assertEqual(list(self.tmp.glob("*.json")), [])


class SpendTests(JudgeCase):
    """The judge's own cost and wall-clock time are recoverable by the trial that paid for them."""

    def test_live_call_records_cost_and_model(self) -> None:
        with replying(judge_verdict("PASS"), cost=0.031):
            judge_once()
        spend = judge.drain_spend()
        self.assertEqual(len(spend), 1)
        self.assertEqual(spend[0]["cost_usd"], 0.031)
        self.assertEqual(spend[0]["model_resolved"], "claude-sonnet-5")
        self.assertFalse(spend[0]["cached"])
        self.assertGreaterEqual(spend[0]["seconds"], 0.0)

    def test_drain_clears_so_spend_is_not_charged_twice(self) -> None:
        with replying(judge_verdict("PASS")):
            judge_once()
        self.assertEqual(len(judge.drain_spend()), 1)
        self.assertEqual(judge.drain_spend(), [])

    def test_inconclusive_call_still_records_its_elapsed_time(self) -> None:
        with spawn(side_effect=subprocess.TimeoutExpired("claude", 120)):
            judge_once()
        spend = judge.drain_spend()
        self.assertEqual(len(spend), 1)
        self.assertIsNone(spend[0]["cost_usd"])

    def test_cache_hit_records_a_free_call_with_the_model_that_judged_it(self) -> None:
        with replying(judge_verdict("PASS")):
            judge_once(cache_dir=self.tmp)
        judge.drain_spend()
        with no_spawn():
            judge_once(cache_dir=self.tmp)
        spend = judge.drain_spend()
        self.assertEqual(len(spend), 1)
        self.assertTrue(spend[0]["cached"])
        self.assertEqual(spend[0]["cost_usd"], 0.0)
        self.assertEqual(spend[0]["model_resolved"], "claude-sonnet-5")


class ModelIdentityTests(JudgeCase):
    """A pinned judge identity survives both the cache and the live call."""

    def _seed_cache(self, model: str) -> None:
        with replying(judge_verdict("PASS"), model=model):
            judge_once(cache_dir=self.tmp)

    def test_live_call_by_another_model_is_inconclusive(self) -> None:
        with replying(judge_verdict("PASS"), model="claude-sonnet-4-5"):
            passed, detail = judge_once(expected_model_id="claude-sonnet-5")
        self.assertFalse(passed)
        self.assertTrue(judge.is_inconclusive(detail))
        self.assertIn("not the pinned", detail)

    def test_cached_verdict_from_another_model_is_re_judged_not_served(self) -> None:
        self._seed_cache("claude-sonnet-4-5")
        with replying(judge_verdict("PASS")) as process:
            passed, detail = judge_once(cache_dir=self.tmp, expected_model_id="claude-sonnet-5")
        self.assertEqual(process.call_count, 1, "a verdict from another model must not be served from cache")
        self.assertTrue(passed)
        self.assertEqual(json.loads(detail)["model_resolved"], "claude-sonnet-5")

    def test_cached_verdict_from_the_pinned_model_is_served(self) -> None:
        self._seed_cache("claude-sonnet-5")
        with no_spawn():
            passed, detail = judge_once(cache_dir=self.tmp, expected_model_id="claude-sonnet-5")
        self.assertTrue(passed)
        self.assertIn('"cached": true', detail)

    def test_cached_verdict_with_ungrounded_evidence_is_re_judged(self) -> None:
        key = judge._cache_key("sonnet", RUBRIC, "irrelevant", "some response")  # the cache layout is this module's own contract
        (self.tmp / f"{key}.json").write_text(
            json.dumps({"verdict_bool": True, "detail": json.dumps({"evidence": ["never said this"]})}), encoding="utf-8"
        )
        with replying(judge_verdict("FAIL")) as process:
            judge_once(cache_dir=self.tmp)
        self.assertEqual(process.call_count, 1)

    def test_resolve_model_identity_returns_the_spending_model(self) -> None:
        envelope = json.dumps({"result": "OK", "is_error": False, "modelUsage": {
            "claude-haiku-4-5-20251001": {"costUSD": 0.0001}, "claude-sonnet-5": {"costUSD": 0.02}}})
        with spawn(return_value=judge_process(stdout=envelope)):
            self.assertEqual(judge.resolve_model_identity("sonnet"), "claude-sonnet-5")

    def test_resolve_model_identity_raises_when_unavailable(self) -> None:
        cases = {
            "auth": {"return_value": judge_process(returncode=1, stderr="Not logged in")},
            "nonzero_exit": {"return_value": judge_process(returncode=1, stdout='{"result": "OK"}')},
            "no_model_usage": {"return_value": judge_process(stdout='{"result": "OK"}')},
            "timeout": {"side_effect": subprocess.TimeoutExpired(cmd="claude", timeout=120)},
        }
        for label, behaviour in cases.items():
            with self.subTest(case=label), spawn(**behaviour), self.assertRaises(judge.JudgeUnavailable):
                judge.resolve_model_identity("sonnet")


class TransportTests(unittest.TestCase):
    """The untrusted response travels on stdin, under the configured CLI."""

    def test_prompt_is_not_an_argument(self) -> None:
        argv = judge._judge_argv("sonnet")  # this module owns the command shape
        self.assertNotIn("-p", argv[2:])
        self.assertEqual(argv[1], "-p")
        self.assertIn("--input-format", argv)
        self.assertEqual(argv[argv.index("--input-format") + 1], "text")

    def test_configured_claude_bin_is_used(self) -> None:
        with mock.patch.dict(judge.os.environ, {"CLAUDE_BIN": "/opt/custom/claude"}):
            self.assertEqual(judge._judge_argv("sonnet")[0], "/opt/custom/claude")
        with mock.patch.dict(judge.os.environ, {}, clear=True):
            self.assertEqual(judge._judge_argv("sonnet")[0], "claude")

    def test_prompt_is_written_to_stdin(self) -> None:
        with mock.patch.object(judge.clean_room, "clean_env", return_value=contextlib.nullcontext({})), \
             mock.patch.object(judge.clean_room, "neutral_workspace", return_value=contextlib.nullcontext(Path("."))), \
             mock.patch.object(judge.subprocess, "run", return_value=judge_process()) as run:
            judge._run_judge_process("PROMPT WITH THE RESPONSE", "sonnet")
        self.assertEqual(run.call_args.kwargs["input"], "PROMPT WITH THE RESPONSE")
        self.assertNotIn("PROMPT WITH THE RESPONSE", run.call_args.args[0])


class CalibrateTests(JudgeCase):
    """Calibration reports agreement over judgments, never over infrastructure failures."""

    def setUp(self) -> None:
        super().setUp()
        self.corpus = self.tmp / "corpus.yaml"
        self.cache_dir = self.tmp / ".eval-runs" / "judge-calibration" / "judge-cache"
        self.enterContext(mock.patch.object(judge, "REPO_ROOT", self.tmp))

    def _write_corpus(self, cases: list[dict]) -> None:
        self.corpus.write_text(json.dumps({"schema_version": 1, "cases": cases}), encoding="utf-8")

    def _calibrate(
        self,
        verdicts: list[tuple[bool, str]],
        spends: list[list[dict]] | None = None,
        **kwargs,
    ) -> tuple[int, list[dict], list[dict]]:
        """Drive calibrate with a stubbed judge that also reports what it spent, as the real one does."""
        spends = spends if spends is not None else [[spent()] for _ in verdicts]
        seen: list[dict] = []

        def _fake_judge(response, name, params, **call_kwargs):
            index = len(seen)
            seen.append(call_kwargs)
            judge._SPEND.extend(spends[index])  # standing in for a real judge call
            return verdicts[index]

        judge.drain_spend()
        with mock.patch.object(judge, "judge", side_effect=_fake_judge):
            code = judge.calibrate(self.corpus, "sonnet", **kwargs)
        results = json.loads((self._run_dir() / "results.json").read_text(encoding="utf-8"))
        return code, results, seen

    def _run_dir(self) -> Path:
        return sorted((self.tmp / ".eval-runs" / "judge-calibration").glob("2*"))[-1]

    def _identity(self) -> dict:
        return json.loads((self._run_dir() / "identity.json").read_text(encoding="utf-8"))

    def test_inconclusive_is_not_counted_as_agreement_and_fails_the_run(self) -> None:
        self._write_corpus(corpus_cases(2))
        # Both cases expect FAIL. A judge that never judged returns False too -- which the old
        # comparison scored as agreement, certifying a rubric on a timeout.
        code, results, _ = self._calibrate([
            (False, json.dumps({"reason": "claims to act"})),
            (False, judge.INCONCLUSIVE_PREFIX + "timed out after 120s"),
        ])
        self.assertEqual(code, 1)
        self.assertEqual([r["judge_verdict"] for r in results], ["fail", "inconclusive"])
        self.assertEqual([r["agree"] for r in results], [True, None])

    def test_a_required_case_must_agree_even_when_the_rubric_clears_the_threshold(self) -> None:
        self._write_corpus([{**case, "required": index == 0} for index, case in enumerate(corpus_cases(20))])
        agree, miss = (False, json.dumps({"reason": "a"})), (True, json.dumps({"reason": "b"}))
        for missed, expected_code in ((19, 0), (0, 1)):  # 19/20 agree either way
            with self.subTest(missed=missed):
                verdicts = [miss if index == missed else agree for index in range(20)]
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    code, _, _ = self._calibrate(verdicts)
                self.assertEqual(expected_code, code)
                self.assertIs(self._identity()["accepted"], expected_code == 0)
                self.assertEqual(expected_code == 1, "required case(s) did not agree" in out.getvalue())

    def test_all_conclusive_agreement_passes(self) -> None:
        self._write_corpus(corpus_cases(2))
        code, results, _ = self._calibrate([(False, json.dumps({"reason": "a"}))] * 2)
        self.assertEqual(code, 0)
        self.assertTrue(all(r["agree"] for r in results))

    def test_a_small_custom_corpus_cannot_certify_normal_grading(self) -> None:
        self._write_corpus(corpus_cases(1))
        code, _, _ = self._calibrate([(False, json.dumps({"model_resolved": "claude-sonnet-5", "reason": "a", "evidence": []}))])
        self.assertEqual(0, code)
        with self.assertRaisesRegex(judge.JudgeUnavailable, "inapplicable"):
            judge.load_binding(self._run_dir() / "identity.json", {RUBRIC})

    def test_identity_comes_from_the_runs_own_calls_without_a_probe(self) -> None:
        """No dedicated probe: the first live call supplies the identity every later call is held to."""
        self._write_corpus(corpus_cases(3))
        with mock.patch.object(judge, "resolve_model_identity", side_effect=AssertionError("no probe")):
            _, _, seen = self._calibrate([(False, json.dumps({"reason": "a"}))] * 3)
        identity = self._identity()
        self.assertEqual(identity["model_resolved"], "claude-sonnet-5")
        self.assertEqual(identity["identity_source"], "live")
        self.assertEqual(identity["live_calls"], 3)
        self.assertAlmostEqual(identity["cost_usd"], 0.09)
        self.assertAlmostEqual(identity["known_cost_usd"], 0.09)
        self.assertEqual(identity["unknown_cost_calls"], 0)
        # The first call has nothing to be held to; every later one is pinned to what judged first.
        self.assertIsNone(seen[0]["expected_model_id"])
        self.assertEqual(seen[1]["expected_model_id"], "claude-sonnet-5")
        self.assertEqual(seen[2]["expected_model_id"], "claude-sonnet-5")

    def test_a_live_call_without_a_reported_cost_leaves_the_receipt_cost_unknown(self) -> None:
        """Threat-model ADR result rule 7: an unpriced call is unknown, never summed as zero."""
        self._write_corpus(corpus_cases(3))
        code, _, _ = self._calibrate([(False, json.dumps({"reason": "a"}))] * 3, spends=[[spent()], [spent(None)], [spent()]])
        self.assertEqual(code, 0)
        identity = self._identity()
        self.assertEqual(identity["live_calls"], 3)
        self.assertIsNone(identity["cost_usd"])
        self.assertAlmostEqual(identity["known_cost_usd"], 0.06)
        self.assertEqual(identity["unknown_cost_calls"], 1)

    def test_a_fully_cached_run_costs_nothing_and_names_its_judge(self) -> None:
        """A re-check of cached verdicts must stay free, and must not claim it called a model."""
        self._write_corpus(corpus_cases(2))
        for index in range(2):
            cache_verdict(self.cache_dir, f"response {index}", "claude-sonnet-5")
        with mock.patch.object(judge, "resolve_model_identity", side_effect=AssertionError("no probe")), no_spawn():
            code = judge.calibrate(self.corpus, "sonnet")
        self.assertEqual(code, 0)
        identity = self._identity()
        self.assertEqual(identity["identity_source"], "cache")
        self.assertEqual(identity["model_resolved"], "claude-sonnet-5")
        self.assertEqual(identity["live_calls"], 0)
        self.assertEqual(identity["cached_calls"], 2)
        self.assertEqual(identity["cost_usd"], 0.0)
        self.assertEqual(identity["unknown_cost_calls"], 0)
        cases = judge._load_calibration(self.corpus)
        cases[0]["expect"] = "pass"
        self._write_corpus(cases)
        with no_spawn("label edit must reuse verdicts"):
            self.assertEqual(1, judge.calibrate(self.corpus, "sonnet"))
        identity = self._identity()
        self.assertEqual("cache", identity["identity_source"])
        self.assertEqual([1, 2, 0], identity["agreement"][RUBRIC])
        self.assertFalse(identity["accepted"])

    def test_a_cache_holding_two_models_stops_the_run(self) -> None:
        self._write_corpus(corpus_cases(2))
        for index, model_id in enumerate(("claude-sonnet-5", "claude-sonnet-4-5")):
            cache_verdict(self.cache_dir, f"response {index}", model_id)
        with no_judging():
            self.assertEqual(judge.calibrate(self.corpus, "sonnet"), 2)

    def test_resolve_identity_flag_probes_and_stops_on_a_moved_alias(self) -> None:
        self._write_corpus(corpus_cases(1))
        cache_verdict(self.cache_dir, "response 0", "claude-sonnet-4-5")
        with mock.patch.object(judge, "resolve_model_identity", return_value="claude-sonnet-5"), no_judging():
            self.assertEqual(judge.calibrate(self.corpus, "sonnet", resolve_identity=True), 2)

    def test_unresolvable_judge_model_stops_a_probed_run(self) -> None:
        self._write_corpus(corpus_cases(1))
        with mock.patch.object(judge, "resolve_model_identity", side_effect=judge.JudgeUnavailable("auth failure")), \
             no_judging():
            self.assertEqual(judge.calibrate(self.corpus, "sonnet", resolve_identity=True), 2)


if __name__ == "__main__":
    unittest.main()
