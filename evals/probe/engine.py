"""The evidence engine: the runner's one grading path (RUNNER-001, cut over at stage 4).

`grade(scenario, evidence, kept)` is pure in what it reads and the same for a live attempt and a
saved run: a check is re-measured from the evidence through the same declared check functions,
against a context rebuilt from the evidence (the parsed trace, the git facts, the fixture's state
files), and the result rules are applied by name. A probe's outcome is evidence, so it is kept,
never re-run: `kept` is the set of probe outcomes the caller still trusts, which is every one the
evidence holds unless the caller says a judgment lapsed.

A live attempt reaches it through `grade_trial`: `probe` runs the probes in the trial's workspace,
`observe` writes what the attempt saw into an evidence record with their outcomes, and `grade`
then reads that record as a regrade later will. `render` is the one rendering of a verdict to the
grading shape.
"""

from __future__ import annotations

import contextlib
import dataclasses
import tempfile
from collections.abc import Iterator, Mapping
from pathlib import Path
from types import EllipsisType
from typing import Any

import judge as rubric_judge

from . import assessment, fingerprints, outcomes, rules
from . import evidence as evidence_v1
from .checks.registry import Context
from .constants import ROOT
from .outcomes import CutShort, Ending, Outcome, Polarity, State
from .tracing import TraceSummary
from .workspaces import GitFacts, Workspace

Spec = Mapping[str, Any]
Kept = Mapping[int, tuple[str, Outcome]]  # a probe's text and outcome, by the position it was recorded at


@dataclasses.dataclass(frozen=True)
class Verdict:
    """What `grade` concludes: the status, its reason, how the run ended, and every graded expectation."""

    status: State
    reason: str | None
    run_level: str | None  # a CutShort for a run cut short, a plain reason for a voided one, else None
    turn_limit: bool
    graded: list[assessment.Graded]
    identity: str
    judge_binding: dict[str, Any] | None
    response_sha256: str


def kept_from(
    found: evidence_v1.EvidenceV1, *, stale_judge: str | None = None, mark: bool = False
) -> dict[int, tuple[str, Outcome]]:
    """The probe outcomes an evidence record holds, as the outcomes a grade keeps, by the position
    each was recorded at (its id's suffix), since two expectations can read the same. With
    `stale_judge`, a judgment the judge that gave it no longer stands behind is unmeasured instead.
    With `mark`, a regrade's, each outcome's evidence leads with the marker naming why it is kept."""
    kept: dict[int, tuple[str, Outcome]] = {}
    for order, probe in enumerate(found.probes):
        if stale_judge and probe.kept_as == "live-judge":
            outcome = outcomes.unmeasured(stale_judge)
        else:
            read = Outcome.read(probe.state is State.PASS, probe.evidence)
            outcome = Outcome(probe.state, probe.evidence, machinery=read.machinery)
            if mark:
                outcome = outcome.with_evidence(outcomes.kept_evidence(probe.kept_as, probe.evidence))
        kept[_position(probe.id, order)] = (probe.text, outcome)
    return kept


def _position(probe_id: str, order: int) -> int:
    """The expectation position a probe's id names (`<identity>:<index>`), else its order."""
    _prefix, _sep, index = probe_id.rpartition(":")
    return int(index) if index.isdigit() else order


def trace_of(found: evidence_v1.EvidenceV1) -> TraceSummary:
    """The parsed trace the evidence carries, as the object the checks read."""
    fields = {f.name for f in dataclasses.fields(TraceSummary)}
    return TraceSummary(**{name: value for name, value in found.trace.model_dump().items() if name in fields})


@contextlib.contextmanager
def context_of(
    spec: Spec, found: evidence_v1.EvidenceV1, plugin_root: Path, run_level: str | None = None
) -> Iterator[Context]:
    """A check context rebuilt from the evidence: its trace, git facts and state files, with a
    placeholder for the workspace that left with the run. `run_level` is how the run ended as the
    grade reads it, which decides whether a cut stream's counts are evidence."""
    trace = trace_of(found)
    git = GitFacts(
        found.git.commits_after,
        found.git.branch,
        [(status, path) for status, path in found.git.changed],
        "",
        found.git.problem,
        commit_ids=frozenset(found.git.commit_ids_after) if found.git.commit_ids_after is not None else None,
    )
    recorded = found.host.workspace
    with tempfile.TemporaryDirectory(prefix="evidence-grade-") as tmp:
        root = Path(tmp)
        state = root / "state"
        state.mkdir()
        for name, content in found.workspace.state_files.items():
            (state / name).write_text(content, encoding="utf-8")
        ws = Workspace(
            root,
            root / "repo-gone",
            root / "bin",
            state,
            found.git.commits_before,
            found.workspace.baseline_branch,
            # The path the trial's commands named, in the form its platform recorded it.
            command_repo=Path(recorded) if recorded else None,
            baseline_commit_ids=(
                frozenset(found.git.commit_ids_before) if found.git.commit_ids_before is not None else None
            ),
        )
        if found.workspace.agents_dir:
            (ws.repo / ".agents").mkdir(parents=True)
        cut = rules.is_cut(run_level)
        # Zero calls are evidence only from an intact stream, or from the summary's complete counts;
        # a cut raw stream still proves what it shows.
        raw_cut = cut and not found.trace.restored_from_summary and (trace.saw_init or bool(trace.tool_counts))
        yield Context(
            dict(spec),
            ws,
            trace,
            git,
            plugin_root=plugin_root,
            service_problem=found.service_problem,
            tool_counts_recorded=trace.tool_counts_complete or raw_cut,
        )


def run_level_of(found: evidence_v1.EvidenceV1) -> str | None:
    """The run-level reason the evidence records: rule 1's void, or how the run was cut short."""
    ending = found.ending
    void = rules.rule_1_identity(ending.kind, ending.reason)
    if void:
        return void
    if ending.kind is Ending.CUT_SHORT:
        return CutShort(ending.reason or "run cut short", ending.stop or outcomes.Stop.UNRECORDED)
    return None


def grade(
    spec: Spec,
    found: evidence_v1.EvidenceV1,
    kept: Kept | None = None,
    *,
    plugin_root: Path | None = None,
    run_level: str | EllipsisType | None = ...,
) -> Verdict:
    """Grade `spec` from `found`. `kept` defaults to every probe outcome the evidence holds;
    `plugin_root` is where the measured plugin's manifest is read, the served image when it still
    exists, else this checkout; `run_level` is the run-level reason the caller settled, a void
    (rule 1) or a cut (rules 2 and 4), None for a run graded in full, or, left out, what the
    evidence's ending records."""
    kept = kept_from(found) if kept is None else kept
    served = found.host.plugin_served_from
    root = plugin_root or (Path(served) if isinstance(served, str) and Path(served).is_dir() else ROOT)
    level = run_level_of(found) if isinstance(run_level, EllipsisType) else run_level
    binding = (
        {
            **found.identity.judge_binding,
            "execution": found.host.judge_execution,
            "cache_dir": found.host.judge_cache_dir,
        }
        if found.identity.judge_binding is not None
        else None
    )
    identity = found.identity.scenario_sha256 or fingerprints.scenario_digest(spec, binding)

    def kept_outcome(index: int, item: assessment.Expectation) -> Outcome | None:
        recorded = kept.get(index)
        return recorded[1] if recorded is not None and recorded[0] == item.text else None

    with context_of(spec, found, root, level) as ctx:
        items = assessment.plan(
            spec,
            ctx.trace,
            ctx,
            root,
            None,
            workspace=ctx.ws.command_repo,  # relative reads resolve against the trial's own repository
            keep=True,
            raw_trace=not found.trace.restored_from_summary,
        )
        graded, reason = assessment.assess(items, level, kept=kept_outcome, instrument=found.service_problem)
        status, reason = rules.rule_3_roll_up([g.outcome for g in graded], level or reason)
        # Without the raw trace the CLI's stop reason is gone; the live grade recorded what it saw.
        at_limit = (
            rules.rule_4_turn_limit(ctx.trace, spec)
            if not found.trace.restored_from_summary
            else found.ending.kind is Ending.TURN_LIMIT
        )
        return Verdict(
            status,
            reason,
            level,
            not level and at_limit,
            graded,
            identity,
            binding,
            rubric_judge._digest(ctx.trace.result_text),
        )


def render(verdict: Verdict, spec: Spec) -> dict[str, Any]:
    """The grade as `grading.json` records it: the one rendering of a verdict."""
    expectations = assessment.records(verdict.graded)
    machinery = rules.rule_5_machinery_failure([g.outcome for g in verdict.graded])
    return {
        "expectations": expectations,
        "judge_binding": verdict.judge_binding,
        "response_sha256": verdict.response_sha256,
        **assessment.native_assessment(spec),
        "scenario_sha256": fingerprints.stamp_assertions(verdict.identity, expectations),
        **assessment.run_fields(verdict.status, verdict.reason, verdict.run_level, turn_limit=verdict.turn_limit),
        **({"grader_error": machinery} if machinery else {}),
        "summary": assessment.summary_of(expectations),
        "status": verdict.status,
    }


# --- the live attempt: probe, observe, grade ---------------------------------------------------


def probe(ctx: Context, *, run_level: str | None, identity: str) -> tuple[list[evidence_v1.ProbeOutcome], str | None]:
    """Run the probes of the trial that just ran, in its workspace, against its services and judge:
    every expectation a regrade keeps rather than re-measures. Their outcomes are evidence, recorded
    before the rules read them, so a probe's measured result is kept whatever the rules then make of
    it. On a void run nothing is measured and on a run cut short only the forbidding probes are,
    as the rules would measure them (rules 1 and 2); a probe the rules leave unmeasured records that
    reason. Also returns the first backing service that stopped answering a probe, the harness's own
    instrument failing, which names the trial's reason."""
    items = assessment.plan(
        ctx.spec, ctx.trace, ctx, ctx.plugin_root, ctx.judge_binding, workspace=ctx.ws.repo, keep=True
    )
    cut = rules.is_cut(run_level)

    def measured(item: assessment.Expectation) -> bool:
        return not run_level or (cut and item.polarity is Polarity.FORBIDS)

    probes: list[evidence_v1.ProbeOutcome] = []
    problem: str | None = None
    for index, item in enumerate(items):
        if item.kept_as is None:
            continue
        if not measured(item):
            outcome = outcomes.unmeasured(str(run_level))
        else:
            outcome, service = assessment._measure(item)
            problem = problem or service
        probes.append(
            evidence_v1.ProbeOutcome(
                id=fingerprints.assertion_id(identity, index),
                text=item.text,
                kind=item.polarity,
                state=outcome.state,
                evidence=outcome.evidence,
                kept_as=item.kept_as,
            )
        )
    return probes, problem


def observe(
    ctx: Context,
    *,
    run_level: str | None,
    identity: str,
    binding: dict[str, Any] | None,
    run_dir: Path | None = None,
    provenance: Mapping[str, Any] | None = None,
    runtime: Mapping[str, Any] | None = None,
    requested_model: str | None = None,
    identity_failure: str | None = None,
) -> evidence_v1.EvidenceV1:
    """What the attempt observed, as the evidence record it writes: the trial's context, how the
    run ended, and the probes' outcomes, measured here once."""
    probes, problem = probe(ctx, run_level=run_level, identity=identity)
    ending = evidence_v1.ending_from(
        run_level,
        turn_limit=not run_level and rules.rule_4_turn_limit(ctx.trace, ctx.spec),
        identity_failure=identity_failure,
    )
    return evidence_v1.from_live(
        ctx,
        run_dir,
        identity=identity,
        binding=binding,
        ending=ending,
        probes=probes,
        service_problem=ctx.service_problem or problem,
        provenance=provenance or {},
        runtime=runtime,
        requested_model=requested_model,
    )


def grade_trial(
    ctx: Context,
    *,
    inconclusive: str | None = None,
    expected_scenario_digest: str | None = None,
    **recording: Any,
) -> tuple[dict[str, Any], evidence_v1.EvidenceV1]:
    """Grade the trial that just ran: observe it into evidence, probes included, then grade that
    evidence as a regrade will. `inconclusive` is the run-level reason the trial found, if any;
    `expected_scenario_digest` the identity the trial started under; `recording` what `observe`
    writes of the attempt's provenance. Returns the grade and the evidence it was read from."""
    binding = fingerprints.binding_for(ctx.spec, ctx.judge_binding)
    identity = expected_scenario_digest or fingerprints.scenario_digest(ctx.spec, binding)
    if fingerprints.scenario_digest(ctx.spec, binding) != identity:
        inconclusive = "scenario inputs changed before grading; re-run the trial"
    if not inconclusive:
        try:
            rubric_judge.validate_binding(ctx.judge_binding, fingerprints.required_rubrics(ctx.spec))
        except rubric_judge.JudgeUnavailable as exc:
            inconclusive = str(exc)
    found = observe(ctx, run_level=inconclusive, identity=identity, binding=binding, **recording)
    verdict = grade(ctx.spec, found, plugin_root=ctx.plugin_root, run_level=inconclusive)
    if fingerprints.scenario_digest(ctx.spec, binding) != identity:
        inconclusive = "scenario inputs changed during grading; re-run the trial"
        found = evidence_v1.ended(found, inconclusive, identity_failure=found.ending.identity_failure)
        verdict = grade(ctx.spec, found, plugin_root=ctx.plugin_root, run_level=inconclusive)
    return render(verdict, ctx.spec), found
