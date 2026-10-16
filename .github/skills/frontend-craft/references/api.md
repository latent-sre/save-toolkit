# Consume the API

Bind the new UI to the actual service contract, whether the backend is new or existing.
The team's FastAPI/Go contract uses OpenAPI, RFC 9457 problems with `request_id`, cursor pages
for paged collections and `Idempotency-Key` for writes. Reuse an equivalent repository client.
Select the sections the app needs.

## Contents

- [Typed client](#typed-client)
- [Problems](#problems)
- [Cursor pages](#cursor-pages)
- [Writes](#writes)
- [Cache and retries](#cache-and-retries)
- [Live data](#live-data)
- [Sessions](#sessions)
- [Contract tests](#contract-tests)

## Typed client

Use the backend's canonical OpenAPI document. New services commit `openapi.json` at the service
root; existing services keep their established format and location. A UI may commit a pinned
consumer copy as `docs/openapi.json` or fetch it in CI from a pinned service revision; that copy
does not become the service's source of truth. FastAPI and Huma serve `/openapi.json` by
default; for another Go generator, check its format (oapi-codegen supports 3.1; swag's stable
line emits Swagger 2.0).

Generate `src/api/schema.d.ts` with `openapi-typescript`, commit it and fail CI if regeneration
differs. `openapi-fetch` provides typed calls; `openapi-react-query` adds TanStack Query
hooks/options and request-derived keys. Create one client from the configured base URL with
`credentials: "same-origin"`; retain `X-Request-ID` from responses.

Declare problem bodies for each error status in the service document. openapi-fetch already
consumes the body, so use
`if (error !== undefined || !response.ok) throw problemFromBody(error, response)`.
Use `readProblem` only for an unread response or clone. The [problem helper](../assets/problem.ts)
also handles FastAPI's native errors and gateway HTML.

## Problems

| Status | UI response |
|---|---|
| 401 | Auth-client sign-in or session refresh; no loop |
| 403 | Explain the denied permission; no retry; other regions keep working |
| 404 | Designed missing/empty state |
| 409 with `Retry-After` | In-flight idempotent write: wait under the same key |
| 409 without it | Show current state beside the user's conflicting intent |
| 410 | Explain that the API version retired and the app needs upgrading |
| 422 | Map `errors[].loc` or FastAPI `detail[].loc` to fields, show `msg`, preserve input |
| 429, 503 | Honour `Retry-After` and show the wait |
| 5xx | Actionable error panel; retry only safe requests |

The error panel shows title, detail/next step, status, time/zone and
copyable request ID, with log/trace links when configuration provides templates. Keep it inside
the failing region; never substitute raw JSON, stack traces or a problem `type` URI.

## Cursor pages

For `{ data: [...], next_cursor: "..." | null }`, return the cursor verbatim as `?cursor=`.
The service caps oversized limits; no total count exists, so show “more” and the loaded count.
Offer only contract-supported filters/sorts, put shareable values in the URL and send them to the
server. Deduplicate appended rows by ID. TanStack Query's page rule is:
`initialPageParam: undefined, getNextPageParam: (last) => last.next_cursor ?? undefined`.

## Writes

Use the [idempotent-write helper](../assets/idempotent-write.ts), which imports the problem
helper, or an equivalent implementation. Create one `newIntentKey()` per user intent; reuse it
with `sendIdempotent()` on every send of the unchanged payload. Editing the payload creates a
new intent/key; reuse with a different payload returns `422`. Disable pending controls and
turn off automatic mutation retries. Unknown outcomes remain unknown until reconciled.
For an in-flight `409`, honor the full `Retry-After`; if it exceeds the wait budget, retain the
pending state and reconcile later without an early resend or a fresh key.

For `202`, poll the status resource with backoff, show progress and allow navigation away.
Cookie-authenticated writes carry the server's CSRF defence through its token/custom header
(`X-Requested-With` where that is the contract), never a plain form post. Send `If-Match`
where supported so stale writes receive `412` instead of overwriting newer state.

## Cache and retries

Keys include every response-changing input: path, filters, sort, cursor and user/tenant scope.
Set `staleTime` and refetch-on-mount/focus/reconnect to the workflow; default immediate staleness
can cause repeated console refetches. Choose one update source per need: polling or streaming.

The query layer owns read retries, normally three with backoff; honour `Retry-After` on
`429`/`503`, skip non-retryable statuses and avoid wrapper-level retries. Show
`dataUpdatedAt` and stale/disconnected state after refresh failure. Log `Deprecation` or
`Sunset` once per session. The UI never calls `/health/*`.

## Live data

Default to polling through the cache; use the API's SSE stream for one-way live updates.
WebSocket fits bidirectional traffic. Native `EventSource` cannot set headers and suits cookie
sessions; bearer auth needs fetch-based `eventsource`, including `Last-Event-ID` replay.
Tokens never belong in stream URLs.

One reconnect owner uses capped backoff/jitter and stops on view/session end or auth failure.
Show connected, stale and reconnecting states with the last failure's request ID. Refetch after
a reconnect gap. Filter changes open a new stream with query parameters, retaining visible rows
until replacement data arrives. Events update the query cache; batch redraws per frame with a
bounded buffer and a timer flush in hidden tabs. Keep a rolling window and disclose dropped
history. For cross-tab sharing, BroadcastChannel and Web Locks can elect one connection owner.

## Sessions

Reuse the backend's auth flow. Corporate SSO does not settle the provider, protocol or browser
session contract; resolve those from the actual integration before implementing a new flow.
When that contract uses OIDC Authorization Code with PKCE through a backend-for-frontend,
keep tokens server-side and use a `Secure`, `HttpOnly`, `SameSite` session cookie. Carry the
actual session and CSRF contract into the UI. Sensitive flows get a `reviewer` pass. If
JavaScript must hold a bearer token, keep it in memory, never storage or URLs; refresh a `401`
once and replay only when safe.

Logout or identity change cancels requests, closes streams and clears/replaces the affected
cache. Notify other tabs through BroadcastChannel; identity-scoped keys prevent late responses
from the previous session populating the new one.

## Contract tests

Use MSW 3 at the network boundary (`setupServer`, `http`, `HttpResponse`) for the contract
the app consumes. Test errors rendering request IDs, API text remaining text, auth/permission
failures and session isolation. For forms, verify `422` field mapping with input preserved;
for paged collections, two pages, deduplication and server filter parameters; for writes, same-key
retry, waiting on `409`/`Retry-After` and a new key after editing. Live views need reconnect,
stale and teardown checks.
