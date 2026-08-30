from __future__ import annotations

from copy import deepcopy
from typing import Annotated, Literal, NotRequired, TypedDict, TypeVar


CONTRACT_VERSION = "checkout-payments-timeout-drill/v1"
SANDBOX_VERSION = "graph-sandbox/v1"
EVENT_VERSION = "graph-boundary-event/v2"
EVIDENCE_VERSION = "graph-evidence/v2"
STATE_SCHEMA_VERSION = "graph-state/v2"
CHECKPOINT_LINEAGE_VERSION = "graph-checkpoint-lineage/v2"

Phase = Literal[
    "ADMISSION",
    "PLANNING",
    "AWAITING_APPROVAL",
    "EXECUTING",
    "RECONCILING",
    "FINALIZING",
    "TERMINAL",
]
Outcome = Literal[
    "SUCCEEDED",
    "FAILED",
    "CANCELLED",
    "REJECTED",
    "INCONCLUSIVE",
    "UNKNOWN",
]


class CheckoutItem(TypedDict):
    sku: str
    quantity: int


class CheckoutInput(TypedDict):
    order_id: str
    amount_cents: int
    currency: str
    items: list[CheckoutItem]


class ApprovalState(TypedDict):
    request_id: str
    status: Literal["PENDING", "APPROVED", "REJECTED", "TIMED_OUT"]
    actor_class: str
    decision_time: str | None


class BudgetCounter(TypedDict):
    limit: int
    consumed: int


class Budgets(TypedDict):
    attempts: BudgetCounter
    wall_time_ms: BudgetCounter
    model_calls: BudgetCounter
    tokens: BudgetCounter
    spend_micro_usd: BudgetCounter


class CancellationState(TypedDict):
    state: Literal[
        "NONE",
        "REQUESTED",
        "PROPAGATED",
        "ACKNOWLEDGED",
        "UNCONFIRMED",
    ]
    request_id: str | None
    acknowledgement_ms: int | None


class FailureState(TypedDict):
    plane: str
    error_class: str
    retryable: bool
    disposition: str


class ReadinessResult(TypedDict):
    status: Literal["ok", "failed"]
    service: str
    error_class: NotRequired[str]


T = TypeVar("T")


def merge_unique_maps(left: dict[str, T], right: dict[str, T]) -> dict[str, T]:
    """Merge parallel results without allowing one identity to change meaning."""

    merged = deepcopy(left)
    for key, value in right.items():
        if key in merged and merged[key] != value:
            raise ValueError(f"conflicting reducer value for {key}")
        merged[key] = deepcopy(value)
    return merged


def merge_ordered_unique(left: list[T], right: list[T]) -> list[T]:
    """Merge parallel ordered values, accepting identical duplicates once."""

    merged = deepcopy(left)
    for value in right:
        if value not in merged:
            merged.append(deepcopy(value))
    return merged


class PendingEffectsUpdate(list[str]):
    """Reducer input that removes reconciled effects before adding new ones."""

    def __init__(self, additions: list[str], removals: list[str]) -> None:
        super().__init__(additions)
        self.removals = frozenset(removals)


def merge_pending_effects(left: list[str], right: list[str]) -> list[str]:
    removals = right.removals if isinstance(right, PendingEffectsUpdate) else frozenset()
    retained = [effect_id for effect_id in left if effect_id not in removals]
    return merge_ordered_unique(retained, list(right))


def remove_pending_effects(*effect_ids: str) -> PendingEffectsUpdate:
    return PendingEffectsUpdate([], list(effect_ids))


class GraphState(TypedDict, total=False):
    contract_version: Literal["checkout-payments-timeout-drill/v1"]
    state_schema: Literal["graph-state/v2"]
    run_id: str
    thread_id: str
    source_revision: str
    case_id: str
    case_digest: str
    replay_number: int
    phase: Phase
    outcome: Outcome | None
    checkout: CheckoutInput
    checkout_status: Literal["NOT_STARTED", "COMPLETE", "FAILED", "UNKNOWN"]
    approval: ApprovalState
    tasks: Annotated[dict[str, dict[str, object]], merge_unique_maps]
    receipts: Annotated[dict[str, dict[str, object]], merge_unique_maps]
    pending_effects: Annotated[list[str], merge_pending_effects]
    readiness: Annotated[dict[str, ReadinessResult], merge_unique_maps]
    readiness_target: str
    budgets: Budgets
    cancellation: CancellationState
    failure: FailureState | None


class ModelFixture(TypedDict):
    plan_class: Literal["checkout"]
    token_count: int


class ServiceFixture(TypedDict):
    readiness: Literal["ready", "unavailable"]
    effect: str


class ServiceFixtures(TypedDict):
    checkout: ServiceFixture
    payments: ServiceFixture
    inventory: ServiceFixture


class SandboxCase(TypedDict):
    case_version: Literal["graph-sandbox-case/v2"]
    case_id: str
    service_fixtures: ServiceFixtures
    checkout: CheckoutInput
    model_fixture: ModelFixture
    budgets: Budgets


def new_run_state(
    case: SandboxCase,
    *,
    run_id: str,
    source_revision: str,
    case_digest: str,
) -> GraphState:
    from runner.validation import validate_atomic_id, validate_sha256, validate_source_revision

    validate_atomic_id(run_id, "run_id")
    validate_source_revision(source_revision)
    validate_sha256(case_digest, "case_digest")

    return {
        "contract_version": CONTRACT_VERSION,
        "state_schema": STATE_SCHEMA_VERSION,
        "run_id": run_id,
        "thread_id": f"checkout-payments-timeout-drill-v1:{run_id}",
        "source_revision": source_revision,
        "case_id": case["case_id"],
        "case_digest": case_digest,
        "replay_number": 0,
        "phase": "ADMISSION",
        "outcome": None,
        "checkout": deepcopy(case["checkout"]),
        "checkout_status": "NOT_STARTED",
        "approval": {
            "request_id": f"approval-{run_id}",
            "status": "PENDING",
            "actor_class": "fixture-operator",
            "decision_time": None,
        },
        "tasks": {},
        "receipts": {},
        "pending_effects": [],
        "readiness": {},
        "budgets": deepcopy(case["budgets"]),
        "cancellation": {
            "state": "NONE",
            "request_id": None,
            "acknowledgement_ms": None,
        },
        "failure": None,
    }
