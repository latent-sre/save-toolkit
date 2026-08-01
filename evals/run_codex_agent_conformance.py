#!/usr/bin/env python3
"""Run isolated Codex custom-agent conformance on an explicitly pinned Sol model.

Codex plugin skills and standalone custom-agent TOML are different host surfaces. This runner
installs both into a temporary CODEX_HOME, delegates from a main Sol thread to a named agent, and
requires persisted parent/child runtime evidence. A final answer that merely claims delegation can
never pass.

Raw CLI JSONL and Codex session rollouts are reduced inside the temporary directory to deterministic
facts and hashes. The live runner accepts only the tokenless loopback provider configuration created
by the trusted Linux broker workflow; it never reads or copies ``auth.json`` or an API key.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evals import run_codex_conformance as base  # noqa: E402
from scripts import install_codex_agents as installer  # noqa: E402


DEFAULT_MANIFEST = REPO_ROOT / "evals" / "conformance" / "codex-sol-agents.json"
AGENT_SOURCE_DIRECTORY = Path(".codex/agents")
AGENT_INPUT_PATHS = (
    "agents",
    ".codex/agents",
    "scripts/generate_platform_adapters.py",
    "scripts/install_codex_agents.py",
)
HARNESS_INPUT_PATHS = (
    "evals/run_codex_agent_conformance.py",
    "evals/run_codex_conformance.py",
    "evals/conformance/codex-sol-agents.json",
    "scripts/evidence_envelope.py",
    "schemas/evidence-envelope-v1.schema.json",
)
ERROR_LINE = re.compile(r"(?:^|\s)ERROR(?:\s|:)|\berror=")


@dataclass(frozen=True)
class AgentScore:
    verdict: str
    reason: str
    response: dict[str, object] | None
    observed_models: tuple[str, ...]
    diagnostics: dict[str, object]

    def __post_init__(self) -> None:
        if self.verdict not in base.VERDICTS:
            raise ValueError(f"unknown verdict: {self.verdict}")


def _load_json_object(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise base.ConformanceError(f"cannot load {label} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise base.ConformanceError(f"{label} must be a JSON object")
    return value


def load_manifest(path: Path) -> dict[str, object]:
    manifest = _load_json_object(path, "Codex agent conformance manifest")
    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest: Mapping[str, object]) -> None:
    if set(manifest) != {"schema_version", "description", "plugin", "agents", "lanes"}:
        raise base.ConformanceError("agent manifest has missing or unknown top-level fields")
    if manifest["schema_version"] != 1:
        raise base.ConformanceError("unsupported Codex agent conformance schema version")
    if not isinstance(manifest["description"], str) or not manifest["description"].strip():
        raise base.ConformanceError("agent manifest description must be non-empty")

    plugin = manifest["plugin"]
    if not isinstance(plugin, dict) or set(plugin) != {
        "marketplace",
        "plugin_id",
        "name",
        "version",
    }:
        raise base.ConformanceError("agent plugin contract has missing or unknown fields")
    if any(not isinstance(plugin[field], str) or not plugin[field].strip() for field in plugin):
        raise base.ConformanceError("agent plugin contract fields must be non-empty strings")
    if plugin["plugin_id"] != f'{plugin["name"]}@{plugin["marketplace"]}':
        raise base.ConformanceError("agent plugin_id must be <name>@<marketplace>")

    agents = manifest["agents"]
    if (
        not isinstance(agents, list)
        or not agents
        or not all(isinstance(agent, str) and agent.strip() for agent in agents)
        or len(set(agents)) != len(agents)
        or agents != sorted(agents)
    ):
        raise base.ConformanceError("agents must be a sorted list of unique non-empty names")

    lane_fields = {
        "id",
        "kind",
        "agent",
        "task_name",
        "model",
        "reasoning_effort",
        "sandbox",
        "approval_policy",
        "prompt",
        "expected",
        "child_expected",
        "timeout_seconds",
        "required",
    }
    lanes = manifest["lanes"]
    if not isinstance(lanes, list) or not lanes:
        raise base.ConformanceError("agent manifest must contain at least one lane")
    seen: set[str] = set()
    for lane in lanes:
        if not isinstance(lane, dict) or set(lane) != lane_fields:
            raise base.ConformanceError("each agent lane has missing or unknown fields")
        lane_id = lane["id"]
        if not isinstance(lane_id, str) or not lane_id or lane_id in seen:
            raise base.ConformanceError("agent lane IDs must be unique non-empty strings")
        seen.add(lane_id)
        if lane["kind"] not in {"agent-delegation", "agent-behavior"}:
            raise base.ConformanceError(f"lane {lane_id!r}: unsupported lane kind")
        if lane["agent"] not in agents:
            raise base.ConformanceError(f"lane {lane_id!r}: agent is outside the inventory")
        if not isinstance(lane["task_name"], str) or not re.fullmatch(
            r"[a-z0-9]+(?:_[a-z0-9]+)*", lane["task_name"]
        ):
            raise base.ConformanceError(f"lane {lane_id!r}: invalid task_name")
        if lane["model"] != base.SOL_MODEL:
            raise base.ConformanceError(f"lane {lane_id!r}: model must be {base.SOL_MODEL}")
        if lane["reasoning_effort"] != "high":
            raise base.ConformanceError(f"lane {lane_id!r}: reasoning effort must be high")
        if lane["sandbox"] != "read-only":
            raise base.ConformanceError(f"lane {lane_id!r}: sandbox must be read-only")
        if lane["approval_policy"] != "never":
            raise base.ConformanceError(f"lane {lane_id!r}: approval policy must be never")
        prompt = lane["prompt"]
        if not isinstance(prompt, str) or not prompt.strip() or lane["agent"] not in prompt:
            raise base.ConformanceError(f"lane {lane_id!r}: prompt must name its agent")
        if lane["task_name"] not in prompt:
            raise base.ConformanceError(f"lane {lane_id!r}: prompt must bind its task_name")
        if "no conversation-history fork" not in prompt:
            raise base.ConformanceError(f"lane {lane_id!r}: prompt must require a no-history fork")
        expected = lane["expected"]
        child_expected = lane["child_expected"]
        if not isinstance(expected, dict) or not expected:
            raise base.ConformanceError(f"lane {lane_id!r}: expected must be a non-empty object")
        if not isinstance(child_expected, str) or not child_expected.strip():
            raise base.ConformanceError(f"lane {lane_id!r}: child_expected must be non-empty")
        if child_expected in prompt:
            raise base.ConformanceError(
                f"lane {lane_id!r}: prompt must not disclose the child oracle"
            )
        if expected.get("agent") != lane["agent"] or expected.get("delegated") is not True:
            raise base.ConformanceError(f"lane {lane_id!r}: expected delegation contract is invalid")
        if lane["kind"] == "agent-delegation":
            if set(expected) != {"agent", "delegated", "instruction_canary"}:
                raise base.ConformanceError(
                    f"lane {lane_id!r}: delegation oracle fields are invalid"
                )
            if expected.get("instruction_canary") != child_expected:
                raise base.ConformanceError(f"lane {lane_id!r}: parent and child oracles differ")
        else:
            try:
                child_result = json.loads(child_expected)
            except json.JSONDecodeError as exc:
                raise base.ConformanceError(
                    f"lane {lane_id!r}: behavioral child oracle must be JSON"
                ) from exc
            if not isinstance(child_result, dict) or not child_result:
                raise base.ConformanceError(
                    f"lane {lane_id!r}: behavioral child oracle must be a non-empty object"
                )
            if set(expected) != {"agent", "delegated", "child_result"} or expected.get(
                "child_result"
            ) != child_result:
                raise base.ConformanceError(
                    f"lane {lane_id!r}: behavioral parent and child oracles differ"
                )
        if not isinstance(lane["timeout_seconds"], int) or not 1 <= lane["timeout_seconds"] <= 900:
            raise base.ConformanceError(f"lane {lane_id!r}: timeout must be between 1 and 900")
        if not isinstance(lane["required"], bool):
            raise base.ConformanceError(f"lane {lane_id!r}: required must be boolean")
    if not any(lane["required"] for lane in lanes):
        raise base.ConformanceError("agent manifest must contain at least one required lane")


def _agent_document(path: Path) -> dict[str, object]:
    try:
        value = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise base.ConformanceError(f"cannot load Codex agent {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise base.ConformanceError(f"Codex agent must be a TOML table: {path}")
    return value


def validate_local_contract(root: Path, manifest: Mapping[str, object]) -> None:
    base.validate_local_plugin_contract(
        root,
        {
            "schema_version": 1,
            "description": manifest["description"],
            "plugin": manifest["plugin"],
            "lanes": [
                {
                    "id": "agent-plugin-bootstrap",
                    "kind": "skill-direct",
                    "model": base.SOL_MODEL,
                    "reasoning_effort": "high",
                    "sandbox": "read-only",
                    "approval_policy": "never",
                    "skill": "stack-profile",
                    "prompt": "$stack-profile bootstrap",
                    "expected": {"bootstrap": True},
                    "timeout_seconds": 1,
                    "required": True,
                }
            ],
        },
    )
    if root.resolve() != REPO_ROOT.resolve():
        if base.codex_plugin_digest(root) != base.codex_plugin_digest(REPO_ROOT):
            raise base.ConformanceError(
                "candidate Codex plugin differs from trusted main; "
                "stage plugin prompt changes before live agent conformance"
            )
    source = root / AGENT_SOURCE_DIRECTORY
    base._assert_no_indirection(root, source, "Codex agent source directory")
    actual = sorted(path.stem for path in source.glob("*.toml") if path.is_file())
    if actual != manifest["agents"]:
        raise base.ConformanceError("Codex agent inventory differs from the agent manifest")
    for name in actual:
        path = source / f"{name}.toml"
        base._assert_no_indirection(root, path, f"Codex agent {name!r}")
        if base._is_link_or_reparse(path):
            raise base.ConformanceError(f"Codex agent is linked or reparsed: {path}")
        document = _agent_document(path)
        if set(document) != {"name", "description", "sandbox_mode", "developer_instructions"}:
            raise base.ConformanceError(
                f"Codex agent {name!r} has an active or unknown configuration field"
            )
        if document.get("name") != name:
            raise base.ConformanceError(f"Codex agent {name!r} has a mismatched name")
        if not isinstance(document.get("description"), str) or not document["description"].strip():
            raise base.ConformanceError(f"Codex agent {name!r} has no description")
        if not isinstance(document.get("developer_instructions"), str) or not document[
            "developer_instructions"
        ].strip():
            raise base.ConformanceError(f"Codex agent {name!r} has no developer instructions")
        if document.get("sandbox_mode") not in {"read-only", "workspace-write"}:
            raise base.ConformanceError(f"Codex agent {name!r} has an unsupported sandbox request")
        if root.resolve() != REPO_ROOT.resolve():
            trusted_path = REPO_ROOT / AGENT_SOURCE_DIRECTORY / f"{name}.toml"
            base._assert_no_indirection(REPO_ROOT, trusted_path, f"trusted Codex agent {name!r}")
            if path.read_bytes() != trusted_path.read_bytes():
                raise base.ConformanceError(
                    f"candidate Codex agent {name!r} differs from trusted main; "
                    "stage agent prompt and capability changes before live conformance"
                )
    for lane in manifest["lanes"]:
        if lane["kind"] != "agent-delegation":
            continue
        document = _agent_document(source / f'{lane["agent"]}.toml')
        if lane["child_expected"] not in document["developer_instructions"]:
            raise base.ConformanceError(
                f"lane {lane['id']!r}: child oracle is absent from the agent instructions"
            )


def agent_source_digest(root: Path) -> str:
    return base.directory_digest(root / AGENT_SOURCE_DIRECTORY)


def _git_status(root: Path, paths: Sequence[str]) -> str:
    return base._git_status(root, paths)


def build_exec_command(executable: str, workspace: Path, lane: Mapping[str, object]) -> list[str]:
    return [
        executable,
        "--ask-for-approval",
        lane["approval_policy"],
        "--strict-config",
        "--enable",
        "multi_agent",
        "-c",
        "agents.max_concurrent_threads_per_session=1",
        "-c",
        "agents.max_depth=1",
        "-c",
        "features.multi_agent_v2.max_concurrent_threads_per_session=2",
        *base.rollout_budget_args(),
        "exec",
        "--json",
        "--ignore-rules",
        "--color",
        "never",
        "--model",
        lane["model"],
        "--sandbox",
        lane["sandbox"],
        "-c",
        f'model_reasoning_effort="{lane["reasoning_effort"]}"',
        "--cd",
        str(workspace),
        "--",
        lane["prompt"],
    ]


def _read_rollouts(
    session_root: Path, *, sensitive_values: Sequence[str] = ()
) -> tuple[list[list[dict[str, object]]], str]:
    rollouts: list[list[dict[str, object]]] = []
    digest = hashlib.sha256()
    for path in sorted(session_root.rglob("*.jsonl")) if session_root.is_dir() else []:
        raw = path.read_bytes()
        decoded = raw.decode("utf-8", errors="replace")
        base.assert_no_credential_output(decoded, sensitive_values=sensitive_values)
        digest.update(path.relative_to(session_root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(raw)
        rows: list[dict[str, object]] = []
        for number, line in enumerate(decoded.splitlines(), 1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise base.ConformanceError(f"malformed Codex rollout {path}:{number}") from exc
            if not isinstance(row, dict):
                raise base.ConformanceError(f"non-object Codex rollout row {path}:{number}")
            rows.append(row)
        if rows:
            rollouts.append(rows)
    return rollouts, digest.hexdigest()


def _meta(rows: Sequence[Mapping[str, object]]) -> Mapping[str, object] | None:
    for row in rows:
        if row.get("type") == "session_meta" and isinstance(row.get("payload"), dict):
            return row["payload"]
    return None


def _turn_context(rows: Sequence[Mapping[str, object]]) -> Mapping[str, object] | None:
    for row in rows:
        if row.get("type") == "turn_context" and isinstance(row.get("payload"), dict):
            return row["payload"]
    return None


def _response_items(rows: Sequence[Mapping[str, object]]) -> list[Mapping[str, object]]:
    return [
        row["payload"]
        for row in rows
        if row.get("type") == "response_item" and isinstance(row.get("payload"), dict)
    ]


def _decode_object(value: object) -> dict[str, object] | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _final_messages(items: Sequence[Mapping[str, object]]) -> list[str]:
    messages: list[str] = []
    for item in items:
        if item.get("type") != "message" or item.get("role") != "assistant":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        text = "".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict)
            and part.get("type") == "output_text"
            and isinstance(part.get("text"), str)
        )
        if text and item.get("phase") == "final_answer":
            messages.append(text)
    return messages


def _developer_texts(items: Sequence[Mapping[str, object]]) -> list[str]:
    texts: list[str] = []
    for item in items:
        if item.get("type") != "message" or item.get("role") != "developer":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        texts.extend(
            part["text"]
            for part in content
            if isinstance(part, dict)
            and part.get("type") == "input_text"
            and isinstance(part.get("text"), str)
        )
    return texts


def _context_contract(context: Mapping[str, object] | None, lane: Mapping[str, object]) -> bool:
    if context is None:
        return False
    sandbox = context.get("sandbox_policy")
    mode = context.get("collaboration_mode")
    settings = mode.get("settings") if isinstance(mode, dict) else None
    return bool(
        context.get("model") == lane["model"]
        and context.get("effort") == lane["reasoning_effort"]
        and context.get("approval_policy") == lane["approval_policy"]
        and isinstance(sandbox, dict)
        and sandbox.get("type") == lane["sandbox"]
        and isinstance(settings, dict)
        and settings.get("model") == lane["model"]
        and settings.get("reasoning_effort") == lane["reasoning_effort"]
    )


def score_agent_evidence(
    *,
    stdout_trace: Mapping[str, object],
    rollouts: Sequence[Sequence[Mapping[str, object]]],
    lane: Mapping[str, object],
    expected_instructions: str,
    returncode: int | None,
    stderr: str,
    timed_out: bool,
) -> AgentScore:
    response = base._extract_object(stdout_trace.get("last_message"))
    base_diagnostics: dict[str, object] = {
        "stdout_thread_id_present": isinstance(stdout_trace.get("thread_id"), str),
        "stdout_trace_complete": bool(
            stdout_trace.get("turn_completed_count") == 1
            and stdout_trace.get("malformed_line_count") == 0
            and stdout_trace.get("unfinished_command_count") == 0
        ),
        "rollout_count": len(rollouts),
        "runtime_error_count": sum(bool(ERROR_LINE.search(line)) for line in stderr.splitlines()),
    }
    if timed_out or returncode is None:
        return AgentScore("inconclusive", "Codex agent lane timed out", response, (), base_diagnostics)
    if returncode != 0:
        return AgentScore(
            "inconclusive", f"Codex agent process exited {returncode}", response, (), base_diagnostics
        )
    if not base_diagnostics["stdout_trace_complete"] or not stdout_trace.get("thread_id"):
        return AgentScore(
            "inconclusive", "Codex agent stdout trace is incomplete", response, (), base_diagnostics
        )

    parent_thread_id = stdout_trace["thread_id"]
    parent_candidates = [
        rows
        for rows in rollouts
        if (_meta(rows) or {}).get("session_id") == parent_thread_id
        and (_meta(rows) or {}).get("parent_thread_id") is None
    ]
    if len(parent_candidates) != 1:
        base_diagnostics["parent_rollout_count"] = len(parent_candidates)
        return AgentScore(
            "inconclusive", "could not identify exactly one parent rollout", response, (), base_diagnostics
        )
    parent = parent_candidates[0]
    parent_items = _response_items(parent)
    spawn_calls = [
        item
        for item in parent_items
        if item.get("type") == "function_call" and item.get("name") == "spawn_agent"
    ]
    wait_calls = [
        item
        for item in parent_items
        if item.get("type") == "function_call" and item.get("name") == "wait_agent"
    ]
    wait_ok = False
    if len(wait_calls) == 1 and isinstance(wait_calls[0].get("call_id"), str):
        wait_outputs = [
            _decode_object(item.get("output"))
            for item in parent_items
            if item.get("type") == "function_call_output"
            and item.get("call_id") == wait_calls[0]["call_id"]
        ]
        wait_ok = len(wait_outputs) == 1 and wait_outputs[0] == {
            "message": "Wait completed.",
            "timed_out": False,
        }
    child_delivery_items = [
        item
        for item in parent_items
        if item.get("type") == "agent_message"
        and item.get("author") == f'/root/{lane["task_name"]}'
        and item.get("recipient") == "/root"
    ]
    spawn_ok = False
    spawn_call_id: str | None = None
    spawn_output: dict[str, object] | None = None
    spawn_arguments_matched = False
    if len(spawn_calls) == 1:
        spawn_call_id = spawn_calls[0].get("call_id") if isinstance(
            spawn_calls[0].get("call_id"), str
        ) else None
        arguments = _decode_object(spawn_calls[0].get("arguments"))
        expected_arguments = {
            "agent_type": lane["agent"],
            "fork_turns": "none",
            "task_name": lane["task_name"],
        }
        if arguments is not None and all(
            arguments.get(key) == expected for key, expected in expected_arguments.items()
        ):
            spawn_arguments_matched = True
            outputs = [
                _decode_object(item.get("output"))
                for item in parent_items
                if item.get("type") == "function_call_output"
                and item.get("call_id") == spawn_call_id
            ]
            if len(outputs) == 1:
                spawn_output = outputs[0]
            spawn_ok = spawn_output == {"task_name": f'/root/{lane["task_name"]}'}

    child_candidates = []
    child_metadata_count = 0
    for rows in rollouts:
        metadata = _meta(rows) or {}
        source = metadata.get("source")
        subagent = source.get("subagent") if isinstance(source, dict) else None
        thread_spawn = subagent.get("thread_spawn") if isinstance(subagent, dict) else None
        if metadata.get("parent_thread_id") == parent_thread_id:
            child_metadata_count += 1
        if (
            metadata.get("parent_thread_id") == parent_thread_id
            and metadata.get("agent_role") == lane["agent"]
            and metadata.get("agent_path") == f'/root/{lane["task_name"]}'
            and isinstance(thread_spawn, dict)
            and thread_spawn.get("parent_thread_id") == parent_thread_id
            and thread_spawn.get("agent_role") == lane["agent"]
        ):
            child_candidates.append(rows)

    parent_context = _turn_context(parent)
    child_context = _turn_context(child_candidates[0]) if len(child_candidates) == 1 else None
    parent_contract = _context_contract(parent_context, lane)
    child_contract = _context_contract(child_context, lane)
    child_items = _response_items(child_candidates[0]) if len(child_candidates) == 1 else []
    child_tool_calls = [
        item
        for item in child_items
        if item.get("type") in {"function_call", "custom_tool_call"}
    ]
    developer_texts = _developer_texts(child_items)
    instructions_loaded = expected_instructions in developer_texts
    child_messages = _final_messages(child_items)
    child_response_ok = child_messages == [lane["child_expected"]]
    response_ok = response == lane["expected"]
    observed_models = tuple(
        sorted(
            {
                context["model"]
                for context in (parent_context, child_context)
                if isinstance(context, dict) and isinstance(context.get("model"), str)
            }
        )
    )
    diagnostics = {
        **base_diagnostics,
        "parent_rollout_count": 1,
        "spawn_call_count": len(spawn_calls),
        "spawn_succeeded": spawn_ok,
        "spawn_arguments_matched": spawn_arguments_matched,
        "spawn_output_matched": spawn_output == {"task_name": f'/root/{lane["task_name"]}'},
        "wait_call_count": len(wait_calls),
        "wait_succeeded": wait_ok,
        "parent_child_delivery_count": len(child_delivery_items),
        "child_rollout_count": len(child_candidates),
        "child_metadata_count": child_metadata_count,
        "child_tool_call_count": len(child_tool_calls),
        "parent_runtime_contract_matched": parent_contract,
        "child_runtime_contract_matched": child_contract,
        "agent_instructions_loaded": instructions_loaded,
        "agent_instruction_sha256": hashlib.sha256(
            expected_instructions.encode("utf-8")
        ).hexdigest(),
        "child_response_matched": child_response_ok,
        "parent_oracle_matched": response_ok,
    }
    if all(
        (
            spawn_ok,
            len(child_delivery_items) == 1,
            len(child_candidates) == 1,
            parent_contract,
            child_contract,
            instructions_loaded,
            child_response_ok,
            not child_tool_calls,
            response_ok,
            diagnostics["runtime_error_count"] == 0,
        )
    ):
        return AgentScore(
            "pass",
            "successful named delegation, child profile load, runtime contract, zero child tool calls, and exact oracles verified",
            response,
            observed_models,
            diagnostics,
        )
    return AgentScore(
        "fail",
        "self-reported delegation did not satisfy the structural parent/child agent contract",
        response,
        observed_models,
        diagnostics,
    )


def _install_agents(frozen: Path, target: Path, names: Sequence[str]) -> str:
    plan = installer.build_sync_plan(frozen, target)
    if plan.conflicts or len(plan.writes) != len(names) or plan.removals:
        raise base.ConformanceError("Codex agent installer produced an unexpected synchronization plan")
    installer.apply_sync_plan(plan)
    check = installer.build_sync_plan(frozen, target)
    if check.out_of_sync:
        raise base.ConformanceError("Codex agents are not synchronized after installation")
    installed = sorted(path.stem for path in target.glob("*.toml") if path.is_file())
    if installed != list(names):
        raise base.ConformanceError("installed Codex agent inventory differs from the manifest")
    for name in names:
        source = (frozen / f"{name}.toml").read_bytes()
        if (target / f"{name}.toml").read_bytes() != installer._installed_bytes(source):
            raise base.ConformanceError(f"installed Codex agent bytes differ for {name!r}")
    return base.directory_digest(target)


def run_live(
    root: Path,
    manifest: Mapping[str, object],
    *,
    executable: str,
    broker_config: Path,
    require_clean_plugin: bool,
    require_clean_agents: bool,
    require_clean_harness: bool,
    runner: base.Runner = base._run,
) -> dict[str, object]:
    base.require_brokered_ci_boundary(broker_config)
    if root.resolve() != REPO_ROOT.resolve():
        base.validate_candidate_materialization(root)
    plugin_digest_before = base.codex_plugin_digest(root)
    agent_digest_before = agent_source_digest(root)
    plugin_status = base._plugin_git_status(root)
    agent_status = _git_status(root, AGENT_INPUT_PATHS)
    # The evaluator and installer come from trusted main; the candidate contributes only agent and
    # plugin bytes. Checking candidate HEAD is not a substitute for evaluator independence.
    harness_status = _git_status(REPO_ROOT, HARNESS_INPUT_PATHS)
    if require_clean_plugin and plugin_status:
        raise base.ConformanceError("Codex plugin inputs differ from HEAD; refusing publishable baseline")
    if require_clean_agents and agent_status:
        raise base.ConformanceError("Codex agent inputs differ from HEAD; refusing publishable baseline")
    if require_clean_harness and harness_status:
        raise base.ConformanceError("Codex agent harness differs from HEAD; refusing publishable baseline")

    sensitive_values = base._sensitive_host_values()
    started_at = base._timestamp()
    start = time.monotonic()
    results: list[dict[str, object]] = []
    suite_usage = {key: 0 for key in base.MAX_SUITE_USAGE_TOKENS}
    runner_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    base_runner_sha256 = hashlib.sha256(Path(base.__file__).read_bytes()).hexdigest()

    with tempfile.TemporaryDirectory(prefix="sre-agents-codex-sol-agent-") as temporary:
        temporary_root = Path(temporary)
        if temporary_root.resolve().is_relative_to(root.resolve()):
            raise base.ConformanceError("isolated Codex agent root resolved inside the repository")
        if base._is_link_or_reparse(temporary_root):
            raise base.ConformanceError("isolated Codex agent root must not be linked or reparsed")
        codex_home = temporary_root / "codex-home"
        workspace = temporary_root / "workspace"
        marketplace = temporary_root / "marketplace"
        frozen_agents = temporary_root / "agents-source"
        installed_agents = codex_home / "agents"
        codex_home.mkdir()
        workspace.mkdir()
        os.chmod(codex_home, stat.S_IRWXU)
        broker_config_sha256 = base.stage_broker_config(broker_config, codex_home)
        if (codex_home / "auth.json").exists():
            raise base.ConformanceError("disposable Codex agent home must remain credential-free")
        base.copy_codex_marketplace_snapshot(root, marketplace)
        shutil.copytree(root / AGENT_SOURCE_DIRECTORY, frozen_agents)
        if base.codex_plugin_digest(marketplace) != plugin_digest_before:
            raise base.ConformanceError("frozen Codex plugin digest differs from source")
        if base.directory_digest(frozen_agents) != agent_digest_before:
            raise base.ConformanceError("frozen Codex agent digest differs from source")

        init = subprocess.run(
            ["git", "init", "--quiet", str(workspace)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if init.returncode != 0:
            raise base.ConformanceError(f"cannot initialize neutral agent workspace: {init.stderr[-300:]}")
        if {path.name for path in workspace.iterdir()} != {".git"}:
            raise base.ConformanceError("neutral agent workspace contains unexpected content")
        env = base.scrubbed_child_env(codex_home, temporary_root / "user-profile")
        version, installed_plugin, inventory_digest = base._bootstrap_plugin(
            executable, marketplace, manifest["plugin"], workspace, env, runner
        )
        if base.directory_digest(installed_plugin) != base.directory_digest(
            marketplace / base.PLUGIN_DIRECTORY
        ):
            raise base.ConformanceError("installed Codex plugin differs from its frozen snapshot")
        installed_agent_digest = _install_agents(frozen_agents, installed_agents, manifest["agents"])

        for lane in manifest["lanes"]:
            lane_started = base._timestamp()
            lane_start = time.monotonic()
            agent_path = installed_agents / f'{lane["agent"]}.toml'
            installed_document = _agent_document(agent_path)
            command = build_exec_command(executable, workspace, lane)
            execution = runner(command, workspace, lane["timeout_seconds"], env)
            base.assert_no_credential_output(
                execution.stdout,
                execution.stderr,
                sensitive_values=sensitive_values,
            )
            stdout_trace = base.parse_codex_jsonl(execution.stdout)
            usage_tokens = base.bounded_usage_evidence(stdout_trace["usage"])
            base.add_suite_usage(suite_usage, usage_tokens)
            try:
                rollouts, rollout_digest = _read_rollouts(
                    codex_home / "sessions", sensitive_values=sensitive_values
                )
            except base.CredentialOutputError:
                raise
            except base.ConformanceError as exc:
                score = AgentScore(
                    "inconclusive",
                    str(exc),
                    base._extract_object(stdout_trace.get("last_message")),
                    (),
                    {"rollout_parse_error": True},
                )
                rollout_digest = hashlib.sha256(b"").hexdigest()
            else:
                score = score_agent_evidence(
                    stdout_trace=stdout_trace,
                    rollouts=rollouts,
                    lane=lane,
                    expected_instructions=installed_document["developer_instructions"],
                    returncode=execution.returncode,
                    stderr=execution.stderr,
                    timed_out=execution.timed_out,
                )
            transcript = execution.stdout + execution.stderr
            results.append(
                {
                    "lane_id": lane["id"],
                    "kind": lane["kind"],
                    "verdict": score.verdict,
                    "reason": score.reason,
                    "required": lane["required"],
                    "started_at": lane_started,
                    "ended_at": base._timestamp(),
                    "duration_ms": round((time.monotonic() - lane_start) * 1000),
                    "cli_version": version,
                    "requested_model": lane["model"],
                    "observed_model_count": len(score.observed_models),
                    "observed_model_verified": bool(score.observed_models) and all(
                        model == lane["model"] for model in score.observed_models
                    ),
                    "observed_model_exposed": bool(score.observed_models),
                    "reasoning_effort": lane["reasoning_effort"],
                    "sandbox": lane["sandbox"],
                    "approval_policy": lane["approval_policy"],
                    "prompt_digest": hashlib.sha256(lane["prompt"].encode("utf-8")).hexdigest(),
                    **base.response_evidence(score.response, lane["expected"]),
                    "agent": lane["agent"],
                    "task_name": lane["task_name"],
                    "agent_sha256": hashlib.sha256(agent_path.read_bytes()).hexdigest(),
                    "agent_instruction_sha256": hashlib.sha256(
                        installed_document["developer_instructions"].encode("utf-8")
                    ).hexdigest(),
                    "diagnostics": score.diagnostics,
                    "event_count": stdout_trace["event_count"],
                    "usage_tokens": usage_tokens,
                    "exit_code": execution.returncode,
                    "timed_out": execution.timed_out,
                    "stdout_stderr_digest": hashlib.sha256(transcript.encode("utf-8")).hexdigest(),
                    "rollout_digest": rollout_digest,
                }
            )

    if base.codex_plugin_digest(root) != plugin_digest_before:
        raise base.ConformanceError("Codex plugin inputs changed during the live agent run")
    if agent_source_digest(root) != agent_digest_before:
        raise base.ConformanceError("Codex agent inputs changed during the live agent run")
    summary = {
        verdict: sum(item["verdict"] == verdict for item in results)
        for verdict in sorted(base.VERDICTS)
    }
    report: dict[str, object] = {
        "schema_version": 1,
        "generated_at": base._timestamp(),
        "started_at": started_at,
        "duration_ms": round((time.monotonic() - start) * 1000),
        "repository_commit": base._git_value(root, ["rev-parse", "HEAD"]),
        "evaluator_commit": base._git_value(REPO_ROOT, ["rev-parse", "HEAD"]),
        "plugin_inputs_dirty": bool(plugin_status),
        "agent_inputs_dirty": bool(agent_status),
        "harness_inputs_dirty": bool(harness_status),
        "runner_sha256": runner_sha256,
        "base_runner_sha256": base_runner_sha256,
        "plugin_source_sha256": plugin_digest_before,
        "agent_source_sha256": agent_digest_before,
        "installed_agent_sha256": installed_agent_digest,
        "manifest_sha256": hashlib.sha256(base._canonical_json(manifest)).hexdigest(),
        "plugin_inventory_sha256": inventory_digest,
        "broker_config_sha256": broker_config_sha256,
        "usage_limits": {
            "per_lane": dict(base.MAX_LANE_USAGE_TOKENS),
            "per_suite": dict(base.MAX_SUITE_USAGE_TOKENS),
        },
        "usage_totals": suite_usage,
        "installed_agent_count": len(manifest["agents"]),
        "raw_transcript_persisted": False,
        "auth_boundary": (
            "The trusted Linux workflow holds the API key in a separate Responses API proxy, "
            "removes sudo, and gives this runner only a tokenless loopback provider config."
        ),
        "summary": summary,
        "results": results,
    }
    report["evidence"] = base.build_conformance_evidence(
        report,
        producer="codex_agent_conformance",
        role="codex-agent-conformance",
        target_root=root,
        tree_digest=agent_digest_before,
        criterion="all required Codex/Sol custom-agent delegation lanes pass",
        source_extra={
            "agent_source_sha256": agent_digest_before,
            "installed_agent_sha256": installed_agent_digest,
            "agent_count": len(manifest["agents"]),
        },
    )
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--validate", action="store_true", help="validate fixed local contracts")
    action.add_argument(
        "--run",
        action="store_true",
        help="run live Codex/Sol agent conformance inside the trusted broker workflow",
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--target-root",
        type=Path,
        default=REPO_ROOT,
        help="candidate checkout whose generated agents and plugin bytes are evaluated as data",
    )
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument(
        "--broker-config",
        type=Path,
        help="tokenless config.toml emitted by the trusted Codex Responses API proxy workflow",
    )
    parser.add_argument("--allow-dirty-plugin", action="store_true", help="development only")
    parser.add_argument("--allow-dirty-agents", action="store_true", help="development only")
    parser.add_argument("--allow-dirty-harness", action="store_true", help="development only")
    parser.add_argument("--output", type=Path, help="write the sanitized report JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        manifest = load_manifest(args.manifest)
        target_root = args.target_root.expanduser().resolve()
        if not target_root.is_dir():
            raise base.ConformanceError(f"candidate target root is not a directory: {target_root}")
        validate_local_contract(target_root, manifest)
        plugin_digest = base.codex_plugin_digest(target_root)
        agent_digest = agent_source_digest(target_root)
        if args.validate:
            report: dict[str, object] = {
                "schema_version": 1,
                "manifest": str(args.manifest),
                "manifest_sha256": hashlib.sha256(base._canonical_json(manifest)).hexdigest(),
                "plugin_source_sha256": plugin_digest,
                "agent_source_sha256": agent_digest,
                "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "base_runner_sha256": hashlib.sha256(Path(base.__file__).read_bytes()).hexdigest(),
                "agents": len(manifest["agents"]),
                "lanes": len(manifest["lanes"]),
                "models": sorted({lane["model"] for lane in manifest["lanes"]}),
                "status": "valid",
            }
            exit_code = 0
        else:
            if args.manifest.resolve() != DEFAULT_MANIFEST.resolve():
                raise base.ConformanceError(
                    "live agent runs require the fixed codex-sol-agents.json manifest"
                )
            if args.broker_config is None:
                raise base.ConformanceError(
                    "--run requires --broker-config from the trusted workflow"
                )
            if target_root == REPO_ROOT.resolve():
                raise base.ConformanceError(
                    "live agent runs require a separate candidate checkout; "
                    "the evaluator must come from trusted main"
                )
            executable = shutil.which(args.codex_bin)
            if executable is None:
                raise base.ConformanceError(f"Codex executable is not on PATH: {args.codex_bin}")
            report = run_live(
                target_root,
                manifest,
                executable=executable,
                broker_config=args.broker_config,
                require_clean_plugin=not args.allow_dirty_plugin,
                require_clean_agents=not args.allow_dirty_agents,
                require_clean_harness=not args.allow_dirty_harness,
            )
            required = [item for item in report["results"] if item["required"]]
            if any(item["verdict"] == "fail" for item in required):
                exit_code = 1
            elif any(item["verdict"] == "inconclusive" for item in required):
                exit_code = 2
            else:
                exit_code = 0
        rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8", newline="\n")
        print(rendered, end="")
        return exit_code
    except (base.ConformanceError, OSError, ValueError) as exc:
        print(f"Codex agent conformance error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
