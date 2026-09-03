"""Claude plugin eval command construction and the callable-tool boundary check.

One host, one command shape. This was a polymorphic adapter class while the fleet measured more
than one engine; Codex was retired as a distribution target on 2026-08-23 and the multi-engine
evaluation ADR was superseded, so what remains is three functions and their constants.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence


READ_TOOLS = ("Glob", "Grep", "Read")
BASE_TOOLS = ("Skill", "Task")
# The exact empty-MCP-server-set literal every clean-room spawn passes alongside
# `--strict-mcp-config`, so no account-level connector can join the namespace. Shared with
# evals/judge.py rather than duplicated -- that spawn also denies tools and MCP entirely.
EMPTY_MCP_CONFIG = '{"mcpServers":{}}'
DENIED_TOOLS = (
    "Bash",
    "Edit",
    "Write",
    "NotebookEdit",
    "Read",
    "Glob",
    "Grep",
    "WebFetch",
    "WebSearch",
    "ToolSearch",
    "CronCreate",
    "CronDelete",
    "DesignSync",
    "EnterWorktree",
    "ExitWorktree",
    "PushNotification",
    "RemoteTrigger",
    "ScheduleWakeup",
    "Workflow",
    "TaskCreate",
    "TaskUpdate",
    "TaskStop",
    "Monitor",
)


def _is_rooted(value: object) -> bool:
    """True when a path is absolute in POSIX form or in this platform's form.

    A tool transcript carries whatever shape the runner produced, and
    ``Path("/a/b").is_absolute()`` is False on Windows because the path has no drive. Reading a
    rooted POSIX path as relative would make an out-of-snapshot read that succeeded look like a
    harmless relative one, so the boundary check must accept both shapes on every platform.
    """
    if value is None:
        return False
    if str(value).replace("\\", "/").startswith("/"):
        return True
    return Path(value).is_absolute()


class AdapterError(ValueError):
    """An adapter command, trace, or host boundary was invalid."""


@dataclass(frozen=True)
class ToolAttempt:
    tool: str
    path: str | None
    outcome: str


def build_command(
    *,
    scenario: Mapping[str, object],
    executable: str,
    plugin_root: Path,
    qualified_target: str,
    model: str | None,
) -> list[str]:
    target = scenario["target"]
    if not isinstance(target, Mapping):
        raise AdapterError("scenario target must be an object")
    prompt = scenario.get("prompt")
    if not isinstance(prompt, str) or not prompt:
        raise AdapterError("scenario prompt must be non-empty")
    command = [executable]
    if scenario.get("mode") == "direct":
        if target.get("kind") == "skill":
            prompt = (
                f"Use the Skill tool to invoke `{qualified_target}` before answering. "
                "If the Skill call does not complete successfully, do not answer the task.\n\n"
                f"{prompt}"
            )
        elif target.get("kind") == "agent":
            command += ["--agent", qualified_target]
        else:
            raise AdapterError("direct scenario target kind must be skill or agent")
    # Agent-target discovery may dispatch a tool-minimal agent (reviewer,
    # repository-investigator, scribe, researcher) whose own declared tools are Read/Grep/Glob
    # with no Skill or Agent grant. The CLI refuses to spawn a subagent whose declared tools
    # resolve to nothing, so the three read tools must be granted here too; the clean room's
    # workspace is empty and outside the checkout, so reads there are harmless.
    agent_target_discovery = scenario.get("mode") != "direct" and target.get("kind") == "agent"
    allowed_tools = (
        tuple(sorted((*BASE_TOOLS, *READ_TOOLS))) if agent_target_discovery else BASE_TOOLS
    )
    denied = [tool for tool in DENIED_TOOLS if tool not in allowed_tools]
    command += [
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--verbose",
        "--forward-subagent-text",
        "--no-session-persistence",
        "--plugin-dir",
        str(plugin_root.resolve()),
        "--mcp-config",
        EMPTY_MCP_CONFIG,
        "--strict-mcp-config",
        "--tools",
        ",".join(allowed_tools),
        "--disallowedTools",
        ",".join(denied),
    ]
    if model:
        command += ["--model", model]
    return command


def validate_tool_boundary(
    *,
    advertised: Sequence[str],
    expected: Sequence[str],
    attempts: Sequence[ToolAttempt],
    plugin_root: Path,
    callable_read_tools: Sequence[str] = (),
    allowed_roots: Sequence[Path] = (),
) -> None:
    # `allowed_roots` are harness-owned trees a callable read may resolve into besides the plugin
    # snapshot — the neutral fixture workspace the trial runs in, whose digest the run records.
    # A relative read resolves against it, so a cwd-relative Grep/Glob is in bounds there and
    # out of bounds anywhere else (HOST-003 owner decision, 2026-08-28).
    roots = [root.resolve() for root in allowed_roots]
    unexpected = set(advertised) - set(expected)
    missing = set(expected) - set(advertised)
    if unexpected:
        raise AdapterError(f"unexpected advertised tool(s): {sorted(unexpected)}")
    if missing:
        raise AdapterError(f"missing advertised tool(s): {sorted(missing)}")
    snapshot = plugin_root.resolve()
    callable_tools = set(callable_read_tools)
    if callable_tools - set(READ_TOOLS):
        raise AdapterError(f"unknown callable read tool(s): {sorted(callable_tools - set(READ_TOOLS))}")
    for attempt in attempts:
        if attempt.outcome not in {"allowed", "denied", "ambiguous"}:
            raise AdapterError(f"unknown tool outcome {attempt.outcome!r}")
        if attempt.outcome == "ambiguous":
            raise AdapterError(f"ambiguous callable outcome for {attempt.tool}")
        if attempt.tool not in READ_TOOLS:
            continue
        if not attempt.path:
            raise AdapterError(f"{attempt.tool} attempt has no path evidence")
        if attempt.outcome == "allowed" and attempt.tool not in callable_tools:
            raise AdapterError(f"unexpected callable read tool: {attempt.tool}")
        normalized = attempt.path.replace("\\", "/")
        if ".." in PurePosixPath(normalized).parts:
            raise AdapterError(f"path traversal attempted by {attempt.tool}: {attempt.path}")
        prefix = normalized
        for marker in ("*", "?", "["):
            prefix = prefix.split(marker, 1)[0]
        candidate = Path(prefix or normalized)
        if not _is_rooted(candidate):
            if attempt.outcome == "allowed" and not roots:
                raise AdapterError(f"successful out-of-snapshot relative read: {attempt.path}")
            continue
        try:
            resolved_candidate = candidate.resolve()
            inside = resolved_candidate.is_relative_to(snapshot) or any(
                resolved_candidate.is_relative_to(root) for root in roots
            )
        except OSError as exc:
            raise AdapterError(f"cannot normalize tool path {attempt.path!r}: {exc}") from exc
        if attempt.outcome == "allowed" and not inside:
            raise AdapterError(f"successful out-of-snapshot read: {attempt.path}")
