"""Closed, immutable contracts for the AutoGen GraphFlow + A2A sandbox."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


INTERFACE_VERSION = "autogen-a2a-interface/v1"
CASE_VERSION = "canary-evidence-case/v1"
REQUEST_VERSION = "canary-analysis-request/v1"
ARTIFACT_VERSION = "release-recommendation/v1"
DECISION_VERSION = "release-decision-state/v1"
CASE_MANIFEST_VERSION = "canary-evidence-case-manifest/v1"

CASE_IDS = (
    "mission-healthy-001",
    "confirmed-regression-001",
    "stale-evidence-reconciled-001",
    "unresolved-contradiction-001",
    "slow-analysis-cancel-001",
    "checkpoint-resume-001",
)
ANALYZER_IDS = (
    "slo_analyzer",
    "deployment_analyzer",
    "dependency_analyzer",
)
RECOMMENDATIONS = ("ADVANCE_CANARY", "HALT_CANARY")
A2A_CASE_STATES = ("completed", "input-required", "canceled", "failed")
DECISIONS = ("ACCEPT", "REJECT")
PACKAGE_NAMES = (
    "agent-framework-core",
    "agent-framework-a2a",
    "autogen-agentchat",
    "a2a-sdk",
)

_LOWER_ID = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{0,127})$")
_OPAQUE_ID = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._:-]{0,127})$")
_TOKEN = re.compile(r"^[a-z][a-z0-9_.-]{0,127}$")
_REVISION = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_UTC_RFC3339 = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})T"
    r"(?P<time>\d{2}:\d{2}:\d{2})(?P<fraction>\.\d+)?Z$"
)


class ContractViolation(ValueError):
    """A decoded object does not satisfy the v1 closed contract."""


@dataclass(frozen=True, slots=True)
class Candidate:
    service: str
    candidate_revision: str
    rollback_revision: str


@dataclass(frozen=True, slots=True)
class SloEvidence:
    observed_at: str
    age_seconds: int
    freshness_limit_seconds: int
    baseline_error_ppm: int
    canary_error_ppm: int
    burn_rate_milli: int


@dataclass(frozen=True, slots=True)
class DeploymentEvidence:
    observed_at: str
    age_seconds: int
    freshness_limit_seconds: int
    candidate_only_change: bool
    rollback_ready: bool
    configuration_drift: bool


@dataclass(frozen=True, slots=True)
class DependencyEvidence:
    observed_at: str
    age_seconds: int
    freshness_limit_seconds: int
    baseline_impacted: bool
    canary_impacted: bool


@dataclass(frozen=True, slots=True)
class EvidenceSnapshot:
    slo: SloEvidence
    deployment: DeploymentEvidence
    dependency: DependencyEvidence


@dataclass(frozen=True, slots=True)
class FaultControls:
    slow_analyzer: str | None
    checkpoint_pause: bool


@dataclass(frozen=True, slots=True)
class ExpectedOutcome:
    a2a_state: str
    recommendation: str | None
    reconciliation_attempts: int


@dataclass(frozen=True, slots=True)
class CanaryCase:
    case_version: str
    case_id: str
    candidate: Candidate
    evidence: EvidenceSnapshot
    reconciliation: EvidenceSnapshot | None
    fault: FaultControls
    expected: ExpectedOutcome


@dataclass(frozen=True, slots=True)
class AnalysisRequest:
    request_version: str
    run_id: str
    source_revision: str
    case_id: str
    case_digest: str
    candidate_revision: str
    case: CanaryCase


@dataclass(frozen=True, slots=True)
class PackageVersions:
    agent_framework_core: str
    agent_framework_a2a: str
    autogen_agentchat: str
    a2a_sdk: str


@dataclass(frozen=True, slots=True)
class RecommendationArtifact:
    artifact_version: str
    artifact_id: str
    run_id: str
    case_id: str
    case_digest: str
    source_revision: str
    candidate_revision: str
    a2a_task_id: str
    a2a_context_id: str
    recommendation: str
    basis: tuple[str, ...]
    resolved_contradictions: tuple[str, ...]
    unresolved_contradictions: tuple[str, ...]
    reconciliation_attempts: int
    graph_state_sha256: str
    packages: PackageVersions
    artifact_digest: str


@dataclass(frozen=True, slots=True)
class ReleaseDecision:
    decision_version: str
    run_id: str
    source_revision: str
    case_id: str
    case_digest: str
    candidate_revision: str
    artifact_digest: str
    decision: str
    approver: str
    decided_at: str
    expires_at: str


def to_plain_object(value: object) -> Any:
    """Convert immutable contract records into their logical JSON object."""

    if is_dataclass(value) and not isinstance(value, type):
        result: dict[str, Any] = {}
        for field in fields(value):
            key = field.name
            if isinstance(value, PackageVersions):
                key = key.replace("_", "-")
            result[key] = to_plain_object(getattr(value, field.name))
        return result
    if isinstance(value, Mapping):
        return {key: to_plain_object(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_plain_object(item) for item in value]
    if value is None or type(value) in (str, int, bool, float):
        return value
    raise ContractViolation(
        f"value of type {type(value).__name__} is not a JSON contract value"
    )


def canonical_json_bytes(
    value: object, *, omit_keys: set[str] | frozenset[str] = frozenset()
) -> bytes:
    """Serialize a logical object as stable compact UTF-8 JSON."""

    plain = to_plain_object(value)
    if omit_keys:
        if not isinstance(plain, dict):
            raise ContractViolation("omit_keys requires a top-level object")
        plain = {key: item for key, item in plain.items() if key not in omit_keys}
    try:
        text = json.dumps(
            plain,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise ContractViolation(f"object is not canonical JSON: {exc}") from exc
    return text.encode("utf-8")


def canonical_sha256(
    value: object, *, omit_keys: set[str] | frozenset[str] = frozenset()
) -> str:
    """Return the lowercase SHA-256 of the canonical logical object."""

    return hashlib.sha256(canonical_json_bytes(value, omit_keys=omit_keys)).hexdigest()


def sha256_bytes(value: bytes) -> str:
    """Return the lowercase SHA-256 of exact bytes."""

    return hashlib.sha256(value).hexdigest()


def expected_artifact_id(run_id: str) -> str:
    """Derive the sole stable recommendation artifact ID for a run."""

    return f"release-recommendation:{run_id}"


def validate_case(value: object) -> CanaryCase:
    root = _closed_map(
        value,
        (
            "case_version",
            "case_id",
            "candidate",
            "evidence",
            "reconciliation",
            "fault",
            "expected",
        ),
        "case",
    )
    case_version = _expect_version(root["case_version"], CASE_VERSION, "case.case_version")
    case_id = _expect_enum(root["case_id"], CASE_IDS, "case.case_id")
    candidate = _validate_candidate(root["candidate"])
    evidence = _validate_evidence(root["evidence"], "case.evidence")
    reconciliation_value = root["reconciliation"]
    reconciliation = (
        None
        if reconciliation_value is None
        else _validate_evidence(reconciliation_value, "case.reconciliation")
    )
    fault = _validate_fault(root["fault"])
    expected = _validate_expected(root["expected"])

    if (reconciliation is None) != (expected.reconciliation_attempts == 0):
        raise ContractViolation(
            "case.reconciliation must be present exactly when "
            "expected.reconciliation_attempts is 1"
        )
    if reconciliation is not None:
        _validate_reconciliation_progress(evidence, reconciliation)
    if expected.a2a_state == "completed" and expected.recommendation is None:
        raise ContractViolation("a completed case requires a recommendation")
    if expected.a2a_state != "completed" and expected.recommendation is not None:
        raise ContractViolation("a non-completed case cannot expect a recommendation")
    if (fault.slow_analyzer is None) != (expected.a2a_state != "canceled"):
        raise ContractViolation(
            "a canceled case requires exactly one slow_analyzer fault and no other case may set it"
        )
    if fault.checkpoint_pause and expected.a2a_state != "completed":
        raise ContractViolation("checkpoint_pause is valid only for a completed case")

    return CanaryCase(
        case_version=case_version,
        case_id=case_id,
        candidate=candidate,
        evidence=evidence,
        reconciliation=reconciliation,
        fault=fault,
        expected=expected,
    )


def validate_analysis_request(value: object) -> AnalysisRequest:
    root = _closed_map(
        value,
        (
            "request_version",
            "run_id",
            "source_revision",
            "case_id",
            "case_digest",
            "candidate_revision",
            "case",
        ),
        "analysis_request",
    )
    request_version = _expect_version(
        root["request_version"], REQUEST_VERSION, "analysis_request.request_version"
    )
    run_id = _expect_id(root["run_id"], "analysis_request.run_id")
    source_revision = _expect_revision(
        root["source_revision"], "analysis_request.source_revision"
    )
    case_id = _expect_enum(root["case_id"], CASE_IDS, "analysis_request.case_id")
    case_digest = _expect_digest(root["case_digest"], "analysis_request.case_digest")
    candidate_revision = _expect_revision(
        root["candidate_revision"], "analysis_request.candidate_revision"
    )
    case = validate_case(root["case"])

    if case_id != case.case_id:
        raise ContractViolation("analysis_request.case_id does not match nested case.case_id")
    if candidate_revision != case.candidate.candidate_revision:
        raise ContractViolation(
            "analysis_request.candidate_revision does not match nested case candidate revision"
        )
    computed_case_digest = canonical_sha256(case)
    if case_digest != computed_case_digest:
        raise ContractViolation(
            "analysis_request.case_digest does not match the canonical nested case"
        )

    return AnalysisRequest(
        request_version=request_version,
        run_id=run_id,
        source_revision=source_revision,
        case_id=case_id,
        case_digest=case_digest,
        candidate_revision=candidate_revision,
        case=case,
    )


def parse_analysis_request_json(value: str | bytes) -> AnalysisRequest:
    """Parse the A2A text Part and require its exact canonical JSON representation."""

    raw = value.encode("utf-8") if isinstance(value, str) else value
    decoded = _load_json_bytes(raw, "analysis_request")
    request = validate_analysis_request(decoded)
    if raw != canonical_json_bytes(request):
        raise ContractViolation("analysis_request text Part is not canonical JSON")
    return request


def validate_recommendation_artifact(
    value: object, *, request: AnalysisRequest | None = None
) -> RecommendationArtifact:
    root = _closed_map(
        value,
        (
            "artifact_version",
            "artifact_id",
            "run_id",
            "case_id",
            "case_digest",
            "source_revision",
            "candidate_revision",
            "a2a_task_id",
            "a2a_context_id",
            "recommendation",
            "basis",
            "resolved_contradictions",
            "unresolved_contradictions",
            "reconciliation_attempts",
            "graph_state_sha256",
            "packages",
            "artifact_digest",
        ),
        "recommendation_artifact",
    )
    artifact_version = _expect_version(
        root["artifact_version"], ARTIFACT_VERSION, "recommendation_artifact.artifact_version"
    )
    run_id = _expect_id(root["run_id"], "recommendation_artifact.run_id")
    artifact_id = _expect_opaque_id(
        root["artifact_id"], "recommendation_artifact.artifact_id"
    )
    if artifact_id != expected_artifact_id(run_id):
        raise ContractViolation(
            "recommendation_artifact.artifact_id is not the stable run-bound ID"
        )
    case_id = _expect_enum(
        root["case_id"], CASE_IDS, "recommendation_artifact.case_id"
    )
    case_digest = _expect_digest(
        root["case_digest"], "recommendation_artifact.case_digest"
    )
    source_revision = _expect_revision(
        root["source_revision"], "recommendation_artifact.source_revision"
    )
    candidate_revision = _expect_revision(
        root["candidate_revision"], "recommendation_artifact.candidate_revision"
    )
    a2a_task_id = _expect_opaque_id(
        root["a2a_task_id"], "recommendation_artifact.a2a_task_id"
    )
    a2a_context_id = _expect_opaque_id(
        root["a2a_context_id"], "recommendation_artifact.a2a_context_id"
    )
    recommendation = _expect_enum(
        root["recommendation"],
        RECOMMENDATIONS,
        "recommendation_artifact.recommendation",
    )
    basis = _expect_token_list(
        root["basis"], "recommendation_artifact.basis", allow_empty=False
    )
    resolved = _expect_token_list(
        root["resolved_contradictions"],
        "recommendation_artifact.resolved_contradictions",
        stable_sorted=True,
    )
    unresolved = _expect_token_list(
        root["unresolved_contradictions"],
        "recommendation_artifact.unresolved_contradictions",
        stable_sorted=True,
    )
    if set(resolved) & set(unresolved):
        raise ContractViolation(
            "recommendation_artifact contradictions cannot be both resolved and unresolved"
        )
    if unresolved:
        raise ContractViolation(
            "recommendation_artifact cannot contain unresolved contradictions"
        )
    reconciliation_attempts = _expect_int_range(
        root["reconciliation_attempts"],
        "recommendation_artifact.reconciliation_attempts",
        minimum=0,
        maximum=1,
    )
    if resolved and reconciliation_attempts == 0:
        raise ContractViolation(
            "recommendation_artifact resolved contradictions require one reconciliation attempt"
        )
    graph_state_sha256 = _expect_digest(
        root["graph_state_sha256"], "recommendation_artifact.graph_state_sha256"
    )
    packages = _validate_packages(root["packages"])
    artifact_digest = _expect_digest(
        root["artifact_digest"], "recommendation_artifact.artifact_digest"
    )

    artifact = RecommendationArtifact(
        artifact_version=artifact_version,
        artifact_id=artifact_id,
        run_id=run_id,
        case_id=case_id,
        case_digest=case_digest,
        source_revision=source_revision,
        candidate_revision=candidate_revision,
        a2a_task_id=a2a_task_id,
        a2a_context_id=a2a_context_id,
        recommendation=recommendation,
        basis=basis,
        resolved_contradictions=resolved,
        unresolved_contradictions=unresolved,
        reconciliation_attempts=reconciliation_attempts,
        graph_state_sha256=graph_state_sha256,
        packages=packages,
        artifact_digest=artifact_digest,
    )
    computed_digest = canonical_sha256(artifact, omit_keys={"artifact_digest"})
    if artifact_digest != computed_digest:
        raise ContractViolation(
            "recommendation_artifact.artifact_digest does not match canonical artifact bytes"
        )
    if request is not None:
        _bind_artifact_to_request(artifact, request)
    return artifact


def validate_release_decision(
    value: object,
    *,
    artifact: RecommendationArtifact,
    at_time: datetime | None = None,
) -> ReleaseDecision:
    if not isinstance(artifact, RecommendationArtifact):
        raise TypeError("artifact must be a validated RecommendationArtifact")
    root = _closed_map(
        value,
        (
            "decision_version",
            "run_id",
            "source_revision",
            "case_id",
            "case_digest",
            "candidate_revision",
            "artifact_digest",
            "decision",
            "approver",
            "decided_at",
            "expires_at",
        ),
        "release_decision",
    )
    decision_version = _expect_version(
        root["decision_version"], DECISION_VERSION, "release_decision.decision_version"
    )
    run_id = _expect_id(root["run_id"], "release_decision.run_id")
    source_revision = _expect_revision(
        root["source_revision"], "release_decision.source_revision"
    )
    case_id = _expect_enum(root["case_id"], CASE_IDS, "release_decision.case_id")
    case_digest = _expect_digest(root["case_digest"], "release_decision.case_digest")
    candidate_revision = _expect_revision(
        root["candidate_revision"], "release_decision.candidate_revision"
    )
    artifact_digest = _expect_digest(
        root["artifact_digest"], "release_decision.artifact_digest"
    )
    decision = _expect_enum(root["decision"], DECISIONS, "release_decision.decision")
    approver = _expect_id(root["approver"], "release_decision.approver")
    decided_at, decided_instant = _expect_utc_rfc3339(
        root["decided_at"], "release_decision.decided_at"
    )
    expires_at, expires_instant = _expect_utc_rfc3339(
        root["expires_at"], "release_decision.expires_at"
    )
    if expires_instant <= decided_instant:
        raise ContractViolation(
            "release_decision.expires_at must be later than decided_at"
        )
    checked_at = datetime.now(timezone.utc) if at_time is None else at_time
    if checked_at.tzinfo is None or checked_at.utcoffset() != timezone.utc.utcoffset(checked_at):
        raise ContractViolation("at_time must be an aware UTC datetime")
    if expires_instant <= checked_at:
        raise ContractViolation("release_decision is expired")

    decision_record = ReleaseDecision(
        decision_version=decision_version,
        run_id=run_id,
        source_revision=source_revision,
        case_id=case_id,
        case_digest=case_digest,
        candidate_revision=candidate_revision,
        artifact_digest=artifact_digest,
        decision=decision,
        approver=approver,
        decided_at=decided_at,
        expires_at=expires_at,
    )
    bindings = {
        "run_id": artifact.run_id,
        "source_revision": artifact.source_revision,
        "case_id": artifact.case_id,
        "case_digest": artifact.case_digest,
        "candidate_revision": artifact.candidate_revision,
        "artifact_digest": artifact.artifact_digest,
    }
    for field_name, expected_value in bindings.items():
        if getattr(decision_record, field_name) != expected_value:
            raise ContractViolation(
                f"release_decision.{field_name} does not match the exact recommendation artifact"
            )
    return decision_record


def validate_decision_replay(
    existing: ReleaseDecision, candidate: ReleaseDecision
) -> ReleaseDecision:
    """Accept an exact idempotent replay and reject any changed record for its key."""

    if not isinstance(existing, ReleaseDecision) or not isinstance(
        candidate, ReleaseDecision
    ):
        raise TypeError("decision replay requires validated ReleaseDecision records")
    existing_key = (existing.run_id, existing.artifact_digest)
    candidate_key = (candidate.run_id, candidate.artifact_digest)
    if existing_key != candidate_key:
        raise ContractViolation("decision replay does not use the same idempotency key")
    if existing != candidate:
        raise ContractViolation(
            "decision replay attempted a different value for run_id + artifact_digest"
        )
    return existing


def verify_case_manifest(cases_directory: str | Path) -> tuple[CanaryCase, ...]:
    """Validate the exact six case files and their byte-level manifest bindings."""

    root = Path(cases_directory)
    manifest_path = root / "manifest.json"
    try:
        manifest_bytes = manifest_path.read_bytes()
    except OSError as exc:
        raise ContractViolation(f"cannot read case manifest: {exc}") from exc
    manifest = _closed_map(
        _load_json_bytes(manifest_bytes, "case_manifest"),
        ("manifest_version", "cases"),
        "case_manifest",
    )
    _expect_version(
        manifest["manifest_version"], CASE_MANIFEST_VERSION, "case_manifest.manifest_version"
    )
    entries_value = manifest["cases"]
    if type(entries_value) is not list:
        raise ContractViolation("case_manifest.cases must be an array")
    if len(entries_value) != len(CASE_IDS):
        raise ContractViolation("case_manifest must bind exactly six cases")

    cases: list[CanaryCase] = []
    for index, (entry_value, required_case_id) in enumerate(zip(entries_value, CASE_IDS)):
        entry = _closed_map(
            entry_value,
            ("case_id", "file", "sha256"),
            f"case_manifest.cases[{index}]",
        )
        case_id = _expect_enum(
            entry["case_id"], CASE_IDS, f"case_manifest.cases[{index}].case_id"
        )
        if case_id != required_case_id:
            raise ContractViolation("case_manifest cases are not in the required stable order")
        expected_file = f"{case_id}.json"
        file_name = _expect_string(entry["file"], f"case_manifest.cases[{index}].file")
        if file_name != expected_file:
            raise ContractViolation(
                f"case_manifest file for {case_id} must be {expected_file}"
            )
        expected_byte_digest = _expect_digest(
            entry["sha256"], f"case_manifest.cases[{index}].sha256"
        )
        case_path = root / file_name
        try:
            case_bytes = case_path.read_bytes()
        except OSError as exc:
            raise ContractViolation(f"cannot read case file {file_name}: {exc}") from exc
        actual_byte_digest = sha256_bytes(case_bytes)
        if actual_byte_digest != expected_byte_digest:
            raise ContractViolation(
                f"case file {file_name} byte digest does not match manifest"
            )
        case = validate_case(_load_json_bytes(case_bytes, f"case file {file_name}"))
        if case.case_id != case_id:
            raise ContractViolation(
                f"case file {file_name} identity does not match its manifest entry"
            )
        cases.append(case)

    actual_json_files = {path.name for path in root.glob("*.json")}
    expected_json_files = {"manifest.json", *(f"{case_id}.json" for case_id in CASE_IDS)}
    if actual_json_files != expected_json_files:
        extras = sorted(actual_json_files - expected_json_files)
        missing = sorted(expected_json_files - actual_json_files)
        raise ContractViolation(
            f"case directory JSON set drifted; missing={missing}, unknown={extras}"
        )
    return tuple(cases)


def _validate_candidate(value: object) -> Candidate:
    candidate = _closed_map(
        value,
        ("service", "candidate_revision", "rollback_revision"),
        "case.candidate",
    )
    service = _expect_lower_id(candidate["service"], "case.candidate.service")
    candidate_revision = _expect_revision(
        candidate["candidate_revision"], "case.candidate.candidate_revision"
    )
    rollback_revision = _expect_revision(
        candidate["rollback_revision"], "case.candidate.rollback_revision"
    )
    if candidate_revision == rollback_revision:
        raise ContractViolation(
            "case candidate_revision and rollback_revision must be different"
        )
    return Candidate(
        service=service,
        candidate_revision=candidate_revision,
        rollback_revision=rollback_revision,
    )


def _validate_evidence(value: object, path: str) -> EvidenceSnapshot:
    evidence = _closed_map(value, ("slo", "deployment", "dependency"), path)
    return EvidenceSnapshot(
        slo=_validate_slo(evidence["slo"], f"{path}.slo"),
        deployment=_validate_deployment(
            evidence["deployment"], f"{path}.deployment"
        ),
        dependency=_validate_dependency(
            evidence["dependency"], f"{path}.dependency"
        ),
    )


def _validate_slo(value: object, path: str) -> SloEvidence:
    slo = _closed_map(
        value,
        (
            "observed_at",
            "age_seconds",
            "freshness_limit_seconds",
            "baseline_error_ppm",
            "canary_error_ppm",
            "burn_rate_milli",
        ),
        path,
    )
    observed_at, _ = _expect_utc_rfc3339(slo["observed_at"], f"{path}.observed_at")
    return SloEvidence(
        observed_at=observed_at,
        age_seconds=_expect_int_range(
            slo["age_seconds"], f"{path}.age_seconds", minimum=0
        ),
        freshness_limit_seconds=_expect_int_range(
            slo["freshness_limit_seconds"],
            f"{path}.freshness_limit_seconds",
            minimum=1,
        ),
        baseline_error_ppm=_expect_int_range(
            slo["baseline_error_ppm"],
            f"{path}.baseline_error_ppm",
            minimum=0,
            maximum=1_000_000,
        ),
        canary_error_ppm=_expect_int_range(
            slo["canary_error_ppm"],
            f"{path}.canary_error_ppm",
            minimum=0,
            maximum=1_000_000,
        ),
        burn_rate_milli=_expect_int_range(
            slo["burn_rate_milli"], f"{path}.burn_rate_milli", minimum=0
        ),
    )


def _validate_deployment(value: object, path: str) -> DeploymentEvidence:
    deployment = _closed_map(
        value,
        (
            "observed_at",
            "age_seconds",
            "freshness_limit_seconds",
            "candidate_only_change",
            "rollback_ready",
            "configuration_drift",
        ),
        path,
    )
    observed_at, _ = _expect_utc_rfc3339(
        deployment["observed_at"], f"{path}.observed_at"
    )
    return DeploymentEvidence(
        observed_at=observed_at,
        age_seconds=_expect_int_range(
            deployment["age_seconds"], f"{path}.age_seconds", minimum=0
        ),
        freshness_limit_seconds=_expect_int_range(
            deployment["freshness_limit_seconds"],
            f"{path}.freshness_limit_seconds",
            minimum=1,
        ),
        candidate_only_change=_expect_bool(
            deployment["candidate_only_change"], f"{path}.candidate_only_change"
        ),
        rollback_ready=_expect_bool(
            deployment["rollback_ready"], f"{path}.rollback_ready"
        ),
        configuration_drift=_expect_bool(
            deployment["configuration_drift"], f"{path}.configuration_drift"
        ),
    )


def _validate_dependency(value: object, path: str) -> DependencyEvidence:
    dependency = _closed_map(
        value,
        (
            "observed_at",
            "age_seconds",
            "freshness_limit_seconds",
            "baseline_impacted",
            "canary_impacted",
        ),
        path,
    )
    observed_at, _ = _expect_utc_rfc3339(
        dependency["observed_at"], f"{path}.observed_at"
    )
    return DependencyEvidence(
        observed_at=observed_at,
        age_seconds=_expect_int_range(
            dependency["age_seconds"], f"{path}.age_seconds", minimum=0
        ),
        freshness_limit_seconds=_expect_int_range(
            dependency["freshness_limit_seconds"],
            f"{path}.freshness_limit_seconds",
            minimum=1,
        ),
        baseline_impacted=_expect_bool(
            dependency["baseline_impacted"], f"{path}.baseline_impacted"
        ),
        canary_impacted=_expect_bool(
            dependency["canary_impacted"], f"{path}.canary_impacted"
        ),
    )


def _validate_fault(value: object) -> FaultControls:
    fault = _closed_map(value, ("slow_analyzer", "checkpoint_pause"), "case.fault")
    slow_value = fault["slow_analyzer"]
    slow_analyzer = (
        None
        if slow_value is None
        else _expect_enum(slow_value, ANALYZER_IDS, "case.fault.slow_analyzer")
    )
    checkpoint_pause = _expect_bool(
        fault["checkpoint_pause"], "case.fault.checkpoint_pause"
    )
    if slow_analyzer is not None and checkpoint_pause:
        raise ContractViolation(
            "case.fault cannot combine slow_analyzer and checkpoint_pause"
        )
    return FaultControls(
        slow_analyzer=slow_analyzer, checkpoint_pause=checkpoint_pause
    )


def _validate_expected(value: object) -> ExpectedOutcome:
    expected = _closed_map(
        value,
        ("a2a_state", "recommendation", "reconciliation_attempts"),
        "case.expected",
    )
    recommendation_value = expected["recommendation"]
    recommendation = (
        None
        if recommendation_value is None
        else _expect_enum(
            recommendation_value, RECOMMENDATIONS, "case.expected.recommendation"
        )
    )
    return ExpectedOutcome(
        a2a_state=_expect_enum(
            expected["a2a_state"], A2A_CASE_STATES, "case.expected.a2a_state"
        ),
        recommendation=recommendation,
        reconciliation_attempts=_expect_int_range(
            expected["reconciliation_attempts"],
            "case.expected.reconciliation_attempts",
            minimum=0,
            maximum=1,
        ),
    )


def _validate_reconciliation_progress(
    initial: EvidenceSnapshot, reconciled: EvidenceSnapshot
) -> None:
    for evidence_name in ("slo", "deployment", "dependency"):
        before = getattr(initial, evidence_name)
        after = getattr(reconciled, evidence_name)
        _, before_time = _expect_utc_rfc3339(
            before.observed_at, f"case.evidence.{evidence_name}.observed_at"
        )
        _, after_time = _expect_utc_rfc3339(
            after.observed_at, f"case.reconciliation.{evidence_name}.observed_at"
        )
        if after_time < before_time:
            raise ContractViolation(
                f"case.reconciliation.{evidence_name}.observed_at cannot move backward"
            )
        if after.freshness_limit_seconds != before.freshness_limit_seconds:
            raise ContractViolation(
                f"case.reconciliation.{evidence_name} cannot change the freshness limit"
            )
        if after_time == before_time and after.age_seconds > before.age_seconds:
            raise ContractViolation(
                f"case.reconciliation.{evidence_name}.age_seconds cannot increase "
                "without a later observation"
            )


def _validate_packages(value: object) -> PackageVersions:
    packages = _closed_map(value, PACKAGE_NAMES, "recommendation_artifact.packages")
    validated = {
        name: _expect_package_version(
            packages[name], f"recommendation_artifact.packages.{name}"
        )
        for name in PACKAGE_NAMES
    }
    return PackageVersions(
        agent_framework_core=validated["agent-framework-core"],
        agent_framework_a2a=validated["agent-framework-a2a"],
        autogen_agentchat=validated["autogen-agentchat"],
        a2a_sdk=validated["a2a-sdk"],
    )


def _bind_artifact_to_request(
    artifact: RecommendationArtifact, request: AnalysisRequest
) -> None:
    bindings = {
        "run_id": request.run_id,
        "source_revision": request.source_revision,
        "case_id": request.case_id,
        "case_digest": request.case_digest,
        "candidate_revision": request.candidate_revision,
    }
    for field_name, expected_value in bindings.items():
        if getattr(artifact, field_name) != expected_value:
            raise ContractViolation(
                f"recommendation_artifact.{field_name} does not match the analysis request"
            )


def _closed_map(
    value: object, expected_fields: Sequence[str], path: str
) -> Mapping[str, object]:
    if type(value) is not dict:
        raise ContractViolation(f"{path} must be an object")
    expected = set(expected_fields)
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing:
        raise ContractViolation(f"{path} has missing fields: {missing}")
    if unknown:
        raise ContractViolation(f"{path} has unknown fields: {unknown}")
    return value


def _expect_version(value: object, expected: str, path: str) -> str:
    actual = _expect_string(value, path)
    if actual != expected:
        raise ContractViolation(f"{path} must be {expected!r}")
    return actual


def _expect_enum(value: object, allowed: Sequence[str], path: str) -> str:
    actual = _expect_string(value, path)
    if actual not in allowed:
        raise ContractViolation(f"{path} must be one of {tuple(allowed)!r}")
    return actual


def _expect_string(value: object, path: str) -> str:
    if type(value) is not str:
        raise ContractViolation(f"{path} must be a string")
    return value


def _expect_lower_id(value: object, path: str) -> str:
    actual = _expect_string(value, path)
    if _LOWER_ID.fullmatch(actual) is None:
        raise ContractViolation(f"{path} is not a valid lowercase ID")
    return actual


def _expect_id(value: object, path: str) -> str:
    return _expect_lower_id(value, path)


def _expect_opaque_id(value: object, path: str) -> str:
    actual = _expect_string(value, path)
    if _OPAQUE_ID.fullmatch(actual) is None:
        raise ContractViolation(f"{path} is not a valid non-empty ID")
    return actual


def _expect_revision(value: object, path: str) -> str:
    actual = _expect_string(value, path)
    if _REVISION.fullmatch(actual) is None:
        raise ContractViolation(f"{path} must be 40 lowercase hexadecimal characters")
    return actual


def _expect_digest(value: object, path: str) -> str:
    actual = _expect_string(value, path)
    if _SHA256.fullmatch(actual) is None:
        raise ContractViolation(f"{path} must be 64 lowercase hexadecimal characters")
    return actual


def _expect_bool(value: object, path: str) -> bool:
    if type(value) is not bool:
        raise ContractViolation(f"{path} must be a boolean")
    return value


def _expect_int_range(
    value: object,
    path: str,
    *,
    minimum: int,
    maximum: int | None = None,
) -> int:
    if type(value) is not int:
        raise ContractViolation(f"{path} must be an integer, not a boolean or other type")
    if value < minimum or (maximum is not None and value > maximum):
        range_text = f">= {minimum}" if maximum is None else f"in {minimum}..{maximum}"
        raise ContractViolation(f"{path} must be {range_text}")
    return value


def _expect_utc_rfc3339(value: object, path: str) -> tuple[str, datetime]:
    actual = _expect_string(value, path)
    if _UTC_RFC3339.fullmatch(actual) is None:
        raise ContractViolation(f"{path} must be UTC RFC3339 using the Z designator")
    try:
        parsed = datetime.fromisoformat(actual[:-1] + "+00:00")
    except ValueError as exc:
        raise ContractViolation(f"{path} is not a real UTC RFC3339 instant") from exc
    return actual, parsed


def _expect_token_list(
    value: object,
    path: str,
    *,
    allow_empty: bool = True,
    stable_sorted: bool = False,
) -> tuple[str, ...]:
    if type(value) is not list:
        raise ContractViolation(f"{path} must be an array")
    items: list[str] = []
    for index, item in enumerate(value):
        token = _expect_string(item, f"{path}[{index}]")
        if _TOKEN.fullmatch(token) is None:
            raise ContractViolation(f"{path}[{index}] is not a valid token")
        items.append(token)
    if not allow_empty and not items:
        raise ContractViolation(f"{path} cannot be empty")
    if len(set(items)) != len(items):
        raise ContractViolation(f"{path} cannot contain duplicates")
    if stable_sorted and items != sorted(items):
        raise ContractViolation(f"{path} must be stable-sorted")
    return tuple(items)


def _expect_package_version(value: object, path: str) -> str:
    actual = _expect_string(value, path)
    if not actual or len(actual) > 128 or actual.strip() != actual:
        raise ContractViolation(f"{path} must be a non-empty installed version string")
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in actual):
        raise ContractViolation(f"{path} contains a control character")
    return actual


def _load_json_bytes(value: bytes, path: str) -> object:
    def object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, item in pairs:
            if key in result:
                raise ContractViolation(f"{path} contains duplicate field {key!r}")
            result[key] = item
        return result

    try:
        return json.loads(value.decode("utf-8"), object_pairs_hook=object_pairs)
    except UnicodeDecodeError as exc:
        raise ContractViolation(f"{path} is not UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise ContractViolation(f"{path} is not valid JSON: {exc.msg}") from exc
