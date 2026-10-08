"""Grade saved runs again: a regrade beside the run, a rescore into a new folder, and a diff of two.

A regrade re-measures what the saved run still supports -- the raw trace, the final text, the state
files and git facts the summary recorded -- and keeps the live verdict of anything else, by position
under the saved scenario identity: a paid rubric judgment, or a check whose evidence left with the
workspace. When the raw trace is gone, what only it held is INCONCLUSIVE, check by check. It never
rewrites the run (threat-model ADR result rule 8). Grading itself is the same
`assessment.assess` loop the live grade uses.
"""

from __future__ import annotations

import json
import re
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import clean_room
import judge as rubric_judge

from . import assessment, checking, fingerprints, invocation, outcomes, records, tracing
from .checking import Context
from .constants import ROOT
from .fingerprints import HARNESS_IDENTITY, HARNESS_SOURCE_SHA256
from .outcomes import EVIDENCE_LIMIT, UNMEASURED, CutShort, Outcome
from .tracing import TraceSummary
from .workspaces import GitFacts, Workspace

Spec = Mapping[str, Any]


_INVALID_NATIVE_EVIDENCE = "native invocation boundary evidence missing or invalid; re-run the trial"


def native_regrade_problem(run_dir: Path, spec: Spec, plugin_root: Path) -> str | None:
    """Replay each invocation's boundary checks using its saved cwd after the workspace is gone.

    Saved evidence that is missing or malformed, or a plugin root the regrade cannot read, leaves the
    run unmeasured under a reason that names it; a defect in the runner raises instead of being
    reported as the saved run's fault.
    """
    resume, workspace = None, None
    for folder in (run_dir, run_dir / "followup"):
        trace_path, metadata_path = folder / "stdout.jsonl", folder / "invocation.json"
        if not trace_path.is_file():
            return "native conversation trace missing; re-run the trial"
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            trace = tracing.parse_trace(trace_path)
        except (OSError, ValueError):
            return _INVALID_NATIVE_EVIDENCE
        saved_cut = isinstance(metadata, dict) and metadata.get("cut_short") is True
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
        pins = [argv[i + 1] if i + 1 < len(argv) else None for i, arg in enumerate(argv) if arg == "--agent"]
        expected_pins = [f"save-toolkit:{spec['agent']}"] if spec.get("agent") else []
        if pins != expected_pins:
            return "native invocation agent pin differs from scenario; re-run the trial"
        if invocation.credential_markers(trace.result_text, trace_path):
            return "native credential marker detected; re-run the trial"
        try:
            problem = invocation.invocation_problem(
                trace, metadata["exit_code"], spec, plugin_root, recorded_workspace, resume
            )
        except (OSError, json.JSONDecodeError) as exc:
            return f"plugin root {plugin_root} could not be read ({type(exc).__name__}); restore it to regrade the run"
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
                return CutShort(str(metadata["inconclusive"]), metadata.get("run_stop") or "cut_short")
            except ValueError:  # a saved stop this runner does not know
                return _INVALID_NATIVE_EVIDENCE
        resume, workspace = trace.session_id, recorded_workspace
    return None


def regrade_run(run_dir: Path, spec: Spec, *, write: bool = True, relax_identity: bool = False) -> dict[str, Any]:
    """Re-score an unchanged scenario; keep only exactly identified original live verdicts.

    `write=False` leaves the run untouched and only returns the grade. `relax_identity` grades a run
    whose saved scenario identity differs, as it does after any runner edit because the identity
    binds the runner's source; kept verdicts are then found under the saved identity, and the grade
    is marked `identity_relaxed` so it serves only to compare runners on the same trace.
    """
    summary = json.loads((run_dir / "outputs" / "trace-summary.json").read_text(encoding="utf-8"))
    old = json.loads((run_dir / "grading.json").read_text(encoding="utf-8"))
    original = run_dir / "grading.original.json"
    live_grade = json.loads(original.read_text(encoding="utf-8")) if original.exists() else old
    old_by_id = {e.get("id"): e for e in live_grade.get("expectations", [])}
    saved_binding = live_grade.get("judge_binding")
    identity = fingerprints.scenario_digest(spec, saved_binding)
    identity_matches = live_grade.get("scenario_sha256") == identity
    relaxed = relax_identity and not identity_matches
    kept_prefix = live_grade.get("scenario_sha256") if relaxed else identity
    text = (run_dir / "outputs" / "response.md").read_text(encoding="utf-8")
    saved_plugin_root = (summary.get("plugin") or {}).get("plugin_root")
    has_plugin_root = isinstance(saved_plugin_root, str) and tracing.is_rooted(saved_plugin_root)
    plugin_root = Path(saved_plugin_root) if has_plugin_root and isinstance(saved_plugin_root, str) else ROOT
    native_problem = native_regrade_problem(run_dir, spec, plugin_root) if spec.get("followups") else None
    native_cut = native_problem if isinstance(native_problem, CutShort) else None
    saved_workspace = summary.get("workspace")
    if spec.get("followups") and (native_problem is None or native_cut):
        # Native invocation metadata already passed the per-turn boundary checks above.
        saved_workspace = json.loads((run_dir / "invocation.json").read_text(encoding="utf-8"))["workspace"]
    recorded_workspace = (
        Path(saved_workspace) if isinstance(saved_workspace, str) and tracing.is_rooted(saved_workspace) else None
    )
    # The raw trace is the truth: a saved summary carries whatever the parser of the day recorded,
    # so re-parse it with the live path's own parser and fall back only when the trace is absent.
    stdout_path = run_dir / "stdout.jsonl"
    reparsed = (
        tracing.parse_trial_trace(run_dir) if stdout_path.is_file() and (not native_problem or native_cut) else None
    )
    if reparsed is not None:
        trace = reparsed
        if not trace.result_text:  # a truncated trace must not silently blank every text check
            trace.result_text = text
    else:
        trace = _summary_trace(summary, text)
    before, after = summary.get("commits_before_after") or [0, 0]
    git = GitFacts(
        int(after),
        str(summary.get("branch") or ""),
        [tuple(x) for x in summary.get("changed_files") or []],
        "",
        str(summary["git_problem"]) if summary.get("git_problem") else None,
    )
    with tempfile.TemporaryDirectory(prefix="regrade-") as tmp:
        state = Path(tmp) / "state"
        state.mkdir()
        for name, content in (summary.get("state_files") or {}).items():
            (state / name).write_text(content, encoding="utf-8")
        ws = Workspace(
            Path(tmp),
            Path(tmp) / "repo-gone",
            Path(tmp) / "bin",
            state,
            int(before),
            "main",
            command_repo=recorded_workspace,
        )
        if summary.get("agents_dir"):
            (ws.repo / ".agents").mkdir(parents=True)
        ctx = Context(dict(spec), ws, trace, git, plugin_root=plugin_root)
        inconclusive = _run_level_reason(
            spec,
            live_grade,
            summary,
            trace,
            native_problem,
            saved_binding,
            has_raw_trace=reparsed is not None,
            has_plugin_root=has_plugin_root,
        )
        if not identity_matches and not relaxed:
            inconclusive = "saved scenario identity is missing or changed; re-run the trial"
        elif len(old_by_id) != len(live_grade.get("expectations", [])):
            inconclusive = "saved assertion identities are duplicated; re-run the trial"
        # Routing, pinned-skill, reference, and non-rubric grader verdicts all come from the saved
        # trace, so a routing or contract run regrades like a build run. A rubric grader would spend
        # a live judge call, so it keeps the verdict the live batch paid for.
        items = assessment.plan(
            spec, trace, ctx, ctx.plugin_root, workspace=recorded_workspace, keep=True, raw_trace=reparsed is not None
        )
        kept = _saved_verdicts(old_by_id, kept_prefix, stale_judge=_stale_judge(spec, saved_binding))
        graded, unmeasured = assessment.assess(items, inconclusive, kept=kept)
    if fingerprints.scenario_digest(spec, saved_binding) != identity:
        inconclusive = "scenario inputs changed during regrade; re-run the trial"
        graded = assessment.unmeasured_all(graded, inconclusive)
    status, reason = assessment.roll_up([g.outcome for g in graded], inconclusive or unmeasured)
    # Without the raw trace the CLI's stop reason is gone; the live grade recorded what it saw.
    turn_limit = not inconclusive and (
        invocation.reached_turn_limit(trace, spec)
        if reparsed is not None
        else live_grade.get("run_end") == "turn_limit"
    )
    expectations = assessment.records(graded)
    grading = {
        **assessment.native_assessment(spec),
        "judge_binding": saved_binding,
        "response_sha256": live_grade.get("response_sha256"),
        "expectations": expectations,
        "scenario_sha256": (
            fingerprints.stamp_assertions(identity, expectations)
            if identity_matches
            else live_grade.get("scenario_sha256")
        ),
        "plugin_source_sha256": (summary.get("plugin") or {}).get("plugin_source_sha256"),
        "runtime": summary.get("runtime"),
        "models": trace.models if reparsed is not None else list(summary.get("models") or []),
        "summary": assessment.summary_of(expectations),
        "status": status,
        "regraded": True,
        **assessment.run_fields(status, reason, inconclusive, turn_limit=turn_limit),
        **({"identity_relaxed": True} if relaxed else {}),
    }
    if not write:
        return grading
    return _add_assessment(run_dir, grading, summary, trace if reparsed is not None else None)


def _summary_trace(summary: Mapping[str, Any], text: str) -> TraceSummary:
    """The trace facts a saved summary restores when the raw trace is gone."""
    return TraceSummary(
        result_text=text,
        skills=list(summary.get("skills") or []),
        skills_failed=list(summary.get("skills_failed") or []),
        bash_commands=list(summary.get("bash_commands") or []),
        subagent_bash_commands=list(summary.get("subagent_bash_commands") or []),
        powershell_commands=list(summary.get("powershell_commands") or []),
        dispatches=list(summary.get("dispatches") or []),
        tool_errors=list(summary.get("tool_errors") or []),
        tool_counts=dict(summary.get("tool_counts") or {}),
    )


def _run_level_reason(
    spec: Spec,
    live_grade: Mapping[str, Any],
    summary: Mapping[str, Any],
    trace: TraceSummary,
    native_problem: str | None,
    saved_binding: Any,
    *,
    has_raw_trace: bool,
    has_plugin_root: bool,
) -> str | None:
    """Why the regrade cannot measure the run at all, or how it was cut short, from saved evidence."""
    inconclusive: str | None
    if isinstance(native_problem, CutShort):
        inconclusive = native_problem
    elif live_grade.get("run_end") == "cut_short" and not native_problem:
        # A cut-short FAIL keeps its reason under `unmeasured`; its forbidding checks still count.
        inconclusive = CutShort(
            live_grade.get("inconclusive") or live_grade.get("unmeasured") or "run cut short",
            live_grade.get("run_stop") or "cut_short",
        )
    else:
        inconclusive = _saved_void(live_grade, summary) or native_problem
    if spec.get("references") and not has_plugin_root:
        inconclusive = "reference plugin root evidence missing or invalid; re-run the trial"
    required = fingerprints.required_rubrics(spec)
    if required and (not saved_binding or live_grade.get("response_sha256") != rubric_judge._digest(trace.result_text)):
        inconclusive = "saved judge binding or judged response identity is missing or changed; re-run the trial"
    elif required:
        try:
            rubric_judge.validate_binding(rubric_judge.JudgeBinding(json.dumps(saved_binding)), required, current=False)
        except rubric_judge.JudgeExecutionChanged:
            pass  # the run's evidence is intact; only its kept judgments fall (`_stale_judge`)
        except rubric_judge.JudgeUnavailable as exc:
            inconclusive = str(exc)
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
    reason = live_grade.get("inconclusive", summary.get("inconclusive"))
    if not reason:
        return None
    marked = f"{UNMEASURED}{reason}"[:EVIDENCE_LIMIT]
    expectations = live_grade.get("expectations") or []
    return str(reason) if all(str(e.get("evidence") or "") == marked for e in expectations) else None


def _stale_judge(spec: Spec, saved_binding: Any) -> str | None:
    """Why the run's kept judgments cannot stand when only the judge has changed since the run.

    A judge whose code or configuration differs from the one the saved binding certified leaves
    each kept judgment INCONCLUSIVE; the checks the saved trace re-measures keep their verdicts,
    so a supported FAIL beside them still fails (result rule 3). Any other binding problem voids
    the whole run in `_run_level_reason`.
    """
    required = fingerprints.required_rubrics(spec)
    if not required or not saved_binding:
        return None
    try:
        rubric_judge.validate_binding(rubric_judge.JudgeBinding(json.dumps(saved_binding)), required, current=False)
    except rubric_judge.JudgeExecutionChanged as exc:
        return f"{exc}; the kept judgment needs a re-run under the current judge"
    except rubric_judge.JudgeUnavailable:
        return None
    return None


def _saved_verdicts(
    old_by_id: Mapping[Any, Mapping[str, Any]], prefix: str | None, *, stale_judge: str | None = None
) -> assessment.Kept:
    """The live verdict an expectation kept by a regrade carries, found by its position and text,
    unless it is a judgment by a judge that has changed since (`stale_judge`)."""

    def kept(index: int, item: assessment.Expectation) -> Outcome | None:
        if stale_judge and item.kept_as == checking.LIVE_JUDGE:
            return outcomes.unmeasured(stale_judge)
        saved = old_by_id.get(f"{prefix}:{index}")
        if saved is None or saved.get("text") != item.text:
            return None
        read = Outcome.read(saved["passed"], saved["evidence"])
        return read.with_evidence(outcomes.kept_evidence(str(item.kept_as), str(saved["evidence"])))

    return kept


def _add_assessment(
    run_dir: Path, grading: dict[str, Any], summary: Mapping[str, Any], trace: TraceSummary | None
) -> dict[str, Any]:
    """Write a regrade as assessments/<k>/ beside the run's original grade, never over it
    (threat-model ADR result rule 8), and list it in the attempt's v1 record."""
    revisions = run_dir / "assessments"
    taken = [int(p.name) for p in revisions.iterdir() if p.name.isdigit()] if revisions.is_dir() else []
    revision = max(taken, default=0) + 1
    target = revisions / str(revision)
    target.mkdir(parents=True)
    grading = {
        **grading,
        "assessment_revision": revision,
        "assessed_at": records.utc_now(),
        "runner_source_sha256": HARNESS_SOURCE_SHA256,
    }
    (target / "grading.json").write_text(json.dumps(grading, indent=2, ensure_ascii=False), encoding="utf-8")
    # This assessment's own trace summary: its verdict, and the trace-derived facts as this runner
    # reads them when the raw trace survives; the live run's summary beside it stays as recorded.
    refreshed = {
        **summary,
        "status": grading["status"],
        "inconclusive": grading["inconclusive"],
        "scenario_sha256": grading["scenario_sha256"],
        "regraded": True,
    }
    if trace is not None:
        refreshed.update(
            skills=trace.skills,
            skills_failed=trace.skills_failed,
            dispatches=trace.dispatches,
            bash_commands=trace.bash_commands,
            tool_counts=trace.tool_counts,
            denials=trace.denials,
            tool_errors=trace.tool_errors,
            models=trace.models,
        )
    (target / "trace-summary.json").write_text(json.dumps(refreshed, indent=2, ensure_ascii=False), encoding="utf-8")
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
) -> tuple[list[tuple[dict[str, Any], Path]], dict[str, Any]]:
    """Each published run in an iteration with its scenario, `eval-<id>/<label>/run-<n>` holding a trace
    summary, and what was passed over: a scenario not loaded, a folder that is not a numbered run (an
    operator's `run-1-old`), and a run without a trace summary. Nothing is dropped silently."""
    by_id = {s["id"]: s for s in scenarios}
    runs: list[tuple[dict[str, Any], Path]] = []
    skipped: dict[str, Any] = {"scenarios": [], "other_run_folders": [], "runs_without_trace_summary": 0}
    for eval_dir in sorted(iteration_dir.glob("eval-*")):
        spec = by_id.get(eval_dir.name.removeprefix("eval-"))
        if spec is None:  # retired, renamed, or excluded by --scenario
            skipped["scenarios"].append(eval_dir.name.removeprefix("eval-"))
            continue
        for run_dir in sorted(eval_dir.glob("*/run-*")):
            if not re.fullmatch(r"run-\d+", run_dir.name):
                skipped["other_run_folders"].append(run_dir.relative_to(iteration_dir).as_posix())
            elif not (run_dir / "outputs" / "trace-summary.json").exists():
                skipped["runs_without_trace_summary"] += 1
            else:
                runs.append((spec, run_dir))
    return runs, skipped


def regrade(iteration_dir: Path, scenarios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    runs, skipped = _saved_runs(iteration_dir, scenarios)
    results = []
    for spec, run_dir in runs:
        g = regrade_run(run_dir, spec)
        results.append(
            {
                "scenario": spec["id"],
                "label": run_dir.parent.name,
                **assessment.native_assessment(spec),
                "run": int(run_dir.name.removeprefix("run-")),
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
        (iteration_dir / f"regrade-{records.utc_now().replace(':', '')}.json").write_text(
            json.dumps({"runner": HARNESS_IDENTITY, "runs": results, "skipped": skipped}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    return results


def _verdicts(grading: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": grading.get("status"),
        "checks": [
            {"text": e.get("text"), "state": outcomes.legacy_state(e), "evidence": str(e.get("evidence") or "")[:200]}
            for e in grading.get("expectations") or []
        ],
    }


def rescore(iteration_dir: Path, scenarios: list[dict[str, Any]], out_dir: Path) -> list[dict[str, Any]]:
    """Grade every saved run with this runner into `out_dir`, leaving the saved runs untouched.

    A saved scenario identity binds the runner that graded it, so after any runner edit `--regrade`
    voids every run. Rescoring grades across that change and marks such runs `identity_relaxed`:
    two rescores of the same runs, one per runner revision, show what the edit changed
    (`rescore_diff`). A rescore is a comparison, never a verdict of its own.
    """
    runs, skipped = _saved_runs(iteration_dir, scenarios)
    rows = []
    for spec, run_dir in runs:
        row = {"scenario": spec["id"], "label": run_dir.parent.name, "run": int(run_dir.name.removeprefix("run-"))}
        try:
            original = run_dir / "grading.original.json"
            saved = json.loads(
                (original if original.exists() else run_dir / "grading.json").read_text(encoding="utf-8")
            )
            grading = regrade_run(run_dir, spec, write=False, relax_identity=True)
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
            # One unreadable or older-shaped run stays visible instead of ending the comparison.
            rows.append({**row, "error": f"{type(exc).__name__}: {exc}"[:300]})
            continue
        target = out_dir / run_dir.relative_to(iteration_dir)
        try:
            target.mkdir(parents=True)
            (target / "grading.json").write_text(json.dumps(grading, indent=2, ensure_ascii=False), encoding="utf-8")
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
    (out_dir / "rescore.json").write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return rows


def rescore_diff(base: Mapping[str, Any], candidate: Mapping[str, Any]) -> list[str]:
    """Each run and check whose rescored verdict differs between two rescores of the same runs."""

    def key(row: Mapping[str, Any]) -> tuple[Any, ...]:
        return row.get("scenario"), row.get("label"), row.get("run")

    def outcome(row: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"status": "ERROR", "checks": []} if row.get("error") else row.get("rescored") or {}

    left = {key(r): r for r in base.get("runs") or []}
    right = {key(r): r for r in candidate.get("runs") or []}
    lines = []
    for k in sorted(left.keys() | right.keys(), key=lambda k: tuple(str(part) for part in k)):
        name = f"eval-{k[0]} {k[1]}/run-{k[2]}"
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
