"""Read a `claude -p --output-format stream-json` trace into the facts the checks grade.

One pass records every tool call and result with its position, then `_Reader.finish` decides what
completed: a Skill load or a dispatch is credited only against its own non-error result, and an
ordering boundary (a load before the first effect, a read before the first dispatch) needs completion
evidence on both sides. Unknown event shapes are skipped rather than trusted.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Final, NotRequired, TypedDict

from .constants import DISPATCH_TOOLS, READ_TOOLS, SHELL_TOOLS, WRITING_TOOLS


class EffectCall(TypedDict):
    """One potentially mutating call (an edit, a shell command or a dispatch), in trace order; `_complete`
    adds its completion evidence once the whole trace is read."""

    id: str
    tool: str
    command: str
    issued: int  # the trace line, counted from 0
    parent: Any  # the dispatch it ran inside, or None on the main thread
    background: bool
    completed: NotRequired[int | None]  # the line of its matched result, or None when unknown
    reported_error: NotRequired[bool]
    success: NotRequired[bool]
    test_summaries: NotRequired[dict[str, str]]  # a shell call's passing summary per test runner
    test_failures: NotRequired[dict[str, str]]


class ReadAttempt(TypedDict):
    tool: str
    path: str | None
    outcome: str  # "allowed" or "denied"


class ParentRead(ReadAttempt):
    """A read the parent completed before its first dispatch, with where it sat in the trace."""

    caller: str
    tool_use_id: str
    issued_line: int
    completed_line: int


class DenialDetail(TypedDict):
    tool: str
    id: str
    command: str
    reason: str  # the matching error tool result


class AgentReturn(TypedDict):
    agent: str
    tool_use_id: str
    completed: bool
    continued: bool  # the dispatching thread spoke again after the return


@dataclass
class TraceSummary:
    result_text: str = ""
    skills: list[str] = field(default_factory=list)
    # Skill calls whose tool_result was is_error, or that never got one: an attempt, not a load.
    skills_failed: list[str] = field(default_factory=list)
    bash_commands: list[str] = field(default_factory=list)
    powershell_commands: list[str] = field(default_factory=list)
    # The subset of bash_commands issued inside a dispatched subagent; `scope: subagent` grades only these.
    subagent_bash_commands: list[str] = field(default_factory=list)
    # Ordered potentially mutating calls, with matched completion evidence. Not filesystem attestation.
    effect_calls: list[EffectCall] = field(default_factory=list)
    dispatches: list[str] = field(default_factory=list)
    # Task/Agent calls that returned a non-error tool_result. `dispatches` records every attempt
    # (the no-dispatch checks grade attempts); routing credits only a completed invocation.
    agents: list[str] = field(default_factory=list)
    agents_failed: list[str] = field(default_factory=list)
    runtime_plugins: list[Any] = field(default_factory=list)
    # {tool, path, outcome} per Read/Grep/Glob call, for the read-path boundary check.
    read_attempts: list[ReadAttempt] = field(default_factory=list)
    tool_counts: dict[str, int] = field(default_factory=dict)
    denials: list[str] = field(default_factory=list)
    duration_ms: int = 0
    total_tokens: int = 0
    output_tokens: int = 0
    models: list[str] = field(default_factory=list)
    # Every model in the CLI's usage table, including its internal helper calls (a Haiku side call
    # of a few tokens). Recorded for cost attribution; `models` is the resolved identity.
    usage_models: list[str] = field(default_factory=list)
    num_turns: int | None = None
    total_cost_usd: float | None = None
    has_result: bool = False
    result_is_error: bool = False
    result_subtype: str = ""
    tool_errors: list[str] = field(default_factory=list)  # is_error tool results, e.g. guard denials
    denial_details: list[DenialDetail] = field(default_factory=list)  # one per permission denial
    # tool_use ids issued inside a dispatched subagent (the event carried parent_tool_use_id).
    subagent_tool_ids: list[str] = field(default_factory=list)
    saw_init: bool = False
    advertised_tools: list[str] = field(default_factory=list)
    mcp_servers: list[Any] = field(default_factory=list)
    permission_mode: str = ""
    session_id: str = ""
    init_session_ids: list[str] = field(default_factory=list)
    main_skills: list[str] = field(default_factory=list)
    main_skills_before_effects: list[str] = field(default_factory=list)
    agent_returns: list[AgentReturn] = field(default_factory=list)
    conversation_sessions: list[str] = field(default_factory=list)
    parent_reads_before_dispatch: list[ParentRead] = field(default_factory=list)
    parent_skills_before_dispatch: list[str] = field(default_factory=list)
    main_models: list[str] = field(default_factory=list)


GUARD_DENIAL_MARKERS = ("read-only agent allowlist guard", "read-only guard", "save-toolkit read-only guard")


# The hook's fail-closed diagnostic when the guard itself cannot run (Python resolution, a crash):
# infrastructure denying a safe observation, never a decision about the agent.
GUARD_UNAVAILABLE_MARKER = "read-only guard unavailable or failed"


def is_guard_denial(reason: str) -> bool:
    """A denial issued by the fleet's read-only Bash guard (hooks/hooks.json) — a result, not harness breakage.

    The guard's own unavailable/failed diagnostic is excluded: a trial that lost safe observations to a
    broken guard is INCONCLUSIVE, not an agent failure."""
    low = (reason or "").lower()
    if GUARD_UNAVAILABLE_MARKER in low:
        return False
    return any(m in low for m in GUARD_DENIAL_MARKERS)


# A failed foreground shell command is receipted as text ("Error: Exit code 1\n..."), not as the dict a
# clean run gets. The exit code shows the command returned, so this exact shape completes the call; any
# other text error (no such tool, an interruption) still leaves completion unknown.
_FAILED_FOREGROUND_RECEIPT = re.compile(r"Error: Exit code \d+(?:\n|\Z)")
TEST_RUNNERS = ("unittest", "pytest", "vitest")  # the runners whose summaries a trace recognizes


def parse_trace(path: Path) -> TraceSummary:
    reader = _Reader()
    for position, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines()):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        reader.event(event, position)
    return reader.finish()


@dataclass
class _Reader:
    """Every call, result and task notice in one trace, by position, until `finish` decides completion."""

    summary: TraceSummary = field(default_factory=TraceSummary)
    errors_by_id: dict[str, str] = field(default_factory=dict)
    clean_result_ids: dict[str, int] = field(default_factory=dict)
    result_positions: dict[str, int] = field(default_factory=dict)
    shell_receipts: dict[str, dict[str, Any]] = field(default_factory=dict)
    skill_uses: list[tuple[str, str, object, int]] = field(default_factory=list)
    agent_uses: list[tuple[str, str, object, int]] = field(default_factory=list)
    asynchronous: set[str] = field(default_factory=set)
    tasks: dict[str, tuple[str, int]] = field(default_factory=dict)
    completed: dict[str, int] = field(default_factory=dict)
    parent_texts: list[tuple[object, int]] = field(default_factory=list)
    read_uses: list[tuple[str, str, str | None, object, int]] = field(default_factory=list)

    def event(self, event: Any, position: int) -> None:
        match event:
            case {"type": "system", "subtype": "init"}:
                self._init(event)
                return
            case {"type": "result"}:
                self._result(event)
                return
            case {"type": "system", "subtype": "task_started"}:
                use_id = str(event.get("tool_use_id") or "")
                self.tasks[use_id] = (str(event.get("task_id") or ""), position)
                if event.get("is_backgrounded"):
                    self.asynchronous.add(use_id)
            case {"type": "system", "subtype": "task_notification"}:
                use_id = str(event.get("tool_use_id") or "")
                task, started = self.tasks.get(use_id, ("", position))
                if task and task == event.get("task_id") and started < position and event.get("status") == "completed":
                    self.completed[use_id] = position
        match event:
            case {"message": dict() as message}:
                self._message(event, message, position)

    def _init(self, event: dict[str, Any]) -> None:
        # The runtime's own inventory, not the flags the probe asked for: a CLI that ignores
        # --tools / --strict-mcp-config is caught here rather than trusted.
        s = self.summary
        s.saw_init = True
        s.advertised_tools = [str(t) for t in event.get("tools") or []]
        # A CLI-bundled plugin (source "<name>@builtin") is part of the host, not a candidate.
        s.runtime_plugins = [
            p
            for p in event.get("plugins") or []
            if not (isinstance(p, dict) and str(p.get("source", "")).endswith("@builtin"))
        ]
        s.mcp_servers = list(event.get("mcp_servers") or [])
        s.permission_mode = str(event.get("permissionMode") or "")
        s.init_session_ids.append(str(event.get("session_id") or ""))
        s.main_models.append(str(event.get("model") or ""))

    def _result(self, event: dict[str, Any]) -> None:
        s = self.summary
        s.has_result = True
        s.result_text = event.get("result") or ""
        s.result_is_error = bool(event.get("is_error"))
        s.result_subtype = str(event.get("subtype") or "")
        s.session_id = str(event.get("session_id") or "")
        s.duration_ms = int(event.get("duration_ms") or 0)
        usage = event.get("usage") or {}
        s.total_tokens = sum(
            int(usage.get(k) or 0)
            for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
        )
        s.output_tokens = int(usage.get("output_tokens") or 0)
        s.usage_models = sorted((event.get("modelUsage") or {}).keys())
        s.models = list(s.usage_models)  # fallback when no main-thread turn was recorded
        s.num_turns = event.get("num_turns")
        s.total_cost_usd = event.get("total_cost_usd")
        for denial in event.get("permission_denials") or []:
            s.denials.append(str(denial.get("tool_name") or denial)[:80])
            if isinstance(denial, dict):
                s.denial_details.append(
                    {
                        "tool": str(denial.get("tool_name") or "")[:80],
                        "id": str(denial.get("tool_use_id") or ""),
                        "command": str((denial.get("tool_input") or {}).get("command") or "")[:200],
                        "reason": "",
                    }
                )

    def _message(self, event: dict[str, Any], message: dict[str, Any], position: int) -> None:
        kind = event.get("type")
        if kind == "assistant" and not event.get("parent_tool_use_id"):
            self.summary.main_models.append(str(message.get("model") or ""))
        for block in message.get("content") or []:
            match block:
                case {"type": "text", "text": str() as text} if text.strip() and kind == "assistant":
                    self.parent_texts.append((event.get("parent_tool_use_id"), position))
                case {"type": "tool_result"}:
                    self._tool_result(event, message, block, position)
                case {"type": "tool_use"}:
                    self._tool_use(event, block, position)

    def _tool_result(
        self, event: dict[str, Any], message: dict[str, Any], block: dict[str, Any], position: int
    ) -> None:
        use_id = str(block.get("tool_use_id") or "")
        receipt = event.get("tool_use_result")
        if event.get("type") == "user":
            self.result_positions[use_id] = position
            # One top-level receipt cannot be assigned to several tool results.
            result_count = sum(
                isinstance(b, dict) and b.get("type") == "tool_result" for b in message.get("content") or []
            )
            if isinstance(receipt, dict) and result_count == 1:
                self.shell_receipts[use_id] = receipt
            elif (
                block.get("is_error")
                and result_count == 1
                and isinstance(receipt, str)
                and _FAILED_FOREGROUND_RECEIPT.match(receipt)
            ):
                self.shell_receipts[use_id] = {"interrupted": False}
        if not block.get("is_error"):
            self.clean_result_ids[use_id] = position
            if isinstance(receipt, dict) and receipt.get("isAsync"):
                self.asynchronous.add(use_id)
            return
        content = block.get("content")
        if isinstance(content, list):
            content = " ".join(str(c.get("text", "")) if isinstance(c, dict) else str(c) for c in content)
        self.summary.tool_errors.append(str(content or "")[:300])
        self.errors_by_id[use_id] = str(content or "")[:300]

    def _tool_use(self, event: dict[str, Any], block: dict[str, Any], position: int) -> None:
        s = self.summary
        name = str(block.get("name"))
        inp = block.get("input") or {}
        use_id = str(block.get("id") or "")
        parent = event.get("parent_tool_use_id")
        s.tool_counts[name] = s.tool_counts.get(name, 0) + 1
        if parent:
            s.subagent_tool_ids.append(use_id)
        if name in WRITING_TOOLS | DISPATCH_TOOLS:
            s.effect_calls.append(
                {
                    "id": use_id,
                    "tool": name,
                    "command": str(inp.get("command") or ""),
                    "issued": position,
                    "parent": parent,
                    "background": bool(inp.get("run_in_background")),
                }
            )
        # An unnamed Skill/Task call is recorded as such, and the checks that reason about names
        # refuse to pass on it — a renamed tool parameter must fail loudly, not vacuously.
        match name:
            case "Skill":
                # Credited in `finish`, and only against a matching non-error tool_result: the runtime
                # answers an unknown skill with is_error, and an attempt is not a load.
                self.skill_uses.append(
                    (use_id, str(inp.get("skill") or inp.get("name") or "") or "<unnamed-skill>", parent, position)
                )
            case "Bash" | "PowerShell":
                # The full command: bash_ran / bash_did_not_run grade every byte of a heredoc or a
                # compound command, so nothing is truncated here (size bounds belong to display).
                command = str(inp.get("command") or "")
                (s.bash_commands if name == "Bash" else s.powershell_commands).append(command)
                if name == "Bash" and parent:
                    s.subagent_bash_commands.append(command)
            case _ if name in DISPATCH_TOOLS:
                agent_name = str(inp.get("subagent_type") or "") or "<unnamed-agent>"
                s.dispatches.append(agent_name)
                self.agent_uses.append((use_id, agent_name, parent, position))
                if inp.get("run_in_background"):
                    self.asynchronous.add(use_id)
            case _ if name in READ_TOOLS:
                path = next((inp[f] for f in ("file_path", "path", "pattern") if isinstance(inp.get(f), str)), None)
                self.read_uses.append((use_id, name, path, parent, position))

    def finish(self) -> TraceSummary:
        s = self.summary
        clean = self.clean_result_ids
        first_dispatch = min((issued for _, _, parent, issued in self.agent_uses if not parent), default=math.inf)
        first_effect = min((call["issued"] for call in s.effect_calls), default=math.inf)
        for use_id, skill_name, parent, issued in self.skill_uses:
            (s.skills if use_id in clean else s.skills_failed).append(skill_name)
            if not parent and use_id in clean:
                s.main_skills.append(skill_name)
                if (
                    issued < clean[use_id] < first_effect
                    and use_id not in self.errors_by_id
                    and use_id not in self.asynchronous
                ):
                    s.main_skills_before_effects.append(skill_name)
                if issued < clean[use_id] < first_dispatch and use_id not in self.errors_by_id:
                    s.parent_skills_before_dispatch.append(skill_name)
        for use_id, agent_name, parent, issued in self.agent_uses:
            returned = (self.completed if use_id in self.asynchronous else clean).get(use_id)
            ok = returned is not None and returned > issued and use_id not in self.errors_by_id
            (s.agents if ok else s.agents_failed).append(agent_name)
            continued = ok and returned is not None and any(p == parent and n > returned for p, n in self.parent_texts)
            s.agent_returns.append(
                {"agent": agent_name, "tool_use_id": use_id, "completed": ok, "continued": bool(continued)}
            )
        for call in s.effect_calls:
            self._complete(call)
        for use_id, tool, path, parent, issued in self.read_uses:
            s.read_attempts.append({"tool": tool, "path": path, "outcome": "allowed" if use_id in clean else "denied"})
            returned = clean.get(use_id)
            if (
                tool == "Read"
                and not parent
                and returned is not None
                and issued < returned < first_dispatch
                and use_id not in self.errors_by_id
            ):
                s.parent_reads_before_dispatch.append(
                    {
                        **s.read_attempts[-1],
                        "caller": "parent",
                        "tool_use_id": use_id,
                        "issued_line": issued + 1,
                        "completed_line": returned + 1,
                    }
                )
        for denial in s.denial_details:  # the reason lives in the matching error tool result
            denial["reason"] = self.errors_by_id.get(denial["id"], "")
        s.main_models = sorted(set(s.main_models))
        # The resolved identity is whoever carried the main thread: the init model and every top-level
        # assistant turn. The usage table also lists the CLI's internal helper calls (the judge's
        # _resolved_model documents the same Haiku side call); those stay in usage_models and do not
        # make a batch mixed. A parent that changed model mid-trial still resolves to two identities.
        resolved = [model for model in s.main_models if model]
        if resolved:
            s.models = resolved
        return s

    def _complete(self, call: EffectCall) -> None:
        """Attach completion evidence to one potentially mutating call."""
        use_id = call["id"]
        returned = self.result_positions.get(use_id)
        if call["tool"] in DISPATCH_TOOLS and use_id in self.asynchronous:
            returned = self.completed.get(use_id)
        receipt = self.shell_receipts.get(use_id, {})
        if call["tool"] in SHELL_TOOLS:
            synchronous = (
                not call["background"]
                and receipt.get("interrupted") is False
                and not any(receipt.get(k) is not None for k in ("backgroundTaskId", "timedOutAfterMs"))
                and not any(
                    receipt.get(k)
                    for k in (
                        "isAsync",
                        "backgroundedByUser",
                        "backgroundedByTurnAbort",
                        "backgroundedToDeliverMessage",
                    )
                )
            )
            # Unknown or background shell completion cannot establish an ordering boundary.
            returned = returned if synchronous else None
        call["completed"] = returned
        call["reported_error"] = use_id in self.errors_by_id
        call["success"] = bool(
            use_id
            and returned is not None
            and returned > call["issued"]
            and use_id in self.clean_result_ids
            and use_id not in self.errors_by_id
        )
        if call["tool"] in SHELL_TOOLS and all(isinstance(receipt.get(k), str) for k in ("stdout", "stderr")):
            output = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", receipt["stdout"] + "\n" + receipt["stderr"]).replace(
                "\r\n", "\n"
            )
            call["test_summaries"] = {runner: _successful_test_summary(output, runner) for runner in TEST_RUNNERS}
            call["test_failures"] = {runner: _recognized_test_failure(output, runner) for runner in TEST_RUNNERS}


def _successful_test_summary(output: str, runner: str) -> str:
    """Retain only a nonzero success summary, not arbitrary shell output in trace summaries."""
    if runner == "unittest":
        count = re.search(r"(?m)^Ran ([1-9]\d*) tests? in [^\r\n]+$", output)
        ok = re.search(r"(?m)^OK(?: \(skipped=(\d+)\))?\s*$", output)
        if count and ok and int(ok.group(1) or 0) < int(count.group(1)):
            return count.group(0) + "; " + ok.group(0).strip()
    else:
        if re.search(r"\b[1-9]\d* (?:failed|errors?)\b", output):
            return ""
        pattern = (
            r"(?m)^\s*(?:=+\s*)?[1-9]\d* passed\b[^\r\n]*$"
            if runner == "pytest"
            else r"(?m)^\s*Tests\s+[1-9]\d* passed\b[^\r\n]*$"
        )
        match = re.search(pattern, output)
        if match:
            return match.group(0).strip()
    return ""


def _recognized_test_failure(output: str, runner: str) -> str:
    """Recognized completed test runs that prove verification failed, not that grading is unsupported."""
    if runner == "unittest":
        count = re.search(r"(?m)^Ran (\d+) tests? in [^\r\n]+$", output)
        ok = re.search(r"(?m)^OK(?: \(skipped=(\d+)\))?\s*$", output)
        if count and ok:
            total = int(count.group(1))
            skipped = int(ok.group(1) or 0)
            if total == 0:
                return "matched shell result ran zero tests"
            if skipped >= total:
                return "matched shell result skipped every discovered test"
    return ""


def is_rooted(value: object) -> bool:
    """True when a path is absolute in POSIX form or in this platform's form.

    A tool transcript carries whatever shape the runner produced, and ``Path("/a/b").is_absolute()``
    is False on Windows because the path has no drive. Reading a rooted POSIX path as relative would
    make an out-of-workspace read that succeeded look like a harmless relative one.
    """
    if value is None:
        return False
    if str(value).replace("\\", "/").startswith("/"):
        return True
    return Path(str(value)).is_absolute()


# How a native conversation's invocations combine into one trace. Every TraceSummary field has a rule,
# so a new field is merged on purpose rather than kept from the last invocation by default.
MERGED_FROM_FIRST = (
    "main_skills",
    "main_skills_before_effects",
    "parent_reads_before_dispatch",
    "parent_skills_before_dispatch",
)
MERGED_IN_ORDER = (
    "skills",
    "skills_failed",
    "bash_commands",
    "powershell_commands",
    "subagent_bash_commands",
    "dispatches",
    "agents",
    "agents_failed",
    "read_attempts",
    "denials",
    "tool_errors",
    "denial_details",
    "subagent_tool_ids",
    "agent_returns",
    "init_session_ids",
)
MERGED_AS_SET = ("models", "main_models", "usage_models")
MERGED_AS_SUM = ("duration_ms", "total_tokens", "output_tokens", "num_turns", "total_cost_usd")  # unknown if any is
# The conversation's final result and session, and the runtime profile each invocation is checked on
# before grading, come from the last invocation; so do the ordered effect calls, whose trace line
# numbers count within one invocation's file.
MERGED_FROM_LAST = (
    "result_text",
    "has_result",
    "result_is_error",
    "result_subtype",
    "session_id",
    "saw_init",
    "advertised_tools",
    "mcp_servers",
    "permission_mode",
    "runtime_plugins",
    "effect_calls",
)
MERGED_SPECIALLY = ("tool_counts", "conversation_sessions")  # summed per tool; one session per invocation


def parse_trial_trace(run_dir: Path) -> TraceSummary:
    """Merge invocation evidence, charging only the last cumulative result within each invocation."""
    traces = [parse_trace(run_dir / "stdout.jsonl")]
    followup = run_dir / "followup" / "stdout.jsonl"
    if followup.is_file():
        traces.append(parse_trace(followup))
    merged = replace(traces[-1], conversation_sessions=[trace.session_id for trace in traces])
    for name in MERGED_FROM_FIRST:
        setattr(merged, name, getattr(traces[0], name))
    for name in MERGED_IN_ORDER:
        setattr(merged, name, [value for trace in traces for value in getattr(trace, name)])
    for name in MERGED_AS_SET:
        setattr(merged, name, sorted({value for trace in traces for value in getattr(trace, name)}))
    merged.tool_counts = {
        name: sum(trace.tool_counts.get(name, 0) for trace in traces)
        for name in {name for trace in traces for name in trace.tool_counts}
    }
    for name in MERGED_AS_SUM:
        values = [getattr(trace, name) for trace in traces]
        setattr(merged, name, sum(values) if all(value is not None for value in values) else None)
    return merged


# What a run's trace summary (outputs/trace-summary.json) saves of its trace, by saved name and
# TraceSummary field, in the order it writes them. A regrade restores the summary's facts from these
# names when the raw trace is gone.
SUMMARY_FIELDS: Final = {
    "conversation_sessions": "conversation_sessions",
    "agent_returns": "agent_returns",
    "initial_parent_reference_reads": "parent_reads_before_dispatch",
    "initial_parent_skills_before_dispatch": "parent_skills_before_dispatch",
    "main_models": "main_models",
    "models": "models",
    "usage_models": "usage_models",
    "num_turns": "num_turns",
    "tool_counts": "tool_counts",
    "skills": "skills",
    "skills_failed": "skills_failed",
    "advertised_tools": "advertised_tools",
    "mcp_servers": "mcp_servers",
    "permission_mode": "permission_mode",
    "dispatches": "dispatches",
    "denials": "denials",
    "bash_commands": "bash_commands",
    "subagent_bash_commands": "subagent_bash_commands",
    "powershell_commands": "powershell_commands",
    "effect_calls": "effect_calls",
    "tool_errors": "tool_errors",
    "denial_details": "denial_details",
}
# What a summary restores when the raw trace is gone: the calls, loads, dispatches and errors a check
# may re-measure from it. Returns, reads and completion order are saved for a reader, but a regrade
# measures them only from the raw trace (checking.RAW_ONLY), so restoring them could only mislead.
RESTORED: Final = (
    "skills",
    "skills_failed",
    "bash_commands",
    "subagent_bash_commands",
    "powershell_commands",
    "dispatches",
    "tool_errors",
    "tool_counts",
)


def to_saved(trace: TraceSummary) -> dict[str, Any]:
    """The trace facts a trace summary saves, by saved name."""
    return {saved: getattr(trace, name) for saved, name in SUMMARY_FIELDS.items()}


def from_saved(summary: Mapping[str, Any], result_text: str) -> TraceSummary:
    """The trace a saved summary restores when the raw trace is gone: its final text and `RESTORED`."""
    restored: dict[str, Any] = {}
    for saved, name in SUMMARY_FIELDS.items():
        if name in RESTORED:
            value = summary.get(saved)
            restored[name] = dict(value or {}) if name == "tool_counts" else list(value or [])
    return TraceSummary(result_text=result_text, **restored)


def runtime_namespace(trace: TraceSummary, plugin_root: Path) -> str:
    """The plugin namespace a component fires under — the loaded plugin's name, or the manifest's."""
    if trace.runtime_plugins:
        name = trace.runtime_plugins[0]
        if isinstance(name, dict) and name.get("name"):
            return str(name["name"])
    manifest = json.loads((plugin_root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    return str(manifest["name"])


def completed_components(trace: TraceSummary, kind: str) -> set[str]:
    """Components whose invocation completed with a non-error tool result."""
    return set(trace.skills if kind == "skill" else trace.agents)
