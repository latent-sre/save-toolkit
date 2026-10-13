"""Reusable HTTP helpers for a FastAPI service; adapt only the pieces the app needs.

    app = house_app("Tools API", "1.0.0", loopback_only=True)

house_app gives every error one RFC 9457 shape carrying request_id (and errors[] for invalid
input), X-Request-ID on every response, lowerCamel operation IDs, one Problem component declared
as application/problem+json on every 4xx and 5xx response, a cross-site
write guard, and, for a service bound to loopback, a Host guard against DNS rebinding.
Register the app's own routes and native/corporate-SSO authentication and object authorization.
The separate auth.py bearer adapter and main.py resource example are optional.

Request IDs: no inbound header is trusted by default. Trust one only when every request passes an
ingress that overwrites it; on PCF, Gorouter overwrites X-Vcap-Request-Id, but container-to-
container traffic and TCP routes bypass Gorouter. Add RequestIdLogFilter to the app's log handlers
so every record carries the same id.

Unhandled errors are logged with the method, path, and each exception's type and code locations,
never its message, notes or locals, which can hold credentials. Starlette re-raises after the
handler, so the server still logs the raw exception: configure that logger's redaction, and keep
debug mode off in production.

For cross-origin browser clients, wrap the ENTIRE app returned here in CORSMiddleware with the
project's allowlist; app.add_middleware(CORSMiddleware) sits inside the error middleware and
cannot add CORS headers to a 500.
"""
from __future__ import annotations

import ipaddress
import logging
import re
import sys
from collections.abc import Mapping
from contextvars import ContextVar
from copy import deepcopy
from http import HTTPStatus
from traceback import walk_tb
from types import TracebackType
from typing import Any, Generic, TypeVar
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field
from starlette.datastructures import Headers, MutableHeaders

# The Starlette base catches FastAPI's HTTPException *and* the router's own 404 and 405.
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

PROBLEM_MEDIA_TYPE = "application/problem+json"
REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_SHAPE = re.compile(r"[A-Za-z0-9._:-]{1,128}")
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
logger = logging.getLogger(__name__)

# Protocol fields a problem keeps from the exception; representation and framing headers are
# rebuilt for the problem body. Extend for the app's own protocol contract.
_PROTOCOL_HEADERS = {
    "www-authenticate", "proxy-authenticate", "allow", "retry-after", "location",
    "cache-control", "expires", "pragma", "vary", "set-cookie", "ratelimit", "ratelimit-policy",
}


class FieldError(BaseModel):
    """One invalid input. It never echoes the submitted value, which may be a secret."""

    loc: list[str] = Field(description="Path to the invalid input, starting with body, query, path or header.")
    msg: str


class Problem(BaseModel):
    """The house error body: RFC 9457 plus request_id and, for invalid input, errors."""

    type: str = Field(description="Stable identifier of the error class; about:blank when the status says it all.")
    title: str
    status: int
    detail: str = Field("", json_schema_extra=lambda schema: schema.pop("default"))  # optional, as in Go
    request_id: str = Field(description="Equals the X-Request-ID response header and the server's log lines.")
    errors: list[FieldError] = Field(default_factory=list)


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """The house collection. Name each page with a subclass (class ThingPage(Page[Thing])) so the
    document says ThingPage, not Page_Thing_."""

    data: list[T]
    next_cursor: str | None = Field(description="Pass back as ?cursor= for the next page; null on the last page.")


class ProblemError(Exception):
    """A domain error the client can act on, raised from code that knows nothing of HTTP:

        raise ProblemError(409, "https://errors.example.internal/thing-locked", "Thing is locked",
                           "Another change to this thing is in progress.")
    """

    def __init__(self, status: int, type_uri: str, title: str, detail: str = "") -> None:
        super().__init__(detail or title)
        self.status, self.type_uri, self.title, self.detail = status, type_uri, title, detail


def problem(
    request: Request, status: int, detail: str = "", *, type_uri: str = "about:blank",
    title: str | None = None, headers: Mapping[str, str] | None = None, **extensions: Any,
) -> JSONResponse:
    """One problem+json response. A status-only error keeps about:blank and the status phrase."""
    body: dict[str, Any] = {"type": type_uri, "title": title or HTTPStatus(status).phrase, "status": status}
    if detail and detail != body["title"]:
        body["detail"] = detail
    body.update(extensions)
    request_id = getattr(request.state, "request_id", None) or str(uuid4())
    body["request_id"] = request_id
    response = JSONResponse(body, status_code=status, media_type=PROBLEM_MEDIA_TYPE)
    for key, value in (headers or {}).items():
        if key.lower() in _PROTOCOL_HEADERS:
            response.headers.append(key, value)  # append: repeated cookies and challenges survive
    response.headers.setdefault(REQUEST_ID_HEADER, request_id)  # 500s leave outside the middleware
    return response


def problems(*statuses: int) -> dict[int | str, dict[str, Any]]:
    """responses= metadata for a route's error statuses; house_app's document hook adds the body."""
    return {status: {"description": HTTPStatus(status).phrase} for status in statuses}


def operation_id(route: APIRoute) -> str:
    """lowerCamel from the handler name: list_things -> listThings. Generated clients use it."""
    first, *rest = route.name.split("_")
    return first + "".join(word.capitalize() for word in rest)


class RequestIdLogFilter(logging.Filter):
    """Stamp record.request_id on every log record; add it to the app's log handlers."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = request_id_var.get()
        return True


class RequestIdMiddleware:
    """Pure ASGI, so streamed and SSE responses pass through unbuffered."""

    def __init__(self, app: ASGIApp, *, trusted_request_id_header: str | None = None) -> None:
        self.app = app
        self.trusted_request_id_header = trusted_request_id_header

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        ingress = Headers(scope=scope).get(self.trusted_request_id_header or "", "")
        request_id = ingress if ingress and _REQUEST_ID_SHAPE.fullmatch(ingress) else str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        token = request_id_var.set(request_id)

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            request_id_var.reset(token)


def _origin(url: str) -> tuple[str, str, int | None] | None:
    """(scheme, lowercase host, effective port), or None for an origin that cannot be parsed."""
    try:
        parts = urlsplit(url)
        port = parts.port or {"http": 80, "https": 443}.get(parts.scheme.lower())
    except ValueError:
        return None
    if not parts.hostname:
        return None
    return parts.scheme.lower(), parts.hostname.lower(), port


class CrossSiteWriteGuard:
    """Refuse browser writes from another origin (Sec-Fetch-Site, else Origin against Host).
    Reads and clients that send neither header, such as scripts, pass."""

    SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

    def __init__(self, app: ASGIApp, *, trusted_origins: frozenset[str] = frozenset()) -> None:
        self.app = app
        self.trusted_origins = trusted_origins

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] not in self.SAFE_METHODS:
            headers = Headers(scope=scope)
            site, origin = headers.get("sec-fetch-site"), headers.get("origin")
            if origin in self.trusted_origins:
                cross = False
            elif site is not None:
                cross = site not in ("same-origin", "none")
            else:
                cross = origin is not None and _origin(origin) != _origin(
                    f"{scope.get('scheme', 'http')}://{headers.get('host', '')}"
                )
            if cross:
                response = problem(Request(scope), 403, "Cross-origin requests are not accepted.")
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


def is_loopback(host: str) -> bool:
    host = host.strip("[]").lower()
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class LoopbackHostGuard:
    """For a service bound to loopback: refuse a Host that is not a loopback name. A web page that
    rebinds its own DNS name to 127.0.0.1 still sends its own name as Host."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            host = Headers(scope=scope).get("host", "")
            name = host.rsplit(":", 1)[0] if not host.endswith("]") else host
            if not is_loopback(name):
                response = problem(Request(scope), 421, "This service answers only on its loopback address.")
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


def _locations(tb: TracebackType | None) -> list[object]:
    """Code locations, outermost first; a repeated frame (recursion) collapses to a count."""
    locations: list[object] = []
    previous, repeats = None, 0
    for frame, line in walk_tb(tb):
        location = (frame.f_code.co_filename, line, frame.f_code.co_name)
        if location == previous:
            repeats += 1
            continue
        if repeats:
            locations.append(f"previous repeated {repeats} times")
            repeats = 0
        locations.append(location)
        previous = location
    if repeats:
        locations.append(f"previous repeated {repeats} times")
    return locations


def _exception_summary(exc: BaseException) -> list[tuple[str, list[object]]]:
    """Type and locations of exc, its group members, and its cause/context chain; no values."""
    summary: list[tuple[str, list[object]]] = []
    pending, seen = [exc], set()
    while pending:
        current = pending.pop(0)
        if id(current) in seen:
            continue
        seen.add(id(current))
        summary.append((type(current).__name__, _locations(current.__traceback__)))
        members = getattr(current, "exceptions", None)  # an exception group
        if isinstance(members, (tuple, list)):
            pending.extend(m for m in members if isinstance(m, BaseException))
        if current.__cause__ is not None:
            pending.append(current.__cause__)
        elif current.__context__ is not None and not current.__suppress_context__:
            pending.append(current.__context__)
    return summary


def _error_with_request_id(request_id: str, msg: str, *args: object) -> None:
    """logger.error with an explicit request_id, set after the record exists: extra= raises
    KeyError when the project's LogRecord factory already sets request_id."""
    if logger.isEnabledFor(logging.ERROR):
        caller = sys._getframe(1)
        record = logger.makeRecord(
            logger.name, logging.ERROR, caller.f_code.co_filename, caller.f_lineno, msg, args,
            None, caller.f_code.co_name,
        )
        record.request_id = request_id
        logger.handle(record)


def _install_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def _http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return problem(request, exc.status_code, str(exc.detail), headers=exc.headers)

    @app.exception_handler(ProblemError)
    async def _domain_problem(request: Request, exc: ProblemError) -> JSONResponse:
        return problem(request, exc.status, exc.detail, type_uri=exc.type_uri, title=exc.title)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        if any(err.get("type") == "json_invalid" for err in exc.errors()):
            return problem(request, 400, "The request body is not valid JSON.")
        errors = [
            {"loc": [str(part) for part in err.get("loc", ())], "msg": err.get("msg", "")}
            for err in exc.errors()
        ]
        return problem(request, 422, "The request failed validation.", errors=errors)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        _error_with_request_id(
            getattr(request.state, "request_id", "-"), "Unhandled %s on %s %s; exceptions=%s",
            type(exc).__name__, request.method, request.url.path, _exception_summary(exc),
        )
        return problem(request, 500, "The request could not be completed.")


def _problem_schemas() -> dict[str, Any]:
    schema = Problem.model_json_schema(ref_template="#/components/schemas/{model}")
    return {**schema.pop("$defs", {}), "Problem": schema}


def _house_document(app: FastAPI) -> None:
    """Declare the Problem body on every 4xx and 5xx response, and a 500 on every operation."""
    generate = app.openapi

    def openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        document = generate()
        schemas = document.setdefault("components", {}).setdefault("schemas", {})
        for unused in ("HTTPValidationError", "ValidationError"):
            schemas.pop(unused, None)
        schemas.update(_problem_schemas())
        body = {PROBLEM_MEDIA_TYPE: {"schema": {"$ref": "#/components/schemas/Problem"}}}
        for path_item in document.get("paths", {}).values():
            for operation in path_item.values():
                responses = operation.setdefault("responses", {})
                responses.setdefault("500", {"description": HTTPStatus(500).phrase})
                if "requestBody" in operation:  # unparseable JSON answers 400
                    responses.setdefault("400", {"description": HTTPStatus(400).phrase})
                if operation.get("security"):  # authentication can reject a caller or be unavailable
                    for status in (401, 503):
                        responses.setdefault(str(status), {"description": HTTPStatus(status).phrase})
                for status, response in responses.items():
                    if status.isdigit() and int(status) >= 400:
                        response["content"] = deepcopy(body)
        app.openapi_schema = document
        return document

    app.openapi = openapi  # type: ignore[method-assign]


def house_app(
    title: str, version: str, *, loopback_only: bool,
    trusted_request_id_header: str | None = None, trusted_origins: frozenset[str] = frozenset(),
    **fastapi_options: Any,
) -> FastAPI:
    """A FastAPI app on the house contract. Register routes after it; pass lifespan= and other
    FastAPI options through fastapi_options."""
    app = FastAPI(
        title=title, version=version, generate_unique_id_function=operation_id,
        separate_input_output_schemas=False, **fastapi_options,
    )
    _install_handlers(app)
    _house_document(app)
    app.add_middleware(CrossSiteWriteGuard, trusted_origins=trusted_origins)
    if loopback_only:
        app.add_middleware(LoopbackHostGuard)
    app.add_middleware(RequestIdMiddleware, trusted_request_id_header=trusted_request_id_header)
    return app
