from __future__ import annotations

import asyncio
import copy
import socket
import sys
import tempfile
import threading
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from unittest.mock import patch


SANDBOX_ROOT = Path(__file__).resolve().parents[1]
CASES_ROOT = SANDBOX_ROOT / "cases"
sys.path.insert(0, str(SANDBOX_ROOT))

from a2a.types import Part  # noqa: E402
from agent_framework import FileCheckpointStorage, WorkflowBuilder  # noqa: E402
from google.protobuf.json_format import ParseDict  # noqa: E402
from google.protobuf.struct_pb2 import Value  # noqa: E402
from sse_starlette.sse import AppStatus  # noqa: E402
from uvicorn import Config, Server  # noqa: E402

from interop_sandbox.a2a_worker import create_worker_app  # noqa: E402
from interop_sandbox.approval_gate import (  # noqa: E402
    ApprovalGateError,
    open_approval_gate,
    resume_approval_gate,
)
from interop_sandbox import approval_gate  # noqa: E402
from interop_sandbox.contracts import (  # noqa: E402
    AnalysisRequest,
    canonical_json_bytes,
    canonical_sha256,
    to_plain_object,
    validate_analysis_request,
    validate_recommendation_artifact,
    validate_release_decision,
    verify_case_manifest,
)
from interop_sandbox.maf_orchestrator import (  # noqa: E402
    RemoteAnalysisResult,
    event_timeline_to_plain_object,
    validate_event_timeline,
)


SOURCE_REVISION = "0123456789abcdef0123456789abcdef01234567"
DECIDED_AT = "2026-08-30T20:00:00Z"
EXPIRES_AT = "2026-08-30T21:00:00Z"
CHECKED_AT = datetime(2026, 8, 30, 20, 30, tzinfo=timezone.utc)


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


def _completed_result(request: AnalysisRequest) -> RemoteAnalysisResult:
    artifact_object: dict[str, object] = {
        "artifact_version": "release-recommendation/v1",
        "artifact_id": f"release-recommendation:{request.run_id}",
        "run_id": request.run_id,
        "case_id": request.case_id,
        "case_digest": request.case_digest,
        "source_revision": request.source_revision,
        "candidate_revision": request.candidate_revision,
        "a2a_task_id": "task-approval-1",
        "a2a_context_id": "context-approval-1",
        "recommendation": "ADVANCE_CANARY",
        "basis": ["canary.healthy"],
        "resolved_contradictions": [],
        "unresolved_contradictions": [],
        "reconciliation_attempts": 0,
        "graph_state_sha256": "a" * 64,
        "packages": {
            name: metadata.version(name)
            for name in (
                "agent-framework-core",
                "agent-framework-a2a",
                "autogen-agentchat",
                "a2a-sdk",
            )
        },
    }
    artifact_object["artifact_digest"] = canonical_sha256(artifact_object)
    data = Value()
    ParseDict(artifact_object, data)
    part = Part(data=data, media_type="application/json")
    return RemoteAnalysisResult(
        a2a_state="completed",
        task_id="task-approval-1",
        context_id="context-approval-1",
        artifact_id=f"release-recommendation:{request.run_id}",
        artifact_object=artifact_object,
        authoritative_part=part,
        request_info_count=0,
        used_streaming_workflow=True,
    )


def _decision_response(
    result: RemoteAnalysisResult, *, decision: str = "ACCEPT"
) -> dict[str, object]:
    artifact = result.artifact_object
    if not isinstance(artifact, dict):
        raise AssertionError("test fixture requires an artifact object")
    return {
        "run_id": artifact["run_id"],
        "source_revision": artifact["source_revision"],
        "case_id": artifact["case_id"],
        "case_digest": artifact["case_digest"],
        "candidate_revision": artifact["candidate_revision"],
        "artifact_digest": artifact["artifact_digest"],
        "decision": decision,
        "approver": "human-release-owner",
        "decided_at": DECIDED_AT,
        "expires_at": EXPIRES_AT,
    }


def _valid_artifact_mutation(
    result: RemoteAnalysisResult, field: str, value: object
) -> dict[str, object]:
    artifact = copy.deepcopy(result.artifact_object)
    if not isinstance(artifact, dict):
        raise AssertionError("test fixture requires an artifact object")
    artifact[field] = value
    artifact["artifact_digest"] = canonical_sha256(
        artifact, omit_keys={"artifact_digest"}
    )
    return artifact


class ApprovalGateTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.checkpoints = self.root / "checkpoints"
        self.decisions = self.root / "decisions"
        self.checkpoints.mkdir()
        self.decisions.mkdir()
        self.request = _requests_by_case()["mission-healthy-001"]
        self.result = _completed_result(self.request)

    async def asyncTearDown(self) -> None:
        self.temporary.cleanup()

    async def test_accept_uses_one_real_request_and_fresh_checkpoint_restore(self) -> None:
        built_workflows: list[object] = []
        real_build = WorkflowBuilder.build

        def tracked_build(builder: WorkflowBuilder):
            workflow = real_build(builder)
            built_workflows.append(workflow)
            return workflow

        with patch.object(WorkflowBuilder, "build", tracked_build):
            pending = await open_approval_gate(
                self.result,
                checkpoint_directory=self.checkpoints,
            )
            self.assertEqual(list(self.decisions.iterdir()), [])
            outcome = await resume_approval_gate(
                artifact_object=self.result.artifact_object,
                checkpoint_directory=self.checkpoints,
                decision_directory=self.decisions,
                checkpoint_id=pending.checkpoint_id,
                response=_decision_response(self.result),
                at_time=CHECKED_AT,
            )

        self.assertEqual(pending.request_info_count, 1)
        storage = FileCheckpointStorage(self.checkpoints)
        checkpoint = await storage.load(pending.checkpoint_id)
        self.assertEqual(list(checkpoint.pending_request_info_events), [pending.request_id])
        self.assertIs(type(checkpoint.pending_request_info_events[pending.request_id].data), dict)
        self.assertEqual(
            checkpoint.pending_request_info_events[pending.request_id].data,
            pending.request_object,
        )
        self.assertEqual(len(built_workflows), 2)
        self.assertIsNot(built_workflows[0], built_workflows[1])
        self.assertIsNot(
            built_workflows[0].executors["final_release_approval"],
            built_workflows[1].executors["final_release_approval"],
        )
        self.assertEqual(outcome.request_info_count, 0)
        self.assertEqual(outcome.restored_checkpoint_id, pending.checkpoint_id)
        self.assertEqual(outcome.decision.decision, "ACCEPT")
        self.assertFalse(outcome.replayed)
        self.assertEqual(
            outcome.decision_path.read_bytes(), canonical_json_bytes(outcome.decision)
        )

    async def test_reject_writes_a_valid_closed_decision_without_release_effect(self) -> None:
        pending = await open_approval_gate(
            self.result, checkpoint_directory=self.checkpoints
        )

        outcome = await resume_approval_gate(
            artifact_object=self.result.artifact_object,
            checkpoint_directory=self.checkpoints,
            decision_directory=self.decisions,
            checkpoint_id=pending.checkpoint_id,
            response=_decision_response(self.result, decision="REJECT"),
            at_time=CHECKED_AT,
        )

        artifact = self.result.artifact_object
        self.assertIsInstance(artifact, dict)
        validate_release_decision(
            to_plain_object(outcome.decision),
            artifact=validate_recommendation_artifact(artifact),
            at_time=CHECKED_AT,
        )
        self.assertEqual(outcome.decision.decision, "REJECT")
        self.assertEqual(list(self.decisions.iterdir()), [outcome.decision_path])

    async def test_exact_replay_is_idempotent_and_changed_replay_fails_closed(self) -> None:
        pending = await open_approval_gate(
            self.result, checkpoint_directory=self.checkpoints
        )
        response = _decision_response(self.result)
        first = await resume_approval_gate(
            artifact_object=self.result.artifact_object,
            checkpoint_directory=self.checkpoints,
            decision_directory=self.decisions,
            checkpoint_id=pending.checkpoint_id,
            response=response,
            at_time=CHECKED_AT,
        )
        original_bytes = first.decision_path.read_bytes()
        original_mtime = first.decision_path.stat().st_mtime_ns

        replay = await resume_approval_gate(
            artifact_object=self.result.artifact_object,
            checkpoint_directory=self.checkpoints,
            decision_directory=self.decisions,
            checkpoint_id=pending.checkpoint_id,
            response=response,
            at_time=CHECKED_AT,
        )

        self.assertTrue(replay.replayed)
        self.assertEqual(replay.decision_path.read_bytes(), original_bytes)
        self.assertEqual(replay.decision_path.stat().st_mtime_ns, original_mtime)

        conflicting = {**response, "decision": "REJECT"}
        with self.assertRaisesRegex(ApprovalGateError, "different value"):
            await resume_approval_gate(
                artifact_object=self.result.artifact_object,
                checkpoint_directory=self.checkpoints,
                decision_directory=self.decisions,
                checkpoint_id=pending.checkpoint_id,
                response=conflicting,
                at_time=CHECKED_AT,
            )
        self.assertEqual(first.decision_path.read_bytes(), original_bytes)

    async def test_two_conflicting_decision_writers_cannot_last_writer_win(self) -> None:
        artifact_object = self.result.artifact_object
        self.assertIsInstance(artifact_object, dict)
        artifact = validate_recommendation_artifact(artifact_object)
        accept = validate_release_decision(
            {
                "decision_version": "release-decision-state/v1",
                **_decision_response(self.result, decision="ACCEPT"),
            },
            artifact=artifact,
            at_time=CHECKED_AT,
        )
        reject = validate_release_decision(
            {
                "decision_version": "release-decision-state/v1",
                **_decision_response(self.result, decision="REJECT"),
            },
            artifact=artifact,
            at_time=CHECKED_AT,
        )
        barrier = threading.Barrier(2)
        link_barrier = threading.Barrier(2)
        decision_path = self.decisions / f"{accept.run_id}.release-decision.json"
        real_exists = Path.exists
        real_link = approval_gate.os.link

        def synchronized_exists(path):
            if path == decision_path:
                barrier.wait(timeout=5)
                return False
            return real_exists(path)

        def synchronized_link(source, target):
            link_barrier.wait(timeout=5)
            return real_link(source, target)

        def write(decision):
            return approval_gate._persist_decision(
                self.decisions,
                decision,
                artifact=artifact,
                at_time=CHECKED_AT,
            )

        with (
            patch.object(Path, "exists", synchronized_exists),
            patch.object(approval_gate.os, "link", synchronized_link),
        ):
            results = await asyncio.gather(
                asyncio.to_thread(write, accept),
                asyncio.to_thread(write, reject),
                return_exceptions=True,
            )

        successes = [result for result in results if not isinstance(result, Exception)]
        failures = [result for result in results if isinstance(result, Exception)]
        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)
        self.assertIsInstance(failures[0], ApprovalGateError)
        written = successes[0][0]
        winner = accept if written.read_bytes() == canonical_json_bytes(accept) else reject
        self.assertEqual(written.read_bytes(), canonical_json_bytes(winner))

    async def test_non_completed_malformed_and_lineage_mismatch_never_open_gate(self) -> None:
        cases: dict[str, RemoteAnalysisResult] = {}
        for state in ("input-required", "canceled", "failed"):
            cases[state] = RemoteAnalysisResult(
                a2a_state=state,
                task_id="task-approval-1",
                context_id="context-approval-1",
                artifact_id=None,
                artifact_object=None,
                authoritative_part=None,
                request_info_count=0,
                used_streaming_workflow=True,
            )
        malformed_object = copy.deepcopy(self.result.artifact_object)
        self.assertIsInstance(malformed_object, dict)
        malformed_object["unexpected"] = "rejected"
        cases["malformed"] = replace(
            self.result, artifact_object=malformed_object
        )
        cases["lineage"] = replace(self.result, task_id="different-task")

        for label, result in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(ApprovalGateError):
                    await open_approval_gate(
                        result, checkpoint_directory=self.checkpoints
                    )
        self.assertEqual(list(self.checkpoints.iterdir()), [])
        self.assertEqual(list(self.decisions.iterdir()), [])

    async def test_artifact_lineage_revision_and_expiry_tamper_fail_closed(self) -> None:
        pending = await open_approval_gate(
            self.result, checkpoint_directory=self.checkpoints
        )
        valid_response = _decision_response(self.result)
        response_mutations = {
            "source_revision": {
                **valid_response,
                "source_revision": "f" * 40,
            },
            "candidate_revision": {
                **valid_response,
                "candidate_revision": "e" * 40,
            },
            "artifact_digest": {
                **valid_response,
                "artifact_digest": "d" * 64,
            },
            "expired": {
                **valid_response,
                "expires_at": "2026-08-30T20:15:00Z",
            },
        }
        for label, response in response_mutations.items():
            with self.subTest(label=label):
                with self.assertRaises(ApprovalGateError):
                    await resume_approval_gate(
                        artifact_object=self.result.artifact_object,
                        checkpoint_directory=self.checkpoints,
                        decision_directory=self.decisions,
                        checkpoint_id=pending.checkpoint_id,
                        response=response,
                        at_time=CHECKED_AT,
                    )

        stale_artifact = _valid_artifact_mutation(
            self.result, "source_revision", "f" * 40
        )
        with self.assertRaisesRegex(ApprovalGateError, "checkpoint"):
            await resume_approval_gate(
                artifact_object=stale_artifact,
                checkpoint_directory=self.checkpoints,
                decision_directory=self.decisions,
                checkpoint_id=pending.checkpoint_id,
                response=valid_response,
                at_time=CHECKED_AT,
            )
        self.assertEqual(list(self.decisions.iterdir()), [])


class A2ASameTaskLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
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
        self.server = Server(
            Config(
                self.app,
                log_level="warning",
                access_log=False,
                lifespan="on",
            )
        )
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

    async def test_stream_abandonment_subscribes_and_gets_the_same_completed_task(self) -> None:
        from interop_sandbox.maf_orchestrator import (  # noqa: PLC0415
            recover_remote_analysis_after_interruption,
        )

        request = self.requests["mission-healthy-001"]

        recovery = await recover_remote_analysis_after_interruption(
            agent_base_url=self.base_url,
            request_text=canonical_json_bytes(request).decode("utf-8"),
        )

        self.assertEqual(recovery.result.a2a_state, "completed")
        self.assertEqual(recovery.initial_task_id, recovery.result.task_id)
        self.assertEqual(set(recovery.observed_task_ids), {recovery.initial_task_id})
        self.assertEqual(recovery.event_timeline, recovery.result.event_timeline)
        validate_event_timeline(
            event_timeline_to_plain_object(recovery.event_timeline),
            task_id=recovery.result.task_id,
            context_id=recovery.result.context_id,
            terminal_state="completed",
            artifact_id=recovery.result.artifact_id,
        )
        self.assertEqual(
            sum(
                event.event_kind == "data_artifact"
                for event in recovery.event_timeline
            ),
            1,
        )
        self.assertGreater(recovery.subscription_event_count, 0)
        self.assertIsNotNone(recovery.result.authoritative_part)
        artifact = validate_recommendation_artifact(
            recovery.result.artifact_object, request=request
        )
        self.assertEqual(artifact.a2a_task_id, recovery.initial_task_id)
        self.assertEqual(self.app.state.analysis_executor.analysis_calls, 1)

    async def test_cancel_task_targets_same_slow_task_and_emits_no_artifact(self) -> None:
        from interop_sandbox.maf_orchestrator import (  # noqa: PLC0415
            cancel_remote_analysis_after_interruption,
        )

        request = self.requests["slow-analysis-cancel-001"]

        recovery = await cancel_remote_analysis_after_interruption(
            agent_base_url=self.base_url,
            request_text=canonical_json_bytes(request).decode("utf-8"),
        )

        self.assertEqual(recovery.cancel_sent_task_id, recovery.initial_task_id)
        self.assertEqual(recovery.result.task_id, recovery.initial_task_id)
        self.assertEqual(recovery.result.a2a_state, "canceled")
        self.assertEqual(recovery.event_timeline, recovery.result.event_timeline)
        self.assertTrue(
            any(event.a2a_state == "working" for event in recovery.event_timeline)
        )
        self.assertEqual(recovery.event_timeline[-1].a2a_state, "canceled")
        validate_event_timeline(
            event_timeline_to_plain_object(recovery.event_timeline),
            task_id=recovery.result.task_id,
            context_id=recovery.result.context_id,
            terminal_state="canceled",
            artifact_id=None,
        )
        self.assertIsNone(recovery.result.artifact_object)
        self.assertIsNone(recovery.result.authoritative_part)
        self.assertEqual(self.app.state.analysis_executor.analysis_calls, 1)
        self.assertNotIn("openai", sys.modules)
        self.assertNotIn("autogen_ext", sys.modules)


if __name__ == "__main__":
    unittest.main()
