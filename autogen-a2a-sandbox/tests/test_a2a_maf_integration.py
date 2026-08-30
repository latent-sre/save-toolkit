from __future__ import annotations

import asyncio
import copy
import json
import socket
import sys
import tempfile
import unittest
from importlib import metadata
from pathlib import Path
from unittest.mock import patch


SANDBOX_ROOT = Path(__file__).resolve().parents[1]
CASES_ROOT = SANDBOX_ROOT / "cases"
sys.path.insert(0, str(SANDBOX_ROOT))

from agent_framework import WorkflowBuilder  # noqa: E402
from a2a.types import Part  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from google.protobuf.descriptor import FieldDescriptor  # noqa: E402
from sse_starlette.sse import AppStatus  # noqa: E402
from uvicorn import Config, Server  # noqa: E402

from interop_sandbox.a2a_worker import create_worker_app  # noqa: E402
from interop_sandbox.contracts import (  # noqa: E402
    AnalysisRequest,
    canonical_json_bytes,
    canonical_sha256,
    to_plain_object,
    validate_analysis_request,
    validate_recommendation_artifact,
    verify_case_manifest,
)
from interop_sandbox.maf_orchestrator import (  # noqa: E402
    event_timeline_to_plain_object,
    run_remote_analysis,
    validate_event_timeline,
)


SOURCE_REVISION = "0123456789abcdef0123456789abcdef01234567"


def _requests_by_case() -> dict[str, AnalysisRequest]:
    requests: dict[str, AnalysisRequest] = {}
    for case in verify_case_manifest(CASES_ROOT):
        requests[case.case_id] = validate_analysis_request(
            {
                "request_version": "canary-analysis-request/v1",
                "run_id": case.case_id,
                "source_revision": SOURCE_REVISION,
                "case_id": case.case_id,
                "case_digest": canonical_sha256(case),
                "candidate_revision": case.candidate.candidate_revision,
                "case": to_plain_object(case),
            }
        )
    return requests


class A2AMAFIntegrationContractTests(unittest.TestCase):
    def test_pinned_fastapi_transport_dependencies_import_public_a2a_routes(self) -> None:
        requirements = (SANDBOX_ROOT / "requirements.txt").read_text(encoding="utf-8")

        for pin in (
            "fastapi==0.116.1",
            "httpx==0.28.1",
            "sse-starlette==2.4.1",
            "uvicorn==0.35.0",
        ):
            with self.subTest(pin=pin):
                self.assertIn(f"\n{pin}\n", f"\n{requirements}")

        from a2a.server.routes import (  # noqa: PLC0415
            add_a2a_routes_to_fastapi,
            create_agent_card_routes,
            create_jsonrpc_routes,
        )

        self.assertTrue(callable(add_a2a_routes_to_fastapi))
        self.assertTrue(callable(create_agent_card_routes))
        self.assertTrue(callable(create_jsonrpc_routes))

    def test_a2a_fastapi_openapi_enricher_is_skipped_for_protobuf5(self) -> None:
        from a2a.server.routes import add_a2a_routes_to_fastapi  # noqa: PLC0415

        self.assertTrue(metadata.version("protobuf").startswith("5.29."))
        self.assertFalse(hasattr(FieldDescriptor, "is_repeated"))
        with tempfile.TemporaryDirectory() as temporary:
            worker = create_worker_app(
                state_directory=temporary,
                agent_url="http://127.0.0.1:1/a2a/jsonrpc",
            )
        jsonrpc_routes = [
            route
            for route in worker.routes
            if getattr(route, "path", None) == "/a2a/jsonrpc"
        ]
        self.assertEqual(len(jsonrpc_routes), 1)

        with self.assertRaisesRegex(AttributeError, "is_repeated"):
            add_a2a_routes_to_fastapi(
                FastAPI(),
                jsonrpc_routes=jsonrpc_routes,
            )


class A2AMAFIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        # sse-starlette 2.4.1 keeps its Uvicorn exit event at process scope;
        # IsolatedAsyncioTestCase intentionally creates a new loop per test.
        AppStatus.should_exit = False
        AppStatus.should_exit_event = None
        self.requests = _requests_by_case()
        self.temporary = tempfile.TemporaryDirectory()
        self.state_directory = Path(self.temporary.name)
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(128)
        self.listener.setblocking(False)
        port = self.listener.getsockname()[1]
        self.base_url = f"http://127.0.0.1:{port}"
        self.app = create_worker_app(
            state_directory=self.state_directory,
            agent_url=f"{self.base_url}/a2a/jsonrpc",
        )
        config = Config(
            self.app,
            log_level="warning",
            access_log=False,
            lifespan="on",
        )
        self.server = Server(config)
        self.server_task = asyncio.create_task(
            self.server.serve(sockets=[self.listener])
        )
        await asyncio.wait_for(self._wait_until_started(), timeout=3)

    async def asyncTearDown(self) -> None:
        self.server.should_exit = True
        await asyncio.wait_for(self.server_task, timeout=3)
        self.listener.close()
        self.temporary.cleanup()

    async def _wait_until_started(self) -> None:
        while not self.server.started:
            if self.server_task.done():
                await self.server_task
            await asyncio.sleep(0)

    async def test_healthy_request_uses_real_maf_workflow_a2a_and_graphflow(self) -> None:
        build_calls: list[str] = []
        real_build = WorkflowBuilder.build

        def tracked_build(builder: WorkflowBuilder):
            build_calls.append(type(builder).__name__)
            return real_build(builder)

        request = self.requests["mission-healthy-001"]
        with patch.object(WorkflowBuilder, "build", tracked_build):
            result = await run_remote_analysis(
                agent_base_url=self.base_url,
                request_text=canonical_json_bytes(request).decode("utf-8"),
            )

        self.assertEqual(build_calls, ["WorkflowBuilder"])
        self.assertTrue(result.used_streaming_workflow)
        self.assertEqual(result.a2a_state, "completed")
        self.assertIsInstance(result.authoritative_part, Part)
        self.assertEqual(result.authoritative_part.WhichOneof("content"), "data")
        artifact = validate_recommendation_artifact(
            result.artifact_object, request=request
        )
        self.assertEqual(artifact.recommendation, "ADVANCE_CANARY")
        self.assertEqual(artifact.a2a_task_id, result.task_id)
        self.assertEqual(artifact.a2a_context_id, result.context_id)
        self.assertEqual(result.artifact_id, artifact.artifact_id)
        plain_timeline = event_timeline_to_plain_object(result.event_timeline)
        self.assertEqual(
            validate_event_timeline(
                plain_timeline,
                task_id=result.task_id,
                context_id=result.context_id,
                terminal_state="completed",
                artifact_id=result.artifact_id,
            ),
            result.event_timeline,
        )
        self.assertEqual(
            sum(event.event_kind == "data_artifact" for event in result.event_timeline),
            1,
        )
        terminal_path = self.state_directory / f"{request.run_id}.graphflow-state.json"
        terminal_state = json.loads(terminal_path.read_bytes())
        self.assertEqual(terminal_state["a2a_task_id"], result.task_id)
        self.assertEqual(terminal_state["a2a_context_id"], result.context_id)
        self.assertEqual(artifact.graph_state_sha256, canonical_sha256(terminal_state))
        self.assertEqual(self.app.state.analysis_executor.analysis_calls, 1)
        self.assertNotIn("openai", sys.modules)
        self.assertNotIn("autogen_ext", sys.modules)

    async def test_unresolved_contradiction_is_input_required_without_artifact(self) -> None:
        request = self.requests["unresolved-contradiction-001"]

        result = await run_remote_analysis(
            agent_base_url=self.base_url,
            request_text=canonical_json_bytes(request).decode("utf-8"),
        )

        self.assertEqual(result.a2a_state, "input-required")
        self.assertTrue(result.task_id)
        self.assertTrue(result.context_id)
        self.assertIsNone(result.authoritative_part)
        self.assertIsNone(result.artifact_object)
        self.assertIsNone(result.artifact_id)
        self.assertTrue(
            any(
                event.event_kind == "workflow_working"
                for event in result.event_timeline
            )
        )
        self.assertEqual(result.event_timeline[-1].a2a_state, "input-required")
        self.assertFalse(
            any(event.event_kind == "data_artifact" for event in result.event_timeline)
        )
        validate_event_timeline(
            event_timeline_to_plain_object(result.event_timeline),
            task_id=result.task_id,
            context_id=result.context_id,
            terminal_state="input-required",
            artifact_id=None,
        )
        self.assertEqual(result.request_info_count, 1)
        self.assertEqual(self.app.state.analysis_executor.analysis_calls, 1)

    async def test_timeline_revalidation_rejects_sequence_and_lineage_drift(self) -> None:
        request = self.requests["mission-healthy-001"]
        result = await run_remote_analysis(
            agent_base_url=self.base_url,
            request_text=canonical_json_bytes(request).decode("utf-8"),
        )
        plain = event_timeline_to_plain_object(result.event_timeline)

        sequence_drift = copy.deepcopy(plain)
        sequence_drift["events"][0]["sequence"] = 2
        lineage_drift = copy.deepcopy(plain)
        lineage_drift["events"][-1]["task_id"] = "different-task"

        with self.assertRaisesRegex(ValueError, "sequence"):
            validate_event_timeline(
                sequence_drift,
                task_id=result.task_id,
                context_id=result.context_id,
                terminal_state=result.a2a_state,
                artifact_id=result.artifact_id,
            )
        with self.assertRaisesRegex(ValueError, "lineage"):
            validate_event_timeline(
                lineage_drift,
                task_id=result.task_id,
                context_id=result.context_id,
                terminal_state=result.a2a_state,
                artifact_id=result.artifact_id,
            )

        fabricated = copy.deepcopy(plain)
        working = next(
            event
            for event in fabricated["events"]
            if event["event_kind"] == "workflow_working"
        )
        working["a2a_state"] = "working"
        with self.assertRaisesRegex(
            ValueError, "cannot claim A2A protocol evidence"
        ):
            validate_event_timeline(
                fabricated,
                task_id=result.task_id,
                context_id=result.context_id,
                terminal_state=result.a2a_state,
                artifact_id=result.artifact_id,
            )

    async def test_unknown_request_field_fails_before_graphflow(self) -> None:
        request_object = to_plain_object(self.requests["mission-healthy-001"])
        request_object["unexpected"] = "must-fail-closed"

        result = await run_remote_analysis(
            agent_base_url=self.base_url,
            request_text=json.dumps(
                request_object,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ),
        )

        self.assertEqual(result.a2a_state, "failed")
        self.assertIsNone(result.authoritative_part)
        self.assertIsNone(result.artifact_object)
        self.assertTrue(
            any(
                event.event_kind == "workflow_working"
                for event in result.event_timeline
            )
        )
        self.assertEqual(result.event_timeline[-1].a2a_state, "failed")
        self.assertEqual(self.app.state.analysis_executor.analysis_calls, 0)


if __name__ == "__main__":
    unittest.main()
