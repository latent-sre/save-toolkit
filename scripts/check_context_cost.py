#!/usr/bin/env python3
"""G6 -- the context-cost gate: bound the bytes a session loads for canonical tasks.

For each canonical task, sums the bytes of the files a session would load and compares the sum
against a budget. Also sums every agent/skill `description:` field, which is always loaded
regardless of task (it is what routes a request to a lane in the first place).
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from scripts import fleet_frontmatter
except ModuleNotFoundError:
    import fleet_frontmatter  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[1]

# Byte budgets per canonical task, set to measured usage plus 5% and rounded up to the next 1,000.
# Raising one is a reviewed decision made in the same diff that earns it, not a side effect of an
# unrelated change.
TASK_FILES: dict[str, list[str]] = {
    "PCF incident, human path": [
        "skills/incident-investigation/SKILL.md",
        "skills/stack-profile/SKILL.md",
        "skills/stack-profile/references/observability-stack.md",
        "skills/incident-command/SKILL.md",
        "skills/incident-command/references/severity-and-declaration.md",
        "skills/pcf-ops/SKILL.md",
        "skills/obs-logs/SKILL.md",
        "skills/obs-logs/references/spl.md",
        "skills/root-cause/SKILL.md",
    ],
    "PCF incident, sre-assistant agent path": [
        "agents/sre-assistant.md",
        "skills/investigation-depth/SKILL.md",
        "skills/investigation-depth/references/first-response.md",
        "skills/pcf-ops/SKILL.md",
        "skills/pcf-ops/references/router-errors.md",
        "skills/obs-logs/SKILL.md",
        "skills/obs-logs/references/spl.md",
        "skills/root-cause/SKILL.md",
        "skills/incident-command/SKILL.md",
        "skills/incident-command/references/severity-and-declaration.md",
        "skills/production-change-gate/SKILL.md",
        "skills/production-change-gate/references/tier-2-approval-example.md",
        "skills/stack-profile/SKILL.md",
    ],
    "Noisy alert": [
        "agents/observability-engineer.md",
        "skills/obs-alerting/SKILL.md",
        "skills/obs-alerting/references/burn-rate.md",
        "skills/obs-alerting/references/grafana-alerting.md",
        "skills/stack-profile/SKILL.md",
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
    ],
    "Build a backend change": [
        "agents/software-engineer.md",
        "skills/backend-craft/SKILL.md",
        "skills/stack-profile/references/application-and-data-stack.md",
        "skills/production-change-gate/SKILL.md",
    ],
}
TASK_BUDGETS: dict[str, int] = {
    "PCF incident, human path": 64_000,
    "PCF incident, sre-assistant agent path": 94_000,
    "Noisy alert": 44_000,
    "Write a runbook": 41_000,
    "Audit a service": 39_000,
    "Build a backend change": 45_000,
}
DESCRIPTION_TASK = "Always-loaded descriptions"
DESCRIPTION_BUDGET = 17_000


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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
