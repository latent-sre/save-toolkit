# FastAPI

Read FastAPI, Pydantic, Starlette and Python versions from manifests/lockfiles. Preserve the
service's contract and identity integration; select additional machinery for an actual requirement.

## App and handlers

- Use typed models, `Annotated` parameters/dependencies and return annotations. A returned
  `Response` bypasses validation/serialization: enforce its contract explicitly.
- Put authentication dependencies on protected routers and authorize objects/collections using
  the trusted caller. Authentication setup alone protects no route.
- Use `lifespan=` to own shared clients/pools on `app.state`; close them after `yield`.
  `on_event` handlers do not run with `lifespan`.
- Keep domain failures independent of the HTTP framework. Map them to the service's documented
  error contract at the boundary. For RFC 9457, cover Starlette's `HTTPException` (including router
  404/405), `RequestValidationError` and unexpected exceptions; redact internal details.
- Keep correlation and browser/host middleware compatible with streaming; pure ASGI middleware
  avoids buffering responses. Configure guards for the actual deployment and session model.
- JSON bodies require JSON `Content-Type`. If a webhook sender omits it, limit
  `APIRouter(strict_content_type=False)` to that route and validate its body explicitly.
- When SSE is selected, `fastapi.sse` supplies `EventSourceResponse`/`ServerSentEvent`;
  use `response_class=` with an async generator. It sends keep-alive comments after 15 s silence
  and disables caching/proxy buffering. Verify reconnect and client event types.

## Concurrency and data

- Awaitable libraries use `async def`; blocking libraries use plain `def` routes/dependencies
  in the thread pool. Blocking inside `async def` stalls the worker.
- SQLAlchemy: one `AsyncSession` per request/task; load serialization data before returning.
  Implicit lazy loading at response time fails. Order cursor queries by a unique tie-breaker.
- Preserve the project's driver. PostgreSQL's psycopg 3 uses SQLAlchemy `postgresql+psycopg`,
  sync or async.
- For SQL Server, `mssql-python` needs no separate ODBC driver manager; Linux still needs
  `libltdl7`, `libkrb5-3`, `libgssapi-krb5-2`. SQLAlchemy 2.1's `mssql+mssqlpython` is sync,
  so use `def` routes. Async `mssql+aioodbc` needs Microsoft's host ODBC driver.

## Tests and runtime

- `with TestClient(app) as client:` runs lifespan; bare `TestClient(app)` does not.
  HTTPX `ASGITransport` also skips it: use `asgi_lifespan.LifespanManager`.
  Assert startup and cleanup.
- Exercise the real app, identity integration, error mapping and object permissions.
  Persistence changes use a disposable real datastore.
- When using [OpenAPI checks](./openapi.md), read `app.openapi()` inside lifespan.
  Schemathesis can run in-process with `schemathesis.openapi.from_dict(app.openapi())` and
  `schema.app = app`; keep test credentials isolated.
- Bind to the intended interface and port; platform ingress needs a reachable listener, while
  a desktop-only tool binds loopback. Configure Uvicorn's graceful timeout inside the deployment
  deadline.
- Behind a proxy, trust only its known addresses through `--forwarded-allow-ips`; `'*'` requires
  the ingress to be the sole route to the app.
- `--workers N`/`WEB_CONCURRENCY` creates N processes and pools; budget memory and database
  connections across them.
- PCF's Python buildpack reads `requirements.txt` (or Pipfile, `setup.py`, conda), not `uv.lock`.
  For a uv project, export requirements beside the lock and pin Python in `runtime.txt`.
  Keep FastAPI/Starlette security patches current.
