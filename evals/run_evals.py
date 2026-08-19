#!/usr/bin/env python3
"""Validate or run direct-contract and autonomous-discovery fleet evals.

Direct scenarios pin a namespaced skill or agent and grade its behavioral contract. Discovery
scenarios pass the authored prompt byte-for-byte and require completed stream-json invocation
evidence. Live runs execute in a neutral, credential-scrubbed workspace and persist private traces.
"""
from __future__ import annotations

import argparse
import contextlib
import functools
import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

EVAL_ROOT = Path(__file__).resolve().parent
EVAL_BUNDLE_ROOT = EVAL_ROOT.parent
TRUSTED_FRONTMATTER_PATH = EVAL_BUNDLE_ROOT / "scripts/fleet_frontmatter.py"

import clean_room
import graders

try:
    import yaml
except ModuleNotFoundError:
    sys.exit("evals: PyYAML required -- `python -m pip install -r requirements-dev.txt`")


ROOT = Path(os.environ.get("FLEET_ROOT") or EVAL_BUNDLE_ROOT).resolve()
SCENARIOS_DIR = EVAL_ROOT / "scenarios"
EVAL_SNAPSHOT_ROOT_ENV = "FLEET_EVAL_SNAPSHOT_ROOT"
EVAL_INPUT_PATHS = ("run_evals.py", "graders.py", "clean_room.py", "scenarios")
EVAL_SUPPORT_INPUT_PATHS = ("scripts/fleet_frontmatter.py",)
SCHEMA_VERSION = 1
MODES = {"direct", "discovery"}
SPLITS = {"calibration", "regression"}
TARGET_KINDS = {"skill", "agent"}
ROUTING_EXPECTATIONS = {"fire", "not_fire"}
DEFAULT_TRIALS = 3
DEFAULT_THRESHOLD = 1.0
ALLOWED_BUILTIN_TOOLS = ("Skill", "Task")
DENIED_TOOLS = (
    "Bash,Edit,Write,NotebookEdit,Read,Glob,Grep,WebFetch,WebSearch,ToolSearch,"
    "CronCreate,CronDelete,DesignSync,EnterWorktree,ExitWorktree,PushNotification,"
    "RemoteTrigger,ScheduleWakeup,Workflow,TaskCreate,TaskUpdate,TaskStop,Monitor"
)
SAFE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PLUGIN_INPUT_PATHS = (
    "agents", "skills", "commands", "hooks", ".claude-plugin/plugin.json",
    "scripts/fleet_frontmatter.py",
    "scripts/readonly-guard.py", "scripts/readonly-guard-hook.sh",
)
REQUIRED = (
    "schema_version", "id", "mode", "split", "target", "prompt", "success_criteria", "graders",
)
ALLOWED_SCENARIO_KEYS = set(REQUIRED) | {
    "routing", "trials", "threshold", "_file", "_source_sha256", "_yaml_error",
}
ALLOWED_TARGET_KEYS = {"kind", "name"}
ALLOWED_ROUTING_KEYS = {"expect", "scope", "also_acceptable", "expected_alternative"}


def positive_trials(value: str) -> int:
    trials = int(value)
    if trials < 2:
        raise argparse.ArgumentTypeError(f"must be >= 2, got {trials}")
    return trials


def bounded_threshold(value: str) -> float:
    threshold = float(value)
    if not 0 < threshold <= 1:
        raise argparse.ArgumentTypeError(f"must be > 0 and <= 1, got {threshold}")
    return threshold


def plugin_manifest(root: Path = ROOT) -> dict:
    return json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))


def plugin_name(root: Path = ROOT) -> str:
    return str(plugin_manifest(root)["name"])


def is_frozen_eval_process() -> bool:
    """Require the bootstrap's exact external snapshot path; a boolean env marker is forgeable."""
    claimed = os.environ.get(EVAL_SNAPSHOT_ROOT_ENV)
    if not claimed:
        return False
    try:
        return Path(claimed).resolve() == EVAL_ROOT and not EVAL_ROOT.is_relative_to(ROOT)
    except OSError:
        return False


def load_scenarios() -> list[dict]:
    scenarios: list[dict] = []
    for path in sorted(SCENARIOS_DIR.glob("*.yaml")):
        source = path.read_bytes()
        try:
            data = yaml.safe_load(source.decode("utf-8")) or {}
        except (UnicodeDecodeError, yaml.YAMLError) as exc:
            data = {"_yaml_error": str(exc)}
        if not isinstance(data, dict):
            data = {"_yaml_error": f"expected mapping, got {type(data).__name__}"}
        data["_file"] = path.name
        data["_source_sha256"] = hashlib.sha256(source).hexdigest()
        scenarios.append(data)
    return scenarios


def load_stable_suite() -> tuple[list[dict], str]:
    """Bind in-memory scenario objects to one stable suite digest."""
    before = eval_suite_digest()
    scenarios = load_scenarios()
    after = eval_suite_digest()
    if before != after:
        raise clean_room.RunnerFailed("eval harness or scenarios changed while the suite was loaded")
    for scenario in scenarios:
        path = SCENARIOS_DIR / scenario["_file"]
        if scenario["_source_sha256"] != _sha256_file(path):
            raise clean_room.RunnerFailed(f"scenario changed while it was loaded: {path}")
    return scenarios, after


def _target_error(target: object) -> str | None:
    if not isinstance(target, dict):
        return "must be a mapping with kind/name"
    unknown = set(target) - ALLOWED_TARGET_KEYS
    if unknown:
        return f"has unknown key(s): {', '.join(sorted(unknown))}"
    if target.get("kind") not in TARGET_KINDS:
        return "kind must be 'skill' or 'agent'"
    if not isinstance(target.get("name"), str) or not target["name"].strip():
        return "name must be a non-empty string"
    if not SAFE_ID_RE.fullmatch(target["name"]):
        return "name must be a canonical lowercase slug"
    return None


def target_exists(target: dict) -> bool:
    name = target["name"]
    if target["kind"] == "skill":
        return (ROOT / "skills" / name / "SKILL.md").is_file()
    return (ROOT / "agents" / f"{name}.md").is_file()


def qualified_target(target: dict, root: Path = ROOT) -> str:
    return f"{plugin_name(root)}:{target['name']}"


def _prompt_names_target(prompt: str, target: dict) -> bool:
    name = re.escape(target["name"])
    namespace = re.escape(plugin_name())
    pattern = rf"(?<![a-z0-9-])(?:/{namespace}:|@agent-{namespace}:|{namespace}:)?{name}(?![a-z0-9-])"
    return re.search(pattern, prompt, re.IGNORECASE) is not None


def validate(scenarios: list[dict]) -> list[str]:
    problems: list[str] = []
    seen: set[str] = set()
    for scenario in scenarios:
        where = scenario.get("_file", "?")
        if scenario.get("_yaml_error"):
            problems.append(f"{where}: YAML parse error: {scenario['_yaml_error']}")
        unknown = set(scenario) - ALLOWED_SCENARIO_KEYS
        if unknown:
            problems.append(f"{where}: unknown key(s): {', '.join(sorted(unknown))}")
        for key in REQUIRED:
            if key not in scenario or scenario.get(key) in (None, ""):
                problems.append(f"{where}: missing '{key}'")

        if scenario.get("schema_version") != SCHEMA_VERSION:
            problems.append(f"{where}: schema_version must be {SCHEMA_VERSION}")
        sid = scenario.get("id")
        if sid:
            if not isinstance(sid, str):
                problems.append(f"{where}: id must be a string")
            elif not SAFE_ID_RE.fullmatch(sid):
                problems.append(f"{where}: id must be a safe lowercase slug (letters, digits, single hyphens)")
            elif sid in seen:
                problems.append(f"{where}: duplicate id '{sid}'")
            else:
                seen.add(sid)
        if scenario.get("mode") not in MODES:
            problems.append(f"{where}: mode must be one of {sorted(MODES)}")
        if scenario.get("split") not in SPLITS:
            problems.append(f"{where}: split must be one of {sorted(SPLITS)}")

        target = scenario.get("target")
        target_problem = _target_error(target)
        if target_problem:
            problems.append(f"{where}: target {target_problem}")
        elif not target_exists(target):
            problems.append(
                f"{where}: target '{target['kind']}:{target['name']}' is not a known component"
            )

        prompt = scenario.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            problems.append(f"{where}: prompt must be a non-empty string")
        criteria = scenario.get("success_criteria")
        if not isinstance(criteria, list) or not criteria or not all(isinstance(x, str) and x.strip() for x in criteria):
            problems.append(f"{where}: success_criteria must be a non-empty list of strings")

        scenario_trials = scenario.get("trials", DEFAULT_TRIALS)
        if isinstance(scenario_trials, bool) or not isinstance(scenario_trials, int) or scenario_trials < 2:
            problems.append(f"{where}: trials must be an integer >= 2")
        scenario_threshold = scenario.get("threshold", DEFAULT_THRESHOLD)
        if isinstance(scenario_threshold, bool) or not isinstance(scenario_threshold, (int, float)) or not 0 < scenario_threshold <= 1:
            problems.append(f"{where}: threshold must be > 0 and <= 1")

        grader_specs = scenario.get("graders")
        if not isinstance(grader_specs, list) or not grader_specs:
            problems.append(f"{where}: graders must be a non-empty list")
        else:
            for grader in grader_specs:
                if not isinstance(grader, dict):
                    problems.append(f"{where}: each grader must be a mapping")
                    continue
                if grader.get("type") not in graders.REGISTRY:
                    problems.append(f"{where}: unknown grader type '{grader.get('type')}'")
                    continue
                try:
                    graders.run_grader(grader, "")
                except TypeError as exc:
                    problems.append(f"{where}: grader '{grader.get('type')}' has bad/missing kwargs: {exc}")
                except re.error as exc:
                    problems.append(f"{where}: grader '{grader.get('type')}' has an invalid regex: {exc}")

        mode = scenario.get("mode")
        routing = scenario.get("routing")
        if mode == "direct" and routing is not None:
            problems.append(f"{where}: direct scenarios must not define routing")
        if mode == "discovery":
            if not isinstance(routing, dict) or routing.get("expect") not in ROUTING_EXPECTATIONS:
                problems.append(f"{where}: discovery scenarios require routing.expect fire|not_fire")
            else:
                routing_unknown = set(routing) - ALLOWED_ROUTING_KEYS
                if routing_unknown:
                    problems.append(f"{where}: routing has unknown key(s): {', '.join(sorted(routing_unknown))}")
                scope = routing.get("scope")
                if scope is not None:
                    if scope != "root":
                        problems.append(f"{where}: routing.scope must be 'root'")
                    elif routing["expect"] != "not_fire":
                        problems.append(f"{where}: routing.scope is only valid for not_fire")
                alternatives = routing.get("also_acceptable", [])
                if not isinstance(alternatives, list):
                    problems.append(f"{where}: routing.also_acceptable must be a list")
                else:
                    for alt in alternatives:
                        alt_problem = _target_error(alt)
                        if alt_problem or not target_exists(alt):
                            problems.append(f"{where}: invalid routing.also_acceptable target {alt!r}")
                expected_alt = routing.get("expected_alternative")
                if routing["expect"] == "not_fire" and expected_alt is None:
                    problems.append(f"{where}: routing.expect not_fire requires expected_alternative")
                if scope == "root" and expected_alt == "inline":
                    problems.append(
                        f"{where}: routing.scope root requires a component expected_alternative"
                    )
                if (
                    routing["expect"] == "not_fire"
                    and "threshold" in scenario
                    and isinstance(scenario_threshold, (int, float))
                    and not isinstance(scenario_threshold, bool)
                    and scenario_threshold < 1
                ):
                    problems.append(
                        f"{where}: not_fire scenarios are zero-tolerance; threshold must be 1 "
                        "(it applies to positives only)"
                    )
                if expected_alt is not None and expected_alt != "inline":
                    alt_problem = _target_error(expected_alt)
                    if alt_problem or not target_exists(expected_alt):
                        problems.append(f"{where}: invalid routing.expected_alternative {expected_alt!r}")
            if not target_problem and isinstance(prompt, str) and _prompt_names_target(prompt, target):
                problems.append(f"{where}: discovery prompt names its target; it must be byte-for-byte unhinted")

    if scenarios and not any(s.get("mode") == "discovery" for s in scenarios):
        problems.append("suite: at least one discovery scenario is required")
    if scenarios and not any(s.get("split") == "regression" for s in scenarios):
        problems.append("suite: at least one visible regression scenario is required")
    return problems


@dataclass(frozen=True)
class StreamDiagnostics:
    init_count: int
    result_count: int
    continuation_count: int
    same_session: bool | None
    root_result_count: int
    parented_result_count: int
    intermediate_root_results: tuple[dict, ...]

    def to_summary(self) -> dict:
        return {
            "init_count": self.init_count,
            "result_count": self.result_count,
            "continuation_count": self.continuation_count,
            "same_session": self.same_session,
            "root_result_count": self.root_result_count,
            "parented_result_count": self.parented_result_count,
            "intermediate_root_results": [dict(item) for item in self.intermediate_root_results],
        }


class StreamTraceFailed(clean_room.RunnerFailed):
    def __init__(self, message: str, diagnostics: StreamDiagnostics):
        super().__init__(message)
        self.stream_diagnostics = diagnostics.to_summary()


class StreamAuthUnavailable(clean_room.AuthUnavailable):
    def __init__(self, message: str, diagnostics: StreamDiagnostics):
        super().__init__(message)
        self.stream_diagnostics = diagnostics.to_summary()


@dataclass(frozen=True)
class NestedComponentOwnership:
    kind: str
    name: str
    root_agent: str | None


@dataclass(frozen=True)
class ParsedTrace:
    response: str
    skills: tuple[str, ...]
    agents: tuple[str, ...]
    root_skills: tuple[str, ...]
    root_agents: tuple[str, ...]
    nested_ownership: tuple[NestedComponentOwnership, ...]
    attempted_skills: tuple[str, ...]
    attempted_agents: tuple[str, ...]
    model: str | None
    session_id: str | None
    total_cost_usd: float | None
    runtime_plugins: tuple[dict, ...]
    mcp_servers: tuple[dict, ...]
    available_skills: tuple[str, ...]
    available_agents: tuple[str, ...]
    available_tools: tuple[str, ...]
    stream_diagnostics: StreamDiagnostics


def _walk(value: object):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _dedupe(values: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _is_canonical_component_identity(value: str) -> bool:
    namespace, separator, name = value.partition(":")
    return bool(
        separator
        and ":" not in name
        and SAFE_ID_RE.fullmatch(namespace)
        and SAFE_ID_RE.fullmatch(name)
    )


def _tool_result_succeeded(node: dict) -> bool:
    if node.get("is_error") is True:
        return False
    statuses = [node.get("status")]
    content = node.get("content")
    if isinstance(content, dict):
        statuses.append(content.get("status"))
    return all(status in (None, "completed", "success", "succeeded") for status in statuses)


def _decode_stream_events(blob: str) -> list[dict]:
    events: list[dict] = []
    for line_number, line in enumerate(blob.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise clean_room.RunnerFailed(f"malformed stream-json at line {line_number}: {exc}") from exc
        if not isinstance(event, dict):
            raise clean_room.RunnerFailed(f"stream-json line {line_number} is not an object")
        events.append(event)
    return events


def _result_origin_kind(event: dict) -> str | None:
    origin = event.get("origin")
    return origin.get("kind") if isinstance(origin, dict) and isinstance(origin.get("kind"), str) else None


def _stream_diagnostics(events: list[dict]) -> StreamDiagnostics:
    init_events = [
        event for event in events
        if event.get("type") == "system"
        and event.get("subtype") == "init"
        and event.get("parent_tool_use_id") is None
    ]
    results = [event for event in events if event.get("type") == "result"]
    root_results = [event for event in results if event.get("parent_tool_use_id") is None]
    session_ids = {
        event["session_id"] for event in events
        if isinstance(event.get("session_id"), str) and event["session_id"]
    }
    intermediate = tuple(
        {
            "ordinal": ordinal,
            "subtype": (
                "success" if event.get("subtype") == "success"
                else "error" if event.get("is_error") is True
                else "unknown"
            ),
            "is_error": event.get("is_error") is True,
            "origin": (
                None if event.get("origin") is None
                else "task-notification" if _result_origin_kind(event) == "task-notification"
                else "unknown"
            ),
        }
        for ordinal, event in enumerate(root_results[:-1], start=1)
    )
    return StreamDiagnostics(
        init_count=len(init_events),
        result_count=len(results),
        continuation_count=sum(
            _result_origin_kind(event) == "task-notification" for event in root_results
        ),
        same_session=None if not session_ids else len(session_ids) == 1,
        root_result_count=len(root_results),
        parented_result_count=len(results) - len(root_results),
        intermediate_root_results=intermediate,
    )


def _safe_stream_diagnostics(blob: str) -> dict | None:
    try:
        events = _decode_stream_events(blob)
    except clean_room.RunnerFailed:
        return None
    return _stream_diagnostics(events).to_summary()


def _fail_stream(message: str, diagnostics: StreamDiagnostics) -> None:
    raise StreamTraceFailed(message, diagnostics)


def _init_runtime_metadata(event: dict) -> dict:
    def records(key: str, fields: tuple[str, ...]) -> tuple[dict, ...]:
        values = (
            {field: item.get(field) for field in fields if item.get(field) is not None}
            for item in event.get(key, []) if isinstance(item, dict)
        )
        return tuple(sorted(values, key=lambda value: json.dumps(value, sort_keys=True)))

    def strings(key: str) -> tuple[str, ...]:
        return tuple(sorted(value for value in event.get(key, []) if isinstance(value, str)))

    return {
        "model": event.get("model") if isinstance(event.get("model"), str) else None,
        "runtime_plugins": records("plugins", ("name", "source", "version", "path")),
        "mcp_servers": records("mcp_servers", ("name", "status")),
        "available_skills": strings("skills"),
        "available_agents": strings("agents"),
        "available_tools": strings("tools"),
    }


def parse_stream_trace(blob: str) -> ParsedTrace:
    events = _decode_stream_events(blob)
    diagnostics = _stream_diagnostics(events)

    for event in events:
        parent = event.get("parent_tool_use_id")
        if parent is not None and not isinstance(parent, str):
            _fail_stream("stream event has a non-string parent_tool_use_id", diagnostics)

    session_ids = _dedupe([
        event["session_id"] for event in events
        if isinstance(event.get("session_id"), str) and event["session_id"]
    ])
    if len(session_ids) > 1:
        _fail_stream(f"mixed session stream-json contains {len(session_ids)} session IDs", diagnostics)

    root_inits = [
        (index, event) for index, event in enumerate(events)
        if event.get("type") == "system"
        and event.get("subtype") == "init"
        and event.get("parent_tool_use_id") is None
    ]
    root_results = [
        (index, event) for index, event in enumerate(events)
        if event.get("type") == "result" and event.get("parent_tool_use_id") is None
    ]
    if not root_results:
        _fail_stream("expected a completed root result event, found 0", diagnostics)
    if root_inits and root_results[0][0] < root_inits[0][0]:
        _fail_stream("root result appeared before the first init event", diagnostics)

    for ordinal, (_, result_event) in enumerate(root_results, start=1):
        subtype = result_event.get("subtype")
        if result_event.get("is_error") is not False or subtype != "success":
            if any(marker in json.dumps(result_event) for marker in clean_room.AUTH_MARKERS):
                raise StreamAuthUnavailable(
                    f"Claude root result {ordinal} reports authentication failure", diagnostics
                )
            _fail_stream(f"root result {ordinal} reports an error", diagnostics)

    if root_inits:
        if len(root_inits) > len(root_results):
            _fail_stream(
                f"unfinished root epoch: {len(root_inits)} init events but only "
                f"{len(root_results)} completed root results",
                diagnostics,
            )
        if len(root_inits) < len(root_results):
            _fail_stream(
                f"root result count exceeds initialized epochs: {len(root_results)} results for "
                f"{len(root_inits)} init events",
                diagnostics,
            )
        if root_inits[-1][0] > root_results[-1][0]:
            _fail_stream("unfinished root epoch: stream ended after an init event", diagnostics)
    elif len(root_results) != 1:
        _fail_stream("multiple root results require explicit init epochs", diagnostics)

    origin_kinds = [_result_origin_kind(result_event) for _, result_event in root_results]
    if root_results[0][1].get("origin") is not None:
        _fail_stream("initial root result has an unexpected continuation origin", diagnostics)
    if any(origin != "task-notification" for origin in origin_kinds[1:]):
        _fail_stream("continuation root result lacks task-notification origin", diagnostics)

    if len(root_results) > 1:
        if diagnostics.same_session is not True or not session_ids:
            _fail_stream("continuation epochs do not prove one non-empty same session", diagnostics)
        canonical_session = session_ids[0]
        for _, event in (*root_inits, *root_results):
            if event.get("session_id") != canonical_session:
                _fail_stream("continuation epoch is missing the canonical session ID", diagnostics)
        for (previous_index, _), (init_index, _) in zip(root_inits, root_inits[1:]):
            completed_notification = any(
                event.get("type") == "system"
                and event.get("subtype") == "task_notification"
                and event.get("parent_tool_use_id") is None
                and event.get("status") == "completed"
                and event.get("session_id") == canonical_session
                for event in events[previous_index + 1:init_index]
            )
            if not completed_notification:
                _fail_stream(
                    "continuation init lacks preceding completed task_notification evidence",
                    diagnostics,
                )

    init_metadata = [_init_runtime_metadata(event) for _, event in root_inits]
    if init_metadata and any(metadata != init_metadata[0] for metadata in init_metadata[1:]):
        _fail_stream("continuation init changed runtime metadata", diagnostics)

    result = root_results[-1][1]

    pending: dict[tuple[int, str | None, str], tuple[str, str]] = {}
    successful_ids: set[tuple[int, str | None, str]] = set()
    attempted_skills: list[str] = []
    attempted_agents: list[str] = []
    epoch = 0
    saw_init = False
    for event in events:
        if (
            event.get("type") == "system"
            and event.get("subtype") == "init"
            and event.get("parent_tool_use_id") is None
        ):
            if saw_init:
                epoch += 1
            saw_init = True
        parent = event.get("parent_tool_use_id")
        for node in _walk(event):
            if node.get("type") == "tool_use" and isinstance(node.get("id"), str):
                tool_input = node.get("input") if isinstance(node.get("input"), dict) else {}
                if node.get("name") == "Skill" and isinstance(tool_input.get("skill"), str):
                    call_key = (epoch, parent, node["id"])
                    if call_key in pending:
                        _fail_stream("duplicate component tool_use within one epoch and parent", diagnostics)
                    pending[call_key] = ("skill", tool_input["skill"])
                    attempted_skills.append(tool_input["skill"])
                elif node.get("name") in ("Task", "Agent") and isinstance(tool_input.get("subagent_type"), str):
                    call_key = (epoch, parent, node["id"])
                    if call_key in pending:
                        _fail_stream("duplicate component tool_use within one epoch and parent", diagnostics)
                    pending[call_key] = ("agent", tool_input["subagent_type"])
                    attempted_agents.append(tool_input["subagent_type"])
            elif node.get("type") == "tool_result" and isinstance(node.get("tool_use_id"), str):
                if _tool_result_succeeded(node):
                    successful_ids.add((epoch, parent, node["tool_use_id"]))

    completed = {
        call_key: component
        for call_key, component in pending.items()
        if call_key in successful_ids
    }
    skills = [name for kind, name in completed.values() if kind == "skill"]
    agents = [name for kind, name in completed.values() if kind == "agent"]
    root_skills = [
        name for call_key, (kind, name) in completed.items()
        if kind == "skill" and call_key[1] is None
    ]
    root_agents = [
        name for call_key, (kind, name) in completed.items()
        if kind == "agent" and call_key[1] is None
    ]

    calls_by_epoch_and_id: dict[tuple[int, str], list[tuple[int, str | None, str]]] = {}
    for call_key in pending:
        calls_by_epoch_and_id.setdefault((call_key[0], call_key[2]), []).append(call_key)

    def root_agent_owner(call_key: tuple[int, str | None, str]) -> str | None:
        epoch_number, parent_id, _ = call_key
        seen: set[tuple[int, str | None, str]] = set()
        while parent_id is not None:
            candidates = calls_by_epoch_and_id.get((epoch_number, parent_id), [])
            if len(candidates) != 1:
                return None
            parent_key = candidates[0]
            if parent_key in seen or parent_key not in completed:
                return None
            seen.add(parent_key)
            parent_kind, parent_name = completed[parent_key]
            if parent_kind != "agent":
                return None
            if parent_key[1] is None:
                return parent_name if _is_canonical_component_identity(parent_name) else None
            parent_id = parent_key[1]
        return None

    nested_ownership = tuple(
        NestedComponentOwnership(kind, name, root_agent_owner(call_key))
        for call_key, (kind, name) in completed.items()
        if call_key[1] is not None and _is_canonical_component_identity(name)
    )
    response = result.get("result", "")
    if not isinstance(response, str):
        response = json.dumps(response, ensure_ascii=False)
    cost = result.get("total_cost_usd")
    metadata = init_metadata[0] if init_metadata else _init_runtime_metadata({})
    return ParsedTrace(
        response=response,
        skills=_dedupe(skills),
        agents=_dedupe(agents),
        root_skills=_dedupe([name for name in root_skills if _is_canonical_component_identity(name)]),
        root_agents=_dedupe([name for name in root_agents if _is_canonical_component_identity(name)]),
        nested_ownership=nested_ownership,
        attempted_skills=_dedupe(attempted_skills),
        attempted_agents=_dedupe(attempted_agents),
        model=metadata["model"],
        session_id=session_ids[0] if session_ids else None,
        total_cost_usd=float(cost) if isinstance(cost, (int, float)) else None,
        runtime_plugins=metadata["runtime_plugins"],
        mcp_servers=metadata["mcp_servers"],
        available_skills=metadata["available_skills"],
        available_agents=metadata["available_agents"],
        available_tools=metadata["available_tools"],
        stream_diagnostics=diagnostics,
    )


def _split_tool_specs(raw: object) -> list[str]:
    if isinstance(raw, list):
        return [item.strip() for item in raw if isinstance(item, str) and item.strip()]
    if not isinstance(raw, str):
        return []
    specs: list[str] = []
    current: list[str] = []
    depth = 0
    for char in raw:
        if char == "(":
            depth += 1
        elif char == ")" and depth:
            depth -= 1
        if char == "," and depth == 0:
            spec = "".join(current).strip()
            if spec:
                specs.append(spec)
            current = []
        else:
            current.append(char)
    spec = "".join(current).strip()
    if spec:
        specs.append(spec)
    return specs


def _require_matching_frontmatter_parser(plugin_root: Path) -> None:
    """Treat the measured parser as data and reject grammar drift from the trusted harness."""
    measured_path = plugin_root / "scripts/fleet_frontmatter.py"
    try:
        for label, path in (
            ("measured plugin", measured_path),
            ("trusted eval harness", TRUSTED_FRONTMATTER_PATH),
        ):
            if not path.is_file() or _is_reparse_point(path):
                raise ValueError(f"{label} frontmatter parser must be an ordinary file")
        if measured_path.read_bytes() != TRUSTED_FRONTMATTER_PATH.read_bytes():
            raise ValueError(
                "measured plugin frontmatter parser differs from the trusted eval harness"
            )
    except (OSError, ValueError) as exc:
        raise clean_room.RunnerFailed(f"cannot verify shared frontmatter parser: {exc}") from exc


@functools.lru_cache(maxsize=1)
def _load_trusted_frontmatter_parser() -> ModuleType:
    """Load only the parser bound into the frozen evaluator bundle."""
    try:
        if not TRUSTED_FRONTMATTER_PATH.is_file() or _is_reparse_point(TRUSTED_FRONTMATTER_PATH):
            raise ValueError("trusted eval harness frontmatter parser must be an ordinary file")
        module_name = "_trusted_fleet_frontmatter_" + hashlib.sha256(
            str(TRUSTED_FRONTMATTER_PATH.resolve()).encode("utf-8")
        ).hexdigest()[:16]
        spec = importlib.util.spec_from_file_location(module_name, TRUSTED_FRONTMATTER_PATH)
        if spec is None or spec.loader is None:
            raise ValueError("could not create trusted frontmatter parser import spec")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except (OSError, UnicodeError, ImportError, ValueError) as exc:
        raise clean_room.RunnerFailed(f"cannot load trusted frontmatter parser: {exc}") from exc


def expected_runtime_tools(scenario: dict, plugin_root: Path = ROOT) -> tuple[str, ...]:
    """Return the exact effective built-in ceiling for this invocation plan."""
    _require_matching_frontmatter_parser(plugin_root)
    frontmatter_parser = _load_trusted_frontmatter_parser()
    target = scenario["target"]
    if scenario["mode"] != "direct" or target["kind"] != "agent":
        return ALLOWED_BUILTIN_TOOLS
    path = plugin_root / "agents" / f"{target['name']}.md"
    try:
        fields = frontmatter_parser.parse_file(path, mode="strict").fields
        if "tools" not in fields:
            raise ValueError("frontmatter must contain an explicit tools field")
    except (OSError, UnicodeError, ValueError) as exc:
        raise clean_room.RunnerFailed(f"cannot derive direct-agent tool boundary from {path}: {exc}") from exc
    bases = {spec.split("(", 1)[0].strip() for spec in _split_tool_specs(fields.get("tools"))}
    effective = []
    if "Skill" in bases:
        effective.append("Skill")
    if "Agent" in bases:
        effective.append("Task")
    return tuple(effective)


def enforce_runtime_boundary(
    parsed: ParsedTrace,
    expected_plugin_root: Path = ROOT,
    *,
    expected_tools: tuple[str, ...] = ALLOWED_BUILTIN_TOOLS,
) -> None:
    """Refuse a measurement if the CLI did not honor the requested namespace/tool boundary."""
    observed_tools = set(parsed.available_tools)
    if observed_tools != set(expected_tools):
        raise clean_room.RunnerFailed(
            f"runtime tool boundary mismatch: expected exactly {sorted(expected_tools)}, "
            f"observed {sorted(parsed.available_tools)}"
        )
    if parsed.mcp_servers:
        raise clean_room.RunnerFailed(f"strict empty MCP boundary violated: observed {list(parsed.mcp_servers)}")
    expected_plugin_root = expected_plugin_root.resolve()
    manifest = plugin_manifest(expected_plugin_root)
    if len(parsed.runtime_plugins) != 1:
        raise clean_room.RunnerFailed(
            f"runtime plugin boundary mismatch: expected exactly one plugin, observed {list(parsed.runtime_plugins)}"
        )
    runtime_plugin = parsed.runtime_plugins[0]
    observed_path = runtime_plugin.get("path")
    path_matches = isinstance(observed_path, str) and Path(observed_path).resolve() == expected_plugin_root
    expected = {
        "name": manifest["name"],
        "version": manifest.get("version"),
        "source": f"{manifest['name']}@inline",
    }
    fields_match = all(runtime_plugin.get(key) == value for key, value in expected.items())
    if not path_matches or not fields_match:
        raise clean_room.RunnerFailed(
            f"runtime plugin identity mismatch: expected {expected} at {expected_plugin_root}, "
            f"observed {runtime_plugin}"
        )


def build_command(
    scenario: dict,
    model: str | None,
    claude_bin: str | None = None,
    plugin_root: Path = ROOT,
) -> list[str]:
    target = scenario["target"]
    prompt = scenario["prompt"]
    command = [claude_bin or os.environ.get("CLAUDE_BIN", "claude")]
    if scenario["mode"] == "direct":
        if target["kind"] == "skill":
            prompt = f"/{qualified_target(target, plugin_root)}\n\n{prompt}"
        else:
            command += ["--agent", qualified_target(target, plugin_root)]
    command += [
        "-p", prompt,
        "--output-format", "stream-json",
        "--verbose",
        "--forward-subagent-text",
        "--no-session-persistence",
        "--plugin-dir", str(plugin_root.resolve()),
        "--mcp-config", '{"mcpServers":{}}',
        "--strict-mcp-config",
        "--tools", ",".join(ALLOWED_BUILTIN_TOOLS),
        "--disallowedTools", DENIED_TOOLS,
    ]
    if model:
        command += ["--model", model]
    return command


class InconclusiveTrial(clean_room.RunnerFailed):
    def __init__(
        self,
        message: str,
        *,
        raw_trace: str = "",
        stderr: str = "",
        returncode: int | None = None,
        command: tuple[str, ...] = (),
        duration_seconds: float | None = None,
        requested_model: str | None = None,
        stream_diagnostics: dict | None = None,
    ):
        super().__init__(message)
        self.raw_trace = raw_trace
        self.stderr = stderr
        self.returncode = returncode
        self.command = command
        self.duration_seconds = duration_seconds
        self.requested_model = requested_model
        self.stream_diagnostics = stream_diagnostics


@dataclass(frozen=True)
class TrialExecution:
    parsed: ParsedTrace
    raw_trace: str
    stderr: str
    command: tuple[str, ...]
    returncode: int
    duration_seconds: float


def run_agent(
    scenario: dict,
    *,
    env: dict[str, str],
    cwd: Path,
    timeout: int,
    model: str | None,
    claude_bin: str | None = None,
    plugin_root: Path = ROOT,
) -> TrialExecution:
    expected_tools = expected_runtime_tools(scenario, plugin_root)
    command = build_command(
        scenario, model=model, claude_bin=claude_bin, plugin_root=plugin_root,
    )
    started = time.monotonic()
    try:
        proc = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raw = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", "replace")
        err = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode("utf-8", "replace")
        raise InconclusiveTrial(
            f"trial timed out after {timeout}s", raw_trace=raw, stderr=err, returncode=None,
            command=tuple(command), duration_seconds=time.monotonic() - started,
            requested_model=model, stream_diagnostics=_safe_stream_diagnostics(raw),
        ) from exc
    duration = time.monotonic() - started
    if clean_room.is_auth_failure(proc.stdout, proc.returncode) or clean_room.is_auth_failure(proc.stderr, proc.returncode):
        raise InconclusiveTrial(
            "Claude trial did not authenticate", raw_trace=proc.stdout, stderr=proc.stderr,
            returncode=proc.returncode, command=tuple(command), duration_seconds=duration,
            requested_model=model, stream_diagnostics=_safe_stream_diagnostics(proc.stdout),
        )
    if proc.returncode != 0:
        raise InconclusiveTrial(
            f"trial exited rc={proc.returncode}: {proc.stderr.strip()[:300]}",
            raw_trace=proc.stdout,
            stderr=proc.stderr,
            returncode=proc.returncode,
            command=tuple(command),
            duration_seconds=duration,
            requested_model=model,
            stream_diagnostics=_safe_stream_diagnostics(proc.stdout),
        )
    try:
        parsed = parse_stream_trace(proc.stdout)
        enforce_runtime_boundary(
            parsed,
            plugin_root,
            expected_tools=expected_tools,
        )
    except clean_room.AuthUnavailable as exc:
        raise InconclusiveTrial(
            str(exc), raw_trace=proc.stdout, stderr=proc.stderr, returncode=proc.returncode,
            command=tuple(command), duration_seconds=duration, requested_model=model,
            stream_diagnostics=(
                getattr(exc, "stream_diagnostics", None) or _safe_stream_diagnostics(proc.stdout)
            ),
        ) from exc
    except clean_room.RunnerFailed as exc:
        raise InconclusiveTrial(
            str(exc), raw_trace=proc.stdout, stderr=proc.stderr, returncode=proc.returncode,
            command=tuple(command), duration_seconds=duration, requested_model=model,
            stream_diagnostics=(
                getattr(exc, "stream_diagnostics", None) or _safe_stream_diagnostics(proc.stdout)
            ),
        ) from exc
    return TrialExecution(parsed, proc.stdout, proc.stderr, tuple(command), proc.returncode, duration)


def _completed_components(parsed: ParsedTrace, kind: str, *, scope: str = "any") -> set[str]:
    if scope == "root":
        return set(parsed.root_skills if kind == "skill" else parsed.root_agents)
    return set(parsed.skills if kind == "skill" else parsed.agents)


def _runtime_namespace(parsed: ParsedTrace) -> str:
    """The plugin namespace a component fires under — the loaded plugin's name, or the default."""
    return str(parsed.runtime_plugins[0].get("name")) if parsed.runtime_plugins else plugin_name()


def grade_routing(scenario: dict, parsed: ParsedTrace) -> tuple[bool, str]:
    target = scenario["target"]
    routing = scenario["routing"]
    scope = routing.get("scope", "any")
    actual = _completed_components(parsed, target["kind"], scope=scope)
    namespace = _runtime_namespace(parsed)

    def runtime_target(component: dict) -> str:
        return f"{namespace}:{component['name']}"

    accepted = {runtime_target(target)}
    accepted.update(runtime_target(alt) for alt in routing.get("also_acceptable", []))
    if routing["expect"] == "fire":
        matched = sorted(actual & accepted)
        return bool(matched), f"routing {'matched ' + ', '.join(matched) if matched else 'saw ' + repr(sorted(actual))}"

    target_name = runtime_target(target)
    if target_name in actual:
        scope_detail = " at root scope" if scope == "root" else ""
        return False, f"routing unexpectedly fired {target_name}{scope_detail}"
    alternative = routing["expected_alternative"]
    if scope == "root":
        if alternative == "inline":
            return False, "routing root scope requires a completed component alternative"
        nested_target_owners = [
            ownership.root_agent
            for ownership in parsed.nested_ownership
            if ownership.kind == target["kind"] and ownership.name == target_name
        ]
        expected_owner = runtime_target(alternative) if alternative["kind"] == "agent" else None
        if nested_target_owners and (
            expected_owner is None
            or any(owner != expected_owner for owner in nested_target_owners)
        ):
            observed_owners = sorted(owner or "unresolved" for owner in nested_target_owners)
            return False, (
                f"routing nested target {target_name} lacks expected root owner "
                f"{expected_owner or 'agent alternative'}; saw {observed_owners}"
            )
    if alternative == "inline":
        scoped_skills = _completed_components(parsed, "skill", scope=scope)
        scoped_agents = _completed_components(parsed, "agent", scope=scope)
        no_components = not scoped_skills and not scoped_agents
        if scope == "any":
            detail = f"routing expected inline; saw skills={list(parsed.skills)}, agents={list(parsed.agents)}"
        else:
            detail = (
                f"routing expected inline at root scope; saw skills={sorted(scoped_skills)}, "
                f"agents={sorted(scoped_agents)}"
            )
        return bool(no_components and parsed.response.strip()), (
            "routing stayed inline" if no_components and parsed.response.strip()
            else detail
        )
    alternate_actual = _completed_components(parsed, alternative["kind"], scope=scope)
    alternate_name = runtime_target(alternative)
    scope_detail = " at root scope" if scope == "root" else ""
    return (
        alternate_name in alternate_actual,
        f"routing expected alternative {alternate_name}{scope_detail}; saw {sorted(alternate_actual)}",
    )


def grade_direct_skill_fired(scenario: dict, parsed: ParsedTrace) -> tuple[bool, str]:
    """Prove a direct-SKILL invocation actually completed.

    A direct-skill case only PREPENDS `/save-toolkit:<skill>` to the prompt. If that slash
    expansion no-ops, the main model can answer inline and the response graders pass on reasoning
    that the skill never contributed. A direct-AGENT case is different: the `--agent` pin runs the
    session AS the agent, so the pin itself is the invocation. This check therefore applies to
    skills only, using the same namespace resolution and completed-component evidence as
    `grade_routing`.
    """
    target = scenario["target"]
    expected = f"{_runtime_namespace(parsed)}:{target['name']}"
    actual = _completed_components(parsed, "skill")
    if expected in actual:
        return True, f"pinned skill fired {expected}"
    return False, f"pinned skill {expected} did not complete; saw skills={sorted(actual)}"


def grade_trial(scenario: dict, parsed: ParsedTrace) -> tuple[bool, list[str]]:
    details: list[str] = []
    passed_all = True
    if scenario["mode"] == "discovery":
        routing_passed, routing_detail = grade_routing(scenario, parsed)
        passed_all &= routing_passed
        details.append(f"    [{'PASS' if routing_passed else 'FAIL'}] routing: {routing_detail}")
    elif scenario["mode"] == "direct" and scenario["target"]["kind"] == "skill":
        fired_passed, fired_detail = grade_direct_skill_fired(scenario, parsed)
        passed_all &= fired_passed
        details.append(f"    [{'PASS' if fired_passed else 'FAIL'}] skill-fired: {fired_detail}")
    for spec in scenario["graders"]:
        passed, detail = graders.run_grader(spec, parsed.response)
        passed_all &= passed
        details.append(f"    [{'PASS' if passed else 'FAIL'}] {spec['type']}: {detail}")
    return passed_all, details


def effective_threshold(scenario: dict, requested: float) -> float:
    """Clamp a not_fire scenario to zero tolerance regardless of the requested threshold.

    `--threshold` (and a scenario's declared threshold) apply to POSITIVES only: how often the
    expected component must fire to pass. A negative (routing.expect == not_fire) scenario passes
    only at a 0% fire rate, so its effective pass threshold is always 1.0 -- otherwise a
    `--threshold 0.66` batch would let a forbidden component over-trigger on a third of trials and
    still report PASS.
    """
    routing = scenario.get("routing")
    if isinstance(routing, dict) and routing.get("expect") == "not_fire":
        return 1.0
    return requested


def observed_models(scenario_results: list[dict]) -> list[str]:
    """The sorted set of resolved models seen across every trial in a batch.

    We record `resolved_model` per trial but never checked it. More than one entry means the batch
    silently mixed measurement conditions -- routing and behavior vary by model tier -- so it must
    not be diffed as a single baseline.
    """
    models: set[str] = set()
    for scenario in scenario_results:
        for trial in scenario.get("trials", []):
            model = trial.get("resolved_model")
            if isinstance(model, str) and model:
                models.add(model)
    return sorted(models)


def aggregate_verdict(states: list[str], threshold: float) -> str:
    required = math.ceil(len(states) * threshold)
    passes = states.count("PASS")
    inconclusive = states.count("INCONCLUSIVE")
    if passes >= required:
        return "PASS"
    if passes + inconclusive < required:
        return "FAIL"
    return "INCONCLUSIVE"


def _is_reparse_point(path: Path) -> bool:
    """Return true for links/junctions so confidentiality checks cannot be redirected."""
    try:
        info = path.lstat()
    except OSError as exc:
        raise clean_room.RunnerFailed(f"could not inspect path {path}: {exc}") from exc
    attributes = getattr(info, "st_file_attributes", 0)
    return path.is_symlink() or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


@functools.lru_cache(maxsize=1)
def _windows_sid() -> str:
    command = [
        "powershell", "-NoProfile", "-NonInteractive", "-Command",
        "[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value",
    ]
    proc = subprocess.run(
        command, capture_output=True, text=True, check=False, encoding="utf-8", errors="replace",
    )
    sid = proc.stdout.strip()
    if proc.returncode != 0 or not re.fullmatch(r"S-\d+(?:-\d+)+", sid):
        raise clean_room.RunnerFailed(
            f"could not determine the current Windows SID: {proc.stderr.strip()[:300]}"
        )
    return sid


def _windows_acl(path: Path) -> list[dict]:
    # Do not use Get-Acl here. It depends on Microsoft.PowerShell.Security module autoloading,
    # which is not reliable on current Windows hosted runners. DirectoryInfo/FileInfo expose the
    # same Windows security descriptor through .NET without importing a PowerShell module.
    script = (
        "$ErrorActionPreference='Stop'; try { "
        "$path=$env:FLEET_EVAL_ACL_PATH; "
        "if ([System.IO.Directory]::Exists($path)) { "
        "$item=[System.IO.DirectoryInfo]::new($path) "
        "} elseif ([System.IO.File]::Exists($path)) { "
        "$item=[System.IO.FileInfo]::new($path) "
        "} else { throw 'ACL path is missing' }; "
        "$acl=$item.GetAccessControl(); "
        "foreach ($entry in $acl.Access) { "
        "$sid=$entry.IdentityReference.Translate("
        "[System.Security.Principal.SecurityIdentifier]).Value; "
        "$fields=@($sid,$entry.AccessControlType.ToString(),"
        "([int]$entry.FileSystemRights).ToString(),([bool]$entry.IsInherited).ToString()); "
        "[Console]::Out.WriteLine(($fields -join [char]9)) "
        "} } catch { [Console]::Error.WriteLine($_.Exception.Message); exit 1 }"
    )
    acl_env = os.environ.copy()
    acl_env["FLEET_EVAL_ACL_PATH"] = str(path)
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script], env=acl_env,
        capture_output=True, text=True, check=False, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise clean_room.RunnerFailed(
            f"could not inspect Windows ACL for {path}: {proc.stderr.strip()[:300]}"
        )
    entries: list[dict] = []
    for line in proc.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) != 4:
            raise clean_room.RunnerFailed(f"malformed Windows ACL output for {path}")
        sid, access_type, raw_rights, raw_inherited = fields
        if (
            not re.fullmatch(r"S-\d+(?:-\d+)+", sid)
            or access_type not in {"Allow", "Deny"}
            or raw_inherited.casefold() not in {"true", "false"}
        ):
            raise clean_room.RunnerFailed(f"malformed Windows ACL output for {path}")
        try:
            rights = int(raw_rights)
        except ValueError as exc:
            raise clean_room.RunnerFailed(f"malformed Windows ACL output for {path}") from exc
        if rights < 0:
            raise clean_room.RunnerFailed(f"malformed Windows ACL output for {path}")
        entries.append(
            {
                "sid": sid,
                "type": access_type,
                "rights": rights,
                "inherited": raw_inherited.casefold() == "true",
            }
        )
    if not entries:
        raise clean_room.RunnerFailed(f"Windows ACL output has no access entries for {path}")
    return entries


def _set_windows_private_acl(path: Path, *, directory: bool) -> None:
    sid = _windows_sid()

    def run_icacls(*arguments: str) -> None:
        proc = subprocess.run(
            ["icacls", str(path), *arguments, "/C", "/Q"],
            capture_output=True, text=True, check=False, encoding="utf-8", errors="replace",
        )
        if proc.returncode != 0:
            raise clean_room.RunnerFailed(
                f"could not secure Windows artifact ACL for {path}: "
                f"{(proc.stderr or proc.stdout).strip()[:300]}"
            )

    permission = f"*{sid}:(OI)(CI)F" if directory else f"*{sid}:F"
    # Establish an explicit owner ACE before removing inherited access, or a newly-created file
    # whose only ACE is inherited can become temporarily unreadable to this process.
    run_icacls("/grant:r", permission)
    run_icacls("/inheritance:r")
    for entry in _windows_acl(path):
        principal = entry.get("sid")
        if isinstance(principal, str) and principal != sid:
            operation = "/remove:d" if entry.get("type") == "Deny" else "/remove:g"
            run_icacls(operation, f"*{principal}")
    run_icacls("/grant:r", permission)


def assert_private_path(path: Path) -> None:
    """Fail unless a trace path is protected for only the current OS identity."""
    if not path.exists() or _is_reparse_point(path):
        raise clean_room.RunnerFailed(f"private artifact path is missing or redirected: {path}")
    if os.name != "nt":
        if path.stat().st_mode & 0o077:
            raise clean_room.RunnerFailed(f"private artifact has group/other permissions: {path}")
        return

    sid = _windows_sid()
    entries = _windows_acl(path)
    if not entries:
        raise clean_room.RunnerFailed(f"private artifact has no verifiable Windows ACL: {path}")
    for entry in entries:
        if (
            entry.get("sid") != sid
            or entry.get("type") != "Allow"
            or entry.get("inherited") is not False
            or int(entry.get("rights", 0)) != 2032127  # FileSystemRights.FullControl
        ):
            raise clean_room.RunnerFailed(
                f"private artifact ACL grants an unexpected principal or permission: {path}: {entry}"
            )


def secure_directory(path: Path, *, recursive: bool = False) -> Path:
    """Create a directory and enforce a private, non-inherited permission boundary."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise clean_room.RunnerFailed(f"could not create private artifact directory {path}: {exc}") from exc
    if _is_reparse_point(path):
        raise clean_room.RunnerFailed(f"refusing redirected private artifact directory: {path}")
    if os.name == "nt":
        targets = [path]
        if recursive:
            targets.extend(path.rglob("*"))
        for target in targets:
            if _is_reparse_point(target):
                raise clean_room.RunnerFailed(
                    f"refusing redirected path beneath private artifact directory: {target}"
                )
            _set_windows_private_acl(target, directory=target.is_dir())
    else:
        try:
            os.chmod(path, stat.S_IRWXU)
            if recursive:
                for child in path.rglob("*"):
                    if _is_reparse_point(child):
                        raise clean_room.RunnerFailed(
                            f"refusing redirected path beneath private artifact directory: {child}"
                        )
                    os.chmod(child, stat.S_IRWXU if child.is_dir() else stat.S_IRUSR | stat.S_IWUSR)
        except OSError as exc:
            raise clean_room.RunnerFailed(f"could not secure artifact directory {path}: {exc}") from exc
    assert_private_path(path)
    if recursive:
        for child in path.rglob("*"):
            assert_private_path(child)
    return path


def resolve_results_root(requested: Path) -> Path:
    """Resolve a dedicated artifact parent without changing permissions on broad directories."""
    if requested.exists() and _is_reparse_point(requested):
        raise clean_room.RunnerFailed(f"refusing linked/reparse results directory: {requested}")
    resolved = requested.resolve()
    filesystem_root = Path(resolved.anchor).resolve()
    home = Path.home().resolve()
    if resolved in {filesystem_root, home} or ROOT.is_relative_to(resolved):
        raise clean_room.RunnerFailed(
            f"results directory must be dedicated and cannot be a filesystem, home, repository, "
            f"or repository-ancestor directory: {resolved}"
        )
    if resolved.exists() and not resolved.is_dir():
        raise clean_room.RunnerFailed(f"results path is not a directory: {resolved}")
    return resolved


def _private_write(path: Path, content: str) -> Path:
    try:
        if path.parent.exists():
            assert_private_path(path.parent)
        else:
            secure_directory(path.parent)
        if path.exists() or path.is_symlink():
            raise clean_room.RunnerFailed(f"refusing to overwrite private artifact: {path}")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        fd = os.open(path, flags, stat.S_IRUSR | stat.S_IWUSR)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                handle.write(content)
        except BaseException:
            try:
                os.close(fd)
            except OSError:
                pass
            raise
        if os.name == "nt":
            _set_windows_private_acl(path, directory=False)
        else:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        assert_private_path(path)
    except clean_room.RunnerFailed:
        raise
    except OSError as exc:
        raise clean_room.RunnerFailed(f"could not persist private artifact {path}: {exc}") from exc
    return path


class ArtifactWriter:
    def __init__(self, root: Path, provenance: dict):
        self.root = root
        self.provenance = provenance
        secure_directory(self.root)
        self._write_json(self.root / "manifest.json", {"schema_version": 1, "provenance": provenance})

    def _write_json(self, path: Path, value: dict) -> Path:
        return _private_write(path, json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")

    def _scenario_dir(self, scenario_id: str) -> Path:
        if not SAFE_ID_RE.fullmatch(scenario_id):
            raise ValueError(f"unsafe scenario id for artifact path: {scenario_id!r}")
        return self.root / scenario_id

    def write_trace(self, scenario_id: str, trial: int, content: str) -> Path:
        return _private_write(self._scenario_dir(scenario_id) / f"trial-{trial:03d}.stdout.jsonl", content)

    def write_stderr(self, scenario_id: str, trial: int, content: str) -> Path:
        return _private_write(self._scenario_dir(scenario_id) / f"trial-{trial:03d}.stderr.txt", content)

    def write_summary(self, summary: dict) -> Path:
        return self._write_json(self.root / "summary.json", {**summary, "provenance": self.provenance})


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_paths(paths: list[Path], *, base: Path = ROOT) -> str:
    digest = hashlib.sha256()
    for path in sorted((p for p in paths if p.is_file()), key=lambda p: p.as_posix()):
        digest.update(path.relative_to(base).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _files_under(*relative_roots: str, root: Path = ROOT) -> list[Path]:
    files: list[Path] = []
    for relative in relative_roots:
        path = root / relative
        if not path.exists():
            raise clean_room.RunnerFailed(f"required measured input is missing: {path}")
        if _is_reparse_point(path):
            raise clean_room.RunnerFailed(f"refusing linked/reparse measured input: {path}")
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            for child in path.rglob("*"):
                if _is_reparse_point(child):
                    raise clean_room.RunnerFailed(f"refusing linked/reparse measured input: {child}")
                if child.is_file():
                    files.append(child)
    return files


def plugin_digest(root: Path = ROOT) -> str:
    return _sha256_paths(_files_under(*PLUGIN_INPUT_PATHS, root=root), base=root)


def eval_suite_digest(root: Path = EVAL_ROOT) -> str:
    inputs = _files_under(*EVAL_INPUT_PATHS, root=root)
    inputs.extend(_files_under(*EVAL_SUPPORT_INPUT_PATHS, root=root.parent))
    return _sha256_paths(inputs, base=root.parent)


@contextlib.contextmanager
def frozen_eval_snapshot():
    """Copy one stable eval suite image before the measured runner process starts."""
    tmp = Path(tempfile.mkdtemp(prefix="fleet-eval-suite-snapshot-"))
    snapshot_root = tmp / "evals"
    try:
        before = eval_suite_digest(EVAL_ROOT)
        for relative in EVAL_INPUT_PATHS:
            source_root = EVAL_ROOT / relative
            if source_root.is_dir():
                (snapshot_root / relative).mkdir(parents=True, exist_ok=True)
        for source in _files_under(*EVAL_INPUT_PATHS, root=EVAL_ROOT):
            destination = snapshot_root / source.relative_to(EVAL_ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        for source in _files_under(*EVAL_SUPPORT_INPUT_PATHS, root=EVAL_ROOT.parent):
            destination = tmp / source.relative_to(EVAL_ROOT.parent)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        after = eval_suite_digest(EVAL_ROOT)
        snapshot = eval_suite_digest(snapshot_root)
        if before != after or snapshot != before:
            raise clean_room.RunnerFailed(
                "eval inputs changed while the frozen execution snapshot was being created"
            )
        yield snapshot_root.resolve()
    except OSError as exc:
        raise clean_room.RunnerFailed(f"could not create frozen eval snapshot: {exc}") from exc
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_from_frozen_eval(argv: list[str]) -> int:
    """Bootstrap a live run from frozen harness/scenario bytes, not the mutable checkout."""
    try:
        with frozen_eval_snapshot() as snapshot_root:
            env = os.environ.copy()
            env[EVAL_SNAPSHOT_ROOT_ENV] = str(snapshot_root)
            env["FLEET_ROOT"] = str(ROOT)
            proc = subprocess.run(
                [sys.executable, str(snapshot_root / "run_evals.py"), *argv],
                cwd=Path.cwd(), env=env, check=False,
            )
            return proc.returncode
    except clean_room.RunnerFailed as exc:
        print(f"run_evals: {exc}", file=sys.stderr)
        return 2


@contextlib.contextmanager
def frozen_plugin_snapshot():
    """Copy one stable plugin image so concurrent source edits cannot mix trial inputs."""
    tmp = Path(tempfile.mkdtemp(prefix="fleet-plugin-snapshot-"))
    try:
        before = plugin_digest(ROOT)
        for relative in PLUGIN_INPUT_PATHS:
            source_root = ROOT / relative
            if source_root.is_dir():
                (tmp / relative).mkdir(parents=True, exist_ok=True)
        for source in _files_under(*PLUGIN_INPUT_PATHS, root=ROOT):
            relative = source.relative_to(ROOT)
            destination = tmp / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        after = plugin_digest(ROOT)
        snapshot = plugin_digest(tmp)
        if before != after or snapshot != before:
            raise clean_room.RunnerFailed(
                "plugin inputs changed while the frozen execution snapshot was being created"
            )
        yield tmp.resolve()
    except OSError as exc:
        raise clean_room.RunnerFailed(f"could not create frozen plugin snapshot: {exc}") from exc
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def required_command_text(argv: list[str], cwd: Path = ROOT) -> str:
    proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise clean_room.RunnerFailed(
            f"provenance command failed rc={proc.returncode}: {' '.join(argv)}: {proc.stderr.strip()[:300]}"
        )
    return proc.stdout.strip()


def measurement_conditions(args: argparse.Namespace) -> dict:
    """Capture the run-shaping parameters that make two batches comparable or not.

    Identity (model, plugin commit, digests) alone does not describe a measurement: `--timeout`
    appears in no other artifact, so two runs taken at different timeouts look identical in their
    recorded conditions yet are not comparable. Trials and threshold shape the verdict the same way.
    The mode/split/match selection states which slice of the suite ran.
    """
    return {
        "timeout_s": args.timeout,
        "requested_trials": args.trials,
        "requested_threshold": args.threshold,
        "selected": {"mode": args.mode, "split": args.split, "match": args.match},
    }
    # denied_tools / allowed_builtin_tools are NOT run-shaping and are already recorded at the top
    # level of the provenance object collect_provenance() builds; they are not repeated here.


def collect_provenance(
    model: str | None,
    workspace: Path,
    claude_bin: str,
    plugin_root: Path,
    suite_sha256: str,
    conditions: dict | None = None,
) -> dict:
    manifest_path = plugin_root / ".claude-plugin" / "plugin.json"
    manifest = plugin_manifest(plugin_root)
    status = required_command_text(["git", "status", "--porcelain=v1", "--untracked-files=all"])
    plugin_status = required_command_text([
        "git", "status", "--porcelain=v1", "--untracked-files=all", "--",
        *PLUGIN_INPUT_PATHS,
    ])
    snapshot_digest = plugin_digest(plugin_root)
    workspace_digest = plugin_digest(ROOT)
    if workspace_digest != snapshot_digest:
        raise clean_room.RunnerFailed(
            "plugin workspace changed after the frozen execution snapshot was created"
        )
    return {
        "run_id": datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8],
        "started_at": datetime.now(UTC).isoformat(),
        "claude_cli_path": str(Path(claude_bin).resolve()),
        "claude_cli_version": required_command_text([claude_bin, "--version"]),
        "requested_model": model,
        "plugin_name": manifest["name"],
        "plugin_version": manifest.get("version"),
        "plugin_commit": required_command_text(["git", "rev-parse", "HEAD"]),
        "workspace_dirty": bool(status),
        "plugin_inputs_dirty": bool(plugin_status),
        "plugin_manifest_sha256": _sha256_file(manifest_path),
        "plugin_source_sha256": snapshot_digest,
        "plugin_workspace_source_sha256": workspace_digest,
        "plugin_snapshot_path": str(plugin_root),
        "plugin_snapshot_kind": "stable-copy-v1",
        "eval_suite_sha256": suite_sha256,
        "eval_snapshot_path": str(EVAL_ROOT),
        "eval_snapshot_kind": (
            "stable-copy-v1" if is_frozen_eval_process() else "workspace"
        ),
        "fixture_cwd": str(workspace),
        "fixture_sha256": hashlib.sha256(b"neutral-empty-git-root-v1\n").hexdigest(),
        "fixture_kind": "neutral-empty-git-root-v1",
        "namespace": "save-toolkit plugin plus Claude built-ins; neutral project; strict empty MCP",
        "denied_tools": DENIED_TOOLS.split(","),
        "allowed_builtin_tools": list(ALLOWED_BUILTIN_TOOLS),
        "conditions": conditions if conditions is not None else {},
    }


def _filter_scenarios(scenarios: list[dict], args: argparse.Namespace) -> list[dict]:
    selected = scenarios
    if args.match:
        selected = [s for s in selected if args.match in s["id"]]
    if args.mode != "all":
        selected = [s for s in selected if s["mode"] == args.mode]
    if args.split != "all":
        selected = [s for s in selected if s["split"] == args.split]
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--validate", action="store_true", help="validate scenario schema; no model")
    action.add_argument("--list", action="store_true", help="list selected scenarios")
    action.add_argument("--run", action="store_true", help="run selected scenarios against Claude")
    parser.add_argument("--mode", choices=["all", *sorted(MODES)], default="all")
    parser.add_argument("--split", choices=["all", *sorted(SPLITS)], default="all")
    parser.add_argument("--match", help="select scenario IDs containing this substring")
    parser.add_argument("--trials", type=positive_trials, help="override trials per scenario (>=2)")
    parser.add_argument("--threshold", type=bounded_threshold, help="override scenario pass threshold")
    parser.add_argument("--timeout", type=int, default=300, help="seconds per trial")
    parser.add_argument("--model", help="Claude model alias or full ID; actual model is recorded from trace")
    parser.add_argument("--results-dir", type=Path, default=ROOT / ".eval-runs")
    parser.add_argument("--require-clean-plugin", action="store_true", help="refuse if plugin inputs differ from HEAD")
    args = parser.parse_args()

    try:
        scenarios, suite_sha256 = load_stable_suite()
    except clean_room.RunnerFailed as exc:
        print(f"run_evals: {exc}", file=sys.stderr)
        return 2 if args.run else 3
    if not scenarios:
        print(f"evals: no scenarios found in {SCENARIOS_DIR}")
        return 3
    problems = validate(scenarios)
    if problems:
        print("EVAL SUITE INVALID:")
        print("\n".join("  - " + problem for problem in problems))
        return 3
    if args.validate:
        direct = sum(s["mode"] == "direct" for s in scenarios)
        discovery = len(scenarios) - direct
        regression = sum(s["split"] == "regression" for s in scenarios)
        print(
            f"eval suite OK -- {len(scenarios)} scenarios "
            f"({direct} direct, {discovery} discovery, {regression} regression)."
        )
        return 0

    selected = _filter_scenarios(scenarios, args)
    if not selected:
        print("no scenarios matched the requested filters")
        return 3
    if args.list:
        for scenario in selected:
            target = scenario["target"]
            print(f"- {scenario['id']} [{scenario['mode']}/{scenario['split']}] -> {target['kind']}:{target['name']}")
        return 0

    if not is_frozen_eval_process():
        print("run_evals: live execution requires the frozen eval bootstrap", file=sys.stderr)
        return 2

    claude_setting = os.environ.get("CLAUDE_BIN", "claude")
    claude_bin = shutil.which(claude_setting) or (claude_setting if Path(claude_setting).is_file() else None)
    if not claude_bin:
        print(f"run_evals: Claude CLI not found: {claude_setting}", file=sys.stderr)
        return 2

    try:
        results_root = resolve_results_root(args.results_dir)
        with (
            frozen_plugin_snapshot() as plugin_root,
            clean_room.clean_env() as env,
            clean_room.neutral_workspace() as workspace,
        ):
            provenance = collect_provenance(
                args.model, workspace, claude_bin, plugin_root, suite_sha256,
                measurement_conditions(args),
            )
            if args.require_clean_plugin and provenance["plugin_inputs_dirty"]:
                print("run_evals: plugin inputs differ from HEAD; refusing publishable baseline", file=sys.stderr)
                return 2
            run_dir = results_root / provenance["run_id"]
            writer = ArtifactWriter(run_dir, provenance)
            scenario_results: list[dict] = []
            print(f"run: {provenance['run_id']} | CLI {provenance['claude_cli_version']} | plugin {provenance['plugin_commit']}")
            print(f"namespace: {provenance['namespace']} | artifacts: {run_dir}")
            for scenario in selected:
                trials = args.trials or scenario.get("trials", DEFAULT_TRIALS)
                threshold = effective_threshold(
                    scenario, args.threshold or scenario.get("threshold", DEFAULT_THRESHOLD)
                )
                states: list[str] = []
                trial_results: list[dict] = []
                print(f"\n== {scenario['id']} [{scenario['mode']}/{scenario['split']}] ==")
                for trial_number in range(1, trials + 1):
                    started_at = datetime.now(UTC).isoformat()
                    planned_command = build_command(
                        scenario, args.model, claude_bin, plugin_root,
                    )
                    try:
                        execution = run_agent(
                            scenario, env=env, cwd=workspace, timeout=args.timeout,
                            model=args.model, claude_bin=claude_bin, plugin_root=plugin_root,
                        )
                        writer.write_trace(scenario["id"], trial_number, execution.raw_trace)
                        writer.write_stderr(scenario["id"], trial_number, execution.stderr)
                        passed, details = grade_trial(scenario, execution.parsed)
                        state = "PASS" if passed else "FAIL"
                        trial_result = {
                            "trial": trial_number,
                            "state": state,
                            "started_at": started_at,
                            "duration_seconds": execution.duration_seconds,
                            "exit_code": execution.returncode,
                            "resolved_model": execution.parsed.model,
                            "session_id": execution.parsed.session_id,
                            "total_cost_usd": execution.parsed.total_cost_usd,
                            "completed_invocations": {
                                "skills": list(execution.parsed.skills),
                                "agents": list(execution.parsed.agents),
                            },
                            "completed_root_invocations": {
                                "skills": list(execution.parsed.root_skills),
                                "agents": list(execution.parsed.root_agents),
                            },
                            "attempted_invocations": {
                                "skills": list(execution.parsed.attempted_skills),
                                "agents": list(execution.parsed.attempted_agents),
                            },
                            "runtime_namespace": {
                                "plugins": list(execution.parsed.runtime_plugins),
                                "mcp_servers": list(execution.parsed.mcp_servers),
                                "available_skills": list(execution.parsed.available_skills),
                                "available_agents": list(execution.parsed.available_agents),
                                "available_tools": list(execution.parsed.available_tools),
                            },
                            "stream_diagnostics": execution.parsed.stream_diagnostics.to_summary(),
                            "details": details,
                            "argv": list(execution.command),
                        }
                    except (InconclusiveTrial, clean_room.AuthUnavailable) as exc:
                        state = "INCONCLUSIVE"
                        raw = getattr(exc, "raw_trace", "")
                        stderr = getattr(exc, "stderr", "")
                        writer.write_trace(scenario["id"], trial_number, raw)
                        writer.write_stderr(scenario["id"], trial_number, stderr)
                        trial_result = {
                            "trial": trial_number,
                            "state": state,
                            "started_at": started_at,
                            "reason": str(exc),
                            "exit_code": getattr(exc, "returncode", None),
                            "duration_seconds": getattr(exc, "duration_seconds", None),
                            "requested_model": getattr(exc, "requested_model", args.model),
                            "resolved_model": None,
                            "session_id": None,
                            "total_cost_usd": None,
                            "completed_invocations": {"skills": [], "agents": []},
                            "completed_root_invocations": {"skills": [], "agents": []},
                            "attempted_invocations": {"skills": [], "agents": []},
                            "runtime_namespace": None,
                            "stream_diagnostics": getattr(exc, "stream_diagnostics", None),
                            "argv": list(getattr(exc, "command", ()) or planned_command),
                        }
                    states.append(state)
                    trial_results.append(trial_result)
                    print(f"  trial {trial_number}: {state}")
                    if state == "FAIL":
                        print("\n".join(trial_result["details"]))
                    elif state == "INCONCLUSIVE":
                        print(f"    {trial_result['reason']}")
                verdict = aggregate_verdict(states, threshold)
                print(f"  -> {verdict} ({states.count('PASS')}/{trials} pass; threshold {threshold})")
                scenario_results.append({
                    "id": scenario["id"],
                    "mode": scenario["mode"],
                    "split": scenario["split"],
                    "target": scenario["target"],
                    "scenario_sha256": scenario["_source_sha256"],
                    "trials": trial_results,
                    "threshold": threshold,
                    "verdict": verdict,
                })

            verdicts = [result["verdict"] for result in scenario_results]
            overall = "FAIL" if "FAIL" in verdicts else ("INCONCLUSIVE" if "INCONCLUSIVE" in verdicts else "PASS")
            integrity_errors: list[str] = []
            if plugin_digest(plugin_root) != provenance["plugin_source_sha256"]:
                integrity_errors.append("frozen plugin snapshot changed during execution")
            if eval_suite_digest() != provenance["eval_suite_sha256"]:
                integrity_errors.append("eval harness or scenario files changed during execution")
            models_observed = observed_models(scenario_results)
            if len(models_observed) > 1:
                integrity_errors.append(f"batch mixed resolved models: {models_observed}")
                print(
                    "\n!! WARNING: this batch mixed resolved models "
                    f"({', '.join(models_observed)}); it mixes measurement conditions and must "
                    "not be diffed as a single baseline. Pin --model for a comparable run."
                )
            if integrity_errors:
                overall = "INCONCLUSIVE"
            summary_path = writer.write_summary({
                "schema_version": 1,
                "verdict": overall,
                "selected": {"mode": args.mode, "split": args.split, "match": args.match},
                "scenarios": scenario_results,
                "models_observed": models_observed,
                "integrity": {
                    "state": "PASS" if not integrity_errors else "INCONCLUSIVE",
                    "errors": integrity_errors,
                },
                "completed_at": datetime.now(UTC).isoformat(),
            })
            if integrity_errors:
                print("\nINCONCLUSIVE integrity check: " + "; ".join(integrity_errors))
            print(f"\n{overall}: {verdicts.count('PASS')}/{len(verdicts)} scenarios passed; summary: {summary_path}")
            return {"PASS": 0, "FAIL": 1, "INCONCLUSIVE": 2}[overall]
    except clean_room.AuthUnavailable as exc:
        print(f"run_evals: {exc}", file=sys.stderr)
        return 2
    except clean_room.RunnerFailed as exc:
        print(f"run_evals: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    if "--run" in sys.argv[1:] and not is_frozen_eval_process():
        raise SystemExit(run_from_frozen_eval(sys.argv[1:]))
    raise SystemExit(main())
