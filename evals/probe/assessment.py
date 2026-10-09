"""Grade one trial: every expectation its scenario states, measured or kept, rolled up by the result rules.

`assess` is the one grading loop. A live grade measures every expectation against the trial it just
ran; a regrade measures what the saved run still supports and keeps the live verdict for the rest
(rescoring.regrade_run). Both apply the threat-model ADR's result rules in the same order, so a rule
changes in one place:
- a run-level failure (a wrong profile, changed inputs) leaves every check INCONCLUSIVE (rule 1);
- on a run cut short, evidence of a forbidden action still fails and nothing else does (rules 2, 4);
- a grader crash or instrument failure is INCONCLUSIVE and named, never a verdict (rule 5);
- a supported FAIL is never hidden by anything unmeasured (rule 3).
"""

from __future__ import annotations

import functools
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Final

import graders as fleet_graders
import judge as rubric_judge

from . import catalog, checking, fingerprints, invocation, outcomes, tracing
from .backing import ServiceUnavailable
from .checking import Context, Need
from .constants import ROOT
from .outcomes import (
    EVIDENCE_LIMIT,
    CutShort,
    Ending,
    Outcome,
    Polarity,
    State,
    grader_error,
    instrument,
    unmeasured,
    verdict,
    violation,
)
from .tracing import TraceSummary

Spec = Mapping[str, Any]


def grade_routing(spec: Spec, trace: TraceSummary, plugin_root: Path) -> Outcome:
    """Did the named component fire (or, for a negative, stay out of the way)?

    One check, from invocation evidence only: a completed non-error Skill/Task call naming the
    target. A negative additionally requires its declared alternative — staying inline, or the
    named component — so a trial does not pass merely because nothing happened.
    """
    target = spec["target"]
    routing = spec["routing"]
    namespace = tracing.runtime_namespace(trace, plugin_root)
    actual = tracing.completed_components(trace, target["kind"])
    if spec.get("followups") and target["kind"] == "skill":
        actual = set(trace.parent_skills_before_dispatch)

    def runtime_target(component: Mapping[str, Any]) -> str:
        return f"{namespace}:{component['name']}"

    target_name = runtime_target(target)
    if routing["expect"] == "fire":
        fired = target_name in actual
        return verdict(fired, f"routing matched {target_name}" if fired else f"routing saw {sorted(actual)}")
    if target_name in actual:
        return violation(f"routing unexpectedly fired {target_name}")
    declared = routing["expected_alternative"]
    alternatives = declared if isinstance(declared, list) else [declared]
    answered = bool(trace.result_text.strip())
    seen = f"skills={trace.skills}, agents={trace.agents}"
    for alternative in alternatives:
        if alternative == "inline" and not trace.skills and not trace.agents and answered:
            return verdict(True, "routing stayed inline")
        if alternative == "main_session" and not trace.agents and answered:
            # The main session keeps the work: craft skills may load, but no agent takes it.
            return verdict(True, f"routing stayed in the main session; skills={trace.skills}")
        if isinstance(alternative, Mapping):
            alternate_name = runtime_target(alternative)
            if alternate_name in tracing.completed_components(trace, alternative["kind"]):
                return verdict(True, f"routing reached alternative {alternate_name}")
    names = [a if isinstance(a, str) else runtime_target(a) for a in alternatives]
    expected = names[0] if len(names) == 1 else f"one of {names}"
    return verdict(False, f"routing expected alternative {expected}; saw {seen}")


def grade_skill_fired(spec: Spec, trace: TraceSummary, plugin_root: Path) -> Outcome:
    """Prove a skill-pinned trial actually invoked the skill.

    The instruction alone is not proof: the main model can ignore it and answer inline, and init
    metadata only establishes that a skill was available.
    """
    expected = f"{tracing.runtime_namespace(trace, plugin_root)}:{spec['skill']}"
    actual = tracing.completed_components(trace, "skill")
    if expected in actual:
        return verdict(True, f"pinned skill fired {expected}")
    return verdict(False, f"pinned skill {expected} did not complete; saw skills={sorted(actual)}")


def reference_read(trace: TraceSummary, reference: str, plugin_root: Path, workspace: Path | None = None) -> Outcome:
    """Require a successful read of the measured canonical file, resolving relatives only from its cwd."""
    expected = (plugin_root / reference).resolve()
    attempts = []
    for attempt in trace.read_attempts:
        if attempt["tool"] != "Read" or not attempt["path"]:
            continue
        candidate = Path(str(attempt["path"]).replace("\\", "/"))
        if not tracing.is_rooted(candidate):
            if workspace is None or candidate.drive:
                continue
            candidate = workspace / candidate
        if candidate.resolve() == expected:
            attempts.append(attempt)
    if any(a["outcome"] == "allowed" for a in attempts):
        return verdict(True, f"read {reference}")
    if attempts:
        return verdict(False, f"{reference} was read but the read did not succeed")
    return verdict(False, f"{reference} was never read; reads: {[a['path'] for a in trace.read_attempts] or 'none'}")


RAW: Final = frozenset({Need.RAW_TRACE})  # completed calls, reads, returns and the plugin namespace


def _trace_expectations(
    spec: Spec, trace: TraceSummary, plugin_root: Path, judge_binding: Any = None, *, workspace: Path | None = None
) -> list[tuple[str, Callable[[], Outcome], frozenset[Need], Polarity]]:
    """Every expectation graded from the trace and final text, as (text, measure, needs, polarity), in
    grading order.

    The scenario's `checks` follow these. One list keeps the live grade, the regrade, and the recorded
    assertion text from drifting apart -- a regrade matches saved verdicts by position and text.
    `needs` is the evidence it reads, as a check declares it: a rubric grader's spends a judge call.
    Each carries its own polarity, from the per-family rule `catalog.assertion_polarities` also uses.
    """
    graded: list[tuple[str, Callable[[], Outcome], frozenset[Need], Polarity]] = []
    if spec.get("routing"):
        target = spec["target"]
        graded.append(
            (
                f"routing {spec['routing']['expect']} {target['kind']}:{target['name']}",
                lambda: grade_routing(spec, trace, plugin_root),
                RAW,
                catalog.routing_polarity(spec),
            )
        )
    if spec.get("skill"):
        graded.append(
            (
                f"pinned skill {spec['skill']} completed",
                lambda: grade_skill_fired(spec, trace, plugin_root),
                RAW,
                Polarity.REQUIRES,
            )
        )
    reference_trace = (
        replace(trace, read_attempts=trace.parent_reads_before_dispatch) if spec.get("followups") else trace
    )
    for reference in spec.get("references") or []:
        scope = " by initial parent before helper dispatch" if spec.get("followups") else ""
        graded.append(
            (
                f"reference {reference} read{scope}",
                functools.partial(reference_read, reference_trace, reference, plugin_root, workspace),
                RAW,
                Polarity.REQUIRES,
            )
        )
    for grader in spec.get("graders") or []:
        traits = checking.grader_traits(grader.get("type"))
        graded.append(
            (
                f"grader {grader.get('type')}",
                functools.partial(_run_grader, grader, trace.result_text, judge_binding),
                traits.needs,
                traits.polarity,
            )
        )
    if spec.get("followups"):
        returns = trace.agent_returns
        sessions = trace.conversation_sessions
        same_session = len(set(sessions + trace.init_session_ids)) == 1

        def helper_completed_once() -> Outcome:
            # Read the namespace when measured, as routing and pinned skills do: a regrade also plans a
            # void run, whose saved plugin root may be gone.
            helper = f"{tracing.runtime_namespace(trace, plugin_root)}:{spec['helper']}"
            return verdict(
                trace.dispatches == [helper] and trace.agents == [helper],
                f"dispatches={trace.dispatches}; completed={trace.agents}",
            )

        graded.extend(
            [
                ("native helper completed exactly once", helper_completed_once, RAW, Polarity.REQUIRES),
                (
                    "parent continued after helper completion",
                    lambda: verdict(len(returns) == 1 and bool(returns[0]["continued"]), f"returns={returns}"),
                    RAW,
                    Polarity.REQUIRES,
                ),
                (
                    "human follow-up resumed the same session",
                    lambda: verdict(
                        len(sessions) == 2 and bool(sessions[0]) and same_session,
                        f"invocations={len(sessions)}; same session={same_session}",
                    ),
                    RAW,
                    Polarity.REQUIRES,
                ),
            ]
        )
    return graded


def _run_grader(grader: Mapping[str, Any], text: str, judge_binding: Any) -> Outcome:
    return outcomes.coerce(fleet_graders.run_grader(dict(grader), text, judge_binding=judge_binding))


def scenario_assertions(spec: Spec) -> list[str]:
    """One line per graded expectation, in the order a grade evaluates them."""
    return [text for text, *_ in _trace_expectations(spec, TraceSummary(), ROOT)] + [
        checking.describe(c) for c in spec.get("checks") or []
    ]


def native_assessment(spec: Spec) -> dict[str, str]:
    return {"assessment_scope": "structural_only", "semantic_assessment": "UNVERIFIED"} if spec.get("followups") else {}


@dataclass(frozen=True)
class Expectation:
    """One expectation, ready to grade: its recorded text, what it asserts, and how to measure it."""

    text: str
    measure: Callable[[], Outcome]
    polarity: Polarity
    check: Mapping[str, Any] | None = None  # the scenario check it grades, when it is one
    # How a `both` expectation is graded on a run cut short, given what was measured.
    on_cut: Callable[[Outcome, str], Outcome] | None = None
    kept_as: str | None = None  # a regrade keeps the live verdict instead: why
    names_unmeasured: bool = False  # its own INCONCLUSIVE names the trial's reason


@dataclass(frozen=True)
class Graded:
    expectation: Expectation
    outcome: Outcome  # evidence cut to the 600 characters the record keeps
    truncated: bool  # the measured evidence was longer


def plan(
    spec: Spec,
    trace: TraceSummary,
    ctx: Context | None,
    plugin_root: Path,
    judge_binding: Any = None,
    *,
    workspace: Path | None = None,
    keep: bool = False,
    raw_trace: bool = True,
) -> list[Expectation]:
    """Every expectation in grading order. With `keep`, a regrade's: an expectation the saved run cannot
    re-measure (a paid judgment, or evidence that left with the workspace) carries why it is kept.
    Without `raw_trace`, one that reads what only the raw trace held is INCONCLUSIVE on its own."""
    lost = frozenset() if raw_trace else checking.RAW_ONLY
    items: list[Expectation] = []
    for text, measure, needs, polarity in _trace_expectations(
        spec, trace, plugin_root, judge_binding, workspace=workspace
    ):
        items.append(
            Expectation(
                text,
                _unless_lost(measure, needs & lost),
                polarity,
                on_cut=routing_on_cut if polarity is Polarity.BOTH else None,
                kept_as=checking.LIVE_JUDGE if keep and Need.JUDGE in needs else None,
            )
        )
    for check in spec.get("checks") or []:
        declared = checking.registered(check)
        polarity = checking.check_polarity(check)
        on_cut = None
        if polarity is Polarity.BOTH:
            rule = declared.on_cut if declared is not None else None
            if rule is None:
                raise ValueError(f"check {check.get('check')!r} has a floor and a ceiling but no cut-short rule")
            on_cut = _cut_rule(rule, check, trace)
        items.append(
            Expectation(
                checking.describe(check),
                _unless_lost(_check_measure(ctx, check), checking.check_needs(check, spec) & lost),
                polarity,
                check=check,
                on_cut=on_cut,
                kept_as=checking.kept_as(check, spec) if keep and not checking.is_regradable(check, spec) else None,
                names_unmeasured=declared is not None and declared.names_unmeasured,
            )
        )
    return items


def _unless_lost(measure: Callable[[], Outcome], lost: frozenset[Need]) -> Callable[[], Outcome]:
    """The measurement, or, when evidence it reads left with the raw trace, why it cannot be made: a
    trace summary would read as "never happened" what it simply does not record."""
    if not lost:
        return measure
    return functools.partial(unmeasured, "the raw trace this expectation reads is missing; re-run the trial")


def _check_measure(ctx: Context | None, check: Mapping[str, Any]) -> Callable[[], Outcome]:
    def measure() -> Outcome:
        if ctx is None:
            raise ValueError("a check needs a trial context")
        return checking.run(ctx, dict(check))

    return measure


def _cut_rule(
    rule: checking.CutRule, check: Mapping[str, Any], trace: TraceSummary
) -> Callable[[Outcome, str], Outcome]:
    return lambda _measured, cut: rule(check, trace, cut)


def routing_on_cut(outcome: Outcome, cut: str) -> Outcome:
    """A negative routing expectation on a run cut short: the forbidden target firing is a violation
    already; a declared alternative that never fired proves nothing, because the run stopped early."""
    if outcome.forbidden:
        return outcome
    return unmeasured(f"no forbidden routing before the run was cut short ({cut})")


def forbidden_on_cut(outcome: Outcome, cut: str) -> Outcome:
    """A forbidding check on a run cut short: a violation stands, but no violation yet proves nothing."""
    if outcome.state is State.PASS:
        return unmeasured(f"no violation before the run was cut short ({cut})")
    return outcome


def _bound(outcome: Outcome) -> tuple[Outcome, bool]:
    truncated = len(outcome.evidence) > EVIDENCE_LIMIT
    return (outcome.with_evidence(outcome.evidence[:EVIDENCE_LIMIT]) if truncated else outcome), truncated


def _measure(item: Expectation) -> tuple[Outcome, str | None]:
    """Measure one expectation. A grader crash is a measurement failure, never a verdict (result
    rule 5); so is a backing service that stops answering, the harness's own instrument, which is
    also named as the trial's reason."""
    try:
        return outcomes.coerce(item.measure()), None
    except ServiceUnavailable as exc:
        return instrument(f"backing service unavailable: {exc}"), str(exc)
    except Exception as exc:  # a grader crash is a measurement failure, never a verdict
        return grader_error(exc), None


def _graded_on_cut(item: Expectation, cut: str) -> Outcome:
    """A floor-and-ceiling expectation on a run cut short: measured, then graded by its cut rule. A
    measurement that failed stays that grading-machinery failure, never "nothing forbidden yet"."""
    measured, _ = _measure(item)
    if measured.machinery or item.on_cut is None:
        return measured
    try:
        return item.on_cut(measured, cut)
    except Exception as exc:  # a crashing cut rule is a measurement failure too
        return grader_error(exc)


Kept = Callable[[int, Expectation], Outcome | None]


def assess(
    items: Sequence[Expectation], inconclusive: str | None, *, kept: Kept | None = None
) -> tuple[list[Graded], str | None]:
    """Grade every expectation under the result rules, in order.

    `inconclusive` is the run-level reason, if any: a CutShort for a run that stopped early on its
    declared profile, any other string for a void one. `kept`, which a regrade's plan requires, returns
    the saved live verdict of an expectation it keeps, or None when none was saved: measuring a kept
    expectation live would spend a judge call or read a workspace that is gone. Returns the graded
    expectations and the first reason one of them went unmeasured that names the trial's reason.
    """
    if kept is None and any(item.kept_as for item in items):
        raise ValueError("this plan keeps live verdicts; assess it with `kept`, the saved verdicts")
    cut = inconclusive if isinstance(inconclusive, CutShort) else None
    graded: list[Graded] = []
    reason: str | None = None
    for index, item in enumerate(items):
        forbids_on_cut = cut is not None and item.polarity is Polarity.FORBIDS
        if cut is not None and item.polarity is Polarity.BOTH and item.on_cut is not None:
            outcome = _graded_on_cut(item, cut)
        elif inconclusive and not forbids_on_cut:
            outcome = unmeasured(inconclusive)
        elif item.kept_as is not None and kept is not None:
            saved = kept(index, item)
            if saved is None:
                missing = f"no saved verdict for a {item.kept_as} expectation; re-run the trial"
                reason = reason or missing
                saved = unmeasured(missing)
            outcome = saved
        else:
            outcome, service = _measure(item)
            reason = reason or service
            if cut is not None and forbids_on_cut:
                outcome = forbidden_on_cut(outcome, cut)
        if item.names_unmeasured and outcome.state is State.INCONCLUSIVE:
            reason = reason or outcome.reason  # whole: only the recorded evidence is cut
        if item.polarity is Polarity.FORBIDS and outcome.state is State.FAIL:
            outcome = outcome.as_violation()
        graded.append(Graded(item, *_bound(outcome)))
    return graded, reason


def unmeasured_all(graded: Sequence[Graded], reason: str) -> list[Graded]:
    """A run-level failure found after grading voids every check already graded (result rule 1)."""
    return [Graded(g.expectation, *_bound(unmeasured(reason))) for g in graded]


def roll_up(outcomes: Sequence[Outcome], unmeasured_reason: str | None) -> tuple[State, str | None]:
    """A trial's status: a supported FAIL wins, then anything unmeasured, then PASS (result rule 3).
    Returns it with the first reason something went unmeasured, if any."""
    states = [outcome.state for outcome in outcomes]
    reason = unmeasured_reason or next(
        (outcome.reason for outcome in outcomes if outcome.state is State.INCONCLUSIVE), None
    )
    if State.FAIL in states:
        return State.FAIL, reason
    return (State.INCONCLUSIVE if reason or State.INCONCLUSIVE in states else State.PASS), reason


def records(graded: Sequence[Graded]) -> list[dict[str, Any]]:
    """Each graded expectation as the grade records it."""
    entries = []
    for g in graded:
        entry: dict[str, Any] = {"text": g.expectation.text, "passed": g.outcome.passed, "evidence": g.outcome.evidence}
        if g.truncated:
            entry["evidence_truncated"] = True
        entry["state"] = g.outcome.state
        entry["kind"] = g.expectation.polarity
        entries.append(entry)
    return entries


def run_fields(
    status: State, reason: str | None, inconclusive: str | None, *, turn_limit: bool = False
) -> dict[str, Any]:
    """How the run ended and why it went unmeasured, independent of what the checks found."""
    return {
        "inconclusive": reason if status is State.INCONCLUSIVE else None,
        **({"unmeasured": reason} if status is State.FAIL and reason else {}),
        **({"run_end": Ending.CUT_SHORT, "run_stop": inconclusive.kind} if isinstance(inconclusive, CutShort) else {}),
        **({"run_end": Ending.TURN_LIMIT} if turn_limit else {}),
        **({"void": inconclusive} if inconclusive and not isinstance(inconclusive, CutShort) else {}),
    }


def summary_of(expectations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    passed = sum(bool(e["passed"]) for e in expectations)
    return {
        "passed": passed,
        "failed": len(expectations) - passed,
        "total": len(expectations),
        "pass_rate": round(passed / len(expectations), 4) if expectations else 0.0,
    }


def machinery_failure(graded: Sequence[Graded]) -> dict[str, str]:
    """The first grading-machinery failure in a grade, if any (threat-model ADR rule 5)."""
    failure = next((g.outcome.reason for g in graded if g.outcome.machinery), None)
    return {"grader_error": failure} if failure else {}


def grade(
    ctx: Context, *, inconclusive: str | None = None, expected_scenario_digest: str | None = None
) -> dict[str, Any]:
    """Grade a trial that just ran, against its live workspace, trace and services."""
    binding = fingerprints.binding_for(ctx.spec, ctx.judge_binding)
    identity = expected_scenario_digest or fingerprints.scenario_digest(ctx.spec, binding)
    if fingerprints.scenario_digest(ctx.spec, binding) != identity:
        inconclusive = "scenario inputs changed before grading; re-run the trial"
    if not inconclusive:
        try:
            rubric_judge.validate_binding(ctx.judge_binding, fingerprints.required_rubrics(ctx.spec))
        except rubric_judge.JudgeUnavailable as exc:
            inconclusive = str(exc)
    items = plan(
        ctx.spec,
        ctx.trace,
        ctx,
        ctx.plugin_root,
        ctx.judge_binding,
        workspace=ctx.ws.repo,
    )
    graded, reason = assess(items, inconclusive)
    if fingerprints.scenario_digest(ctx.spec, binding) != identity:
        inconclusive = "scenario inputs changed during grading; re-run the trial"
        graded = unmeasured_all(graded, inconclusive)
    status, reason = roll_up([g.outcome for g in graded], inconclusive or reason)
    expectations = records(graded)
    return {
        "expectations": expectations,
        "judge_binding": binding,
        "response_sha256": rubric_judge._digest(ctx.trace.result_text),
        **native_assessment(ctx.spec),
        "scenario_sha256": fingerprints.stamp_assertions(identity, expectations),
        **run_fields(
            status,
            reason,
            inconclusive,
            turn_limit=not inconclusive and invocation.reached_turn_limit(ctx.trace, ctx.spec),
        ),
        **machinery_failure(graded),
        "summary": summary_of(expectations),
        "status": status,
    }
