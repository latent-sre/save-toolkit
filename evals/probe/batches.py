"""Pool a batch's trials into one verdict per scenario, and refuse to pool what is not one measurement.

Trials of another candidate, scenario, CLI version or host never pool with a batch; a scenario
with a forbidding check or a negative routing expectation holds every trial (result rule 3).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

import judge as rubric_judge

from . import catalog, fingerprints
from .outcomes import State


def merge_summary_entries(existing: list[dict[str, Any]], updates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Replace the entry for each (scenario, label, run) the updates name; append the rest."""
    keys = {(u["scenario"], u["label"], u["run"]) for u in updates}
    kept = [e for e in existing if (e.get("scenario"), e.get("label"), e.get("run")) not in keys]
    return kept + updates


def batch_identity_problem(
    entries: list[dict[str, Any]],
    scenarios: list[dict[str, Any]],
    plugin_sha: str,
    judge_binding: rubric_judge.JudgeBinding | None = None,
    runtime: dict[str, Any] | None = None,
) -> str | None:
    """Refuse to pool trials of another candidate, scenario, CLI version or host into one verdict.

    A trial recorded before the CLI and host were recorded never pools with one that has them.
    """
    if runtime is not None and not runtime.get("cli_version"):
        return "the CLI did not report its version, so no result would identify it; fix --executable first"
    expected = {
        spec["id"]: fingerprints.scenario_digest(spec, judge_binding.metadata if judge_binding else None)
        for spec in scenarios
    }
    for entry in entries:
        scenario = entry.get("scenario")
        if scenario not in expected:
            continue
        if entry.get("plugin_source_sha256") != plugin_sha:
            return "candidate digest is missing or differs; use a new label or overwrite every affected run"
        if runtime is not None and entry.get("runtime") != runtime:
            return "CLI version or host is missing or differs; use a new label or overwrite every affected run"
        if entry.get("scenario_sha256") != expected[scenario]:
            return f"{scenario}: scenario identity is missing or changed; use a new label or rerun the batch"
    return None


def effective_threshold(spec: Mapping[str, Any], requested: float | None) -> float:
    """Clamp a not_fire scenario to zero tolerance regardless of the requested threshold.

    The threshold applies to POSITIVES only: how often the expected component must fire. A negative
    passes only at a 0% fire rate, so its effective threshold is always 1.0 -- otherwise a
    --threshold 0.66 batch would let a forbidden component over-trigger on a third of trials and
    still report PASS. Any forbidding check is held to every trial the same way (threat-model ADR
    result rule 3), so a requested threshold lowers only scenarios whose checks all require.
    """
    if catalog.is_negative_routing(spec) or catalog.has_forbidding_assertion(spec):
        return 1.0
    declared = spec.get("threshold")
    if requested is not None:
        return float(requested)
    return float(declared) if declared is not None else 1.0


def model_identities(entries: list[dict[str, Any]]) -> list[str]:
    """Every concrete model recorded across a batch's trials. A mutable alias can resolve twice."""
    return sorted({str(model) for entry in entries for model in (entry.get("models") or [])})


def aggregate_verdict(states: list[str], threshold: float) -> State:
    required = math.ceil(len(states) * threshold)
    passes = states.count(State.PASS)
    inconclusive = states.count(State.INCONCLUSIVE)
    if passes >= required:
        return State.PASS
    if passes + inconclusive < required:
        return State.FAIL
    return State.INCONCLUSIVE


def aggregate_by_scenario(
    scenarios: list[dict[str, Any]], results: list[dict[str, Any]], requested: float | None
) -> dict[str, dict[str, Any]]:
    by_id = {spec["id"]: spec for spec in scenarios}
    grouped: dict[str, list[str]] = {}
    for result in results:
        grouped.setdefault(result["scenario"], []).append(result["status"])
    verdicts: dict[str, dict[str, Any]] = {}
    for scenario_id, states in grouped.items():
        threshold = effective_threshold(by_id.get(scenario_id, {}), requested)
        verdicts[scenario_id] = {
            "verdict": aggregate_verdict(states, threshold),
            "passed": states.count("PASS"),
            "trials": len(states),
            "threshold": threshold,
        }
    return verdicts
