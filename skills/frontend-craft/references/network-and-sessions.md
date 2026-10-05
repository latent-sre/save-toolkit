# Network requests, sessions and live data

Read when changing API requests, query caching, authentication, sessions or live updates.
Preserve the repository's clients and auth contract; add only mechanisms the affected flow needs.

## Cache identity and request load

- Include changing inputs that determine the response in the query key, including user/tenant
  scope where applicable; use identifiers, never credentials. On logout or identity/scope change,
  cancel affected requests, close old streams and clear or replace the affected cache. Late results
  from the old scope must not populate the new one.
- Set freshness and refetch triggers from the view's needs. TanStack Query defaults to stale data,
  refetches on mount/focus/reconnect and retries failed client queries three times. Choose one
  retry owner or coordinate a total attempt budget across client and query layers. Bound retries,
  skip non-retryable errors, and honor server retry delays such as `Retry-After`; do not multiply
  retries or duplicate polling and streams for the same need.

[sourced: TanStack Query [keys](https://tanstack.com/query/latest/docs/framework/react/guides/query-keys)
and [defaults](https://tanstack.com/query/latest/docs/framework/react/guides/important-defaults)]

## Authentication

For new corporate SSO flows use OIDC Authorization Code + PKCE; get a `reviewer` pass for sensitive
flows. A BFF keeps OAuth tokens on the backend. Its session cookies need Secure, HttpOnly and
SameSite set for the flow, plus CSRF protection for state-changing cookie-authenticated requests.

If JavaScript calls an API with bearer tokens, keep access tokens in memory, never `localStorage`.
Use the project's auth client for renewal. Retry once after a refreshable auth failure only when
replay is safe or the original operation was rejected before effects. Failed renewal returns to
sign-in without a retry loop. A read-query retry policy does not authorize replaying writes.

## SSE transport

Native `EventSource` has no API for setting an Authorization header. Use a BFF session cookie
(`withCredentials` for cross-origin requests, with the server's matching CORS policy). For bearer
auth, use a fetch-based SSE reader that sets the header and implements reconnect and `Last-Event-ID`
handling. Never put tokens in stream URLs. Keep one reconnect owner, stop on session/view end or
failed authentication, and resynchronize the query cache after replay gaps.

[sourced: MDN [EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource/EventSource)
and [SSE event IDs and reconnect](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)]
