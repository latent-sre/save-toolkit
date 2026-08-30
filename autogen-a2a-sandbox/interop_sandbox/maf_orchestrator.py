"""Microsoft Agent Framework client workflow for the A2A analysis worker."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx
from a2a.client import A2ACardResolver
from a2a.types import Part, TaskArtifactUpdateEvent, TaskState
from agent_framework import AgentExecutor, AgentResponseUpdate, WorkflowBuilder
from agent_framework.a2a import A2AAgent
from google.protobuf.json_format import MessageToDict

from .contracts import (
    ContractViolation,
    parse_analysis_request_json,
    validate_recommendation_artifact,
)


_A2A_STATES = {
    "TASK_STATE_COMPLETED": "completed",
    "TASK_STATE_INPUT_REQUIRED": "input-required",
    "TASK_STATE_CANCELED": "canceled",
    "TASK_STATE_FAILED": "failed",
    "TASK_STATE_REJECTED": "failed",
}


@dataclass(frozen=True, slots=True)
class RemoteAnalysisResult:
    """Closed transport result consumed by the later approval workflow."""

    a2a_state: str
    task_id: str
    context_id: str
    artifact_id: str | None
    artifact_object: Mapping[str, object] | None
    authoritative_part: Part | None
    request_info_count: int
    used_streaming_workflow: bool


async def run_remote_analysis(
    *,
    agent_base_url: str,
    request_text: str,
) -> RemoteAnalysisResult:
    """Discover, invoke, and validate one remote analysis through a MAF workflow."""

    if not agent_base_url.startswith("http://"):
        raise ValueError("agent_base_url must be an HTTP URL")
    if type(request_text) is not str or not request_text:
        raise ValueError("request_text must be a non-empty string")

    timeout = httpx.Timeout(10.0, connect=3.0)
    async with httpx.AsyncClient(timeout=timeout) as discovery_client:
        resolver = A2ACardResolver(discovery_client, agent_base_url)
        card = await resolver.get_agent_card()

    async with A2AAgent(
        id="remote_canary_worker",
        name="remote_canary_worker",
        description="Remote deterministic canary evidence worker",
        agent_card=card,
        timeout=timeout,
        supported_protocol_bindings=["JSONRPC"],
    ) as remote_agent:
        session = remote_agent.create_session()
        executor = AgentExecutor(
            remote_agent,
            session=session,
            id="remote_canary_worker_executor",
        )
        workflow = WorkflowBuilder(
            start_executor=executor,
            output_from=[executor],
            # The first superstep invokes the agent; the second drains the
            # terminal executor response through MAF's normal edge runner.
            max_iterations=2,
            name="remote_canary_analysis",
        ).build()
        stream = workflow.run(request_text, stream=True)
        async for _event in stream:
            pass
        run_result = await stream.get_final_response()

    service_state = session.service_session_id
    if not isinstance(service_state, Mapping):
        raise RuntimeError("A2AAgent did not persist task lineage on its session")
    task_id = service_state.get("task_id")
    context_id = service_state.get("context_id")
    raw_task_state = service_state.get("task_state")
    if not isinstance(task_id, str) or not task_id:
        raise RuntimeError("A2AAgent session is missing the task ID")
    if not isinstance(context_id, str) or not context_id:
        raise RuntimeError("A2AAgent session is missing the context ID")
    if not isinstance(raw_task_state, int):
        raise RuntimeError("A2AAgent session is missing the task state")
    state_name = TaskState.Name(raw_task_state)
    if state_name not in _A2A_STATES:
        raise RuntimeError(f"A2A task stopped in unsupported state {state_name}")
    a2a_state = _A2A_STATES[state_name]

    artifact_events = _artifact_events(run_result.get_outputs())
    if len(artifact_events) > 1:
        raise RuntimeError("A2A task emitted more than one artifact")
    artifact_id: str | None = None
    artifact_object: Mapping[str, object] | None = None
    authoritative_part: Part | None = None
    if artifact_events:
        event = artifact_events[0]
        if event.task_id != task_id or event.context_id != context_id:
            raise RuntimeError("A2A artifact lineage does not match the task session")
        artifact = event.artifact
        if len(artifact.parts) != 1:
            raise RuntimeError("recommendation artifact must contain exactly one Part")
        part = artifact.parts[0]
        if part.WhichOneof("content") != "data":
            raise RuntimeError("recommendation artifact must use the A2A data Part")
        plain = _part_data_object(part)
        try:
            request = parse_analysis_request_json(request_text)
        except ContractViolation:
            request = None
        validated = validate_recommendation_artifact(plain, request=request)
        artifact_id = artifact.artifact_id
        if artifact.name != "release-recommendation.json":
            raise RuntimeError("A2A recommendation artifact has an unexpected name")
        if artifact_id != validated.artifact_id:
            raise RuntimeError("A2A artifact ID does not match its data object")
        artifact_object = plain
        authoritative_part = part

    if a2a_state == "completed" and authoritative_part is None:
        raise RuntimeError("completed A2A task did not emit a recommendation artifact")
    if a2a_state != "completed" and authoritative_part is not None:
        raise RuntimeError("non-completed A2A task emitted a recommendation artifact")

    return RemoteAnalysisResult(
        a2a_state=a2a_state,
        task_id=task_id,
        context_id=context_id,
        artifact_id=artifact_id,
        artifact_object=artifact_object,
        authoritative_part=authoritative_part,
        request_info_count=len(run_result.get_request_info_events()),
        used_streaming_workflow=True,
    )


def _artifact_events(outputs: list[Any]) -> tuple[TaskArtifactUpdateEvent, ...]:
    events: list[TaskArtifactUpdateEvent] = []
    for output in outputs:
        if not isinstance(output, AgentResponseUpdate):
            raise RuntimeError("MAF workflow emitted an unexpected output type")
        if isinstance(output.raw_representation, TaskArtifactUpdateEvent):
            events.append(output.raw_representation)
    return tuple(events)


def _part_data_object(part: Part) -> Mapping[str, object]:
    decoded = MessageToDict(part.data, preserving_proto_field_name=True)
    normalized = _normalize_integral_numbers(decoded)
    if not isinstance(normalized, dict):
        raise RuntimeError("A2A data Part must contain an object")
    return normalized


def _normalize_integral_numbers(value: object) -> object:
    """Restore JSON integer semantics lost by protobuf Value's double storage."""

    if type(value) is float and value.is_integer():
        return int(value)
    if isinstance(value, dict):
        return {key: _normalize_integral_numbers(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_integral_numbers(item) for item in value]
    return value
