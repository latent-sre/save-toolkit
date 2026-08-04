#!/usr/bin/env python3
"""Starter skeleton for an ops CLI — copy and adapt. Embodies the ops-tooling rules.

Demonstrates: distinct exit codes, result-on-stdout / logs-on-stderr, --json,
a real --dry-run (decision separated from effect), confirm-before-destruct,
and secrets-from-env (never a flag). Requires: typer (`uv add typer`).
"""
from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass, asdict
from enum import IntEnum

import typer

# Logs/progress/diagnostics go to STDERR so stdout stays pipeable (`| jq`).
logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(levelname)s %(message)s")
log = logging.getLogger("opstool")

app = typer.Typer(add_completion=False, help="Example ops tool.")


class Exit(IntEnum):
    OK = 0
    USAGE = 2          # bad invocation / args
    NOT_FOUND = 3      # target resource missing
    UPSTREAM = 4       # a dependency (cf/Splunk/...) failed — report the upstream boundary
    # ... document every code you add; CI branches on them.


@dataclass(frozen=True)
class Plan:
    """The DECISION — pure, testable, side-effect-free."""
    app_name: str
    target_instances: int


def decide(app_name: str, want: int) -> Plan:
    return Plan(app_name=app_name, target_instances=want)


def apply(plan: Plan) -> None:
    """The EFFECT — the only place that mutates state. Kept thin on purpose."""
    log.info("scaling %s -> %d instances", plan.app_name, plan.target_instances)
    # e.g. ops_stack.cf_scale(plan.app_name, plan.target_instances)  # timeouts/retries live there


@app.command()
def scale(
    app_name: str,
    instances: int = typer.Argument(..., min=1),
    dry_run: bool = typer.Option(False, "--dry-run", help="Compute the plan; change nothing."),
    yes: bool = typer.Option(False, "--yes", help="Skip the confirmation prompt."),
    as_json: bool = typer.Option(False, "--json", help="Emit the result as JSON on stdout."),
) -> None:
    """Scale an app. Secrets come from env (e.g. CF_TOKEN), never a flag."""
    if not os.getenv("CF_TOKEN"):
        log.error("CF_TOKEN not set in the environment")
        raise typer.Exit(Exit.USAGE)

    plan = decide(app_name, instances)

    if dry_run:
        _emit(plan, as_json, dry_run=True)        # dry-run calls NOTHING (prove it in a test)
        raise typer.Exit(Exit.OK)
    if not yes and not typer.confirm(f"Scale {plan.app_name} to {plan.target_instances}?"):
        raise typer.Exit(Exit.OK)

    apply(plan)                                   # idempotent: re-running converges
    _emit(plan, as_json, dry_run=False)
    raise typer.Exit(Exit.OK)


def _emit(plan: Plan, as_json: bool, *, dry_run: bool) -> None:
    if as_json:                                   # stable shape — version before changing
        print(json.dumps({**asdict(plan), "dry_run": dry_run}))
    else:
        prefix = "[dry-run] would scale" if dry_run else "scaled"
        print(f"{prefix} {plan.app_name} to {plan.target_instances}")


if __name__ == "__main__":
    app()
