# FastAPI and Go HTTP services

Read locked framework, Pydantic, Starlette, SQLAlchemy, and Go versions from manifests (`uv.lock`,
`go.mod`) before editing.

## FastAPI & Starlette

- **Handlers & routing:** A returned `Response` bypasses response-model validation/serialization. Attach
  auth dependencies to protected routers and enforce object/collection authorization in handlers. Map
  Starlette `HTTPException` (including 404/405), `RequestValidationError`, and unexpected errors to
  the service error contract without leaking internal exceptions or submitted secrets. Use
  `APIRouter(strict_content_type=False)` only on endpoints that must accept headerless JSON. Keep
  middleware streaming-compatible (do not buffer whole responses).
- **Lifespan & proxies:** Put shared HTTP clients and pools in `lifespan=` on `app.state`, closing after
  `yield` (`on_event` hooks do not run when `lifespan` is used). Use `--root-path` behind path prefixes,
  scope `--forwarded-allow-ips` strictly to trusted proxies (`'*'` only when ingress strips client-supplied
  forwarded headers), align Uvicorn graceful shutdown timeout inside the deploy deadline, and budget DB
  connection pools across `--workers N` / `WEB_CONCURRENCY`.
- **SQLAlchemy & drivers:** Use one `AsyncSession` per request/task with `expire_on_commit=False` and
  eagerly load response data before returning (prevents `MissingGreenlet`). Keep the repo's driver:
  PostgreSQL uses `postgresql+psycopg` (psycopg 3, sync or async); SQL Server uses sync
  `mssql+mssqlpython` (SQLAlchemy 2.1, off the event loop, no ODBC manager needed) or async
  `mssql+aioodbc` (requires Microsoft's host ODBC driver).
- **Tests:** `with TestClient(app) as client:` and `schemathesis.openapi.from_asgi(schema_path, app)` /
  `from_dict(app.openapi())` execute `lifespan` automatically (do not wrap Schemathesis inside
  `TestClient` or `LifespanManager`). Bare `TestClient(app)` and HTTPX `ASGITransport` skip `lifespan`
  unless wrapped in `asgi_lifespan.LifespanManager`. On FastAPI/Pydantic upgrades, test omitted booleans,
  empty scalar forms, and unselected files.

## Go HTTP services

- **Timeouts & lifecycle:** A zero `http.Server` has no timeouts — always configure `ReadHeaderTimeout`,
  `ReadTimeout`, `WriteTimeout`, and `IdleTimeout` (with per-response write deadlines for streaming
  handlers) and verify header timeouts against a live `httptest`/serving listener. Use
  `signal.NotifyContext` with deadline-bounded `srv.Shutdown`.
- **Middleware & CSRF:** Preserve the repo's router/framework; `http.CrossOriginProtection` requires
  Go 1.25+. Enforce authentication, authorization, and browser protections across the full handler chain,
  including routes mounted outside framework middleware.
- **Databases:** With PostgreSQL `pgx`/`pgxpool`, propagate request context cancellation and bound pool
  size. With SQL Server `github.com/microsoft/go-mssqldb` (no ODBC needed), configure TLS encryption and
  certificate verification explicitly, and bound `database/sql` open/idle connections and lifetime.
  (`sqlc` supports PostgreSQL, not SQL Server.)
