"""Explicit host adapters for Claude plugin and Codex context-bundle eval execution."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence

import engine_contract


ADAPTER_VERSION = "1"
READ_TOOLS = ("Glob", "Grep", "Read")
BASE_TOOLS = ("Skill", "Task")
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
API_KEY_ENV = {
    "ANTHROPIC_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "CODEX_API_KEY",
    "OPENAI_API_KEY",
}
PROVIDER_ENV_PREFIXES = ("ANTHROPIC_", "AZURE_OPENAI_", "OPENAI_")
CANARY_RE = re.compile(r"^q_[a-z0-9_]{3,}$")


class AdapterError(ValueError):
    """An adapter command, trace, or host boundary was invalid."""


@dataclass(frozen=True)
class ToolAttempt:
    tool: str
    path: str | None
    outcome: str


@dataclass(frozen=True)
class CodexTrace:
    response: str
    reference_canaries: tuple[str, ...]
    resolved_model: str
    policy_sha256: str
    usage: Mapping[str, int]
    complete: bool


CODEX_EFFECTIVE_POLICY = {
    "additional_directories": [],
    "approval_policy": "never",
    "mcp_servers": [],
    "network_access": False,
    "rules_loaded": False,
    "sandbox": "read-only",
    "shell_environment_inherit": "none",
    "user_config_loaded": False,
}


def _policy_digest(value: Mapping[str, object]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(b"save-toolkit-engine-policy-v1\0" + encoded).hexdigest()


class ClaudeNativeAdapter:
    name = "claude-plugin"
    version = ADAPTER_VERSION
    supported_claims = engine_contract.ENGINE_CLAIMS[name]

    def build_command(
        self,
        *,
        scenario: Mapping[str, object],
        executable: str,
        plugin_root: Path,
        qualified_target: str,
        model: str | None,
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
            if denied_probe_path is None or not denied_probe_path.is_absolute():
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
                *(f"- Use Read on {path}. It must succeed." for path in reference_paths),
                f"- Use Read on {denied_probe_path.resolve()}. It must be denied.",
                "Continue with the task only after making every probe. Do not quote the denied file.",
            ]
            prompt = "\n".join(preflight) + "\n\n" + prompt
        allowed_tools = tuple(sorted((*BASE_TOOLS, *READ_TOOLS))) if enable_snapshot_reads else BASE_TOOLS
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
            '{"mcpServers":{}}',
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
        return command

    def policy_sha256(self, *, enable_snapshot_reads: bool) -> str:
        return _policy_digest(
            {
                "adapter": self.name,
                "version": self.version,
                "claims": sorted(self.supported_claims),
                "base_tools": list(BASE_TOOLS),
                "read_tools": list(READ_TOOLS) if enable_snapshot_reads else [],
                "denied_tools": [
                    tool
                    for tool in DENIED_TOOLS
                    if not enable_snapshot_reads or tool not in READ_TOOLS
                ],
                "empty_mcp": True,
                "permission_mode": "dontAsk" if enable_snapshot_reads else None,
                "positive_and_negative_boundary_preflight": enable_snapshot_reads,
            }
        )

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
    ) -> None:
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
            if not candidate.is_absolute():
                if attempt.outcome == "allowed":
                    raise AdapterError(f"successful out-of-snapshot relative read: {attempt.path}")
                continue
            try:
                resolved_candidate = candidate.resolve()
                inside = resolved_candidate.is_relative_to(snapshot)
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


class CodexResolvedContextAdapter:
    name = "codex-cli"
    version = ADAPTER_VERSION
    supported_claims = engine_contract.ENGINE_CLAIMS[name]

    def require_safe_live_activation(self) -> None:
        """Fail until the host can structurally remove Codex access to non-bundle files."""

        raise AdapterError(
            "Codex live execution is disabled: read-only prevents writes but does not confine "
            "tool reads away from HOME/CODEX_HOME; require a proven no-tool or bundle-only "
            "runtime boundary before any subscriber-backed model process starts"
        )

    def build_command(
        self,
        *,
        executable: str,
        bundle_root: Path,
        response_schema: Path,
        model: str,
    ) -> list[str]:
        if not model.strip():
            raise AdapterError("Codex evals require one explicit model")
        root = bundle_root.resolve()
        schema = response_schema.resolve()
        if not schema.is_relative_to(root):
            raise AdapterError("response schema must be inside the resolved context bundle")
        return [
            executable,
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--strict-config",
            "--config",
            "shell_environment_policy.inherit=none",
            "--config",
            'approval_policy="never"',
            "--sandbox",
            "read-only",
            "--skip-git-repo-check",
            "--json",
            "--output-schema",
            str(schema),
            "--cd",
            str(root),
            "--model",
            model,
            "-",
        ]

    def sanitized_environment(self, source: Mapping[str, str] | None = None) -> dict[str, str]:
        environment = dict(source if source is not None else os.environ)
        for name in tuple(environment):
            if name in API_KEY_ENV or name.startswith(PROVIDER_ENV_PREFIXES):
                environment.pop(name, None)
        environment["NO_COLOR"] = "1"
        return environment

    def requested_policy_sha256(self) -> str:
        return _policy_digest(
            {
                "adapter": self.name,
                "version": self.version,
                "claims": sorted(self.supported_claims),
                "ephemeral": True,
                "ignore_user_config": True,
                "ignore_rules": True,
                "strict_config": True,
                "sandbox": "read-only",
                "approval_policy": "never",
                "skip_git_repository_check": True,
                "shell_environment_policy": {"inherit": "none"},
                "session_resume": False,
                "structured_output_required": True,
                "additional_directories": [],
                "mcp_configuration": "ignored with user config; none supplied",
                "provider_environment": "removed",
            }
        )

    def parse_trace(self, raw: str, *, requested_model: str) -> CodexTrace:
        events: list[Mapping[str, object]] = []

        def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
            value: dict[str, object] = {}
            for key, child in pairs:
                if key in value:
                    raise AdapterError(f"duplicate JSON trace key {key!r}")
                value[key] = child
            return value

        for line_number, line in enumerate(raw.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line, object_pairs_hook=reject_duplicates)
            except (json.JSONDecodeError, AdapterError) as exc:
                raise AdapterError(f"invalid Codex JSONL at line {line_number}: {exc}") from exc
            if not isinstance(event, Mapping) or not isinstance(event.get("type"), str):
                raise AdapterError(f"invalid Codex event at line {line_number}")
            events.append(event)
        if any(event["type"] in {"turn.failed", "error"} for event in events):
            raise AdapterError("Codex trace reports a failed turn")
        started_events = [event for event in events if event["type"] == "thread.started"]
        completed = [event for event in events if event["type"] == "turn.completed"]
        messages: list[str] = []
        for event in events:
            if event["type"] != "item.completed":
                continue
            item = event.get("item")
            if isinstance(item, Mapping) and item.get("type") == "agent_message":
                text = item.get("text")
                if isinstance(text, str) and text:
                    messages.append(text)
        if len(started_events) != 1 or len(completed) != 1 or not messages:
            raise AdapterError("incomplete Codex trace")
        started = started_events[0]
        resolved_model = started.get("model")
        if not isinstance(resolved_model, str) or not resolved_model.strip():
            raise AdapterError("Codex trace does not report the resolved model identity")
        effective_policy = started.get("effective_policy")
        if not isinstance(effective_policy, Mapping):
            raise AdapterError("Codex trace does not report the effective ambient policy")
        if dict(effective_policy) != CODEX_EFFECTIVE_POLICY:
            raise AdapterError(
                "Codex effective ambient policy does not match the approved read-only contract"
            )
        policy_sha256 = _policy_digest(
            {
                "adapter": self.name,
                "version": self.version,
                "requested": self.requested_policy_sha256(),
                "effective": dict(effective_policy),
            }
        )
        usage_raw = completed[0].get("usage")
        usage: dict[str, int] = {}
        if isinstance(usage_raw, Mapping):
            for key, amount in usage_raw.items():
                if isinstance(key, str) and isinstance(amount, int) and not isinstance(amount, bool) and amount >= 0:
                    usage[key] = amount
        raw_response = messages[-1]
        try:
            structured = json.loads(raw_response, object_pairs_hook=reject_duplicates)
        except (json.JSONDecodeError, AdapterError) as exc:
            raise AdapterError("Codex final message is not the bound structured response") from exc
        if not isinstance(structured, Mapping) or set(structured) != {
            "response", "reference_canaries"
        }:
            raise AdapterError("Codex final message is not the bound structured response")
        response = structured["response"]
        structured_canaries = structured["reference_canaries"]
        if not isinstance(response, str) or not response:
            raise AdapterError("Codex structured response text must be non-empty")
        if (
            not isinstance(structured_canaries, list)
            or not all(
                isinstance(token, str) and CANARY_RE.fullmatch(token)
                for token in structured_canaries
            )
            or len(structured_canaries) != len(set(structured_canaries))
        ):
            raise AdapterError("Codex structured reference_canaries are invalid")
        canaries = tuple(structured_canaries)
        return CodexTrace(
            response=response,
            reference_canaries=canaries,
            resolved_model=resolved_model,
            policy_sha256=policy_sha256,
            usage=usage,
            complete=True,
        )
