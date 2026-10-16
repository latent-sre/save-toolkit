# Go HTTP services

Framework selection is open. Preserve the repository's choice; use standard-library HTTP or
another framework when it fits the task. The Huma notes below apply only when Huma is selected.
Read versions from `go.mod`; `http.CrossOriginProtection` needs Go 1.25+.

## Server and data

- A zero `http.Server` has no timeouts. Set header, read, write and idle limits for the workload;
  streaming handlers need an appropriate per-response write deadline.
- Use `signal.NotifyContext` and deadline-bounded `srv.Shutdown` within the host's grace period.
  Windows Ctrl+C is `os.Interrupt`; console closure gives limited shutdown time.
- Set container memory headroom deliberately. Go 1.25+ follows cgroup CPU quotas for
  `GOMAXPROCS`; PCF shares may leave it at cell CPU count. Verify effective limits on the target.
- Use structured request-context logging and the service's correlation identity.
  Enforce authentication, object permissions and browser/host protections across the real chain,
  including routes outside framework middleware.
- PostgreSQL: `pgx`/`pgxpool` is an option; bound pool connections and propagate cancellation.
  Cancellation can close the underlying connection.
- SQL Server: `github.com/microsoft/go-mssqldb` needs no ODBC. Configure encryption and certificate
  validation explicitly. With `database/sql`, bound open/idle connections and connection lifetime.
  `sqlc` supports PostgreSQL, not SQL Server.

## When using Huma

- `humago` integrates with `http.ServeMux`. Match the selected API contract: stable operation IDs,
  paths, security declarations and returned error statuses.
- For a contract excluding Huma's `$schema` body property and `Link` header, set
  `config.CreateHooks = nil`. For RFC 9457 errors, replace `huma.NewError` and
  `huma.NewErrorWithContext` before `huma.Register`, which reads the error type for documentation.
  Its `ContentType` method declares the chosen media type.
- Inputs/outputs use structs with `path:`, `query:`, `header:` tags and `Body`.
  Validation tags drive schema and validation. Put cross-field checks and required
  present-but-empty query rejection in `Resolve(huma.Context) []error`; Huma treats empty query
  values as absent.
- `api.UseMiddleware` sees registered operations. Cover router 404/405, health and other handlers
  separately when they need correlation, error mapping or security controls.
- Authenticate protected operations even when document security metadata is missing; a verifier
  failure must not make an operation public.

## Verification

Exercise the real handler chain with `httptest`: serialization, errors, authentication and object
access, pagination, concurrency and lifecycle where applicable. Use `go test -race` for shared state.

For [OpenAPI](./openapi.md), verify the selected document and consumer contract.
Schemathesis can run against an `httptest` server; `PYTHONUTF8=1` avoids Windows pipe decoding
mismatches. Required CI checks must fail when their tooling is unavailable.
`humatest.New` does not apply application configuration; `humatest.Wrap` only covers the Huma layer.
