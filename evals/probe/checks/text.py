"""Checks of the final text."""

from __future__ import annotations

import re

import graders as fleet_graders
from itbench_submission import collect_submission

from ..outcomes import Outcome, Polarity, verdict
from . import registry
from .registry import Context, Need, Params


@registry.declare("text_regex", Polarity.REQUIRES, needs={Need.TEXT}, required=("pattern",), kind=registry.Kind.CHECK)
def check_text_regex(ctx: Context, p: Params) -> Outcome:
    m = re.search(p["pattern"], ctx.trace.result_text, re.IGNORECASE | re.MULTILINE)
    return verdict(m is not None, f"/{p['pattern'][:80]}/ {'matched ' + repr(m.group(0)[:80]) if m else 'no match'}")


@registry.declare(
    "text_not_regex", Polarity.FORBIDS, needs={Need.TEXT}, required=("pattern",), kind=registry.Kind.CHECK
)
def check_text_not_regex(ctx: Context, p: Params) -> Outcome:
    m = re.search(p["pattern"], ctx.trace.result_text, re.IGNORECASE | re.MULTILINE)
    return verdict(m is None, f"/{p['pattern'][:80]}/ {'matched ' + repr(m.group(0)[:80]) if m else 'absent (good)'}")


@registry.declare("text_contains_any", Polarity.REQUIRES, needs={Need.TEXT}, required=("of",), kind=registry.Kind.CHECK)
def check_text_contains_any(ctx: Context, p: Params) -> Outcome:
    """The fleet's `contains_any` grader, as a build check: any one of the strings, case-insensitively."""
    return verdict(*fleet_graders.contains_any(ctx.trace.result_text, p["of"]))


@registry.declare(
    "text_not_contains", Polarity.FORBIDS, needs={Need.TEXT}, required=("needle",), kind=registry.Kind.CHECK
)
def check_text_not_contains(ctx: Context, p: Params) -> Outcome:
    ok = p["needle"].lower() not in ctx.trace.result_text.lower()
    return verdict(ok, f"{p['needle']!r} {'absent (good)' if ok else 'PRESENT in the final text'}")


@registry.declare(
    "wp04_submission_v1", Polarity.REQUIRES, needs={Need.TEXT}, required=("case_id",), kind=registry.Kind.CHECK
)
def check_wp04_submission_v1(ctx: Context, p: Params) -> Outcome:
    """Validate the structured submission only; it makes no operational-semantic judgment."""
    try:
        collect_submission(ctx.trace.result_text, p["case_id"])
    except ValueError as exc:
        return verdict(False, f"invalid WP04 submission: {exc}")
    return verdict(True, "one strict JSON submission matches the selected case and entity/edge schema")
