# Go and Huma

Read Go/Huma versions from `go.mod`; `http.CrossOriginProtection` needs Go 1.25+.
Preserve existing service contracts and adapt only the components the task needs.

Use the service's established corporate SSO middleware, keeping authentication in place before
exposing shared internal operations and retaining object checks. Corporate SSO does not establish
a token format or protocol; reuse the existing provider integration.

## API and handlers

- Use `http.ServeMux` with `humago`. Set `config.CreateHooks = nil` so responses carry no `$schema`
  body property or `Link` header. Replace `huma.NewError` and `huma.NewErrorWithContext` with a
  problem type before the first `huma.Register`, which reads the error type to document each
  status; its `ContentType` method returns `application/problem+json`. Stamp request IDs on
  errors created without a request context.
- Register a full `huma.Operation`: lowerCamel `OperationID`, `Method`, `/v1` `Path`, `Summary`,
  the actual identity scheme in `Security`, and every returned error status in `Errors`. Body
  operations include `400` for unparseable JSON. Authenticate every operation not explicitly
  public, even if `Security` is omitted; a missing verifier answers `503` and never makes an
  operation public. Public operations set empty `Security` and are listed as deliberate
  exceptions in the contract test; preserve unauthenticated and unauthorized denial checks.
- Inputs/outputs are structs: `path:`, `query:`, `header:` tags and a `Body` field. Validation tags
  (`minLength`, `maxLength`, `pattern`, `enum`, `minimum`, `maximum`) drive schema and validation.
  Invalid values/unknown body fields return `422`, unparseable JSON `400`. Cross-field checks and
  present-but-empty query values belong in `Resolve(huma.Context) []error`; Huma treats empty
  query values as absent.
- Return `huma.Error404NotFound(...)` and siblings, or `*Problem` with a domain `Type`. An error
  without a status becomes `500` with no exception message exposed.
- Wrap every request, including router 404/405 and health, with:
  request ID, access log, loopback Host guard, `http.CrossOriginProtection`, and a fallback that
  turns `ServeMux`'s plain-text 404/405 (with `Allow`) into problems. Huma middleware
  (`api.UseMiddleware` before operations) sees only registered operations/metadata; auth lives there.

## Server

- A zero `http.Server` has no timeouts. Set `ReadHeaderTimeout`, `ReadTimeout`, `WriteTimeout`,
  `IdleTimeout`. A streaming handler lifts its write deadline with
  `http.NewResponseController(w).SetWriteDeadline(time.Time{})`.
- Use `signal.NotifyContext(ctx, os.Interrupt, syscall.SIGTERM)` and deadline-bounded
  `srv.Shutdown` inside the platform's grace period. Windows Ctrl+C is `os.Interrupt`; console
  closure is `SIGTERM` with 5 s to exit.
- Go does not derive `GOMEMLIMIT` from container memory: set about 90% of the PCF/Cloud Run quota.
  Since 1.25, `GOMAXPROCS` follows cgroup CPU quota. PCF Diego supplies shares, not quota, leaving
  it at cell CPU count: log `runtime.GOMAXPROCS(0)` and verify on each platform.
- Use JSON `log/slog`; attach `request_id` to request-context records and use
  `slog.InfoContext(ctx, ...)`.

## Data and tests

- PostgreSQL: `pgx` v5/`pgxpool`, explicit `MaxConns` (default: larger of 4 or CPU count).
  Pass request context to queries; cancellation abandons the query and usually closes its connection.
- SQL Server: pure-Go `github.com/microsoft/go-mssqldb` needs no ODBC. Set `encrypt` explicitly;
  unset, the driver trusts any server certificate.
- `sqlc` generates PostgreSQL code, not SQL Server; SQL Server uses `database/sql` with explicit
  `SetMaxOpenConns`, `SetMaxIdleConns`, `SetConnMaxLifetime`.
- Exercise the real handler chain with `httptest`, asserting problem bodies and request IDs on
  router 404/405, validation, unparseable JSON and identity failures.
- One test fixture feeds the [OpenAPI](./openapi.md) gates: the real handler, stable generated
  document bytes, a local test identity, the document's actual security schemes (including cookie
  sessions and inherited top-level security), deliberately public operation IDs, and the actual
  identity failure statuses, including 401. Schemathesis runs the `st` CLI against an `httptest`
  server with `PYTHONUTF8=1` (Windows pipes otherwise default to cp1252); it skips locally
  without `st` and fails in CI. After `go test -run TestOpenAPIDocument -update`, review
  `openapi.json` and run `go test ./...`.
- Test pagination, object permissions, browser protection and lifecycle against the real service;
  contract-fixture wiring does not supply those checks.
  `humatest.New` omits house configuration; `humatest.Wrap` is only for Huma-layer tests.
- Use `go test -race` for goroutines/shared state.
