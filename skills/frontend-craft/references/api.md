# Consume the API

Bind the UI to the actual service contract and reuse an existing typed client. Select only the
sections the app needs.

## Typed client

When OpenAPI is available, generate or bind types from the service's canonical document (`openapi-typescript`,
`openapi-fetch` and `openapi-react-query` are options; FastAPI 0.134+/0.135+ emits OpenAPI 3.2
`itemSchema` for JSONL/SSE, which `openapi-typescript` 7.x reads as `unknown` unless `schema` is
also present). Otherwise bind typed interfaces and runtime validation to the published contract.
Configure base URL, session credentials and correlation headers.

With `openapi-fetch` (which already consumes the response body), parse errors via
`if (error !== undefined || !response.ok) throw problemFromBody(error, response)`.
Use `readProblem` only for an unread response or clone. The [problem helper](../assets/problem.ts)
also normalizes FastAPI native `422`/`HTTPException` shapes and gateway HTML.

## Problems

Map the service's documented statuses and bodies:

| Status | UI response |
|---|---|
| 401 | Auth-client sign-in or session refresh; no loop |
| 403 | Explain the denied permission; no retry; other regions keep working |
| 404 | Designed missing/empty state |
| 409 with `Retry-After` | In-flight idempotent write: wait under the same key |
| 409 without it | Show current state beside the user's conflicting intent |
| 410 | Explain that the API version retired and the app needs upgrading |
| 422 | Map `errors[].loc` or FastAPI `detail[].loc` to fields, show `msg` beside the field (or via `aria-describedby`), preserve input |
| 429, 503 | Honour `Retry-After` and show the wait |
| 5xx | Actionable error panel; retry only safe requests |

The error panel shows title, detail/next step, status, time/zone and correlation ID (`request_id`
or `X-Request-ID`), with log/trace links when configured. Keep it inside the failing region; never
render raw JSON, stack traces or a problem `type` URI.

## Cursor pages

For `{ data: [...], next_cursor: "..." | null }`, pass `next_cursor` verbatim as `?cursor=`.
Show a "Load more" control and loaded count rather than a total count. Offer only
contract-supported filters/sorts, sync shareable values to the URL and pass them to the server.
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
Cookie-authenticated writes include the server's CSRF token or custom header (`X-Requested-With`).

## Cache and retries

Include path, filters, sort, cursor and user/tenant scope in query keys. Set `staleTime` and
refetch behaviour for the workflow; choose either polling or streaming per resource.

Let the query layer own read retries (typically three with backoff, honouring `Retry-After` on
`429`/`503` and skipping non-retryable statuses). Show `dataUpdatedAt` and stale/disconnected
state after refresh failure. Log `Deprecation` or `Sunset` once per session.

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

Use MSW 3 (`setupServer`, `http`, `HttpResponse`; note MSW 3 renamed `onUnhandledRequest` to
`onUnhandledFrame` on `server.listen()`/`worker.start()`, though fixtures on MSW 2 still use
`onUnhandledRequest`). MSW's `sse` handler (`msw/sse`) intercepts `EventSource` only in the
browser, so use it with `setupWorker` in browser-mode tests; under Node/jsdom, test fetch-based
streams through an `http` handler returning a `ReadableStream`. Test error panels showing
`request_id`, API strings rendered as text, auth/permission failures, session isolation (switch
identity while an old-session response is delayed; none of its data becomes visible), `422`
field-error mapping with input preserved, cursor pagination and URL-synced server filters,
same-key `409` `Retry-After` replay vs new-intent keys, and stream reconnect/teardown.
