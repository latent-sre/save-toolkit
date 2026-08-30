"""Final Agent Framework HITL checkpoint and release-decision persistence."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from agent_framework import (
    Executor,
    FileCheckpointStorage,
    WorkflowBuilder,
    handler,
    response_handler,
)
from google.protobuf.json_format import MessageToDict

from .contracts import (
    DECISION_VERSION,
    ContractViolation,
    RecommendationArtifact,
    ReleaseDecision,
    canonical_json_bytes,
    to_plain_object,
    validate_decision_replay,
    validate_recommendation_artifact,
    validate_release_decision,
)
from .maf_orchestrator import RemoteAnalysisResult


APPROVAL_REQUEST_VERSION = "release-approval-request/v1"
_WORKFLOW_NAME_PREFIX = "release-approval-gate-v1"
_EXECUTOR_ID = "final_release_approval"
_RESPONSE_FIELDS = (
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
)


class ApprovalGateError(RuntimeError):
    """The final approval boundary rejected unsafe or inconsistent state."""


@dataclass(frozen=True, slots=True)
class PendingApproval:
    checkpoint_id: str
    request_id: str
    request_info_count: int
    workflow_name: str
    request_object: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class ApprovalOutcome:
    decision: ReleaseDecision
    decision_path: Path
    replayed: bool
    request_info_count: int
    restored_checkpoint_id: str


class _FinalApprovalExecutor(Executor):
    """Emit one external request and yield only the closed response record."""

    def __init__(self) -> None:
        super().__init__(id=_EXECUTOR_ID)

    @handler(input=dict)
    async def request_final_approval(self, request, context) -> None:
        request_id = _request_id(request)
        await context.request_info(request, dict, request_id=request_id)

    @response_handler(request=dict, response=dict, workflow_output=dict)
    async def handle_final_decision(
        self, original_request, response, context
    ) -> None:
        del original_request
        await context.yield_output(
            {"decision_version": DECISION_VERSION, **response}
        )


async def open_approval_gate(
    result: RemoteAnalysisResult,
    *,
    checkpoint_directory: str | Path,
) -> PendingApproval:
    """Validate a completed recommendation and persist one real MAF pause."""

    artifact = _validated_completed_artifact(result)
    checkpoint_root = _existing_directory(
        checkpoint_directory, "checkpoint_directory"
    )
    request_object = _approval_request(artifact)
    workflow_name = _workflow_name(artifact.run_id)
    storage = FileCheckpointStorage(checkpoint_root)
    workflow = _build_workflow(storage, workflow_name)

    run_result = await workflow.run(dict(request_object))
    request_events = run_result.get_request_info_events()
    if len(request_events) != 1:
        raise ApprovalGateError("approval workflow did not emit exactly one request_info")
    if run_result.get_outputs():
        raise ApprovalGateError("pending approval workflow emitted an output")
    event = request_events[0]
    if event.data != request_object:
        raise ApprovalGateError("approval request_info payload changed in the workflow")

    checkpoint = await storage.get_latest(workflow_name=workflow_name)
    if checkpoint is None:
        raise ApprovalGateError("approval workflow did not persist a checkpoint")
    _validate_pending_checkpoint(
        checkpoint,
        checkpoint_id=checkpoint.checkpoint_id,
        workflow_name=workflow_name,
        request_object=request_object,
    )
    return PendingApproval(
        checkpoint_id=checkpoint.checkpoint_id,
        request_id=event.request_id,
        request_info_count=1,
        workflow_name=workflow_name,
        request_object=request_object,
    )


async def resume_approval_gate(
    *,
    artifact_object: Mapping[str, object] | None,
    checkpoint_directory: str | Path,
    decision_directory: str | Path,
    checkpoint_id: str,
    response: Mapping[str, object],
    at_time: datetime,
) -> ApprovalOutcome:
    """Restore one MAF pause, validate its exact decision, and persist it once."""

    checkpoint_root = _existing_directory(
        checkpoint_directory, "checkpoint_directory"
    )
    decision_root = _existing_directory(decision_directory, "decision_directory")
    if type(checkpoint_id) is not str or not checkpoint_id:
        raise ApprovalGateError("checkpoint_id must be a non-empty string")
    try:
        artifact = validate_recommendation_artifact(artifact_object)
    except (ContractViolation, TypeError) as exc:
        raise ApprovalGateError(f"recommendation artifact rejected: {exc}") from exc

    workflow_name = _workflow_name(artifact.run_id)
    request_object = _approval_request(artifact)
    storage = FileCheckpointStorage(checkpoint_root)
    try:
        checkpoint = await storage.load(checkpoint_id)
    except Exception as exc:  # framework translates file and decoding failures
        raise ApprovalGateError(f"approval checkpoint could not be loaded: {exc}") from exc
    request_event = _validate_pending_checkpoint(
        checkpoint,
        checkpoint_id=checkpoint_id,
        workflow_name=workflow_name,
        request_object=request_object,
    )
    decision_value = _decision_value(response)
    try:
        expected_decision = validate_release_decision(
            decision_value,
            artifact=artifact,
            at_time=at_time,
        )
    except (ContractViolation, TypeError) as exc:
        raise ApprovalGateError(f"release decision rejected: {exc}") from exc

    workflow = _build_workflow(FileCheckpointStorage(checkpoint_root), workflow_name)
    run_result = await workflow.run(
        checkpoint_id=checkpoint_id,
        responses={request_event.request_id: dict(response)},
    )
    if run_result.get_request_info_events():
        raise ApprovalGateError("resumed approval workflow emitted another request_info")
    outputs = run_result.get_outputs()
    if len(outputs) != 1:
        raise ApprovalGateError("resumed approval workflow did not emit one decision")
    try:
        actual_decision = validate_release_decision(
            outputs[0], artifact=artifact, at_time=at_time
        )
    except (ContractViolation, TypeError) as exc:
        raise ApprovalGateError(f"resumed release decision rejected: {exc}") from exc
    if actual_decision != expected_decision:
        raise ApprovalGateError("resumed release decision changed after validation")

    decision_path, replayed = _persist_decision(
        decision_root,
        actual_decision,
        artifact=artifact,
        at_time=at_time,
    )
    return ApprovalOutcome(
        decision=actual_decision,
        decision_path=decision_path,
        replayed=replayed,
        request_info_count=0,
        restored_checkpoint_id=checkpoint_id,
    )


def _build_workflow(storage: FileCheckpointStorage, workflow_name: str):
    executor = _FinalApprovalExecutor()
    return WorkflowBuilder(
        start_executor=executor,
        checkpoint_storage=storage,
        output_from=[executor],
        # One superstep handles the response and one proves convergence.
        max_iterations=2,
        name=workflow_name,
    ).build()


def _validated_completed_artifact(
    result: RemoteAnalysisResult,
) -> RecommendationArtifact:
    if not isinstance(result, RemoteAnalysisResult):
        raise ApprovalGateError("approval requires a RemoteAnalysisResult")
    if result.a2a_state != "completed":
        raise ApprovalGateError("approval is forbidden for a non-completed A2A task")
    if result.request_info_count != 0:
        raise ApprovalGateError("approval is forbidden after an earlier request_info")
    if result.authoritative_part is None:
        raise ApprovalGateError("completed A2A result lacks the authoritative data Part")
    if result.authoritative_part.WhichOneof("content") != "data":
        raise ApprovalGateError("authoritative A2A Part is not data content")
    try:
        artifact = validate_recommendation_artifact(result.artifact_object)
    except (ContractViolation, TypeError) as exc:
        raise ApprovalGateError(f"recommendation artifact rejected: {exc}") from exc
    if result.task_id != artifact.a2a_task_id:
        raise ApprovalGateError("A2A task lineage does not match the artifact")
    if result.context_id != artifact.a2a_context_id:
        raise ApprovalGateError("A2A context lineage does not match the artifact")
    if result.artifact_id != artifact.artifact_id:
        raise ApprovalGateError("A2A artifact ID does not match the artifact data")
    part_object = _normalize_integral_numbers(
        MessageToDict(
            result.authoritative_part.data,
            preserving_proto_field_name=True,
        )
    )
    if part_object != to_plain_object(artifact):
        raise ApprovalGateError("authoritative A2A Part bytes do not match the artifact")
    return artifact


def _approval_request(artifact: RecommendationArtifact) -> dict[str, object]:
    return {
        "approval_request_version": APPROVAL_REQUEST_VERSION,
        "run_id": artifact.run_id,
        "source_revision": artifact.source_revision,
        "case_id": artifact.case_id,
        "case_digest": artifact.case_digest,
        "candidate_revision": artifact.candidate_revision,
        "artifact_digest": artifact.artifact_digest,
        "recommendation": artifact.recommendation,
    }


def _request_id(request: Mapping[str, object]) -> str:
    digest = request.get("artifact_digest")
    if type(digest) is not str or len(digest) != 64:
        raise ApprovalGateError("approval request lacks an artifact digest")
    return f"final-approval-{digest}"


def _workflow_name(run_id: str) -> str:
    return f"{_WORKFLOW_NAME_PREFIX}-{run_id}"


def _validate_pending_checkpoint(
    checkpoint,
    *,
    checkpoint_id: str,
    workflow_name: str,
    request_object: Mapping[str, object],
):
    if checkpoint.checkpoint_id != checkpoint_id:
        raise ApprovalGateError("approval checkpoint ID changed while loading")
    if checkpoint.workflow_name != workflow_name:
        raise ApprovalGateError("approval checkpoint belongs to a different workflow")
    pending = checkpoint.pending_request_info_events
    if len(pending) != 1:
        raise ApprovalGateError(
            "approval checkpoint does not contain exactly one pending request"
        )
    event = next(iter(pending.values()))
    if event.type != "request_info" or type(event.data) is not dict:
        raise ApprovalGateError("approval checkpoint pending request is malformed")
    if event.data != request_object:
        raise ApprovalGateError("approval checkpoint is not bound to the artifact")
    if event.request_id != _request_id(request_object):
        raise ApprovalGateError("approval checkpoint request ID is not artifact-bound")
    return event


def _decision_value(response: Mapping[str, object]) -> dict[str, object]:
    if type(response) is not dict:
        raise ApprovalGateError("approval response must be a plain object")
    missing = sorted(set(_RESPONSE_FIELDS) - set(response))
    unknown = sorted(set(response) - set(_RESPONSE_FIELDS))
    if missing:
        raise ApprovalGateError(f"approval response has missing fields: {missing}")
    if unknown:
        raise ApprovalGateError(f"approval response has unknown fields: {unknown}")
    return {"decision_version": DECISION_VERSION, **response}


def _persist_decision(
    root: Path,
    decision: ReleaseDecision,
    *,
    artifact: RecommendationArtifact,
    at_time: datetime,
) -> tuple[Path, bool]:
    path = root / f"{decision.run_id}.release-decision.json"
    value = canonical_json_bytes(decision)
    if path.exists():
        try:
            existing_bytes = path.read_bytes()
            existing_object = json.loads(existing_bytes.decode("utf-8"))
            existing = validate_release_decision(
                existing_object, artifact=artifact, at_time=at_time
            )
            if existing_bytes != canonical_json_bytes(existing):
                raise ContractViolation("existing decision file is not canonical JSON")
            validate_decision_replay(existing, decision)
        except (OSError, UnicodeError, json.JSONDecodeError, ContractViolation) as exc:
            raise ApprovalGateError(f"decision replay rejected: {exc}") from exc
        return path, True
    _atomic_write(path, value)
    return path, False


def _atomic_write(path: Path, value: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _existing_directory(value: str | Path, label: str) -> Path:
    root = Path(value)
    if not root.is_dir():
        raise ApprovalGateError(f"{label} must be an existing directory")
    return root


def _normalize_integral_numbers(value: object) -> object:
    if type(value) is float and value.is_integer():
        return int(value)
    if isinstance(value, dict):
        return {key: _normalize_integral_numbers(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_integral_numbers(item) for item in value]
    return value
