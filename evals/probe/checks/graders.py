"""The fleet graders a scenario runs as a check, including the paid rubric judge."""

from __future__ import annotations

from typing import Any

import graders as fleet_graders

from ..outcomes import Outcome, Polarity
from . import registry
from .registry import Context, Need, Params


def _grader_polarity(params: Params) -> Polarity:
    return registry.grader_traits(params.get("name")).polarity


def _grader_needs(params: Params, _spec: Params) -> frozenset[Need]:
    return registry.grader_traits(params.get("name")).needs


def fleet_grader_spec(p: Params) -> dict[str, Any]:
    """The grader configuration a `fleet_grader` check runs, which validation also tries on an empty
    response: the check's other keys are the grader's arguments."""
    kwargs = {k: v for k, v in p.items() if k not in ("check", "name", "text")}
    if p["name"] == "rubric":
        # `rubric`'s own identity kwarg is also called `name`, which this config already spends on
        # the registered grader TYPE ("rubric"). Spell the rubric identity `rubric_name` here and
        # translate it to the `name` kwarg `graders.rubric()` expects.
        kwargs["name"] = kwargs.pop("rubric_name")
    return {"type": p["name"], **kwargs}


@registry.declare("fleet_grader", _grader_polarity, needs=_grader_needs, required=("name",), optional=None)
def check_fleet_grader(ctx: Context, p: Params) -> Outcome:
    """Run one of the fleet's registered response graders (evals/graders.py) on the final text."""
    name = p["name"]
    if name not in fleet_graders.REGISTRY:  # validation rejects this; reaching it is a harness defect
        raise ValueError(f"unknown fleet grader {name!r}")
    passed, detail = fleet_graders.run_grader(
        fleet_grader_spec(p), ctx.trace.result_text, judge_binding=ctx.judge_binding
    )
    return Outcome.read(passed, detail)
