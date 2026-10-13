# Go and Huma

Read Go/Huma versions from `go.mod`; Huma v2 needs Go 1.25+. Preserve existing service contracts.
For a new house API, adapt [house.go](../assets/go/house.go),
[main.go](../assets/go/main.go) and [things.go](../assets/go/things.go).

## API and handlers

- `NewAPI(mux, title, version, verify)` uses `http.ServeMux`/`humago` with house configuration:
  no `$schema` body property or `Link` header, request IDs on problems, bearer security and
  `RequireAuth`. `house.go`'s `init` replaces `huma.NewError` and `huma.NewErrorWithContext`
  before the first `huma.Register`, when Huma reads the error type.
- Register a full `huma.Operation`: lowerCamel `OperationID`, `Method`, `/v1` `Path`, `Summary`,
  `Security: Bearer`, and every returned error status in `Errors`. Body operations include `400`
  for unparseable JSON. Public operations set `Metadata: Public`, empty `Security` and an entry
  in `publicOperations`; all others are authenticated even if `Security` is omitted.
- Inputs/outputs are structs: `path:`, `query:`, `header:` tags and a `Body` field. Validation tags
  (`minLength`, `maxLength`, `pattern`, `enum`, `minimum`, `maximum`) drive schema and validation.
  Invalid values/unknown body fields return `422`, unparseable JSON `400`. Cross-field checks and
  present-but-empty query values belong in `Resolve(huma.Context) []error`; Huma treats empty
  query values as absent.
- Return `huma.Error404NotFound(...)` and siblings, or `*Problem` with a domain `Type`. An error
  without a status becomes `500` with no exception message exposed.
- `newService` wraps every request, including router 404/405 and health: request ID, access log,
  loopback Host guard, `http.CrossOriginProtection`, `WithProblemFallback`. Huma middleware
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
- Use JSON `log/slog`; the starter adds `request_id` to request-context records, so use
  `slog.InfoContext(ctx, ...)`.

## Data and tests

- PostgreSQL: `pgx` v5/`pgxpool`, explicit `MaxConns` (default: larger of 4 or CPU count).
  Pass request context to queries; cancellation abandons the query and usually closes its connection.
- SQL Server: pure-Go `github.com/microsoft/go-mssqldb` needs no ODBC. Set `encrypt` explicitly;
  unset, the driver trusts any server certificate.
- `sqlc` generates PostgreSQL code, not SQL Server; SQL Server uses `database/sql` with explicit
  `SetMaxOpenConns`, `SetMaxIdleConns`, `SetConnMaxLifetime`.
- Exercise `newService`'s full handler with `httptest` as `house_test.go` does. `humatest.New`
  omits house configuration; `humatest.Wrap` is only for Huma-layer tests.
- Use `go test -race` for goroutines/shared state.
