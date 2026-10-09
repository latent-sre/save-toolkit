"""What one attempt cost, and the v1 result record it publishes (EVAL-012 DEC-22).

`RecordV1` is the record's contract: every write, the first and each later change, validates the
record against it strictly, as the JSON its readers parse, and
docs/fleet-evaluation/eval-record-v1.schema.json is generated from it (`build_probe.py schema`), so the
published schema and the records cannot drift apart. Unknown values stay null; a record never fills a
fact from the computer writing it.
"""

from __future__ import annotations

import datetime
import enum
import json
import math
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Annotated, Any, Literal, cast, get_args

from pydantic import BaseModel, ConfigDict, Field, NonNegativeFloat, NonNegativeInt, PositiveInt, model_validator

from . import fingerprints
from .outcomes import EVIDENCE_LIMIT, UNMEASURED, Ending, Polarity, State, Stop


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
    known = round(math.fsum(priced), 6)  # a float even with no call, as the record writes it
    return {
        "calls": len(calls),
        **({"records": calls} if calls else {}),
        "cost_usd": None if unknown else known,
        "known_cost_usd": known,
        "unknown_cost_calls": unknown,
        "live_calls": sum(1 for c in calls if not c.get("cached")),
        "cached_calls": sum(1 for c in calls if c.get("cached")),
        "seconds": round(sum(float(c.get("seconds") or 0.0) for c in calls), 3),
    }


def utc_now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")


class _Section(BaseModel):
    # Strict: a value is checked as the JSON a reader parses, never coerced into place.
    model_config = ConfigDict(extra="forbid", strict=True)


Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
UtcTime = Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|\+00:00)$")]
# A path inside the attempt folder: relative, forward slashes, and no segment that starts with a dot.
InsidePath = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-][A-Za-z0-9_.-]*(/[A-Za-z0-9_-][A-Za-z0-9_.-]*)*$")]


class RecordFormat(_Section):
    name: Literal["save-toolkit.eval-record"]
    version: Literal[1]


# The one format this runner writes, as its readers check it before validating: read from the model.
RECORD_FORMAT = {field: get_args(info.annotation)[0] for field, info in RecordFormat.model_fields.items()}


class Case(_Section):
    id: str
    case_sha256: Sha256 = Field(description="The case alone: scenario, oracle bytes and rubrics, without the runner.")
    scenario_sha256: Sha256 | None = Field(description="The case bound to the runner, Python and judge that graded it.")


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
    turn_limit: PositiveInt | None
    wall_clock_seconds: PositiveInt


class AttemptState(enum.StrEnum):
    """Where an attempt stands: the slot's published run, one a later attempt replaced, or one that
    raised before it published (threat-model ADR result rule 7)."""

    FINAL = "final"
    SUPERSEDED = "superseded"
    INCOMPLETE = "incomplete"


class Attempt(_Section):
    label: str
    slot: PositiveInt
    number: PositiveInt
    state: AttemptState
    started_at: UtcTime
    ended_at: UtcTime
    reason: str | None = None


class RunEnd(_Section):
    kind: Ending = Field(description="How execution ended, independent of what the checks found.")
    stop: Stop | None = Field(description="How a run cut short stopped.")
    reason: str | None

    @model_validator(mode="after")
    def _stop_only_when_cut(self) -> RunEnd:
        if (self.stop is not None) != (self.kind is Ending.CUT_SHORT):
            raise ValueError("a stop is recorded exactly when the run was cut short")
        return self


class Check(_Section):
    id: str
    text: str
    kind: Polarity
    state: State
    reason: str | None = Field(description="Why an INCONCLUSIVE check could not measure; null for PASS and FAIL.")
    evidence: str = Field(max_length=EVIDENCE_LIMIT)
    evidence_truncated: bool

    @model_validator(mode="after")
    def _reason_only_when_unmeasured(self) -> Check:
        if (self.reason is not None) != (self.state is State.INCONCLUSIVE):
            raise ValueError("a check carries a reason exactly when it is INCONCLUSIVE")
        return self


class Verdict(_Section):
    status: State | None = Field(description="Null for an incomplete attempt: never a guessed verdict.")
    reason: str | None
    assessment_revision: Literal[0] = Field(description="The original assessment; later ones are `assessments`.")
    after_assessment: str | None


class Cost(_Section):
    trial_usd: NonNegativeFloat | None
    judge_usd: NonNegativeFloat | None
    known_usd: NonNegativeFloat | None
    complete: bool | None
    judge_calls: NonNegativeInt | None
    judge_live_calls: NonNegativeInt | None
    judge_cached_calls: NonNegativeInt | None
    judge_unknown_cost_calls: NonNegativeInt | None

    @model_validator(mode="after")
    def _complete_only_when_every_part_is_known(self) -> Cost:
        if self.complete and (self.trial_usd is None or self.judge_usd is None):
            raise ValueError("a cost is complete only when the trial and judge costs are both known")
        return self


class AssessmentEntry(_Section):
    revision: PositiveInt
    status: State
    reason: str | None
    grading: InsidePath
    runner_source_sha256: Sha256
    assessed_at: UtcTime


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
    evidence: dict[InsidePath, InsidePath] = Field(
        description="Evidence files, by path relative to the attempt folder."
    )
    assessments: list[AssessmentEntry] = Field(
        default_factory=list, description="Each later regrade, beside the original verdict."
    )

    @model_validator(mode="after")
    def _consistent(self) -> RecordV1:
        incomplete = self.attempt.state is AttemptState.INCOMPLETE
        if incomplete != (self.run_end.kind is Ending.INCOMPLETE) or incomplete != (self.verdict.status is None):
            raise ValueError("an incomplete attempt, and only one, ends incomplete and has no verdict")
        if [entry.revision for entry in self.assessments] != list(range(1, len(self.assessments) + 1)):
            raise ValueError("assessment revisions count up from 1")
        return self


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
    incomplete: str | None = None,
) -> dict[str, Any]:
    """The v1 result record (docs/fleet-evaluation/contracts.md#result-record-v1) for one attempt.

    It maps facts the attempt's own files already hold, so a record refused here can be written again
    from them once the runner is fixed; unknown values stay null, never filled from the computer
    writing it, and evidence paths are relative to the attempt folder. `incomplete` is why an attempt
    that raised before it was graded ended; such an attempt has no verdict.
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
    raised = incomplete is not None
    ended = (
        Ending.VOID
        if grading.get("void")
        else grading["run_end"]
        if grading.get("run_end") in (Ending.CUT_SHORT, Ending.TURN_LIMIT)
        else Ending.COMPLETED
    )
    fields = {
        "format": RECORD_FORMAT,
        "case": {
            "id": spec["id"],
            "case_sha256": fingerprints.case_digest(spec),
            "scenario_sha256": grading.get("scenario_sha256"),
        },
        "candidate": {key: provenance.get(key) for key in Candidate.model_fields},
        "runner": {key: provenance.get(key) for key in Runner.model_fields},
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
            "state": AttemptState.INCOMPLETE if raised else AttemptState.FINAL,
            "started_at": started_at,
            "ended_at": utc_now(),
        },
        "run_end": (
            {"kind": Ending.INCOMPLETE, "stop": None, "reason": incomplete}
            if raised
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
                "reason": str(e.get("evidence")).removeprefix(UNMEASURED)
                if e.get("state") == State.INCONCLUSIVE
                else None,
                "evidence": e.get("evidence"),
                "evidence_truncated": bool(e.get("evidence_truncated")),
            }
            for e in grading.get("expectations") or []
        ],
        "verdict": {
            "status": None if raised else grading.get("status"),
            "reason": None if raised else grading.get("inconclusive") or grading.get("unmeasured"),
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
    return _store(run_dir / "record.json", fields)


def update_record(run_dir: Path, change: Callable[[dict[str, Any]], object]) -> None:
    """Change an attempt's record through the validation that wrote it. The verdict already stands, so
    a change the contract refuses is reported and left unwritten, never raised (result rule 6)."""
    path = run_dir / "record.json"
    if not path.is_file():
        return
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        change(record)
        _store(path, record)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        print(f"warning: {path} was not updated: {exc}", file=sys.stderr)


def _store(path: Path, fields: Mapping[str, Any]) -> dict[str, Any]:
    """Write a record only once it validates, as the JSON its readers parse."""
    record = RecordV1.model_validate_json(json.dumps(fields)).model_dump(mode="json", exclude_unset=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return record
