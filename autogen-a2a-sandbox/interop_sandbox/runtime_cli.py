"""Container-only process wiring for the two-service sandbox."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import re
import sys
import tempfile
import time
import urllib.request
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path


PENDING_VERSION = "autogen-a2a-pending-state/v1"
HANDOFF_VERSION = "autogen-a2a-resume-handoff/v1"
RUNTIME_EVIDENCE_VERSION = "autogen-a2a-runtime-evidence/v1"
EXIT_PENDING = 20
EXIT_TERMINAL = 2
_REVISION = re.compile(r"^[0-9a-f]{40}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_PENDING_FIELDS = frozenset(
    {
        "pending_version",
        "state",
        "run_id",
        "source_revision",
        "case_id",
        "case_digest",
        "candidate_revision",
        "analysis_invocations",
        "artifact",
        "a2a",
        "approval",
    }
)
_A2A_FIELDS = frozenset(
    {
        "state",
        "task_id",
        "context_id",
        "artifact_id",
        "authoritative_content",
        "used_streaming_workflow",
    }
)
_APPROVAL_FIELDS = frozenset(
    {
        "checkpoint_id",
        "request_id",
        "request_info_count",
        "workflow_name",
    }
)
_RUNTIME_FINAL_FIELDS = frozenset(
    {
        "runtime_evidence_version",
        "status",
        "run_id",
        "source_revision",
        "case_id",
        "case_digest",
        "candidate_revision",
        "python",
        "packages",
        "analysis_invocations",
        "a2a",
        "graphflow",
        "approval",
        "artifact",
        "decision",
        "release_effect_executed",
    }
)
_FINAL_GRAPHFLOW_FIELDS = frozenset(
    {
        "state_sha256",
        "state_loaded_for_analysis",
        "analysis_rerun_on_approval_resume",
    }
)
_FINAL_APPROVAL_FIELDS = frozenset(
    {
        "checkpoint_id",
        "restored_checkpoint_id",
        "initial_request_info_count",
        "resume_request_info_count",
        "decision_replayed",
    }
)
_FORBIDDEN_ENV_EXACT = frozenset(
    {
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "CF_HOME",
        "SSH_AUTH_SOCK",
        "MODEL_NAME",
    }
)
_FORBIDDEN_ENV_PREFIXES = (
    "OPENAI_",
    "ANTHROPIC_",
    "AZURE_",
    "AWS_",
    "GCP_",
    "GOOGLE_CLOUD_",
    "GITHUB_",
    "CF_",
    "PCF_",
    "SSH_",
    "MODEL_",
    "DOCKER_",
    "COMPOSE_",
)


class RuntimeBoundaryError(RuntimeError):
    """Runtime state or evidence violated the closed sandbox boundary."""


class RuntimeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise RuntimeBoundaryError(f"invalid runtime arguments: {message}")


def validate_runtime_pending(
    value: object,
    *,
    run_id: str,
    source_revision: str,
    case_id: str,
) -> Mapping[str, object]:
    """Validate enough persisted state before importing framework code on resume."""

    if type(value) is not dict or set(value) != _PENDING_FIELDS:
        raise RuntimeBoundaryError("pending state is not a closed object")
    expected = {
        "pending_version": PENDING_VERSION,
        "state": "AWAITING_APPROVAL",
        "run_id": run_id,
        "source_revision": source_revision,
        "case_id": case_id,
        "analysis_invocations": 1,
    }
    for field, expected_value in expected.items():
        if value.get(field) != expected_value:
            raise RuntimeBoundaryError(f"pending state {field} mismatch")
    for field, pattern in (
        ("case_digest", _DIGEST),
        ("candidate_revision", _REVISION),
    ):
        item = value.get(field)
        if type(item) is not str or pattern.fullmatch(item) is None:
            raise RuntimeBoundaryError(f"pending state {field} is malformed")
    artifact = value.get("artifact")
    if type(artifact) is not dict:
        raise RuntimeBoundaryError("pending artifact is not an object")
    bindings = {
        "run_id": run_id,
        "source_revision": source_revision,
        "case_id": case_id,
        "case_digest": value["case_digest"],
        "candidate_revision": value["candidate_revision"],
    }
    for field, expected_value in bindings.items():
        if artifact.get(field) != expected_value:
            raise RuntimeBoundaryError(f"pending artifact {field} mismatch")
    artifact_digest = artifact.get("artifact_digest")
    if type(artifact_digest) is not str or _DIGEST.fullmatch(artifact_digest) is None:
        raise RuntimeBoundaryError("pending artifact digest is malformed")
    a2a = value.get("a2a")
    if type(a2a) is not dict or set(a2a) != _A2A_FIELDS:
        raise RuntimeBoundaryError("pending A2A proof is not closed")
    if (
        a2a.get("state") != "completed"
        or a2a.get("authoritative_content") != "data"
        or a2a.get("used_streaming_workflow") is not True
    ):
        raise RuntimeBoundaryError("pending A2A proof is not approval-eligible")
    for field in ("task_id", "context_id", "artifact_id"):
        if type(a2a.get(field)) is not str or not a2a[field]:
            raise RuntimeBoundaryError(f"pending A2A {field} is malformed")
    if artifact.get("a2a_task_id") not in (None, a2a["task_id"]):
        raise RuntimeBoundaryError("pending A2A task lineage mismatch")
    if artifact.get("a2a_context_id") not in (None, a2a["context_id"]):
        raise RuntimeBoundaryError("pending A2A context lineage mismatch")
    if artifact.get("artifact_id") not in (None, a2a["artifact_id"]):
        raise RuntimeBoundaryError("pending A2A artifact lineage mismatch")
    approval = value.get("approval")
    if type(approval) is not dict or set(approval) != _APPROVAL_FIELDS:
        raise RuntimeBoundaryError("pending approval proof is not closed")
    if approval.get("request_info_count") != 1:
        raise RuntimeBoundaryError("pending approval must contain exactly one request_info")
    for field in ("checkpoint_id", "request_id", "workflow_name"):
        if type(approval.get(field)) is not str or not approval[field]:
            raise RuntimeBoundaryError(f"pending approval {field} is malformed")
    return value


def recover_existing_final(
    *,
    runtime_final_path: Path,
    decision_path: Path,
    pending: Mapping[str, object],
    requested_decision: str,
) -> bytes | None:
    """Return one exact completed resume result without reopening its MAF gate."""

    from .contracts import (
        ContractViolation,
        canonical_json_bytes,
        to_plain_object,
        validate_recommendation_artifact,
        validate_release_decision,
    )

    final_exists = runtime_final_path.is_file()
    decision_exists = decision_path.is_file()
    if not final_exists and not decision_exists:
        return None
    if final_exists != decision_exists:
        raise RuntimeBoundaryError(
            "completed resume evidence is partial; refusing to reopen approval"
        )
    if requested_decision not in ("ACCEPT", "REJECT"):
        raise RuntimeBoundaryError("requested decision is not closed")
    try:
        runtime_bytes = runtime_final_path.read_bytes()
        decision_bytes = decision_path.read_bytes()
        runtime_object = json.loads(runtime_bytes)
        decision_object = json.loads(decision_bytes)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeBoundaryError("completed resume evidence cannot be decoded") from exc
    if type(runtime_object) is not dict or set(runtime_object) != _RUNTIME_FINAL_FIELDS:
        raise RuntimeBoundaryError("existing runtime-final is not a closed object")
    if runtime_bytes != _canonical_json(runtime_object):
        raise RuntimeBoundaryError("existing runtime-final is not canonical JSON")
    if type(decision_object) is not dict:
        raise RuntimeBoundaryError("existing decision is not an object")

    try:
        artifact = validate_recommendation_artifact(pending.get("artifact"))
        decided_at_value = decision_object.get("decided_at")
        if type(decided_at_value) is not str or not decided_at_value.endswith("Z"):
            raise RuntimeBoundaryError("existing decision decided_at is malformed")
        decided_at = datetime.fromisoformat(decided_at_value[:-1] + "+00:00")
        decision = validate_release_decision(
            decision_object,
            artifact=artifact,
            # Validate that the persisted decision was valid when recorded. A
            # host-export retry may legitimately occur after expires_at.
            at_time=decided_at,
        )
    except (ContractViolation, TypeError, ValueError) as exc:
        raise RuntimeBoundaryError("existing decision or artifact is invalid") from exc
    if decision_bytes != canonical_json_bytes(decision):
        raise RuntimeBoundaryError("existing decision bytes are not canonical")
    if decision.decision != requested_decision:
        raise RuntimeBoundaryError(
            "existing decision does not match the requested decision"
        )

    expected = {
        "runtime_evidence_version": RUNTIME_EVIDENCE_VERSION,
        "status": "DECISION_RECORDED",
        "run_id": pending.get("run_id"),
        "source_revision": pending.get("source_revision"),
        "case_id": pending.get("case_id"),
        "case_digest": pending.get("case_digest"),
        "candidate_revision": pending.get("candidate_revision"),
        "python": platform.python_version(),
        "packages": to_plain_object(artifact.packages),
        "analysis_invocations": 1,
        "a2a": pending.get("a2a"),
        "artifact": to_plain_object(artifact),
        "decision": to_plain_object(decision),
        "release_effect_executed": False,
    }
    for field, expected_value in expected.items():
        actual = runtime_object.get(field)
        if field == "analysis_invocations":
            if type(actual) is not int or actual != expected_value:
                raise RuntimeBoundaryError(
                    "existing runtime-final analysis count mismatch"
                )
        elif field == "release_effect_executed":
            if actual is not False:
                raise RuntimeBoundaryError(
                    "existing runtime-final reports a release effect"
                )
        elif actual != expected_value:
            raise RuntimeBoundaryError(
                f"existing runtime-final {field} mismatch"
            )

    graphflow = runtime_object.get("graphflow")
    if type(graphflow) is not dict or set(graphflow) != _FINAL_GRAPHFLOW_FIELDS:
        raise RuntimeBoundaryError("existing GraphFlow proof is not closed")
    if (
        graphflow.get("state_sha256") != artifact.graph_state_sha256
        or graphflow.get("state_loaded_for_analysis") is not True
        or graphflow.get("analysis_rerun_on_approval_resume") is not False
    ):
        raise RuntimeBoundaryError("existing GraphFlow proof is invalid")

    approval = runtime_object.get("approval")
    pending_approval = pending.get("approval")
    if (
        type(approval) is not dict
        or set(approval) != _FINAL_APPROVAL_FIELDS
        or type(pending_approval) is not dict
    ):
        raise RuntimeBoundaryError("existing approval proof is not closed")
    checkpoint_id = pending_approval.get("checkpoint_id")
    if (
        approval.get("checkpoint_id") != checkpoint_id
        or approval.get("restored_checkpoint_id") != checkpoint_id
        or approval.get("initial_request_info_count") != 1
        or approval.get("resume_request_info_count") != 0
        or type(approval.get("decision_replayed")) is not bool
    ):
        raise RuntimeBoundaryError("existing approval proof is invalid")
    return runtime_bytes


def reject_runtime_environment(environment: Mapping[str, str]) -> None:
    rejected = []
    for raw_name in environment:
        name = raw_name.upper()
        if (
            name in _FORBIDDEN_ENV_EXACT
            or name.endswith("_PROXY")
            or any(name.startswith(prefix) for prefix in _FORBIDDEN_ENV_PREFIXES)
        ):
            rejected.append(raw_name)
    if rejected:
        raise RuntimeBoundaryError(
            "rejected ambient environment variable(s): "
            + ", ".join(sorted(rejected, key=str.upper))
        )


def validate_noncompleted_terminal(
    *,
    a2a_state: str,
    artifact_object: object,
    remote_request_info_count: int,
) -> Mapping[str, int]:
    """Keep an A2A input request distinct from the final approval gate."""

    expected_remote_requests = {"input-required": 1, "canceled": 0, "failed": 0}
    if a2a_state not in expected_remote_requests:
        raise RuntimeBoundaryError("non-completed A2A state is unsupported")
    if artifact_object is not None:
        raise RuntimeBoundaryError("non-completed A2A task emitted an artifact")
    if remote_request_info_count != expected_remote_requests[a2a_state]:
        raise RuntimeBoundaryError("non-completed A2A request_info count is unexpected")
    return {
        "remote_request_info_count": remote_request_info_count,
        "approval_request_info_count": 0,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = RuntimeArgumentParser(description="Container runtime for the A2A sandbox")
    commands = parser.add_subparsers(dest="command", required=True)
    worker = commands.add_parser("worker")
    worker.add_argument("--state-directory", required=True)
    worker.add_argument("--agent-url", required=True)
    worker.add_argument("--host", required=True)
    worker.add_argument("--port", type=int, required=True)
    health = commands.add_parser("healthcheck")
    health.add_argument("--url", required=True)
    orchestrate = commands.add_parser("orchestrate")
    orchestrate.add_argument("--mode", choices=("fresh", "resume"), required=True)
    orchestrate.add_argument("--source-revision", required=True)
    orchestrate.add_argument("--run-id", required=True)
    orchestrate.add_argument("--case", required=True)
    orchestrate.add_argument("--decision", choices=("NONE", "ACCEPT", "REJECT"), required=True)
    orchestrate.add_argument("--worker-url", required=True)
    orchestrate.add_argument("--state-directory", required=True)
    orchestrate.add_argument("--evidence-directory", required=True)
    orchestrate.add_argument("--cases-directory", required=True)
    return parser


async def _run_fresh(args: argparse.Namespace) -> int:
    from .approval_gate import open_approval_gate
    from .contracts import (
        REQUEST_VERSION,
        canonical_json_bytes,
        canonical_sha256,
        to_plain_object,
        validate_analysis_request,
        verify_case_manifest,
    )
    from .maf_orchestrator import (
        cancel_remote_analysis_after_interruption,
        run_remote_analysis,
    )

    if args.decision != "NONE":
        raise RuntimeBoundaryError("fresh mode cannot carry an approval decision")
    state_root = _existing_directory(args.state_directory, "state directory")
    evidence_root = _existing_directory(args.evidence_directory, "evidence directory")
    cases_root = _existing_directory(args.cases_directory, "cases directory")
    checkpoints = state_root / "checkpoints"
    decisions = state_root / "decisions"
    checkpoints.mkdir(exist_ok=True)
    decisions.mkdir(exist_ok=True)
    cases = {case.case_id: case for case in verify_case_manifest(cases_root)}
    case = cases.get(args.case)
    if case is None:
        raise RuntimeBoundaryError("case is not in the immutable manifest")
    request = validate_analysis_request(
        {
            "request_version": REQUEST_VERSION,
            "run_id": args.run_id,
            "source_revision": args.source_revision,
            "case_id": case.case_id,
            "case_digest": canonical_sha256(case),
            "candidate_revision": case.candidate.candidate_revision,
            "case": to_plain_object(case),
        }
    )
    await _wait_ready(args.worker_url + "/readyz", timeout_seconds=20.0)
    request_text = canonical_json_bytes(request).decode("utf-8")
    if case.fault.slow_analyzer is not None:
        recovery = await cancel_remote_analysis_after_interruption(
            agent_base_url=args.worker_url,
            request_text=request_text,
        )
        result = recovery.result
        same_task = len(set(recovery.observed_task_ids)) == 1
        recovery_proof: Mapping[str, object] = {
            "cancel_sent_task_id": recovery.cancel_sent_task_id,
            "initial_task_id": recovery.initial_task_id,
            "observed_task_ids": list(recovery.observed_task_ids),
            "same_task": same_task,
        }
        if not same_task:
            raise RuntimeBoundaryError("cancellation crossed A2A task lineage")
    else:
        result = await run_remote_analysis(
            agent_base_url=args.worker_url,
            request_text=request_text,
        )
        recovery_proof = {"same_task": True}
    if result.a2a_state != case.expected.a2a_state:
        raise RuntimeBoundaryError(
            f"A2A state {result.a2a_state!r} does not match immutable expectation"
        )
    if result.a2a_state != "completed":
        request_proof = validate_noncompleted_terminal(
            a2a_state=result.a2a_state,
            artifact_object=result.artifact_object,
            remote_request_info_count=result.request_info_count,
        )
        terminal = {
            "runtime_evidence_version": RUNTIME_EVIDENCE_VERSION,
            "status": result.a2a_state,
            "run_id": args.run_id,
            "source_revision": args.source_revision,
            "case_id": args.case,
            "analysis_invocations": 1,
            **request_proof,
            "artifact": None,
            "a2a": {
                "task_id": result.task_id,
                "context_id": result.context_id,
                "used_streaming_workflow": result.used_streaming_workflow,
                "recovery": recovery_proof,
            },
            "release_effect_executed": False,
        }
        _publish_once(evidence_root / "runtime-terminal.json", _canonical_json(terminal))
        _print_event("terminal_without_approval", args.run_id)
        return EXIT_TERMINAL

    artifact = result.artifact_object
    if not isinstance(artifact, Mapping):
        raise RuntimeBoundaryError("completed task lacks an artifact object")
    if artifact.get("recommendation") != case.expected.recommendation:
        raise RuntimeBoundaryError("recommendation does not match immutable expectation")
    pending = await open_approval_gate(result, checkpoint_directory=checkpoints)
    pending_state = {
        "pending_version": PENDING_VERSION,
        "state": "AWAITING_APPROVAL",
        "run_id": args.run_id,
        "source_revision": args.source_revision,
        "case_id": args.case,
        "case_digest": request.case_digest,
        "candidate_revision": request.candidate_revision,
        "analysis_invocations": 1,
        "artifact": dict(artifact),
        "a2a": {
            "state": result.a2a_state,
            "task_id": result.task_id,
            "context_id": result.context_id,
            "artifact_id": result.artifact_id,
            "authoritative_content": "data",
            "used_streaming_workflow": result.used_streaming_workflow,
        },
        "approval": {
            "checkpoint_id": pending.checkpoint_id,
            "request_id": pending.request_id,
            "request_info_count": pending.request_info_count,
            "workflow_name": pending.workflow_name,
        },
    }
    validate_runtime_pending(
        pending_state,
        run_id=args.run_id,
        source_revision=args.source_revision,
        case_id=args.case,
    )
    _publish_once(state_root / "pending-state.json", _canonical_json(pending_state))
    handoff = {
        "handoff_version": HANDOFF_VERSION,
        "state": "AWAITING_APPROVAL",
        "run_id": args.run_id,
        "source_revision": args.source_revision,
        "case_id": args.case,
        "case_digest": request.case_digest,
        "candidate_revision": request.candidate_revision,
        "artifact_digest": artifact["artifact_digest"],
        "checkpoint_id": pending.checkpoint_id,
    }
    _publish_once(evidence_root / "pending-handoff.json", _canonical_json(handoff))
    _print_event("AWAITING_APPROVAL", args.run_id)
    return EXIT_PENDING


async def _run_resume(args: argparse.Namespace) -> int:
    from .approval_gate import resume_approval_gate
    from .contracts import (
        canonical_sha256,
        to_plain_object,
        validate_recommendation_artifact,
        verify_case_manifest,
    )

    if args.decision not in ("ACCEPT", "REJECT"):
        raise RuntimeBoundaryError("resume requires ACCEPT or REJECT")
    state_root = _existing_directory(args.state_directory, "state directory")
    evidence_root = _existing_directory(args.evidence_directory, "evidence directory")
    cases_root = _existing_directory(args.cases_directory, "cases directory")
    pending_object = _load_json(state_root / "pending-state.json", "pending state")
    pending = validate_runtime_pending(
        pending_object,
        run_id=args.run_id,
        source_revision=args.source_revision,
        case_id=args.case,
    )
    cases = {case.case_id: case for case in verify_case_manifest(cases_root)}
    case = cases.get(args.case)
    if case is None:
        raise RuntimeBoundaryError("case is not in the immutable manifest")
    if canonical_sha256(case) != pending["case_digest"]:
        raise RuntimeBoundaryError("pending state does not bind the immutable case")
    artifact = validate_recommendation_artifact(pending["artifact"])
    state_path = state_root / f"{args.run_id}.graphflow-state.json"
    graph_state = _load_json(state_path, "GraphFlow state")
    if canonical_sha256(graph_state) != artifact.graph_state_sha256:
        raise RuntimeBoundaryError("GraphFlow state digest does not match the artifact")
    existing_final = recover_existing_final(
        runtime_final_path=evidence_root / "runtime-final.json",
        decision_path=(
            state_root / "decisions" / f"{args.run_id}.release-decision.json"
        ),
        pending=pending,
        requested_decision=args.decision,
    )
    if existing_final is not None:
        _print_event("decision_recorded_replay", args.run_id)
        return 0
    now = datetime.now(timezone.utc).replace(microsecond=0)
    response = {
        "run_id": artifact.run_id,
        "source_revision": artifact.source_revision,
        "case_id": artifact.case_id,
        "case_digest": artifact.case_digest,
        "candidate_revision": artifact.candidate_revision,
        "artifact_digest": artifact.artifact_digest,
        "decision": args.decision,
        "approver": "human-release-owner",
        "decided_at": _rfc3339(now),
        "expires_at": _rfc3339(now + timedelta(minutes=15)),
    }
    approval = pending["approval"]
    outcome = await resume_approval_gate(
        artifact_object=pending["artifact"],
        checkpoint_directory=state_root / "checkpoints",
        decision_directory=state_root / "decisions",
        checkpoint_id=approval["checkpoint_id"],
        response=response,
        at_time=now,
    )
    runtime_final = {
        "runtime_evidence_version": RUNTIME_EVIDENCE_VERSION,
        "status": "DECISION_RECORDED",
        "run_id": args.run_id,
        "source_revision": args.source_revision,
        "case_id": args.case,
        "case_digest": pending["case_digest"],
        "candidate_revision": pending["candidate_revision"],
        "python": platform.python_version(),
        "packages": to_plain_object(artifact.packages),
        "analysis_invocations": pending["analysis_invocations"],
        "a2a": pending["a2a"],
        "graphflow": {
            "state_sha256": artifact.graph_state_sha256,
            "state_loaded_for_analysis": True,
            "analysis_rerun_on_approval_resume": False,
        },
        "approval": {
            "checkpoint_id": approval["checkpoint_id"],
            "restored_checkpoint_id": outcome.restored_checkpoint_id,
            "initial_request_info_count": approval["request_info_count"],
            "resume_request_info_count": outcome.request_info_count,
            "decision_replayed": outcome.replayed,
        },
        "artifact": to_plain_object(artifact),
        "decision": to_plain_object(outcome.decision),
        "release_effect_executed": False,
    }
    _publish_once(evidence_root / "runtime-final.json", _canonical_json(runtime_final))
    _print_event("decision_recorded", args.run_id)
    return 0


async def _orchestrate(args: argparse.Namespace) -> int:
    if _REVISION.fullmatch(args.source_revision) is None:
        raise RuntimeBoundaryError("source revision is malformed")
    if args.worker_url != "http://worker:8081":
        raise RuntimeBoundaryError("worker URL is not the internal service endpoint")
    return await (_run_fresh(args) if args.mode == "fresh" else _run_resume(args))


def _run_worker(args: argparse.Namespace) -> int:
    import uvicorn

    from .a2a_worker import create_worker_app

    if args.host != "0.0.0.0" or args.port != 8081:
        raise RuntimeBoundaryError("worker listen address drifted")
    state_root = _existing_directory(args.state_directory, "state directory")
    app = create_worker_app(state_directory=state_root, agent_url=args.agent_url)
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        access_log=False,
        log_level="warning",
        timeout_graceful_shutdown=5,
    )
    return 0


def _run_healthcheck(url: str) -> int:
    if url != "http://127.0.0.1:8081/readyz":
        raise RuntimeBoundaryError("healthcheck URL drifted")
    with urllib.request.urlopen(url, timeout=1.5) as response:  # noqa: S310 - fixed loopback URL
        if response.status != 200 or json.loads(response.read()) != {"status": "ready"}:
            raise RuntimeBoundaryError("worker is not ready")
    return 0


async def _wait_ready(url: str, *, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            await asyncio.to_thread(_probe_ready, url)
            return
        except (OSError, ValueError, RuntimeBoundaryError):
            if time.monotonic() >= deadline:
                raise RuntimeBoundaryError("worker readiness deadline expired")
            await asyncio.sleep(0.2)


def _probe_ready(url: str) -> None:
    if url != "http://worker:8081/readyz":
        raise RuntimeBoundaryError("readiness URL drifted")
    with urllib.request.urlopen(url, timeout=1.0) as response:  # noqa: S310 - fixed internal URL
        if response.status != 200 or json.loads(response.read()) != {"status": "ready"}:
            raise RuntimeBoundaryError("worker is not ready")


def _existing_directory(value: str | Path, label: str) -> Path:
    root = Path(value)
    if not root.is_dir():
        raise RuntimeBoundaryError(f"{label} must be an existing directory")
    return root


def _load_json(path: Path, label: str) -> Mapping[str, object]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeBoundaryError(f"{label} cannot be decoded") from exc
    if type(value) is not dict:
        raise RuntimeBoundaryError(f"{label} must be an object")
    return value


def _publish_once(path: Path, data: bytes) -> None:
    if path.exists():
        if path.read_bytes() == data:
            return
        raise RuntimeBoundaryError(f"refusing to overwrite changed runtime evidence: {path.name}")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            raise RuntimeBoundaryError(f"refusing to overwrite changed runtime evidence: {path.name}")
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _rfc3339(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _print_event(event: str, run_id: str) -> None:
    print(
        json.dumps(
            {"event": event, "run_id": run_id},
            separators=(",", ":"),
            sort_keys=True,
        )
    )


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        reject_runtime_environment(os.environ)
        if args.command == "worker":
            return _run_worker(args)
        if args.command == "healthcheck":
            return _run_healthcheck(args.url)
        return asyncio.run(_orchestrate(args))
    except RuntimeBoundaryError as exc:
        print(
            json.dumps(
                {"error_class": "runtime_boundary", "message": str(exc)},
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 70
    except Exception as exc:  # process boundary: do not emit unrestricted exception bodies
        print(
            json.dumps(
                {
                    "error_class": "runtime_failure",
                    "exception_type": type(exc).__name__,
                    "message": "sandbox runtime failed",
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 70


if __name__ == "__main__":
    raise SystemExit(main())
