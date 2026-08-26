"""Build strict claim-scoped result envelopes from shared evaluator records."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Mapping, Sequence

import engine_adapters
import engine_contract
import execution_profiles


class EvidenceError(ValueError):
    """Runner records cannot be represented by the normalized evidence contract."""


def _framed_digest(label: str, values: Sequence[str]) -> str:
    digest = hashlib.sha256(f"save-toolkit-{label}-v1\0".encode("ascii"))
    ordered = sorted(values)
    digest.update(str(len(ordered)).encode("ascii"))
    digest.update(b"\0")
    for value in ordered:
        if engine_contract.SHA256_RE.fullmatch(value) is None:
            raise EvidenceError(f"{label} contains an invalid SHA-256 digest")
        digest.update(bytes.fromhex(value))
    return digest.hexdigest()


def _utc(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError(f"invalid result timestamp {value!r}") from exc
    if parsed.tzinfo is None:
        raise EvidenceError("result timestamp must carry a UTC offset")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _aggregate(states: Sequence[str]) -> str:
    if "FAIL" in states:
        return "FAIL"
    if "INCONCLUSIVE" in states:
        return "INCONCLUSIVE"
    return "PASS"


def _trial_digests(scenario: Mapping[str, object], field: str) -> list[str]:
    values: list[str] = []
    for trial in scenario["trials"]:  # type: ignore[index]
        value = trial.get(field)  # type: ignore[union-attr]
        if isinstance(value, str):
            values.append(value)
    return values


def _evidence_digests(scenario: Mapping[str, object]) -> list[str]:
    values = _trial_digests(scenario, "trace_sha256")
    if not values:
        raise EvidenceError(f"scenario {scenario.get('id')} has no trace evidence digest")
    return sorted(set(values))


def _claim(
    claim_type: str,
    status: str,
    evidence: Sequence[str],
    limitations: Sequence[str] = (),
) -> dict[str, object]:
    return {
        "type": claim_type,
        "status": status,
        "evidence": sorted(set(evidence)),
        "limitations": list(limitations),
    }


def _native_component_status(scenario: Mapping[str, object]) -> str:
    trials = scenario["trials"]  # type: ignore[index]
    if any(trial.get("state") == "INCONCLUSIVE" for trial in trials):
        return "INCONCLUSIVE"
    target = scenario.get("target")
    if not isinstance(target, Mapping):
        raise EvidenceError(f"scenario {scenario.get('id')} lacks its target identity")
    kind = target.get("kind")
    name = target.get("name")
    if kind == "agent" and scenario.get("mode") == "direct":
        # The real plugin agent is selected by the adapter's --agent flag; a successful bounded
        # trace proves that pin even though Claude does not emit a nested Agent tool event.
        return "PASS"
    bucket = "skills" if kind == "skill" else "agents"
    if kind not in {"skill", "agent"} or not isinstance(name, str):
        raise EvidenceError(f"scenario {scenario.get('id')} has an invalid target identity")
    invoked_everywhere = bool(trials) and all(
        any(
            observed == name or observed.endswith(f":{name}")
            for observed in trial.get("completed_invocations", {}).get(bucket, [])
        )
        for trial in trials
    )
    return "PASS" if invoked_everywhere else "FAIL"


def build_envelope(
    *,
    provenance: Mapping[str, object],
    profile: execution_profiles.ExecutionProfile,
    scenario_results: Sequence[Mapping[str, object]],
    reference_canaries: Mapping[str, Mapping[str, str]],
    grader_sha256: str,
    ended_at: str,
    integrity_errors: Sequence[str] = (),
) -> dict[str, object]:
    """Normalize one engine batch; this validates before returning."""

    engine = profile.engine
    if provenance.get("engine") != engine:
        raise EvidenceError("profile engine and runtime provenance disagree")
    if not scenario_results:
        raise EvidenceError("normalized evidence requires at least one scenario")
    requested = set(profile.claims)
    all_trials = [
        trial
        for scenario in scenario_results
        for trial in scenario["trials"]  # type: ignore[index]
    ]
    trace_complete = bool(all_trials) and all(
        trial.get("state") in {"PASS", "FAIL"} for trial in all_trials
    )
    resolved_models = sorted(
        {
            str(trial["resolved_model"])
            for trial in all_trials
            if isinstance(trial.get("resolved_model"), str) and trial["resolved_model"]
        }
    )
    resolved_model = resolved_models[0] if len(resolved_models) == 1 else None
    policy_digests = [
        digest
        for scenario in scenario_results
        for digest in _trial_digests(scenario, "policy_sha256")
    ]
    global_inconclusive = (
        bool(integrity_errors)
        or not trace_complete
        or resolved_model is None
        or not policy_digests
    )

    canaries: list[dict[str, object]] = []
    canary_status: dict[str, str] = {}
    for scenario in scenario_results:
        scenario_id = str(scenario["id"])
        states: list[str] = []
        for path, expected in sorted(reference_canaries.get(scenario_id, {}).items()):
            trials = scenario["trials"]  # type: ignore[index]
            observed_everywhere = bool(trials) and all(
                expected in trial.get("canaries", {}).get("observed", [])  # type: ignore[union-attr]
                for trial in trials
            )
            expected_everywhere = bool(trials) and all(
                expected in trial.get("canaries", {}).get("expected", [])  # type: ignore[union-attr]
                for trial in trials
            )
            status = "PASS" if observed_everywhere and expected_everywhere else "MISSING"
            canaries.append(
                {
                    "scenario_id": scenario_id,
                    "path": path,
                    "expected": expected,
                    "observed": expected if status == "PASS" else None,
                    "status": status,
                }
            )
            states.append("PASS" if status == "PASS" else "INCONCLUSIVE")
        if states:
            canary_status[scenario_id] = _aggregate(states)
            if canary_status[scenario_id] != "PASS":
                global_inconclusive = True

    normalized_scenarios: list[dict[str, object]] = []
    emitted: set[str] = set()
    integrity_evidence = [str(provenance["plugin_source_sha256"])]
    for index, scenario in enumerate(scenario_results):
        scenario_id = str(scenario["id"])
        scenario_state = (
            "INCONCLUSIVE" if global_inconclusive else str(scenario["verdict"])
        )
        traces = _evidence_digests(scenario)
        claims: list[dict[str, object]] = []
        if index == 0 and "candidate_snapshot_integrity" in requested:
            status = "INCONCLUSIVE" if global_inconclusive else "PASS"
            claims.append(_claim(
                "candidate_snapshot_integrity",
                status,
                integrity_evidence,
                list(integrity_errors),
            ))
        if engine == "claude-plugin":
            host_state = "INCONCLUSIVE" if scenario_state == "INCONCLUSIVE" else "PASS"
            for claim_type in (
                "native_plugin_loaded",
                "native_component_invoked",
                "advertised_tool_inventory",
                "callable_tool_boundary",
            ):
                if claim_type in requested:
                    status = (
                        _native_component_status(scenario)
                        if claim_type == "native_component_invoked"
                        else host_state
                    )
                    claims.append(_claim(claim_type, status, traces))
        if "reference_used" in requested and scenario_id in reference_canaries:
            claims.append(_claim(
                "reference_used",
                canary_status.get(scenario_id, "INCONCLUSIVE"),
                traces,
                () if canary_status.get(scenario_id) == "PASS" else ("required canary was not observed in every trial",),
            ))
        for claim_type in ("behavioral_contract", "deterministic_grader_result"):
            if claim_type in requested:
                claims.append(_claim(claim_type, scenario_state, traces))
        if not claims:
            raise EvidenceError(f"scenario {scenario_id} has no applicable requested claim")
        emitted.update(str(claim["type"]) for claim in claims)
        verdict = _aggregate([str(claim["status"]) for claim in claims])
        normalized_scenarios.append(
            {
                "id": scenario_id,
                "sha256": str(scenario["scenario_sha256"]),
                "verdict": verdict,
                "claims": claims,
            }
        )
    if emitted != requested:
        raise EvidenceError(f"requested claims were not emitted: {sorted(requested - emitted)}")

    context_digests = [
        digest
        for scenario in scenario_results
        for digest in _trial_digests(scenario, "context_sha256")
    ]
    if engine == "codex-cli" and not context_digests:
        raise EvidenceError("Codex envelope has no resolved-context digest")

    trace_digests = [
        digest
        for scenario in scenario_results
        for digest in _trial_digests(scenario, "trace_sha256")
    ]
    started = _utc(str(provenance["started_at"]))
    ended = _utc(ended_at)
    duration = max(
        0.0,
        (datetime.fromisoformat(ended.replace("Z", "+00:00")) -
         datetime.fromisoformat(started.replace("Z", "+00:00"))).total_seconds(),
    )
    executed_trials = [
        trial for trial in all_trials if trial.get("model_executed", True) is not False
    ]
    costs = [trial.get("total_cost_usd") for trial in executed_trials]
    if engine == "claude-plugin" and costs and all(
        isinstance(value, (int, float)) and not isinstance(value, bool) for value in costs
    ):
        cost = {"status": "available", "amount": sum(costs), "currency": "USD", "reason": None}
    else:
        cost = {
            "status": "unavailable",
            "amount": None,
            "currency": None,
            "reason": "subscriber CLI does not expose a trustworthy currency-denominated run cost",
        }
    limitations = list(integrity_errors)
    if engine == "codex-cli":
        limitations.append("resolved-context evidence does not prove native plugin loading or host tool authority")
    if provenance.get("plugin_inputs_dirty"):
        limitations.append("candidate inputs differ from the recorded Git revision")
    envelope: dict[str, object] = {
        "schema_version": engine_contract.SCHEMA_VERSION,
        "run_id": str(provenance["run_id"]),
        "engine": {
            "name": engine,
            "adapter_version": engine_adapters.ADAPTER_VERSION,
            "runtime_version": str(provenance["runtime_cli_version"]),
            "requested_model": profile.model,
            "resolved_model": resolved_model,
            "auth_mode": "subscriber_session",
        },
        "candidate": {
            "git_sha": str(provenance["plugin_commit"]),
            "clean": not bool(provenance.get("plugin_inputs_dirty")),
            "input_sha256": str(provenance["plugin_source_sha256"]),
        },
        "artifacts": {
            "plugin_snapshot": {
                "applicable": engine == "claude-plugin",
                "sha256": str(provenance["plugin_source_sha256"]) if engine == "claude-plugin" else None,
            },
            "resolved_context": {
                "applicable": engine == "codex-cli",
                "sha256": _framed_digest("resolved-contexts", context_digests) if engine == "codex-cli" else None,
            },
        },
        "digests": {
            "scenario_suite": str(provenance["eval_suite_sha256"]),
            "graders": grader_sha256,
            "execution_profile": profile.sha256,
            "comparison": profile.comparison_sha256,
            "policy": _framed_digest("policies", policy_digests) if policy_digests else None,
        },
        "canaries": canaries,
        "claims_requested": list(profile.claims),
        "claims_supported": sorted(engine_contract.ENGINE_CLAIMS[engine]),
        "scenarios": normalized_scenarios,
        "verdict": _aggregate([str(item["verdict"]) for item in normalized_scenarios]),
        "timing": {"started_at": started, "ended_at": ended, "duration_seconds": duration},
        "cost": cost,
        "trace": {"complete": trace_complete, "sha256": _framed_digest("traces", trace_digests)},
        # Automated evidence never promotes. A human may accept only this exact candidate revision.
        "promotion_eligible": False,
        "limitations": limitations,
    }
    engine_contract.validate_envelope(envelope)
    return envelope
