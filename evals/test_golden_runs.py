"""The golden saved runs reproduce under the current runner (stage 0 of the runner rewrite).

Each fixture under evals/fixtures/runner-goldens holds one stub-driven attempt as the runner published
it, the scenario it graded, and two verdict views: the live grade's and a regrade's of that same
directory. Both must match what the current code produces, so a runner change that alters a verdict
shows up here before it reaches a saved result, and a regenerated golden is an explained decision.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import golden_runs
import pytest
from probe import outcomes, rescoring

CASES = golden_runs.CASES
IDS = [c.name for c in CASES]


@pytest.mark.parametrize("item", CASES, ids=IDS)
def test_regrade_of_the_committed_run_matches_its_expected_view(item: golden_runs.Case, tmp_path: Path) -> None:
    want = golden_runs.expected(item)
    copy = tmp_path / "run-1"
    shutil.copytree(golden_runs.FIXTURES / item.name / "run-1", copy)
    assert golden_runs.regrade_view(copy, golden_runs.scenario(item)) == want["regrade"]


@pytest.mark.parametrize("item", CASES, ids=IDS)
def test_a_fresh_stub_trial_matches_its_expected_live_view(item: golden_runs.Case, tmp_path: Path) -> None:
    want = golden_runs.expected(item)
    run_dir, grading, raised, summary = golden_runs.run_live(item, tmp_path)
    assert golden_runs.live_view(grading, raised, run_dir) == want["live"]
    assert golden_runs.batch_view(summary) == want["batch"]
    committed = {p.relative_to(golden_runs.FIXTURES / item.name / "run-1").as_posix()
                 for p in (golden_runs.FIXTURES / item.name / "run-1").rglob("*") if p.is_file()}
    produced = {p.relative_to(run_dir).as_posix() for p in run_dir.rglob("*") if p.is_file()}
    # The fixtures are pre-evidence directories by construction; a graded attempt now also writes
    # its evidence-v1 artifact beside them.
    assert produced == committed | ({"evidence.json"} if grading is not None else set()), (
        "the runner publishes the artifact set the fixture holds, plus its evidence"
    )


def test_the_fixtures_name_no_host_path() -> None:
    for path in golden_runs.FIXTURES.rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            assert str(golden_runs.ROOT) not in text and "/tmp/" not in text, path
            assert not any(prefix in text for prefix in ("/opt/", "/usr/", "/home/")), path


@pytest.mark.parametrize("item", [c for c in CASES if c.judged], ids=[c.name for c in CASES if c.judged])
def test_a_kept_judgment_holds_under_its_judge_and_lapses_under_another(item: golden_runs.Case, tmp_path: Path) -> None:
    """A regrade keeps the judgment the live batch paid for only under the judge that gave it."""
    want = golden_runs.expected(item)
    copy = tmp_path / "run-1"
    shutil.copytree(golden_runs.FIXTURES / item.name / "run-1", copy)
    assert golden_runs.regrade_view(copy, golden_runs.scenario(item), other_judge=True) == want["regrade_other_judge"]
    assert want["regrade"]["status"] == "PASS" and want["regrade"]["inconclusive"] is None
    assert want["regrade_other_judge"]["status"] == "INCONCLUSIVE"
    assert "needs a re-run under the current judge" in want["regrade_other_judge"]["inconclusive"]


def test_the_batch_reads_rules_1_5_6_and_7_from_the_result_row() -> None:
    """What a finished trial tells the batch: rule 1 stops the batch, rule 5 stops the scenario,
    rule 6 blocks the environment, and rule 7 keeps an unknown cost unknown."""
    batch = {c.name: golden_runs.expected(c)["batch"] for c in CASES}
    assert batch["incomplete"] is None, "an attempt that raised has no result row"
    assert "identity check" in batch["void_identity"]["batch_stop"]
    assert "cleanup failed" in batch["after_assessment"]["batch_stop"]
    for name in ("machinery_failure", "service_unavailable"):
        assert batch[name]["scenario_stop"] and batch[name]["batch_stop"] is None, name
    for name in ("pass", "fail_forbidding", "cut_forbidden_fails", "wall_clock", "native_pass"):
        assert (batch[name]["batch_stop"], batch[name]["scenario_stop"]) == (None, None), name
    assert batch["native_pass"]["cost_known"] is True
    assert batch["native_incomplete_followup"]["cost_known"] is False, "a follow-up without a result has no cost"
    record = json.loads((golden_runs.FIXTURES / "native_incomplete_followup/run-1/record.json").read_text("utf-8"))
    assert (record["cost"]["trial_usd"], record["cost"]["complete"]) == (None, False), "unknown, never zero"


def test_a_written_regrade_lands_beside_the_original_grade(tmp_path: Path) -> None:
    """Rule 8: a regrade adds an assessment beside the live grade and never rewrites it."""
    item = next(c for c in CASES if c.name == "pass")
    copy = tmp_path / "run-1"
    shutil.copytree(golden_runs.FIXTURES / item.name / "run-1", copy)
    golden_runs.denormalize(copy, tmp_path)
    before = (copy / "grading.json").read_bytes()
    rescoring.regrade_run(copy, golden_runs.scenario(item), write=True, relax_identity=True)
    assert (copy / "grading.json").read_bytes() == before
    assert sorted(p.name for p in (copy / "assessments").iterdir()) == ["1"]
    assert (copy / "assessments/1/grading.json").is_file()


def test_the_native_conversation_goldens_cover_a_pass_an_identity_void_and_a_cut() -> None:
    views = {c.name: golden_runs.expected(c)["live"] for c in CASES if c.native is not None}
    assert set(views) == {"native_pass", "native_wrong_session", "native_incomplete_followup"}
    assert views["native_pass"]["status"] == "PASS" and views["native_pass"]["run_end"] is None
    assert "session" in str(views["native_wrong_session"]["void"]), "rule 1: not the conversation declared"
    cut = views["native_incomplete_followup"]
    assert (cut["run_end"], cut["run_stop"], cut["void"]) == (outcomes.Ending.CUT_SHORT, "no_result", None)


def test_every_ending_and_every_result_rule_has_a_golden() -> None:
    endings = {golden_runs.expected(c)["live"].get("run_end") for c in CASES}
    assert {None, outcomes.Ending.CUT_SHORT, outcomes.Ending.TURN_LIMIT, outcomes.Ending.INCOMPLETE} <= endings
    assert any(golden_runs.expected(c)["live"].get("void") for c in CASES), "rule 1 voids a trial"
    timed_out = golden_runs.expected(next(c for c in CASES if c.name == "wall_clock"))["live"]
    assert (timed_out["run_end"], timed_out["run_stop"]) == (outcomes.Ending.CUT_SHORT, "wall_clock")
    assert timed_out["void"] is None, "a timeout with a resolved identity is a cut, not a void"
    assert {rule for c in CASES for rule in c.rules} == set(range(1, 9))
    for item in CASES:
        assert golden_runs.expected(item)["rules"] == list(item.rules), item.name


def test_live_and_regrade_views_differ_only_where_the_record_says_they_may() -> None:
    """A regrade keeps the verdict and loses only what the live run alone could see."""
    # Two divergences the result-rules ADR's 2026-11-02 amendment settles:
    # - a cleanup failure after grading is the live attempt's evidence; a regrade carries none (rule 6);
    # - a grading-machinery failure is `grader_error` on a live grade but `void` on a regrade, which
    #   rule 5 now forbids; the rewrite's stage 3 fixes the regrade and regenerates that golden.
    allowed = {"after_assessment": {"after_assessment"}, "machinery_failure": {"grader_error", "void"}}
    for item in CASES:
        want = golden_runs.expected(item)
        if want["regrade"] is None:
            assert item.raises, item.name
            continue
        differing = {k for k in want["live"] if want["live"][k] != want["regrade"].get(k)}
        assert differing <= allowed.get(item.name, set()), (item.name, differing)
        assert json.dumps(want["live"]["expectations"]) == json.dumps(want["regrade"]["expectations"]), item.name
