"""Microsoft Agent Framework client workflow for the A2A analysis worker."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.helpers.proto_helpers import new_text_message
from a2a.types import (
    CancelTaskRequest,
    GetTaskRequest,
    Message as A2AMessage,
    Part,
    Role,
    SendMessageRequest,
    StreamResponse,
    SubscribeToTaskRequest,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatusUpdateEvent,
)
from agent_framework import (
    AgentExecutor,
    AgentResponseUpdate,
    WorkflowBuilder,
    WorkflowEvent,
    WorkflowRunState,
)
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
_OBSERVED_A2A_STATES = {
    "TASK_STATE_SUBMITTED": "submitted",
    "TASK_STATE_WORKING": "working",
    **_A2A_STATES,
}
_EVENT_KINDS = {
    "workflow_working",
    "task",
    "status",
    "data_artifact",
    "message",
    "session",
}
_EVENT_TIMELINE_VERSION = "a2a-event-timeline/v1"
_MAX_TIMELINE_EVENTS = 64


@dataclass(frozen=True, slots=True)
class RemoteEvent:
    """One bounded transport observation without diagnostic or payload text."""

    sequence: int
    event_kind: str
    task_id: str | None
    context_id: str | None
    a2a_state: str | None
    artifact_id: str | None


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
    event_timeline: tuple[RemoteEvent, ...] = ()


@dataclass(frozen=True, slots=True)
class RemoteTaskRecovery:
    """Protocol observations proving recovery or cancel used one A2A task."""

    initial_task_id: str
    observed_task_ids: tuple[str, ...]
    subscription_event_count: int
    cancel_sent_task_id: str | None
    result: RemoteAnalysisResult
    event_timeline: tuple[RemoteEvent, ...] = ()


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
        timeline: list[RemoteEvent] = []
        async for event in stream:
            _append_workflow_event(timeline, event)
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
    _append_event(
        timeline,
        event_kind="session",
        task_id=task_id,
        context_id=context_id,
        a2a_state=a2a_state,
    )

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

    event_timeline = validate_event_timeline(
        event_timeline_to_plain_object(tuple(timeline)),
        task_id=task_id,
        context_id=context_id,
        terminal_state=a2a_state,
        artifact_id=artifact_id,
    )
    return RemoteAnalysisResult(
        a2a_state=a2a_state,
        task_id=task_id,
        context_id=context_id,
        artifact_id=artifact_id,
        artifact_object=artifact_object,
        authoritative_part=authoritative_part,
        request_info_count=len(run_result.get_request_info_events()),
        used_streaming_workflow=True,
        event_timeline=event_timeline,
    )


async def recover_remote_analysis_after_interruption(
    *,
    agent_base_url: str,
    request_text: str,
) -> RemoteTaskRecovery:
    """Abandon one real SSE stream, then subscribe to and fetch that task."""

    _validate_remote_inputs(agent_base_url, request_text)
    client = await _create_raw_client(agent_base_url)
    async with client:
        stream = client.send_message(_send_request(request_text))
        initial_task_id, observed, timeline = await _abandon_after_task_id(stream)
        subscription_events = 0
        async with asyncio.timeout(10):
            async for event in client.subscribe(
                SubscribeToTaskRequest(id=initial_task_id)
            ):
                subscription_events += 1
                observed.extend(_stream_response_task_ids(event))
                _append_stream_response(timeline, event)
        task = await client.get_task(GetTaskRequest(id=initial_task_id))

    observed.append(task.id)
    result = _result_from_task(task, request_text=request_text, timeline=timeline)
    _require_same_task(initial_task_id, observed, result.task_id)
    return RemoteTaskRecovery(
        initial_task_id=initial_task_id,
        observed_task_ids=tuple(observed),
        subscription_event_count=subscription_events,
        cancel_sent_task_id=None,
        result=result,
        event_timeline=result.event_timeline,
    )


async def cancel_remote_analysis_after_interruption(
    *,
    agent_base_url: str,
    request_text: str,
) -> RemoteTaskRecovery:
    """Abandon a working stream and cancel the server-issued task ID."""

    _validate_remote_inputs(agent_base_url, request_text)
    client = await _create_raw_client(agent_base_url)
    async with client:
        stream = client.send_message(_send_request(request_text))
        initial_task_id, observed, timeline = await _abandon_after_task_id(
            stream, require_working=True
        )
        canceled = await client.cancel_task(CancelTaskRequest(id=initial_task_id))
        observed.append(canceled.id)
        _append_raw_event(timeline, canceled)
        task = await client.get_task(GetTaskRequest(id=initial_task_id))

    observed.append(task.id)
    result = _result_from_task(task, request_text=request_text, timeline=timeline)
    _require_same_task(initial_task_id, observed, result.task_id)
    if result.a2a_state != "canceled":
        raise RuntimeError("CancelTask did not leave the same A2A task canceled")
    return RemoteTaskRecovery(
        initial_task_id=initial_task_id,
        observed_task_ids=tuple(observed),
        subscription_event_count=0,
        cancel_sent_task_id=initial_task_id,
        result=result,
        event_timeline=result.event_timeline,
    )


def event_timeline_to_plain_object(
    timeline: tuple[RemoteEvent, ...],
) -> dict[str, object]:
    """Convert the immutable bounded timeline to its persistence object."""

    if not isinstance(timeline, tuple) or not all(
        isinstance(event, RemoteEvent) for event in timeline
    ):
        raise TypeError("timeline must be a tuple of RemoteEvent values")
    return {
        "events": [
            {
                "a2a_state": event.a2a_state,
                "artifact_id": event.artifact_id,
                "context_id": event.context_id,
                "event_kind": event.event_kind,
                "sequence": event.sequence,
                "task_id": event.task_id,
            }
            for event in timeline
        ],
        "timeline_version": _EVENT_TIMELINE_VERSION,
    }


def validate_event_timeline(
    value: object,
    *,
    task_id: str,
    context_id: str,
    terminal_state: str,
    artifact_id: str | None,
) -> tuple[RemoteEvent, ...]:
    """Validate a persisted timeline against one terminal A2A task lineage."""

    if type(value) is not dict or set(value) != {"events", "timeline_version"}:
        raise ValueError("event timeline must be a closed object")
    if value["timeline_version"] != _EVENT_TIMELINE_VERSION:
        raise ValueError("event timeline version is unsupported")
    task_id = _nonempty_id(task_id, "task_id")
    context_id = _nonempty_id(context_id, "context_id")
    if terminal_state not in _A2A_STATES.values():
        raise ValueError("event timeline terminal state is unsupported")
    if artifact_id is not None:
        artifact_id = _nonempty_id(artifact_id, "artifact_id")
    events_value = value["events"]
    if (
        type(events_value) is not list
        or not events_value
        or len(events_value) > _MAX_TIMELINE_EVENTS
    ):
        raise ValueError("event timeline must contain 1..64 events")

    events: list[RemoteEvent] = []
    for sequence, event_value in enumerate(events_value):
        if type(event_value) is not dict or set(event_value) != {
            "a2a_state",
            "artifact_id",
            "context_id",
            "event_kind",
            "sequence",
            "task_id",
        }:
            raise ValueError("event timeline entry must be closed")
        if event_value["sequence"] != sequence:
            raise ValueError("event timeline sequence is not contiguous")
        event_kind = event_value["event_kind"]
        if type(event_kind) is not str or event_kind not in _EVENT_KINDS:
            raise ValueError("event timeline kind is unsupported")
        observed_task_id = _optional_id(event_value["task_id"], "event task_id")
        observed_context_id = _optional_id(
            event_value["context_id"], "event context_id"
        )
        if observed_task_id is not None and observed_task_id != task_id:
            raise ValueError("event timeline contains more than one task lineage")
        if observed_context_id is not None and observed_context_id != context_id:
            raise ValueError("event timeline contains more than one context lineage")
        observed_state = event_value["a2a_state"]
        if observed_state is not None and observed_state not in _OBSERVED_A2A_STATES.values():
            raise ValueError("event timeline contains an unsupported A2A state")
        requires_lineage = event_kind != "workflow_working" and (
            event_kind == "data_artifact" or observed_state is not None
        )
        if requires_lineage and (
            observed_task_id != task_id or observed_context_id != context_id
        ):
            raise ValueError("event timeline lineage is missing or changed")
        observed_artifact_id = _optional_id(
            event_value["artifact_id"], "event artifact_id"
        )
        if event_kind == "workflow_working":
            if any(
                item is not None
                for item in (
                    observed_task_id,
                    observed_context_id,
                    observed_state,
                    observed_artifact_id,
                )
            ):
                raise ValueError(
                    "workflow working event cannot claim A2A protocol evidence"
                )
        elif event_kind == "data_artifact":
            if observed_artifact_id is None:
                raise ValueError("data artifact event is missing its artifact ID")
        elif observed_artifact_id is not None:
            raise ValueError("non-artifact event cannot carry an artifact ID")
        events.append(
            RemoteEvent(
                sequence=sequence,
                event_kind=event_kind,
                task_id=observed_task_id,
                context_id=observed_context_id,
                a2a_state=observed_state,
                artifact_id=observed_artifact_id,
            )
        )

    if events[-1].a2a_state != terminal_state:
        raise ValueError("event timeline does not end in the expected terminal state")
    if not any(
        event.event_kind == "workflow_working" or event.a2a_state == "working"
        for event in events[:-1]
    ):
        raise ValueError("event timeline lacks a working observation before terminal")
    data_artifacts = [event for event in events if event.event_kind == "data_artifact"]
    if terminal_state == "completed":
        if len(data_artifacts) != 1 or data_artifacts[0].artifact_id != artifact_id:
            raise ValueError("completed timeline requires exactly one bound data artifact")
    elif data_artifacts or artifact_id is not None:
        raise ValueError("non-completed timeline cannot contain an artifact")
    return tuple(events)


def _append_workflow_event(
    timeline: list[RemoteEvent], event: object
) -> None:
    if not isinstance(event, WorkflowEvent):
        raise RuntimeError("MAF workflow stream emitted an unexpected event type")
    if event.state == WorkflowRunState.IN_PROGRESS and not any(
        item.event_kind == "workflow_working" for item in timeline
    ):
        _append_event(
            timeline,
            event_kind="workflow_working",
            task_id=None,
            context_id=None,
        )
    if isinstance(event.data, AgentResponseUpdate):
        _append_raw_event(timeline, event.data.raw_representation)


def _append_stream_response(
    timeline: list[RemoteEvent], event: StreamResponse
) -> None:
    if event.HasField("task"):
        _append_raw_event(timeline, event.task)
    elif event.HasField("status_update"):
        _append_raw_event(timeline, event.status_update)
    elif event.HasField("artifact_update"):
        _append_raw_event(timeline, event.artifact_update)
    elif event.HasField("message"):
        _append_raw_event(timeline, event.message)


def _append_raw_event(timeline: list[RemoteEvent], raw: object) -> None:
    if isinstance(raw, Task):
        _append_event(
            timeline,
            event_kind="task",
            task_id=raw.id,
            context_id=raw.context_id,
            a2a_state=_observed_state(raw.status.state),
        )
    elif isinstance(raw, TaskStatusUpdateEvent):
        _append_event(
            timeline,
            event_kind="status",
            task_id=raw.task_id,
            context_id=raw.context_id,
            a2a_state=_observed_state(raw.status.state),
        )
    elif isinstance(raw, TaskArtifactUpdateEvent):
        if (
            len(raw.artifact.parts) != 1
            or raw.artifact.parts[0].WhichOneof("content") != "data"
        ):
            raise RuntimeError("streamed A2A artifact is not one data Part")
        _append_event(
            timeline,
            event_kind="data_artifact",
            task_id=raw.task_id,
            context_id=raw.context_id,
            artifact_id=raw.artifact.artifact_id,
        )
    elif isinstance(raw, A2AMessage):
        _append_event(
            timeline,
            event_kind="message",
            task_id=raw.task_id or None,
            context_id=raw.context_id or None,
        )


def _append_event(
    timeline: list[RemoteEvent],
    *,
    event_kind: str,
    task_id: str | None,
    context_id: str | None,
    a2a_state: str | None = None,
    artifact_id: str | None = None,
) -> None:
    if len(timeline) >= _MAX_TIMELINE_EVENTS:
        raise RuntimeError("A2A event timeline exceeded its 64-event bound")
    timeline.append(
        RemoteEvent(
            sequence=len(timeline),
            event_kind=event_kind,
            task_id=task_id,
            context_id=context_id,
            a2a_state=a2a_state,
            artifact_id=artifact_id,
        )
    )


def _observed_state(value: int) -> str:
    state_name = TaskState.Name(value)
    if state_name not in _OBSERVED_A2A_STATES:
        raise RuntimeError(f"A2A event used unsupported state {state_name}")
    return _OBSERVED_A2A_STATES[state_name]


def _nonempty_id(value: object, label: str) -> str:
    if type(value) is not str or not value or len(value) > 128:
        raise ValueError(f"{label} must be a non-empty bounded string")
    return value


def _optional_id(value: object, label: str) -> str | None:
    return None if value is None else _nonempty_id(value, label)


async def _create_raw_client(agent_base_url: str):
    timeout = httpx.Timeout(10.0, connect=3.0)
    async with httpx.AsyncClient(timeout=timeout) as discovery_client:
        resolver = A2ACardResolver(discovery_client, agent_base_url)
        card = await resolver.get_agent_card()
    transport_client = httpx.AsyncClient(timeout=timeout)
    factory = ClientFactory(
        ClientConfig(
            streaming=True,
            httpx_client=transport_client,
            supported_protocol_bindings=["JSONRPC"],
        )
    )
    try:
        return factory.create(card)
    except Exception:
        await transport_client.aclose()
        raise


def _send_request(request_text: str) -> SendMessageRequest:
    return SendMessageRequest(
        message=new_text_message(request_text, role=Role.ROLE_USER)
    )


async def _abandon_after_task_id(
    stream,
    *,
    require_working: bool = False,
) -> tuple[str, list[str], list[RemoteEvent]]:
    task_id: str | None = None
    observed: list[str] = []
    timeline: list[RemoteEvent] = []
    try:
        async with asyncio.timeout(10):
            async for event in stream:
                _append_stream_response(timeline, event)
                event_ids = _stream_response_task_ids(event)
                observed.extend(event_ids)
                if task_id is None and event_ids:
                    task_id = event_ids[0]
                if task_id is None:
                    continue
                if not require_working or _is_working_event(event):
                    break
    finally:
        await stream.aclose()
    if task_id is None:
        raise RuntimeError("A2A stream ended before the server issued a task ID")
    _require_same_task(task_id, observed, task_id)
    return task_id, observed, timeline


def _is_working_event(event: StreamResponse) -> bool:
    return event.HasField("status_update") and (
        event.status_update.status.state == TaskState.TASK_STATE_WORKING
    )


def _stream_response_task_ids(event: StreamResponse) -> tuple[str, ...]:
    if event.HasField("task"):
        return (event.task.id,)
    if event.HasField("status_update"):
        return (event.status_update.task_id,)
    if event.HasField("artifact_update"):
        return (event.artifact_update.task_id,)
    if event.HasField("message") and event.message.task_id:
        return (event.message.task_id,)
    return ()


def _result_from_task(
    task: Task,
    *,
    request_text: str,
    timeline: list[RemoteEvent],
) -> RemoteAnalysisResult:
    state_name = TaskState.Name(task.status.state)
    if state_name not in _A2A_STATES:
        raise RuntimeError(f"A2A task stopped in unsupported state {state_name}")
    a2a_state = _A2A_STATES[state_name]
    if len(task.artifacts) > 1:
        raise RuntimeError("A2A task stored more than one artifact")

    artifact_id: str | None = None
    artifact_object: Mapping[str, object] | None = None
    authoritative_part: Part | None = None
    if task.artifacts:
        artifact = task.artifacts[0]
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
        if artifact.name != "release-recommendation.json":
            raise RuntimeError("A2A recommendation artifact has an unexpected name")
        if artifact.artifact_id != validated.artifact_id:
            raise RuntimeError("A2A artifact ID does not match its data object")
        if validated.a2a_task_id != task.id or validated.a2a_context_id != task.context_id:
            raise RuntimeError("stored A2A artifact lineage does not match its task")
        artifact_id = artifact.artifact_id
        artifact_object = plain
        authoritative_part = part

    if a2a_state == "completed" and authoritative_part is None:
        raise RuntimeError("completed A2A task did not store a recommendation artifact")
    if a2a_state != "completed" and authoritative_part is not None:
        raise RuntimeError("non-completed A2A task stored a recommendation artifact")
    _append_raw_event(timeline, task)
    event_timeline = validate_event_timeline(
        event_timeline_to_plain_object(tuple(timeline)),
        task_id=task.id,
        context_id=task.context_id,
        terminal_state=a2a_state,
        artifact_id=artifact_id,
    )
    return RemoteAnalysisResult(
        a2a_state=a2a_state,
        task_id=task.id,
        context_id=task.context_id,
        artifact_id=artifact_id,
        artifact_object=artifact_object,
        authoritative_part=authoritative_part,
        request_info_count=0,
        used_streaming_workflow=False,
        event_timeline=event_timeline,
    )


def _require_same_task(
    initial_task_id: str,
    observed_task_ids: list[str],
    final_task_id: str,
) -> None:
    if not initial_task_id or final_task_id != initial_task_id:
        raise RuntimeError("A2A recovery changed the task ID")
    if not observed_task_ids or set(observed_task_ids) != {initial_task_id}:
        raise RuntimeError("A2A lifecycle events referred to more than one task")


def _validate_remote_inputs(agent_base_url: str, request_text: str) -> None:
    if not agent_base_url.startswith("http://"):
        raise ValueError("agent_base_url must be an HTTP URL")
    if type(request_text) is not str or not request_text:
        raise ValueError("request_text must be a non-empty string")


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
