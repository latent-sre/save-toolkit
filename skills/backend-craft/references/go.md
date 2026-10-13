# Go and Huma

Read Go/Huma versions from `go.mod`; the browser guard in this example needs Go 1.25+.
Preserve existing service contracts and adapt only the components the task needs.

- [house.go](../assets/go/house.go) supplies common problems, request IDs, router fallbacks,
  cursor-page types and `HouseConfig(title, version)`. It works without the other example files.
  `HouseConfig` supplies document/error configuration only: it installs no authentication or
  request middleware. Use it with the service's established corporate SSO middleware, keeping
  authentication in place before exposing shared internal operations and retaining object checks.
- [auth.go](../assets/go/auth.go) is an optional bearer adapter for an integration that actually
  verifies bearer tokens. Corporate SSO does not establish a token format or protocol. Reuse the
  existing provider integration instead of adding this adapter when it already handles identity.
- [main.go](../assets/go/main.go) and [things.go](../assets/go/things.go) are optional service and
  domain examples. Skipping them does not remove browser/Host protection, request logging,
  object authorization, server timeouts or shutdown requirements from the real service.

## API and handlers

- The optional adapter's `NewAPI(mux, title, version, verify)` uses `http.ServeMux`/`humago` with:
  no `$schema` body property or `Link` header, request IDs on problems, bearer security and
  `RequireAuth`. It authenticates unmarked operations and returns `503` when the verifier is nil;
  it never turns protected operations public. `house.go`'s `init` replaces `huma.NewError` and
  `huma.NewErrorWithContext` before the first `huma.Register`, when Huma reads the error type.
- Register a full `huma.Operation`: lowerCamel `OperationID`, `Method`, `/v1` `Path`, `Summary`,
  the actual identity scheme in `Security`, and every returned error status in `Errors`. Body
  operations include `400` for unparseable JSON. With the optional bearer adapter, use
  `Security: Bearer`; public operations set `Metadata: Public`, empty `Security` and an entry
  in the service fixture's `publicOperations`. All others are authenticated even if
  `Security` is omitted. For another SSO integration, configure its named document schemes and
  test identity in the fixture; preserve unauthenticated and unauthorized denial checks.
- Inputs/outputs are structs: `path:`, `query:`, `header:` tags and a `Body` field. Validation tags
  (`minLength`, `maxLength`, `pattern`, `enum`, `minimum`, `maximum`) drive schema and validation.
  Invalid values/unknown body fields return `422`, unparseable JSON `400`. Cross-field checks and
  present-but-empty query values belong in `Resolve(huma.Context) []error`; Huma treats empty
  query values as absent.
- Return `huma.Error404NotFound(...)` and siblings, or `*Problem` with a domain `Type`. An error
  without a status becomes `500` with no exception message exposed.
- The optional `newService` example wraps every request, including router 404/405 and health:
  request ID, access log, loopback Host guard, `http.CrossOriginProtection`, `WithProblemFallback`. Huma middleware
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
- Exercise the real handler chain with `httptest` and the reusable `call`, `assertProblem` and
  `assertRequestID` in [contract_helpers_test.go](../assets/go/contract_helpers_test.go).
  [core_test.go](../assets/go/core_test.go) needs only those helpers and `house.go`;
  [auth_test.go](../assets/go/auth_test.go) separately checks the optional bearer adapter.
- Replace [example_fixture_test.go](../assets/go/example_fixture_test.go) with a service test
  fixture: `contractService(t)` returns the real handler and stable generated document bytes;
  `contractHeaders` supplies a local test identity; `authenticatedSchemes` names the document's
  actual schemes, `authErrorStatuses` lists actual identity failures, and `publicOperations` lists
  deliberate anonymous exceptions. This one seam feeds [openapi_test.go](../assets/go/openapi_test.go) and
  [schemathesis_test.go](../assets/go/schemathesis_test.go), including cookie sessions and inherited
  top-level security. No Things store or bearer adapter is required. Keep the update command:
  `go test -run TestOpenAPIDocument -update`, then review `openapi.json` and run `go test ./...`.
- [house_test.go](../assets/go/house_test.go) retains the optional Things example's pagination,
  object permissions, browser protection and lifecycle checks. Reuse applicable cases with the
  real service's resources; changing fixture wiring does not supply those domain checks.
  `humatest.New` omits house configuration; `humatest.Wrap` is only for Huma-layer tests.
- Use `go test -race` for goroutines/shared state.
