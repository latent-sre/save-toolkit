# FastAPI

Read FastAPI, Pydantic, Starlette and Python versions from manifests/lockfiles. Preserve existing
service contracts and native identity integration. Shared internal tools use corporate SSO;
its vendor and protocol come from the project. Authenticate protected routes
and authorize each object and collection regardless of network exposure. Public means explicitly
unauthenticated, not internet-facing.

## App and handlers

- Build the app with `generate_unique_id_function` returning the lowerCamel handler name,
  `separate_input_output_schemas=False` and `lifespan=`. Register problem+json handlers for
  Starlette's `HTTPException` (it also catches the router's own 404/405), `RequestValidationError`
  and `Exception`; override `app.openapi` so every 4xx/5xx response declares the problem schema.
  Request-ID and browser/host guards are pure ASGI middleware so streamed responses stay unbuffered.
- Put versioning and the project's authentication dependency on protected routers; get the trusted
  caller from that integration for object authorization. Declare each applicable error status in
  `responses=`. Authentication setup alone protects no route.
- Use `Annotated` parameters/dependencies and return annotations. A returned `Response` bypasses
  validation/serialization: enforce its contract explicitly.
- One lifespan opens shared clients/pools before `yield`, stores them on `app.state`, and closes
  them afterwards. `on_event` handlers do not run with `lifespan`.
- Domain code raises a framework-free problem exception carrying status, type URI, title and
  detail; one exception handler serializes it.
- JSON bodies require JSON `Content-Type`. For a webhook sender omitting it, only that route uses
  `APIRouter(strict_content_type=False)` with explicit body validation.
- SSE uses `EventSourceResponse`/`ServerSentEvent` from `fastapi.sse`, as `response_class=` on an
  async generator. It sends `: ping` after 15 s silence and sets `Cache-Control: no-cache` and
  `X-Accel-Buffering: no`. [OpenAPI](./openapi.md) covers generated-client stream types.

## Concurrency and data

- Awaitable libraries use `async def`; blocking libraries use plain `def` routes/dependencies,
  which run in the thread pool. Blocking inside `async def` stalls the worker.
- SQLAlchemy: one `AsyncSession` per request/task, never shared concurrently. Load serialization
  data before returning; implicit lazy loading then fails. Paginated queries order by a unique key.
- PostgreSQL: psycopg 3 via SQLAlchemy `postgresql+psycopg`, sync or async.
- SQL Server: `mssql-python` needs no separate ODBC driver manager; Linux still needs `libltdl7`,
  `libkrb5-3`, `libgssapi-krb5-2`. SQLAlchemy 2.1 uses sync `mssql+mssqlpython`, so routes are
  `def`. Async `mssql+aioodbc` requires Microsoft's ODBC driver on the host.

## Tests and runtime

- `with TestClient(app) as client:` runs lifespan; bare `TestClient(app)` does not.
  `httpx.AsyncClient(transport=ASGITransport(app=app))` also skips it: wrap with
  `asgi_lifespan.LifespanManager`. Assert startup and cleanup, not just responses.
- Exercise the real app with the project's test identity; persistence changes use a disposable
  real datastore.
- Assert problem bodies and `X-Request-ID` on router 404/405, validation 422, unhandled 500 and
  identity failures, plus real-route authentication and object authorization.
- The [OpenAPI](./openapi.md) gates use one test fixture built on the real app and its identity
  integration. Read the schema from `app.openapi()` inside lifespan; Schemathesis runs in-process
  with `schemathesis.openapi.from_dict(app.openapi())` and `schema.app = app`, so no public
  document endpoint is required. Keep fixture credentials confined to tests.
- Start through settings with `uvicorn.run`: all interfaces on platform
  `$PORT`, otherwise `127.0.0.1`, with `timeout_graceful_shutdown=8`. Bare uvicorn binds loopback,
  unreachable by the platform; `fastapi run` binds `0.0.0.0`, unsuitable for a desktop default.
- Behind Gorouter/Cloud Run, `--proxy-headers` trusts only `--forwarded-allow-ips` (default
  loopback). Set ingress addresses; use `'*'` only when the ingress is the sole route to the app.
- `--workers N`/`WEB_CONCURRENCY` means N independent processes and pools: size against memory and
  database connection limits.
- PCF's Python buildpack reads `requirements.txt` (or Pipfile, `setup.py`, conda), not `uv.lock`.
  Commit `uv export --format requirements.txt --no-dev` beside the lock; pin Python in
  `runtime.txt` rather than using the buildpack's old default.
- Keep FastAPI/Starlette patched: Starlette Host-header flaws have bypassed path authorization.
