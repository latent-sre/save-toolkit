# Go HTTP services

Preserve the repository's HTTP framework; Huma notes apply only when selected.
Read versions from `go.mod`; `http.CrossOriginProtection` needs Go 1.25+.

## Server and data

- A zero `http.Server` has no timeouts. Set header (`ReadHeaderTimeout`), read, write and idle
  limits for the workload; streaming handlers need an appropriate per-response write deadline.
- Use `signal.NotifyContext` and deadline-bounded `srv.Shutdown` within the host's grace period.
- Enforce authentication, object permissions and browser/host protections across the real chain,
  including routes outside framework middleware.
- With PostgreSQL `pgx`/`pgxpool`, cancellation can close the underlying connection; propagate it
  and bound pool connections.
- SQL Server: `github.com/microsoft/go-mssqldb` needs no ODBC. Configure encryption and certificate
  validation explicitly. With `database/sql`, bound open/idle connections and connection lifetime.
  `sqlc` supports PostgreSQL, not SQL Server.

## When using Huma

- To omit default `$schema`/`Link` additions, remove the schema-link create hook
  (`config.CreateHooks = nil` for an otherwise unmodified `huma.DefaultConfig`).
- Huma already uses RFC 9457 errors. Override `huma.NewError` only for a custom contract, before
  `huma.Register` reads its type for documentation. `NewErrorWithContext` delegates to it by default;
  if overriding that hook too, keep its type aligned. Both are package-level globals, so mutate them
  once at startup and restore in tests (never with `t.Parallel()`). `ContentType` declares the
  chosen media type.
- Inputs/outputs use structs with `path:`, `query:`, `header:` tags and `Body` (non-body parameter
  fields cannot be pointers; Huma panics at registration).
  Put cross-field checks and required
  present-but-empty query rejection in `Resolve(huma.Context) []error` (or
  `Resolve(huma.Context, *huma.PathBuffer) []error` on reusable nested types); Huma treats empty
  query values as absent.
- For SSE, use `github.com/danielgtaylor/huma/v2/sse.Register` with an event-type map.
- `api.UseMiddleware` sees registered operations. Cover router 404/405, health and other handlers
  separately when they need correlation, error mapping or security controls.
- Authenticate protected operations even when document security metadata is missing; a verifier
  failure must not make an operation public.

## Verification

Use `httptest` against the full handler chain; test lifecycle changes. Prove header-read timeouts
against the serving listener with an incomplete request, not by finding a field in source.
`go-craft` owns language checks.

For Schemathesis [OpenAPI checks](./openapi.md) against `httptest`, `PYTHONUTF8=1` avoids Windows
pipe decoding mismatches. Missing required tooling must fail CI.
`humatest.New(t, config)` accepts configuration but creates a test router. `humatest.Wrap(t, api)`
exercises the existing adapter/router; separately test outer middleware with the full handler.
