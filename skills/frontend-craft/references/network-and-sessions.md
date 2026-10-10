# Network requests, sessions and live data

Read when changing API requests, untrusted-content rendering, caching, authentication, sessions or live updates.
Preserve the repository's clients and auth contract; add only mechanisms the affected flow needs.

## API contracts and untrusted content

Preserve the existing API/client approach. Generate a typed client when supported by its contract
and tooling; OpenAPI is optional. Check generated-client drift in CI; test other clients' response
and error handling against their contract.
Validate untrusted data at the boundary; static types do not validate network responses at runtime.
Keep secrets out of browser bundles and public configuration. Render text through the framework's
safe binding; sanitize untrusted HTML, including HTML produced by a Markdown renderer, and validate
URL schemes before using rendering escape hatches. UI visibility is not authorization: the server
must enforce access to actions and data.

## Cache identity and request load

- Include changing inputs that determine the response in the query key, including user/tenant
  scope where applicable; use identifiers, never credentials. On logout or identity/scope change,
  cancel affected requests, close old streams and clear or replace the affected cache. Late results
  from the old scope must not populate the new one.
- Set freshness and refetch triggers from the view's needs. If using TanStack Query, its defaults are stale data,
  refetches on mount/focus/reconnect and retries failed client queries three times. Choose one
  retry owner or coordinate a total attempt budget across client and query layers. Bound retries,
  skip non-retryable errors, and honor server retry delays such as `Retry-After`; do not multiply
  retries or duplicate polling and streams for the same need.

## Authentication

For new corporate SSO flows use OIDC Authorization Code + PKCE; get a `reviewer` pass for sensitive
flows. A BFF keeps OAuth tokens on the backend. Its session cookies need Secure, HttpOnly and
SameSite set for the flow, plus CSRF protection for state-changing cookie-authenticated requests.

If JavaScript calls an API with bearer tokens, keep access tokens in memory, never `localStorage`.
Use the project's auth client for renewal. Retry once after a refreshable auth failure only when
replay is safe or the original operation was rejected before effects. Failed renewal returns to
sign-in without a retry loop. A read-query retry policy does not authorize replaying writes.

## Live transport

Choose polling, SSE or WebSockets from the API and update needs, including direction, latency and
connection cost. Close subscriptions on view/session end, show stale/disconnected state, and
resynchronize state after reconnect gaps. Coordinate polling and streams instead of duplicating
load. Apply the following mechanics when SSE is selected.

Native `EventSource` has no API for setting an Authorization header. Use a BFF session cookie
(`withCredentials` for cross-origin requests, with the server's matching CORS policy). For bearer
auth, use a fetch-based SSE reader that sets the header and implements reconnect and `Last-Event-ID`
handling. Never put tokens in stream URLs. Keep one reconnect owner, stop on session/view end or
failed authentication, and resynchronize the affected state after replay gaps.
