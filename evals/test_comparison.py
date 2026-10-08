"""The WP-01 comparison over v1 records, on the committed synthetic bundle (EVAL-012 AC-01/02/17/19/23).

The bundle (evals/fixtures/v1-bundle, written by its generate.py) holds an incumbent and a candidate
label over twenty synthetic cases, one behavior each, named for it: verdict pairs, a native 0.66
threshold, replaced and raised attempts, missing, legacy and recordless runs, an arm that stopped
early, an unpublished folder, unusable and misfiled records, and arms that differ in case, model,
runner, CLI or candidate. CI runs these tests on Linux and the owner's host runs them on Windows over
the same bytes, against one committed expected report.
"""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import compare_runs as comparison
from probe import catalog

BUNDLE = Path(__file__).resolve().parent / "fixtures" / "v1-bundle"
RUNS = BUNDLE / "runs"
COST_FIELDS = ("trial_usd", "judge_usd", "known_usd", "complete")


def report_for(runs: Path, scenarios: list[dict] | None = None) -> dict:
    if scenarios is None:
        scenarios = catalog.load_all_scenarios(BUNDLE / "scenarios")
    # Through JSON, as a reader of the printed report sees it.
    return json.loads(json.dumps(comparison.compare_bundle(runs, "incumbent", "candidate", scenarios)))


def case(report: dict, case_id: str) -> dict:
    return next(c for c in report["cases"] if c["case"] == case_id)


def problems(report: dict, case_id: str) -> list[tuple[str, str]]:
    prefix = f"eval-{case_id}/"
    return [(p["folder"].removeprefix(prefix), p["problem"]) for p in report["problems"] if p["folder"].startswith(prefix)]


class ComparisonTests(unittest.TestCase):
    report: dict

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = report_for(RUNS)

    def test_pairs_are_classified_by_native_verdicts(self) -> None:
        outcomes = {c["case"]: (c["outcome"], c["reason"]) for c in self.report["cases"]}
        self.assertEqual(
            {
                "synthetic-gain": ("gain", None),
                "synthetic-regression": ("regression", None),
                "synthetic-unchanged": ("unchanged", None),
                "synthetic-threshold": ("gain", None),
                "synthetic-unmeasured": ("unmeasured", "no PASS or FAIL verdict for the candidate"),
                "synthetic-attempts": ("unmeasured", "no PASS or FAIL verdict for the candidate"),
                "synthetic-missing": ("missing_pair", "the candidate has no trial with a v1 record"),
                "synthetic-legacy": ("missing_pair", "the incumbent has no trial with a v1 record"),
                "synthetic-case-changed": ("not_compared", "the arms differ in case_sha256"),
                "synthetic-conditions": ("not_compared", "the arms differ in runtime"),
                "synthetic-identity-gap": ("not_compared", "the arms differ in runtime"),
                "synthetic-model": ("not_compared", "the arms differ in requested_model, observed_models"),
                "synthetic-runner": ("not_compared", "the arms differ in scenario_sha256"),
                "synthetic-stopped-early": ("not_compared", "the arms ran different trial slots: [1, 2, 3] and [1]"),
                "synthetic-unusable": ("unmeasured", "no PASS or FAIL verdict for the candidate"),
                "synthetic-recordless": ("unmeasured", "no PASS or FAIL verdict for the candidate"),
                "synthetic-misfiled": ("unmeasured", "no PASS or FAIL verdict for the candidate"),
                "synthetic-mixed-candidate": ("unmeasured", "no PASS or FAIL verdict for the candidate"),
                "synthetic-regraded": ("unchanged", None),
                "synthetic-unpublished": ("unchanged", None),
            },
            outcomes,
        )
        # 2 of 3 meets the scenario's 0.66 and 1 of 3 does not; an average would rank, not decide.
        threshold = case(self.report, "synthetic-threshold")
        self.assertEqual(("FAIL", 0.66), (threshold["incumbent"]["verdict"], threshold["incumbent"]["threshold"]))
        self.assertEqual(("PASS", 2, 3), tuple(threshold["candidate"][k] for k in ("verdict", "passed", "slots")))

    def test_an_arm_pools_only_one_measurement_with_known_identity(self) -> None:
        """What a batch refuses to pool, the comparison refuses to pool: an unknown CLI, two candidates
        in one arm. A later regrade sits beside the original verdict, which is the one compared."""
        arms = {
            name: (case(self.report, name)["candidate"]["verdict"], case(self.report, name)["candidate"]["reason"])
            for name in ("synthetic-identity-gap", "synthetic-mixed-candidate", "synthetic-regraded")
        }
        self.assertEqual(
            {
                "synthetic-identity-gap": ("INCONCLUSIVE", "the CLI version or host is unknown"),
                "synthetic-mixed-candidate": (
                    "INCONCLUSIVE", "the trials are not one measurement: they differ in plugin_source_sha256"),
                "synthetic-regraded": ("PASS", None),
            },
            arms,
        )
        self.assertEqual(1, self.report["arms"]["candidate"]["later_assessments"])

    def test_source_verdicts_checks_and_costs_are_preserved(self) -> None:
        """AC-01: every published trial reports its record's own status, check counts and spend."""
        seen = 0
        for pair in self.report["cases"]:
            for role in ("incumbent", "candidate"):
                for trial in (pair[role] or {}).get("trials", []):
                    if trial["folder"] is None:
                        continue
                    record = json.loads((RUNS / trial["folder"] / "record.json").read_text(encoding="utf-8"))
                    states = [c["state"] for c in record["checks"]]
                    self.assertEqual(record["verdict"]["status"], trial["status"])
                    self.assertEqual({s: states.count(s) for s in ("PASS", "FAIL", "INCONCLUSIVE")}, trial["checks"])
                    self.assertEqual({k: record["cost"][k] for k in COST_FIELDS}, trial["cost"])
                    seen += 1
        self.assertEqual(51, seen)
        candidate = self.report["arms"]["candidate"]["cost"]
        # Twenty final trials at 0.10, the judged gain at 0.11, and the replaced attempt's 0.20, paid too.
        self.assertEqual(2.31, candidate["known_usd"])
        self.assertEqual((1, 1), (candidate["judge_live_calls"], candidate["judge_cached_calls"]))

    def test_every_paid_attempt_is_in_the_spend(self) -> None:
        """AC-17 (model-free) and result rule 7: a replacement fills its slot once, a raised attempt fills
        none, and every attempt whose cost this reader cannot read counts as unknown, never as zero."""
        attempts = case(self.report, "synthetic-attempts")["candidate"]
        self.assertEqual("INCONCLUSIVE", attempts["verdict"])
        self.assertEqual(
            [("PASS", {"final": 1, "superseded": 1, "incomplete": 0, "unusable": 0}),
             (None, {"final": 0, "superseded": 0, "incomplete": 1, "unusable": 0})],
            [(t["status"], t["attempts"]) for t in attempts["trials"]],
        )
        arm = self.report["arms"]["candidate"]
        self.assertEqual({"final": 21, "superseded": 1, "incomplete": 1, "unusable": 9, "unpublished": 1}, arm["attempts"])
        self.assertEqual((28, 7), (arm["slots"], arm["slots_without_trial"]))
        # The raised attempt, nine unusable records and the unpublished folder.
        self.assertEqual(11, arm["cost"]["unknown_cost_attempts"])
        self.assertEqual(1, self.report["arms"]["incumbent"]["cost"]["unknown_cost_attempts"])  # its legacy run
        self.assertEqual(
            [("candidate/.run-1-previous-0a1b2c3d4e5f6a7b",
              "an unpublished attempt folder (in flight, or left by a failed move): not compared, "
              "and its cost is unknown")],
            problems(self.report, "synthetic-unpublished"),
        )

    def test_a_run_without_its_record_or_a_short_arm_never_pools_as_fewer_trials(self) -> None:
        """AC-02 'missing record': a published FAIL whose record was refused fails to measure instead of
        vanishing, and an arm that stopped early is never set beside a complete one."""
        recordless = case(self.report, "synthetic-recordless")["candidate"]
        self.assertEqual(("INCONCLUSIVE", 1, 2), (recordless["verdict"], recordless["passed"], recordless["slots"]))
        self.assertEqual(
            [("candidate/attempts/run-1/1",
              "kept without record.json: the runner refused or failed to write it, so it cannot be measured"),
             ("candidate/run-2",
              "published without record.json: the runner refused or failed to write it, so it cannot be measured")],
            problems(self.report, "synthetic-recordless"),
        )
        stopped = case(self.report, "synthetic-stopped-early")
        self.assertEqual(("FAIL", "PASS"), (stopped["incumbent"]["verdict"], stopped["candidate"]["verdict"]))
        self.assertEqual("not_compared", stopped["outcome"])

    def test_unusable_and_misfiled_records_stay_visible_and_never_pass(self) -> None:
        """AC-02: a cut-off record, an unsupported version and records filed where they disagree with
        their folder are named, not read."""
        self.assertEqual(
            [
                ("candidate/attempts/run-1/1", "record disagrees with its folder: state final filed as a kept attempt"),
                ("candidate/run-1", "record is not valid JSON (line 33, column 3)"),
                ("candidate/run-2", "record version 2 is not supported; this reader takes version 1"),
            ],
            problems(self.report, "synthetic-unusable"),
        )
        self.assertEqual(
            [
                ("candidate/attempts/run-4/1", "record disagrees with its folder: attempt 3 filed as 1"),
                ("candidate/run-1", "record disagrees with its folder: slot 9 filed under run-1"),
                ("candidate/run-2", "record disagrees with its folder: label 'incumbent' filed under 'candidate'"),
                ("candidate/run-3",
                 "record disagrees with its folder: case 'synthetic-gain' filed under 'synthetic-misfiled'"),
            ],
            problems(self.report, "synthetic-misfiled"),
        )
        unusable = case(self.report, "synthetic-unusable")["candidate"]
        self.assertEqual((None, 0, 2), (unusable["verdict"], unusable["passed"], unusable["slots"]))
        self.assertEqual((1, 4), (case(self.report, "synthetic-misfiled")["candidate"]["passed"],
                                  case(self.report, "synthetic-misfiled")["candidate"]["slots"]))
        self.assertEqual(
            [{"folder": "eval-synthetic-legacy/incumbent/run-1", "label": "incumbent",
              "gaps": ["no v1 record", "candidate and runner identity", "cost"]}],
            self.report["legacy"],
        )

    def test_a_record_that_breaks_the_contract_is_a_problem(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            shutil.copytree(RUNS, runs)
            path = runs / "eval-synthetic-gain" / "candidate" / "run-1" / "record.json"
            path.write_text(path.read_text(encoding="utf-8").replace('"PASS"', '"MAYBE"'), encoding="utf-8")
            report = report_for(runs)
        self.assertEqual(
            [("candidate/run-1", "record breaks the v1 contract at checks.0.state: enum")],
            problems(report, "synthetic-gain"),
        )
        self.assertEqual("unmeasured", case(report, "synthetic-gain")["outcome"])

    def test_an_unknown_scenario_identity_never_pools(self) -> None:
        """A batch refuses trials whose scenario identity is missing; two unknowns are not a match."""
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            shutil.copytree(RUNS, runs)
            for label in ("incumbent", "candidate"):
                path = runs / "eval-synthetic-gain" / label / "run-1" / "record.json"
                record = json.loads(path.read_text(encoding="utf-8"))
                record["case"]["scenario_sha256"] = None
                path.write_text(json.dumps(record), encoding="utf-8")
            gain = case(report_for(runs), "synthetic-gain")
        self.assertEqual(("INCONCLUSIVE", "the scenario identity is unknown"),
                         (gain["candidate"]["verdict"], gain["candidate"]["reason"]))
        self.assertEqual("unmeasured", gain["outcome"])

    def test_without_the_measured_scenario_no_verdict_is_assumed(self) -> None:
        report = report_for(RUNS, scenarios=[])
        self.assertEqual({"unmeasured": 12, "missing_pair": 2, "not_compared": 6},
                         {k: v for k, v in report["outcomes"].items() if v})
        changed = case(self.report, "synthetic-case-changed")["candidate"]
        self.assertEqual((None, "the scenario given differs from the case these trials measured"),
                         (changed["verdict"], changed["reason"]))

    def test_report_matches_the_committed_report_after_relocation(self) -> None:
        """AC-23 and AC-19: the same logical report from a relocated copy under a path with spaces, every
        evidence link opening there, and the one missing trace still reported missing."""
        expected = json.loads((BUNDLE / "expected-report.json").read_text(encoding="utf-8"))
        self.assertEqual(expected, self.report)
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "relocated bundle" / "with spaces"
            shutil.copytree(RUNS, runs)
            relocated = report_for(runs)
            self.assertEqual(expected, relocated)
            links = [
                (link, link in trial["missing_evidence"])
                for pair in relocated["cases"]
                for role in ("incumbent", "candidate")
                for trial in (pair[role] or {}).get("trials", [])
                for link in trial["evidence"]
            ]
            for link, missing in links:
                self.assertEqual(not missing, (runs / link).is_file(), link)
        self.assertEqual(["eval-synthetic-unchanged/candidate/run-1/stdout.jsonl"],
                         [link for link, missing in links if missing])
        self.assertEqual((1, 1), tuple(relocated["arms"]["candidate"][k] for k in ("missing_evidence", "truncated_checks")))


class CompareCommandTests(unittest.TestCase):
    def run_cli(self, *argv: str, runs: Path = RUNS) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = comparison.main([str(runs), *argv])
        return code, out.getvalue(), err.getvalue()

    def test_text_report_leads_with_counts(self) -> None:
        code, out, _ = self.run_cli("--incumbent", "incumbent", "--candidate", "candidate",
                                    "--scenarios", str(BUNDLE / "scenarios"))
        self.assertEqual(0, code)
        lines = out.splitlines()
        self.assertTrue(lines[3].startswith("incumbent incumbent: 19 case(s), 30 slot(s)"), lines[3])
        self.assertIn("2 gain, 1 regression, 3 unchanged, 6 unmeasured, 2 missing pair, 6 not compared", out)
        self.assertIn("regression    synthetic-regression  PASS 1/1 -> FAIL 0/1", out)

    def test_refuses_what_it_cannot_report(self) -> None:
        """AC-02: a duplicate or absent label, a missing bundle and a usage error are refused before
        anything is reported."""
        for argv, runs, message in (
            (("--incumbent", "candidate", "--candidate", "candidate"), RUNS, "must name different labels"),
            (("--incumbent", "incumbent", "--candidate", "typo"), RUNS, "no runs labelled 'typo'"),
            (("--incumbent", "incumbent", "--candidate", "candidate"), RUNS / "absent", "no saved runs at"),
            (("--incumbent", "incumbent"), RUNS, "--candidate"),
        ):
            code, out, err = self.run_cli(*argv, runs=runs)
            self.assertEqual((3, ""), (code, out), argv)
            self.assertIn(message, err, argv)

    def test_a_walk_that_cannot_read_a_folder_is_refused(self) -> None:
        """No partial report stands in for a bundle the walk could not read."""
        with mock.patch.object(comparison, "compare_bundle", side_effect=PermissionError("denied")):
            code, out, err = self.run_cli("--incumbent", "incumbent", "--candidate", "candidate",
                                          "--scenarios", str(BUNDLE / "scenarios"))
        self.assertEqual((3, ""), (code, out))
        self.assertIn("cannot read the saved runs", err)


if __name__ == "__main__":
    unittest.main()
