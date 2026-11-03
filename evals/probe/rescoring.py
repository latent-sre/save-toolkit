"""Grade saved runs again: a regrade beside the run, a rescore into a new folder, and a diff of two.

A regrade grades the run's evidence with the engine the live grade used: its own `evidence.json`
when it wrote one, else what `legacy` reads back from the files a pre-evidence run kept, the raw
trace re-parsed when it survives. The checks are re-measured from that evidence and each probe's
recorded outcome is kept, by position under the saved scenario identity: a paid rubric judgment, or
a reading of the workspace that left with the run. When the raw trace is gone, what only it held is
INCONCLUSIVE, check by check. What a regrade settles itself is the run-level reason: the saved
identity, the judge binding, and a native conversation's replayed boundary checks. It never
rewrites the run (threat-model ADR result rule 8).
"""

from __future__ import annotations

import contextlib
import json
import re
import shutil
import tempfile
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import clean_room
import judge as rubric_judge

from . import (
    assessment,
    catalog,
    conversations,
    engine,
    evidence,
    fingerprints,
    invocation,
    layout,
    legacy,
    outcomes,
    records,
    rules,
    tracing,
)
from .constants import ROOT
from .fingerprints import HARNESS_IDENTITY, HARNESS_SOURCE_SHA256
from .outcomes import EVIDENCE_LIMIT, UNMEASURED, CutShort, Ending, Stop
from .tracing import TraceSummary

Spec = Mapping[str, Any]


_INVALID_NATIVE_EVIDENCE = "native invocation boundary evidence missing or invalid; re-run the trial"
# The wall-clock reason every runner has written; one saved before `run_end` voided the whole run.
_SAVED_TIMEOUT = re.compile(r"timed out after \d+s")


def _unreadable_root(plugin_root: Path, exc: Exception) -> str:
    return f"plugin root {plugin_root} could not be read ({type(exc).__name__}); restore it to regrade the run"


def native_regrade_problem(
    run_dir: Path, spec: Spec, plugin_root: Path, *, recorded_plugin_sha: str | None = None
) -> str | None:
    """Replay each invocation's boundary checks using its saved cwd after the workspace is gone.

    Saved evidence that is missing or malformed, or a plugin root the regrade cannot read, leaves the
    run unmeasured under a reason that names it; a defect in the runner raises instead of being
    reported as the saved run's fault.
    """
    if conversations.enabled(spec):
        problem = conversations.replay_problem(run_dir, spec, catalog.scenario_prompt(spec, plugin_root))
        if problem:
            return problem
    resume, workspace = None, None
    done: list[TraceSummary] = []
    for index, folder in enumerate(conversations.folders(run_dir, spec)):
        current_spec = conversations.turn_spec(spec, index)
        left = invocation.turns_left(spec, done)
        if left is not None and left <= 0:  # the conversation spent its limit, so no follow-up started
            return (
                "native follow-up ran past the conversation's turn limit; re-run the trial" if folder.exists() else None
            )
        trace_path, metadata_path = folder / "stdout.jsonl", folder / "invocation.json"
        if not trace_path.is_file():
            return "native conversation trace missing; re-run the trial"
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            trace = tracing.parse_trace(trace_path)
        except (OSError, ValueError):
            return _INVALID_NATIVE_EVIDENCE
        legacy_timeout = (
            isinstance(metadata, dict)
            and "cut_short" not in metadata
            and _SAVED_TIMEOUT.fullmatch(str(metadata.get("inconclusive") or "")) is not None
        )
        saved_cut = isinstance(metadata, dict) and (metadata.get("cut_short") is True or legacy_timeout)
        if (
            not isinstance(metadata, dict)
            or not tracing.is_rooted(metadata.get("workspace"))
            or not (type(metadata.get("exit_code")) is int or (saved_cut and metadata.get("exit_code") is None))
            or not {"expected_model", "resume", "inconclusive"} <= metadata.keys()
        ):
            return _INVALID_NATIVE_EVIDENCE
        if metadata["inconclusive"] and not saved_cut:
            return str(metadata["inconclusive"])
        recorded_workspace = Path(metadata["workspace"]).resolve()
        if (
            metadata.get("resume") != resume
            or metadata["expected_model"] != spec.get("expected_model")
            or (workspace is not None and recorded_workspace != workspace)
        ):
            return "native invocation session, workspace, or model binding changed; re-run the trial"
        argv = metadata.get("argv")
        if not isinstance(argv, list) or not all(isinstance(arg, str) for arg in argv):
            return "native invocation agent command evidence missing; re-run the trial"
        if conversations.enabled(spec):
            for flag, expected in (("--resume", [resume] if resume else []), ("--max-turns", [str(left)])):
                observed = [argv[i + 1] if i + 1 < len(argv) else None for i, arg in enumerate(argv) if arg == flag]
                if observed != expected:
                    return "incident saved resume or cumulative turn-budget command differs"
            if "--no-session-persistence" in argv or "--restricted" not in argv:
                return "incident saved command did not persist a restricted session"
        pins = [argv[i + 1] if i + 1 < len(argv) else None for i, arg in enumerate(argv) if arg == "--agent"]
        pin = catalog.agent_pin(spec)
        if pins != ([pin] if pin else []):
            return "native invocation agent pin differs from scenario; re-run the trial"
        if invocation.credential_markers(trace.result_text, trace_path):
            return "native credential marker detected; re-run the trial"
        try:
            if legacy_timeout:
                if not recorded_plugin_sha:
                    return "native timeout plugin digest evidence missing; re-run the trial"
                # Before cut_short was recorded a timeout bypassed the live boundary checks. Recover
                # it only from unchanged inputs and the partial trace's actual profile and session.
                problem = (
                    fingerprints.plugin_drift_problem(plugin_root, recorded_plugin_sha)
                    or invocation.profile_problem(trace, spec, plugin_root, recorded_workspace)
                    or invocation.native_identity_problem(trace, current_spec, resume, complete=False)
                )
            else:
                problem = invocation.invocation_problem(
                    trace, metadata["exit_code"], current_spec, plugin_root, recorded_workspace, resume
                )
        except (OSError, json.JSONDecodeError) as exc:
            return _unreadable_root(plugin_root, exc)
        except clean_room.AuthUnavailable:
            return "native invocation reported an authentication failure; re-run the trial"
        if problem and not (saved_cut and isinstance(problem, CutShort)):
            return problem
        if (
            metadata.get("session_id") != trace.session_id
            or metadata.get("main_models") != trace.main_models
            or metadata.get("init_session_ids") != trace.init_session_ids
        ):
            return "native invocation identity differs from its trace; re-run the trial"
        if saved_cut:
            # The partial trace still shows the declared identity; the saved stop stays a cut, so
            # a forbidding check it already failed survives the regrade. No follow-up started.
            try:
                stop = Stop.WALL_CLOCK if legacy_timeout else metadata.get("run_stop") or Stop.UNRECORDED
                return CutShort(str(metadata["inconclusive"]), stop)
            except ValueError:  # a saved stop this runner does not know
                return _INVALID_NATIVE_EVIDENCE
        resume, workspace = trace.session_id, recorded_workspace
        done.append(trace)
    left = invocation.turns_left(spec, done)
    if left is not None and left < 0:
        return "native conversation ran past its turn limit; re-run the trial"
    return None


def regrade_run(
    run_dir: Path,
    spec: Spec,
    *,
    write: bool = True,
    relax_identity: bool = False,
) -> dict[str, Any]:
    """Re-score an unchanged scenario; keep only exactly identified original live verdicts.

    `write=False` leaves the run untouched and only returns the grade. `relax_identity` grades a run
    whose saved scenario identity differs, as it does after any runner edit because the identity
    binds the runner's source; kept verdicts are then found under the saved identity, and the grade
    is marked `identity_relaxed` so it serves only to compare runners on the same trace.
    """
    summary = json.loads((run_dir / "outputs" / "trace-summary.json").read_text(encoding="utf-8"))
    with _served_plugin_root(summary) as (plugin_root, has_plugin_root):
        return _regrade_run(
            run_dir, spec, summary, plugin_root, has_plugin_root, write=write, relax_identity=relax_identity
        )


def load_evidence(run_dir: Path, spec: Spec) -> evidence.EvidenceV1:
    """A saved run as evidence-v1: its own `evidence.json` when it wrote one, else what `legacy`
    reads back from the files a pre-evidence run kept, with the raw trace re-parsed when it survives."""
    summary = json.loads((run_dir / "outputs" / "trace-summary.json").read_text(encoding="utf-8"))
    recorded = summary.get("workspace")
    with _served_plugin_root(summary) as (plugin_root, _has_plugin_root):
        return _evidence(
            run_dir,
            spec,
            summary,
            plugin_root,
            Path(recorded) if isinstance(recorded, str) and tracing.is_rooted(recorded) else None,
            reparse=True,
        )


def _evidence(
    run_dir: Path,
    spec: Spec,
    summary: Mapping[str, Any],
    plugin_root: Path,
    recorded_workspace: Path | None,
    *,
    reparse: bool,
) -> evidence.EvidenceV1:
    """The run's evidence: as written, or as `legacy` reads a pre-evidence directory back."""
    own = run_dir / evidence.FILE
    if own.is_file():
        return evidence.EvidenceV1.model_validate_json(own.read_text(encoding="utf-8"))
    live_grade = json.loads(layout.live_grade(run_dir).read_text(encoding="utf-8"))
    text = (run_dir / "outputs" / "response.md").read_text(encoding="utf-8")
    saved = legacy.reconstruct(run_dir, summary, text, reparse=reparse)
    with tempfile.TemporaryDirectory(prefix="evidence-") as tmp:
        ws = legacy.workspace(Path(tmp), summary, saved, recorded_workspace)
        return legacy.evidence_of(run_dir, spec, summary, saved, ws, live_grade, plugin_root)


@contextlib.contextmanager
def _served_plugin_root(summary: Mapping[str, Any]) -> Iterator[tuple[Path, bool]]:
    """The plugin root a regrade measures the run against, and whether the run recorded one.

    A run served an image of the measured inputs is measured against that path, restaged from the
    saved plugin root while the regrade runs when it left with the workspace; a run served the
    checkout itself is measured against the saved root. A saved root the regrade cannot read is
    reported where the root is read, as it is for a run served the checkout.
    """
    plugin = summary.get("plugin") or {}
    saved = plugin.get("plugin_root")
    has_plugin_root = isinstance(saved, str) and tracing.is_rooted(saved)
    root = Path(saved) if has_plugin_root and isinstance(saved, str) else ROOT
    served = plugin.get("plugin_served_from")
    if not (isinstance(served, str) and tracing.is_rooted(served)):
        yield root, has_plugin_root
        return
    image = Path(served)
    if image.exists():
        yield image, has_plugin_root
        return
    created = image  # the topmost directory restaging creates: the trial's workspace root is gone too
    while not created.parent.exists() and created.parent != created:
        created = created.parent
    with contextlib.suppress(OSError, RuntimeError):
        fingerprints.stage_plugin(root, image)
    try:
        yield image, has_plugin_root
    finally:
        shutil.rmtree(created, ignore_errors=True)


def _regrade_run(
    run_dir: Path,
    spec: Spec,
    summary: Mapping[str, Any],
    plugin_root: Path,
    has_plugin_root: bool,
    *,
    write: bool,
    relax_identity: bool,
) -> dict[str, Any]:
    live_grade = json.loads(layout.live_grade(run_dir).read_text(encoding="utf-8"))
    old_by_id = {e.get("id"): e for e in live_grade.get("expectations", [])}
    saved_binding = live_grade.get("judge_binding")
    identity = fingerprints.scenario_digest(spec, saved_binding)
    identity_matches = live_grade.get("scenario_sha256") == identity
    relaxed = relax_identity and not identity_matches
    native_problem = (
        native_regrade_problem(
            run_dir,
            spec,
            plugin_root,
            recorded_plugin_sha=(summary.get("plugin") or {}).get("plugin_source_sha256") if has_plugin_root else None,
        )
        if spec.get("followups")
        else None
    )
    native_cut = native_problem if isinstance(native_problem, CutShort) else None
    saved_workspace = summary.get("workspace")
    if spec.get("followups") and (native_problem is None or native_cut):
        # Native invocation metadata already passed the per-turn boundary checks above.
        saved_workspace = json.loads((run_dir / "invocation.json").read_text(encoding="utf-8"))["workspace"]
    recorded_workspace = (
        Path(saved_workspace) if isinstance(saved_workspace, str) and tracing.is_rooted(saved_workspace) else None
    )
    # The run's evidence, its raw trace re-parsed with the live parser when the run kept no evidence
    # of its own: an incomplete stream preserves positive observations but cannot establish an
    # absent call, which validated summary counts fill (legacy.reconstruct).
    found = _evidence(
        run_dir, spec, summary, plugin_root, recorded_workspace, reparse=not native_problem or bool(native_cut)
    )
    trace = engine.trace_of(found)
    has_raw_trace = not found.trace.restored_from_summary
    judge_problem = _saved_judge_problem(spec, saved_binding)
    inconclusive = _run_level_reason(
        spec,
        live_grade,
        summary,
        trace,
        native_problem,
        saved_binding,
        judge_problem=judge_problem,
        has_raw_trace=has_raw_trace,
        has_plugin_root=has_plugin_root,
        plugin_root=plugin_root,
        workspace=recorded_workspace,
    )
    if not identity_matches and not relaxed:
        inconclusive = "saved scenario identity is missing or changed; re-run the trial"
    elif len(old_by_id) != len(live_grade.get("expectations", [])):
        inconclusive = "saved assertion identities are duplicated; re-run the trial"
    stale_judge = (
        f"{judge_problem}; the kept judgment needs a re-run under the current judge"
        if isinstance(judge_problem, rubric_judge.JudgeExecutionChanged)
        else None
    )
    # Routing, pinned-skill, reference, and non-rubric grader verdicts all come from the saved
    # trace, so a routing or contract run regrades like a build run. A rubric grader would spend
    # a live judge call, so it keeps the verdict the live batch paid for, found by its position.
    kept = engine.kept_from(found, stale_judge=stale_judge, mark=True)
    verdict = engine.grade(spec, found, kept, plugin_root=plugin_root, run_level=inconclusive)
    if fingerprints.scenario_digest(spec, saved_binding) != identity:
        inconclusive = "scenario inputs changed during regrade; re-run the trial"
        verdict = engine.grade(spec, found, kept, plugin_root=plugin_root, run_level=inconclusive)
    rendered = engine.render(verdict, spec)
    grading = {
        **rendered,
        "judge_binding": saved_binding,
        "response_sha256": live_grade.get("response_sha256"),
        "scenario_sha256": rendered["scenario_sha256"] if identity_matches else live_grade.get("scenario_sha256"),
        "plugin_source_sha256": (summary.get("plugin") or {}).get("plugin_source_sha256"),
        "runtime": summary.get("runtime"),
        "models": trace.models if has_raw_trace else list(summary.get("models") or []),
        "regraded": True,
        **({"identity_relaxed": True} if relaxed else {}),
    }
    if not write:
        return grading
    # The evidence the regrade graded is written beside its assessment; the live attempt's folder
    # is never rewritten (result rule 8).
    return _add_assessment(run_dir, grading, summary, trace if has_raw_trace else None, found)


def _run_level_reason(
    spec: Spec,
    live_grade: Mapping[str, Any],
    summary: Mapping[str, Any],
    trace: TraceSummary,
    native_problem: str | None,
    saved_binding: Any,
    *,
    judge_problem: rubric_judge.JudgeUnavailable | None,
    has_raw_trace: bool,
    has_plugin_root: bool,
    plugin_root: Path,
    workspace: Path | None,
) -> str | None:
    """Why the regrade cannot measure the run at all, or how it was cut short, from saved evidence."""
    inconclusive: str | None
    if isinstance(native_problem, CutShort):
        inconclusive = native_problem
    elif live_grade.get("run_end") == Ending.CUT_SHORT and not native_problem:
        # A cut-short FAIL keeps its reason under `unmeasured`; its forbidding checks still count.
        inconclusive = CutShort(
            live_grade.get("inconclusive") or live_grade.get("unmeasured") or "run cut short",
            live_grade.get("run_stop") or Stop.UNRECORDED,
        )
    else:
        inconclusive = _saved_void(live_grade, summary) or native_problem
        recorded_sha = (summary.get("plugin") or {}).get("plugin_source_sha256")
        older_timeout = (
            not native_problem
            and not {"run_end", "void"} & live_grade.keys()
            and _SAVED_TIMEOUT.fullmatch(str(inconclusive or ""))
        )
        if older_timeout and has_raw_trace and has_plugin_root and workspace is not None and recorded_sha:
            # A grade saved before `run_end` voided a timeout, and its runner never checked drift on
            # one. In the live path's order, the plugin inputs must still hash as the run recorded and
            # the partial trace must show the declared profile; then the run is cut short, so a
            # forbidden action before the timeout still fails (result rules 2 and 4). Otherwise void.
            try:
                problem = fingerprints.plugin_drift_problem(plugin_root, str(recorded_sha)) or (
                    invocation.profile_problem(trace, spec, plugin_root, workspace)
                )
            except (OSError, json.JSONDecodeError) as exc:
                problem = _unreadable_root(plugin_root, exc)
            inconclusive = problem or CutShort(str(inconclusive), Stop.WALL_CLOCK)
    if spec.get("references") and not has_plugin_root:
        inconclusive = "reference plugin root evidence missing or invalid; re-run the trial"
    if fingerprints.required_rubrics(spec) and (
        not saved_binding or live_grade.get("response_sha256") != rubric_judge._digest(trace.result_text)
    ):
        inconclusive = "saved judge binding or judged response identity is missing or changed; re-run the trial"
    elif judge_problem is not None and not isinstance(judge_problem, rubric_judge.JudgeExecutionChanged):
        inconclusive = str(judge_problem)
    if has_raw_trace and str(inconclusive or "").startswith(invocation.BLOCKED_TOOLS):
        # The denial rule is re-derived from the raw trace so a regrade applies the live rule
        # (a subagent's refusal no longer voids a routing verdict), not the one saved that day.
        blocked = invocation.runtime_blocked_tools(trace, spec)
        inconclusive = f"{invocation.BLOCKED_TOOLS}: {blocked}" if blocked else None
    return inconclusive


def _saved_void(live_grade: Mapping[str, Any], summary: Mapping[str, Any]) -> str | None:
    """The reason the live grade measured nothing at all, if it had one (result rule 1).

    A grade's `inconclusive` names the first reason anything went unmeasured: a run-level failure,
    such as a wrong plugin or changed inputs, or one check's own, such as an instrument failure, a
    judge that could not judge, or an unavailable service. Only the first voids the run. Reading
    the second as run-level would void checks the live grade measured, and hide a supported FAIL
    beside the unmeasured check (rule 3). A current grade records a run-level reason as `void`; an
    older one did not, so its reason is run-level only when every saved check carries it.
    """
    if live_grade.get("void"):
        return str(live_grade["void"])
    if live_grade.get("grader_error"):
        # The grade names a grading-machinery failure: the check's, recorded as a grader error and
        # never in rule 1's form (result rule 5, amended 2026-11-02), so the regrade re-measures.
        return None
    reason = live_grade.get("inconclusive", summary.get("inconclusive"))
    if not reason:
        return None
    marked = f"{UNMEASURED}{reason}"[:EVIDENCE_LIMIT]
    expectations = live_grade.get("expectations") or []
    return str(reason) if all(str(e.get("evidence") or "") == marked for e in expectations) else None


def _saved_judge_problem(spec: Spec, saved_binding: Any) -> rubric_judge.JudgeUnavailable | None:
    """Why the judge binding a run saved no longer validates, or None, as for a run that has none.

    `JudgeExecutionChanged`, a judge whose code or configuration differs from the one the binding
    certified, leaves only each kept judgment INCONCLUSIVE: the checks the saved trace re-measures
    keep their verdicts, so a supported FAIL beside them still fails (result rule 3). Any other
    binding problem voids the whole run in `_run_level_reason`.
    """
    required = fingerprints.required_rubrics(spec)
    if not required or not saved_binding:
        return None
    try:
        rubric_judge.validate_binding(rubric_judge.JudgeBinding(json.dumps(saved_binding)), required, current=False)
    except rubric_judge.JudgeUnavailable as exc:
        return exc
    return None


def _add_assessment(
    run_dir: Path,
    grading: dict[str, Any],
    summary: Mapping[str, Any],
    trace: TraceSummary | None,
    found: evidence.EvidenceV1,
) -> dict[str, Any]:
    """Write a regrade as assessments/<k>/ beside the run's original grade, never over it
    (threat-model ADR result rule 8), with the evidence it graded, and list it in the attempt's v1
    record."""
    revisions = run_dir / "assessments"
    revision = layout.next_number(revisions)
    target = rules.rule_8_regrade_adds(run_dir, revision)
    target.mkdir(parents=True)
    evidence.write(target, found)
    grading = {
        **grading,
        "assessment_revision": revision,
        "assessed_at": records.utc_now(),
        "runner_source_sha256": HARNESS_SOURCE_SHA256,
    }
    layout.write_json(target / "grading.json", grading)
    # This assessment's own trace summary: its verdict, and every trace fact the run saved as this
    # runner reads it when the raw trace survives; the live run's summary beside it stays as recorded.
    refreshed = {
        **summary,
        "status": grading["status"],
        "inconclusive": grading["inconclusive"],
        "scenario_sha256": grading["scenario_sha256"],
        "regraded": True,
        **(tracing.to_saved(trace) if trace is not None else {}),
    }
    layout.write_json(target / "trace-summary.json", refreshed)
    entry = {
        "revision": revision,
        "status": grading["status"],
        "reason": grading.get("inconclusive") or grading.get("unmeasured"),
        "grading": f"assessments/{revision}/grading.json",
        "runner_source_sha256": HARNESS_SOURCE_SHA256,
        "assessed_at": grading["assessed_at"],
    }
    records.update_record(run_dir, lambda record: record.setdefault("assessments", []).append(entry))
    return grading


def _saved_runs(
    iteration_dir: Path, scenarios: list[dict[str, Any]]
) -> tuple[list[tuple[dict[str, Any], Path, dict[str, Any]]], dict[str, Any]]:
    """Each published run in an iteration with its scenario and the row naming it, a run being a
    `layout` slot folder holding a trace summary, and what was passed over: a scenario not loaded, a
    folder that is not a numbered run (an operator's `run-1-old`), and a run without a trace summary.
    Nothing is dropped silently."""
    by_id = {s["id"]: s for s in scenarios}
    runs: list[tuple[dict[str, Any], Path, dict[str, Any]]] = []
    skipped: dict[str, Any] = {"scenarios": [], "other_run_folders": [], "runs_without_trace_summary": 0}
    for case_dir in layout.case_dirs(iteration_dir):
        spec = by_id.get(layout.case_id(case_dir))
        if spec is None:  # retired, renamed, or excluded by --scenario
            skipped["scenarios"].append(layout.case_id(case_dir))
            continue
        for run_dir in sorted(case_dir.glob(f"*/{layout.SLOT_PREFIX}*")):
            slot = layout.slot(run_dir.name)
            if slot is None:
                skipped["other_run_folders"].append(run_dir.relative_to(iteration_dir).as_posix())
            elif not (run_dir / "outputs" / "trace-summary.json").exists():
                skipped["runs_without_trace_summary"] += 1
            else:
                runs.append((spec, run_dir, {"scenario": spec["id"], "label": run_dir.parent.name, "run": slot}))
    return runs, skipped


def regrade(iteration_dir: Path, scenarios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    runs, skipped = _saved_runs(iteration_dir, scenarios)
    results = []
    for spec, run_dir, row in runs:
        g = regrade_run(run_dir, spec)
        results.append(
            {
                "scenario": row["scenario"],
                "label": row["label"],
                **assessment.native_assessment(spec),
                "run": row["run"],
                "status": g["status"],
                "passed": g["summary"]["passed"],
                "total": g["summary"]["total"],
                "scenario_sha256": g["scenario_sha256"],
                "plugin_source_sha256": g["plugin_source_sha256"],
                "runtime": g["runtime"],
                "models": g["models"],
                "inconclusive": g["inconclusive"],
            }
        )
    # Saved summaries keep the verdicts their batch recorded; the regrade's rows go beside them.
    if results:
        layout.write_json(
            iteration_dir / f"regrade-{records.utc_now().replace(':', '')}.json",
            {"runner": HARNESS_IDENTITY, "runs": results, "skipped": skipped},
        )
    return results


# A regrade bounds a kept marker and its evidence together to EVIDENCE_LIMIT; what any two grades of
# the same evidence surely share of an expectation's evidence is the bound less the longest marker.
_KEPT_MARKER = re.compile(r"^\[kept: [\w-]+\] ")
_COMMON_EVIDENCE = EVIDENCE_LIMIT - len("[kept: workspace-dependent] ")


def comparable(grading: Mapping[str, Any]) -> dict[str, Any]:
    """The verdict of a grade: everything but what is beside it, which two grades of the same
    evidence may differ in without disagreeing (identities and digests, the judge binding, times, the
    after-assessment record of rule 6, a regrade's kept markers, and the tail of bounded evidence)."""
    return {
        "status": grading.get("status"),
        "inconclusive": grading.get("inconclusive"),
        "unmeasured": grading.get("unmeasured"),
        "void": grading.get("void"),
        "run_end": grading.get("run_end"),
        "run_stop": grading.get("run_stop"),
        "grader_error": grading.get("grader_error"),
        "expectations": [
            {
                "text": e.get("text"),
                "kind": e.get("kind"),
                "state": e.get("state"),
                "passed": e.get("passed"),
                "evidence": _KEPT_MARKER.sub("", str(e.get("evidence") or ""))[:_COMMON_EVIDENCE],
            }
            for e in grading.get("expectations") or []
        ],
        "summary": {key: (grading.get("summary") or {}).get(key) for key in ("passed", "failed", "total")},
    }


def differences(saved: Mapping[str, Any], graded: Mapping[str, Any]) -> list[str]:
    """Each place two grades' verdicts differ, as `path: saved != graded`."""
    found: list[str] = []
    _walk(comparable(saved), comparable(graded), "", found)
    return found


def _walk(left: Any, right: Any, path: str, found: list[str]) -> None:
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(left.keys() | right.keys()):
            _walk(left.get(key), right.get(key), f"{path}.{key}" if path else str(key), found)
    elif isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
        for index, (a, b) in enumerate(zip(left, right, strict=True)):
            _walk(a, b, f"{path}[{index}]", found)
    elif left != right:
        found.append(f"{path}: {left!r} != {right!r}")


def evidence_check(iteration_dir: Path, scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    """Grade every published run that wrote `evidence.json` from that evidence alone, under the
    run level its ending records and the probe outcomes it holds, and compare each verdict with the
    run's own `grading.json`. A difference means the evidence lacks something the live grade read,
    or the scenario changed since the run (`scenario_changed`); a run saved before evidence-v1 is
    counted, not checked. Nothing is written."""
    runs, skipped = _saved_runs(iteration_dir, scenarios)
    rows: list[dict[str, Any]] = []
    without_evidence = 0
    for spec, run_dir, row in runs:
        if not (run_dir / evidence.FILE).is_file():
            without_evidence += 1
            continue
        try:
            found = evidence.EvidenceV1.model_validate_json((run_dir / evidence.FILE).read_text(encoding="utf-8"))
            saved = json.loads(layout.live_grade(run_dir).read_text(encoding="utf-8"))
            summary = json.loads((run_dir / "outputs" / "trace-summary.json").read_text(encoding="utf-8"))
            with _served_plugin_root(summary) as (plugin_root, _has_plugin_root):
                graded = engine.render(engine.grade(spec, found, plugin_root=plugin_root), spec)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            rows.append({**row, "error": f"{type(exc).__name__}: {exc}"[:300]})
            continue
        rows.append(
            {
                **row,
                "differences": differences(saved, graded),
                "scenario_changed": found.identity.case_sha256 not in (None, fingerprints.case_digest(spec)),
            }
        )
    return {"runs": rows, "skipped": {**skipped, "runs_without_evidence": without_evidence}}


def _verdicts(grading: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": grading.get("status"),
        "checks": [
            {"text": e.get("text"), "state": outcomes.legacy_state(e), "evidence": str(e.get("evidence") or "")[:200]}
            for e in grading.get("expectations") or []
        ],
    }


def rescore(iteration_dir: Path, scenarios: list[dict[str, Any]], out_dir: Path) -> dict[str, Any]:
    """Grade every saved run with this runner into `out_dir`, leaving the saved runs untouched, and
    return the record written as `out_dir/rescore.json`.

    A saved scenario identity binds the runner that graded it, so after any runner edit `--regrade`
    voids every run. Rescoring grades across that change and marks such runs `identity_relaxed`:
    two rescores of the same runs, one per runner revision, show what the edit changed
    (`rescore_diff`). A rescore is a comparison, never a verdict of its own.
    """
    runs, skipped = _saved_runs(iteration_dir, scenarios)
    rows = []
    for spec, run_dir, row in runs:
        try:
            saved = json.loads(layout.live_grade(run_dir).read_text(encoding="utf-8"))
            grading = regrade_run(run_dir, spec, write=False, relax_identity=True)
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
            # One unreadable or older-shaped run stays visible instead of ending the comparison.
            rows.append({**row, "error": f"{type(exc).__name__}: {exc}"[:300]})
            continue
        target = out_dir / run_dir.relative_to(iteration_dir)
        try:
            target.mkdir(parents=True)
            layout.write_json(target / "grading.json", grading)
        except OSError as exc:  # e.g. a path past Windows' 260-character limit: report it, keep going
            rows.append({**row, "error": f"cannot write the rescored grade: {type(exc).__name__}: {exc}"[:300]})
            continue
        rows.append(
            {
                **row,
                "identity_relaxed": bool(grading.get("identity_relaxed")),
                "saved": _verdicts(saved),
                "rescored": _verdicts(grading),
            }
        )
    record = {"runner": HARNESS_IDENTITY, "iteration": str(iteration_dir), "runs": rows, "skipped": skipped}
    layout.write_json(out_dir / "rescore.json", record)
    return record


def rescore_diff(base: Mapping[str, Any], candidate: Mapping[str, Any]) -> list[str]:
    """Each run and check whose rescored verdict differs between two rescores of the same runs."""

    def outcome(row: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"status": "ERROR", "checks": []} if row.get("error") else row.get("rescored") or {}

    left = {layout.run_key(r): r for r in base.get("runs") or []}
    right = {layout.run_key(r): r for r in candidate.get("runs") or []}
    lines = []
    for k in sorted(left.keys() | right.keys(), key=lambda k: tuple(str(part) for part in k)):
        name = layout.run_name(*k)
        if k not in left or k not in right:
            lines.append(f"{name}: rescored only by the {'candidate' if k not in left else 'base'} runner")
            continue
        a, b = outcome(left[k]), outcome(right[k])
        if a.get("status") != b.get("status"):
            lines.append(f"{name}: {a.get('status')} -> {b.get('status')}")
        checks_a, checks_b = a.get("checks") or [], b.get("checks") or []
        for index in range(max(len(checks_a), len(checks_b))):
            ca = checks_a[index] if index < len(checks_a) else {}
            cb = checks_b[index] if index < len(checks_b) else {}
            if (ca.get("text"), ca.get("state")) != (cb.get("text"), cb.get("state")):
                lines.append(
                    f"{name} check {index}: {ca.get('text')!r} {ca.get('state')} -> "
                    f"{cb.get('text')!r} {cb.get('state')}: {cb.get('evidence') or ca.get('evidence')}"
                )
    return lines


def load_rescore(path: Path) -> dict[str, Any]:
    record = json.loads(((path / "rescore.json") if path.is_dir() else path).read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise ValueError(f"{path} is not a rescore record")
    return record
