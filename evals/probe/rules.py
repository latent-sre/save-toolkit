"""The eight result rules, each a named function cited by its number in the result-rules decision
record (docs/decisions/2026-10-03-eval-harness-threat-model.md, amended 2026-11-02).

`assessment` applies them to a live grade and a regrade alike, `engine.grade` applies them to an
evidence record, and `attempt` applies rule 7 to an attempt's life; each rule has its own test in
evals/test_probe_rules.py. A rule changes here and nowhere else.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from . import invocation, layout
from .outcomes import CutShort, Ending, Outcome, Polarity, State, unmeasured
from .records import AttemptState
from .tracing import TraceSummary


def rule_1_identity(kind: Ending | str, reason: str | None) -> str | None:
    """Rule 1: a trial whose candidate, model, plugin, tool set or scenario differs from the one
    declared is inconclusive in full. Given how a run ended, the reason that voids it, or None."""
    return (reason or "run voided without a recorded reason") if Ending(kind) is Ending.VOID else None


def rule_1_void_check(reason: str) -> Outcome:
    """Rule 1, applied to one check: a voided trial's check counts nothing, whatever it measured."""
    return unmeasured(reason)


def rule_2_polarity_on_cut(outcome: Outcome, polarity: Polarity, cut: str) -> Outcome:
    """Rule 2 on a run cut short: a forbidding check fails on any evidence of the action, including
    from the cut run, and a requiring check is inconclusive, since its outcome was not collected.
    A `both` check is graded by its own cut rule and never reaches here."""
    if polarity is Polarity.FORBIDS:
        if outcome.state is State.PASS:
            return unmeasured(f"no violation before the run was cut short ({cut})")
        return outcome
    return unmeasured(cut)


def rule_3_roll_up(outcomes: Sequence[Outcome], unmeasured_reason: str | None) -> tuple[State, str | None]:
    """Rule 3: a trial with any failed check fails; otherwise any inconclusive check makes it
    inconclusive; otherwise it passes. Returns the status with the first reason something went
    unmeasured, if any."""
    states = [outcome.state for outcome in outcomes]
    reason = unmeasured_reason or next(
        (outcome.reason for outcome in outcomes if outcome.state is State.INCONCLUSIVE), None
    )
    if State.FAIL in states:
        return State.FAIL, reason
    return (State.INCONCLUSIVE if reason or State.INCONCLUSIVE in states else State.PASS), reason


def rule_4_turn_limit(trace: TraceSummary, spec: dict[str, Any] | Any) -> bool:
    """Rule 4: a run the CLI ended at the scenario's declared turn limit is complete, so the
    requirements it left unmet fail. The wall-clock timeout and the spend cap cut a run short instead,
    which `CutShort` carries."""
    return invocation.reached_turn_limit(trace, spec)


def rule_5_machinery_failure(outcomes: Sequence[Outcome]) -> str | None:
    """Rule 5: a failure of the grading machinery is a measurement failure, recorded as a grader
    error, never as a verdict and never in rule 1's form; it stops the scenario's further trials.
    The first such failure among the outcomes, or None."""
    return next((outcome.reason for outcome in outcomes if outcome.machinery), None)


def rule_6_after_assessment(grading: dict[str, Any], problem: str | None) -> dict[str, Any]:
    """Rule 6: a problem after assessment, such as failed service cleanup, is recorded beside the
    verdict and blocks reuse of the environment; it does not change the verdict. The record is the
    live attempt's; a regrade carries none."""
    if not problem:
        return grading
    return {**grading, "after_assessment": problem}


def rule_7_attempt_kept(ending: str) -> AttemptState:
    """Rule 7: every attempt is kept with its trace, timing and cost. An attempt that published is
    the slot's run, one a later attempt replaced stays visible as superseded, and one that raised
    before it was graded is kept as incomplete; nothing is deleted."""
    return {
        "published": AttemptState.FINAL,
        "replaced": AttemptState.SUPERSEDED,
        "raised": AttemptState.INCOMPLETE,
    }[ending]


def rule_8_regrade_adds(run_dir: Path, revision: int) -> Path:
    """Rule 8: a regrade adds a new assessment beside the original and never rewrites it. The folder
    revision `revision` of `run_dir`'s regrades is written to, which is never the live grade's."""
    target = run_dir / "assessments" / str(revision)
    if target == layout.live_grade(run_dir).parent:
        raise ValueError("a regrade never writes where the live grade is")
    return target


def is_cut(reason: str | None) -> bool:
    """Whether a run-level reason cuts the run short (rules 2 and 4) rather than voiding it (rule 1)."""
    return isinstance(reason, CutShort)
