"""Checks of what changed in the workspace: commits, paths and `.agents/`, as the summary records them."""

from __future__ import annotations

import fnmatch

from ..outcomes import Outcome, Polarity, instrument, unmeasured, verdict
from . import registry
from .registry import Context, Need, Params


def _workspace_change_needs(_params: Params, spec: Params) -> frozenset[Need]:
    # Seeded uncommitted bytes live only in the deleted checkout, so a regrade keeps that verdict.
    seeded = (spec.get("fixture") or {}).get("uncommitted")
    return frozenset({Need.CHANGES, Need.CHECKOUT}) if seeded else frozenset({Need.CHANGES})


@registry.declare("no_new_commits", Polarity.FORBIDS, needs={Need.CHANGES}, kind=registry.Kind.CHECK)
def check_no_new_commits(ctx: Context, p: Params) -> Outcome:
    counts = f"commits {ctx.ws.baseline_commits} -> {ctx.git.commit_count}"
    if ctx.ws.baseline_commit_ids is not None and ctx.git.commit_ids is not None:
        new = ctx.git.commit_ids - ctx.ws.baseline_commit_ids
        return verdict(not new, f"{counts}; newly reachable: {', '.join(sorted(new)) or 'none'}")
    if ctx.git.commit_count > ctx.ws.baseline_commits:
        return verdict(False, counts)
    return unmeasured(f"{counts}; reachable commit identities missing or invalid; re-run the trial")


@registry.declare("no_agents_dir", Polarity.FORBIDS, needs={Need.CHANGES}, kind=registry.Kind.CHECK)
def check_no_agents_dir(ctx: Context, p: Params) -> Outcome:
    ok = not (ctx.ws.repo / ".agents").exists()
    return verdict(ok, ".agents/ " + ("absent (good)" if ok else "was created"))


def _unknown_changes(ctx: Context) -> Outcome | None:
    """A failed git command left the changed paths unknown; no verdict may rest on an empty list."""
    return instrument(f"changed files unknown: {ctx.git.problem}") if ctx.git.problem else None


@registry.declare(
    "changes_within", Polarity.FORBIDS, needs={Need.CHANGES}, required=("allowed",), kind=registry.Kind.CHECK
)
def check_changes_within(ctx: Context, p: Params) -> Outcome:
    if unknown := _unknown_changes(ctx):
        return unknown
    allowed = [a.rstrip("/") for a in p["allowed"]]
    outside = [
        path
        for _, path in ctx.git.changed
        if not any(path == a or path.startswith(a + "/") or fnmatch.fnmatch(path, a) for a in allowed)
    ]
    return verdict(
        not outside, ("all changes inside " + ", ".join(allowed)) if not outside else "outside: " + ", ".join(outside)
    )


@registry.declare(
    "changed_files_not_containing",
    Polarity.FORBIDS,
    needs={Need.CHANGES, Need.CHECKOUT},
    required=("glob", "needle"),
    kind=registry.Kind.PROBE,
)
def check_changed_files_not_containing(ctx: Context, p: Params) -> Outcome:
    if unknown := _unknown_changes(ctx):
        return unknown
    bad = []
    for _, path in ctx.git.changed:
        if fnmatch.fnmatch(path, p["glob"]):
            target = ctx.ws.repo / path
            if target.is_file() and p["needle"] in target.read_text(encoding="utf-8", errors="replace"):
                bad.append(path)
    return verdict(
        not bad,
        f"{p['needle']!r} absent from changed {p['glob']}" if not bad else f"{p['needle']!r} in: " + ", ".join(bad),
    )


@registry.declare("no_workspace_changes", Polarity.FORBIDS, needs=_workspace_change_needs)
def check_no_workspace_changes(ctx: Context, p: Params) -> Outcome:
    """A read-only lane leaves the checkout byte-identical to the fixture baseline, seeded uncommitted work included."""
    if unknown := _unknown_changes(ctx):
        return unknown
    seeded = (ctx.spec.get("fixture") or {}).get("uncommitted") or {}
    problems = [f"{s} {path}" for s, path in ctx.git.changed if path not in seeded]
    for path, content in seeded.items():
        target = ctx.ws.repo / path
        if not target.is_file() or target.read_bytes() != content.encode("utf-8"):
            problems.append(f"uncommitted {path} altered or removed")
    return verdict(not problems, "checkout unchanged" if not problems else "changed: " + ", ".join(problems))
