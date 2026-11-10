# Go HTTP services

Preserve the repository's HTTP framework.
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

## Verification

Use `httptest` against the full handler chain; test lifecycle changes. Prove header-read timeouts
against the serving listener with an incomplete request, not by finding a field in source.
`go-craft` owns language checks. Missing required tooling must fail CI.
