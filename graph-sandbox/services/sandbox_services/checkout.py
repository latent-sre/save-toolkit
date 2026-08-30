"""Synthetic checkout coordinator with durable target-owned receipt identities."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import os
import threading
from typing import Annotated, Any, Literal

import httpx
from fastapi import FastAPI, Header, Query
from pydantic import Field, ValidationError

from sandbox_services.common import (
    IDENTITY_PATTERN,
    CheckoutRecordStore,
    IdempotencyConflict,
    ServiceConfig,
    StrictModel,
    SyntheticItem,
    TargetReceipt,
    canonical_digest,
    case_error,
    derive_id,
    error_response,
    install_boundary_controls,
    service_port,
)


CONTRACT_VERSION = "checkout-payments-timeout-drill/v1"

IdempotencyHeader = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=128, pattern=IDENTITY_PATTERN),
]
RequestIdHeader = Annotated[
    str,
    Header(alias="X-Request-ID", min_length=1, max_length=128, pattern=IDENTITY_PATTERN),
]
SandboxCaseHeader = Annotated[
    str,
    Header(alias="X-Sandbox-Case", min_length=1, max_length=128, pattern=IDENTITY_PATTERN),
]
ReceiptKeyQuery = Annotated[
    str,
    Query(alias="idempotency_key", min_length=1, max_length=128, pattern=IDENTITY_PATTERN),
]


class CheckoutRequest(StrictModel):
    order_id: str = Field(min_length=1, max_length=128, pattern=IDENTITY_PATTERN)
    amount_cents: int = Field(ge=1, le=10_000_000)
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    items: list[SyntheticItem] = Field(min_length=1, max_length=16)


class LiveResponse(StrictModel):
    status: Literal["ok"] = "ok"
    service: Literal["checkout"] = "checkout"


class HealthResponse(StrictModel):
    status: Literal["ready", "unavailable"]
    service: Literal["checkout"] = "checkout"


class CompletedCheckout(StrictModel):
    authoritative_result_id: str = Field(pattern=IDENTITY_PATTERN)
    order_id: str = Field(pattern=IDENTITY_PATTERN)
    completion_class: Literal["COMPLETE"] = "COMPLETE"
    payment_receipt: TargetReceipt
    inventory_receipt: TargetReceipt
    replayed: bool


class TargetFailure(Exception):
    def __init__(self, *, code: str, outcome: Literal["not_committed", "unknown"]) -> None:
        super().__init__(code)
        self.code = code
        self.outcome = outcome


def _dependency_timeout() -> float:
    raw = os.environ.get("DEPENDENCY_TIMEOUT_SECONDS", "2")
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError("DEPENDENCY_TIMEOUT_SECONDS must be numeric") from exc
    if not 0.01 <= value <= 5.0:
        raise RuntimeError("DEPENDENCY_TIMEOUT_SECONDS must be between 0.01 and 5.0")
    return value


async def _dispatch(
    client: httpx.AsyncClient,
    *,
    path: str,
    payload: dict[str, Any],
    idempotency_key: str,
    request_id: str,
    sandbox_case: str,
    expected_effect: Literal["payment", "inventory"],
) -> TargetReceipt:
    headers = {
        "Idempotency-Key": idempotency_key,
        "X-Request-ID": request_id,
        "X-Sandbox-Case": sandbox_case,
    }
    try:
        response = await client.post(path, json=payload, headers=headers)
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise TargetFailure(
            code=f"{expected_effect}_transport_failure", outcome="unknown"
        ) from exc

    if response.status_code == 503:
        raise TargetFailure(code=f"{expected_effect}_unavailable", outcome="not_committed")
    if response.status_code >= 400:
        raise TargetFailure(code=f"{expected_effect}_unresolved", outcome="unknown")
    try:
        receipt = TargetReceipt.model_validate(response.json())
    except (ValueError, ValidationError) as exc:
        raise TargetFailure(code=f"{expected_effect}_invalid_receipt", outcome="unknown") from exc
    if receipt.effect_class != expected_effect or receipt.idempotency_key != idempotency_key:
        raise TargetFailure(code=f"{expected_effect}_conflicting_receipt", outcome="unknown")
    return receipt


def _failure_body(
    failure: TargetFailure,
    known_receipts: dict[str, TargetReceipt],
) -> dict[str, Any]:
    outcome: Literal["not_committed", "partial", "unknown"] = failure.outcome
    if failure.outcome == "not_committed" and known_receipts:
        outcome = "partial"
    return {
        "code": failure.code,
        "outcome": outcome,
        "known_receipts": {
            name: receipt.model_dump(mode="json")
            for name, receipt in sorted(known_receipts.items())
        },
    }


def _failure_response(body: dict[str, Any]):
    status = 504 if body["outcome"] == "unknown" else 502
    return error_response(
        status,
        body["code"],
        outcome=body["outcome"],
        known_receipts=body["known_receipts"],
    )


def create_app(
    *,
    config: ServiceConfig | None = None,
    payments_client: httpx.AsyncClient | None = None,
    inventory_client: httpx.AsyncClient | None = None,
    store: CheckoutRecordStore | None = None,
) -> FastAPI:
    selected = config or ServiceConfig.from_environment("checkout")
    if selected.service != "checkout":
        raise ValueError("checkout app requires checkout configuration")
    payments_url = os.environ.get("PAYMENTS_URL", "http://payments:8081")
    inventory_url = os.environ.get("INVENTORY_URL", "http://inventory:8082")
    timeout_seconds = _dependency_timeout()
    checkout_store = store or CheckoutRecordStore(selected.data_db)
    locks_guard = threading.Lock()
    request_locks: dict[str, asyncio.Lock] = {}
    owned_clients: list[httpx.AsyncClient] = []

    def request_lock(idempotency_key: str) -> asyncio.Lock:
        with locks_guard:
            return request_locks.setdefault(idempotency_key, asyncio.Lock())

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if payments_client is None:
            app.state.payments = httpx.AsyncClient(
                base_url=payments_url,
                timeout=httpx.Timeout(timeout_seconds),
            )
            owned_clients.append(app.state.payments)
        else:
            app.state.payments = payments_client
        if inventory_client is None:
            app.state.inventory = httpx.AsyncClient(
                base_url=inventory_url,
                timeout=httpx.Timeout(timeout_seconds),
            )
            owned_clients.append(app.state.inventory)
        else:
            app.state.inventory = inventory_client
        try:
            yield
        finally:
            for client in owned_clients:
                await client.aclose()

    app = FastAPI(title="graph-sandbox-checkout", version="2", lifespan=lifespan)
    install_boundary_controls(app)
    app.state.records = checkout_store

    @app.get("/livez", response_model=LiveResponse)
    async def livez() -> LiveResponse:
        return LiveResponse()

    @app.get("/healthz", response_model=HealthResponse)
    async def healthz(sandbox_case: SandboxCaseHeader) -> Any:
        invalid_case = case_error(sandbox_case, selected)
        if invalid_case is not None:
            return invalid_case
        response = HealthResponse(status=selected.readiness_fixture)
        if selected.readiness_fixture == "unavailable":
            return error_response(503, "readiness_unavailable", service="checkout")
        return response

    @app.post("/checkout", response_model=CompletedCheckout)
    async def checkout(
        request: CheckoutRequest,
        idempotency_key: IdempotencyHeader,
        request_id: RequestIdHeader,
        sandbox_case: SandboxCaseHeader,
    ) -> Any:
        invalid_case = case_error(sandbox_case, selected)
        if invalid_case is not None:
            return invalid_case
        request_digest = canonical_digest(request)

        async with request_lock(idempotency_key):
            try:
                recorded = checkout_store.get(idempotency_key, request_digest)
            except IdempotencyConflict:
                return error_response(409, "idempotency_conflict")
            if recorded is not None:
                if recorded.get("completion_class") == "COMPLETE":
                    recorded["replayed"] = True
                    return recorded
                return _failure_response(recorded)

            payment_key = derive_id(CONTRACT_VERSION, idempotency_key, "payment")
            inventory_key = derive_id(CONTRACT_VERSION, idempotency_key, "inventory")
            known_receipts: dict[str, TargetReceipt] = {}
            try:
                payment = await _dispatch(
                    app.state.payments,
                    path="/v1/authorizations",
                    payload={
                        "order_id": request.order_id,
                        "amount_cents": request.amount_cents,
                        "currency": request.currency,
                    },
                    idempotency_key=payment_key,
                    request_id=request_id,
                    sandbox_case=sandbox_case,
                    expected_effect="payment",
                )
                known_receipts["payment"] = payment
                inventory = await _dispatch(
                    app.state.inventory,
                    path="/v1/reservations",
                    payload={
                        "order_id": request.order_id,
                        "items": [item.model_dump(mode="json") for item in request.items],
                    },
                    idempotency_key=inventory_key,
                    request_id=request_id,
                    sandbox_case=sandbox_case,
                    expected_effect="inventory",
                )
                known_receipts["inventory"] = inventory
            except TargetFailure as failure:
                body = _failure_body(failure, known_receipts)
                recorded_failure = checkout_store.put(idempotency_key, request_digest, body)
                return _failure_response(recorded_failure)

            completed = CompletedCheckout(
                authoritative_result_id=derive_id("checkout", idempotency_key, request_digest),
                order_id=request.order_id,
                payment_receipt=payment,
                inventory_receipt=inventory,
                replayed=False,
            )
            recorded_success = checkout_store.put(
                idempotency_key,
                request_digest,
                completed.model_dump(mode="json"),
            )
            return recorded_success

    @app.get("/checkout/receipt")
    async def receipt(idempotency_key: ReceiptKeyQuery, sandbox_case: SandboxCaseHeader) -> Any:
        invalid_case = case_error(sandbox_case, selected)
        if invalid_case is not None:
            return invalid_case
        recorded = checkout_store.get(idempotency_key)
        if recorded is None:
            return error_response(404, "not_found")
        return recorded

    return app


def main() -> None:
    import uvicorn

    uvicorn.run(create_app(), host="0.0.0.0", port=service_port(8080), access_log=False)


if __name__ == "__main__":
    main()
