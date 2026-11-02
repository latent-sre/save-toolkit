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
from probe import outcomes

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
    run_dir, grading, raised = golden_runs.run_live(item, tmp_path)
    assert golden_runs.live_view(grading, raised, run_dir) == want["live"]
    committed = {p.relative_to(golden_runs.FIXTURES / item.name / "run-1").as_posix()
                 for p in (golden_runs.FIXTURES / item.name / "run-1").rglob("*") if p.is_file()}
    produced = {p.relative_to(run_dir).as_posix() for p in run_dir.rglob("*") if p.is_file()}
    assert produced == committed, "the runner publishes the artifact set the fixture holds"


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
    # Known divergences in today's runner, recorded as findings for the rewrite's stage 3:
    # - a cleanup failure after grading is live-only evidence, which a regrade cannot see;
    # - a grading-machinery failure is `grader_error` on a live grade (rule 5) but surfaces as
    #   `void` on a regrade, the word rule 1 reserves for an identity failure.
    allowed = {"after_assessment": {"after_assessment"}, "machinery_failure": {"grader_error", "void"}}
    for item in CASES:
        want = golden_runs.expected(item)
        if want["regrade"] is None:
            assert item.raises, item.name
            continue
        differing = {k for k in want["live"] if want["live"][k] != want["regrade"].get(k)}
        assert differing <= allowed.get(item.name, set()), (item.name, differing)
        assert json.dumps(want["live"]["expectations"]) == json.dumps(want["regrade"]["expectations"]), item.name
