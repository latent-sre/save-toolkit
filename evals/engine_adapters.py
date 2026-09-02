"""Explicit host adapter for Claude plugin eval execution."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence


ADAPTER_VERSION = "2"
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


def _policy_digest(value: Mapping[str, object]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(b"save-toolkit-engine-policy-v1\0" + encoded).hexdigest()


class ClaudeNativeAdapter:
    name = "claude-plugin"
    version = ADAPTER_VERSION
    supported_claims = frozenset(
        {
            "candidate_snapshot_integrity",
            "native_plugin_loaded",
            "native_component_invoked",
            "advertised_tool_inventory",
            "callable_tool_boundary",
            "reference_used",
            "behavioral_contract",
            "deterministic_grader_result",
        }
    )

    def build_command(
        self,
        *,
        scenario: Mapping[str, object],
        executable: str,
        plugin_root: Path,
        qualified_target: str,
        model: str | None,
        reasoning_effort: str | None = None,
        enable_snapshot_reads: bool = False,
        required_reference_paths: Sequence[str] = (),
        denied_probe_path: Path | None = None,
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
        if enable_snapshot_reads:
            if not required_reference_paths:
                raise AdapterError("snapshot reads require at least one positive reference probe")
            if not _is_rooted(denied_probe_path):
                raise AdapterError("snapshot reads require one absolute negative boundary probe")
            reference_paths = [
                (plugin_root / relative).resolve()
                for relative in required_reference_paths
            ]
            snapshot = plugin_root.resolve()
            if any(not path.is_relative_to(snapshot) for path in reference_paths):
                raise AdapterError("positive reference probe escaped the plugin snapshot")
            preflight = [
                "Before the task, perform this evaluator boundary preflight exactly:",
                # POSIX form, matching the --allowedTools glob built from as_posix() below.
                # A backslash path here would instruct the model to read a file the
                # permission pattern does not cover, so the probe would be denied for the
                # wrong reason and the boundary check would read as a real refusal.
                *(f"- Use Read on {path.as_posix()}. It must succeed." for path in reference_paths),
                f"- Use Read on {denied_probe_path.resolve().as_posix()}. It must be denied.",
                "Continue with the task only after making every probe. Do not quote the denied file.",
            ]
            prompt = "\n".join(preflight) + "\n\n" + prompt
        # Agent-target discovery may dispatch a tool-minimal agent (reviewer,
        # repository-investigator, scribe, researcher) whose own declared tools are Read/Grep/Glob
        # with no Skill or Agent grant. The CLI refuses to spawn a subagent whose declared tools
        # resolve to nothing, so the three read tools must be granted here too; the clean room's
        # workspace is empty and outside the checkout, so reads there are harmless.
        agent_target_discovery = scenario.get("mode") != "direct" and target.get("kind") == "agent"
        allowed_tools = (
            tuple(sorted((*BASE_TOOLS, *READ_TOOLS)))
            if enable_snapshot_reads or agent_target_discovery
            else BASE_TOOLS
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
        if enable_snapshot_reads:
            root_pattern = plugin_root.resolve().as_posix().rstrip("/") + "/**"
            command += [
                "--allowedTools",
                ",".join(f"{tool}({root_pattern})" for tool in ("Read", "Grep", "Glob")),
                "--permission-mode",
                "dontAsk",
            ]
        if model:
            command += ["--model", model]
        if reasoning_effort:
            command += ["--effort", reasoning_effort]
        return command

    def policy_sha256(
        self,
        *,
        enable_snapshot_reads: bool,
        agent_target_discovery: bool = False,
        reasoning_effort: str | None = None,
        adapter_version: str | None = None,
    ) -> str:
        # The read grant is real under either flag; the digest must change whenever the effective
        # tool inventory does, or an agent-target discovery trial would share a policy identity
        # with a base-set trial it did not run under.
        reads_granted = enable_snapshot_reads or agent_target_discovery
        policy: dict[str, object] = {
                "adapter": self.name,
                "version": adapter_version or self.version,
                "claims": sorted(self.supported_claims),
                "base_tools": list(BASE_TOOLS),
                "read_tools": list(READ_TOOLS) if reads_granted else [],
                "denied_tools": [
                    tool
                    for tool in DENIED_TOOLS
                    if not reads_granted or tool not in READ_TOOLS
                ],
                "empty_mcp": True,
                "permission_mode": "dontAsk" if enable_snapshot_reads else None,
                "positive_and_negative_boundary_preflight": enable_snapshot_reads,
            }
        if agent_target_discovery:
            policy["agent_target_discovery_reads"] = True
        if reasoning_effort is not None:
            policy["reasoning_effort"] = reasoning_effort
        return _policy_digest(policy)

    def validate_tool_boundary(
        self,
        *,
        advertised: Sequence[str],
        expected: Sequence[str],
        attempts: Sequence[ToolAttempt],
        plugin_root: Path,
        callable_read_tools: Sequence[str] = (),
        required_allowed_paths: Sequence[Path] = (),
        required_denied_path: Path | None = None,
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
        required_allowed = {path.resolve() for path in required_allowed_paths}
        if any(not path.is_relative_to(snapshot) for path in required_allowed):
            raise AdapterError("positive boundary probe is outside the plugin snapshot")
        denied_probe = required_denied_path.resolve() if required_denied_path else None
        if denied_probe is not None and denied_probe.is_relative_to(snapshot):
            raise AdapterError("negative boundary probe must be outside the plugin snapshot")
        observed_allowed: set[Path] = set()
        observed_denied = False
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
            if attempt.tool == "Read" and attempt.outcome == "allowed":
                if resolved_candidate in required_allowed:
                    observed_allowed.add(resolved_candidate)
            if (
                attempt.tool == "Read"
                and attempt.outcome == "denied"
                and denied_probe is not None
                and resolved_candidate == denied_probe
            ):
                observed_denied = True
        missing_allowed = required_allowed - observed_allowed
        if missing_allowed:
            raise AdapterError(
                f"missing successful in-snapshot boundary probe(s): "
                f"{sorted(str(path) for path in missing_allowed)}"
            )
        if denied_probe is not None and not observed_denied:
            raise AdapterError("missing denied out-of-snapshot boundary probe")

