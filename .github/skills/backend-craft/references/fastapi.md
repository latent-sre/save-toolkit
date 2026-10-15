# FastAPI

Read FastAPI, Pydantic, Starlette and Python versions from manifests/lockfiles. Preserve existing
service contracts and native identity integration. Shared internal tools use corporate SSO;
its vendor and protocol come from the project. Authenticate protected routes
and authorize each object and collection regardless of network exposure. Public means explicitly
unauthenticated, not internet-facing.

[house.py](../assets/fastapi/house.py) supplies reusable HTTP helpers without an auth adapter or
dummy verifier. Adopt the helpers the app needs.

## App and handlers

- `house_app(title, version, loopback_only=...)` installs problems, request IDs,
  lowerCamel operation IDs, one schema per model, documented Problem errors and browser/host
  guards. Pass `lifespan=` and register routes afterwards.
- Put versioning and the project's authentication dependency on protected routers; get the trusted
  caller from that integration for object authorization. Declare applicable error statuses with
  `responses=problems(401, 404, 422)`.
- Only when that integration accepts bearer tokens, the optional [auth.py](../assets/fastapi/auth.py)
  offers `configure_bearer_auth(app, verify)`, `authenticated` and `Authenticated`. Configure the
  verifier and attach `Depends(authenticated)` to protected routers; setup alone protects no route.
  The verifier returns a trusted `Principal` or `None` for an invalid token and raises on an outage.
  Missing/invalid credentials return 401; an unconfigured or failed verifier returns 503 for a supplied
  bearer token. The adapter supplies no identity provider and assumes no JWT format.
- Use `Annotated` parameters/dependencies and return annotations. A returned `Response` bypasses
  validation/serialization: enforce its contract explicitly.
- One lifespan opens shared clients/pools before `yield`, stores them on `app.state`, and closes
  them afterwards. `on_event` handlers do not run with `lifespan`.
- Domain code raises framework-free `ProblemError(status, type_uri, title, detail)`; the handler
  serializes it.
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
- [contract_checks.py](../assets/fastapi/contract_checks.py) exports plain problem/request-ID and
  document assertions. [test_http_core.py](../assets/fastapi/test_http_core.py) exercises the HTTP
  helper without any app or identity example. Keep real-route authentication and object-authorization
  tests; [test_auth.py](../assets/fastapi/test_auth.py) checks the optional bearer adapter.
- For `test_openapi_document.py` and `test_schemathesis.py`, create a test-only
  `contract_app.py`: supply `make_app()`, seeded resources,
  `TEST_HEADERS` for the test identity, `AUTH_SCHEME` matching the actual named security scheme,
  `AUTH_ERROR_STATUSES` for actual identity failures, and explicit `PUBLIC_OPERATIONS`. The
  fixture must use the real app and its identity integration. Checks run
  lifespan and obtain the schema directly, so no
  public document endpoint is required. Keep fixture credentials confined to tests.
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
