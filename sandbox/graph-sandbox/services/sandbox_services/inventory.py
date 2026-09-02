"""Deterministic synthetic inventory reservation service."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import FastAPI, Header, Query
from pydantic import Field

from sandbox_services.common import (
    IDENTITY_PATTERN,
    IdempotencyConflict,
    ReceiptStore,
    ServiceConfig,
    StrictModel,
    SyntheticItem,
    TargetReceipt,
    canonical_digest,
    case_error,
    error_response,
    install_boundary_controls,
    service_port,
)


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


class ReservationRequest(StrictModel):
    order_id: str = Field(min_length=1, max_length=128, pattern=IDENTITY_PATTERN)
    items: list[SyntheticItem] = Field(min_length=1, max_length=16)


class LiveResponse(StrictModel):
    status: Literal["ok"] = "ok"
    service: Literal["inventory"] = "inventory"


class HealthResponse(StrictModel):
    status: Literal["ready", "unavailable"]
    service: Literal["inventory"] = "inventory"


def create_app(
    *,
    config: ServiceConfig | None = None,
    store: ReceiptStore | None = None,
) -> FastAPI:
    selected = config or ServiceConfig.from_environment("inventory")
    if selected.service != "inventory":
        raise ValueError("inventory app requires inventory configuration")
    receipt_store = store or ReceiptStore(selected.data_db)
    app = FastAPI(title="graph-sandbox-inventory", version="2")
    install_boundary_controls(app)
    app.state.receipts = receipt_store

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
            return error_response(503, "readiness_unavailable", service="inventory")
        return response

    @app.post("/v1/reservations", response_model=TargetReceipt)
    async def reserve(
        request: ReservationRequest,
        idempotency_key: IdempotencyHeader,
        _request_id: RequestIdHeader,
        sandbox_case: SandboxCaseHeader,
    ) -> Any:
        invalid_case = case_error(sandbox_case, selected)
        if invalid_case is not None:
            return invalid_case
        if selected.effect_fixture == "http_error":
            return error_response(503, "synthetic_http_error")

        request_digest = canonical_digest(request)
        try:
            receipt = receipt_store.commit(
                effect_class="inventory",
                idempotency_key=idempotency_key,
                request_digest=request_digest,
            )
            if selected.effect_fixture == "duplicate" and not receipt.replayed:
                receipt = receipt_store.commit(
                    effect_class="inventory",
                    idempotency_key=idempotency_key,
                    request_digest=request_digest,
                )
            return receipt
        except IdempotencyConflict:
            return error_response(409, "idempotency_conflict")

    @app.get("/v1/reservations/receipt", response_model=TargetReceipt)
    async def receipt(idempotency_key: ReceiptKeyQuery, sandbox_case: SandboxCaseHeader) -> Any:
        invalid_case = case_error(sandbox_case, selected)
        if invalid_case is not None:
            return invalid_case
        stored = receipt_store.get(idempotency_key)
        if stored is None:
            return error_response(404, "not_found")
        return stored

    return app


def main() -> None:
    import uvicorn

    uvicorn.run(create_app(), host="0.0.0.0", port=service_port(8082), access_log=False)


if __name__ == "__main__":
    main()
