"""Versioned execution profiles bind eval claims, selection, budgets, and approval."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping

import engine_adapters
import engine_contract


SCHEMA_VERSION = "eval-execution-profile/v1"
FIELDS = {
    "schema_version",
    "id",
    "comparison",
    "engine",
    "claims",
    "scenario_ids",
    "required_references",
    "model",
    "trials",
    "timeout_s",
    "total_timeout_s",
    "cost_budget",
    "approval",
}
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)


class ProfileError(ValueError):
    """An execution profile is malformed, unsupported, or unapproved."""


@dataclass(frozen=True)
class ExecutionProfile:
    id: str
    comparison: Mapping[str, object]
    engine: str
    claims: tuple[str, ...]
    scenario_ids: tuple[str, ...]
    required_references: Mapping[str, tuple[str, ...]]
    model: str
    trials: int
    timeout_s: int
    total_timeout_s: int
    cost_budget: Mapping[str, object]
    approval: Mapping[str, str] | None
    sha256: str
    comparison_sha256: str


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ProfileError(f"{field} must be an object")
    return value


def _exact(value: Mapping[str, object], expected: set[str], field: str) -> None:
    missing = expected - set(value)
    unknown = set(value) - expected
    if missing:
        raise ProfileError(f"{field} missing fields: {sorted(missing)}")
    if unknown:
        raise ProfileError(f"{field} has unknown fields: {sorted(unknown)}")


def _positive_int(value: object, field: str, *, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ProfileError(f"{field} must be an integer >= {minimum}")
    return value


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProfileError(f"{field} must be a non-empty string")
    return value


def _canonical_digest(value: Mapping[str, object]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(b"save-toolkit-eval-profile-v1\0" + encoded).hexdigest()


def _comparison_digest(
    comparison: Mapping[str, object],
    *,
    scenario_ids: list[str],
    references: Mapping[str, tuple[str, ...]],
    trials: int,
    timeout_s: int,
    total_timeout_s: int,
) -> str:
    value = {
        "comparison": comparison,
        "scenario_ids": sorted(scenario_ids),
        "required_references": {
            scenario_id: sorted(paths)
            for scenario_id, paths in sorted(references.items())
        },
        "trials": trials,
        "timeout_s": timeout_s,
        "total_timeout_s": total_timeout_s,
        "adapter_contract_version": "1",
        "policy_contracts": {
            "claude-plugin": sorted(
                {
                    engine_adapters.ClaudeNativeAdapter().policy_sha256(
                        enable_snapshot_reads=bool(references.get(scenario_id))
                    )
                    for scenario_id in scenario_ids
                }
            ),
            "codex-cli": [
                engine_adapters.CodexResolvedContextAdapter().requested_policy_sha256()
            ],
        },
    }
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(b"save-toolkit-eval-comparison-v1\0" + encoded).hexdigest()


def validate_profile(
    value: object,
    *,
    require_approval: bool = False,
) -> ExecutionProfile:
    profile = _mapping(value, "profile")
    _exact(profile, FIELDS, "profile")
    if profile["schema_version"] != SCHEMA_VERSION:
        raise ProfileError(f"profile.schema_version must be {SCHEMA_VERSION!r}")
    profile_id = _string(profile["id"], "profile.id")
    if ID_RE.fullmatch(profile_id) is None:
        raise ProfileError("profile.id must be a canonical lowercase slug")
    engine = _string(profile["engine"], "profile.engine")
    if engine not in engine_contract.ENGINE_CLAIMS:
        raise ProfileError(f"unknown eval engine {engine!r}")

    comparison_raw = _mapping(profile["comparison"], "profile.comparison")
    _exact(comparison_raw, {"id", "models"}, "profile.comparison")
    comparison_id = _string(comparison_raw["id"], "profile.comparison.id")
    if ID_RE.fullmatch(comparison_id) is None:
        raise ProfileError("profile.comparison.id must be a canonical lowercase slug")
    models_raw = _mapping(comparison_raw["models"], "profile.comparison.models")
    _exact(models_raw, set(engine_contract.ENGINE_CLAIMS), "profile.comparison.models")
    comparison = {
        "id": comparison_id,
        "models": {
            name: _string(models_raw[name], f"profile.comparison.models.{name}")
            for name in sorted(models_raw)
        },
    }

    raw_claims = profile["claims"]
    if not isinstance(raw_claims, list) or not all(isinstance(item, str) for item in raw_claims):
        raise ProfileError("profile.claims must be a string list")
    try:
        engine_contract.validate_claim_request(engine, raw_claims)
    except engine_contract.ContractError as exc:
        raise ProfileError(str(exc)) from exc
    required_gate_claims = {"behavioral_contract", "deterministic_grader_result"}
    if not required_gate_claims.issubset(raw_claims):
        raise ProfileError(
            "behavioral_contract and deterministic_grader_result are mandatory automated gate claims"
        )

    raw_scenarios = profile["scenario_ids"]
    if (
        not isinstance(raw_scenarios, list)
        or not raw_scenarios
        or not all(isinstance(item, str) and ID_RE.fullmatch(item) for item in raw_scenarios)
        or len(raw_scenarios) != len(set(raw_scenarios))
    ):
        raise ProfileError("profile.scenario_ids must be unique canonical slugs")
    if engine == "codex-cli" and any(item.startswith("discovery-") for item in raw_scenarios):
        raise ProfileError("codex-cli profiles support direct scenarios only")

    raw_references = _mapping(profile["required_references"], "profile.required_references")
    references: dict[str, tuple[str, ...]] = {}
    unknown_scenarios = set(raw_references) - set(raw_scenarios)
    if unknown_scenarios:
        raise ProfileError(
            f"required_references names unselected scenarios: {sorted(unknown_scenarios)}"
        )
    for scenario_id, raw_paths in raw_references.items():
        if not isinstance(raw_paths, list) or not raw_paths:
            raise ProfileError(f"required references for {scenario_id} must be a non-empty list")
        paths: list[str] = []
        for raw_path in raw_paths:
            if not isinstance(raw_path, str):
                raise ProfileError("reference path must be a string")
            normalized = raw_path.replace("\\", "/")
            path = PurePosixPath(normalized)
            if (
                path.is_absolute()
                or any(part in {"", ".", ".."} for part in path.parts)
                or not normalized.startswith("skills/")
            ):
                raise ProfileError(f"unsafe reference path: {raw_path!r}")
            paths.append(path.as_posix())
        if len(paths) != len(set(paths)):
            raise ProfileError(f"duplicate reference path for {scenario_id}")
        references[scenario_id] = tuple(paths)
    if "reference_used" in raw_claims and not references:
        raise ProfileError("reference_used claim requires at least one required reference")

    model = _string(profile["model"], "profile.model")
    if comparison["models"][engine] != model:  # type: ignore[index]
        raise ProfileError("profile.model must match its comparison model matrix entry")
    trials = _positive_int(profile["trials"], "profile.trials", minimum=2)
    timeout_s = _positive_int(profile["timeout_s"], "profile.timeout_s")
    total_timeout_s = _positive_int(profile["total_timeout_s"], "profile.total_timeout_s")
    if total_timeout_s < timeout_s:
        raise ProfileError("profile.total_timeout_s must allow at least one trial timeout")

    cost = _mapping(profile["cost_budget"], "profile.cost_budget")
    _exact(cost, {"status", "max_usd"}, "profile.cost_budget")
    if cost["status"] == "unavailable":
        if cost["max_usd"] is not None:
            raise ProfileError("unavailable cost budget requires null max_usd, never zero")
    elif cost["status"] == "available":
        maximum = cost["max_usd"]
        if isinstance(maximum, bool) or not isinstance(maximum, (int, float)) or maximum <= 0:
            raise ProfileError("available cost budget requires positive max_usd")
    else:
        raise ProfileError("profile.cost_budget.status must be available or unavailable")
    if engine == "codex-cli" and cost["status"] != "unavailable":
        raise ProfileError("subscriber Codex cost must be recorded as unavailable")

    raw_approval = profile["approval"]
    approval: dict[str, str] | None = None
    if raw_approval is not None:
        approved = _mapping(raw_approval, "profile.approval")
        _exact(approved, {"approved_by", "approved_at", "budget_id"}, "profile.approval")
        approval = {
            "approved_by": _string(approved["approved_by"], "profile.approval.approved_by"),
            "approved_at": _string(approved["approved_at"], "profile.approval.approved_at"),
            "budget_id": _string(approved["budget_id"], "profile.approval.budget_id"),
        }
        if TIMESTAMP_RE.fullmatch(approval["approved_at"]) is None:
            raise ProfileError("profile.approval.approved_at must be an RFC3339 UTC timestamp")
    if require_approval and approval is None:
        raise ProfileError("live model execution requires explicit profile approval")

    return ExecutionProfile(
        id=profile_id,
        comparison=comparison,
        engine=engine,
        claims=tuple(raw_claims),
        scenario_ids=tuple(raw_scenarios),
        required_references=references,
        model=model,
        trials=trials,
        timeout_s=timeout_s,
        total_timeout_s=total_timeout_s,
        cost_budget=dict(cost),
        approval=approval,
        sha256=_canonical_digest(profile),
        comparison_sha256=_comparison_digest(
            comparison,
            scenario_ids=list(raw_scenarios),
            references=references,
            trials=trials,
            timeout_s=timeout_s,
            total_timeout_s=total_timeout_s,
        ),
    )


def load_profile(path: Path, *, require_approval: bool = False) -> ExecutionProfile:
    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, child in pairs:
            if key in result:
                raise ProfileError(f"duplicate JSON object key {key!r}")
            result[key] = child
        return result

    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates)
    except ProfileError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProfileError(f"cannot read execution profile {path}: {exc}") from exc
    return validate_profile(value, require_approval=require_approval)
