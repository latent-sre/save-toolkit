# Sessions, authentication and live transport

Read when changing authentication, session handling, or a live connection. Preserve the
repository's auth client and session contract; add only the mechanisms the affected flow needs.
Requests, caching and problem handling live in [the API reference](./api.md).

## Sign-in and tokens

A new corporate SSO flow uses OIDC Authorization Code with PKCE through a backend-for-frontend
that keeps the OAuth tokens server-side and gives the browser a session cookie: `Secure`,
`HttpOnly`, `SameSite` set for the flow. Sensitive flows get a `reviewer` pass. When JavaScript
must hold a bearer token, keep it in memory, never `localStorage`, `sessionStorage` or a URL;
renew through the project's auth client; retry a request once after a refreshable `401` only when
replay is safe or the server rejected it before any effect. A failed renewal returns to sign-in
without a retry loop, keeping the draft and the URL so the user lands back where they were.

## CSRF on cookie-authenticated writes

The browser sends cookies with cross-site requests, so every state-changing request needs a
defence the server checks. Modern browsers send `Sec-Fetch-Site` on every request; the server
rejects cross-site state changes on it, and keeps a fallback for clients without it — a
synchronizer token for stateful sessions, a signed double-submit cookie for stateless ones. The
UI's part: send API writes with a custom header (`X-Requested-With` or the project's token
header), never as a plain form post, and read the project's token source rather than inventing
one. `SameSite=Lax` is defence in depth, not the defence.

## Identity changes and many tabs

On logout or an identity or scope change: cancel in-flight requests, close every stream, clear or
replace the affected query cache, and announce the change on a `BroadcastChannel` so other tabs
sign out too. A late response from the old identity must never populate the new one, so query
keys carry the scope identifier. Consoles stay open for days: show data age, re-read current
state inside a confirm dialog, and send `If-Match` where the API supports it so a stale tab gets
a `412` instead of overwriting another operator's change.

## Live transport

SSE carries one-way live data; use a WebSocket only when the UI must send as well as receive.
Native `EventSource` sets no headers — it works with a cookie session (`withCredentials` for
cross-origin, with the server's matching CORS policy) — so bearer auth needs a fetch-based reader
such as the maintained `eventsource` package, which also honours `Last-Event-ID` on reconnect.
Never put a token in a stream URL. One reconnect owner per stream, with capped backoff and
jitter; stop on view or session end and on an authentication failure; show connected, stale and
reconnecting states, with the last failure's request ID beside the reconnecting state; after a
reconnect gap, refetch the affected queries rather than trusting the replay alone. Send the
contract's stream filters as query parameters; a filter change opens a new stream and keeps the
visible lines until it delivers. Feed stream events into the query cache so the view renders one
source of truth. Batch redraws per animation frame with a bounded pending buffer, and flush on a
timer while `document.hidden`, because a background tab gets no frames.
