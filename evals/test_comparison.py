"""The WP-01 comparison over v1 records, on the committed synthetic bundle (EVAL-012 AC-01/02/17/19/23).

The bundle (evals/fixtures/v1-bundle, written by its generate.py) holds an incumbent and a candidate
label over twenty-four synthetic cases, one behavior each, named for it: verdict pairs, a native 0.66
threshold, replaced and raised attempts, missing, legacy, recordless and refused runs, an arm that
stopped early, unpublished folders, unusable and misfiled records, a twice-regraded trial, and arms
that differ in case, model, runner, CLI, wall-clock or turn limit. CI runs these tests on Linux and the owner's host runs them on Windows over
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
                "synthetic-mixed-trials": ("unmeasured", "no PASS or FAIL verdict for the candidate"),
                "synthetic-regraded": ("unchanged", None),
                "synthetic-unpublished": ("unchanged", None),
                "synthetic-refused": ("unmeasured", "no PASS or FAIL verdict for the candidate"),
                "synthetic-wall-clock": ("not_compared", "the arms differ in wall_clock_seconds"),
                "synthetic-turn-limit": ("not_compared", "the arms differ in turn_limit"),
                "synthetic-unpublished-slot": ("not_compared", "the arms ran different trial slots: [1] and [1, 2]"),
            },
            outcomes,
        )
        # 2 of 3 meets the scenario's 0.66 and 1 of 3 does not; an average would rank, not decide.
        threshold = case(self.report, "synthetic-threshold")
        self.assertEqual(("FAIL", 0.66), (threshold["incumbent"]["verdict"], threshold["incumbent"]["threshold"]))
        self.assertEqual(("PASS", 2, 3), tuple(threshold["candidate"][k] for k in ("verdict", "passed", "slots")))

    def test_an_arm_pools_only_one_measurement_with_known_identity(self) -> None:
        """What a batch refuses to pool, the comparison refuses to pool: an unknown CLI, two models in one
        arm's case. Later regrades sit beside the original verdict, which is the one compared."""
        arms = {
            name: (case(self.report, name)["candidate"]["verdict"], case(self.report, name)["candidate"]["reason"])
            for name in ("synthetic-identity-gap", "synthetic-mixed-trials", "synthetic-regraded")
        }
        self.assertEqual(
            {
                "synthetic-identity-gap": ("INCONCLUSIVE", "the CLI version or host is unknown"),
                "synthetic-mixed-trials": (
                    "INCONCLUSIVE", "the trials are not one measurement: they differ in observed_models"),
                "synthetic-regraded": ("PASS", None),
            },
            arms,
        )
        self.assertEqual(2, self.report["arms"]["candidate"]["later_assessments"])  # one trial, two regrades

    def test_source_verdicts_checks_and_costs_are_preserved(self) -> None:
        """AC-01: every published trial, and every attempt kept beside it, reports its record's own
        status and spend; published trials also report their check counts."""
        seen = kept = 0
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
                for row in (row for trial in (pair[role] or {}).get("trials", []) for row in trial["kept"]):
                    record = json.loads((RUNS / row["folder"] / "record.json").read_text(encoding="utf-8"))
                    self.assertEqual((record["attempt"]["number"], record["attempt"]["state"],
                                      record["verdict"]["status"]), (row["attempt"], row["state"], row["status"]))
                    self.assertEqual({k: record["cost"][k] for k in COST_FIELDS}, row["cost"])
                    kept += 1
        self.assertEqual((58, 2), (seen, kept))
        candidate = self.report["arms"]["candidate"]["cost"]
        # Twenty-three final trials at 0.10, the judged gain at 0.11, the replaced attempt's 0.20 and the
        # unpublished previous run's 0.30, read from its record: every paid attempt with a known cost.
        self.assertEqual(2.91, candidate["known_usd"])
        # Judge calls are unknown for the raised attempt, ten unusable records and one unreadable
        # unpublished folder: counted as unknown, never summed as zero.
        self.assertEqual((1, 1, 12), tuple(candidate[k] for k in (
            "judge_live_calls", "judge_cached_calls", "judge_calls_unknown_attempts")))
        self.assertEqual(1, self.report["arms"]["incumbent"]["cost"]["judge_calls_unknown_attempts"])  # legacy

    def test_every_paid_attempt_is_in_the_spend(self) -> None:
        """AC-17 (model-free) and result rule 7: a replacement fills its slot once, a raised attempt fills
        none, and every attempt whose cost this reader cannot read counts as unknown, never as zero."""
        attempts = case(self.report, "synthetic-attempts")["candidate"]
        self.assertEqual("INCONCLUSIVE", attempts["verdict"])
        self.assertEqual(
            [("PASS", {"final": 1, "superseded": 1, "incomplete": 0, "unusable": 0, "unpublished": 0}),
             (None, {"final": 0, "superseded": 0, "incomplete": 1, "unusable": 0, "unpublished": 0})],
            [(t["status"], t["attempts"]) for t in attempts["trials"]],
        )
        # Each kept attempt is reachable by its folder, with its own verdict, cost and evidence.
        self.assertEqual(
            [[(1, "superseded", "replaced by attempt 2", "eval-synthetic-attempts/candidate/attempts/run-1/1",
               "FAIL", 0.2, ["eval-synthetic-attempts/candidate/attempts/run-1/1/outputs/response.md"])],
             [(1, "incomplete", None, "eval-synthetic-attempts/candidate/attempts/run-2/1", None, None, [])]],
            [[(k["attempt"], k["state"], k["reason"], k["folder"], k["status"], k["cost"]["known_usd"], k["evidence"])
              for k in t["kept"]] for t in attempts["trials"]],
        )
        arm = self.report["arms"]["candidate"]
        self.assertEqual({"final": 24, "superseded": 1, "incomplete": 1, "unusable": 10, "unpublished": 2}, arm["attempts"])
        self.assertEqual((33, 9), (arm["slots"], arm["slots_without_trial"]))
        # The raised attempt, ten unusable records and the unpublished folder with no record.
        self.assertEqual(12, arm["cost"]["unknown_cost_attempts"])
        self.assertEqual(1, self.report["arms"]["incumbent"]["cost"]["unknown_cost_attempts"])  # its legacy run
        # Unpublished folders are listed, keep the slot they started, and add their cost when it is known.
        self.assertEqual(
            [("candidate/.run-1-previous-0a1b2c3d4e5f6a7b",
              "an unpublished attempt folder (in flight, or left by a failed move): not compared; "
              "its record gives its cost")],
            problems(self.report, "synthetic-unpublished"),
        )
        self.assertEqual(
            [("candidate/.run-2-attempt-1a2b3c4d5e6f7a8b",
              "an unpublished attempt folder (in flight, or left by a failed move): not compared; "
              "its cost is unknown")],
            problems(self.report, "synthetic-unpublished-slot"),
        )
        started = case(self.report, "synthetic-unpublished-slot")["candidate"]["trials"][1]
        self.assertEqual((2, None, [{"folder": "eval-synthetic-unpublished-slot/candidate/.run-2-attempt-1a2b3c4d5e6f7a8b",
                                     "cost": None}]), (started["slot"], started["status"], started["unpublished"]))

    def test_a_run_without_its_record_or_a_short_arm_never_pools_as_fewer_trials(self) -> None:
        """AC-02 'missing record': a published FAIL whose record was refused fails to measure instead of
        vanishing, and an arm that stopped early is never set beside a complete one."""
        recordless = case(self.report, "synthetic-recordless")["candidate"]
        self.assertEqual(("INCONCLUSIVE", 1, 2), (recordless["verdict"], recordless["passed"], recordless["slots"]))
        self.assertEqual(
            [("candidate/attempts/run-1/1",
              "kept without record.json, so it cannot be measured (a refused or unwritten record, or a run from before v1 records)"),
             ("candidate/run-2",
              "published without record.json, so it cannot be measured (a refused or unwritten record, or a run from before v1 records)")],
            problems(self.report, "synthetic-recordless"),
        )
        # A case whose only attempt lost its record is not legacy: its attempt.json names a runner that
        # writes records, so the slot stays instead of the case reading as a missing pair.
        refused = case(self.report, "synthetic-refused")["candidate"]
        self.assertEqual((None, 1), (refused["verdict"], refused["slots"]))
        self.assertEqual(
            [("candidate/run-1",
              "published without record.json, so it cannot be measured (a refused or unwritten record, or a run from before v1 records)")],
            problems(self.report, "synthetic-refused"),
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

    def test_a_label_holding_several_candidates_is_not_one_candidate(self) -> None:
        """A label reused for another candidate on some cases would add several candidates' results into
        one set of outcome counts, so none of its cases is measured."""
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            shutil.copytree(RUNS, runs)
            path = runs / "eval-synthetic-gain" / "candidate" / "run-1" / "record.json"
            record = json.loads(path.read_text(encoding="utf-8"))
            record["candidate"]["plugin_source_sha256"] = "f" * 64
            path.write_text(json.dumps(record), encoding="utf-8")
            report = report_for(runs)
        self.assertEqual(["b" * 64, "f" * 64], report["arms"]["candidate"]["candidates"])
        self.assertEqual(["a" * 64], report["arms"]["incumbent"]["candidates"])
        self.assertEqual((0, 0, 0), tuple(report["outcomes"][k] for k in ("gain", "regression", "unchanged")))
        self.assertEqual(("INCONCLUSIVE", "the label holds 2 candidates across its cases"),
                         (case(report, "synthetic-regression")["candidate"]["verdict"],
                          case(report, "synthetic-regression")["candidate"]["reason"]))

    def test_without_the_measured_scenario_no_verdict_is_assumed(self) -> None:
        report = report_for(RUNS, scenarios=[])
        self.assertEqual({"unmeasured": 13, "missing_pair": 2, "not_compared": 9},
                         {k: v for k, v in report["outcomes"].items() if v})
        changed = case(self.report, "synthetic-case-changed")["candidate"]
        self.assertEqual((None, "the scenario given differs from the case these trials measured"),
                         (changed["verdict"], changed["reason"]))

    def test_evidence_that_exists_but_cannot_be_opened_is_unavailable(self) -> None:
        """AC-19: a link the reviewer cannot open is reported, not advertised as evidence."""
        locked = "eval-synthetic-gain/candidate/run-1/outputs/response.md"
        real_open = Path.open

        def guarded(self: Path, *args, **kwargs):
            if self.as_posix().endswith(locked):
                raise PermissionError("denied")
            return real_open(self, *args, **kwargs)

        with mock.patch.object(Path, "open", guarded):
            report = report_for(RUNS)
        self.assertEqual([locked], case(report, "synthetic-gain")["candidate"]["trials"][0]["missing_evidence"])

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
                (link, link in row["missing_evidence"])
                for pair in relocated["cases"]
                for role in ("incumbent", "candidate")
                for trial in (pair[role] or {}).get("trials", [])
                for row in [trial, *trial["kept"]]
                for link in row["evidence"]
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
        self.assertTrue(lines[3].startswith("incumbent incumbent: 23 case(s), 34 slot(s)"), lines[3])
        self.assertIn("2 gain, 1 regression, 3 unchanged, 7 unmeasured, 2 missing pair, 9 not compared", out)
        self.assertIn("regression    synthetic-regression  PASS 1/1 -> FAIL 0/1", out)
        # Every attempt behind a case line is traced to its folder, cost and unavailable evidence.
        for line in (
            "    candidate slot 1: PASS eval-synthetic-attempts/candidate/run-1 (USD 0.100000)",
            "      kept attempt 1 superseded FAIL eval-synthetic-attempts/candidate/attempts/run-1/1 (USD 0.200000)",
            "      kept attempt 1 incomplete no verdict eval-synthetic-attempts/candidate/attempts/run-2/1 (USD unknown)",
            "      unpublished eval-synthetic-unpublished/candidate/.run-1-previous-0a1b2c3d4e5f6a7b (USD 0.300000)",
            "      unavailable evidence eval-synthetic-unchanged/candidate/run-1/stdout.jsonl",
        ):
            self.assertIn(line, lines)

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

    def test_a_scenario_directory_it_cannot_read_is_refused(self) -> None:
        """A malformed or unreadable scenario is a refusal (exit 3), never a traceback."""
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "broken.yaml").write_text("id: [unclosed\n", encoding="utf-8")
            code, out, err = self.run_cli("--incumbent", "incumbent", "--candidate", "candidate", "--scenarios", tmp)
        self.assertEqual((3, ""), (code, out))
        self.assertIn("invalid scenario", err)
        with mock.patch.object(comparison.catalog, "load_all_scenarios", side_effect=PermissionError("denied")):
            code, out, err = self.run_cli("--incumbent", "incumbent", "--candidate", "candidate")
        self.assertEqual((3, ""), (code, out))
        self.assertIn("invalid scenario: denied", err)

    def test_a_walk_that_cannot_read_a_folder_is_refused(self) -> None:
        """No partial report stands in for a bundle the walk could not read."""
        with mock.patch.object(comparison, "compare_bundle", side_effect=PermissionError("denied")):
            code, out, err = self.run_cli("--incumbent", "incumbent", "--candidate", "candidate",
                                          "--scenarios", str(BUNDLE / "scenarios"))
        self.assertEqual((3, ""), (code, out))
        self.assertIn("cannot read the saved runs", err)


if __name__ == "__main__":
    unittest.main()
