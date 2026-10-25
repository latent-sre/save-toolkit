"""Private, screened artifacts and identity-bound v1 result records."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from probe import invocation, tracing
from probe.records import RecordV1

PROFILE = {"name": "static-repair-independently-verified-dec13", "authentication": "openrouter-host-proxy"}
_PATH = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*(/[A-Za-z0-9_-][A-Za-z0-9_.-]*)*")
_MARKERS = (b"sk-or-", b"sk-ant-", b"ghp_", b"AKIA")


def screen(data: bytes, secrets: Sequence[str] = ()) -> None:
    """Reject disclosure before persistence; errors contain no candidate output."""
    if any(marker in data for marker in _MARKERS) or any(secret.encode() in data for secret in secrets if secret):
        raise ValueError("credential-shaped content rejected before artifact storage")


def store_bytes(root: Path, name: str, data: bytes, *, secrets: Sequence[str] = ()) -> Path:
    screen(data, secrets)
    if not _PATH.fullmatch(name) or any(part.startswith(".") for part in name.split("/")):
        raise ValueError("artifact path must remain inside its attempt")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.is_symlink():
        raise ValueError("artifact root path must not be a symlink")
    path = root / name
    parent = root
    for part in name.split("/")[:-1]:
        parent = parent / part
        if parent.is_symlink():
            raise ValueError("artifact parent path must not be a symlink")
        parent.mkdir(mode=0o700, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags, 0o600), "wb") as stream:
        stream.write(data)
    return path


def store_json(root: Path, name: str, value: object, *, secrets: Sequence[str] = ()) -> Path:
    return store_bytes(root, name, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode(), secrets=secrets)


def runtime_problem(
    trace_path: Path, plugin_root: Path, runtime_path: str, model: str, tools: Sequence[str]
) -> str | None:
    """An init event must name the model and the exact mounted snapshot."""
    try:
        events = [json.loads(line) for line in trace_path.read_text().splitlines() if line.strip()]
        inits = [
            event
            for event in events
            if isinstance(event, dict)
            and event.get("type") == "system"
            and event.get("subtype") == "init"
            and not event.get("parent_tool_use_id")
        ]
        if len(inits) != 1:
            return "expected exactly one main init event"
        init = inits[0]
        if init.get("model") != model:
            return "init model differs from the frozen model"
        plugins = init.get("plugins")
        name = json.loads((plugin_root / ".claude-plugin/plugin.json").read_text())["name"]
        if not isinstance(plugins, list) or len(plugins) != 1:
            return "init must contain exactly one staged plugin"
        plugin = plugins[0]
        if not isinstance(plugin, dict) or plugin.get("name") != name or plugin.get("path") != runtime_path:
            return "init plugin name or mounted path differs from the staged plugin"
        trace = tracing.parse_trace(trace_path)
        return invocation.runtime_boundary_problem(trace, tools)
    except (ValueError, OSError, KeyError, TypeError):
        return "runtime identity evidence is unreadable or malformed"


def make_record(
    *,
    identity: Mapping[str, Any],
    candidate: Mapping[str, Any],
    runner: Mapping[str, Any],
    model: str,
    runtime: Mapping[str, Any],
    label: str,
    started: str,
    ended: str,
    state: str,
    reason: str | None,
    ending: str,
    stop: str | None,
    estimated_cost: float | None,
    evidence: Mapping[str, str],
    after_assessment: str | None = None,
) -> dict[str, Any]:
    """Keep verifier results and CLI cost estimates separate from measured billing."""
    raw = {
        "format": {"name": "save-toolkit.eval-record", "version": 1},
        "case": {
            "id": identity["instance_id"],
            "case_sha256": hashlib.sha256(
                json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            "scenario_sha256": None,
        },
        "candidate": dict(candidate),
        "runner": dict(runner),
        "conditions": {
            "requested_model": model,
            "observed_models": [model] if ending in {"completed", "turn_limit"} else None,
            "runtime": dict(runtime),
            "turn_limit": 64,
            "wall_clock_seconds": 2700,
            "execution_profile": PROFILE,
        },
        "attempt": {"label": label, "slot": 1, "number": 1, "state": "final", "started_at": started, "ended_at": ended},
        "run_end": {"kind": ending, "stop": stop, "reason": reason},
        "checks": [
            {
                "id": "independent-repair-verification",
                "text": "Independent SWE-bench repair verification",
                "kind": "requires",
                "state": state,
                "reason": reason if state == "INCONCLUSIVE" else None,
                "evidence": reason or "all required repair and regression tests passed",
                "evidence_truncated": False,
            }
        ],
        "verdict": {"status": state, "reason": reason, "assessment_revision": 0, "after_assessment": after_assessment},
        "cost": {
            "trial_usd": estimated_cost,
            "judge_usd": 0.0,
            "known_usd": estimated_cost,
            "complete": estimated_cost is not None,
            "judge_calls": 0,
            "judge_live_calls": 0,
            "judge_cached_calls": 0,
            "judge_unknown_cost_calls": 0,
        },
        "evidence": dict(evidence),
        "assessments": [],
    }
    return RecordV1.model_validate_json(json.dumps(raw)).model_dump(mode="json")
