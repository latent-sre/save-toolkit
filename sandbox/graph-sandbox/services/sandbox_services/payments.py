"""Deterministic synthetic payment authorization service."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any, Literal

from fastapi import FastAPI, Header, Query
from pydantic import Field
from starlette.responses import Response

from sandbox_services.common import (
    IDENTITY_PATTERN,
    IdempotencyConflict,
    ReceiptStore,
    ServiceConfig,
    StrictModel,
    TargetReceipt,
    canonical_digest,
    case_error,
    error_response,
    install_boundary_controls,
    service_port,
)


LATENCY_SECONDS = 2.25

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


class AuthorizationRequest(StrictModel):
    order_id: str = Field(min_length=1, max_length=128, pattern=IDENTITY_PATTERN)
    amount_cents: int = Field(ge=1, le=10_000_000)
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")


class LiveResponse(StrictModel):
    status: Literal["ok"] = "ok"
    service: Literal["payments"] = "payments"


class HealthResponse(StrictModel):
    status: Literal["ready", "unavailable"]
    service: Literal["payments"] = "payments"


class CommitResponseLost(Response):
    """Commit first, then force the server to close an incomplete response."""

    media_type = "application/json"

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", b"1"),
                ],
            }
        )
        raise RuntimeError("synthetic_response_lost_after_commit")


def create_app(
    *,
    config: ServiceConfig | None = None,
    store: ReceiptStore | None = None,
) -> FastAPI:
    selected = config or ServiceConfig.from_environment("payments")
    if selected.service != "payments":
        raise ValueError("payment app requires payment configuration")
    receipt_store = store or ReceiptStore(selected.data_db)
    app = FastAPI(title="graph-sandbox-payments", version="2")
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
            return error_response(503, "readiness_unavailable", service="payments")
        return response

    @app.post("/v1/authorizations", response_model=TargetReceipt)
    async def authorize(
        request: AuthorizationRequest,
        idempotency_key: IdempotencyHeader,
        _request_id: RequestIdHeader,
        sandbox_case: SandboxCaseHeader,
    ) -> Any:
        invalid_case = case_error(sandbox_case, selected)
        if invalid_case is not None:
            return invalid_case
        if selected.effect_fixture == "http_error":
            return error_response(503, "synthetic_http_error")
        if selected.effect_fixture == "latency":
            await asyncio.sleep(LATENCY_SECONDS)

        request_digest = canonical_digest(request)
        try:
            receipt = receipt_store.commit(
                effect_class="payment",
                idempotency_key=idempotency_key,
                request_digest=request_digest,
            )
            if selected.effect_fixture == "duplicate" and not receipt.replayed:
                receipt = receipt_store.commit(
                    effect_class="payment",
                    idempotency_key=idempotency_key,
                    request_digest=request_digest,
                )
        except IdempotencyConflict:
            return error_response(409, "idempotency_conflict")

        if selected.effect_fixture == "ambiguous_after_commit":
            return CommitResponseLost()
        return receipt

    @app.get("/v1/authorizations/receipt", response_model=TargetReceipt)
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

    uvicorn.run(create_app(), host="0.0.0.0", port=service_port(8081), access_log=False)


if __name__ == "__main__":
    main()
