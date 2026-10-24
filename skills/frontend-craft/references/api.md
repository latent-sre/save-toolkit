# Consume the API

Reuse the service's client and contract; load only applicable sections.

## Typed client

Use the canonical OpenAPI document when available; verify the selected generator handles streaming
`itemSchema`, not just ordinary `schema`, without degrading event types to `unknown`. Otherwise bind
types and runtime validation to the published contract. Configure base URL, credentials and correlation.

With `openapi-fetch` (which already consumes the response body), parse errors via
`if (error !== undefined || !response.ok) throw problemFromBody(error, response)`.
Use `readProblem` only for an unread response or clone. The [problem helper](../assets/problem.ts)
also normalizes FastAPI native `422`/`HTTPException` shapes and gateway HTML.

## Problems

Use documented status/body semantics. Auth refresh must not loop; permission denial is not retryable
and must leave other regions usable. A `409`/retry hint means in-flight replay only under that
contract; other conflicts show current state beside intent. `410` does not necessarily mean API-version
retirement. Honour documented `Retry-After`; retry failures only for safe requests.

For field errors, map `errors[].loc` or FastAPI `detail[].loc`, preserve input and associate `msg`
with the field (`aria-describedby` where needed). Missing resources get a designed missing/empty state.

Show errors inside the failing region with next step, status, time/zone and correlation ID
(`request_id` or `X-Request-ID`); never dump raw JSON, stack traces or a problem `type` URI.

## Cursor pages

For `{ data: [...], next_cursor: "..." | null }`, pass `next_cursor` verbatim as `?cursor=`.
Do not invent a total count. Use contract-supported server filters/sorts and shareable URL state.
Deduplicate appended rows by ID. In TanStack Query:
`initialPageParam: undefined, getNextPageParam: (last) => last.next_cursor ?? undefined`.

## Writes

Follow the service's write contract: native idempotence, preconditions (`If-Match` → `412`) or
replay keys. For the [idempotent-write helper](../assets/idempotent-write.ts) (`422` payload
mismatch, `409` in-flight with `Retry-After`): mint one `newIntentKey()` per user intent, reuse it
with `sendIdempotent()` on every retry of the unchanged payload, and mint a new key when the user
edits the payload. Pass replayable, non-stream bodies (`ReadableStream` is rejected). Disable
pending controls and automatic mutation retries. Honor `Retry-After` up to `maxWaitMs`; if
exceeded, keep pending state and reconcile without a fresh key.

For `202`, poll the status resource with backoff, show progress and allow navigation away.
Cookie-authenticated writes follow the server's validated CSRF token/header contract; an arbitrary
custom header is not a substitute.

## Cache and retries

Include path, filters, sort, cursor and user/tenant scope in query keys. Set `staleTime` and
refetch behaviour for the workflow; choose either polling or streaming per resource.

Let the query layer own bounded read retries, honouring `Retry-After` and skipping non-retryable
statuses. Show `dataUpdatedAt` and stale/disconnected state after refresh failure; surface applicable
deprecation notices without repeated noise.

## Live data

Default to cache polling; use SSE for one-way streams and WebSocket for bidirectional traffic.
Native `EventSource` suits cookie sessions; bearer auth requires fetch-based `eventsource`
(including `Last-Event-ID` replay; never put tokens in URLs).

Use one reconnect owner with capped backoff/jitter, stopping on unmount, session end or auth
failure. Show connected, stale and reconnecting states with the last failure's request ID, and
refetch after a reconnect gap. Filter changes open a new stream with query parameters while
retaining visible rows until replacement data arrives. Batch cache updates per animation frame
with a bounded buffer (plus timer flush in hidden tabs) and a rolling window that discloses
dropped history.

## Sessions

Reuse the backend's auth and CSRF contract. For OIDC Authorization Code with PKCE via a BFF,
keep tokens server-side behind a `Secure`, `HttpOnly`, `SameSite` cookie. If JavaScript must hold
a bearer token, keep it in memory only (never storage or URLs); refresh `401` once.

On logout or identity change, cancel requests, close streams, clear or re-scope the cache, and
notify other tabs via `BroadcastChannel`; identity-scoped keys stop late responses from the
previous session populating the new one.

## Contract tests

For MSW 3, import `http`/`HttpResponse` from `msw/http`; `server.listen()`/`worker.start()` use
`onUnhandledFrame` rather than MSW 2's `onUnhandledRequest`. Its `sse` handler (`msw/sse`) intercepts `EventSource` only in the
browser, so use it with `setupWorker` in browser-mode tests; under Node/jsdom, test fetch-based
streams through an `http` handler returning a `ReadableStream`. Test error panels showing
`request_id`, API strings rendered as text, auth/permission failures, session isolation (switch
identity while an old-session response is delayed; none of its data becomes visible), `422`
field-error mapping with input preserved, cursor pagination and URL-synced server filters,
same-key `409` `Retry-After` replay vs new-intent keys, and stream reconnect/teardown.
