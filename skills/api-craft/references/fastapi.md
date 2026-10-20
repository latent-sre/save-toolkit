# FastAPI

Read FastAPI, Pydantic, Starlette and Python versions from manifests/lockfiles.

## App and handlers

- A returned `Response` bypasses validation/serialization: enforce its contract explicitly.
- Put authentication dependencies on protected routers and authorize objects/collections using
  the trusted caller. Authentication setup alone protects no route.
- Use `lifespan=` to own shared clients/pools on `app.state`; close them after `yield`.
  `on_event` handlers do not run with `lifespan`. Avoid `FastAPI(root_path=...)` (deprecated in
  0.146+; configure the server `--root-path` instead).
- Map failures to the service's error contract. For RFC 9457, cover Starlette's `HTTPException`
  (including router 404/405), `RequestValidationError` and unexpected exceptions; redact internal details.
- Keep correlation and browser/host middleware streaming-compatible; avoid buffering whole responses.
- FastAPI 0.132+ requires JSON `Content-Type` for JSON parsing. For a webhook sender that omits it,
  isolate `APIRouter(strict_content_type=False)` to that endpoint and validate the body explicitly.
- On FastAPI 0.147+, omitted boolean `Form` fields become `False`, empty scalar `Form` values and
  unselected `File` inputs count as missing, and omitted parameter defaults skip validation unless
  `validate_default=True` is set.
- For JSON Lines on FastAPI 0.134+, `yield` items from a handler annotated with
  `AsyncIterable[Item]` or `Iterable[Item]`. For SSE on FastAPI 0.135+, add
  `response_class=EventSourceResponse` (`fastapi.sse`, with `ServerSentEvent` when setting `event`,
  `id`, `retry`, `comment` or `raw_data`); it sends keep-alive comments after 15 s silence and sets
  `Cache-Control: no-cache` and `X-Accel-Buffering: no`. Verify buffering, reconnects and event
  types through the actual proxy/client chain; headers alone do not establish streaming delivery.

## Concurrency and data

- Awaitable libraries use `async def`; blocking libraries use plain `def` routes/dependencies
  in the thread pool. Blocking inside `async def` stalls the worker.
- SQLAlchemy: one `AsyncSession` per request/task with `expire_on_commit=False`; load serialization
  data before returning. Implicit lazy loading or post-commit attribute refresh at response time
  fails (`MissingGreenlet`).
- Preserve the project's driver. PostgreSQL's psycopg 3 uses SQLAlchemy `postgresql+psycopg`,
  sync or async.
- For SQL Server, `mssql-python` needs no separate ODBC driver manager. Its Linux prerequisites
  depend on the distribution: RHEL uses `libtool-ltdl`/`krb5-libs`; Debian/Ubuntu use
  `libltdl7`/`libkrb5-3`/`libgssapi-krb5-2`. SQLAlchemy 2.1's `mssql+mssqlpython` is sync;
  keep calls off the event loop. Async `mssql+aioodbc` needs Microsoft's host ODBC driver.

## Tests and runtime

- `with TestClient(app) as client:` runs lifespan; bare `TestClient(app)` does not.
  HTTPX `ASGITransport` also skips it: use `asgi_lifespan.LifespanManager`.
  Assert startup and cleanup.
- Persistence changes use a disposable real datastore.
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
- PCF's Python buildpack reads `requirements.txt` (or Pipfile, `setup.py`, conda), not `uv.lock`.
  For a uv project, export requirements beside the lock and pin Python in `runtime.txt`.
