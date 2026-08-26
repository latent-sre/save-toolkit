"""Claim registry, evidence validation, and comparison for multi-engine evals."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Mapping, Sequence


SCHEMA_VERSION = "eval-result-envelope/v1"
VERDICTS = {"PASS", "FAIL", "INCONCLUSIVE"}
CLAIM_TYPES = frozenset(
    {
        "candidate_snapshot_integrity",
        "native_plugin_loaded",
        "native_component_invoked",
        "advertised_tool_inventory",
        "callable_tool_boundary",
        "reference_used",
        "behavioral_contract",
        "deterministic_grader_result",
        "cross_engine_divergence",
    }
)
ENGINE_CLAIMS = {
    "claude-plugin": frozenset(
        {
            "candidate_snapshot_integrity",
            "native_plugin_loaded",
            "native_component_invoked",
            "advertised_tool_inventory",
            "callable_tool_boundary",
            "reference_used",
            "behavioral_contract",
            "deterministic_grader_result",
        }
    ),
    "codex-cli": frozenset(
        {
            "candidate_snapshot_integrity",
            "reference_used",
            "behavioral_contract",
            "deterministic_grader_result",
        }
    ),
}
TOP_LEVEL_FIELDS = {
    "schema_version",
    "run_id",
    "engine",
    "candidate",
    "artifacts",
    "digests",
    "canaries",
    "claims_requested",
    "claims_supported",
    "scenarios",
    "verdict",
    "timing",
    "cost",
    "trace",
    "promotion_eligible",
    "limitations",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SCENARIO_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CANARY_RE = re.compile(r"^[a-z][a-z0-9_]{5,63}$")
RFC3339_UTC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)


class ContractError(ValueError):
    """An eval profile, result envelope, or comparison violated the contract."""


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{field} must be an object")
    return value


def _exact_fields(value: Mapping[str, object], expected: set[str], field: str) -> None:
    missing = expected - set(value)
    unknown = set(value) - expected
    if missing:
        raise ContractError(f"{field} missing fields: {sorted(missing)}")
    if unknown:
        raise ContractError(f"{field} has unknown fields: {sorted(unknown)}")


def _string(value: object, field: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field} must be a non-empty string")
    return value


def _digest(value: object, field: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise ContractError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _strings(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ContractError(f"{field} must be a string list")
    if len(value) != len(set(value)):
        raise ContractError(f"{field} must not contain duplicates")
    return value


def _limitations(value: object, field: str) -> None:
    values = _strings(value, field)
    if any(len(item) > 600 for item in values):
        raise ContractError(f"{field} entries are limited to 600 characters")


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or RFC3339_UTC_RE.fullmatch(value) is None:
        raise ContractError(f"{field} must be an RFC3339 UTC timestamp ending in Z")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00").astimezone(timezone.utc)
    except ValueError as exc:
        raise ContractError(f"{field} is not a valid timestamp") from exc


def validate_claim_request(engine: str, requested: Sequence[str]) -> None:
    if engine not in ENGINE_CLAIMS:
        raise ContractError(f"unknown eval engine {engine!r}")
    if not requested:
        raise ContractError("at least one claim must be requested")
    unknown = set(requested) - CLAIM_TYPES
    if unknown:
        raise ContractError(f"unknown claim type(s): {sorted(unknown)}")
    unsupported = set(requested) - ENGINE_CLAIMS[engine]
    if unsupported:
        raise ContractError(f"{engine} requested unsupported claim(s): {sorted(unsupported)}")
    if len(requested) != len(set(requested)):
        raise ContractError("requested claims must not contain duplicates")


def _validate_artifact(value: object, field: str) -> tuple[bool, str | None]:
    artifact = _mapping(value, field)
    _exact_fields(artifact, {"applicable", "sha256"}, field)
    applicable = artifact["applicable"]
    if not isinstance(applicable, bool):
        raise ContractError(f"{field}.applicable must be boolean")
    digest = _digest(artifact["sha256"], f"{field}.sha256", nullable=True)
    if applicable != (digest is not None):
        raise ContractError(f"{field} applicability and digest disagree")
    return applicable, digest


def _validate_claim(
    value: object,
    field: str,
    *,
    requested: set[str],
    supported: set[str],
) -> tuple[str, str]:
    claim = _mapping(value, field)
    _exact_fields(claim, {"type", "status", "evidence", "limitations"}, field)
    claim_type = _string(claim["type"], f"{field}.type")
    if claim_type not in CLAIM_TYPES:
        raise ContractError(f"{field} has unknown claim type {claim_type!r}")
    if claim_type not in supported or claim_type not in requested:
        raise ContractError(f"{field} emitted unsupported claim {claim_type!r}")
    status = _string(claim["status"], f"{field}.status")
    if status not in VERDICTS:
        raise ContractError(f"{field}.status must be one of {sorted(VERDICTS)}")
    evidence = claim["evidence"]
    if not isinstance(evidence, list) or not evidence:
        raise ContractError(f"{field}.evidence must be a non-empty digest list")
    for index, digest in enumerate(evidence):
        _digest(digest, f"{field}.evidence[{index}]")
    if len(evidence) != len(set(evidence)):
        raise ContractError(f"{field}.evidence must not contain duplicates")
    _limitations(claim["limitations"], f"{field}.limitations")
    return claim_type, status


def _aggregate(states: Sequence[str]) -> str:
    if "FAIL" in states:
        return "FAIL"
    if "INCONCLUSIVE" in states:
        return "INCONCLUSIVE"
    return "PASS"


def validate_envelope(envelope: object) -> None:
    value = _mapping(envelope, "envelope")
    _exact_fields(value, TOP_LEVEL_FIELDS, "envelope")
    if value["schema_version"] != SCHEMA_VERSION:
        raise ContractError(f"schema_version must be {SCHEMA_VERSION!r}")
    run_id = _string(value["run_id"], "run_id")
    if RUN_ID_RE.fullmatch(run_id) is None:
        raise ContractError("run_id is not a safe bounded identifier")

    engine = _mapping(value["engine"], "engine")
    _exact_fields(
        engine,
        {
            "name",
            "adapter_version",
            "runtime_version",
            "requested_model",
            "resolved_model",
            "auth_mode",
        },
        "engine",
    )
    engine_name = _string(engine["name"], "engine.name")
    if engine_name not in ENGINE_CLAIMS:
        raise ContractError(f"unknown eval engine {engine_name!r}")
    _string(engine["adapter_version"], "engine.adapter_version")
    _string(engine["runtime_version"], "engine.runtime_version")
    _string(engine["requested_model"], "engine.requested_model", nullable=True)
    resolved_model = _string(engine["resolved_model"], "engine.resolved_model", nullable=True)
    if engine["auth_mode"] != "subscriber_session":
        raise ContractError("engine.auth_mode must be subscriber_session")

    candidate = _mapping(value["candidate"], "candidate")
    _exact_fields(candidate, {"git_sha", "clean", "input_sha256"}, "candidate")
    if not isinstance(candidate["git_sha"], str) or GIT_SHA_RE.fullmatch(candidate["git_sha"]) is None:
        raise ContractError("candidate.git_sha must be a full lowercase Git SHA")
    if not isinstance(candidate["clean"], bool):
        raise ContractError("candidate.clean must be boolean")
    _digest(candidate["input_sha256"], "candidate.input_sha256")

    artifacts = _mapping(value["artifacts"], "artifacts")
    _exact_fields(artifacts, {"plugin_snapshot", "resolved_context"}, "artifacts")
    plugin_applicable, plugin_digest = _validate_artifact(
        artifacts["plugin_snapshot"], "artifacts.plugin_snapshot"
    )
    context_applicable, _ = _validate_artifact(
        artifacts["resolved_context"], "artifacts.resolved_context"
    )
    expected_artifacts = {
        "claude-plugin": (True, False),
        "codex-cli": (False, True),
    }[engine_name]
    if (plugin_applicable, context_applicable) != expected_artifacts:
        raise ContractError(
            f"{engine_name} plugin_snapshot/resolved_context applicability is invalid"
        )
    if engine_name == "claude-plugin" and plugin_digest != candidate["input_sha256"]:
        raise ContractError("candidate input digest and plugin snapshot digest disagree")

    digests = _mapping(value["digests"], "digests")
    _exact_fields(
        digests,
        {"scenario_suite", "graders", "execution_profile", "comparison", "policy"},
        "digests",
    )
    for name in ("scenario_suite", "graders", "execution_profile", "comparison"):
        _digest(digests[name], f"digests.{name}")
    policy_digest = _digest(digests["policy"], "digests.policy", nullable=True)

    requested = _strings(value["claims_requested"], "claims_requested")
    validate_claim_request(engine_name, requested)
    supported = _strings(value["claims_supported"], "claims_supported")
    if set(supported) != set(ENGINE_CLAIMS[engine_name]):
        raise ContractError("claims_supported must exactly match the registered engine ceiling")
    requested_set = set(requested)
    supported_set = set(supported)

    scenarios = value["scenarios"]
    if not isinstance(scenarios, list) or not scenarios:
        raise ContractError("scenarios must be a non-empty list")
    scenario_ids: set[str] = set()
    scenario_verdicts: list[str] = []
    emitted_types: set[str] = set()
    for index, raw_scenario in enumerate(scenarios):
        field = f"scenarios[{index}]"
        scenario = _mapping(raw_scenario, field)
        _exact_fields(scenario, {"id", "sha256", "verdict", "claims"}, field)
        scenario_id = _string(scenario["id"], f"{field}.id")
        if SCENARIO_ID_RE.fullmatch(scenario_id) is None or scenario_id in scenario_ids:
            raise ContractError(f"{field}.id must be a unique canonical scenario slug")
        scenario_ids.add(scenario_id)
        _digest(scenario["sha256"], f"{field}.sha256")
        verdict = _string(scenario["verdict"], f"{field}.verdict")
        if verdict not in VERDICTS:
            raise ContractError(f"{field}.verdict must be one of {sorted(VERDICTS)}")
        claims = scenario["claims"]
        if not isinstance(claims, list) or not claims:
            raise ContractError(f"{field}.claims must be a non-empty list")
        claim_types: set[str] = set()
        claim_states: list[str] = []
        for claim_index, claim in enumerate(claims):
            claim_type, claim_state = _validate_claim(
                claim,
                f"{field}.claims[{claim_index}]",
                requested=requested_set,
                supported=supported_set,
            )
            if claim_type in claim_types:
                raise ContractError(f"{field}.claims contains duplicate claim {claim_type!r}")
            claim_types.add(claim_type)
            emitted_types.add(claim_type)
            claim_states.append(claim_state)
        if verdict != _aggregate(claim_states):
            raise ContractError(f"{field}.verdict disagrees with its claim statuses")
        scenario_verdicts.append(verdict)
    if emitted_types != requested_set:
        raise ContractError("every requested claim must be emitted by at least one scenario")

    canaries = value["canaries"]
    if not isinstance(canaries, list):
        raise ContractError("canaries must be a list")
    canary_keys: set[tuple[str, str]] = set()
    bad_canary = False
    canary_scenarios: set[str] = set()
    for index, raw_canary in enumerate(canaries):
        field = f"canaries[{index}]"
        canary = _mapping(raw_canary, field)
        _exact_fields(
            canary,
            {"scenario_id", "path", "expected", "observed", "status"},
            field,
        )
        scenario_id = _string(canary["scenario_id"], f"{field}.scenario_id")
        if scenario_id not in scenario_ids:
            raise ContractError(f"{field}.scenario_id does not name an envelope scenario")
        path = _string(canary["path"], f"{field}.path")
        if path.startswith(("/", "\\")) or ".." in path.replace("\\", "/").split("/"):
            raise ContractError(f"{field}.path must be a safe relative path")
        expected = _string(canary["expected"], f"{field}.expected")
        if CANARY_RE.fullmatch(expected) is None:
            raise ContractError(f"{field}.expected is not a canonical canary token")
        observed = _string(canary["observed"], f"{field}.observed", nullable=True)
        status = canary["status"]
        if status not in {"PASS", "FAIL", "MISSING"}:
            raise ContractError(f"{field}.status must be PASS, FAIL, or MISSING")
        if status == "PASS" and observed != expected:
            raise ContractError(f"{field} PASS canary does not match its expected token")
        if status == "MISSING" and observed is not None:
            raise ContractError(f"{field} MISSING canary must have no observed token")
        key = (scenario_id, path)
        if key in canary_keys:
            raise ContractError(f"duplicate canary path for scenario: {key}")
        canary_keys.add(key)
        canary_scenarios.add(scenario_id)
        bad_canary = bad_canary or status != "PASS"
    if "reference_used" in emitted_types and not canaries:
        raise ContractError("reference_used claims require reference canary evidence")

    verdict = value["verdict"]
    if verdict not in VERDICTS:
        raise ContractError(f"verdict must be one of {sorted(VERDICTS)}")
    if verdict != _aggregate(scenario_verdicts):
        raise ContractError("overall verdict disagrees with scenario verdicts")

    timing = _mapping(value["timing"], "timing")
    _exact_fields(timing, {"started_at", "ended_at", "duration_seconds"}, "timing")
    started = _timestamp(timing["started_at"], "timing.started_at")
    ended = _timestamp(timing["ended_at"], "timing.ended_at")
    if ended < started:
        raise ContractError("timing.ended_at cannot precede timing.started_at")
    duration = timing["duration_seconds"]
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration < 0:
        raise ContractError("timing.duration_seconds must be a non-negative number")

    cost = _mapping(value["cost"], "cost")
    _exact_fields(cost, {"status", "amount", "currency", "reason"}, "cost")
    if cost["status"] == "unavailable":
        if cost["amount"] is not None or cost["currency"] is not None:
            raise ContractError("unavailable cost must use null amount and currency, never zero")
        _string(cost["reason"], "cost.reason")
    elif cost["status"] == "available":
        amount = cost["amount"]
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount < 0:
            raise ContractError("available cost amount must be a non-negative number")
        currency = _string(cost["currency"], "cost.currency")
        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise ContractError("cost.currency must be a three-letter uppercase code")
        if cost["reason"] is not None:
            raise ContractError("available cost.reason must be null")
    else:
        raise ContractError("cost.status must be available or unavailable")

    trace = _mapping(value["trace"], "trace")
    _exact_fields(trace, {"complete", "sha256"}, "trace")
    if not isinstance(trace["complete"], bool):
        raise ContractError("trace.complete must be boolean")
    _digest(trace["sha256"], "trace.sha256")
    if (
        not trace["complete"] or resolved_model is None or policy_digest is None
    ) and verdict != "INCONCLUSIVE":
        raise ContractError(
            "incomplete trace, unresolved model, or unobserved policy requires INCONCLUSIVE verdict"
        )
    if bad_canary and verdict != "INCONCLUSIVE":
        raise ContractError("a failed or missing canary requires INCONCLUSIVE verdict")

    promotion_eligible = value["promotion_eligible"]
    if not isinstance(promotion_eligible, bool):
        raise ContractError("promotion_eligible must be boolean")
    if promotion_eligible and not candidate["clean"]:
        raise ContractError("dirty candidate cannot be promotion eligible")
    if promotion_eligible and verdict != "PASS":
        raise ContractError("only a PASS envelope can be promotion eligible")
    _limitations(value["limitations"], "limitations")


def _scenario_index(envelope: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    return {
        str(scenario["id"]): scenario
        for scenario in envelope["scenarios"]  # type: ignore[index]
    }


def _claim_index(scenario: Mapping[str, object]) -> dict[str, str]:
    return {
        str(claim["type"]): str(claim["status"])
        for claim in scenario["claims"]  # type: ignore[index]
    }


def compare_envelopes(left: object, right: object) -> dict[str, object]:
    """Classify comparable engine results without reducing them to one score."""

    validate_envelope(left)
    validate_envelope(right)
    first = _mapping(left, "left")
    second = _mapping(right, "right")
    reasons: list[str] = []
    first_engine = first["engine"]["name"]  # type: ignore[index]
    second_engine = second["engine"]["name"]  # type: ignore[index]
    if first_engine == second_engine:
        reasons.append("comparison requires two different engines")
    for parent, field in (
        ("candidate", "git_sha"),
        ("candidate", "input_sha256"),
        ("digests", "scenario_suite"),
        ("digests", "graders"),
        ("digests", "comparison"),
    ):
        first_value = first[parent][field]  # type: ignore[index]
        second_value = second[parent][field]  # type: ignore[index]
        if first_value != second_value:
            reasons.append(f"{parent}.{field} differs")
    first_scenarios = _scenario_index(first)
    second_scenarios = _scenario_index(second)
    if set(first_scenarios) != set(second_scenarios):
        reasons.append("scenario ids differ")
    else:
        for scenario_id in sorted(first_scenarios):
            if first_scenarios[scenario_id]["sha256"] != second_scenarios[scenario_id]["sha256"]:
                reasons.append(f"scenario digest differs: {scenario_id}")
    if reasons:
        return {
            "classification": "incomparable",
            "engines": [first_engine, second_engine],
            "reasons": reasons,
            "scenarios": [],
        }

    comparisons: list[dict[str, object]] = []
    any_difference = False
    any_gap = False
    for scenario_id in sorted(first_scenarios):
        first_claims = _claim_index(first_scenarios[scenario_id])
        second_claims = _claim_index(second_scenarios[scenario_id])
        shared = sorted(set(first_claims) & set(second_claims))
        if not shared:
            classification = "evidence_gap"
            any_gap = True
        elif any(first_claims[name] != second_claims[name] for name in shared):
            classification = "behavioral_divergence"
            any_difference = True
        elif set(first_claims) != set(second_claims):
            classification = "evidence_gap"
            any_gap = True
        else:
            classification = "agreement"
        comparisons.append(
            {
                "scenario_id": scenario_id,
                "classification": classification,
                "shared_claims": shared,
                "left": {name: first_claims[name] for name in shared},
                "right": {name: second_claims[name] for name in shared},
            }
        )
    overall = (
        "behavioral_divergence"
        if any_difference
        else "evidence_gap"
        if any_gap
        else "agreement"
    )
    return {
        "classification": overall,
        "engines": [first_engine, second_engine],
        "reasons": [],
        "scenarios": comparisons,
    }
