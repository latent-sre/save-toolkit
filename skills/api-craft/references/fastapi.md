# FastAPI

Read FastAPI, Pydantic, Starlette and Python versions from manifests/lockfiles.

## App and handlers

- A returned `Response` bypasses validation/serialization: enforce its contract explicitly.
- Put authentication dependencies on protected routers and authorize objects/collections using
  the trusted caller. Authentication setup alone protects no route.
- Shared clients/pools belong to `lifespan=` on `app.state`, closed after `yield`;
  `on_event` handlers do not run with `lifespan`. Configure proxy root paths through the server's
  supported `--root-path` option.
- Map failures to the service's error contract. For RFC 9457, cover Starlette's `HTTPException`
  (including router 404/405), `RequestValidationError` and unexpected exceptions; redact internal details.
- Keep correlation and browser/host middleware streaming-compatible; avoid buffering whole responses.
- Where strict JSON content-type checks are enabled, a sender omitting the header needs an
  endpoint-scoped exception (`APIRouter(strict_content_type=False)` when supported) and explicit
  body validation; do not relax unrelated routes.
- Form/file missing-value normalization and default validation depend on the pinned versions.
  Test omitted booleans, empty scalar forms, unselected files and invalid defaults on upgrades.
- Use native typed JSONL/SSE support when the pinned framework and client support it. Verify
  buffering, reconnects and event types through the actual proxy/client chain; response headers
  alone do not establish streaming delivery. Check the generated schema under [OpenAPI](./openapi.md).

## Concurrency and data

- Keep blocking library calls off the event loop; plain `def` routes/dependencies use the thread pool.
- SQLAlchemy: one `AsyncSession` per request/task with `expire_on_commit=False`; load serialization
  data before returning. Implicit lazy loading or post-commit attribute refresh at response time
  fails (`MissingGreenlet`).
- Preserve the project's driver. PostgreSQL's psycopg 3 uses SQLAlchemy `postgresql+psycopg`,
  sync or async. For SQL Server, SQLAlchemy 2.1's `mssql+mssqlpython` is sync (keep calls off the
  event loop, no ODBC manager needed); async `mssql+aioodbc` requires Microsoft's host ODBC driver.

## Tests and runtime

- `with TestClient(app) as client:` runs lifespan; bare `TestClient(app)` does not.
  HTTPX `ASGITransport` also skips it: use `asgi_lifespan.LifespanManager`.
  Assert startup and cleanup.
- For in-process [OpenAPI checks](./openapi.md), use
  `schemathesis.openapi.from_asgi(schema_path, app)` with the service's actual schema URL path, or
  `schemathesis.openapi.from_dict(app.openapi())` with `case.call_and_validate(app=app)` inside
  lifespan when no schema route is served. Schemathesis `from_asgi` owns lifespan; do not also wrap
  the app in a `TestClient` or `LifespanManager`.
  Keep test credentials isolated.
- Configure Uvicorn's graceful timeout inside the deployment deadline.
- Behind a proxy, trust only its known addresses through `--forwarded-allow-ips`; `'*'` requires
  the ingress to be the sole route to the app.
- `--workers N`/`WEB_CONCURRENCY` creates N processes and pools; budget memory and database
  connections across them.
