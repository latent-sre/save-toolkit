"""A2A v1 FastAPI worker for the deterministic canary analysis graph."""

from __future__ import annotations

from contextlib import asynccontextmanager
from importlib import metadata
from pathlib import Path

from a2a.helpers.proto_helpers import new_task_from_user_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    create_agent_card_routes,
    create_jsonrpc_routes,
)
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    Part,
)
from autogen_core import CancellationToken
from fastapi import FastAPI
from google.protobuf.json_format import ParseDict
from google.protobuf.struct_pb2 import Value

from .contracts import (
    ARTIFACT_VERSION,
    PACKAGE_NAMES,
    ContractViolation,
    AnalysisRequest,
    canonical_sha256,
    expected_artifact_id,
    parse_analysis_request_json,
    to_plain_object,
    validate_recommendation_artifact,
)
from .graphflow_runtime import AnalysisResult, bind_transport_lineage, run_analysis


WORKER_VERSION = "autogen-a2a-worker/v1"
ARTIFACT_NAME = "release-recommendation.json"


class CanaryAnalysisExecutor(AgentExecutor):
    """Validate one A2A text request and publish its GraphFlow outcome."""

    def __init__(self, state_directory: Path) -> None:
        self._state_directory = state_directory
        self._tokens: dict[str, CancellationToken] = {}
        self.analysis_calls = 0

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        message = context.message
        if message is None:
            return
        task = context.current_task
        if task is None:
            task = new_task_from_user_message(message)
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)
        await updater.start_work(
            updater.new_agent_message([Part(text="canary analysis started")])
        )

        token = CancellationToken()
        self._tokens[task.id] = token
        try:
            try:
                request = parse_analysis_request_json(context.get_user_input())
            except ContractViolation:
                await updater.failed(
                    updater.new_agent_message([Part(text="analysis request rejected")])
                )
                return

            self.analysis_calls += 1
            try:
                result = await run_analysis(
                    request,
                    state_directory=self._state_directory,
                    cancellation_token=token,
                )
                await self._publish_result(updater, request, result)
            except Exception:  # noqa: BLE001 - translate the request boundary without leaking internals
                await updater.failed(
                    updater.new_agent_message([Part(text="analysis execution failed")])
                )
        finally:
            self._tokens.pop(task.id, None)

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        task_id = context.task_id
        context_id = context.context_id
        if not task_id or not context_id:
            return
        if token := self._tokens.get(task_id):
            token.cancel()
        updater = TaskUpdater(event_queue, task_id, context_id)
        await updater.cancel(
            updater.new_agent_message([Part(text="analysis cancellation acknowledged")])
        )

    async def _publish_result(
        self,
        updater: TaskUpdater,
        request: AnalysisRequest,
        result: AnalysisResult,
    ) -> None:
        if result.status in ("COMPLETED", "INPUT_REQUIRED"):
            result = bind_transport_lineage(
                result,
                task_id=updater.task_id,
                context_id=updater.context_id,
            )
        if result.status == "INPUT_REQUIRED":
            await updater.requires_input(
                updater.new_agent_message(
                    [Part(text="canary evidence remains contradictory after reconciliation")]
                )
            )
            return
        if result.status == "CANCELED":
            return
        if result.status != "COMPLETED":
            await updater.failed(
                updater.new_agent_message([Part(text="analysis returned an invalid state")])
            )
            return

        artifact = _build_recommendation_artifact(
            request=request,
            result=result,
            task_id=updater.task_id,
            context_id=updater.context_id,
        )
        data = Value()
        ParseDict(to_plain_object(artifact), data)
        await updater.add_artifact(
            parts=[Part(data=data, media_type="application/json")],
            artifact_id=artifact.artifact_id,
            name=ARTIFACT_NAME,
            last_chunk=True,
        )
        await updater.complete(
            updater.new_agent_message([Part(text="canary recommendation published")])
        )


def _build_recommendation_artifact(
    *,
    request: AnalysisRequest,
    result: AnalysisResult,
    task_id: str,
    context_id: str,
):
    if result.recommendation is None or result.graph_state_sha256 is None:
        raise ValueError("completed analysis lacks a recommendation or state digest")
    if result.a2a_task_id != task_id or result.a2a_context_id != context_id:
        raise ValueError("completed analysis state is not bound to this A2A task")
    payload = {
        "artifact_version": ARTIFACT_VERSION,
        "artifact_id": expected_artifact_id(request.run_id),
        "run_id": request.run_id,
        "case_id": request.case_id,
        "case_digest": request.case_digest,
        "source_revision": request.source_revision,
        "candidate_revision": request.candidate_revision,
        "a2a_task_id": task_id,
        "a2a_context_id": context_id,
        "recommendation": result.recommendation,
        "basis": list(result.basis),
        "resolved_contradictions": list(result.resolved_contradictions),
        "unresolved_contradictions": list(result.unresolved_contradictions),
        "reconciliation_attempts": result.reconciliation_attempts,
        "graph_state_sha256": result.graph_state_sha256,
        "packages": {name: metadata.version(name) for name in PACKAGE_NAMES},
    }
    payload["artifact_digest"] = canonical_sha256(payload)
    return validate_recommendation_artifact(payload, request=request)


def create_worker_app(*, state_directory: str | Path, agent_url: str) -> FastAPI:
    """Build the worker app without opening a socket or starting background work."""

    state_root = Path(state_directory)
    if not state_root.is_dir():
        raise ValueError("state_directory must be an existing directory")
    if not agent_url.startswith("http://") or not agent_url.endswith("/a2a/jsonrpc"):
        raise ValueError("agent_url must be an HTTP A2A JSON-RPC URL")

    card = AgentCard(
        name="canary-analysis-worker",
        description="Deterministic AutoGen GraphFlow canary evidence analysis",
        version=WORKER_VERSION,
        capabilities=AgentCapabilities(streaming=True),
        default_input_modes=["text/plain"],
        default_output_modes=["application/json"],
        supported_interfaces=[
            AgentInterface(
                url=agent_url,
                protocol_binding="JSONRPC",
                protocol_version="1.0",
            )
        ],
        skills=[
            AgentSkill(
                id="canary-evidence-analysis",
                name="Canary evidence analysis",
                description="Analyze one closed canary evidence case",
                tags=["canary", "deterministic", "offline"],
                input_modes=["text/plain"],
                output_modes=["application/json"],
            )
        ],
    )
    executor = CanaryAnalysisExecutor(state_root)
    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        await handler.aclose()

    app = FastAPI(
        title="AutoGen A2A canary worker",
        version=WORKER_VERSION,
        lifespan=lifespan,
    )
    # a2a-sdk 1.1.2's optional FastAPI OpenAPI enhancer assumes protobuf 6's
    # FieldDescriptor.is_repeated, while AutoGen 0.7.5 pins protobuf 5.29.x.
    # The public route factories themselves are Starlette/FastAPI compatible.
    app.router.routes.extend(create_agent_card_routes(card))
    app.router.routes.extend(
        create_jsonrpc_routes(
            handler,
            rpc_url="/a2a/jsonrpc",
            enable_v0_3_compat=False,
        )
    )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "up"}

    @app.get("/readyz")
    async def readyz() -> dict[str, str]:
        return {"status": "ready"}

    app.state.analysis_executor = executor
    return app
