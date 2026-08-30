from __future__ import annotations

from copy import deepcopy

from runner.models import Budgets, CancellationState


class BudgetExhausted(RuntimeError):
    def __init__(
        self,
        kind: str,
        *,
        limit: int,
        consumed: int,
        requested: int,
    ) -> None:
        super().__init__(f"budget exhausted: {kind}")
        self.kind = kind
        self.limit = limit
        self.consumed = consumed
        self.requested = requested


def consume_budget(budgets: Budgets, kind: str, amount: int) -> Budgets:
    if kind not in budgets:
        raise ValueError(f"unknown budget kind: {kind}")
    if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
        raise ValueError("budget amount must be a non-negative integer")

    counter = budgets[kind]  # type: ignore[literal-required]
    proposed = counter["consumed"] + amount
    if proposed > counter["limit"]:
        raise BudgetExhausted(
            kind,
            limit=counter["limit"],
            consumed=counter["consumed"],
            requested=amount,
        )
    updated = deepcopy(budgets)
    updated[kind]["consumed"] = proposed  # type: ignore[literal-required]
    return updated


class CancellationError(RuntimeError):
    pass


_CANCELLATION_TRANSITIONS = {
    "NONE": {"REQUESTED"},
    "REQUESTED": {"PROPAGATED"},
    "PROPAGATED": {"ACKNOWLEDGED", "UNCONFIRMED"},
    "ACKNOWLEDGED": set(),
    "UNCONFIRMED": set(),
}


def transition_cancellation(
    cancellation: CancellationState,
    next_state: str,
    *,
    acknowledgement_ms: int | None = None,
) -> CancellationState:
    current = cancellation["state"]
    if next_state not in _CANCELLATION_TRANSITIONS[current]:
        raise CancellationError(f"invalid cancellation transition {current} -> {next_state}")
    if next_state == "ACKNOWLEDGED":
        if (
            not isinstance(acknowledgement_ms, int)
            or isinstance(acknowledgement_ms, bool)
            or acknowledgement_ms < 0
        ):
            raise CancellationError("ACKNOWLEDGED requires non-negative acknowledgement_ms")
    elif acknowledgement_ms is not None:
        raise CancellationError(f"{next_state} cannot carry acknowledgement_ms")
    if current == "NONE" and not cancellation.get("request_id"):
        raise CancellationError("REQUESTED requires a request_id")

    updated = deepcopy(cancellation)
    updated["state"] = next_state  # type: ignore[typeddict-item]
    updated["acknowledgement_ms"] = acknowledgement_ms
    return updated
