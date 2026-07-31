#!/usr/bin/env python3
"""Reject retired fleet-unit names in new LLM-facing content and metadata."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


ROOT = Path(os.environ.get("FLEET_ROOT") or Path(__file__).resolve().parents[1]).resolve()
STALE = (
    # `researcher` and `prompt-engineer` remain canonical plugin agents.
    # `observer` and `scribe` retired into `sre-steward`.
    "sre-engineer", "sde-engineer", "code-reviewer", "security-reviewer",
    "test-engineer", "sre-monitor", "runbook-author",
    "observer", "scribe",
    "incident-severity", "blameless-postmortem",
    "rollback-mitigation", "github-actions-ci", "wavefront-queries",
    "splunk-triage", "grafana-dashboards", "moogsoft-correlation",
    "thousandeyes-network", "slo-error-budget", "instrument-service",
    "api-design", "ops-stack-integration", "spa-architecture", "ops-cli",
    "sde-ladder", "sre-ladder", "tdd-workflow", "safe-refactor",
    "debug-rca", "self-improve-loop", "context-engineering", "tool-design",
    "handoff-protocol", "route-request", "adr-template", "runbook-template",
    "bamboo-to-actions-migration", "sde-fullstack", "homelab-platform",
    "principal-engineer", "distinguished-architect", "multi-agent-architect",
    "prompt-craft", "sre-tool", "service-onboard", "lab-audit", "sde-agents",
    # Generator-era vocabulary retired by the de-projection (Tasks 2-3 of the adoption plan).
    "required-skills", "generate_fleet",
)
STALE_RE = re.compile(
    r"(?<![A-Za-z0-9-])(" + "|".join(re.escape(name) for name in sorted(STALE, key=len, reverse=True))
    + r")(?![A-Za-z0-9-])"
)


def _hits(text: str):
    for match in STALE_RE.finditer(text):
        before = text[match.start() - 1] if match.start() else ""
        after = text[match.end() :]
        if before == "/" or after.startswith("/") or after.startswith(".md"):
            continue
        yield match


def _scan_file(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    except OSError as exc:
        return [f"{path.as_posix()}: cannot read: {exc}"]
    failures = []
    for number, line in enumerate(text.splitlines(), start=1):
        for match in _hits(line):
            failures.append(
                f"{path.as_posix()}:{number}: stale fleet-unit name '{match.group(1)}'"
            )
    return failures


def _scan_tree(root: Path) -> list[str]:
    failures = []
    for relative in (Path("skills"), Path("agents"), Path("commands")):
        base = root / relative
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                failures.extend(_scan_file(path))
    return failures


def _scan_value(value: object, json_path: str) -> list[str]:
    if not isinstance(value, str):
        return []
    return [
        f"canonical/fleet.json:{json_path}: stale fleet-unit name '{match.group(1)}'"
        for match in _hits(value)
    ]


def _scan_metadata(root: Path) -> list[str]:
    path = root / "canonical" / "fleet.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"canonical/fleet.json: cannot parse metadata for stale-name scan: {exc}"]
    failures = []
    for index, agent in enumerate(data.get("agents", [])):
        if isinstance(agent, dict):
            failures.extend(
                _scan_value(agent.get("description"), f"agents[{index}].description")
            )
    for index, command in enumerate(data.get("commands", [])):
        if not isinstance(command, dict):
            continue
        failures.extend(
            _scan_value(command.get("description"), f"commands[{index}].description")
        )
        if "argument_usage" in command:
            failures.extend(
                _scan_value(command.get("argument_usage"), f"commands[{index}].argument_usage")
            )
    return failures


def check(root: Path = ROOT) -> list[str]:
    root = Path(root).resolve()
    return _scan_tree(root) + _scan_metadata(root)


def main() -> int:
    failures = check(ROOT)
    if failures:
        print("check_stale_names: FAIL")
        for failure in failures:
            print("  " + failure)
        return 1
    print("check_stale_names: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
