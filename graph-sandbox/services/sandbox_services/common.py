"""Closed service configuration, bounded models, and durable SQLite receipt stores."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from typing import Any, Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field


MAX_BODY_BYTES = 16 * 1024
IDENTITY_PATTERN = r"^[a-z0-9][a-z0-9._-]{0,127}$"
IDENTITY_RE = re.compile(IDENTITY_PATTERN)
RECEIPT_VERSION = "synthetic-receipt/v1"
CASE_IDS = frozenset(
    {
        "mission-healthy-001",
        "checkout-readiness-failure-001",
        "payments-latency-001",
        "payments-http-error-001",
        "payments-ambiguous-after-commit-001",
        "inventory-http-error-after-payment-001",
        "duplicate-effect-001",
    }
)
SERVICE_EFFECTS: dict[str, frozenset[str]] = {
    "checkout": frozenset({"success"}),
    "payments": frozenset(
        {"success", "latency", "http_error", "ambiguous_after_commit", "duplicate"}
    ),
    "inventory": frozenset({"success", "http_error", "duplicate"}),
}


class StrictModel(BaseModel):
    """Reject accidental contract expansion at every synthetic boundary."""

    model_config = ConfigDict(extra="forbid", strict=True)


class SyntheticItem(StrictModel):
    sku: str = Field(min_length=1, max_length=128, pattern=IDENTITY_PATTERN)
    quantity: int = Field(ge=1, le=100)


class TargetReceipt(StrictModel):
    receipt_version: Literal["synthetic-receipt/v1"] = RECEIPT_VERSION
    effect_class: Literal["payment", "inventory"]
    receipt_id: str = Field(pattern=IDENTITY_PATTERN)
    idempotency_key: str = Field(pattern=IDENTITY_PATTERN)
    request_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal["committed"] = "committed"
    replayed: bool


@dataclass(frozen=True, slots=True)
class ServiceConfig:
    """One service's immutable projection of a checked-in sandbox case."""

    service: str
    sandbox_case_id: str
    readiness_fixture: Literal["ready", "unavailable"]
    effect_fixture: str
    data_db: Path

    @classmethod
    def from_environment(cls, service: str) -> ServiceConfig:
        missing = [
            name
            for name in ("SANDBOX_CASE_ID", "READINESS_FIXTURE", "EFFECT_FIXTURE", "DATA_DB")
            if name not in os.environ
        ]
        if missing:
            raise RuntimeError(f"missing required service environment: {', '.join(missing)}")
        try:
            return cls.from_values(
                service=service,
                sandbox_case_id=os.environ["SANDBOX_CASE_ID"],
                readiness_fixture=os.environ["READINESS_FIXTURE"],
                effect_fixture=os.environ["EFFECT_FIXTURE"],
                data_db=os.environ["DATA_DB"],
            )
        except ValueError as exc:
            raise RuntimeError(str(exc)) from exc

    @classmethod
    def from_values(
        cls,
        *,
        service: str,
        sandbox_case_id: str,
        readiness_fixture: str,
        effect_fixture: str,
        data_db: str,
    ) -> ServiceConfig:
        expected_path = f"/data/{service}.sqlite3"
        return cls._validated(
            service=service,
            sandbox_case_id=sandbox_case_id,
            readiness_fixture=readiness_fixture,
            effect_fixture=effect_fixture,
            data_db=data_db,
            expected_path=expected_path,
        )

    @classmethod
    def for_test(
        cls,
        service: str,
        sandbox_case_id: str,
        data_db: Path,
        *,
        readiness_fixture: str = "ready",
        effect_fixture: str = "success",
    ) -> ServiceConfig:
        """Build explicit container-test configuration without weakening runtime paths."""

        return cls._validated(
            service=service,
            sandbox_case_id=sandbox_case_id,
            readiness_fixture=readiness_fixture,
            effect_fixture=effect_fixture,
            data_db=str(data_db),
            expected_path=None,
        )

    @classmethod
    def _validated(
        cls,
        *,
        service: str,
        sandbox_case_id: str,
        readiness_fixture: str,
        effect_fixture: str,
        data_db: str,
        expected_path: str | None,
    ) -> ServiceConfig:
        if service not in SERVICE_EFFECTS:
            raise ValueError("service is not in the closed service allowlist")
        if not IDENTITY_RE.fullmatch(sandbox_case_id) or sandbox_case_id not in CASE_IDS:
            raise ValueError("SANDBOX_CASE_ID must name a closed graph-sandbox-case/v2 case")
        if readiness_fixture not in {"ready", "unavailable"}:
            raise ValueError("READINESS_FIXTURE must be ready or unavailable")
        if effect_fixture not in SERVICE_EFFECTS[service]:
            allowed = ", ".join(sorted(SERVICE_EFFECTS[service]))
            raise ValueError(f"EFFECT_FIXTURE for {service} must be one of: {allowed}")
        database = Path(data_db)
        if not database.is_absolute():
            raise ValueError("DATA_DB must be absolute")
        if expected_path is not None and database.as_posix() != expected_path:
            raise ValueError(f"DATA_DB for {service} must be {expected_path}")
        return cls(
            service=service,
            sandbox_case_id=sandbox_case_id,
            readiness_fixture=readiness_fixture,
            effect_fixture=effect_fixture,
            data_db=database,
        )


def canonical_digest(value: BaseModel | Mapping[str, Any]) -> str:
    """Return a stable body digest without retaining the raw request body."""

    if isinstance(value, BaseModel):
        payload = value.model_dump(mode="json")
    else:
        payload = dict(value)
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def derive_id(*parts: str) -> str:
    encoded = "\n".join(parts).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _closed_json(value: Mapping[str, Any]) -> str:
    return json.dumps(dict(value), ensure_ascii=True, separators=(",", ":"), sort_keys=True)


class IdempotencyConflict(Exception):
    """The same idempotency key was presented with a different body digest."""


class _SqliteStore:
    def __init__(self, db_path: Path) -> None:
        self._path = db_path
        if not self._path.is_absolute():
            raise ValueError("database path must be absolute")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, isolation_level=None, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def _initialize(self, statement: str) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(statement)
            except BaseException:
                connection.rollback()
                raise
            else:
                connection.commit()


class ReceiptStore(_SqliteStore):
    """Target-owned receipt store with durable atomic key/digest binding."""

    def __init__(self, db_path: Path) -> None:
        super().__init__(db_path)
        self._initialize(
            """
            CREATE TABLE IF NOT EXISTS target_receipts (
                idempotency_key TEXT PRIMARY KEY,
                request_digest TEXT NOT NULL,
                receipt_json TEXT NOT NULL
            )
            """
        )

    def commit(
        self,
        *,
        effect_class: Literal["payment", "inventory"],
        idempotency_key: str,
        request_digest: str,
    ) -> TargetReceipt:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = connection.execute(
                    "SELECT request_digest, receipt_json FROM target_receipts "
                    "WHERE idempotency_key = ?",
                    (idempotency_key,),
                ).fetchone()
                if row is not None:
                    if row["request_digest"] != request_digest:
                        raise IdempotencyConflict
                    receipt = TargetReceipt.model_validate_json(row["receipt_json"])
                    connection.commit()
                    return receipt.model_copy(update={"replayed": True})

                receipt = TargetReceipt(
                    effect_class=effect_class,
                    receipt_id=derive_id(effect_class, idempotency_key, request_digest),
                    idempotency_key=idempotency_key,
                    request_digest=request_digest,
                    replayed=False,
                )
                connection.execute(
                    "INSERT INTO target_receipts "
                    "(idempotency_key, request_digest, receipt_json) VALUES (?, ?, ?)",
                    (
                        idempotency_key,
                        request_digest,
                        _closed_json(receipt.model_dump(mode="json")),
                    ),
                )
                connection.commit()
                return receipt
            except BaseException:
                connection.rollback()
                raise

    def get(self, idempotency_key: str) -> TargetReceipt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT receipt_json FROM target_receipts WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
        if row is None:
            return None
        return TargetReceipt.model_validate_json(row["receipt_json"])


class CheckoutRecordStore(_SqliteStore):
    """Digest-bound durable authoritative or failure state owned by checkout."""

    def __init__(self, db_path: Path) -> None:
        super().__init__(db_path)
        self._initialize(
            """
            CREATE TABLE IF NOT EXISTS checkout_records (
                idempotency_key TEXT PRIMARY KEY,
                request_digest TEXT NOT NULL,
                record_class TEXT NOT NULL
                    CHECK(record_class IN ('completed', 'partial', 'unknown')),
                record_json TEXT NOT NULL
            )
            """
        )

    def get(self, idempotency_key: str, request_digest: str | None = None) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT request_digest, record_json FROM checkout_records "
                "WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
        if row is None:
            return None
        if request_digest is not None and row["request_digest"] != request_digest:
            raise IdempotencyConflict
        decoded = json.loads(row["record_json"])
        if not isinstance(decoded, dict):
            raise RuntimeError("checkout record is not a JSON object")
        return decoded

    def put(
        self,
        idempotency_key: str,
        request_digest: str,
        body: Mapping[str, Any],
    ) -> dict[str, Any]:
        record_class = self._record_class(body)
        encoded = _closed_json(body)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = connection.execute(
                    "SELECT request_digest, record_json FROM checkout_records "
                    "WHERE idempotency_key = ?",
                    (idempotency_key,),
                ).fetchone()
                if row is not None:
                    if row["request_digest"] != request_digest:
                        raise IdempotencyConflict
                    connection.commit()
                    decoded = json.loads(row["record_json"])
                    if not isinstance(decoded, dict):
                        raise RuntimeError("checkout record is not a JSON object")
                    return decoded
                connection.execute(
                    "INSERT INTO checkout_records "
                    "(idempotency_key, request_digest, record_class, record_json) "
                    "VALUES (?, ?, ?, ?)",
                    (idempotency_key, request_digest, record_class, encoded),
                )
                connection.commit()
                return dict(body)
            except BaseException:
                connection.rollback()
                raise

    @staticmethod
    def _record_class(body: Mapping[str, Any]) -> Literal["completed", "partial", "unknown"]:
        if body.get("completion_class") == "COMPLETE":
            return "completed"
        if body.get("outcome") == "unknown":
            return "unknown"
        if body.get("outcome") in {"partial", "not_committed"}:
            return "partial"
        raise ValueError("checkout record is not a closed terminal record")


class BodyLimitMiddleware:
    """Reject an oversized request before FastAPI parses or retains it."""

    def __init__(self, app: Any, limit_bytes: int = MAX_BODY_BYTES) -> None:
        self.app = app
        self.limit_bytes = limit_bytes

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        if scope.get("type") != "http" or scope.get("method") not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return

        messages: list[dict[str, Any]] = []
        size = 0
        more_body = True
        while more_body:
            message = await receive()
            messages.append(message)
            if message.get("type") == "http.disconnect":
                return
            size += len(message.get("body", b""))
            more_body = bool(message.get("more_body", False))
            if size > self.limit_bytes:
                response = JSONResponse(status_code=413, content={"code": "request_too_large"})
                await response(scope, receive, send)
                return

        message_index = 0

        async def replay_receive() -> dict[str, Any]:
            nonlocal message_index
            if message_index < len(messages):
                message = messages[message_index]
                message_index += 1
                return message
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay_receive, send)


def install_boundary_controls(app: FastAPI) -> None:
    app.add_middleware(BodyLimitMiddleware)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, _exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"code": "validation_error"})


def error_response(status_code: int, code: str, **fields: Any) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"code": code, **fields})


def service_port(expected: int) -> int:
    raw = os.environ.get("SERVICE_PORT", str(expected))
    try:
        configured = int(raw)
    except ValueError as exc:
        raise RuntimeError("SERVICE_PORT must be an integer") from exc
    if configured != expected:
        raise RuntimeError(f"SERVICE_PORT must be {expected}")
    return configured


def case_error(selected: str, configured: ServiceConfig) -> JSONResponse | None:
    if selected != configured.sandbox_case_id:
        return error_response(422, "invalid_sandbox_case")
    return None
