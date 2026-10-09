"""Launch one `claude -p` invocation and decide whether its trace may be graded at all.

A trace is graded only when it ran on the declared plugin, tools, read boundary and, for a native
conversation, model, session and helper. A run that stopped early on that profile is cut short (its
forbidding checks still count); one on any other profile is void (threat-model ADR result rule 1).
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

import clean_room
import yaml

from . import catalog, fingerprints, records, tracing
from .constants import BUILD_TOOLS, READ_TOOLS, SHELL_TOOLS, WRITING_TOOLS
from .outcomes import CutShort, Stop
from .tracing import TraceSummary

# Account skills synced from claude.ai download in the background at session start and reached 7 of 8
# unisolated probe sessions; this setting kept them out of 16 of 16 (WP-02 gap 1).
ISOLATION_SETTINGS = json.dumps({"syncClaudeAiSkills": False})


def build_command(
    executable: str,
    plugin_root: Path,
    agent: str | None,
    prompt: str,
    model: str | None,
    tools: Sequence[str] = BUILD_TOOLS,
    *,
    pre_approve: bool = True,
    persistent: bool = False,
    resume: str | None = None,
    max_turns: int | None = None,
) -> list[str]:
    tools = tuple(tools)
    denied = [t for t in clean_room.DENIED_TOOLS if t not in tools]
    command = fingerprints.executable_argv(executable)
    if agent:
        command += ["--agent", agent]
    command += [
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--verbose",
        "--forward-subagent-text",
        "--plugin-dir",
        str(plugin_root.resolve()),
        "--mcp-config",
        '{"mcpServers":{}}',
        "--strict-mcp-config",
        "--settings",
        ISOLATION_SETTINGS,
        "--tools",
        ",".join(tools),
        "--disallowedTools",
        ",".join(denied),
    ]
    if not persistent:
        command += ["--no-session-persistence"]
        if not WRITING_TOOLS & set(tools):
            # A read-only inventory gets the plugin root as a working directory, as persistent trials
            # do: a `references:` read lands outside the neutral CWD, and a -p session cannot answer
            # the permission prompt. An inventory that can Edit, Write, or run Bash does not get it.
            command += ["--add-dir", str(plugin_root.resolve())]
    else:
        command += [
            "--restricted",
            "--add-dir",
            str(plugin_root.resolve()),
            "--max-budget-usd",
            "0.75",
            "--prompt-suggestions",
            "false",
        ]
        if resume:
            command += ["--resume", resume]
    if (agent and pre_approve) or persistent:
        # Build tools and the native conversation's explicitly read-only inventory are pre-approved.
        # Ordinary routing/contract trials keep their existing permission behavior.
        command += ["--allowedTools", ",".join(tools), "--permission-mode", "dontAsk"]
    if model:
        command += ["--model", model]
    if max_turns:  # the scenario's declared task budget; the CLI ends the session there (result rule 4)
        command += ["--max-turns", str(max_turns)]
    return command


def runtime_blocked_tools(trace: TraceSummary, spec: Mapping[str, Any]) -> list[str]:
    """Build tools the runtime (not the guard) refused; a non-empty list voids the trial.

    A routing trial's verdict is the main session's dispatch, so a refusal inside the subagent it
    dispatched lands after the verdict was decided and does not void it: the clean room runs a
    dispatched agent without Bash and the CLI refuses its reads outside the workspace, which on
    2026-09-03 voided two of three dispatched-read trials whose dispatch had already happened.
    """
    inside = (
        set(trace.subagent_tool_ids)
        if catalog.scenario_kind(spec) == "routing" and not spec.get("followups")
        else set()
    )
    if trace.denial_details:
        return [
            d["tool"]
            for d in trace.denial_details
            if d["tool"] in set(BUILD_TOOLS) | SHELL_TOOLS
            and not tracing.is_guard_denial(d["reason"])
            and d["id"] not in inside
        ]
    return [d for d in trace.denials if d in set(BUILD_TOOLS) | SHELL_TOOLS]


def declared_agent_tools(plugin_root: Path, agent: str) -> tuple[str, ...] | None:
    """The tools this agent's frontmatter declares, in runtime names (`Agent(...)` → `Task`).

    `None` when the agent omits `tools:` — omission inherits every tool. A read-only lane declares
    no `Edit`/`Write`, and the runtime is right to advertise fewer tools than the probe asked for;
    measuring against the probe's superset made every `sre-assistant` trial INCONCLUSIVE (2026-08-28).
    """
    text = (plugin_root / "agents" / f"{agent}.md").read_text(encoding="utf-8")
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if match is None:
        raise RuntimeError(f"agents/{agent}.md has no frontmatter; cannot bound the tool inventory")
    raw = (yaml.safe_load(match.group(1)) or {}).get("tools")
    if raw is None:
        return None
    names = raw if isinstance(raw, list) else str(raw).split(",")
    resolved = []
    for name in names:
        base = str(name).strip().split("(")[0].strip()
        if base:
            resolved.append("Task" if base == "Agent" else base)
    return tuple(dict.fromkeys(resolved))


def expected_runtime_tools(plugin_root: Path, agent: str, requested: Sequence[str] = BUILD_TOOLS) -> tuple[str, ...]:
    """What the runtime should advertise: the probe's requested set, bounded by what the agent declares."""
    declared = declared_agent_tools(plugin_root, agent)
    return tuple(t for t in requested if declared is None or t in declared)


def read_boundary_applies(spec: Mapping[str, Any], requested: Sequence[str]) -> bool:
    """Fixture-less trials, routing trials and native read-only conversations stay inside harness-owned trees.

    A build lane runs with its real tools on the host and legitimately reads outside the workspace
    (the CLI's own bundled-skill cache, the npm cache); it is graded on what it produced. Applying
    the read boundary to it turned every frontend build trial INCONCLUSIVE on 2026-09-03. A routing
    trial keeps the boundary when it carries a fixture: it has no shell, and its verdict must not be
    shaped by what it found outside the harness (EVAL-013, EVAL-014).
    """
    bounded = spec.get("followups") or spec.get("routing") or not spec.get("fixture")
    return bool(bounded) and bool(set(requested) & set(READ_TOOLS))


def read_boundary_problem(trace: TraceSummary, allowed_roots: Sequence[Path]) -> str | None:
    """Why a granted read escaped its allowed roots, or None.

    Only trials that were granted read tools reach this. `allowed_roots` are harness-owned trees a
    read may resolve into -- the fixture workspace and the plugin snapshot. A relative read resolves
    against the workspace cwd, so a cwd-relative Grep/Glob is in bounds there and out of bounds
    anywhere else (HOST-003 owner decision, 2026-08-28).
    """
    roots = [root.resolve() for root in allowed_roots]
    for attempt in trace.read_attempts:
        path, outcome = attempt["path"], attempt["outcome"]
        if not path:
            return f"{attempt['tool']} attempt has no path evidence"
        normalized = path.replace("\\", "/")
        if ".." in PurePosixPath(normalized).parts:
            return f"path traversal attempted by {attempt['tool']}: {path}"
        if outcome != "allowed":
            continue
        prefix = normalized
        for marker in ("*", "?", "["):
            prefix = prefix.split(marker, 1)[0]
        candidate = Path(prefix or normalized)
        if not tracing.is_rooted(candidate):
            continue  # relative: resolves inside the workspace cwd
        try:
            resolved = candidate.resolve()
        except OSError as exc:
            return f"cannot normalize tool path {path!r}: {exc}"
        if not any(resolved.is_relative_to(root) for root in roots):
            return f"successful out-of-workspace read: {path}"
    return None


def runtime_boundary_problem(trace: TraceSummary, expected: Sequence[str]) -> str | None:
    """Why the observed runtime boundary is not the one the probe requested, or None.

    Fail closed: no init event, any tool the agent does not declare, any declared tool the runtime
    dropped, or any MCP server in a strict-empty run makes the trial INCONCLUSIVE, never a verdict
    about the agent.
    """
    if not trace.saw_init:
        return "no init event: the runtime never advertised its tool inventory"
    advertised = set(trace.advertised_tools)
    extra = sorted(advertised - set(expected))
    missing = sorted(set(expected) - advertised)
    if extra or missing:
        return f"runtime tool inventory mismatch (extra {extra}, missing {missing}; expected {sorted(expected)})"
    if trace.mcp_servers:
        return f"MCP servers present in a strict-empty run: {trace.mcp_servers}"
    return None


def plugin_identity_problem(trace: TraceSummary, plugin_root: Path) -> str | None:
    """Why the runtime did not load exactly the measured plugin snapshot, or None.

    The tool inventory says nothing about which plugin answered. If `--plugin-dir` loaded nothing,
    loaded a second plugin, or resolved to another checkout, then a FAIL means "the candidate bytes
    were never there" and a PASS means "something else passed" -- neither is a verdict about the
    measured revision. `runtime_namespace` would also fall back to the candidate manifest and
    manufacture a namespace no component actually fired under.
    """
    if len(trace.runtime_plugins) != 1:
        return f"expected exactly one runtime plugin from the measured snapshot, observed {trace.runtime_plugins}"
    observed = trace.runtime_plugins[0]
    if not isinstance(observed, dict):
        return f"runtime plugin entry is not an object: {observed!r}"
    manifest = json.loads((plugin_root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    if observed.get("name") != manifest["name"]:
        return f"runtime plugin name {observed.get('name')!r}, expected {manifest['name']!r}"
    observed_path = observed.get("path")
    try:
        matches = isinstance(observed_path, str) and Path(observed_path).resolve() == plugin_root.resolve()
    except OSError as exc:
        return f"cannot normalize runtime plugin path {observed_path!r}: {exc}"
    if not matches:
        return f"runtime plugin path {observed_path!r}, expected {plugin_root.resolve()}"
    return None


# The reason a runtime refusal voids a trial; a regrade re-derives it from the raw trace.
BLOCKED_TOOLS = "build tools denied by the runtime"


CREDENTIAL_MARKERS = (".credentials.json", "sk-ant-", "ghp_", "AKIA")


def credential_markers(final_text: str, trace_path: Path | None) -> list[str]:
    """Names of credential-shaped markers found in the final text or the raw trace (never their values)."""
    haystack = final_text
    if trace_path is not None and trace_path.exists():
        haystack += trace_path.read_text(encoding="utf-8", errors="replace")
    return [m for m in CREDENTIAL_MARKERS if m in haystack]


def reached_turn_limit(trace: TraceSummary, spec: Mapping[str, Any]) -> bool:
    """The CLI ended the session at the scenario's declared turn limit: a completed run whose unmet
    requirements fail (threat-model ADR result rule 4). Without a declared limit it is cut short."""
    return trace.result_subtype == "error_max_turns" and bool(spec.get("max_turns"))


def turns_left(spec: Mapping[str, Any], traces: Sequence[TraceSummary]) -> int | None:
    """What remains of the scenario's turn limit after `traces`, a conversation's earlier invocations:
    `--max-turns` bounds one invocation, so a resumed one gets only the rest. None without a declared
    limit; zero or less once the conversation has spent it."""
    limit = spec.get("max_turns")
    if not limit:
        return None
    if any(reached_turn_limit(trace, spec) for trace in traces):
        return 0
    return limit - sum(trace.num_turns or 0 for trace in traces)


def turn_reason(
    current: TraceSummary,
    returncode: int | None,
    timed_out: CutShort | None,
    spec: Mapping[str, Any],
    plugin_root: Path,
    plugin_sha: str,
    workdir: Path,
    resume: str | None,
    stdout: Path,
) -> tuple[str | None, str | None]:
    """How one invocation ends its trial early, if it does, and any identity failure it showed.

    The order of the checks is the precedence, and the first reason found wins: plugin drift, then a
    native run's credential marker, then a timed-out run's profile and identity (its partial trace
    must show the declared profile before its evidence counts), then the timeout itself, then the
    invocation's own problems. Once a timeout makes the run cut short, a later problem here does not
    void it; after the run, `outcomes.void_over_cut` lets drift do so.
    """
    followups = bool(spec.get("followups"))
    drift = fingerprints.plugin_drift_problem(plugin_root, plugin_sha)
    identity = (
        drift
        or identity_problem(current, spec, plugin_root)
        or (native_model_problem(current, spec) if followups else None)
    )
    reason = drift
    if followups and credential_markers(current.result_text, stdout):
        reason = reason or "native credential marker detected; no follow-up allowed"
    if timed_out:
        reason = (
            reason
            or profile_problem(current, spec, plugin_root, workdir)
            or (native_identity_problem(current, spec, resume, complete=False) if followups else None)
            or timed_out
        )
    return reason or invocation_problem(current, returncode, spec, plugin_root, workdir, resume), identity


def identity_problem(trace: TraceSummary, spec: Mapping[str, Any], plugin_root: Path) -> str | None:
    """Whether the trace ran as the declared candidate: its plugin, tool inventory and model. A wrong
    identity stops the batch, since every later trial would run as the same wrong candidate."""
    requested = catalog.scenario_tools(spec)
    expected = expected_runtime_tools(plugin_root, spec["agent"], requested) if spec.get("agent") else requested
    problem = runtime_boundary_problem(trace, expected) or plugin_identity_problem(trace, plugin_root)
    if not problem and trace.foreign_skills:  # outside the measured plugin: the profile is not the one declared
        problem = f"skills advertised outside the measured plugin: {trace.foreign_skills[:5]}"
    if not problem and not any(trace.models):  # a result whose model is unknown is never pooled
        problem = "resolved model identity missing"
    return problem


def profile_problem(trace: TraceSummary, spec: Mapping[str, Any], plugin_root: Path, workspace: Path) -> str | None:
    """Whether the trace ran on the declared plugin, tools and read boundary, finished or not."""
    requested = catalog.scenario_tools(spec)
    problem = identity_problem(trace, spec, plugin_root)
    if not problem and read_boundary_applies(spec, requested):
        problem = read_boundary_problem(trace, (workspace, plugin_root.resolve()))
    blocked = runtime_blocked_tools(trace, spec)
    if not problem and blocked:
        problem = f"{BLOCKED_TOOLS}: {blocked}"
    return problem


def invocation_problem(
    trace: TraceSummary,
    returncode: int | None,
    spec: Mapping[str, Any],
    plugin_root: Path,
    workspace: Path,
    resume: str | None = None,
) -> str | None:
    """Check every invocation before a follow-up may inherit its state.

    A run that ended early returns a CutShort reason only after its partial trace passes the profile
    checks; a profile problem voids the trial whether or not the run finished.
    """
    cut = None
    if not trace.has_result:
        cut = CutShort(f"no result event (claude exit {returncode})", Stop.NO_RESULT)
    elif trace.result_is_error or trace.result_subtype not in ("", "success"):
        if clean_room.is_auth_failure(trace.result_text, returncode):
            raise clean_room.AuthUnavailable(f"claude reported an authentication failure: {trace.result_text[:200]}")
        if not reached_turn_limit(trace, spec):
            cut = CutShort(
                f"claude reported an error result (subtype={trace.result_subtype or '?'}, "
                f"is_error={trace.result_is_error})",
                Stop.ERROR_RESULT,
            )
    elif returncode not in (0, None):
        if clean_room.is_auth_failure(trace.result_text, returncode):
            raise clean_room.AuthUnavailable(
                f"claude exited {returncode} with an authentication failure: {trace.result_text[:200]}"
            )
        cut = CutShort(f"claude exited {returncode} after emitting a result event", Stop.NONZERO_EXIT)
    problem = profile_problem(trace, spec, plugin_root, workspace)
    if not problem and spec.get("followups"):
        problem = native_identity_problem(trace, spec, resume, complete=cut is None)
    if problem:  # a wrong profile or identity voids the trial whether or not the run finished
        return f"{cut}; {problem}" if cut else problem
    if cut:
        return cut
    if spec.get("followups"):
        cost = records.known_usd(trace.total_cost_usd)
        if cost is None:
            return "native cost missing or invalid; no further invocation"
        if cost > 0.75:
            # The spend guard is an instrument limit: reaching it cuts the conversation short.
            return CutShort("native cost exceeds $0.75; no further invocation", Stop.SPEND_GUARD)
        if spec.get("max_turns") and type(trace.num_turns) is not int:
            return "native turn count missing; the turn limit cannot carry to a further invocation"
    return None


def native_model_problem(trace: TraceSummary, spec: Mapping[str, Any]) -> str | None:
    """Whether a native conversation's parent ran on the scenario's expected model, part of its identity."""
    if spec.get("expected_model") and trace.main_models != [spec["expected_model"]]:
        return f"native parent model missing or differs from {spec['expected_model']}: {trace.main_models}"
    return None


def native_identity_problem(
    trace: TraceSummary, spec: Mapping[str, Any], resume: str | None, *, complete: bool
) -> str | None:
    """A native conversation's model, grants, session and helper identity, on a finished or partial
    trace. A partial trace has no result event, so its session is read from the init events alone."""
    requested = catalog.scenario_tools(spec)
    used = {"Task" if tool == "Agent" else tool for tool in trace.tool_counts}
    if used - set(requested):
        return f"native ungranted tool use: {sorted(used - set(requested))}"
    model = native_model_problem(trace, spec)
    if model:
        return model
    sessions = trace.init_session_ids + ([trace.session_id] if complete else [])
    anchor = resume or (trace.session_id if complete else next(iter(trace.init_session_ids), None))
    if (complete and not trace.session_id) or not trace.init_session_ids or any(s != anchor for s in sessions):
        return "native session identity missing or resume session mismatch"
    if trace.tool_errors or trace.denials:
        return "native tool denial/error"
    if len(trace.dispatches) > (0 if resume else 1) or set(trace.dispatches) - {f"save-toolkit:{spec['helper']}"}:
        return "unexpected native helper session"
    return None
