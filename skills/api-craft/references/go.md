# Go HTTP services

Preserve the repository's HTTP framework; Huma notes apply only when selected.
Read versions from `go.mod`; `http.CrossOriginProtection` needs Go 1.25+.

## Server and data

- A zero `http.Server` has no timeouts. Set header (`ReadHeaderTimeout`), read, write and idle
  limits for the workload; streaming handlers need an appropriate per-response write deadline.
- Use `signal.NotifyContext` and deadline-bounded `srv.Shutdown` within the host's grace period.
- Enforce authentication, object permissions and browser/host protections across the real chain,
  including routes outside framework middleware.
- PostgreSQL: `pgx`/`pgxpool` is an option; bound pool connections and propagate cancellation.
  Cancellation can close the underlying connection.
- SQL Server: `github.com/microsoft/go-mssqldb` needs no ODBC. Configure encryption and certificate
  validation explicitly. With `database/sql`, bound open/idle connections and connection lifetime.
  `sqlc` supports PostgreSQL, not SQL Server.

## When using Huma

- `humago` integrates with `http.ServeMux`. Match the selected API contract: stable operation IDs,
  paths, security declarations and returned error statuses.
- To omit default `$schema`/`Link` additions, remove the schema-link create hook
  (`config.CreateHooks = nil` for an otherwise unmodified `huma.DefaultConfig`).
- Huma already uses RFC 9457 errors. Override `huma.NewError` only for a custom contract, before
  `huma.Register` reads its type for documentation. `NewErrorWithContext` delegates to it by default;
  if overriding that hook too, keep its type aligned. Both are package-level globals, so mutate them
  once at startup and restore in tests (never with `t.Parallel()`). `ContentType` declares the
  chosen media type.
- Inputs/outputs use structs with `path:`, `query:`, `header:` tags and `Body` (non-body parameter
  fields cannot be pointers; Huma panics at registration).
  Validation tags drive schema and validation. Put cross-field checks and required
  present-but-empty query rejection in `Resolve(huma.Context) []error` (or
  `Resolve(huma.Context, *huma.PathBuffer) []error` on reusable nested types); Huma treats empty
  query values as absent.
- For SSE, use `github.com/danielgtaylor/huma/v2/sse.Register` with an event-type map.
- `api.UseMiddleware` sees registered operations. Cover router 404/405, health and other handlers
  separately when they need correlation, error mapping or security controls.
- Authenticate protected operations even when document security metadata is missing; a verifier
  failure must not make an operation public.

## Verification

Use `httptest` against the full handler chain; test changed lifecycle behavior.
`go-craft` owns language checks.

For [OpenAPI checks](./openapi.md), Schemathesis can run against an `httptest` server.
`PYTHONUTF8=1` avoids Windows pipe decoding mismatches. Required CI checks must fail when their
tooling is unavailable.
`humatest.New(t, config)` accepts configuration but creates a test router. `humatest.Wrap(t, api)`
exercises the existing adapter/router; separately test outer middleware with the full handler.
