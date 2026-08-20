#!/usr/bin/env python3
"""Fail-closed Codex CLI 0.148 JSONL parsing and sanitized evidence facts.

The parser retains the final agent message only as transient in-memory grading input.  Callers must
persist :meth:`ParsedTrace.persistable_facts`, which contains hashes and bounded structural facts,
never raw prompts, responses, command output, paths, or session identifiers.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from typing import Mapping

CODEX_CLI_VERSION = "0.148.0"
MODEL = "gpt-5.6-terra"
REASONING_EFFORT = "medium"
SANDBOX_MODE = "read-only"
APPROVAL_POLICY = "never"
TIMEOUT_SECONDS = 300
TRIALS = 2


@dataclass(frozen=True)
class TrialSpec:
    """One immutable ROUTE-001 scenario/revision/trial coordinate."""

    scenario_id: str
    cohort: str
    revision: str
    trial: int
    scenario_sha256: str

_TOP_LEVEL_EVENTS = {
    "thread.started",
    "turn.started",
    "turn.completed",
    "turn.failed",
    "item.started",
    "item.updated",
    "item.completed",
    "error",
}
_HOOK_EVENTS = {"SessionStart", "SubagentStart", "PostToolUse"}
_TERMINAL_EVENTS = {"turn.completed", "turn.failed"}
_COMPLETION_ONLY_ITEMS = {"agent_message", "reasoning"}
_ALLOWED_ITEM_TYPES = _COMPLETION_ONLY_ITEMS | {
    "command_execution",
    "collab_tool_call",
}
_COMMAND_STATUSES = {"in_progress", "completed", "failed", "declined"}
_COLLAB_TOOLS = {"spawn_agent", "send_input", "wait", "close_agent"}
_COLLAB_STATUSES = {"in_progress", "completed", "failed"}
_AGENT_STATES = {
    "pending_init",
    "running",
    "interrupted",
    "completed",
    "errored",
    "shutdown",
    "not_found",
}
_USAGE_FIELDS = {
    "input_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
}
_LABEL_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_COMPONENT_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,127}$")
_CREDENTIAL_PATTERNS = (
    re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{16,}\b"),
    re.compile(
        r"(?i)\b(?:authorization|proxy-authorization)\s*:\s*bearer\s+"
        r"[A-Za-z0-9._~+/=-]{12,}"
    ),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    re.compile(
        r"(?i)\b(?:password|passwd|api[_-]?key|access[_-]?token|refresh[_-]?token|"
        r"client[_-]?secret)[\"']?\s*[:=]\s*[\"']?"
        r"(?!<redacted>|redacted\b|\*{3,})[^\s\"',;]{4,}"
    ),
)


class TraceError(ValueError):
    """The JSONL stream cannot be trusted as one complete Codex turn."""


class CredentialExposureError(TraceError):
    """A raw trace value resembles a credential and must not enter evidence handling."""


class HookReceiptError(TraceError):
    """Hook JSONL cannot be trusted as one coherent Codex session receipt set."""


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalized_path_bytes(path: str | os.PathLike[str]) -> bytes:
    """Return deterministic host-normalized absolute path bytes for hashing only."""

    raw = os.fspath(path)
    if not isinstance(raw, str) or not raw:
        raise ValueError("path must be a non-empty string-like value")
    normalized = os.path.normcase(os.path.normpath(os.path.abspath(raw))).replace("\\", "/")
    return normalized.encode("utf-8")


def sanitized_path_fact(label: str, path: str | os.PathLike[str]) -> dict[str, str]:
    """Describe a path by an operator-safe label and normalized digest, never by its bytes."""

    if not isinstance(label, str) or not _LABEL_RE.fullmatch(label):
        raise ValueError("path fact label must be a lowercase underscore slug")
    return {
        "label": label,
        "path_sha256": hashlib.sha256(normalized_path_bytes(path)).hexdigest(),
    }


@dataclass(frozen=True)
class CommandFact:
    """Persistable facts from one terminal command_execution item."""

    item_sha256: str
    command_sha256: str
    output_sha256: str
    output_bytes: int
    exit_code: int | None
    status: str

    def as_dict(self) -> dict[str, object]:
        return {
            "item_sha256": self.item_sha256,
            "command_sha256": self.command_sha256,
            "output_sha256": self.output_sha256,
            "output_bytes": self.output_bytes,
            "exit_code": self.exit_code,
            "status": self.status,
        }


@dataclass(frozen=True)
class CollabToolFact:
    """Persistable facts from one terminal collab_tool_call item."""

    item_sha256: str
    tool: str
    status: str
    sender_thread_sha256: str
    receiver_thread_sha256s: tuple[str, ...]
    prompt_sha256: str | None
    agent_state_counts: dict[str, int]

    @property
    def receiver_count(self) -> int:
        return len(self.receiver_thread_sha256s)

    def as_dict(self) -> dict[str, object]:
        return {
            "item_sha256": self.item_sha256,
            "tool": self.tool,
            "status": self.status,
            "sender_thread_sha256": self.sender_thread_sha256,
            "receiver_thread_sha256s": list(self.receiver_thread_sha256s),
            "receiver_count": self.receiver_count,
            "prompt_sha256": self.prompt_sha256,
            "agent_state_counts": dict(sorted(self.agent_state_counts.items())),
        }


@dataclass(frozen=True)
class ParsedTrace:
    """Validated trace with one explicitly transient raw field for behavior grading."""

    event_count: int
    terminal: str
    thread_sha256: str
    last_agent_message: str | None
    terminal_error_sha256: str | None
    usage: dict[str, int] | None
    command_facts: tuple[CommandFact, ...]
    collab_tool_facts: tuple[CollabToolFact, ...]

    def persistable_facts(self) -> dict[str, object]:
        """Return the only trace representation suitable for serialized evidence."""

        return {
            "schema_version": 1,
            "event_count": self.event_count,
            "terminal": self.terminal,
            "thread_sha256": self.thread_sha256,
            "last_agent_message_present": self.last_agent_message is not None,
            "last_agent_message_sha256": (
                _sha256_text(self.last_agent_message)
                if self.last_agent_message is not None
                else None
            ),
            "terminal_error_sha256": self.terminal_error_sha256,
            "usage": dict(self.usage) if self.usage is not None else None,
            "command_facts": [fact.as_dict() for fact in self.command_facts],
            "collab_tool_facts": [fact.as_dict() for fact in self.collab_tool_facts],
        }


@dataclass(frozen=True)
class TransientToolReceipt:
    """Raw PostToolUse values retained only for immediate in-memory grading."""

    tool_name: str
    agent_type: str | None
    tool_input: object = field(repr=False)
    tool_response: object = field(repr=False)


@dataclass(frozen=True)
class PostToolUseFact:
    """Persistable, identifier-free digest facts for one trusted PostToolUse receipt."""

    tool_name: str
    agent_type: str | None
    tool_input_sha256: str
    tool_response_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "tool_name": self.tool_name,
            "agent_type": self.agent_type,
            "tool_input_sha256": self.tool_input_sha256,
            "tool_response_sha256": self.tool_response_sha256,
        }


@dataclass(frozen=True)
class ParsedHookReceipts:
    """Validated hook receipts with raw tool values separated from persistable facts."""

    receipt_count: int
    tool_receipts: tuple[TransientToolReceipt, ...] = field(repr=False)
    post_tool_use_facts: tuple[PostToolUseFact, ...]
    hook_event_counts: dict[str, int]
    model_counts: dict[str, int]
    agent_type_counts: dict[str, int]
    tool_name_counts: dict[str, int]

    def persistable_facts(self) -> dict[str, object]:
        """Return facts without session, turn, agent, tool-use IDs, raw values, or paths."""

        return {
            "schema_version": 1,
            "receipt_count": self.receipt_count,
            "hook_event_counts": dict(sorted(self.hook_event_counts.items())),
            "model_counts": dict(sorted(self.model_counts.items())),
            "agent_type_counts": dict(sorted(self.agent_type_counts.items())),
            "tool_name_counts": dict(sorted(self.tool_name_counts.items())),
            "post_tool_use_facts": [fact.as_dict() for fact in self.post_tool_use_facts],
        }


def _reject_credentials(value: object, *, location: str) -> None:
    if isinstance(value, str):
        for pattern in _CREDENTIAL_PATTERNS:
            if pattern.search(value):
                raise CredentialExposureError(
                    f"credential-shaped text rejected at {location}"
                )
        return
    if isinstance(value, Mapping):
        for index, (key, child) in enumerate(value.items()):
            _reject_credentials(key, location=f"{location}.key[{index}]")
            if isinstance(key, str) and isinstance(child, str):
                _reject_credentials(
                    f"{key}: {child}", location=f"{location}.field[{index}]"
                )
            _reject_credentials(child, location=f"{location}.value[{index}]")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _reject_credentials(child, location=f"{location}[{index}]")


def reject_credentials(value: object, *, location: str) -> None:
    """Reject credential-shaped content before a caller records or reduces it."""

    if not isinstance(location, str) or not location:
        raise ValueError("credential scan location must be a non-empty string")
    _reject_credentials(value, location=location)


def _require_string(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise TraceError(f"{field} must be a non-empty string")
    return value


def _require_item(event: Mapping[str, object], *, event_type: str) -> Mapping[str, object]:
    item = event.get("item")
    if not isinstance(item, Mapping):
        raise TraceError(f"{event_type} requires an object item")
    _require_string(item.get("id"), field=f"{event_type}.item.id")
    _require_string(item.get("type"), field=f"{event_type}.item.type")
    return item


def _validate_command_item(item: Mapping[str, object], *, phase: str) -> None:
    _require_string(item.get("command"), field="command_execution.command")
    if not isinstance(item.get("aggregated_output"), str):
        raise TraceError("command_execution.aggregated_output must be a string")
    status = item.get("status")
    if not isinstance(status, str) or status not in _COMMAND_STATUSES:
        raise TraceError("command_execution.status is invalid")
    exit_code = item.get("exit_code")
    if isinstance(exit_code, bool) or (exit_code is not None and not isinstance(exit_code, int)):
        raise TraceError("command_execution.exit_code must be an integer or null")
    if phase == "started" and (status != "in_progress" or exit_code is not None):
        raise TraceError("started command_execution must be in_progress with null exit_code")
    if phase == "completed" and status == "in_progress":
        raise TraceError("completed command_execution cannot remain in_progress")


def _collab_fields(
    item: Mapping[str, object],
    *,
    phase: str,
) -> tuple[str, str, list[str], str | None, dict[str, str], str]:
    tool = item.get("tool")
    if not isinstance(tool, str) or tool not in _COLLAB_TOOLS:
        raise TraceError("collab_tool_call.tool is invalid")
    sender = _require_string(
        item.get("sender_thread_id"), field="collab_tool_call.sender_thread_id"
    )
    receivers_value = item.get("receiver_thread_ids")
    if not isinstance(receivers_value, list):
        raise TraceError("collab_tool_call.receiver_thread_ids must be a list")
    receivers = [
        _require_string(value, field="collab_tool_call.receiver_thread_ids[]")
        for value in receivers_value
    ]
    if len(receivers) != len(set(receivers)):
        raise TraceError("collab_tool_call.receiver_thread_ids must be unique")
    prompt = item.get("prompt")
    if prompt is not None and not isinstance(prompt, str):
        raise TraceError("collab_tool_call.prompt must be a string or null")
    states_value = item.get("agents_states")
    if not isinstance(states_value, Mapping):
        raise TraceError("collab_tool_call.agents_states must be an object")
    states: dict[str, str] = {}
    for thread_id, state in states_value.items():
        thread = _require_string(thread_id, field="collab_tool_call.agents_states key")
        if not isinstance(state, str) or state not in _AGENT_STATES:
            raise TraceError("collab_tool_call agent state is invalid")
        states[thread] = state
    status = item.get("status")
    if not isinstance(status, str) or status not in _COLLAB_STATUSES:
        raise TraceError("collab_tool_call.status is invalid")
    if phase == "started" and status != "in_progress":
        raise TraceError("started collab_tool_call must be in_progress")
    if phase == "completed" and status == "in_progress":
        raise TraceError("completed collab_tool_call cannot remain in_progress")
    return tool, sender, receivers, prompt, states, status


def _command_fact(item: Mapping[str, object]) -> CommandFact:
    _validate_command_item(item, phase="completed")
    item_id = _require_string(item.get("id"), field="command_execution.id")
    command = _require_string(item.get("command"), field="command_execution.command")
    output = item["aggregated_output"]
    if not isinstance(output, str):  # Kept explicit for type narrowing at this trust boundary.
        raise TraceError("command_execution.aggregated_output must be a string")
    exit_code = item.get("exit_code")
    if isinstance(exit_code, bool) or (exit_code is not None and not isinstance(exit_code, int)):
        raise TraceError("command_execution.exit_code must be an integer or null")
    status = item.get("status")
    if not isinstance(status, str):
        raise TraceError("command_execution.status must be a string")
    return CommandFact(
        item_sha256=_sha256_text(item_id),
        command_sha256=_sha256_text(command),
        output_sha256=_sha256_text(output),
        output_bytes=len(output.encode("utf-8")),
        exit_code=exit_code,
        status=status,
    )


def _collab_fact(item: Mapping[str, object]) -> CollabToolFact:
    item_id = _require_string(item.get("id"), field="collab_tool_call.id")
    tool, sender, receivers, prompt, states, status = _collab_fields(
        item, phase="completed"
    )
    counts: dict[str, int] = {}
    for state in states.values():
        counts[state] = counts.get(state, 0) + 1
    return CollabToolFact(
        item_sha256=_sha256_text(item_id),
        tool=tool,
        status=status,
        sender_thread_sha256=_sha256_text(sender),
        receiver_thread_sha256s=tuple(_sha256_text(receiver) for receiver in receivers),
        prompt_sha256=_sha256_text(prompt) if prompt is not None else None,
        agent_state_counts=dict(sorted(counts.items())),
    )


def _validate_usage(value: object) -> dict[str, int]:
    if not isinstance(value, Mapping) or set(value) != _USAGE_FIELDS:
        raise TraceError("turn.completed usage does not match the Codex 0.147 schema")
    usage: dict[str, int] = {}
    for field in sorted(_USAGE_FIELDS):
        count = value[field]
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise TraceError(f"turn.completed usage field {field} must be non-negative")
        usage[field] = count
    return usage


def _decode_events(text: str) -> list[dict[str, object]]:
    if not isinstance(text, str):
        raise TraceError("Codex JSONL must be text")
    events: list[dict[str, object]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise TraceError(f"malformed JSONL at line {line_number}") from exc
        if not isinstance(value, dict):
            raise TraceError(f"JSONL line {line_number} must contain an object")
        event_type = value.get("type")
        if not isinstance(event_type, str) or event_type not in _TOP_LEVEL_EVENTS:
            raise TraceError(f"unknown Codex 0.147 event at line {line_number}")
        _reject_credentials(value, location=f"event[{line_number}]")
        events.append(value)
    if not events:
        raise TraceError("Codex JSONL contained no events")
    return events


def _same_item_identity(started: Mapping[str, object], completed: Mapping[str, object]) -> bool:
    return started.get("id") == completed.get("id") and started.get("type") == completed.get("type")


def _validate_completed_matches_started(
    started: Mapping[str, object],
    completed: Mapping[str, object],
) -> None:
    if not _same_item_identity(started, completed):
        raise TraceError("completed item identity does not match its start")
    item_type = completed.get("type")
    if item_type == "command_execution":
        _validate_command_item(started, phase="started")
        if started.get("command") != completed.get("command"):
            raise TraceError("completed command_execution changed its command")
    elif item_type == "collab_tool_call":
        started_fields = _collab_fields(started, phase="started")
        completed_fields = _collab_fields(completed, phase="completed")
        # Agent states and lifecycle status are expected to change; the invocation identity is not.
        if started_fields[:4] != completed_fields[:4]:
            raise TraceError("completed collab_tool_call changed its invocation identity")


def parse_jsonl(text: str, *, process_exit_code: int) -> ParsedTrace:
    """Parse exactly one Codex CLI 0.147 turn and fail closed on ambiguity."""

    if isinstance(process_exit_code, bool) or not isinstance(process_exit_code, int):
        raise TraceError("process exit code must be an integer")
    events = _decode_events(text)
    thread_sha256: str | None = None
    turn_started = False
    terminal: str | None = None
    terminal_error_sha256: str | None = None
    usage: dict[str, int] | None = None
    last_agent_message: str | None = None
    started_items: dict[str, Mapping[str, object]] = {}
    completed_item_ids: set[str] = set()
    command_facts: list[CommandFact] = []
    collab_tool_facts: list[CollabToolFact] = []

    for event_index, event in enumerate(events):
        event_type = event["type"]
        if terminal is not None:
            if event_type in _TERMINAL_EVENTS:
                raise TraceError("trace contains duplicate terminal turn events")
            raise TraceError("trace contains an event after its terminal turn event")

        if event_type == "thread.started":
            if event_index != 0 or thread_sha256 is not None or turn_started:
                raise TraceError("thread.started must be the first and only thread event")
            thread_id = _require_string(event.get("thread_id"), field="thread.started.thread_id")
            thread_sha256 = _sha256_text(thread_id)
            continue

        if event_type == "turn.started":
            if event_index != 1 or thread_sha256 is None or turn_started:
                raise TraceError("turn.started must immediately follow thread.started")
            turn_started = True
            continue

        if thread_sha256 is None or not turn_started:
            raise TraceError(f"{event_type} appeared before thread and turn start")

        if event_type in {"item.started", "item.updated", "item.completed"}:
            item = _require_item(event, event_type=event_type)
            item_id = _require_string(item.get("id"), field=f"{event_type}.item.id")
            item_type = _require_string(item.get("type"), field=f"{event_type}.item.type")
            if item_type not in _ALLOWED_ITEM_TYPES:
                raise TraceError(f"unsupported item type: {item_type}")
            if event_type == "item.started":
                if item_id in started_items or item_id in completed_item_ids:
                    raise TraceError("item.started reused an item id")
                if item_type in _COMPLETION_ONLY_ITEMS:
                    raise TraceError(f"{item_type} must appear only as item.completed")
                if item_type == "command_execution":
                    _validate_command_item(item, phase="started")
                elif item_type == "collab_tool_call":
                    _collab_fields(item, phase="started")
                started_items[item_id] = item
                continue
            if event_type == "item.updated":
                started = started_items.get(item_id)
                if started is None or item_id in completed_item_ids:
                    raise TraceError("item.updated requires one unfinished matching item.start")
                if started.get("type") != item_type:
                    raise TraceError("item.updated changed its item type")
                continue

            if item_id in completed_item_ids:
                raise TraceError("item.completed reused an item id")
            started = started_items.get(item_id)
            if item_type not in _COMPLETION_ONLY_ITEMS:
                if started is None:
                    raise TraceError("item.completed requires one matching item.started")
                _validate_completed_matches_started(started, item)
                del started_items[item_id]
            elif started is not None:
                raise TraceError(f"{item_type} unexpectedly emitted item.started")
            completed_item_ids.add(item_id)
            if item_type == "agent_message":
                last_agent_message = _require_string(
                    item.get("text"), field="agent_message.text"
                )
            elif item_type == "command_execution":
                command_facts.append(_command_fact(item))
            elif item_type == "collab_tool_call":
                collab_tool_facts.append(_collab_fact(item))
            continue

        if event_type == "error":
            _require_string(event.get("message"), field="error.message")
            continue

        if event_type == "turn.completed":
            terminal = "completed"
            usage = _validate_usage(event.get("usage"))
            continue

        if event_type == "turn.failed":
            error = event.get("error")
            if not isinstance(error, Mapping):
                raise TraceError("turn.failed requires an error object")
            message = _require_string(error.get("message"), field="turn.failed.error.message")
            terminal_error_sha256 = _sha256_text(message)
            terminal = "failed"
            continue

        raise TraceError(f"unhandled Codex event type: {event_type}")

    if terminal is None:
        raise TraceError("trace is missing a terminal turn.completed or turn.failed event")
    if started_items:
        raise TraceError("trace ended with unfinished item lifecycles")
    if terminal == "completed" and process_exit_code != 0:
        raise TraceError("turn.completed is inconsistent with a non-zero process exit")
    if terminal == "failed" and process_exit_code == 0:
        raise TraceError("turn.failed is inconsistent with a zero process exit")
    if terminal == "completed" and last_agent_message is None:
        raise TraceError("completed turn emitted no completed agent message")
    if thread_sha256 is None:
        raise TraceError("trace is missing thread.started")

    return ParsedTrace(
        event_count=len(events),
        terminal=terminal,
        thread_sha256=thread_sha256,
        last_agent_message=last_agent_message,
        terminal_error_sha256=terminal_error_sha256,
        usage=usage,
        command_facts=tuple(command_facts),
        collab_tool_facts=tuple(collab_tool_facts),
    )


def _reject_json_constant(value: str) -> object:
    raise ValueError(f"non-standard JSON constant {value!r}")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key {key!r}")
        result[key] = value
    return result


def _decode_hook_receipts(text: str) -> list[dict[str, object]]:
    if not isinstance(text, str):
        raise HookReceiptError("hook receipt JSONL must be text")
    receipts: list[dict[str, object]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(
                line,
                parse_constant=_reject_json_constant,
                object_pairs_hook=_unique_json_object,
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise HookReceiptError(
                f"malformed hook receipt JSONL at line {line_number}"
            ) from exc
        if not isinstance(value, dict):
            raise HookReceiptError(f"hook receipt line {line_number} must be an object")
        event_name = value.get("hook_event_name")
        if not isinstance(event_name, str) or event_name not in _HOOK_EVENTS:
            raise HookReceiptError(f"unknown hook receipt at line {line_number}")
        reject_credentials(value, location=f"hook-receipt[{line_number}]")
        receipts.append(value)
    if not receipts:
        raise HookReceiptError("hook receipt JSONL contained no receipts")
    return receipts


def _hook_string(receipt: Mapping[str, object], field: str, event_name: str) -> str:
    value = receipt.get(field)
    if not isinstance(value, str) or not value:
        raise HookReceiptError(f"{event_name}.{field} must be a non-empty string")
    return value


def _hook_component_name(
    receipt: Mapping[str, object],
    field: str,
    event_name: str,
) -> str:
    value = _hook_string(receipt, field, event_name)
    if not _COMPONENT_NAME_RE.fullmatch(value):
        raise HookReceiptError(
            f"{event_name}.{field} must be a bounded component name, not a path"
        )
    return value


def _validate_hook_common(
    receipt: Mapping[str, object],
    *,
    event_name: str,
) -> tuple[str, str]:
    session_id = _hook_string(receipt, "session_id", event_name)
    _hook_string(receipt, "transcript_path", event_name)
    _hook_string(receipt, "cwd", event_name)
    model = _hook_string(receipt, "model", event_name)
    permission_mode = _hook_string(receipt, "permission_mode", event_name)
    if model != MODEL:
        raise HookReceiptError(
            f"{event_name}.model must be the exact authorized model {MODEL}"
        )
    if permission_mode != SANDBOX_MODE:
        raise HookReceiptError(
            f"{event_name}.permission_mode must be {SANDBOX_MODE}"
        )
    return session_id, model


def _canonical_json_sha256(value: object, *, field: str) -> str:
    try:
        payload = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise HookReceiptError(f"{field} is not canonical JSON data") from exc
    return hashlib.sha256(payload).hexdigest()


def parse_hook_receipts(text: str) -> ParsedHookReceipts:
    """Validate and reduce trusted Codex 0.147 hook receipts without retaining identities."""

    receipts = _decode_hook_receipts(text)
    if receipts[0].get("hook_event_name") != "SessionStart":
        raise HookReceiptError("the first hook receipt must be the one root SessionStart")

    root_session_id: str | None = None
    agent_types_by_id: dict[str, str] = {}
    seen_tool_use_ids: set[str] = set()
    transient_tools: list[TransientToolReceipt] = []
    post_tool_facts: list[PostToolUseFact] = []
    hook_event_counts: dict[str, int] = {}
    model_counts: dict[str, int] = {}
    agent_type_counts: dict[str, int] = {}
    tool_name_counts: dict[str, int] = {}

    for receipt_index, receipt in enumerate(receipts):
        event_name = _hook_string(receipt, "hook_event_name", "hook receipt")
        session_id, model = _validate_hook_common(receipt, event_name=event_name)
        hook_event_counts[event_name] = hook_event_counts.get(event_name, 0) + 1
        model_counts[model] = model_counts.get(model, 0) + 1

        if receipt_index == 0:
            root_session_id = session_id
        elif session_id != root_session_id:
            raise HookReceiptError("hook receipts do not share the root session identity")

        if event_name == "SessionStart":
            if receipt_index != 0 or hook_event_counts[event_name] != 1:
                raise HookReceiptError("hook receipts require exactly one root SessionStart")
            _hook_string(receipt, "source", event_name)
            continue

        if event_name == "SubagentStart":
            _hook_string(receipt, "turn_id", event_name)
            agent_id = _hook_string(receipt, "agent_id", event_name)
            agent_type = _hook_component_name(receipt, "agent_type", event_name)
            if agent_id in agent_types_by_id:
                prior_type = agent_types_by_id[agent_id]
                detail = "conflicting" if prior_type != agent_type else "duplicate"
                raise HookReceiptError(f"{detail} SubagentStart agent identity")
            agent_types_by_id[agent_id] = agent_type
            agent_type_counts[agent_type] = agent_type_counts.get(agent_type, 0) + 1
            continue

        if event_name == "PostToolUse":
            _hook_string(receipt, "turn_id", event_name)
            tool_name = _hook_component_name(receipt, "tool_name", event_name)
            tool_use_id = _hook_string(receipt, "tool_use_id", event_name)
            if tool_use_id in seen_tool_use_ids:
                raise HookReceiptError("duplicate PostToolUse tool identity")
            seen_tool_use_ids.add(tool_use_id)
            if "tool_input" not in receipt:
                raise HookReceiptError("PostToolUse.tool_input is required")
            if "tool_response" not in receipt:
                raise HookReceiptError("PostToolUse.tool_response is required")

            agent_id_value = receipt.get("agent_id")
            agent_type_value = receipt.get("agent_type")
            has_agent_id = agent_id_value is not None
            has_agent_type = agent_type_value is not None
            if has_agent_id != has_agent_type:
                raise HookReceiptError(
                    "PostToolUse agent_id and agent_type must be both present or both absent"
                )
            agent_type: str | None = None
            if has_agent_id:
                agent_id = _hook_string(receipt, "agent_id", event_name)
                agent_type = _hook_component_name(receipt, "agent_type", event_name)
                expected_type = agent_types_by_id.get(agent_id)
                if expected_type is None:
                    raise HookReceiptError(
                        "PostToolUse references an unknown SubagentStart identity"
                    )
                if expected_type != agent_type:
                    raise HookReceiptError(
                        "PostToolUse agent_type conflicts with SubagentStart identity"
                    )

            tool_input = receipt["tool_input"]
            tool_response = receipt["tool_response"]
            transient_tools.append(
                TransientToolReceipt(
                    tool_name=tool_name,
                    agent_type=agent_type,
                    tool_input=tool_input,
                    tool_response=tool_response,
                )
            )
            post_tool_facts.append(
                PostToolUseFact(
                    tool_name=tool_name,
                    agent_type=agent_type,
                    tool_input_sha256=_canonical_json_sha256(
                        tool_input, field="PostToolUse.tool_input"
                    ),
                    tool_response_sha256=_canonical_json_sha256(
                        tool_response, field="PostToolUse.tool_response"
                    ),
                )
            )
            tool_name_counts[tool_name] = tool_name_counts.get(tool_name, 0) + 1
            continue

        raise HookReceiptError(f"unhandled hook receipt event {event_name}")

    if hook_event_counts.get("SessionStart") != 1 or root_session_id is None:
        raise HookReceiptError("hook receipts require exactly one root SessionStart")

    return ParsedHookReceipts(
        receipt_count=len(receipts),
        tool_receipts=tuple(transient_tools),
        post_tool_use_facts=tuple(post_tool_facts),
        hook_event_counts=dict(sorted(hook_event_counts.items())),
        model_counts=dict(sorted(model_counts.items())),
        agent_type_counts=dict(sorted(agent_type_counts.items())),
        tool_name_counts=dict(sorted(tool_name_counts.items())),
    )
