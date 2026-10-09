"""No-model tests for batches (evals/probe/batches.py, cli.py, records.py): aggregation and
thresholds, identity pooling, spend caps, exit codes and the v1 record contract.

Run directly: python evals/test_probe_batches.py
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import clean_room
from probe import batches as probe_batches
from probe import catalog as probe_catalog
from probe import cli as probe_cli
from probe import fingerprints as probe_fingerprints
from probe import layout as probe_layout
from probe import records as probe_records
from probe import rescoring as probe_rescoring
from probe import trials as probe_trials
from probe_testkit import (
    ReviewFindingTestCase,
    TempRootTestCase,
    all_scenarios,
    read_json,
    saved_grade,
    saved_summary,
    tiny_spec,
    write_saved_run,
)

ROOT = Path(__file__).resolve().parent.parent


class ReviewFindingTests(ReviewFindingTestCase):
    """The 2026-08-28 review findings on the probe, each pinned by the behaviour it asked for."""

    def test_trials_must_be_positive(self) -> None:
        for trials, message in (("0", "--trials must be at least 1"), ("two", "--trials must be a whole number")):
            with self.subTest(trials=trials), contextlib.redirect_stderr(io.StringIO()) as err, \
                    self.assertRaises(SystemExit) as refused:
                probe_cli.main(["--trials", trials, "--label", "x", "--out", str(self.root / "out")])
            self.assertEqual(3, refused.exception.code)
            self.assertIn(f"error: argument --trials: {message}", err.getvalue())
            self.assertFalse((self.root / "out").exists())

    def test_regrade_exit_code_separates_fail_inconclusive_and_nothing_regraded(self) -> None:
        """A run exits 1 on FAIL and 2 on INCONCLUSIVE; a regrade that graded nothing measured nothing."""
        for states, expected in (((), 2), (("PASS",), 0), (("PASS", "INCONCLUSIVE", "FAIL"), 1),
                                 (("PASS", "INCONCLUSIVE"), 2)):
            rows = [{"scenario": "s", "label": "l", "run": n, "status": state, "passed": 0, "total": 1,
                     "models": ["m"], "plugin_source_sha256": "0" * 64, "runtime": {"cli_version": "2.1.291 (Claude Code)", "host_platform": {"system": "Windows"}}}
                    for n, state in enumerate(states, 1)]
            with self.subTest(states=states), mock.patch.object(probe_rescoring, "regrade", return_value=rows):
                self.assertEqual(expected, probe_cli.main(["--regrade", str(self.root)]))

    def test_regrade_exit_code_aggregates_each_label_against_the_scenario_threshold(self) -> None:
        """Two of three trials pass a 0.66 scenario, as in a run; a failing arm is not pooled away."""
        scenario = "discovery-agent-authoring-loop-engineering"
        def row(label, n, state, model="claude-sonnet-5"):
            return {
            "scenario": scenario, "label": label, "run": n, "status": state, "passed": 0, "total": 1,
            "models": [model], "plugin_source_sha256": "0" * 64, "runtime": {"cli_version": "2.1.291 (Claude Code)", "host_platform": {"system": "Windows"}}}
        for rows, expected in (
            ([row("arm", 1, "PASS"), row("arm", 2, "PASS"), row("arm", 3, "FAIL")], 0),
            ([row("good", n, "PASS") for n in (1, 2, 3)] + [row("bad", n, "FAIL") for n in (1, 2, 3)], 1),
            # One label can hold runs from two resolved models; the failing model's arm is not pooled away.
            ([row("arm", 1, "PASS"), row("arm", 2, "PASS"), row("arm", 3, "FAIL", "claude-opus-5")], 1),
        ):
            with self.subTest(expected=expected), mock.patch.object(probe_rescoring, "regrade", return_value=rows):
                self.assertEqual(expected, probe_cli.main(["--regrade", str(self.root)]))

    def test_a_trial_that_raises_leaves_the_finished_trials_in_the_batch_summary(self) -> None:
        finished = {"scenario": "build-operator-cli-safe-requeue", "label": "l", "run": 1, "status": "PASS",
                    "passed": 1, "total": 1, "models": ["m"], "known_cost_usd": 0.0, "cost_complete": True}
        out = self.root / "it"
        with mock.patch.object(probe_trials, "run_trial", side_effect=[finished, RuntimeError("harness defect")]), \
                mock.patch.object(probe_batches, "batch_identity_problem", return_value=None), \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(RuntimeError, "harness defect"):
            probe_cli.main(["--scenario", "build-operator-cli-safe-requeue", "--label", "l", "--trials", "2",
                              "--out", str(out), "--executable", sys.executable])
        self.assertEqual([finished], read_json(out / "summary-l-default.json"))

    def test_overwrite_replaces_the_summary_entry(self) -> None:
        existing = [{"scenario": "tiny", "label": "new_skill", "run": 1, "status": "PASS"},
                    {"scenario": "tiny", "label": "new_skill", "run": 2, "status": "PASS"}]
        merged = probe_batches.merge_summary_entries(existing, [{"scenario": "tiny", "label": "new_skill", "run": 1, "status": "FAIL"}])
        self.assertEqual(2, len(merged))
        self.assertEqual({1: "FAIL", 2: "PASS"}, {e["run"]: e["status"] for e in merged})


class ThresholdAggregationTests(unittest.TestCase):
    def test_positive_threshold_is_honoured(self) -> None:
        spec = {"id": "p", "threshold": 0.66}
        self.assertEqual(0.66, probe_batches.effective_threshold(spec, None))
        self.assertEqual("PASS", probe_batches.aggregate_verdict(["PASS", "PASS", "FAIL"], 0.66))
        self.assertEqual("FAIL", probe_batches.aggregate_verdict(["PASS", "FAIL", "FAIL"], 0.66))

    def test_negative_routing_is_clamped_to_full(self) -> None:
        spec = {"id": "n", "routing": {"expect": "not_fire", "expected_alternative": "inline"},
                "target": {"kind": "skill", "name": "pcf-deploy"}}
        self.assertEqual(1.0, probe_batches.effective_threshold(spec, 0.5))
        self.assertEqual("FAIL", probe_batches.aggregate_verdict(["PASS", "PASS", "FAIL"], 1.0))

    def test_a_sub_full_threshold_on_a_negative_is_a_validation_error(self) -> None:
        spec = {"id": "n", "prompt": "unrelated words", "threshold": 0.5,
                "target": {"kind": "skill", "name": "pcf-deploy"},
                "routing": {"expect": "not_fire", "expected_alternative": "inline"}}
        problems = probe_catalog.validate_scenario(spec)
        self.assertTrue(any("zero-tolerance" in p for p in problems), problems)

    def test_inconclusive_short_of_the_bar_is_inconclusive_not_fail(self) -> None:
        self.assertEqual("INCONCLUSIVE", probe_batches.aggregate_verdict(["PASS", "INCONCLUSIVE"], 1.0))
        self.assertEqual("FAIL", probe_batches.aggregate_verdict(["FAIL", "FAIL"], 1.0))

    def test_aggregation_groups_by_scenario(self) -> None:
        scenarios = [{"id": "a", "threshold": 0.5}, {"id": "b"}]
        results = [
            {"scenario": "a", "status": "PASS"}, {"scenario": "a", "status": "FAIL"},
            {"scenario": "b", "status": "PASS"}, {"scenario": "b", "status": "FAIL"},
        ]
        verdicts = probe_batches.aggregate_by_scenario(scenarios, results, None)
        self.assertEqual("PASS", verdicts["a"]["verdict"])
        self.assertEqual("FAIL", verdicts["b"]["verdict"])


class BatchAggregationTests(TempRootTestCase):
    """Codex review of PR #222: the batch verdict must cover the batch, and one model identity."""

    SPEC = {"id": "batch-contract", "agent": "sre-assistant", "prompt": "p",
            "graders": [{"type": "contains_any", "of": ["x"]}]}

    TEMP_PREFIX = "build-probe-batch-"

    def setUp(self) -> None:
        super().setUp()
        self.out = self.root / "iteration"

    # One measured CLI and host, as a real batch records once; pooling needs it to match (EVAL-011).
    RUNTIME = {"cli_version": "2.1.291 (Claude Code)",
               "host_platform": {"system": "Windows", "release": "11", "machine": "AMD64"}}

    def _trial(self, run: int, status: str, model: str = "claude-sonnet-4-5") -> dict:
        return {"scenario": self.SPEC["id"], "label": "cand", "run": run, "status": status,
                "passed": 1 if status == "PASS" else 0, "total": 1, "models": [model],
                "tokens": 10, "seconds": 0.1, "plugin_commit": "0" * 12,
                "plugin_source_sha256": "0" * 64, "scenario_sha256": probe_fingerprints.scenario_digest(self.SPEC),
                "plugin_inputs_dirty": False, "isolation": "host", "runtime": self.RUNTIME}

    def _main(self, trials: list[dict], *extra: str, plugin_sha: str = "0" * 64,
              expected_calls: int | None = None, command: tuple[str, ...] = ()) -> tuple[int, str]:
        buffer = io.StringIO()
        with mock.patch.object(probe_catalog, "load_all_scenarios", return_value=[self.SPEC]), \
                mock.patch.object(probe_fingerprints, "plugin_provenance", return_value={"plugin_source_sha256": plugin_sha}), \
                mock.patch.object(probe_fingerprints, "runtime_identity", return_value=self.RUNTIME), \
                mock.patch.object(probe_trials, "run_trial", side_effect=trials) as runner, \
                contextlib.redirect_stdout(buffer):
            code = probe_cli.main([*command, "--scenario", self.SPEC["id"], "--label", "cand",
                                     "--out", str(self.out), "--trials", str(len(trials)), *extra])
        if expected_calls is not None:
            self.assertEqual(expected_calls, runner.call_count)
        return code, buffer.getvalue()

    def test_an_auth_stop_exits_4_whatever_rows_an_overwrite_had_not_replaced(self) -> None:
        """Copilot on PR #328: rows an --overwrite cut short had not replaced, of another candidate or
        model, made the batch INCONCLUSIVE (2), whose advice to overwrite hid the lost authentication."""
        seeded, _ = self._main([self._trial(1, "PASS"), self._trial(2, "PASS")])
        self.assertEqual(0, seeded)
        for sha, model in (("b" * 64, "claude-sonnet-4-5"), ("0" * 64, "claude-opus-4-1")):
            with self.subTest(candidate=sha[0], model=model):
                replacement = {**self._trial(1, "PASS", model), "plugin_source_sha256": sha}
                auth = clean_room.AuthUnavailable("Not logged in")
                code, output = self._main([replacement, auth], "--overwrite", plugin_sha=sha, expected_calls=2)
                self.assertEqual(4, code, output)
                self.assertIn("stopped after authentication unavailable: Not logged in", output)
                self.assertNotIn('"verdict"', output)
                self.assertNotIn("unfixed_by_resume", output, "resuming the overwrite replaces those rows")

    def test_a_regrade_pools_only_runs_of_one_identity(self) -> None:
        """Copilot and Codex on PR #328: a regrade's exit pooled a label's runs across candidates, CLIs,
        hosts and scenario identities, so a PASS from one and a FAIL from another passed a 0.5 scenario.
        A run whose candidate, CLI, host or model is unknown pools with nothing."""
        other_cli = {**self.RUNTIME, "cli_version": "2.1.300 (Claude Code)"}
        other_host = {**self.RUNTIME, "host_platform": {**self.RUNTIME["host_platform"], "system": "Linux"}}
        for index, (second, expected) in enumerate((
            ({}, 0),  # one arm: 1 of 2 trials meets 0.5
            ({"plugin_source_sha256": "b" * 64}, 1),
            ({"runtime": other_cli}, 1),
            ({"runtime": other_host}, 1),
            ({"scenario_sha256": "f" * 64}, 2),  # graded under another scenario identity: void, never pooled
            ({"runtime": None}, 2),
            ({"runtime": {"cli_version": self.RUNTIME["cli_version"]}}, 2),  # host unknown
            ({"plugin_source_sha256": None}, 2),
            ({"models": []}, 2),
        )):
            iteration = self.out / str(index)
            for run, text, identity in ((1, "x", {}), (2, "y", second)):
                grade = saved_grade(self.SPEC, [])
                grade["scenario_sha256"] = identity.get("scenario_sha256", grade["scenario_sha256"])
                write_saved_run(
                    iteration / "eval-batch-contract" / "cand" / f"run-{run}", response=text,
                    summary=saved_summary(models=identity.get("models", ["claude-sonnet-4-5"]),
                                          runtime=identity.get("runtime", self.RUNTIME),
                                          plugin={"plugin_source_sha256": identity.get("plugin_source_sha256", "0" * 64)}),
                    grading=grade)
            with self.subTest(second=second), \
                    mock.patch.object(probe_catalog, "load_all_scenarios", return_value=[self.SPEC]), \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                code = probe_cli.main(["regrade", str(iteration), "--threshold", "0.5"])
                self.assertEqual(expected, code, output.getvalue())
                rows = read_json(next(iteration.glob("regrade-*.json")))["runs"]
                self.assertEqual(second.get("runtime", self.RUNTIME), rows[1].get("runtime", "dropped"))

    def test_an_auth_stop_exits_4_beside_a_failed_trial(self) -> None:
        auth = clean_room.AuthUnavailable("Not logged in")
        code, output = self._main([self._trial(1, "FAIL"), auth], expected_calls=2)
        self.assertEqual(4, code, output)

    def test_an_auth_stop_names_what_a_resume_would_not_fix(self) -> None:
        # The append's own trial resolved another model, then authentication was lost: resuming
        # re-authenticates but cannot pool two models, so the stop line says so up front.
        seeded, _ = self._main([self._trial(1, "PASS")])
        self.assertEqual(0, seeded)
        auth = clean_room.AuthUnavailable("Not logged in")
        code, output = self._main([self._trial(2, "PASS", "claude-opus-4-1"), auth], "--run-offset", "1",
                                  expected_calls=2)
        self.assertEqual(4, code, output)
        stop = json.loads(next(line for line in output.splitlines() if "stopped after" in line))
        self.assertEqual("mixed resolved model identities", stop.get("unfixed_by_resume"))

    def test_an_appended_run_is_aggregated_with_the_batch_it_appends_to(self) -> None:
        """P1: a final one-trial --run-offset append reported PASS over an earlier FAIL."""
        first, _ = self._main([self._trial(1, "FAIL")])
        self.assertEqual(1, first)
        second, output = self._main([self._trial(2, "PASS")], "--run-offset", "1")
        self.assertEqual(1, second, "one PASS appended to one FAIL is not a passing batch")
        verdict = [json.loads(line) for line in output.splitlines() if line.startswith('{"scenario"')]
        self.assertEqual([{"scenario": "batch-contract", "verdict": "FAIL", "passed": 1,
                           "trials": 2, "threshold": 1.0}], verdict)

    def test_main_measures_the_runtime_once_and_passes_it_to_every_trial(self) -> None:
        runtime = {"cli_version": "9.9.9 (Claude Code)", "host_platform": {"system": "X", "release": "1", "machine": "y"}}
        trials = [self._trial(1, "PASS"), self._trial(2, "PASS")]
        buffer = io.StringIO()
        with mock.patch.object(probe_fingerprints, "runtime_identity", return_value=runtime) as probe, \
                mock.patch.object(probe_catalog, "load_all_scenarios", return_value=[self.SPEC]), \
                mock.patch.object(probe_fingerprints, "plugin_provenance", return_value={"plugin_source_sha256": "0" * 64}), \
                mock.patch.object(probe_trials, "run_trial", side_effect=trials) as runner, \
                contextlib.redirect_stdout(buffer):
            probe_cli.main(["--scenario", self.SPEC["id"], "--label", "cand", "--out", str(self.out), "--trials", "2"])
        self.assertEqual(1, probe.call_count, "one runtime identity per batch")
        self.assertEqual([runtime, runtime], [call.kwargs["settings"].runtime for call in runner.call_args_list])
        header = json.loads(buffer.getvalue().splitlines()[0])
        self.assertEqual(runtime, header["runtime"])

    def test_a_batch_that_resolved_two_models_is_inconclusive_not_aggregated(self) -> None:
        """P1: routing and behaviour are model-dependent; a mixed batch is not one measurement."""
        code, output = self._main([self._trial(1, "PASS"), self._trial(2, "PASS", "claude-opus-4-1")])
        self.assertEqual(2, code)
        self.assertIn("mixed resolved model identities", output)
        self.assertNotIn('"verdict": "PASS"', output)

    def test_one_resolved_model_still_aggregates(self) -> None:
        code, output = self._main([self._trial(1, "PASS"), self._trial(2, "PASS")])
        self.assertEqual(0, code)
        self.assertIn('"verdict": "PASS"', output)

    def test_different_candidate_cannot_inherit_an_existing_labels_passes(self) -> None:
        self._main([self._trial(1, "PASS"), self._trial(2, "PASS")])
        changed = self._trial(3, "FAIL")
        changed["plugin_source_sha256"] = "b" * 64
        code, output = self._main([changed], "--run-offset", "2", "--threshold", "0.66",
                                  "--expect-plugin-digest", "b" * 64, plugin_sha="b" * 64, expected_calls=0)
        self.assertEqual(2, code, output)
        self.assertNotIn('"verdict": "PASS"', output)

    def test_changed_scenario_cannot_reuse_an_existing_labels_trials(self) -> None:
        self._main([self._trial(1, "PASS")])
        with mock.patch.dict(self.SPEC, {"prompt": "a different task"}):
            code, output = self._main([self._trial(2, "PASS")], "--run-offset", "1", expected_calls=0)
        self.assertEqual(2, code, output)
        self.assertNotIn('"verdict": "PASS"', output)

    def test_legacy_batch_is_rejected_before_spending_but_complete_overwrite_is_allowed(self) -> None:
        self._main([self._trial(1, "PASS")])
        path = self.out / "summary-cand-default.json"
        legacy = read_json(path)
        legacy[0]["plugin_source_sha256"] = "0" * 12
        legacy[0].pop("scenario_sha256")
        path.write_text(json.dumps(legacy), encoding="utf-8")
        code, _ = self._main([self._trial(2, "PASS")], "--run-offset", "1", expected_calls=0)
        self.assertEqual(2, code)
        code, _ = self._main([self._trial(1, "PASS")], "--overwrite", expected_calls=1)
        self.assertEqual(0, code)

    def test_an_out_of_range_threshold_is_refused(self) -> None:
        """P2: --threshold 0 made `required` zero and reported PASS for a batch where everything failed."""
        for bad in ("0", "-1", "1.5", "nan"):
            with self.assertRaises(SystemExit, msg=bad):
                self._main([self._trial(1, "PASS")], "--threshold", bad)
        code, _ = self._main([self._trial(1, "PASS")], "--threshold", "0.5")
        self.assertEqual(0, code)

    def test_a_usage_error_exits_3_not_inconclusive_2(self) -> None:
        """Exit 2 means an INCONCLUSIVE batch; a command line the runner refuses is exit 3, in both forms."""
        for argv in (["--no-such-flag"], ["run", "--no-such-flag"], ["regrade"], ["no-such-scenario-dir", "--x"]):
            with (
                self.subTest(argv=argv),
                contextlib.redirect_stderr(io.StringIO()) as err,
                self.assertRaises(SystemExit) as refused,
            ):
                probe_cli.main(argv)
            self.assertEqual(3, refused.exception.code, err.getvalue())
            self.assertIn("error:", err.getvalue())
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as helped:
            probe_cli.main(["--help"])
        self.assertEqual(0, helped.exception.code)

    def test_a_negative_run_offset_is_refused_before_any_trial(self) -> None:
        """Codex P2 on PR #328: `--run-offset -1` published the trial as `run-0`, a slot the v1 record
        refuses, while the batch summary still counted its verdict."""
        for command in ((), ("run",)):  # the flat flags and the `run` subcommand share `_run_options`
            with contextlib.redirect_stderr(io.StringIO()) as err, \
                    self.assertRaises(SystemExit, msg=command) as refused:
                self._main([self._trial(0, "PASS")], "--run-offset", "-1", command=command)
            self.assertEqual(3, refused.exception.code, command)  # refused: bad input, not INCONCLUSIVE
            self.assertIn("error: argument --run-offset: --run-offset must be at least 0", err.getvalue())
            self.assertFalse(self.out.exists(), "refused before any trial ran or a summary was written")
        code, _ = self._main([self._trial(1, "PASS")], "--run-offset", "0", expected_calls=1)
        self.assertEqual(0, code)


class JudgeSpendAccountingTests(unittest.TestCase):
    """Codex review of PR #222: a rubric grader spends a paid call the trial's own trace never sees."""

    def test_drained_judge_calls_are_added_to_the_trial_cost_and_duration(self) -> None:
        stub = types.SimpleNamespace(drain_spend=lambda: [
            {"cost_usd": 0.02, "seconds": 3.5, "cached": False, "model_resolved": "claude-sonnet-4-5"},
            {"cost_usd": 0.01, "seconds": 1.5, "cached": False, "model_resolved": "claude-sonnet-4-5"},
        ])
        with mock.patch.dict(sys.modules, {"judge": stub}):
            spend = probe_records.judge_spend()
        self.assertEqual(2, spend["calls"])
        self.assertAlmostEqual(0.03, spend["cost_usd"])
        self.assertAlmostEqual(5.0, spend["seconds"])

    def test_no_judge_module_means_no_spend(self) -> None:
        with mock.patch.dict(sys.modules, {}, clear=False):
            sys.modules.pop("judge", None)
            self.assertEqual({"calls": 0, "cost_usd": 0.0, "known_cost_usd": 0, "unknown_cost_calls": 0,
                              "live_calls": 0, "cached_calls": 0, "seconds": 0.0},
                             probe_records.judge_spend())

    def test_live_and_cached_judge_calls_are_counted_apart(self) -> None:
        fake_judge = mock.Mock(drain_spend=lambda: [{"cost_usd": 0.02, "seconds": 1.0, "cached": False},
                                                    {"cost_usd": 0.0, "seconds": 0.0, "cached": True}])
        with mock.patch.dict(sys.modules, {"judge": fake_judge}):
            spend = probe_records.judge_spend()
        self.assertEqual((1, 1), (spend["live_calls"], spend["cached_calls"]))


class RunnerIdentityTests(unittest.TestCase):
    """EVAL-011 identity: results name the runner, never pool CLI versions or hosts, and measure every hook."""

    RUNTIME = {"cli_version": "2.1.291", "host_platform": {"system": "Windows", "release": "11", "machine": "AMD64"}}

    def test_runner_provenance_names_this_checkout_and_its_source_digest(self) -> None:
        runner = probe_fingerprints.runner_provenance()
        self.assertEqual(probe_fingerprints.HARNESS_SOURCE_SHA256, runner["runner_source_sha256"])
        self.assertRegex(runner["runner_commit"] or "", r"^[0-9a-f]{40}$")
        self.assertIn(runner["runner_source_dirty"], (True, False))

    def test_trials_from_another_cli_version_or_host_never_pool(self) -> None:
        entry = {"scenario": "tiny", "plugin_source_sha256": "p", "runtime": self.RUNTIME,
                 "scenario_sha256": probe_fingerprints.scenario_digest(tiny_spec())}
        self.assertIsNone(probe_batches.batch_identity_problem([entry], [tiny_spec()], "p", None, self.RUNTIME))
        newer = {**self.RUNTIME, "cli_version": "2.1.292"}
        self.assertIn("CLI version or host", probe_batches.batch_identity_problem([entry], [tiny_spec()], "p", None, newer))
        legacy = {key: value for key, value in entry.items() if key != "runtime"}
        self.assertIn("CLI version or host",
                      probe_batches.batch_identity_problem([legacy], [tiny_spec()], "p", None, self.RUNTIME))

    def test_the_powershell_guard_hook_is_part_of_the_measured_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp)
            for relative in (*probe_fingerprints.PLUGIN_INPUT_PATHS, *probe_fingerprints.OPTIONAL_PLUGIN_INPUT_PATHS):
                source, target = ROOT / relative, plugin / relative
                if source.is_dir():
                    shutil.copytree(source, target)
                elif source.is_file():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(source.read_bytes())
            before = probe_fingerprints.plugin_digest(plugin)
            hook = plugin / "scripts" / "readonly-guard-hook.ps1"
            hook.write_bytes(hook.read_bytes() + b"\n# changed\n")
            self.assertNotEqual(before, probe_fingerprints.plugin_digest(plugin))

    def test_an_unknown_cli_version_refuses_the_batch(self) -> None:
        runtime = {"cli_version": None, "host_platform": {"system": "Windows", "release": "11", "machine": "AMD64"}}
        self.assertIn("did not report its version", probe_batches.batch_identity_problem([], [tiny_spec()], "p", None, runtime))


class UnknownCostTests(unittest.TestCase):
    """EVAL-011 attempts and cost: an unknown cost is recorded as unknown, never as zero."""

    def test_an_unpriced_live_judge_call_leaves_the_judge_cost_unknown(self) -> None:
        fake_judge = mock.Mock(drain_spend=lambda: [{"cost_usd": 0.02, "seconds": 1.0, "cached": False},
                                                    {"cost_usd": None, "seconds": 1.0, "cached": False},
                                                    {"cost_usd": 0.0, "seconds": 0.0, "cached": True}])
        with mock.patch.dict(sys.modules, {"judge": fake_judge}):
            spend = probe_records.judge_spend()
        self.assertIsNone(spend["cost_usd"])
        self.assertEqual((0.02, 1), (spend["known_cost_usd"], spend["unknown_cost_calls"]))

    def test_a_trial_total_is_unknown_when_any_part_is(self) -> None:
        known = {"cost_usd": 0.03, "known_cost_usd": 0.03}
        unknown = {"cost_usd": None, "known_cost_usd": 0.02}
        self.assertEqual({"cost_usd": 0.13, "known_cost_usd": 0.13, "cost_complete": True}, probe_records.trial_cost(0.1, known))
        self.assertEqual({"cost_usd": None, "known_cost_usd": 0.03, "cost_complete": False}, probe_records.trial_cost(None, known))
        self.assertEqual({"cost_usd": None, "known_cost_usd": 0.12, "cost_complete": False}, probe_records.trial_cost(0.1, unknown))

    def test_invalid_reported_costs_are_unknown(self) -> None:
        for bad in (float("nan"), float("inf"), -0.01, "0.1", True):
            with self.subTest(bad=bad):
                self.assertIsNone(probe_records.known_usd(bad))
        judge_cost = {"cost_usd": 0.0, "known_cost_usd": 0.0}
        self.assertEqual({"cost_usd": None, "known_cost_usd": 0.0, "cost_complete": False},
                         probe_records.trial_cost(float("nan"), judge_cost))
        spend = mock.Mock(drain_spend=lambda: [{"cost_usd": -1.0, "seconds": 1.0, "cached": False}])
        with mock.patch.dict(sys.modules, {"judge": spend}):
            self.assertIsNone(probe_records.judge_spend()["cost_usd"])


# A measured runtime a batch accepts: one CLI version and host, as a real batch records once.
STUB_RUNTIME = {"cli_version": "x", "host_platform": {"system": "Windows", "release": "11", "machine": "AMD64"}}


class BatchSpendCapTests(unittest.TestCase):
    """AC-18: the batch cap stops scheduling at the known spend, or when a cost is unknown."""

    RUNTIME = STUB_RUNTIME

    def test_kept_attempts_count_only_toward_the_model_that_ran_them(self) -> None:
        """The batch summary is per label and model, but a label's kept attempts are shared: a capped
        sonnet batch counted the opus attempts beside it. An attempt whose model is unreadable counts."""
        with tempfile.TemporaryDirectory() as tmp:
            kept = probe_layout.attempts_dir(Path(tmp) / "eval-tiny" / "l") / "run-1"
            for number, timing, record in (
                ("1", {"requested_model": "opus", "known_cost_usd": 0.9, "cost_complete": True}, None),
                ("2", {"requested_model": "sonnet", "known_cost_usd": 0.2, "cost_complete": True}, None),
                ("3", {"known_cost_usd": 0.0, "cost_complete": True}, {"conditions": {"requested_model": "opus"}}),
                ("4", {"known_cost_usd": 0.0, "cost_complete": True}, {"conditions": {"requested_model": None}}),
                ("5", None, None),
            ):
                (kept / number).mkdir(parents=True)
                if timing is not None:
                    (kept / number / "timing.json").write_text(json.dumps(timing), encoding="utf-8")
                if record is not None:
                    (kept / number / "record.json").write_text(json.dumps(record), encoding="utf-8")
            costs = {model: probe_trials.kept_attempt_costs(Path(tmp), "l", ["tiny"], model)
                     for model in ("sonnet", "opus", None)}
        unknown = {"cost_complete": False}
        self.assertEqual([0.2], [c["known_cost_usd"] for c in costs["sonnet"] if c != unknown])
        self.assertEqual([0.9, 0.0], [c["known_cost_usd"] for c in costs["opus"] if c != unknown])
        self.assertEqual([0.0], [c["known_cost_usd"] for c in costs[None] if c != unknown])
        self.assertTrue(all(unknown in found for found in costs.values()), "an unreadable attempt counts for every model")

    def test_a_malformed_attempt_model_never_hides_a_paid_attempt(self) -> None:
        """Copilot on PR #329: a `requested_model` that is neither a string nor null was taken as a
        model no batch runs, so the paid attempt counted toward none and the cap understated spend."""
        with tempfile.TemporaryDirectory() as tmp:
            kept = probe_layout.attempts_dir(Path(tmp) / "eval-tiny" / "l") / "run-1"
            for number, model, record in (("1", [], {"conditions": {"requested_model": "sonnet"}}), ("2", 5, None)):
                (kept / number).mkdir(parents=True)
                timing = {"requested_model": model, "known_cost_usd": 0.4, "cost_complete": True}
                (kept / number / "timing.json").write_text(json.dumps(timing), encoding="utf-8")
                if record is not None:
                    (kept / number / "record.json").write_text(json.dumps(record), encoding="utf-8")
            counted = {model: len(probe_trials.kept_attempt_costs(Path(tmp), "l", ["tiny"], model))
                       for model in ("sonnet", "opus", None)}
        self.assertEqual({"sonnet": 2, "opus": 1, None: 1}, counted, "the record names the first; the second is unknown")

    def _main(self, costs: list[tuple[float | None, bool]], cap: str) -> tuple[int, list[int], str]:
        spec = all_scenarios()[0]
        calls: list[int] = []

        def fake_run_trial(spec_arg, **kwargs):
            calls.append(kwargs["run_number"])
            known, complete = costs[len(calls) - 1]
            return {"scenario": spec_arg["id"], "label": "l", "run": kwargs["run_number"], "status": "PASS",
                    "passed": 1, "total": 1, "models": ["m"], "runtime": self.RUNTIME,
                    "plugin_source_sha256": "0" * 64, "scenario_sha256": probe_fingerprints.scenario_digest(spec_arg),
                    "cost_usd": known if complete else None, "known_cost_usd": known, "cost_complete": complete}

        with tempfile.TemporaryDirectory() as tmp,                 mock.patch.object(probe_fingerprints, "plugin_provenance", return_value={"plugin_source_sha256": "0" * 64}),                 mock.patch.object(probe_fingerprints, "runtime_identity", return_value=self.RUNTIME),                 mock.patch.object(probe_trials, "run_trial", side_effect=fake_run_trial),                 contextlib.redirect_stdout(io.StringIO()) as out:
            code = probe_cli.main(["--scenario", spec["id"], "--label", "l", "--trials", str(len(costs)),
                                     "--out", str(Path(tmp) / "it"), "--max-batch-usd", cap])
        return code, calls, out.getvalue()

    def test_scheduling_stops_once_the_known_spend_reaches_the_cap(self) -> None:
        code, calls, out = self._main([(0.6, True), (0.6, True), (0.6, True)], "1.0")
        self.assertEqual([1, 2], calls)
        self.assertEqual(2, code)
        self.assertIn('"trials_not_run": 1', out)

    def test_an_unknown_cost_stops_the_batch_because_the_cap_cannot_hold(self) -> None:
        _code, calls, out = self._main([(0.1, False), (0.1, True)], "20")
        self.assertEqual([1], calls)
        self.assertIn("cap cannot be enforced", out)

    def test_the_batch_cap_must_be_finite_and_non_negative(self) -> None:
        for bad in ("nan", "inf", "-1", "abc"):
            with self.subTest(bad=bad), self.assertRaises(argparse.ArgumentTypeError):
                probe_cli._budget(bad)
        self.assertEqual(20.0, probe_cli._budget("20"))
        with self.assertRaises(argparse.ArgumentTypeError):
            probe_cli._budget("0")  # a zero cap would schedule nothing; a cap must be positive

    def test_a_resumed_batch_counts_what_its_retained_trials_spent(self) -> None:
        runtime = {"cli_version": "x", "host_platform": {"system": "Windows", "release": "11", "machine": "AMD64"}}
        spec = next(s for s in all_scenarios() if not probe_fingerprints.required_rubrics(s)
                    and not (s.get("fixture") or {}).get("services") and not s.get("followups"))
        def row(run, known, complete):
            return {
            "scenario": spec["id"], "label": "l", "run": run, "status": "PASS", "passed": 1, "total": 1,
            "models": ["m"], "runtime": runtime, "plugin_source_sha256": "0" * 64,
            "scenario_sha256": probe_fingerprints.scenario_digest(spec), "known_cost_usd": known, "cost_complete": complete}
        for retained, expected_calls in (((0.9, True), [2]), ((0.0, False), [])):
            calls: list[int] = []

            def fake_run_trial(spec_arg, **kwargs):
                calls.append(kwargs["run_number"])  # noqa: B023 -- called within this iteration
                return row(kwargs["run_number"], 0.2, True)

            with (
                self.subTest(retained=retained),
                tempfile.TemporaryDirectory() as tmp,
                mock.patch.object(probe_catalog, "load_all_scenarios", return_value=[spec]),
                mock.patch.object(probe_fingerprints, "plugin_provenance", return_value={"plugin_source_sha256": "0" * 64}),
                mock.patch.object(probe_fingerprints, "runtime_identity", return_value=runtime),
                mock.patch.object(probe_trials, "run_trial", side_effect=fake_run_trial),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                out = Path(tmp) / "it"
                out.mkdir()
                (out / "summary-l-default.json").write_text(json.dumps([row(1, *retained)]), encoding="utf-8")
                probe_cli.main(["--scenario", spec["id"], "--label", "l", "--trials", "2", "--run-offset", "1",
                                  "--out", str(out), "--max-batch-usd", "1.0"])
            self.assertEqual(expected_calls, calls)


class SpendCapAttemptTests(TempRootTestCase):
    """Copilot and Codex on PR #328: the cap counts every attempt the label paid for, once (rule 7).

    The real run_trial publishes and keeps the attempts; only the trial itself is stubbed.
    """

    RUNTIME = STUB_RUNTIME

    TEMP_PREFIX = "build-probe-cap-"

    def setUp(self) -> None:
        super().setUp()
        self.out = self.root / "it"
        self.spec = all_scenarios()[0]

    def _start_over(self) -> None:
        """Send the next batches to an output folder no earlier batch in this test has written."""
        self.out = Path(tempfile.mkdtemp(dir=self.root)) / "it"

    def _main(self, steps: list, *extra: str, plugin_sha: str = "0" * 64) -> tuple[int, int, str]:
        """Each step is a graded trial's cost (None: unknown) or (exception, partial trace or None)."""
        calls: list[int] = []

        def fake_run_trial(spec, run_number, run_out, settings):
            step = steps[len(calls)]
            calls.append(run_number)
            if isinstance(step, tuple):
                exc, trace = step
                if trace is not None:
                    (run_out / "stdout.jsonl").write_text(trace, encoding="utf-8")
                raise exc
            cost = {"known_cost_usd": step or 0.0, "cost_complete": step is not None}
            (run_out / "timing.json").write_text(json.dumps(cost), encoding="utf-8")
            return {"scenario": spec["id"], "label": settings.label, "run": run_number, "status": "PASS", "passed": 1,
                    "total": 1, "models": ["m"], "runtime": self.RUNTIME, "plugin_source_sha256": "0" * 64,
                    "scenario_sha256": probe_fingerprints.scenario_digest(spec), **cost}

        with mock.patch.object(probe_fingerprints, "plugin_provenance", return_value={"plugin_source_sha256": plugin_sha}), \
                mock.patch.object(probe_fingerprints, "runtime_identity", return_value=self.RUNTIME), \
                mock.patch.object(probe_trials, "_run_trial", side_effect=fake_run_trial), \
                mock.patch.object(probe_records, "write_record"), \
                contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
            code = probe_cli.main(["--scenario", self.spec["id"], "--label", "l", "--trials", str(len(steps)),
                                     "--out", str(self.out), *extra])
        return code, len(calls), out.getvalue()

    def test_a_replaced_and_a_superseded_attempt_still_count(self) -> None:
        self._main([0.9])
        code, calls, out = self._main([0.2, 0.2], "--overwrite", "--max-batch-usd", "1")
        self.assertEqual((2, 1), (code, calls), "run 1's USD 0.90 leaves room for one more trial")
        self.assertIn("reached the USD 1 cap", out)
        self._start_over()
        self._main([0.3])
        self._main([0.4], "--overwrite")  # the USD 0.30 attempt is now kept as superseded
        code, calls, out = self._main([0.35, 0.35], "--run-offset", "1", "--max-batch-usd", "1")
        self.assertEqual((2, 1), (code, calls), "USD 0.40 published and 0.30 superseded: room for one more")

    def test_an_attempt_that_raised_counts_what_it_is_known_to_have_cost(self) -> None:
        auth = clean_room.AuthUnavailable("Not logged in")
        priced = '{"type": "result", "subtype": "success", "is_error": false, "total_cost_usd": 0.9}\n'
        for name, trace, capped_calls in (("no CLI process started", None, 2),
                                          ("a partial trace that reports its cost", priced, 1),
                                          ("a partial trace without a cost", "", 0)):
            with self.subTest(name):
                self._start_over()
                self.assertEqual(4, self._main([(auth, trace)])[0])
                _code, calls, out = self._main([0.2, 0.2], "--run-offset", "1", "--max-batch-usd", "1")
                self.assertEqual(capped_calls, calls, out)
                if not capped_calls:
                    self.assertIn("an earlier attempt's cost is unknown", out)

    def test_a_cap_stop_stays_visible_beside_an_identity_refusal(self) -> None:
        self._main([None])  # a trial of unknown cost
        code, calls, out = self._main([0.2], "--overwrite", "--max-batch-usd", "1", plugin_sha="b" * 64)
        self.assertEqual((2, 0), (code, calls))
        self.assertIn("candidate digest", out)
        self.assertIn("an earlier attempt's cost is unknown", out)


class AuthStopsTheBatchTests(unittest.TestCase):
    """An authentication failure exits 4 and stops the batch; completed trials are still reported."""

    def test_an_auth_failure_stops_scheduling_and_exits_distinctly(self) -> None:
        runtime = {"cli_version": "x", "host_platform": {"system": "Windows", "release": "11", "machine": "AMD64"}}
        spec = all_scenarios()[0]
        calls: list[int] = []

        def fake_run_trial(spec_arg, **kwargs):
            calls.append(kwargs["run_number"])
            if len(calls) == 2:
                raise clean_room.AuthUnavailable("Not logged in")
            return {"scenario": spec_arg["id"], "label": "l", "run": kwargs["run_number"], "status": "PASS",
                    "passed": 1, "total": 1, "models": ["m"], "runtime": runtime,
                    "plugin_source_sha256": "0" * 64, "scenario_sha256": probe_fingerprints.scenario_digest(spec_arg)}

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(probe_fingerprints, "plugin_provenance", return_value={"plugin_source_sha256": "0" * 64}), \
                mock.patch.object(probe_fingerprints, "runtime_identity", return_value=runtime), \
                mock.patch.object(probe_trials, "run_trial", side_effect=fake_run_trial), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            code = probe_cli.main(["--scenario", spec["id"], "--label", "l", "--trials", "3",
                                     "--out", str(Path(tmp) / "it")])
        self.assertEqual((4, [1, 2]), (code, calls))
        self.assertIn("authentication unavailable", out.getvalue())
        self.assertIn('"trials_not_run": 2', out.getvalue())


class RecordContractTests(unittest.TestCase):
    """The v1 record refuses what its contract rules out, on the first write and on every later change."""

    START = "2026-10-06T12:00:00+00:00"
    GRADING = {"status": "FAIL", "inconclusive": None, "unmeasured": "judge down", "scenario_sha256": "a" * 64,
               "expectations": [
                   {"id": "x:0", "text": "never deploys", "kind": "forbids", "passed": False, "state": "FAIL",
                    "evidence": "deployed"},
                   {"id": "x:1", "text": "judged", "kind": "requires", "passed": False, "state": "INCONCLUSIVE",
                    "evidence": "INCONCLUSIVE: judge down"}]}

    def _record(self, run: Path, **kwargs: object) -> dict:
        (run / "grading.json").write_text(json.dumps(self.GRADING), encoding="utf-8")
        return probe_records.write_record(run, tiny_spec(), label="l", run_number=1, attempt=1, started_at=self.START,
                                        model=None, timeout=60, **kwargs)

    def test_a_check_says_why_it_could_not_measure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            record = self._record(Path(tmp))
        self.assertEqual([None, "judge down"], [check["reason"] for check in record["checks"]])
        self.assertEqual(("FAIL", "judge down"), (record["verdict"]["status"], record["verdict"]["reason"]))

    def test_an_incomplete_attempt_has_no_verdict_even_beside_a_grade(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            record = self._record(Path(tmp), incomplete="KeyboardInterrupt: ")
        self.assertEqual(("incomplete", "incomplete", None, None),
                         (record["attempt"]["state"], record["run_end"]["kind"], record["verdict"]["status"],
                          record["verdict"]["reason"]))

    def test_the_contract_refuses_what_it_rules_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            valid = self._record(Path(tmp))
        self.assertEqual(valid, probe_records.RecordV1.model_validate_json(json.dumps(valid)).model_dump(
            mode="json", exclude_unset=True))

        def broken(path: str, value: object) -> dict:
            record = json.loads(json.dumps(valid))
            *parents, leaf = path.split(".")
            target = record
            for part in parents:
                target = target[int(part)] if part.isdigit() else target[part]
            target[leaf] = value
            return record

        for path, value in (
                ("attempt.state", "incomplete"),  # an incomplete attempt that still carries a verdict
                ("verdict.status", None),  # a final attempt without one
                ("cost.trial_usd", -3.0),
                ("cost.complete", True),  # complete while both costs are unknown
                ("verdict.assessment_revision", 7),
                ("attempt.started_at", "yesterday"),
                ("attempt.slot", True),  # strict: a bool is not a number
                ("checks.0.evidence", "x" * 601),  # longer than the record keeps
                ("checks.1.reason", None),  # an INCONCLUSIVE check that does not say why
                ("checks.0.passed", False),  # a field the contract does not define
                ("run_end.stop", "wall_clock"),  # a stop on a run that was not cut short
                ("evidence.../../etc/passwd", "stdout.jsonl"),
                ("evidence.grading.json", "/abs/grading.json")):
            if path.startswith("evidence."):
                record = json.loads(json.dumps(valid))
                record["evidence"][path.removeprefix("evidence.")] = value
            else:
                record = broken(path, value)
            with self.subTest(path=path, value=value), self.assertRaises(ValueError):
                probe_records.RecordV1.model_validate_json(json.dumps(record))

    def test_a_later_change_passes_the_same_validation_or_is_left_unwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            self._record(run)
            probe_records.update_record(
                run, lambda record: record["attempt"].update(state="superseded", reason="replaced by attempt 2"))
            before = (run / "record.json").read_text(encoding="utf-8")
            self.assertEqual("superseded", json.loads(before)["attempt"]["state"])
            with contextlib.redirect_stderr(io.StringIO()) as err:
                probe_records.update_record(run, lambda record: record.setdefault("assessments", []).append(
                    {"revision": 3, "status": "PASS"}))
            self.assertEqual(before, (run / "record.json").read_text(encoding="utf-8"))
        self.assertIn("was not updated", err.getvalue())

    def test_a_judge_total_is_a_float_even_without_a_call(self) -> None:
        with mock.patch.dict(sys.modules, {"judge": mock.Mock(drain_spend=lambda: [])}):
            spend = probe_records.judge_spend()
        self.assertEqual((0.0, float), (spend["cost_usd"], type(spend["cost_usd"])))

    def test_the_record_carries_how_execution_stopped_not_what_the_checks_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            for grading, kind, stop in (
                    ({"status": "INCONCLUSIVE", "inconclusive": "grader error: boom",
                      "expectations": [{"id": "x:0", "text": "graded", "kind": "requires", "passed": False,
                                        "state": "INCONCLUSIVE", "evidence": "INCONCLUSIVE: grader error: boom"}]},
                     "completed", None),
                    ({"status": "INCONCLUSIVE", "void": "wrong plugin", "inconclusive": "wrong plugin"}, "void", None),
                    ({"status": "FAIL", "run_end": "cut_short", "run_stop": "spend_guard", "unmeasured": "cap"},
                     "cut_short", "spend_guard")):
                (run / "grading.json").write_text(json.dumps(grading), encoding="utf-8")
                record = probe_records.write_record(run, tiny_spec(), label="l", run_number=1, attempt=1,
                                                  started_at=RecordContractTests.START, model=None, timeout=60)
                with self.subTest(kind=kind):
                    self.assertEqual((kind, stop), (record["run_end"]["kind"], record["run_end"]["stop"]))


if __name__ == "__main__":
    unittest.main()
