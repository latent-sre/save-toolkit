"""The evidence engine: grade a scenario from an evidence record and the probe outcomes it keeps.

`grade(scenario, evidence, kept)` is the one grading path of the runner rewrite (RUNNER-001): pure
in what it reads, the same for a live attempt and a saved run, and expressed in the result rules by
name. In stage 3 it runs in shadow beside the authoritative engine; `shadow` compares the two.

A check is re-measured from the evidence through the same declared check functions the live grade
runs, against a context rebuilt from the evidence: the parsed trace, the git facts, the fixture's
state files. A probe's live outcome is evidence, so it is kept, never re-run; `kept` is the set of
probe outcomes the caller still trusts, which is every one the evidence holds unless the caller says
a judgment lapsed.
"""

from __future__ import annotations

import contextlib
import dataclasses
import tempfile
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import judge as rubric_judge

from . import assessment, fingerprints, outcomes, rules, tracing
from . import evidence as evidence_v1
from .checks.registry import Context
from .constants import ROOT
from .outcomes import CutShort, Ending, Outcome, State
from .tracing import TraceSummary
from .workspaces import GitFacts, Workspace

Spec = Mapping[str, Any]
Kept = Mapping[str, Outcome]  # a probe's outcome, by the expectation text it was recorded under


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


def kept_from(found: evidence_v1.EvidenceV1, *, stale_judge: str | None = None) -> dict[str, Outcome]:
    """The probe outcomes an evidence record holds, as the outcomes a grade keeps. With
    `stale_judge`, a judgment the judge that gave it no longer stands behind is unmeasured instead."""
    kept: dict[str, Outcome] = {}
    for probe in found.probes:
        if stale_judge and probe.kept_as == "live-judge":
            kept[probe.text] = outcomes.unmeasured(stale_judge)
        elif probe.state is State.PASS:
            kept[probe.text] = Outcome(State.PASS, probe.evidence)
        else:
            kept[probe.text] = Outcome.read(False, probe.evidence)
    return kept


def trace_of(found: evidence_v1.EvidenceV1) -> TraceSummary:
    """The parsed trace the evidence carries, as the object the checks read."""
    fields = {f.name for f in dataclasses.fields(TraceSummary)}
    return TraceSummary(**{name: value for name, value in found.trace.model_dump().items() if name in fields})


@contextlib.contextmanager
def context_of(spec: Spec, found: evidence_v1.EvidenceV1, plugin_root: Path) -> Iterator[Context]:
    """A check context rebuilt from the evidence: its trace, git facts and state files, with a
    placeholder for the workspace that left with the run."""
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
            command_repo=Path(recorded) if isinstance(recorded, str) and tracing.is_rooted(recorded) else None,
            baseline_commit_ids=(
                frozenset(found.git.commit_ids_before) if found.git.commit_ids_before is not None else None
            ),
        )
        if found.workspace.agents_dir:
            (ws.repo / ".agents").mkdir(parents=True)
        cut = found.ending.kind is Ending.CUT_SHORT
        yield Context(
            dict(spec),
            ws,
            trace,
            git,
            plugin_root=plugin_root,
            service_problem=found.service_problem,
            # Zero calls are evidence only from an intact stream; a cut stream still proves what it
            # shows, and a summary's counts are what the run recorded (the regrade's rule).
            tool_counts_recorded=(
                trace.tool_counts_complete
                or (cut and (trace.saw_init or bool(trace.tool_counts)))
                or found.trace.restored_from_summary
            ),
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
    spec: Spec, found: evidence_v1.EvidenceV1, kept: Kept | None = None, *, plugin_root: Path | None = None
) -> Verdict:
    """Grade `spec` from `found`. `kept` defaults to every probe outcome the evidence holds;
    `plugin_root` is where the measured plugin's manifest is read, the served image when it still
    exists, else this checkout."""
    kept = kept_from(found) if kept is None else kept
    served = found.host.plugin_served_from
    root = plugin_root or (Path(served) if isinstance(served, str) and Path(served).is_dir() else ROOT)
    run_level = run_level_of(found)
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

    def kept_outcome(_index: int, item: assessment.Expectation) -> Outcome | None:
        return kept.get(item.text)

    with context_of(spec, found, root) as ctx:
        items = assessment.plan(
            spec,
            ctx.trace,
            ctx,
            root,
            None,
            workspace=ctx.ws.repo,
            keep=True,
            raw_trace=not found.trace.restored_from_summary,
        )
        graded, reason = assessment.assess(items, run_level, kept=kept_outcome)
        status, reason = rules.rule_3_roll_up([g.outcome for g in graded], run_level or reason)
        return Verdict(
            status,
            reason,
            run_level,
            not run_level and rules.rule_4_turn_limit(ctx.trace, spec),
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
