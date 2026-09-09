"""One RFC 9457 problem+json shape on a FastAPI app.

    from fastapi import FastAPI
    from problem_fastapi import install_problem_handlers, problem_responses

    def create_app() -> FastAPI:
        app = FastAPI(responses=problem_responses(400, 422, 500))
        install_problem_handlers(app)
        # Register routes/routers here; add their applicable errors (e.g. 401, 409, 429).
        return app

Choose applicable status codes at app, router, or operation scope using responses=.
Handlers alone do not update OpenAPI. Configure response metadata before registering routes;
retain project-specific response descriptions, headers, and schemas when combining dictionaries.
Use application/problem+json and the protocol-header allowlist below. Adapt request_id to the app's
correlation middleware; this starter echoes X-Request-ID supplied by a validating trusted ingress.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
# The Starlette base catches FastAPI's HTTPException (a subclass) *and* the framework's own
# 404/405 for an unknown route, which a fastapi.HTTPException handler alone would miss.
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_TYPE_BASE = "https://errors.example.internal"
PROBLEM_MEDIA_TYPE = "application/problem+json"

# Extend for the app's protocol contract, never stale representation or framing metadata.
_PROTOCOL_HEADERS = {
    "www-authenticate", "proxy-authenticate", "allow", "retry-after", "location",
    "cache-control", "expires", "pragma", "vary", "set-cookie",
    "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset",
}

_TITLES = {
    400: "Malformed request", 401: "Unauthenticated", 403: "Forbidden", 404: "Not found",
    409: "Conflict", 422: "Validation failed", 429: "Too many requests",
    500: "Internal server error", 503: "Dependency unavailable",
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
            "type": "string", "description": "Correlates this response with the request log line.",
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
    "required": ["type", "title", "status"],
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


def problem(
    status: int, title: str, detail: str, request: Request,
    *, headers: Mapping[str, str] | None = None, **extensions: Any,
) -> JSONResponse:
    """One problem+json response. Call it directly when translating an upstream failure:

        return problem(503, "Paging vendor unavailable", "Timed out after 3s.", request)
    """
    body: dict[str, Any] = {
        "type": f"{PROBLEM_TYPE_BASE}/{_slug(title)}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
    }
    request_id = request.headers.get("X-Request-ID")
    if request_id:
        body["request_id"] = request_id
    body.update(extensions)
    # Rebuild body metadata; append protocol fields so repeated cookies/challenges survive.
    response = JSONResponse(body, status_code=status, media_type=PROBLEM_MEDIA_TYPE)
    for key, value in (headers or {}).items():
        if key.lower() in _PROTOCOL_HEADERS:
            response.headers.append(key, value)
    return response


def install_problem_handlers(app: FastAPI) -> None:
    """Normalize HTTP/validation/unhandled exceptions; configure OpenAPI separately above."""

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
        # Never the exception text: it leaks internals to the caller. Log it instead.
        return problem(
            500, "Internal server error", "The request could not be completed.", request
        )
