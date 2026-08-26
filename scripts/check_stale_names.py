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
    # `researcher` and `agent-engineer` remain canonical plugin agents.
    # `observer` retired into `sre-steward`, which then retired into `observability-engineer`;
    # `scribe` is canonical again. `sre-steward` was renamed because `sre` is a strict prefix of
    # it, which makes substring-matching tooling (eval graders, adapter name rewriting) confuse
    # the incident lane with the steady-state lane.
    # `prompt-engineer` retired into `agent-engineer`: the lane owns agent bodies, skills, roster
    # and delegation graphs, and eval loops, of which prompt text is one artifact. The sibling
    # `sde-agents` fleet still ships a `prompt-engineer`, so leaving the old name unguarded here
    # would let a cross-fleet copy read as this fleet's.
    "prompt-engineer",
    "sde", "sre-engineer", "sde-engineer", "code-reviewer", "security-reviewer",
    "test-engineer", "sre-monitor", "runbook-author",
    "observer", "sre-steward",
    # The plugin itself was renamed `sre-agents` -> `save-toolkit`, which is what finally removed
    # the `sre` ⊂ `sre-agents` prefix collision (renaming agents alone could never fix it, because
    # the namespace carried the collision). Listed here so leftover `sre-agents:<component>`
    # addressing in agents/, skills/, or commands/ fails the build instead of silently not
    # resolving. Repository URLs are unaffected: `SIBLING_REPOSITORIES` keeps it usable as a path.
    "sre-agents",
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
    # `craft` (the skill) retired into `language-idiom` but is NOT listed here, deliberately: it is
    # ordinary English, and the boundary regex would flag legitimate prose ("# Frontend craft",
    # "reads as noise rather than craft" — 19 such hits when probed). This is exactly why common
    # English words make poor component names: they cannot be machine-protected after retirement.
    # Drift to the old name is caught by the adapter byte-for-byte check and the router eval instead.
    # Generator-era vocabulary retired by the de-projection (Tasks 2-3 of the adoption plan).
    "required-skills", "generate_fleet",
)
STALE_RE = re.compile(
    r"(?<![A-Za-z0-9-])(" + "|".join(re.escape(name) for name in sorted(STALE, key=len, reverse=True))
    + r")(?![A-Za-z0-9-])"
)


SCANNED_ROOTS = (Path("skills"), Path("agents"), Path("commands"), Path("evals/scenarios"))
# Real sibling repositories, so `latent-sre/sde-agents` in a URL is a legitimate reference even
# though both names are retired as fleet units. Names, not paths: the carve-out below is granted
# per name, never to every retired unit.
SIBLING_REPOSITORIES = frozenset({"sre-agents", "sde-agents"})


def _filename_exempt_names(root: Path) -> frozenset:
    """Retired unit names that still name a real file in the scanned tree.

    Some units were retired as *units* while their name survived as a *filename*: `api-design`
    became `skills/backend-craft/references/api-design.md`. A link to that file must not trip the
    guard. Granting the carve-out to every retired name instead made it far too wide -- a handoff
    naming `agents/prompt-engineer.md` passed Gate A, which is the retired identity the rename
    exists to reject. Tie the exemption to evidence that such a file is actually there.
    """

    live = set()
    for relative in SCANNED_ROOTS:
        base = root / relative
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_file():
                live.add(path.stem)
    return frozenset(live & set(STALE)) | SIBLING_REPOSITORIES


def _hits(text: str, exempt: frozenset = SIBLING_REPOSITORIES):
    for match in STALE_RE.finditer(text):
        before = text[match.start() - 1] if match.start() else ""
        after = text[match.end() :]
        adjacent = before == "/" or after.startswith("/") or after.startswith(".md")
        if adjacent and match.group(1) in exempt:
            continue
        yield match


def _scan_file(path: Path, exempt: frozenset) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    except OSError as exc:
        return [f"{path.as_posix()}: cannot read: {exc}"]
    failures = []
    for number, line in enumerate(text.splitlines(), start=1):
        for match in _hits(line, exempt):
            failures.append(
                f"{path.as_posix()}:{number}: stale fleet-unit name '{match.group(1)}'"
            )
    return failures


def _scan_tree(root: Path) -> list[str]:
    failures = []
    # `evals/scenarios` and NOT `evals`. Scenario prompts are sent to the model byte-for-byte, so a
    # retired name in one actively teaches the fleet's old vocabulary -- two did, naming
    # `sde-engineer` and `code-reviewer`. The rest of evals/ must stay out of scope: `baselines/`
    # holds frozen result JSON that records what was true on the day it ran, and the repo has
    # committed to leaving those bytes unchanged. Widening this to `evals` lights up on 24 such
    # hits that are supposed to be there.
    exempt = _filename_exempt_names(root)
    for relative in SCANNED_ROOTS:
        base = root / relative
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                failures.extend(_scan_file(path, exempt))
    return failures


def _scan_value(value: object, json_path: str, exempt: frozenset) -> list[str]:
    if not isinstance(value, str):
        return []
    return [
        f"canonical/fleet.json:{json_path}: stale fleet-unit name '{match.group(1)}'"
        for match in _hits(value, exempt)
    ]


def _scan_metadata(root: Path) -> list[str]:
    # `canonical/fleet.json` is not part of the current architecture (the fleet generates from
    # canonical agents/skills/commands, with no separate metadata manifest), so this scan is dormant
    # on the shipped tree. It is retained, not dead: it is exercised by fixtures in
    # test_check_links.py (StaleNameCheckerTests), and it guards the reintroduction of any such
    # manifest against carrying a retired name. A dormant-but-tested guard over a cheap no-op branch
    # stays; deleting a tested guard because its target file is currently absent is the exact
    # "the failure can't happen right now" reasoning this repo distrusts.
    path = root / "canonical" / "fleet.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"canonical/fleet.json: cannot parse metadata for stale-name scan: {exc}"]
    exempt = _filename_exempt_names(root)
    failures = []
    for index, agent in enumerate(data.get("agents", [])):
        if isinstance(agent, dict):
            failures.extend(
                _scan_value(agent.get("description"), f"agents[{index}].description", exempt)
            )
    for index, command in enumerate(data.get("commands", [])):
        if not isinstance(command, dict):
            continue
        failures.extend(
            _scan_value(command.get("description"), f"commands[{index}].description", exempt)
        )
        if "argument_usage" in command:
            failures.extend(
                _scan_value(command.get("argument_usage"), f"commands[{index}].argument_usage", exempt)
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
