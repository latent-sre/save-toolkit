#!/usr/bin/env python3
"""G6 -- bound canonical instruction-file bytes for representative task paths.

Each profile names its conditional references as well as entrypoints. These are instruction-file
budgets, not full runtime context: host/caller instructions, project source and tool output are
excluded, and tokens are only a bytes/4 estimate. Other task predicates can load further references.
Always-loaded agent/skill descriptions have a separate budget.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from scripts import fleet_frontmatter
except ModuleNotFoundError:
    import fleet_frontmatter  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[1]

# Fixed budgets allow ordinary wording changes without a 5% ratchet. The 2026-09-14 rebaseline
# uses at least 20% headroom (2 KB minimum), rounded up to 1 KB, retaining higher existing limits.
# They never grow from live measurements; increasing a limit remains a reviewed source change.
_ENGINEERING_CONTEXT = [
    "agents/software-engineer.md",
    "skills/stack-profile/SKILL.md",
    "skills/stack-profile/references/application-and-data-stack.md",
]
_PYTHON_CONTEXT = [
    *_ENGINEERING_CONTEXT,
    "skills/python-craft/SKILL.md",
    "skills/python-craft/references/writing-python.md",
]
_FASTAPI_UPSTREAM = [
    *_PYTHON_CONTEXT,
    "skills/backend-craft/SKILL.md",
    "skills/backend-craft/references/fastapi.md",
    "skills/backend-craft/references/consuming-apis.md",
]
_AGENT_REPAIR_CONTEXT = [
    "agents/agent-engineer.md",
    "skills/agent-authoring/SKILL.md",
    "skills/agent-authoring/references/artifact.md",
    "skills/agent-authoring/references/agent-security.md",
]
TASK_FILES: dict[str, list[str]] = {
    # Reader lanes have no skill loads. Repository contents, fetched evidence and tool schemas
    # remain outside this instruction-file measurement, as they do for every other profile.
    "Repository fact lookup": ["agents/repository-investigator.md"],
    "Public contract research": ["agents/researcher.md"],
    "Agent instruction repair": [*_AGENT_REPAIR_CONTEXT],
    "Agent delegation and tool change": [
        *_AGENT_REPAIR_CONTEXT,
        "skills/agent-authoring/references/roster.md",
        "skills/agent-authoring/references/tools.md",
        "skills/agent-authoring/references/context.md",
        "skills/agent-authoring/references/delegation-graph.md",
        "skills/agent-authoring/references/claude-code-frontmatter.md",
    ],
    # Trusted guidance selected for a Python review; candidate source and tool output are separate.
    "Independent Python review": [
        "agents/reviewer.md",
        "skills/stack-profile/SKILL.md",
        "skills/stack-profile/references/application-and-data-stack.md",
        "skills/python-craft/SKILL.md",
        "skills/python-craft/references/writing-python.md",
        "skills/python-craft/references/refactoring.md",
        "docs/docker-verification.md",
    ],
    "PCF incident, human path": [
        "skills/incident-investigation/SKILL.md",
        "skills/incident-investigation/references/symptom-investigation.md",
        "skills/stack-profile/SKILL.md",
        "skills/stack-profile/references/observability-stack.md",
        "skills/incident-investigation/references/severity-and-escalation.md",
        "skills/pcf-ops/SKILL.md",
        "skills/obs-logs/SKILL.md",
        "skills/obs-logs/references/spl.md",
        "skills/root-cause/SKILL.md",
    ],
    "PCF incident, sre-assistant agent path": [
        "agents/sre-assistant.md",
        "skills/pcf-ops/SKILL.md",
        "skills/pcf-ops/references/router-errors.md",
        "skills/obs-logs/SKILL.md",
        "skills/obs-logs/references/spl.md",
        "skills/root-cause/SKILL.md",
        "skills/incident-investigation/references/severity-and-escalation.md",
        "skills/production-change-gate/SKILL.md",
        "skills/production-change-gate/references/tier-2-approval-example.md",
        "skills/stack-profile/SKILL.md",
        "skills/stack-profile/references/observability-stack.md",
    ],
    # Mitigation choice and a technical update load different depth from symptom diagnosis.
    "PCF mitigation advice and TLC update": [
        "skills/incident-investigation/SKILL.md",
        "skills/incident-investigation/references/mitigation-selection.md",
        "skills/incident-investigation/references/severity-and-escalation.md",
        "skills/incident-investigation/references/technical-updates.md",
        "skills/incident-investigation/references/pcf-rollback-readback.md",
        "skills/stack-profile/SKILL.md",
        "skills/pcf-ops/SKILL.md",
        "skills/production-change-gate/SKILL.md",
        "skills/production-change-gate/references/incident-fast-path.md",
    ],
    # A metric-backed Grafana burn-rate rule, including the query and backend guidance it loads.
    "Noisy alert": [
        "agents/observability-engineer.md",
        "skills/obs-alerting/SKILL.md",
        "skills/obs-alerting/references/burn-rate.md",
        "skills/obs-alerting/references/grafana-alerting.md",
        "skills/stack-profile/SKILL.md",
        "skills/stack-profile/references/observability-stack.md",
        "skills/obs-metrics/SKILL.md",
        "skills/obs-metrics/references/promql.md",
    ],
    "Write a runbook": [
        "agents/scribe.md",
        "skills/runbook/SKILL.md",
        "skills/runbook/assets/runbook-template.md",
        "skills/runbook/assets/runbook-example.md",
    ],
    "Audit a service": [
        "skills/service-lifecycle/SKILL.md",
        "skills/stack-profile/SKILL.md",
        "skills/obs-alerting/SKILL.md",
        "skills/obs-pipeline/SKILL.md",
        "skills/runbook/SKILL.md",
        "skills/stack-profile/references/observability-stack.md",
    ],
    # Existing HTTP read-path changes with an upstream call and stack/toolchain inspection.
    # No new schema, retryable write, migration, telemetry or CI change is implied by these profiles.
    "FastAPI upstream change": [*_FASTAPI_UPSTREAM],
    # Explicitly automated tasks exercise the optional tools reference; ordinary Python work
    # loads only the references matching its task. Keep every new reference on a measured path.
    "Python automated refactor": [
        *_PYTHON_CONTEXT,
        "skills/python-craft/references/environment-and-checks.md",
        "skills/python-craft/references/refactoring.md",
        "skills/python-craft/references/refactoring-tools.md",
    ],
    "Python library migration": [
        *_PYTHON_CONTEXT,
        "skills/python-craft/references/environment-and-checks.md",
        "skills/python-craft/references/libraries-and-modernization.md",
        "skills/python-craft/references/refactoring-tools.md",
    ],
    "Existing UI change": [
        *_ENGINEERING_CONTEXT,
        "skills/frontend-craft/SKILL.md",
    ],
    "Greenfield UI": [
        *_ENGINEERING_CONTEXT,
        "skills/frontend-craft/SKILL.md",
        "skills/frontend-craft/references/stack.md",
        "skills/frontend-craft/references/design-language.md",
    ],
    # The same FastAPI task followed by release-readiness/artifact review, not live authorization.
    "Prepare FastAPI release": [
        *_FASTAPI_UPSTREAM,
        "skills/production-change-gate/SKILL.md",
        "skills/production-change-gate/references/release-readiness.md",
        "skills/production-change-gate/references/release-artifact-evidence.md",
    ],
}
TASK_BUDGETS: dict[str, int] = {
    "Repository fact lookup": 8_000,
    "Public contract research": 12_000,
    "Agent instruction repair": 42_000,
    "Agent delegation and tool change": 74_000,
    "Independent Python review": 50_000,
    "PCF incident, human path": 87_000,
    "PCF incident, sre-assistant agent path": 85_000,
    "PCF mitigation advice and TLC update": 86_000,
    "Noisy alert": 62_000,
    "Write a runbook": 48_000,
    "Audit a service": 44_000,
    "FastAPI upstream change": 69_000,
    "Python automated refactor": 72_000,
    "Python library migration": 71_000,
    "Existing UI change": 52_000,
    "Greenfield UI": 60_000,
    "Prepare FastAPI release": 83_000,
}
DESCRIPTION_TASK = "Always-loaded descriptions"
DESCRIPTION_BUDGET = 20_000


class MissingFile(Exception):
    """A canonical task lists a file that no longer exists."""


def task_bytes(paths: list[str]) -> int:
    total = 0
    for rel in paths:
        path = ROOT / rel
        if not path.is_file():
            raise MissingFile(rel)
        total += path.stat().st_size
    return total


def description_bytes() -> int:
    """Sum every agent/skill `description:` field -- loaded on every turn, not just one task."""
    total = 0
    for pattern in ("agents/*.md", "skills/*/SKILL.md"):
        for path in sorted(ROOT.glob(pattern)):
            parsed = fleet_frontmatter.parse(
                path.read_text(encoding="utf-8"), path.relative_to(ROOT), mode="lenient"
            )
            description = parsed.fields.get("description")
            if isinstance(description, str):
                total += len(description.encode("utf-8"))
    return total


def main(argv: list[str] | None = None) -> int:
    rows: list[tuple[str, int, int]] = []
    failed: list[str] = []

    for task, paths in TASK_FILES.items():
        budget = TASK_BUDGETS[task]
        try:
            total = task_bytes(paths)
        except MissingFile as exc:
            print("ERROR: %s: missing file %s" % (task, exc), file=sys.stderr)
            failed.append(task)
            continue
        rows.append((task, total, budget))
        if total > budget:
            failed.append(task)

    total = description_bytes()
    rows.append((DESCRIPTION_TASK, total, DESCRIPTION_BUDGET))
    if total > DESCRIPTION_BUDGET:
        failed.append(DESCRIPTION_TASK)

    width = max(len(task) for task, _, _ in rows)
    print("%-*s  %10s  %10s  %10s" % (width, "Task", "bytes", "~tokens", "budget"))
    for task, total, budget in rows:
        flag = "FAIL" if total > budget else "ok"
        print(
            "%-*s  %10d  %10d  %10d  %s"
            % (width, task, total, total // 4, budget, flag)
        )

    if failed:
        print("\ncheck_context_cost: FAIL -- over budget: %s" % ", ".join(failed))
        return 1
    print("\ncheck_context_cost: PASS -- %d/%d tasks within budget" % (len(rows), len(rows)))
    print("Representative instruction files only; host context, tool schemas/results and task data excluded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
