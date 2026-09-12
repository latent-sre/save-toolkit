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

# Byte budgets per canonical task, set to measured usage plus 5% and rounded up to the next 1,000.
# Raising one is a reviewed decision made in the same diff that earns it, not a side effect of an
# unrelated change.
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
TASK_FILES: dict[str, list[str]] = {
    "PCF incident, human path": [
        "skills/incident-investigation/SKILL.md",
        "skills/incident-investigation/references/symptom-investigation.md",
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
    "PCF incident, human path": 77_000,
    "PCF incident, sre-assistant agent path": 76_000,
    "Noisy alert": 44_000,
    "Write a runbook": 41_000,
    "Audit a service": 39_000,
    # Python craft adds its short entrypoint and conditional writing depth to the existing
    # FastAPI task. Its new skill-body weight is budgeted in weights.json; deeper references
    # remain conditional and are bounded here, including automated refactoring/migration.
    "FastAPI upstream change": 61_000,
    # These task paths include choosing the development environment as well as the scoped
    # transformation; the added uv/interpreter depth is conditional elsewhere.
    "Python automated refactor": 63_000,
    "Python library migration": 63_000,
    "Existing UI change": 47_000,
    "Greenfield UI": 53_000,
    "Prepare FastAPI release": 73_000,
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
