from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, cast

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send, interrupt

from runner.controls import BudgetExhausted, consume_budget, transition_cancellation
from runner.effects import EffectLedger, ReplayRefused, derive_idempotency_key
from runner.events import BoundaryEventStore
from runner.gateway import AmbiguousDispatch, CheckoutFailure, GatewayUnavailable
from runner.models import GraphState, SandboxCase, remove_pending_effects
from runner.validation import require_closed_mapping


READINESS_SERVICES = ("checkout", "payments", "inventory")
GRAPH_NODE_NAMES = (
    "admit_run",
    "readiness",
    "join_readiness",
    "fixture_plan",
    "request_approval",
    "checkout_effect",
    "reconcile_if_ambiguous",
    "terminal",
)


class Gateway(Protocol):
    def health(self, service: str, *, case_id: str) -> dict[str, str]: ...

    def dispatch_checkout(
        self,
        checkout: Mapping[str, object],
        *,
        idempotency_key: str,
        case_id: str,
        request_id: str,
    ) -> dict[str, object]: ...

    def get_checkout_receipt(
        self,
        idempotency_key: str,
        *,
        case_id: str,
    ) -> dict[str, object] | None: ...

    def get_target_receipt(
        self,
        effect_class: str,
        checkout_idempotency_key: str,
        *,
        case_id: str,
    ) -> dict[str, object] | None: ...


@dataclass(frozen=True)
class RunnerDependencies:
    gateway: Gateway
    ledger: EffectLedger
    events: BoundaryEventStore
    case: SandboxCase
    approval_fixture: str = "APPROVED"
    monotonic_clock: Any = time.monotonic
    started_monotonic: float = field(default_factory=time.monotonic)
    wall_time_elapsed_ms: Callable[[], int] | None = None

    def __post_init__(self) -> None:
        if self.approval_fixture not in {"APPROVED", "REJECTED", "TIMEOUT"}:
            raise ValueError("approval_fixture must be APPROVED, REJECTED, or TIMEOUT")

    def observed_wall_time_ms(self) -> int:
        if self.wall_time_elapsed_ms is not None:
            observed = self.wall_time_elapsed_ms()
            if isinstance(observed, bool) or not isinstance(observed, int) or observed < 0:
                raise ValueError("wall_time_elapsed_ms must return a non-negative integer")
            return observed
        return max(
            0,
            int((self.monotonic_clock() - self.started_monotonic) * 1000),
        )


def _task_lineage(state: Mapping[str, object], node_id: str) -> tuple[str, str]:
    task_id = f"{state['run_id']}:{node_id}:0"
    return task_id, f"{task_id}:attempt-1"


def _checkout_effect_id(state: Mapping[str, object]) -> str:
    return f"{state['run_id']}:checkout_effect:0:effect-checkout"


def _payload_hash(checkout: Mapping[str, object]) -> str:
    payload = {
        "order_id": checkout["order_id"],
        "amount_cents": checkout["amount_cents"],
        "items": checkout["items"],
    }
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _receipt_updates(
    state: Mapping[str, object],
    effect_id: str,
    checkout_receipt: Mapping[str, object],
) -> dict[str, dict[str, object]]:
    run_id = state["run_id"]
    return {
        effect_id: dict(checkout_receipt),
        f"{run_id}:checkout_effect:0:effect-payment": dict(
            cast(Mapping[str, object], checkout_receipt["payment_receipt"])
        ),
        f"{run_id}:checkout_effect:0:effect-inventory": dict(
            cast(Mapping[str, object], checkout_receipt["inventory_receipt"])
        ),
    }


def _known_target_receipt_updates(
    state: Mapping[str, object],
    known_receipts: Mapping[str, Mapping[str, object]],
) -> dict[str, dict[str, object]]:
    run_id = state["run_id"]
    return {
        f"{run_id}:checkout_effect:0:effect-{effect_class}": dict(receipt)
        for effect_class, receipt in known_receipts.items()
    }


def emit_terminal_event(
    events: BoundaryEventStore,
    state: Mapping[str, object],
) -> None:
    """Emit the sole terminal event after LangGraph has persisted its final checkpoint."""

    existing = [
        event
        for event in events.project()
        if event["event_type"] in {"run.terminal", "run.cancelled", "run.inconclusive"}
    ]
    if existing:
        if len(existing) != 1 or events.project()[-1] != existing[0]:
            raise RuntimeError("boundary event store contains a non-final or duplicate terminal")
        return
    outcome = state.get("outcome")
    if not isinstance(outcome, str):
        raise RuntimeError("terminal state lacks an outcome")
    event_type = {
        "CANCELLED": "run.cancelled",
        "INCONCLUSIVE": "run.inconclusive",
    }.get(outcome, "run.terminal")
    data: dict[str, object] = {"result": "terminal", "outcome": outcome}
    if outcome == "SUCCEEDED":
        effect_id = _checkout_effect_id(state)
        receipt = cast(
            Mapping[str, object] | None,
            cast(Mapping[str, Mapping[str, object]], state.get("receipts", {})).get(effect_id),
        )
        authoritative_result_id = None if receipt is None else receipt.get("authoritative_result_id")
        if not isinstance(authoritative_result_id, str):
            raise RuntimeError("successful terminal state lacks an authoritative result")
        data["authoritative_result_id"] = authoritative_result_id
    events.emit(event_type, state, data, node_id="terminal")


def ensure_run_started_events(
    events: BoundaryEventStore,
    state: Mapping[str, object],
) -> None:
    projected = events.project()
    if not projected:
        events.emit("run.accepted", state, {"result": "accepted"}, node_id="admit_run")
        events.emit("run.started", state, {"result": "started"}, node_id="admit_run")
        return
    if len(projected) == 1 and projected[0]["event_type"] == "run.accepted":
        events.emit("run.started", state, {"result": "started"}, node_id="admit_run")
        return
    if [event["event_type"] for event in projected[:2]] != ["run.accepted", "run.started"]:
        raise RuntimeError("boundary event store lacks the immutable run start prefix")


def build_graph(dependencies: RunnerDependencies, checkpointer: Any) -> Any:
    """Build the one consumer-specific graph; effect execution has no RetryPolicy."""

    def wall_budget_failure(
        state: GraphState,
        *,
        node_id: str,
        task_id: str | None = None,
        attempt_id: str | None = None,
        effect_id: str | None = None,
    ) -> GraphState | None:
        wall_budget = state["budgets"]["wall_time_ms"]
        observed = max(wall_budget["consumed"], dependencies.observed_wall_time_ms())
        if observed < wall_budget["limit"]:
            return None
        budgets = consume_budget(
            state["budgets"],
            "wall_time_ms",
            wall_budget["limit"] - wall_budget["consumed"],
        )
        dependencies.events.emit(
            "budget.exhausted",
            state,
            {
                "kind": "wall_time_ms",
                "limit": wall_budget["limit"],
                "consumed": wall_budget["limit"],
                "remaining": 0,
            },
            node_id=node_id,
            task_id=task_id,
            attempt_id=attempt_id,
            effect_id=effect_id,
            failure_plane="graph-control",
            error_class="budget_exhausted",
        )
        return {
            "budgets": budgets,
            "phase": "TERMINAL",
            "outcome": "FAILED",
            "failure": {
                "plane": "graph-control",
                "error_class": "budget_exhausted",
                "retryable": False,
                "disposition": "stop",
            },
        }

    def admit_run(state: GraphState) -> GraphState:
        cancellation = state["cancellation"]
        if cancellation["state"] == "REQUESTED":
            dependencies.events.emit(
                "cancellation.requested",
                state,
                {"state": "REQUESTED", "request_id": cancellation["request_id"]},
                node_id="admit_run",
            )
            propagated = transition_cancellation(cancellation, "PROPAGATED")
            dependencies.events.emit(
                "cancellation.propagated",
                state,
                {"state": "PROPAGATED", "request_id": propagated["request_id"]},
                node_id="admit_run",
            )
            acknowledged = transition_cancellation(
                propagated,
                "ACKNOWLEDGED",
                acknowledgement_ms=0,
            )
            dependencies.events.emit(
                "cancellation.acknowledged",
                state,
                {
                    "state": "ACKNOWLEDGED",
                    "request_id": acknowledged["request_id"],
                    "acknowledgement_ms": 0,
                },
                node_id="admit_run",
            )
            return {
                "cancellation": acknowledged,
                "phase": "TERMINAL",
                "outcome": "CANCELLED",
            }
        failure = wall_budget_failure(state, node_id="admit_run")
        if failure is not None:
            return failure
        return {"phase": "ADMISSION"}

    def fanout_or_terminal(state: GraphState) -> str | list[Send]:
        if state.get("outcome") is not None:
            return "terminal"
        dependencies.events.emit(
            "edge.fanout_emitted",
            state,
            {"targets": list(READINESS_SERVICES)},
            node_id="admit_run",
        )
        shared = {
            "contract_version": state["contract_version"],
            "state_schema": state["state_schema"],
            "run_id": state["run_id"],
            "thread_id": state["thread_id"],
            "source_revision": state["source_revision"],
            "case_id": state["case_id"],
            "case_digest": state["case_digest"],
            "replay_number": state["replay_number"],
        }
        return [Send("readiness", {**shared, "readiness_target": service}) for service in READINESS_SERVICES]

    def readiness(state: GraphState) -> GraphState:
        service = state["readiness_target"]
        ordinal = READINESS_SERVICES.index(service)
        task_id = f"{state['run_id']}:readiness:{ordinal}"
        attempt_id = f"{task_id}:attempt-1"
        dependencies.events.emit(
            "task.started",
            state,
            {"status": "started"},
            node_id="readiness",
            task_id=task_id,
            attempt_id=attempt_id,
        )
        try:
            result = dependencies.gateway.health(service, case_id=state["case_id"])
            readiness_result: dict[str, object] = {
                "status": "ok",
                "service": result["service"],
            }
            task_status = "completed"
            event_type = "task.completed"
            event_data = {"status": "completed"}
            failure_plane = None
            error_class = None
        except GatewayUnavailable as exc:
            readiness_result = {
                "status": "failed",
                "service": service,
                "error_class": exc.error_class,
            }
            task_status = "failed"
            event_type = "task.failed"
            event_data = {"status": "failed", "disposition": "stop"}
            failure_plane = service
            error_class = exc.error_class
        dependencies.events.emit(
            event_type,
            state,
            event_data,
            node_id="readiness",
            task_id=task_id,
            attempt_id=attempt_id,
            failure_plane=failure_plane,
            error_class=error_class,
        )
        return {
            "readiness": {service: cast(Any, readiness_result)},
            "tasks": {task_id: {"status": task_status, "attempt": 1}},
        }

    def join_readiness(state: GraphState) -> GraphState:
        readiness_results = state.get("readiness", {})
        missing = sorted(set(READINESS_SERVICES) - set(readiness_results))
        failed = sorted(
            service
            for service, result in readiness_results.items()
            if result["status"] != "ok"
        )
        if missing or failed:
            dependencies.events.emit(
                "edge.join_starved",
                state,
                {"missing_branches": missing or failed},
                node_id="join_readiness",
                failure_plane=(failed[0] if failed else "graph-control"),
                error_class="readiness_join_incomplete",
            )
            return {
                "phase": "TERMINAL",
                "outcome": "FAILED",
                "failure": {
                    "plane": failed[0] if failed else "graph-control",
                    "error_class": "readiness_join_incomplete",
                    "retryable": False,
                    "disposition": "stop",
                },
            }
        dependencies.events.emit(
            "edge.join_satisfied",
            state,
            {"branches": list(READINESS_SERVICES)},
            node_id="join_readiness",
        )
        return {"phase": "PLANNING"}

    def after_readiness(state: GraphState) -> str:
        return "terminal" if state.get("outcome") is not None else "fixture_plan"

    def fixture_plan(state: GraphState) -> GraphState:
        try:
            budgets = consume_budget(state["budgets"], "model_calls", 1)
            budgets = consume_budget(
                budgets,
                "tokens",
                dependencies.case["model_fixture"]["token_count"],
            )
        except BudgetExhausted as exc:
            counter = state["budgets"][exc.kind]  # type: ignore[literal-required]
            dependencies.events.emit(
                "budget.exhausted",
                state,
                {
                    "kind": exc.kind,
                    "limit": counter["limit"],
                    "consumed": counter["consumed"],
                    "remaining": counter["limit"] - counter["consumed"],
                },
                node_id="fixture_plan",
                failure_plane="model-fixture",
                error_class="budget_exhausted",
            )
            return {
                "phase": "TERMINAL",
                "outcome": "FAILED",
                "failure": {
                    "plane": "model-fixture",
                    "error_class": "budget_exhausted",
                    "retryable": False,
                    "disposition": "stop",
                },
            }

        for kind in ("model_calls", "tokens", "spend_micro_usd"):
            counter = budgets[kind]  # type: ignore[literal-required]
            dependencies.events.emit(
                "budget.observed",
                state,
                {
                    "kind": kind,
                    "limit": counter["limit"],
                    "consumed": counter["consumed"],
                    "remaining": counter["limit"] - counter["consumed"],
                },
                node_id="fixture_plan",
            )
        request_id = state["approval"]["request_id"]
        dependencies.events.emit(
            "approval.requested",
            state,
            {"request_id": request_id, "approval_status": "PENDING"},
            node_id="request_approval",
        )
        if dependencies.approval_fixture == "TIMEOUT":
            timed_out = dependencies.events.emit(
                "approval.timed_out",
                state,
                {"request_id": request_id, "approval_status": "TIMED_OUT"},
                node_id="request_approval",
            )
            return {
                "budgets": budgets,
                "approval": {
                    "request_id": request_id,
                    "status": "TIMED_OUT",
                    "actor_class": "fixture-operator",
                    "decision_time": cast(str, timed_out["time_utc"]),
                },
                "phase": "TERMINAL",
                "outcome": "REJECTED",
            }
        return {
            "budgets": budgets,
            "approval": {
                "request_id": request_id,
                "status": "PENDING",
                "actor_class": "fixture-operator",
                "decision_time": None,
            },
            "phase": "AWAITING_APPROVAL",
        }

    def approval_route(state: GraphState) -> str:
        return "terminal" if state["approval"]["status"] == "TIMED_OUT" else "request_approval"

    def request_approval(state: GraphState) -> GraphState:
        response = interrupt(
            {
                "contract_version": state["contract_version"],
                "request_id": state["approval"]["request_id"],
                "action": "dispatch synthetic checkout",
                "allowed_decisions": ["APPROVED", "REJECTED"],
            }
        )
        if state["cancellation"]["state"] == "REQUESTED":
            requested = state["cancellation"]
            dependencies.events.emit(
                "cancellation.requested",
                state,
                {"state": "REQUESTED", "request_id": requested["request_id"]},
                node_id="request_approval",
            )
            propagated = transition_cancellation(requested, "PROPAGATED")
            dependencies.events.emit(
                "cancellation.propagated",
                state,
                {"state": "PROPAGATED", "request_id": propagated["request_id"]},
                node_id="request_approval",
            )
            acknowledged = transition_cancellation(
                propagated,
                "ACKNOWLEDGED",
                acknowledgement_ms=0,
            )
            dependencies.events.emit(
                "cancellation.acknowledged",
                state,
                {
                    "state": "ACKNOWLEDGED",
                    "request_id": acknowledged["request_id"],
                    "acknowledgement_ms": 0,
                },
                node_id="request_approval",
            )
            return {
                "cancellation": acknowledged,
                "phase": "TERMINAL",
                "outcome": "CANCELLED",
            }
        parsed = require_closed_mapping(
            response,
            field="approval response",
            required={"decision", "actor_class"},
            optional={"decision_time"},
        )
        decision = parsed["decision"]
        if decision not in {"APPROVED", "REJECTED"}:
            raise ValueError("approval decision must be APPROVED or REJECTED")
        if parsed["actor_class"] != "fixture-operator":
            raise ValueError("approval actor_class must be fixture-operator")
        event_type = "approval.approved" if decision == "APPROVED" else "approval.rejected"
        event = dependencies.events.emit(
            event_type,
            state,
            {
                "request_id": state["approval"]["request_id"],
                "approval_status": decision,
                "actor_class": "fixture-operator",
            },
            node_id="request_approval",
        )
        return {
            "approval": {
                "request_id": state["approval"]["request_id"],
                "status": decision,
                "actor_class": "fixture-operator",
                "decision_time": cast(str, event["time_utc"]),
            },
            "phase": "EXECUTING" if decision == "APPROVED" else "TERMINAL",
            "outcome": None if decision == "APPROVED" else "REJECTED",
        }

    def after_approval(state: GraphState) -> str:
        return "checkout_effect" if state["approval"]["status"] == "APPROVED" else "terminal"

    def after_checkout(state: GraphState) -> str:
        checkout_fixture = cast(
            Mapping[str, Mapping[str, str]],
            dependencies.case["service_fixtures"],
        )["checkout"]["effect"]
        if state.get("pending_effects") and checkout_fixture == "ambiguous_after_commit":
            return "reconcile_after_snapshot"
        return "reconcile_if_ambiguous"

    def checkout_effect(state: GraphState) -> GraphState:
        effect_id = _checkout_effect_id(state)
        task_id = f"{state['run_id']}:checkout_effect:0"
        attempt_number = dependencies.events.next_attempt_number(task_id)
        attempt_id = f"{task_id}:attempt-{attempt_number}"
        request_id = hashlib.sha256(attempt_id.encode("ascii")).hexdigest()
        replay_id = f"{state['run_id']}:replay-{state['replay_number']}"
        key = derive_idempotency_key(effect_id)
        payload_hash = _payload_hash(state["checkout"])
        wall_failure = wall_budget_failure(
            state,
            node_id="checkout_effect",
            task_id=task_id,
            attempt_id=attempt_id,
            effect_id=effect_id,
        )
        if wall_failure is not None:
            return wall_failure
        try:
            budgets = consume_budget(state["budgets"], "attempts", 1)
        except BudgetExhausted as exc:
            counter = state["budgets"]["attempts"]
            dependencies.events.emit(
                "budget.exhausted",
                state,
                {
                    "kind": "attempts",
                    "limit": counter["limit"],
                    "consumed": counter["consumed"],
                    "remaining": counter["limit"] - counter["consumed"],
                },
                node_id="checkout_effect",
                task_id=task_id,
                attempt_id=attempt_id,
                effect_id=effect_id,
                failure_plane="graph-control",
                error_class="budget_exhausted",
            )
            return {
                "phase": "TERMINAL",
                "outcome": "FAILED",
                "failure": {
                    "plane": "graph-control",
                    "error_class": "budget_exhausted",
                    "retryable": False,
                    "disposition": "stop",
                },
            }

        dependencies.events.emit(
            "task.started",
            state,
            {"status": "started"},
            node_id="checkout_effect",
            task_id=task_id,
            attempt_id=attempt_id,
            effect_id=effect_id,
        )

        current = dependencies.ledger.current(effect_id)
        if current is not None:
            if current["effect_state"] in {"RECEIPT_RECORDED", "RECONCILED"}:
                receipt = cast(Mapping[str, object], current["receipt"])
                dependencies.events.emit(
                    "task.completed",
                    state,
                    {"status": "completed"},
                    node_id="checkout_effect",
                    task_id=task_id,
                    attempt_id=attempt_id,
                    effect_id=effect_id,
                )
                return {
                    "budgets": budgets,
                    "receipts": _receipt_updates(state, effect_id, receipt),
                    "pending_effects": remove_pending_effects(effect_id),
                    "checkout_status": "COMPLETE",
                    "phase": "FINALIZING",
                    "tasks": {
                        task_id: {"status": "completed", "attempt": attempt_number}
                    },
                }
            if current["effect_state"] == "DISPATCHED":
                current = dependencies.ledger.mark_unknown(
                    effect_id,
                    "runner_restart_after_dispatch",
                    attempt_id=attempt_id,
                    replay_id=replay_id,
                )
                dependencies.events.emit(
                    "effect.unknown",
                    state,
                    {
                        "effect_class": "checkout",
                        "effect_state": "UNKNOWN",
                        "reason_class": "runner_restart_after_dispatch",
                    },
                    node_id="checkout_effect",
                    task_id=task_id,
                    attempt_id=attempt_id,
                    effect_id=effect_id,
                    failure_plane="runner",
                    error_class="runner_restart_after_dispatch",
                )
            try:
                dependencies.ledger.require_replay_safe(effect_id, explicit_replay=False)
            except ReplayRefused:
                dependencies.events.emit(
                    "effect.replay_refused",
                    state,
                    {
                        "effect_class": "checkout",
                        "effect_state": "UNKNOWN",
                        "reason_class": "automatic_replay_forbidden",
                    },
                    node_id="checkout_effect",
                    task_id=task_id,
                    attempt_id=attempt_id,
                    effect_id=effect_id,
                    failure_plane="graph-control",
                    error_class="automatic_replay_forbidden",
                )
                dependencies.events.emit(
                    "task.failed",
                    state,
                    {"status": "failed", "disposition": "reconcile"},
                    node_id="checkout_effect",
                    task_id=task_id,
                    attempt_id=attempt_id,
                    effect_id=effect_id,
                    failure_plane="graph-control",
                    error_class="automatic_replay_forbidden",
                )
                return {
                    "budgets": budgets,
                    "pending_effects": [effect_id],
                    "checkout_status": "UNKNOWN",
                    "phase": "RECONCILING",
                    "outcome": "UNKNOWN",
                    "tasks": {
                        task_id: {"status": "failed", "attempt": attempt_number}
                    },
                }

        if current is None:
            dependencies.ledger.prepare(
                effect_id,
                key,
                payload_hash,
                "checkout",
                attempt_id=attempt_id,
                replay_id=replay_id,
            )
            dependencies.events.emit(
                "effect.prepared",
                state,
                {"effect_class": "checkout", "effect_state": "PREPARED"},
                node_id="checkout_effect",
                task_id=task_id,
                attempt_id=attempt_id,
                effect_id=effect_id,
            )
        dependencies.ledger.mark_dispatched(
            effect_id,
            attempt_id=attempt_id,
            replay_id=replay_id,
        )
        dependencies.events.emit(
            "effect.dispatched",
            state,
            {"effect_class": "checkout", "effect_state": "DISPATCHED"},
            node_id="checkout_effect",
            task_id=task_id,
            attempt_id=attempt_id,
            effect_id=effect_id,
        )
        try:
            receipt = dependencies.gateway.dispatch_checkout(
                state["checkout"],
                idempotency_key=key,
                case_id=state["case_id"],
                request_id=request_id,
            )
        except (AmbiguousDispatch, TimeoutError) as exc:
            reason = getattr(exc, "error_class", "runner_deadline_exceeded")
            dependencies.ledger.mark_unknown(
                effect_id,
                reason,
                attempt_id=attempt_id,
                replay_id=replay_id,
            )
            dependencies.events.emit(
                "effect.unknown",
                state,
                {
                    "effect_class": "checkout",
                    "effect_state": "UNKNOWN",
                    "reason_class": reason,
                },
                node_id="checkout_effect",
                task_id=task_id,
                attempt_id=attempt_id,
                effect_id=effect_id,
                failure_plane="checkout",
                error_class=reason,
            )
            dependencies.events.emit(
                "task.failed",
                state,
                {"status": "failed", "disposition": "reconcile"},
                node_id="checkout_effect",
                task_id=task_id,
                attempt_id=attempt_id,
                effect_id=effect_id,
                failure_plane="checkout",
                error_class=reason,
            )
            if (
                cast(
                    Mapping[str, Mapping[str, str]],
                    dependencies.case["service_fixtures"],
                )["checkout"]["effect"]
                == "ambiguous_after_commit"
            ):
                dependencies.events.emit(
                    "effect.replay_refused",
                    state,
                    {
                        "effect_class": "checkout",
                        "effect_state": "UNKNOWN",
                        "reason_class": "reconciliation_snapshot_required",
                    },
                    node_id="checkout_effect",
                    task_id=task_id,
                    attempt_id=attempt_id,
                    effect_id=effect_id,
                    failure_plane="graph-control",
                    error_class="automatic_replay_forbidden",
                )
            return {
                "budgets": budgets,
                "pending_effects": [effect_id],
                "checkout_status": "UNKNOWN",
                "phase": "RECONCILING",
                "outcome": "UNKNOWN",
                "tasks": {
                    task_id: {"status": "failed", "attempt": attempt_number}
                },
            }
        except CheckoutFailure as exc:
            dependencies.ledger.mark_unknown(
                effect_id,
                exc.error_class,
                attempt_id=attempt_id,
                replay_id=replay_id,
            )
            dependencies.events.emit(
                "effect.unknown",
                state,
                {
                    "effect_class": "checkout",
                    "effect_state": "UNKNOWN",
                    "reason_class": exc.error_class,
                },
                node_id="checkout_effect",
                task_id=task_id,
                attempt_id=attempt_id,
                effect_id=effect_id,
                failure_plane="checkout",
                error_class=exc.error_class,
            )
            dependencies.events.emit(
                "task.failed",
                state,
                {"status": "failed", "disposition": "reconcile"},
                node_id="checkout_effect",
                task_id=task_id,
                attempt_id=attempt_id,
                effect_id=effect_id,
                failure_plane="checkout",
                error_class=exc.error_class,
            )
            return {
                "budgets": budgets,
                "pending_effects": [effect_id],
                "checkout_status": "UNKNOWN",
                "phase": "RECONCILING",
                "outcome": "UNKNOWN",
                "tasks": {
                    task_id: {"status": "failed", "attempt": attempt_number}
                },
                "failure": {
                    "plane": "checkout",
                    "error_class": exc.error_class,
                    "retryable": False,
                    "disposition": "reconcile",
                },
            }

        dependencies.ledger.record_receipt(
            effect_id,
            receipt,
            attempt_id=attempt_id,
            replay_id=replay_id,
        )
        dependencies.events.emit(
            "effect.receipt_recorded",
            state,
            {
                "effect_class": "checkout",
                "effect_state": "RECEIPT_RECORDED",
                "authoritative_result_id": receipt["authoritative_result_id"],
            },
            node_id="checkout_effect",
            task_id=task_id,
            attempt_id=attempt_id,
            effect_id=effect_id,
        )
        dependencies.events.emit(
            "task.completed",
            state,
            {"status": "completed"},
            node_id="checkout_effect",
            task_id=task_id,
            attempt_id=attempt_id,
            effect_id=effect_id,
        )
        return {
            "budgets": budgets,
            "receipts": _receipt_updates(state, effect_id, receipt),
            "pending_effects": remove_pending_effects(effect_id),
            "checkout_status": "COMPLETE",
            "phase": "FINALIZING",
            "outcome": None,
            "tasks": {task_id: {"status": "completed", "attempt": attempt_number}},
        }

    def reconcile_if_ambiguous(state: GraphState) -> GraphState:
        effect_id = _checkout_effect_id(state)
        task_id = f"{state['run_id']}:reconcile_if_ambiguous:0"
        attempt_number = dependencies.events.next_attempt_number(task_id)
        attempt_id = f"{task_id}:attempt-{attempt_number}"
        replay_id = f"{state['run_id']}:replay-{state['replay_number']}"
        dependencies.events.emit(
            "task.started",
            state,
            {"status": "started"},
            node_id="reconcile_if_ambiguous",
            task_id=task_id,
            attempt_id=attempt_id,
            effect_id=effect_id,
        )
        current = dependencies.ledger.current(effect_id)
        if current is None or current["effect_state"] != "UNKNOWN":
            dependencies.events.emit(
                "task.completed",
                state,
                {"status": "completed"},
                node_id="reconcile_if_ambiguous",
                task_id=task_id,
                attempt_id=attempt_id,
                effect_id=effect_id,
            )
            return {
                "phase": "FINALIZING",
                "tasks": {task_id: {"status": "completed", "attempt": attempt_number}},
            }
        known_receipts: dict[str, Mapping[str, object]] = {}
        authoritative_outcome: str | None = None
        try:
            receipt = dependencies.gateway.get_checkout_receipt(
                current["idempotency_key"],
                case_id=state["case_id"],
            )
        except CheckoutFailure as exc:
            receipt = None
            authoritative_outcome = exc.outcome
            known_receipts.update(
                {
                    effect_class: cast(Mapping[str, object], target_receipt)
                    for effect_class, target_receipt in exc.known_receipts.items()
                }
            )
        except GatewayUnavailable as exc:
            dependencies.events.emit(
                "effect.replay_refused",
                state,
                {
                    "effect_class": "checkout",
                    "effect_state": "UNKNOWN",
                    "reason_class": "reconciliation_unavailable",
                },
                node_id="reconcile_if_ambiguous",
                effect_id=effect_id,
                failure_plane="checkout",
                error_class=exc.error_class,
            )
            dependencies.events.emit(
                "task.failed",
                state,
                {"status": "failed", "disposition": "stop"},
                node_id="reconcile_if_ambiguous",
                task_id=task_id,
                attempt_id=attempt_id,
                effect_id=effect_id,
                failure_plane="checkout",
                error_class=exc.error_class,
            )
            return {
                "phase": "TERMINAL",
                "outcome": "UNKNOWN",
                "checkout_status": "UNKNOWN",
                "tasks": {task_id: {"status": "failed", "attempt": attempt_number}},
            }
        if receipt is None:
            unavailable_class: str | None = None
            for effect_class in ("payment", "inventory"):
                if effect_class in known_receipts:
                    continue
                try:
                    target_receipt = dependencies.gateway.get_target_receipt(
                        effect_class,
                        cast(str, current["idempotency_key"]),
                        case_id=state["case_id"],
                    )
                except GatewayUnavailable as exc:
                    unavailable_class = exc.error_class
                    continue
                if target_receipt is not None:
                    known_receipts[effect_class] = target_receipt
            if (
                authoritative_outcome == "not_committed"
                and not known_receipts
                and unavailable_class is None
            ):
                dependencies.events.emit(
                    "effect.replay_refused",
                    state,
                    {
                        "effect_class": "checkout",
                        "effect_state": "UNKNOWN",
                        "reason_class": "authoritative_not_committed",
                    },
                    node_id="reconcile_if_ambiguous",
                    effect_id=effect_id,
                    failure_plane="checkout",
                    error_class="authoritative_not_committed",
                )
                dependencies.events.emit(
                    "task.failed",
                    state,
                    {"status": "failed", "disposition": "stop"},
                    node_id="reconcile_if_ambiguous",
                    task_id=task_id,
                    attempt_id=attempt_id,
                    effect_id=effect_id,
                    failure_plane="checkout",
                    error_class="authoritative_not_committed",
                )
                return {
                    "phase": "TERMINAL",
                    "outcome": "FAILED",
                    "checkout_status": "FAILED",
                    "pending_effects": remove_pending_effects(effect_id),
                    "tasks": {
                        task_id: {"status": "failed", "attempt": attempt_number}
                    },
                    "failure": {
                        "plane": "checkout",
                        "error_class": "authoritative_not_committed",
                        "retryable": False,
                        "disposition": "stop",
                    },
                }
            dependencies.events.emit(
                "effect.replay_refused",
                state,
                {
                    "effect_class": "checkout",
                    "effect_state": "UNKNOWN",
                    "reason_class": "authoritative_not_found",
                },
                node_id="reconcile_if_ambiguous",
                effect_id=effect_id,
                failure_plane="graph-control",
                error_class=(unavailable_class or "automatic_replay_forbidden"),
            )
            dependencies.events.emit(
                "task.failed",
                state,
                {"status": "failed", "disposition": "stop"},
                node_id="reconcile_if_ambiguous",
                task_id=task_id,
                attempt_id=attempt_id,
                effect_id=effect_id,
                failure_plane="graph-control",
                error_class=(unavailable_class or "automatic_replay_forbidden"),
            )
            return {
                "phase": "TERMINAL",
                "outcome": "UNKNOWN",
                "checkout_status": "UNKNOWN",
                "tasks": {task_id: {"status": "failed", "attempt": attempt_number}},
                "receipts": _known_target_receipt_updates(state, known_receipts),
            }
        reconciled = dependencies.ledger.reconcile(
            effect_id,
            receipt,
            attempt_id=cast(str, current["attempt_id"]),
            replay_id=replay_id,
        )
        dependencies.events.emit(
            "effect.reconciled",
            state,
            {
                "effect_class": "checkout",
                "effect_state": "RECONCILED",
                "authoritative_result_id": receipt["authoritative_result_id"],
            },
            node_id="reconcile_if_ambiguous",
            task_id=cast(str, current["task_id"]),
            attempt_id=cast(str, current["attempt_id"]),
            effect_id=effect_id,
        )
        dependencies.events.emit(
            "task.completed",
            state,
            {"status": "completed"},
            node_id="reconcile_if_ambiguous",
            task_id=task_id,
            attempt_id=attempt_id,
            effect_id=effect_id,
        )
        return {
            "receipts": _receipt_updates(state, effect_id, cast(Mapping[str, object], reconciled["receipt"])),
            "pending_effects": remove_pending_effects(effect_id),
            "checkout_status": "COMPLETE",
            "phase": "FINALIZING",
            "outcome": None,
            "tasks": {task_id: {"status": "completed", "attempt": attempt_number}},
        }

    def terminal(state: GraphState) -> GraphState:
        effect_id = _checkout_effect_id(state)
        outcome = state.get("outcome")
        if outcome is None:
            checkout_receipt = state.get("receipts", {}).get(effect_id)
            if (
                checkout_receipt is not None
                and checkout_receipt.get("completion_class") == "COMPLETE"
                and isinstance(checkout_receipt.get("authoritative_result_id"), str)
                and isinstance(checkout_receipt.get("payment_receipt"), Mapping)
                and isinstance(checkout_receipt.get("inventory_receipt"), Mapping)
            ):
                outcome = "SUCCEEDED"
            else:
                outcome = "INCONCLUSIVE"
        if state.get("pending_effects"):
            outcome = "UNKNOWN"
        checkout_status = state.get("checkout_status", "NOT_STARTED")
        if outcome == "SUCCEEDED":
            checkout_status = "COMPLETE"
        elif outcome == "UNKNOWN":
            checkout_status = "UNKNOWN"
        elapsed_ms = dependencies.observed_wall_time_ms()
        wall_counter = state["budgets"]["wall_time_ms"]
        remaining = wall_counter["limit"] - wall_counter["consumed"]
        newly_consumed = max(0, elapsed_ms - wall_counter["consumed"])
        budgets = consume_budget(
            state["budgets"],
            "wall_time_ms",
            min(newly_consumed, remaining),
        )
        prior_budget_failure = (
            isinstance(state.get("failure"), Mapping)
            and state["failure"].get("error_class") == "budget_exhausted"
        )
        wall_event = (
            "budget.exhausted"
            if newly_consumed > remaining and not prior_budget_failure
            else "budget.observed"
        )
        dependencies.events.emit(
            wall_event,
            state,
            {
                "kind": "wall_time_ms",
                "limit": budgets["wall_time_ms"]["limit"],
                "consumed": budgets["wall_time_ms"]["consumed"],
                "remaining": (
                    budgets["wall_time_ms"]["limit"]
                    - budgets["wall_time_ms"]["consumed"]
                ),
            },
            node_id="terminal",
        )
        failure = state.get("failure")
        if wall_event == "budget.exhausted" and outcome == "SUCCEEDED":
            outcome = "FAILED"
            failure = {
                "plane": "graph-control",
                "error_class": "budget_exhausted",
                "retryable": False,
                "disposition": "effect-completed-budget-exceeded",
            }
        return {
            "phase": "TERMINAL",
            "outcome": outcome,
            "checkout_status": checkout_status,
            "budgets": budgets,
            "failure": failure,
        }

    builder = StateGraph(GraphState)
    builder.add_node("admit_run", admit_run)
    builder.add_node("readiness", readiness)
    builder.add_node("join_readiness", join_readiness)
    builder.add_node("fixture_plan", fixture_plan)
    builder.add_node("request_approval", request_approval)
    # Deliberately no retry_policy: durable effect safety lives in the target and ledger.
    builder.add_node("checkout_effect", checkout_effect)
    builder.add_node("reconcile_if_ambiguous", reconcile_if_ambiguous)
    builder.add_node("reconcile_after_snapshot", reconcile_if_ambiguous)
    builder.add_node("terminal", terminal)
    builder.add_edge(START, "admit_run")
    builder.add_conditional_edges(
        "admit_run",
        fanout_or_terminal,
        ["readiness", "terminal"],
    )
    builder.add_edge("readiness", "join_readiness")
    builder.add_conditional_edges(
        "join_readiness",
        after_readiness,
        ["fixture_plan", "terminal"],
    )
    builder.add_conditional_edges(
        "fixture_plan",
        approval_route,
        ["request_approval", "terminal"],
    )
    builder.add_conditional_edges(
        "request_approval",
        after_approval,
        ["checkout_effect", "terminal"],
    )
    builder.add_conditional_edges(
        "checkout_effect",
        after_checkout,
        ["reconcile_if_ambiguous", "reconcile_after_snapshot"],
    )
    builder.add_edge("reconcile_if_ambiguous", "terminal")
    builder.add_edge("reconcile_after_snapshot", "terminal")
    builder.add_edge("terminal", END)
    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["reconcile_after_snapshot"],
    )
