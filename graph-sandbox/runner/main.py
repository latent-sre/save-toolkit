from __future__ import annotations

import hashlib
import json
import os
import signal
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator, Mapping, cast

from langgraph.types import Command

from runner.budgets import DurableWallTimeBudget
from runner.checkpoints import (
    CheckpointFingerprint,
    CheckpointIncompatible,
    CheckpointStore,
    ObservedCheckpointSaver,
    reconcile_interrupted_checkpoint_events,
)
from runner.effects import EffectLedger, reconcile_effect_transition_events
from runner.events import BoundaryEventStore
from runner.evidence import EvidenceExporter
from runner.fixtures import load_case
from runner.gateway import HttpGateway, ServiceOrigins
from runner.graph import (
    RunnerDependencies,
    build_graph,
    emit_terminal_event,
    ensure_run_started_events,
)
from runner.models import (
    CHECKPOINT_LINEAGE_VERSION,
    CONTRACT_VERSION,
    EVIDENCE_VERSION,
    SANDBOX_VERSION,
    GraphState,
    new_run_state,
)
from runner.runtime import runtime_evidence
from runner.validation import validate_atomic_id, validate_sha256, validate_source_revision


class ConfigurationError(ValueError):
    pass


class RunDeadlineExceeded(TimeoutError):
    pass


@dataclass(frozen=True)
class ExecutionResult:
    state: GraphState
    resume_source_checkpoint_id: str | None
    reconciliation_snapshot_pending: bool = False


@dataclass(frozen=True)
class RunnerConfig:
    checkout_url: str
    payments_url: str
    inventory_url: str
    checkpoint_db: Path
    effect_ledger_db: Path
    evidence_dir: Path
    run_id: str
    source_revision: str
    case_id: str
    case_digest: str
    run_timeout_seconds: int
    approval_fixture: str
    case_path: Path

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> "RunnerConfig":
        values = os.environ if environment is None else environment
        required = {
            "CHECKOUT_URL",
            "PAYMENTS_URL",
            "INVENTORY_URL",
            "CHECKPOINT_DB",
            "EFFECT_LEDGER_DB",
            "EVIDENCE_DIR",
            "RUN_ID",
            "SOURCE_REVISION",
            "CASE_ID",
            "CASE_DIGEST",
            "RUN_TIMEOUT_SECONDS",
            "APPROVAL_FIXTURE",
        }
        missing = sorted(name for name in required if not values.get(name))
        if missing:
            raise ConfigurationError(f"missing required environment: {', '.join(missing)}")
        run_id = validate_atomic_id(values["RUN_ID"], "RUN_ID")
        source_revision = validate_source_revision(values["SOURCE_REVISION"])
        case_id = validate_atomic_id(values["CASE_ID"], "CASE_ID")
        case_digest = values["CASE_DIGEST"]
        validate_sha256(case_digest, "CASE_DIGEST")
        try:
            timeout = int(values["RUN_TIMEOUT_SECONDS"])
        except ValueError as exc:
            raise ConfigurationError("RUN_TIMEOUT_SECONDS must be an integer") from exc
        if not 1 <= timeout <= 300:
            raise ConfigurationError("RUN_TIMEOUT_SECONDS must be from 1 through 300")
        approval_fixture = values["APPROVAL_FIXTURE"]
        if approval_fixture not in {"APPROVED", "REJECTED", "TIMEOUT"}:
            raise ConfigurationError(
                "APPROVAL_FIXTURE must be APPROVED, REJECTED, or TIMEOUT"
            )
        checkpoint_db = _absolute_path(values["CHECKPOINT_DB"], "CHECKPOINT_DB")
        effect_ledger_db = _absolute_path(values["EFFECT_LEDGER_DB"], "EFFECT_LEDGER_DB")
        evidence_dir = _absolute_path(values["EVIDENCE_DIR"], "EVIDENCE_DIR")
        if checkpoint_db == effect_ledger_db:
            raise ConfigurationError("checkpoint and effect ledger databases must be separate")
        case_path = Path("/app/cases") / f"{case_id}.json"
        return cls(
            checkout_url=values["CHECKOUT_URL"],
            payments_url=values["PAYMENTS_URL"],
            inventory_url=values["INVENTORY_URL"],
            checkpoint_db=checkpoint_db,
            effect_ledger_db=effect_ledger_db,
            evidence_dir=evidence_dir,
            run_id=run_id,
            source_revision=source_revision,
            case_id=case_id,
            case_digest=case_digest,
            run_timeout_seconds=timeout,
            approval_fixture=approval_fixture,
            case_path=case_path,
        )


def _absolute_path(value: str, field: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        raise ConfigurationError(f"{field} must be an absolute container path")
    return path


@contextmanager
def _run_deadline(seconds: float) -> Iterator[None]:
    if not hasattr(signal, "SIGALRM"):
        raise RuntimeError("graph-sandbox/v1 requires a Linux SIGALRM runtime")

    def deadline_handler(_signum: int, _frame: object) -> None:
        raise RunDeadlineExceeded("run deadline exhausted")

    previous = signal.signal(signal.SIGALRM, deadline_handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def _checkpoint_id(snapshot: object) -> str | None:
    config = getattr(snapshot, "config", None)
    if not isinstance(config, Mapping):
        return None
    configurable = config.get("configurable")
    if not isinstance(configurable, Mapping):
        return None
    candidate = configurable.get("checkpoint_id")
    return candidate if isinstance(candidate, str) else None


def _snapshot_has_interrupt(snapshot: object) -> bool:
    tasks = getattr(snapshot, "tasks", ())
    return any(bool(getattr(task, "interrupts", ())) for task in tasks)


def _execute_graph(
    graph: Any,
    initial_state: GraphState,
    events: BoundaryEventStore,
    approval_fixture: str,
) -> ExecutionResult:
    config = {"configurable": {"thread_id": initial_state["thread_id"]}}

    def result_from_state(
        result: Mapping[str, object],
        resume_source_checkpoint_id: str | None,
    ) -> ExecutionResult:
        snapshot = graph.get_state(config)
        next_nodes = tuple(getattr(snapshot, "next", ()))
        if next_nodes == ("reconcile_after_snapshot",):
            values = getattr(snapshot, "values", None)
            if not isinstance(values, Mapping):
                raise RuntimeError("reconciliation snapshot lacks durable state")
            return ExecutionResult(
                cast(GraphState, dict(values)),
                resume_source_checkpoint_id,
                True,
            )
        return ExecutionResult(
            cast(GraphState, dict(result)),
            resume_source_checkpoint_id,
        )

    snapshot = graph.get_state(config)
    values = getattr(snapshot, "values", None)
    if values and getattr(snapshot, "next", ()):
        checkpoint_id = _checkpoint_id(snapshot)
        if checkpoint_id is None:
            raise RuntimeError("resumable state lacks a source checkpoint ID")
        events.emit(
            "checkpoint.resume_started",
            initial_state,
            {"operation": "resume"},
            node_id="admit_run",
            checkpoint_id=checkpoint_id,
        )
        invocation: object
        if _snapshot_has_interrupt(snapshot):
            if approval_fixture == "TIMEOUT":
                events.emit(
                    "checkpoint.resume_failed",
                    initial_state,
                    {"operation": "resume", "result": "failed"},
                    node_id="terminal",
                    checkpoint_id=checkpoint_id,
                    failure_plane="graph-control",
                    error_class="approval-timeout-resume-refused",
                )
                raise RuntimeError("TIMEOUT fixture cannot resume an approval interrupt")
            invocation = Command(
                resume={
                    "decision": approval_fixture,
                    "actor_class": "fixture-operator",
                }
            )
        else:
            invocation = None
        try:
            result = graph.invoke(invocation, config)
        except Exception:
            events.emit(
                "checkpoint.resume_failed",
                initial_state,
                {"operation": "resume", "result": "failed"},
                node_id="terminal",
                checkpoint_id=checkpoint_id,
                failure_plane="checkpoint-store",
                error_class="checkpoint-resume-failed",
            )
            raise
        descendant_id = _checkpoint_id(graph.get_state(config))
        if descendant_id is None or descendant_id == checkpoint_id:
            events.emit(
                "checkpoint.resume_failed",
                initial_state,
                {"operation": "resume", "result": "failed"},
                node_id="terminal",
                checkpoint_id=checkpoint_id,
                failure_plane="checkpoint-store",
                error_class="checkpoint-resume-no-descendant",
            )
            raise RuntimeError("checkpoint resume did not create a recorded descendant")
        events.emit(
            "checkpoint.resume_completed",
            initial_state,
            {"operation": "resume", "result": "completed"},
            node_id="terminal",
            checkpoint_id=descendant_id,
        )
        return result_from_state(cast(Mapping[str, object], result), checkpoint_id)

    if values:
        return ExecutionResult(cast(GraphState, dict(values)), None)

    result = graph.invoke(initial_state, config)
    if "__interrupt__" in result:
        if approval_fixture == "TIMEOUT":
            raise RuntimeError("TIMEOUT fixture unexpectedly entered an approval interrupt")
        result = graph.invoke(
            Command(
                resume={
                    "decision": approval_fixture,
                    "actor_class": "fixture-operator",
                }
            ),
            config,
        )
    return result_from_state(cast(Mapping[str, object], result), None)


def _snapshot_terminal_event(
    events: BoundaryEventStore,
    state: Mapping[str, object],
    ended_at: str,
) -> dict[str, object]:
    """Build the non-durable terminal projection for one provisional snapshot."""

    projected = events.project()
    if not projected or state.get("outcome") != "UNKNOWN":
        raise RuntimeError("provisional reconciliation snapshot is not UNKNOWN")
    last = projected[-1]
    sequence = int(last["sequence"]) + 1
    return {
        "event_version": last["event_version"],
        "event_type": "run.terminal",
        "event_id": f"{state['run_id']}:{sequence:08d}",
        "sequence": sequence,
        "time_utc": ended_at,
        "contract_version": last["contract_version"],
        "sandbox_version": last["sandbox_version"],
        "source_revision": state["source_revision"],
        "run_id": state["run_id"],
        "case_id": state["case_id"],
        "case_digest": state["case_digest"],
        "thread_id": state["thread_id"],
        "node_id": "terminal",
        "task_id": None,
        "attempt_id": None,
        "replay_id": f"{state['run_id']}:replay-{state['replay_number']}",
        "checkpoint_id": None,
        "effect_id": None,
        "failure_plane": None,
        "error_class": None,
        "data": {"result": "terminal", "outcome": "UNKNOWN"},
    }


def _checkpoint_lineage(
    checkpointer: Any,
    thread_id: str,
    fingerprint: CheckpointFingerprint,
    resume_source_checkpoint_id: str | None,
) -> dict[str, object]:
    config = {"configurable": {"thread_id": thread_id}}
    checkpoints: list[dict[str, object]] = []
    for item in checkpointer.list(config):
        configurable = item.config.get("configurable", {})
        checkpoints.append(
            {
                "checkpoint_id": configurable.get("checkpoint_id"),
                "operation": "write",
                "result": "recorded",
            }
        )
    checkpoints.reverse()
    saver_checkpoint_ids = [
        cast(str, record["checkpoint_id"])
        for record in checkpoints
        if isinstance(record["checkpoint_id"], str)
    ]
    if len(saver_checkpoint_ids) != len(checkpoints):
        raise RuntimeError("configured SQLite saver returned a checkpoint without an ID")
    return {
        "lineage_version": CHECKPOINT_LINEAGE_VERSION,
        "contract_version": CONTRACT_VERSION,
        "state_schema": fingerprint.state_schema,
        "source_revision": fingerprint.source_revision,
        "thread_id": thread_id,
        "langgraph_version": fingerprint.langgraph_version,
        "sqlite_saver_version": fingerprint.sqlite_saver_version,
        "resume_source_checkpoint_id": resume_source_checkpoint_id,
        "checkpoints": checkpoints,
        "saver_checkpoint_ids": saver_checkpoint_ids,
    }


def _sanitized_final_state(state: Mapping[str, object]) -> dict[str, object]:
    allowed = {
        "contract_version",
        "state_schema",
        "run_id",
        "thread_id",
        "source_revision",
        "case_id",
        "case_digest",
        "replay_number",
        "phase",
        "outcome",
        "checkout",
        "checkout_status",
        "approval",
        "tasks",
        "receipts",
        "pending_effects",
        "readiness",
        "budgets",
        "cancellation",
        "failure",
    }
    return {key: state[key] for key in sorted(allowed) if key in state}


def _export_evidence(
    config: RunnerConfig,
    *,
    state: Mapping[str, object],
    events: BoundaryEventStore,
    ledger: EffectLedger,
    checkpoint_lineage: Mapping[str, object],
    started_at: str,
    ended_at: str,
    directory_name: str | None = None,
    event_records: list[Mapping[str, object]] | None = None,
) -> None:
    exporter = EvidenceExporter(
        config.evidence_dir,
        config.run_id,
        directory_name=directory_name,
    )
    exporter.write_jsonl(
        "events.jsonl",
        events.project() if event_records is None else event_records,
    )
    exporter.write_jsonl("effects.jsonl", ledger.project())
    final_state = _sanitized_final_state(state)
    exporter.write_json("final-state.json", final_state)
    exporter.write_json("checkpoint-lineage.json", checkpoint_lineage)
    exporter.write_json("runtime.json", runtime_evidence())

    checkout_effect_id = f"{config.run_id}:checkout_effect:0:effect-checkout"
    receipts = cast(Mapping[str, Mapping[str, object]], state.get("receipts", {}))
    checkout_receipt = receipts.get(checkout_effect_id)
    authoritative_result_id = None
    if checkout_receipt is not None:
        authoritative_result_id = checkout_receipt.get("authoritative_result_id")
        for name, field_name in (
            ("payment", "payment_receipt"),
            ("inventory", "inventory_receipt"),
        ):
            target_receipt = checkout_receipt.get(field_name)
            if isinstance(target_receipt, Mapping):
                exporter.write_json(f"receipts/{name}.json", dict(target_receipt))
    else:
        for name in ("payment", "inventory"):
            target_effect_id = f"{config.run_id}:checkout_effect:0:effect-{name}"
            target_receipt = receipts.get(target_effect_id)
            if target_receipt is not None:
                exporter.write_json(f"receipts/{name}.json", dict(target_receipt))

    inventory = sorted(
        path.relative_to(exporter.run_dir).as_posix()
        for path in exporter.run_dir.rglob("*")
        if path.is_file() and path.name not in {"manifest.json", "checksums.sha256"}
    )
    outcome = state.get("outcome")
    if outcome == "SUCCEEDED" and authoritative_result_id is None:
        raise RuntimeError("success cannot be exported without authoritative_result_id")
    exporter.write_json(
        "manifest.json",
        {
            "evidence_version": EVIDENCE_VERSION,
            "contract_version": CONTRACT_VERSION,
            "sandbox_version": SANDBOX_VERSION,
            "source_revision": config.source_revision,
            "run_id": config.run_id,
            "case_id": config.case_id,
            "case_digest": config.case_digest,
            "thread_id": state["thread_id"],
            "outcome": outcome,
            "authoritative_result_id": authoritative_result_id,
            "started_at": started_at,
            "ended_at": ended_at,
            "artifacts": inventory,
        },
    )
    exporter.write_checksums()


def run(environment: Mapping[str, str] | None = None) -> int:
    config = RunnerConfig.from_environment(environment)
    try:
        case_bytes = config.case_path.read_bytes()
    except OSError as exc:
        raise ConfigurationError("unable to read the selected immutable case") from exc
    observed_case_digest = hashlib.sha256(case_bytes).hexdigest()
    if observed_case_digest != config.case_digest:
        raise ConfigurationError("CASE_DIGEST does not match the selected immutable case")
    sandbox_case = load_case(config.case_path)
    if sandbox_case["case_id"] != config.case_id:
        raise ConfigurationError("CASE_ID does not match the selected immutable case")
    state = new_run_state(
        sandbox_case,
        run_id=config.run_id,
        source_revision=config.source_revision,
        case_digest=config.case_digest,
    )
    wall_budget = DurableWallTimeBudget.acquire(
        config.checkpoint_db.with_name("wall-time-budget.sqlite3"),
        run_id=config.run_id,
        thread_id=state["thread_id"],
        source_revision=config.source_revision,
        case_digest=config.case_digest,
        limit_ms=state["budgets"]["wall_time_ms"]["limit"],
    )
    started_at = datetime.fromtimestamp(
        wall_budget.started_epoch_ms / 1000,
        UTC,
    ).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    events_path = config.effect_ledger_db.with_name("events.sqlite3")
    events = BoundaryEventStore(events_path)
    ledger = EffectLedger(config.effect_ledger_db)
    fingerprint = CheckpointFingerprint.current(config.source_revision)
    gateway = HttpGateway(
        ServiceOrigins(
            checkout=config.checkout_url,
            payments=config.payments_url,
            inventory=config.inventory_url,
        ),
        timeout_seconds=min(5.0, float(config.run_timeout_seconds)),
    )
    dependencies = RunnerDependencies(
        gateway=gateway,
        ledger=ledger,
        events=events,
        case=sandbox_case,
        approval_fixture=config.approval_fixture,
        wall_time_elapsed_ms=wall_budget.elapsed_ms,
    )
    ensure_run_started_events(events, state)
    reconcile_effect_transition_events(ledger, events, state)
    try:
        with CheckpointStore(config.checkpoint_db, fingerprint) as checkpointer:
            recovered_resume_source = reconcile_interrupted_checkpoint_events(
                checkpointer,
                events,
                state,
            )
            observed_checkpointer = ObservedCheckpointSaver(checkpointer, events, state)
            graph = build_graph(dependencies, observed_checkpointer)
            remaining_wall_ms = wall_budget.remaining_ms()
            effective_timeout = (
                min(config.run_timeout_seconds, remaining_wall_ms / 1000)
                if remaining_wall_ms > 0
                else 1.0
            )
            with _run_deadline(effective_timeout):
                execution = _execute_graph(
                    graph,
                    state,
                    events,
                    config.approval_fixture,
                )
            if execution.reconciliation_snapshot_pending:
                provisional_state = cast(GraphState, dict(execution.state))
                provisional_state.update(
                    {
                        "phase": "TERMINAL",
                        "outcome": "UNKNOWN",
                        "checkout_status": "UNKNOWN",
                    }
                )
                provisional_ended_at = (
                    datetime.now(UTC)
                    .isoformat(timespec="milliseconds")
                    .replace("+00:00", "Z")
                )
                provisional_events = [
                    *events.project(),
                    _snapshot_terminal_event(
                        events,
                        provisional_state,
                        provisional_ended_at,
                    ),
                ]
                provisional_lineage = _checkpoint_lineage(
                    checkpointer,
                    state["thread_id"],
                    fingerprint,
                    None,
                )
                _export_evidence(
                    config,
                    state=provisional_state,
                    events=events,
                    ledger=ledger,
                    checkpoint_lineage=provisional_lineage,
                    started_at=started_at,
                    ended_at=provisional_ended_at,
                    directory_name=f"{config.run_id}-unknown",
                    event_records=provisional_events,
                )
                with _run_deadline(max(0.001, wall_budget.remaining_ms() / 1000)):
                    execution = _execute_graph(
                        graph,
                        state,
                        events,
                        config.approval_fixture,
                    )
                if execution.reconciliation_snapshot_pending:
                    raise RuntimeError("reconciliation resume did not advance")
            final_state = execution.state
            emit_terminal_event(events, final_state)
            lineage = _checkpoint_lineage(
                checkpointer,
                state["thread_id"],
                fingerprint,
                execution.resume_source_checkpoint_id or recovered_resume_source,
            )
    except CheckpointIncompatible as exc:
        events.emit(
            "checkpoint.rejected",
            state,
            {
                "operation": "resume",
                "result": "rejected",
                "mismatches": sorted(exc.mismatches),
            },
            node_id="admit_run",
            failure_plane="checkpoint-store",
            error_class="checkpoint_incompatible",
        )
        raise
    ended_at = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    timeline_completed = (config.evidence_dir / f"{config.run_id}-unknown").is_dir()
    if timeline_completed:
        current_effect = ledger.current(
            f"{config.run_id}:checkout_effect:0:effect-checkout"
        )
        if (
            final_state.get("outcome") != "SUCCEEDED"
            or current_effect is None
            or current_effect.get("effect_state") != "RECONCILED"
        ):
            raise RuntimeError("reconciliation timeline did not reach RECONCILED")
    _export_evidence(
        config,
        state=final_state,
        events=events,
        ledger=ledger,
        checkpoint_lineage=lineage,
        started_at=started_at,
        ended_at=ended_at,
        directory_name=(
            f"{config.run_id}-reconciled" if timeline_completed else None
        ),
    )
    summary = {
        "event": "graph_runner_terminal",
        "run_id": config.run_id,
        "outcome": final_state.get("outcome"),
    }
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")), flush=True)
    return 0 if final_state.get("outcome") == "SUCCEEDED" else 2


def main() -> None:
    try:
        exit_code = run()
    except (ConfigurationError, ValueError) as exc:
        print(
            json.dumps(
                {"event": "graph_runner_rejected", "error_class": type(exc).__name__},
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(64) from None
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
