"""One RFC 9457 problem+json shape on a FastAPI app.

    from fastapi import FastAPI
    from starlette.middleware.cors import CORSMiddleware
    from starlette.types import ASGIApp
    from problem_fastapi import install_problem_handlers, problem_responses

    def create_app() -> ASGIApp:
        app = FastAPI(responses=problem_responses(400, 422, 500))
        install_problem_handlers(app)
        # Register routes/routers here; add their applicable errors (e.g. 401, 409, 429).
        return CORSMiddleware(
            app,
            allow_origins=["https://console.example.internal"],
            allow_methods=["GET", "POST"],
            allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
            expose_headers=[
                "X-Request-ID", "Retry-After", "Idempotent-Replayed",
                "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset",
            ],
        )

Choose applicable status codes at app, router, or operation scope using responses=.
Handlers alone do not update OpenAPI. Configure response metadata before registering routes;
retain project-specific response descriptions, headers, and schemas when combining dictionaries.
Use application/problem+json and the protocol-header allowlist below.
`type` is the contract; `title` is display text that may be reworded or localized, so the type
comes from a stable slug, never from a caller's title.
install_problem_handlers also adds RequestIdMiddleware. It uses an already selected, validated
request.state.request_id, else Gorouter's X-Vcap-Request-Id on PCF, else X-Request-ID from a
validating trusted ingress, else a generated uuid4. The same id reaches request state, problem
bodies, X-Request-ID response headers, and logs filtered by RequestIdLogFilter.
Choose one correlation owner. Middleware that only selects the project's id must run OUTSIDE
RequestIdMiddleware (add it after install_problem_handlers) and must not rewrite it downstream.
If the project already owns correlation end to end, use install_request_id=False. That owner must
validate its id against [A-Za-z0-9._:-]{1,128}, set request.state.request_id, bind request_id_var
with set()/reset(token) in try/finally, and set the X-Request-ID response header. Add
RequestIdLogFilter to the app's log handlers; exception logging preserves its explicit id.
For cross-origin clients, wrap the ENTIRE exported app with CORSMiddleware as above, using the
project's allowlist. The example permits the paired OpenAPI starter's bearer-authenticated GET and
JSON POST with Idempotency-Key, and exposes its correlation, replay, and rate-limit response headers
to browser code. Adapt methods and headers to the project's contract.
app.add_middleware(CORSMiddleware, ...) is inside ServerErrorMiddleware and
cannot add CORS headers to unhandled 500s. A service without cross-origin clients can return app.
"""
from __future__ import annotations

from collections.abc import Mapping
from contextvars import ContextVar
from copy import deepcopy
import logging
import re
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers, MutableHeaders
# The Starlette base catches FastAPI's HTTPException (a subclass) *and* the framework's own
# 404/405 for an unknown route, which a fastapi.HTTPException handler alone would miss.
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

PROBLEM_TYPE_BASE = "https://errors.example.internal"
PROBLEM_MEDIA_TYPE = "application/problem+json"
REQUEST_ID_HEADER = "X-Request-ID"
# Gorouter sets X-Vcap-Request-Id on every request, overwriting any client value; X-Request-ID
# counts only from a validating ingress. Both must match the bounded shape.
_REQUEST_ID_SOURCES = ("X-Vcap-Request-Id", REQUEST_ID_HEADER)
_REQUEST_ID_SHAPE = re.compile(r"[A-Za-z0-9._:-]{1,128}")
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
logger = logging.getLogger(__name__)

# Extend for the app's protocol contract, never stale representation or framing metadata.
_PROTOCOL_HEADERS = {
    "www-authenticate", "proxy-authenticate", "allow", "retry-after", "location",
    "cache-control", "expires", "pragma", "vary", "set-cookie",
    "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset",
}

# Default title per status. Its slug is that status's stable problem type, so rewording an entry
# here changes a contract URI; localize titles at the call site instead.
_TITLES = {
    400: "Malformed request", 401: "Unauthenticated", 403: "Forbidden", 404: "Not found",
    405: "Method not allowed", 406: "Not acceptable", 409: "Conflict",
    410: "Version retired",  # the house Versioning rule: dated Sunset, then 410
    413: "Content too large", 415: "Unsupported media type", 422: "Validation failed",
    429: "Too many requests", 500: "Internal server error", 503: "Dependency unavailable",
}

# Inline for a self-contained starter; keep aligned with openapi.starter.yaml's Problem schema.
_PROBLEM_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string", "format": "uri",
            "description": "Stable URI identifying the error class.",
        },
        "title": {"type": "string"},
        "status": {"type": "integer"},
        "detail": {"type": "string"},
        "instance": {"type": "string"},
        "request_id": {
            "type": "string", "minLength": 1,
            "description": "Correlates this response with the request log line.",
        },
        "errors": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "loc": {"type": "array", "items": {"type": "string"}},
                    "msg": {"type": "string"},
                },
                "required": ["loc", "msg"],
            },
        },
    },
    "required": ["type", "title", "status", "request_id"],
}


def problem_responses(*statuses: int) -> dict[int, dict[str, Any]]:
    """Fresh metadata for FastAPI/APIRouter/path-operation responses=; does not install handlers."""
    return {
        status: {
            "description": _TITLES.get(status, "Request failed"),
            "content": {PROBLEM_MEDIA_TYPE: {"schema": deepcopy(_PROBLEM_SCHEMA)}},
        }
        for status in statuses
    }


def _slug(title: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in title.lower()).strip("-")


class RequestIdLogFilter(logging.Filter):
    """Stamp record.request_id on every log record; add it to the app's log handlers."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = request_id_var.get()
        return True


class RequestIdMiddleware:
    """Pure ASGI, so streamed and SSE responses pass through unbuffered."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        state = scope.setdefault("state", {})
        candidates = [state.get("request_id"), *(headers.get(name, "") for name in _REQUEST_ID_SOURCES)]
        request_id = next(
            (v for v in candidates if isinstance(v, str) and _REQUEST_ID_SHAPE.fullmatch(v)),
            str(uuid4()),
        )
        state["request_id"] = request_id
        token = request_id_var.set(request_id)

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            request_id_var.reset(token)


def problem(
    status: int, title: str, detail: str, request: Request,
    *, headers: Mapping[str, str] | None = None, type_slug: str | None = None, **extensions: Any,
) -> JSONResponse:
    """One problem+json response. Call it directly when translating an upstream failure:

        return problem(
            503, "Paging vendor unavailable", "Timed out after 3s.", request,
            type_slug="paging-vendor-unavailable",
        )

    The type is PROBLEM_TYPE_BASE/type_slug, else the slug of the status's default title.
    """
    type_slug = type_slug or _slug(_TITLES.get(status, "Request failed"))
    body: dict[str, Any] = {
        "type": f"{PROBLEM_TYPE_BASE}/{type_slug}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
    }
    body.update(extensions)
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        body["request_id"] = request_id
    # Rebuild body metadata; append protocol fields so repeated cookies/challenges survive.
    response = JSONResponse(body, status_code=status, media_type=PROBLEM_MEDIA_TYPE)
    for key, value in (headers or {}).items():
        if key.lower() in _PROTOCOL_HEADERS:
            response.headers.append(key, value)
    if request_id:  # also on 500s, which ServerErrorMiddleware sends outside RequestIdMiddleware
        response.headers.setdefault(REQUEST_ID_HEADER, request_id)
    return response


def install_problem_handlers(app: FastAPI, *, install_request_id: bool = True) -> None:
    """Install handlers and, by default, correlation; see the integration contract above."""
    if install_request_id:
        app.add_middleware(RequestIdMiddleware)

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        title = _TITLES.get(exc.status_code, "Request failed")
        return problem(exc.status_code, title, str(exc.detail), request, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        if any(err.get("type") == "json_invalid" for err in exc.errors()):
            return problem(400, "Malformed request", "The request body is not valid JSON.", request)
        errors = [
            {"loc": [str(part) for part in err.get("loc", ())], "msg": err.get("msg", "")}
            for err in exc.errors()
        ]
        return problem(
            422, "Validation failed", "The request failed validation.", request, errors=errors
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Never the exception text: it leaks internals to the caller. Log it with the request id,
        # which RequestIdMiddleware has already reset in the context by the time this runs.
        request_id = getattr(request.state, "request_id", "-")
        logger.error(
            "Unhandled error on %s %s", request.method, request.url.path,
            exc_info=exc, extra={"request_id": request_id},
        )
        return problem(
            500, "Internal server error", "The request could not be completed.", request
        )
