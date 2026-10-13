"""Optional resource example: settings read and validated at startup,
a loopback default, a lifespan that owns shared resources, health outside the API contract, and a
resource with /v1 paths, bearer security, cursor pages whose oversized limit is lowered, and a 404
problem for a missing or unpermitted object. Adapt relevant patterns to the real app; Thing,
ThingStore and the bearer adapter are examples, not required scaffolding. Shared internal tools
use their native/corporate-SSO integration; select this adapter only when it accepts bearer tokens.

Run it with `python main.py`: it listens on all interfaces at $PORT when the platform sets PORT
(PCF, Cloud Run), and on 127.0.0.1:8000 otherwise, as load_settings decides.
"""
from __future__ import annotations

import os
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated

from auth import (
    Authenticated,
    Principal,
    TokenVerifier,
    authenticated,
    configure_bearer_auth,
)
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Path, Query, Request, Response
from house import Page, house_app, is_loopback, problem, problems
from pydantic import BaseModel

MAX_PAGE_SIZE = 200


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    trusted_request_id_header: str | None


def load_settings(environ: Mapping[str, str]) -> Settings:
    """Read once at startup; an invalid value stops the process. A platform that sets PORT routes
    to the instance from outside, so the service listens on all interfaces there; anywhere else it
    stays on loopback unless HOST says otherwise."""
    port = environ.get("PORT", "8000")
    if not port.isdigit() or not 0 < int(port) < 65536:
        raise ValueError(f"PORT {port!r} is not a TCP port")
    return Settings(
        host=environ.get("HOST") or ("0.0.0.0" if "PORT" in environ else "127.0.0.1"),
        port=int(port),
        trusted_request_id_header=environ.get("TRUSTED_REQUEST_ID_HEADER") or None,
    )


class Thing(BaseModel):
    id: str
    name: str
    team: str


class ThingPage(Page[Thing]):
    pass


def can_read(principal: Principal, thing: Thing) -> bool:
    """The object-level rule: a principal reads the things of the teams in its scopes."""
    return f"team:{thing.team}" in principal.scopes


class ThingStore:
    """Stands in for the datastore; the real one queries with an index on id."""

    def __init__(self, things: list[Thing] | None = None) -> None:
        self._things = sorted(things or [], key=lambda t: t.id)  # ordered by id, the page order

    async def ready(self) -> bool:
        return True  # with a database, a short ping

    async def after(self, principal: Principal, after_id: str, limit: int) -> list[Thing]:
        rows = (t for t in self._things if t.id > after_id and can_read(principal, t))
        return [row for _, row in zip(range(limit), rows, strict=False)]

    async def get(self, thing_id: str) -> Thing | None:
        return next((t for t in self._things if t.id == thing_id), None)


# The document declares exactly the cursors the service accepts: every string matching this
# pattern decodes, and anything else is a 422 from validation. A cursor the service never issued
# only moves the page start; authorization still filters every row.
CURSOR_PATTERN = r"^([0-9a-f]{2})+$"


def encode_cursor(thing_id: str) -> str:
    return thing_id.encode().hex()


def decode_cursor(cursor: str) -> str:
    return bytes.fromhex(cursor).decode("utf-8", "replace")


def things_router(store: ThingStore) -> APIRouter:
    # Router-level authentication: an operation added here is authenticated even if it forgets to.
    router = APIRouter(prefix="/v1", dependencies=[Depends(authenticated)])

    @router.get("/things", responses=problems(401, 422))
    async def list_things(
        principal: Authenticated,
        cursor: Annotated[
            str | None, Query(pattern=CURSOR_PATTERN, max_length=2048, description="Opaque cursor from next_cursor; omit for the first page.")
        ] = None,
        limit: Annotated[int, Query(ge=1, description="Page size; values above 200 are lowered to 200.")] = 50,
    ) -> ThingPage:
        """List the things the caller may read, one cursor page at a time."""
        after = decode_cursor(cursor) if cursor is not None else ""
        limit = min(limit, MAX_PAGE_SIZE)
        rows = await store.after(principal, after, limit + 1)  # one extra row says whether more exist
        if len(rows) > limit:
            return ThingPage(data=rows[:limit], next_cursor=encode_cursor(rows[limit - 1].id))
        return ThingPage(data=rows, next_cursor=None)

    @router.get("/things/{thing_id}", responses=problems(401, 404, 422))
    async def get_thing(thing_id: Annotated[str, Path(max_length=64)], principal: Authenticated) -> Thing:
        """Get one thing."""
        thing = await store.get(thing_id)
        if thing is None or not can_read(principal, thing):  # unpermitted means absent for this caller
            raise HTTPException(404, "No thing with that id.")
        return thing

    return router


def create_app(settings: Settings, verify_token: TokenVerifier, store: ThingStore) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Open shared clients and pools here, keep them on app.state, and close them after yield.
        yield

    app = house_app(
        "Things API", "1.0.0", loopback_only=is_loopback(settings.host),
        trusted_request_id_header=settings.trusted_request_id_header, lifespan=lifespan,
    )
    configure_bearer_auth(app, verify_token)

    # Health stays outside the contract and authentication; no health path ends in "z".
    @app.get("/health/live", include_in_schema=False)
    async def live() -> Response:
        return Response(status_code=200)  # process-local: never a dependency check

    @app.get("/health/ready", include_in_schema=False)
    async def ready(request: Request) -> Response:
        if await store.ready():
            return Response(status_code=200)
        return problem(request, 503, "Not ready to receive traffic.")

    app.include_router(things_router(store))
    return app


async def refuse_every_token(token: str) -> Principal | None:
    """The example denies all tokens until wired to the app's trusted bearer verifier."""
    return None


def run() -> None:
    import uvicorn  # noqa: PLC0415 -- the server is needed to run the service, not to test it

    settings = load_settings(os.environ)
    app = create_app(settings, refuse_every_token, ThingStore())
    # PCF and Cloud Run send SIGKILL 10 s after SIGTERM: finish draining inside that.
    uvicorn.run(app, host=settings.host, port=settings.port, timeout_graceful_shutdown=8)


if __name__ == "__main__":
    run()
