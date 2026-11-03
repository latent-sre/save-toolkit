"""Load a pre-evidence run directory: the reconstruction a regrade did inline until evidence-v1.

A run saved before `evidence.json` kept its facts across `outputs/trace-summary.json`, the raw trace,
`grading.json`, `provenance.json` and each invocation's metadata. This module reads them back into
the objects the grading loop takes and into an evidence object of the same shape the live path
writes, so every saved iteration stays readable (RUNNER-001). It is quarantined here, moved from
`rescoring`, not rewritten; it is never used for a run that has `evidence.json`.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import evidence, fingerprints, layout, tracing
from .tracing import TraceSummary
from .workspaces import GitFacts, Workspace

Spec = Mapping[str, Any]


def saved_tool_counts(value: object) -> dict[str, int] | None:
    """A recorded complete count map, including {}, or None for missing/malformed evidence."""
    if not isinstance(value, dict) or not all(
        isinstance(name, str) and name.strip() and type(count) is int and count >= 0 for name, count in value.items()
    ):
        return None
    return dict(value)


def saved_commit_ids(value: object, count: int) -> frozenset[str] | None:
    """A complete saved reachability set; legacy counts alone cannot rule out a rewrite."""
    if not isinstance(value, list) or not all(
        isinstance(sha, str) and re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", sha) for sha in value
    ):
        return None
    ids = frozenset(value)
    return ids if len(ids) == len(value) == count else None


@dataclass
class Saved:
    """What a saved run's files give back: its trace, as re-parsed or as the summary restores it, the
    summary's complete tool counts, and the git facts the summary recorded."""

    trace: TraceSummary
    reparsed: bool
    saved_counts: dict[str, int] | None
    git: GitFacts
    before: int
    before_ids: object


def reconstruct(run_dir: Path, summary: Mapping[str, Any], text: str, *, reparse: bool) -> Saved:
    """The trace and git facts of a saved run. With `reparse`, the raw evidence is read with the live
    parser: an incomplete stream preserves positive observations but cannot establish an absent call;
    validated summary counts can fill that gap. Without it, the summary restores what it can."""
    stdout_path = run_dir / "stdout.jsonl"
    reparsed = tracing.parse_trial_trace(run_dir) if stdout_path.is_file() and reparse else None
    saved_counts = saved_tool_counts(summary.get("tool_counts"))
    if reparsed is not None:
        trace = reparsed
        if not trace.result_text:  # a truncated trace must not silently blank every text check
            trace.result_text = text
    else:
        trace = tracing.from_saved({**summary, "tool_counts": saved_counts or {}}, text)
    before, after = summary.get("commits_before_after") or [0, 0]
    saved_ids = summary.get("commit_ids_before_after")
    before_ids, after_ids = saved_ids if isinstance(saved_ids, list) and len(saved_ids) == 2 else (None, None)
    git = GitFacts(
        int(after),
        str(summary.get("branch") or ""),
        [tuple(x) for x in summary.get("changed_files") or []],
        "",
        str(summary["git_problem"]) if summary.get("git_problem") else None,
        commit_ids=saved_commit_ids(after_ids, int(after)),
    )
    return Saved(trace, reparsed is not None, saved_counts, git, int(before), before_ids)


def workspace(tmp: Path, summary: Mapping[str, Any], saved: Saved, recorded_workspace: Path | None) -> Workspace:
    """A placeholder workspace under `tmp` holding what the summary kept of the real one: its state
    files, whether `.agents/` existed, and the baseline the checks compare against."""
    state = tmp / "state"
    state.mkdir()
    for name, content in (summary.get("state_files") or {}).items():
        (state / name).write_text(content, encoding="utf-8")
    ws = Workspace(
        tmp,
        tmp / "repo-gone",
        tmp / "bin",
        state,
        saved.before,
        "main",
        command_repo=recorded_workspace,
        baseline_commit_ids=saved_commit_ids(saved.before_ids, saved.before),
    )
    if summary.get("agents_dir"):
        (ws.repo / ".agents").mkdir(parents=True)
    return ws


def evidence_of(
    run_dir: Path,
    spec: Spec,
    summary: Mapping[str, Any],
    saved: Saved,
    ws: Workspace,
    live_grade: Mapping[str, Any],
    plugin_root: Path,
) -> evidence.EvidenceV1:
    """The saved run as evidence-v1, from what its files kept. Two facts the old format never saved
    stay null: the identity failure the batch read from the result row, and a service problem seen
    after the proxy stopped; the live grade's `void` and `inconclusive` carry what it recorded."""
    provenance = layout.read_object(run_dir / "provenance.json") or {}
    plugin = dict(summary.get("plugin") or {})
    binding, execution, cache_dir = evidence.split_binding(live_grade.get("judge_binding"))
    git = saved.git
    return evidence.EvidenceV1(
        format=evidence.EvidenceFormat(**evidence.EVIDENCE_FORMAT),
        written_by="legacy",
        identity=evidence.Identity(
            case_id=str(spec["id"]),
            case_sha256=fingerprints.case_digest(spec),
            scenario_sha256=live_grade.get("scenario_sha256"),
            plugin_commit=plugin.get("plugin_commit"),
            plugin_inputs_dirty=plugin.get("plugin_inputs_dirty"),
            plugin_source_sha256=plugin.get("plugin_source_sha256"),
            runner_commit=provenance.get("runner_commit"),
            runner_source_dirty=provenance.get("runner_source_dirty"),
            runner_source_sha256=provenance.get("runner_source_sha256"),
            requested_model=(layout.read_object(run_dir / "timing.json") or {}).get("requested_model"),
            observed_models=list(saved.trace.models),
            judge_binding=binding,
        ),
        host=evidence.Host(
            runtime=summary.get("runtime"),
            workspace=summary.get("workspace") if isinstance(summary.get("workspace"), str) else None,
            plugin_root=plugin.get("plugin_root"),
            plugin_served_from=plugin.get("plugin_served_from"),
            judge_execution=execution,
            judge_cache_dir=cache_dir,
        ),
        trace=evidence.trace_facts(saved.trace, run_dir, restored=not saved.reparsed),
        git=evidence.Git(
            commits_before=ws.baseline_commits,
            commits_after=git.commit_count,
            commit_ids_before=sorted(ws.baseline_commit_ids) if ws.baseline_commit_ids is not None else None,
            commit_ids_after=sorted(git.commit_ids) if git.commit_ids is not None else None,
            branch=git.branch,
            changed=[[status, path] for status, path in git.changed],
            problem=git.problem,
            patch_sha256=evidence.file_sha256(run_dir / "outputs" / "workspace.patch"),
        ),
        workspace=evidence.WorkspaceFacts(
            state_files={p.name: p.read_text(encoding="utf-8") for p in ws.state_dir.iterdir() if p.is_file()},
            agents_dir=(ws.repo / ".agents").exists(),
            baseline_branch=ws.baseline_branch,
        ),
        services=[
            evidence.ServiceFacts(name=str(s["name"]), image=str(s["image"]), base_url=str(s["base_url"]))
            for s in summary.get("services") or []
        ],
        service_problem=None,
        ending=evidence.ending_of(live_grade, None),
        turns=evidence.turns(run_dir),
        probes=evidence.probes(spec, live_grade, saved.trace, plugin_root, None),
    )
