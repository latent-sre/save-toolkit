# FastAPI

`../SKILL.md` owns the house contract; on any conflict it wins. Read FastAPI, Pydantic, Starlette
and Python versions from the project's manifests and lockfiles, never assume them. The starter is
[house.py](../assets/fastapi/house.py) with [main.py](../assets/fastapi/main.py) as its example.

## Building the app

- **`house_app(title, version, verify_token=..., loopback_only=...)`** builds the FastAPI app on
  the house contract: problem handlers, request IDs, lowerCamel operation IDs, one schema per
  model, the Problem body on every error response in the document, and the browser and host
  guards. Pass `lifespan=` through it; register routes after it.
- **Routers carry the version and the authentication**:
  `APIRouter(prefix="/v1", dependencies=[Depends(authenticated)])`, so an operation added later is
  authenticated even if it forgets. A handler that needs the caller takes `principal: Authenticated`.
  Declare each route's error statuses with `responses=problems(401, 404, 422)`.
- **Declare parameters and dependencies with `Annotated`**, and the response by the handler's
  return annotation. A returned `Response` bypasses validation and serialization; enforce its
  contract yourself.
- **One lifespan owns shared resources**: open clients and pools before `yield`, keep them on
  `app.state`, close them after. `on_event` handlers do not run when `lifespan` is set.
- **Domain errors stay free of FastAPI**: raise `ProblemError(status, type_uri, title, detail)`
  from domain code; the installed handler turns it into the problem.
- **Strict JSON bodies**: a JSON body must arrive with a JSON `Content-Type`. For a webhook sender
  that omits it, put only that route on `APIRouter(strict_content_type=False)` and validate the
  body explicitly.
- **Server-Sent Events**: `EventSourceResponse` with `ServerSentEvent` from `fastapi.sse`, used
  as `response_class=` on an async generator. It sends a `: ping` comment after 15 s of silence
  and sets `Cache-Control: no-cache` and `X-Accel-Buffering: no`. See the OpenAPI reference for
  how generated clients type the stream.

## Concurrency and data

- `async def` fits awaitable libraries; a plain `def` route or dependency runs in the thread pool
  and suits blocking libraries. A blocking call made directly inside `async def` stalls every
  request on the worker.
- With async SQLAlchemy, open one `AsyncSession` per request or task and never share it across
  concurrent tasks. Load what serialization needs before returning: implicit lazy loading during
  serialization fails. Paginated queries order by a unique key.
- PostgreSQL: psycopg 3, through SQLAlchemy's `postgresql+psycopg` dialect, sync or async.
- SQL Server: `mssql-python` needs no separately installed ODBC driver manager (Linux images still
  need `libltdl7`, `libkrb5-3` and `libgssapi-krb5-2`); SQLAlchemy 2.1 reaches it as
  `mssql+mssqlpython`, synchronously, so its routes are `def`. The only async SQLAlchemy SQL Server
  dialect, `mssql+aioodbc`, needs Microsoft's ODBC driver installed on the host.

## Tests

- `with TestClient(app) as client:` runs the lifespan; a bare `TestClient(app)` does not.
- `httpx.AsyncClient(transport=ASGITransport(app=app))` never runs the lifespan: wrap the app in
  `asgi_lifespan.LifespanManager`. Assert startup and cleanup; a response alone proves neither ran.
- Drive the real app with the project's test identity; a changed persistence boundary gets a
  disposable real datastore.

## Running

- `uvicorn main:build --factory --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}"
  --timeout-graceful-shutdown 8`. uvicorn binds `127.0.0.1` by default; `fastapi run` binds
  `0.0.0.0`, so never use it for a desktop tool.
- Behind Gorouter or Cloud Run, `--proxy-headers` trusts `X-Forwarded-*` only from the addresses
  in `--forwarded-allow-ips` (default loopback): set the ingress's addresses, or `'*'` only when
  nothing reaches the app except through the ingress.
- `--workers N` (or `WEB_CONCURRENCY`) starts N processes, each with its own memory and
  connection pools: size N against the memory quota and the database's connection limit.
- PCF's Python buildpack installs from `requirements.txt` (or Pipfile, `setup.py`, conda), not
  from `uv.lock`: commit `uv export --format requirements.txt --no-dev` output beside the lock, and
  pin the Python version in `runtime.txt`, since the buildpack's default is old.
- Keep FastAPI and Starlette on patched releases: Host-header handling flaws in Starlette have
  bypassed path-based authorization.
