"""What one attempt cost, and the v1 result record it publishes (EVAL-012 DEC-22).

`RecordV1` is the record's contract: `write_record` validates every record against it before writing,
and docs/fleet-evaluation/eval-record-v1.schema.json is generated from it (`build_probe.py schema`),
so the published schema and the records cannot drift apart. Unknown values stay null; a record never
fills a fact from the computer writing it.
"""

from __future__ import annotations

import datetime
import json
import math
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from . import fingerprints
from .outcomes import Polarity, State, Stop


def known_usd(value: object) -> float | None:
    """A reported cost, or None when it is missing, not a number, infinite, NaN or negative."""
    if type(value) not in (int, float):  # exactly a number: a bool or a float subclass is not a reported cost
        return None
    number = cast(float, value)
    return float(number) if math.isfinite(number) and number >= 0 else None


def trial_cost(trial_usd: object, judge: dict[str, Any]) -> dict[str, Any]:
    """A trial's spend: the total only when every part is known, with the known floor beside it."""
    known_trial = known_usd(trial_usd)
    known = known_trial is not None and judge["cost_usd"] is not None
    floor = round((known_trial or 0.0) + judge["known_cost_usd"], 6)
    return {"cost_usd": floor if known else None, "known_cost_usd": floor, "cost_complete": known}


def judge_spend() -> dict[str, Any]:
    """Drain and total the judge calls a `rubric` grader spent inside this trial's grading.

    A rubric grader launches a second paid Claude process. Its cost and duration are in neither the
    graded trial's trace nor the elapsed time measured around it, so candidate-budget and
    incumbent/candidate comparisons understate every judged scenario until this is added back.
    The runner imports the judge to bind its implementation; unjudged batches record zero calls.
    """
    drain = getattr(sys.modules.get("judge"), "drain_spend", None)
    calls = list(drain()) if callable(drain) else []
    # A cached verdict is a known zero; a live call whose cost was not reported stays unknown.
    priced = [cost for cost in (known_usd(c.get("cost_usd")) for c in calls) if cost is not None]
    unknown = len(calls) - len(priced)
    return {
        "calls": len(calls),
        **({"records": calls} if calls else {}),
        "cost_usd": None if unknown else round(sum(priced), 6),
        "known_cost_usd": round(sum(priced), 6),
        "unknown_cost_calls": unknown,
        "live_calls": sum(1 for c in calls if not c.get("cached")),
        "cached_calls": sum(1 for c in calls if c.get("cached")),
        "seconds": round(sum(float(c.get("seconds") or 0.0) for c in calls), 3),
    }


def utc_now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")


RECORD_FORMAT = {"name": "save-toolkit.eval-record", "version": 1}


class _Section(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RecordFormat(_Section):
    name: Literal["save-toolkit.eval-record"]
    version: Literal[1]


class Case(_Section):
    id: str
    case_sha256: str = Field(description="The case alone: scenario, oracle bytes and rubrics, without the runner.")
    scenario_sha256: str | None = Field(description="The case bound to the runner, Python and judge that graded it.")


class Candidate(_Section):
    plugin_root: str | None
    plugin_commit: str | None
    plugin_inputs_dirty: bool | None
    plugin_source_sha256: str | None


class Runner(_Section):
    runner_commit: str | None
    runner_source_dirty: bool | None
    runner_source_sha256: str | None


class Runtime(_Section):
    cli_version: str | None
    host_platform: dict[str, str]


class Conditions(_Section):
    requested_model: str | None
    observed_models: list[str] | None
    runtime: Runtime | None
    turn_limit: int | None
    wall_clock_seconds: int


class Attempt(_Section):
    label: str
    slot: int
    number: int
    state: Literal["final", "superseded", "incomplete"]
    started_at: str
    ended_at: str
    reason: str | None = None


class RunEnd(_Section):
    kind: Literal["completed", "turn_limit", "cut_short", "void", "incomplete"] = Field(
        description="How execution ended, independent of what the checks found."
    )
    stop: Stop | None = Field(description="How a run cut short stopped.")
    reason: str | None


class Check(_Section):
    id: str | None
    text: str | None
    kind: Polarity | None
    state: State | None
    evidence: str | None
    evidence_truncated: bool


class Verdict(_Section):
    status: State | None = Field(description="Null for an incomplete attempt: never a guessed verdict.")
    reason: str | None
    assessment_revision: int
    after_assessment: str | None


class Cost(_Section):
    trial_usd: float | None
    judge_usd: float | None
    known_usd: float | None
    complete: bool | None
    judge_calls: int | None
    judge_live_calls: int | None
    judge_cached_calls: int | None
    judge_unknown_cost_calls: int | None


class AssessmentEntry(_Section):
    revision: int
    status: State
    reason: str | None
    grading: str
    runner_source_sha256: str
    assessed_at: str


class RecordV1(_Section):
    """One eval attempt's result record, version 1 (docs/fleet-evaluation/contracts.md)."""

    model_config = ConfigDict(extra="forbid", title="save-toolkit eval record, v1")

    format: RecordFormat
    case: Case
    candidate: Candidate
    runner: Runner
    conditions: Conditions
    attempt: Attempt
    run_end: RunEnd
    checks: list[Check]
    verdict: Verdict
    cost: Cost
    evidence: dict[str, str] = Field(description="Evidence files, by path relative to the attempt folder.")
    assessments: list[AssessmentEntry] = Field(
        default_factory=list, description="Each later regrade, beside the original verdict."
    )


def record_schema() -> dict[str, Any]:
    """The JSON Schema of the v1 record, as published for its readers."""
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", **RecordV1.model_json_schema()}


def write_record(
    run_dir: Path,
    spec: Mapping[str, Any],
    *,
    label: str,
    run_number: int,
    attempt: int,
    started_at: str,
    model: str | None,
    timeout: int,
    end: tuple[str, str | None] | None = None,
) -> dict[str, Any]:
    """The v1 result record (docs/fleet-evaluation/contracts.md#result-record-v1) for one attempt.

    It maps facts the attempt's own files already hold; unknown values stay null, never filled from
    the computer writing it, and evidence paths are relative to the attempt folder.
    """

    def read(name: str) -> dict[str, Any]:
        try:
            value = json.loads((run_dir / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return value if isinstance(value, dict) else {}

    grading, timing, provenance = read("grading.json"), read("timing.json"), read("provenance.json")
    summary = read("outputs/trace-summary.json")
    judge = timing.get("judge") or {}
    ended = (
        "void"
        if grading.get("void")
        else grading["run_end"]
        if grading.get("run_end") in ("cut_short", "turn_limit")
        else "completed"
    )
    fields = {
        "format": RECORD_FORMAT,
        "case": {
            "id": spec["id"],
            "case_sha256": fingerprints.case_digest(spec),
            "scenario_sha256": grading.get("scenario_sha256"),
        },
        "candidate": {
            key: provenance.get(key)
            for key in ("plugin_root", "plugin_commit", "plugin_inputs_dirty", "plugin_source_sha256")
        },
        "runner": {
            key: provenance.get(key) for key in ("runner_commit", "runner_source_dirty", "runner_source_sha256")
        },
        "conditions": {
            "requested_model": model,
            "observed_models": summary.get("models"),
            "runtime": provenance.get("runtime"),
            "turn_limit": spec.get("max_turns"),
            "wall_clock_seconds": timeout,
        },
        "attempt": {
            "label": label,
            "slot": run_number,
            "number": attempt,
            "state": "incomplete" if end and end[0] == "incomplete" else "final",
            "started_at": started_at,
            "ended_at": utc_now(),
        },
        "run_end": (
            {"kind": end[0], "stop": None, "reason": end[1]}
            if end
            else {
                "kind": ended,
                "stop": grading.get("run_stop"),
                "reason": grading.get("void") or grading.get("inconclusive") or grading.get("unmeasured"),
            }
        ),
        "checks": [
            {
                "id": e.get("id"),
                "text": e.get("text"),
                "kind": e.get("kind"),
                "state": e.get("state"),
                "evidence": e.get("evidence"),
                "evidence_truncated": bool(e.get("evidence_truncated")),
            }
            for e in grading.get("expectations") or []
        ],
        "verdict": {
            "status": grading.get("status"),
            "reason": grading.get("inconclusive") or grading.get("unmeasured"),
            "assessment_revision": 0,
            "after_assessment": grading.get("after_assessment"),
        },
        "cost": {
            "trial_usd": timing.get("trial_cost_usd"),
            "judge_usd": judge.get("cost_usd"),
            "known_usd": timing.get("known_cost_usd"),
            "complete": timing.get("cost_complete"),
            "judge_calls": judge.get("calls"),
            "judge_live_calls": judge.get("live_calls"),
            "judge_cached_calls": judge.get("cached_calls"),
            "judge_unknown_cost_calls": judge.get("unknown_cost_calls"),
        },
        "evidence": {
            name: name
            for name in (
                "outputs/response.md",
                "stdout.jsonl",
                "outputs/workspace.patch",
                "grading.json",
                "timing.json",
                "provenance.json",
            )
            if (run_dir / name).is_file()
        },
    }
    record = RecordV1.model_validate(fields).model_dump(mode="json", exclude_unset=True)
    (run_dir / "record.json").write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return record
