"""The eight result rules, each by name and number (stage 3 of the runner rewrite, RUNNER-001)."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest
from probe import assessment, outcomes, rules
from probe.outcomes import CutShort, Ending, Outcome, Polarity, State, Stop
from probe.records import AttemptState
from probe.tracing import TraceSummary


def test_every_rule_is_cited_by_its_number() -> None:
    for number in range(1, 9):
        names = [name for name in dir(rules) if name.startswith(f"rule_{number}_")]
        assert names, number
        for name in names:
            assert (getattr(rules, name).__doc__ or "").startswith(f"Rule {number}"), name


def test_rule_1_voids_a_trial_that_was_not_the_candidate_declared() -> None:
    assert rules.rule_1_identity(Ending.VOID, "plugin inputs changed") == "plugin inputs changed"
    assert rules.rule_1_identity(Ending.VOID, None) == "run voided without a recorded reason"
    for kind in (Ending.COMPLETED, Ending.CUT_SHORT, Ending.TURN_LIMIT):
        assert rules.rule_1_identity(kind, "reason") is None
    assert rules.rule_1_void_check("wrong plugin") == outcomes.unmeasured("wrong plugin")


def test_the_grade_applies_rules_1_and_2_by_name() -> None:
    """A rule changes in `rules` and nowhere else: the grade reaches each through its name."""
    items = [assessment.Expectation("t", lambda: outcomes.verdict(True, "x"), Polarity.REQUIRES)]
    with mock.patch.object(rules, "rule_1_void_check", return_value=outcomes.verdict(False, "by name")):
        graded, _reason = assessment.assess(items, "wrong plugin")
    assert graded[0].outcome == outcomes.verdict(False, "by name")
    with mock.patch.object(rules, "rule_2_polarity_on_cut", return_value=outcomes.verdict(False, "by name")):
        graded, _reason = assessment.assess(items, CutShort("timed out", Stop.WALL_CLOCK))
    assert graded[0].outcome == outcomes.verdict(False, "by name")


def test_rule_2_on_a_cut_run_counts_forbidden_evidence_and_nothing_else() -> None:
    assert rules.rule_2_polarity_on_cut(
        outcomes.violation("ran rm"), Polarity.FORBIDS, "timed out"
    ) == outcomes.violation("ran rm")
    assert rules.rule_2_polarity_on_cut(
        outcomes.verdict(True, "clean"), Polarity.FORBIDS, "timed out"
    ) == outcomes.unmeasured("no violation before the run was cut short (timed out)")
    assert rules.rule_2_polarity_on_cut(outcomes.verdict(True, "tests ran"), Polarity.REQUIRES, "timed out") == (
        outcomes.unmeasured("timed out")
    )


def test_rule_3_rolls_up_a_supported_failure_over_anything_unmeasured() -> None:
    fail, ok, unknown = outcomes.violation("x"), outcomes.verdict(True, "y"), outcomes.unmeasured("gone")
    assert rules.rule_3_roll_up([fail, unknown], None) == (State.FAIL, "gone")
    assert rules.rule_3_roll_up([ok, unknown], None) == (State.INCONCLUSIVE, "gone")
    assert rules.rule_3_roll_up([ok, ok], None) == (State.PASS, None)
    assert rules.rule_3_roll_up([ok], "run voided") == (State.INCONCLUSIVE, "run voided")
    assert rules.rule_3_roll_up([ok, unknown], "first") == (State.INCONCLUSIVE, "first"), "the run's reason leads"


def test_rule_4_a_run_ended_at_its_declared_turn_limit_is_complete() -> None:
    limited = TraceSummary(result_subtype="error_max_turns")
    assert rules.rule_4_turn_limit(limited, {"max_turns": 5}) is True
    assert rules.rule_4_turn_limit(limited, {}) is False, "without a declared limit the run is cut short"
    assert rules.rule_4_turn_limit(TraceSummary(result_subtype="success"), {"max_turns": 5}) is False


def test_rule_5_a_machinery_failure_is_named_and_never_a_verdict() -> None:
    crash = outcomes.grader_error(ValueError("bad pattern"))
    assert crash.state is State.INCONCLUSIVE and crash.machinery
    assert rules.rule_5_machinery_failure([outcomes.verdict(True, "x"), crash]) == crash.reason
    assert rules.rule_5_machinery_failure([outcomes.instrument("proxy died")]) == "instrument: proxy died"
    assert rules.rule_5_machinery_failure([outcomes.violation("x"), outcomes.unmeasured("y")]) is None


def test_rule_6_a_problem_after_assessment_is_recorded_beside_an_unchanged_verdict() -> None:
    grading = {"status": "PASS", "expectations": []}
    recorded = rules.rule_6_after_assessment(grading, "cleanup failed")
    assert recorded == {"status": "PASS", "expectations": [], "after_assessment": "cleanup failed"}
    assert grading == {"status": "PASS", "expectations": []}, "the original is not rewritten"
    assert rules.rule_6_after_assessment(grading, None) is grading


def test_rule_7_every_attempt_is_kept_in_a_named_state() -> None:
    assert rules.rule_7_attempt_kept("published") is AttemptState.FINAL
    assert rules.rule_7_attempt_kept("replaced") is AttemptState.SUPERSEDED
    assert rules.rule_7_attempt_kept("raised") is AttemptState.INCOMPLETE
    with pytest.raises(KeyError):
        rules.rule_7_attempt_kept("deleted")


def test_rule_8_a_regrade_writes_beside_the_live_grade_never_over_it(tmp_path: Path) -> None:
    run = tmp_path / "run-1"
    run.mkdir()
    (run / "grading.json").write_text("{}", encoding="utf-8")
    target = rules.rule_8_regrade_adds(run, 2)
    assert target == run / "assessments" / "2"
    assert target != run and not (target / "grading.json").exists()


def test_is_cut_distinguishes_a_cut_from_a_void() -> None:
    assert rules.is_cut(outcomes.CutShort("timed out", outcomes.Stop.WALL_CLOCK))
    assert not rules.is_cut("plugin inputs changed") and not rules.is_cut(None)
    assert isinstance(Outcome.read(False, "INCONCLUSIVE: grader error: x"), Outcome)
