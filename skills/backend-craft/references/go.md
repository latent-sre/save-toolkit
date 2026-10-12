# Go and Huma

`../SKILL.md` owns the house contract; on any conflict it wins. Read the Go and Huma versions from
`go.mod`, never assume them; Huma v2 needs Go 1.25 or later. The starter is
[house.go](../assets/go/house.go) with [main.go](../assets/go/main.go) and
[things.go](../assets/go/things.go) as its example.

## Building the API

- **`NewAPI(mux, title, version, verify)`** builds the Huma API on a standard `http.ServeMux`
  (the `humago` adapter) with the house configuration: no `$schema` property or `Link` header in
  bodies, the request ID stamped on every problem, the bearer scheme, and `RequireAuth`. The
  `init` in `house.go` replaces `huma.NewError` and `huma.NewErrorWithContext` with the house
  Problem; Huma reads the error type when an operation registers, so both must be set before
  the first `huma.Register`.
- **Register with `huma.Register` and a full `huma.Operation`**: `OperationID` (lowerCamel),
  `Method`, a `/v1` `Path`, `Summary`, `Security: Bearer`, and `Errors` listing every error
  status the operation can return, so the document declares them; an operation with a body
  lists `400`, which Huma sends for unparseable JSON. An operation that needs no
  authentication sets `Metadata: Public`, leaves `Security` empty, and is listed in
  `publicOperations`; any other operation is authenticated even if it forgot `Security`.
- **Inputs and outputs are structs.** Parameters are tagged `path:`, `query:` and `header:`;
  the body is a `Body` field. Validation tags (`minLength`, `maxLength`, `pattern`, `enum`,
  `minimum`, `maximum`) become both the document and the check. Huma answers `422` for invalid
  values and unknown body fields and `400` for unparseable JSON. Cross-field checks, and a query
  parameter sent with an empty value (which Huma treats as absent), belong in the input's
  `Resolve(huma.Context) []error` method.
- **Handlers return the house errors**: `huma.Error404NotFound(...)` and its siblings, or a
  `*Problem` for a domain error with its own `Type`. A handler error that is not a status error
  becomes a 500 whose message reaches no client.
- **Two middleware layers.** The `net/http` chain in `newService` wraps every request, including
  the router's own 404 and 405 and the health endpoints: request ID, access log, loopback `Host`
  guard, `http.CrossOriginProtection`, then `WithProblemFallback`. Huma middleware
  (`api.UseMiddleware`, registered before the operations) sees only Huma operations and their
  metadata; authentication lives there.

## The server

- **Timeouts**: the zero `http.Server` has none. Set `ReadHeaderTimeout`, `ReadTimeout`,
  `WriteTimeout` and `IdleTimeout`. `WriteTimeout` also ends a long stream, so a streaming handler
  lifts its own deadline with `http.NewResponseController(w).SetWriteDeadline(time.Time{})`.
- **Shutdown**: `signal.NotifyContext(ctx, os.Interrupt, syscall.SIGTERM)`, then
  `srv.Shutdown` with a deadline inside the platform's grace period. On Windows, Ctrl+C arrives
  as `os.Interrupt` and closing the console window as `SIGTERM`, with 5 s to exit.
- **Memory and CPU**: Go does not derive `GOMEMLIMIT` from the container's memory limit; set it
  to about 90% of the PCF or Cloud Run memory quota so the collector works before the platform
  kills the instance. Since Go 1.25, `GOMAXPROCS` follows a cgroup CPU quota. PCF's Diego gives
  containers CPU shares, not a quota, so `GOMAXPROCS` there stays at the cell's CPU count; log
  `runtime.GOMAXPROCS(0)` at startup and check it on each platform.
- **Logs**: `log/slog` with a JSON handler; the starter's handler adds `request_id` to every
  record logged with a request's context, so log with `slog.InfoContext(ctx, ...)`.

## Data

- PostgreSQL: `pgx` v5 with `pgxpool`. Set `MaxConns` explicitly (the default is the larger of 4
  and the CPU count), and pass the request context to every query: a cancelled context abandons
  the query and usually closes its connection.
- SQL Server: `github.com/microsoft/go-mssqldb`, a pure Go `database/sql` driver with no ODBC
  dependency. Always set `encrypt` explicitly; with it unset, the driver trusts any server
  certificate.
- `sqlc` generates typed Go from SQL for PostgreSQL but does not support SQL Server; SQL Server
  code uses `database/sql` with explicit pool settings (`SetMaxOpenConns`, `SetMaxIdleConns`,
  `SetConnMaxLifetime`).

## Tests

- Drive the full handler from `newService` with `httptest`, as `house_test.go` does, so the
  `net/http` chain is in the test. `humatest.New` builds a bare API without the house
  configuration; use `humatest.Wrap` only for a test of the Huma layer alone.
- `go test -race` for code with goroutines or shared state.
