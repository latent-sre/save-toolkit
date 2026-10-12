# Consume the API

Read before any request, cache, page, write, error display, live stream or test double. The team's
services are FastAPI and Go behind one contract, backend-craft's: an OpenAPI document, RFC 9457
problems carrying a `request_id`, cursor pages, an `Idempotency-Key` on writes. A repository's own
client wins over every default here. The starting files [problem.ts](../assets/problem.ts) and
[idempotent-write.ts](../assets/idempotent-write.ts) encode the error and write halves: read them,
copy both beside the API client (`idempotent-write.ts` imports `problem.ts`), and keep their tests
green in the app.

## The document and the typed client

Generate from the `openapi.json` the service commits at its repository root; `backend-craft` owns
that file and its gates, and a service without one gains it in its next API change. Copy it into
the UI repository as `docs/openapi.json`, or fetch it in CI from the service's repository at a
pinned ref, and generate from it:

- `openapi-typescript` turns the document into `src/api/schema.d.ts`; commit the output and
  regenerate on every contract change, with a CI step that regenerates and fails on a diff.
- `openapi-fetch` calls through those types: `client.GET("/v1/orders", { params })` returns `data`
  typed as the 2xx body and `error` typed as the declared problem body, so a changed contract fails
  the typecheck at every call site instead of at runtime.
- `openapi-react-query` wraps the client for TanStack Query (`useQuery`, `useSuspenseQuery`,
  `useInfiniteQuery`, `useMutation`, `queryOptions`) and derives query keys from the request.

The error body is typed only where the contract declares `application/problem+json` on that
status, so keep it declared in the service; a FastAPI service without the house error handler
answers its native `{ detail }` shapes, and the problem helper reads both. openapi-fetch reads
every error body before it returns `{ error, response }`, so build the problem from that body:
`if (error !== undefined || !response.ok) throw problemFromBody(error, response)`; `readProblem`
is for a response nobody has read, a plain `fetch` or a middleware handed `response.clone()`.
Create the client once with the base URL from runtime configuration and
`credentials: "same-origin"`, with a middleware that keeps `X-Request-ID` from every response so a
failure is reportable even when the body is not a problem.

## Problems

| Status | The UI does |
|---|---|
| 401 | Hand to the auth client (sign-in or a session refresh); never loop |
| 403 | Say what is not permitted and why; no retry; the rest of the view keeps working |
| 404 | The designed missing or empty state, not an error card |
| 409 with `Retry-After` | An idempotent write still in flight: keep waiting under the same key |
| 409 without | A conflict with current state: show the current state beside the user's intent |
| 410 | The API version is retired; say the app needs an upgrade |
| 422 | Map each `errors[].loc` (or FastAPI's `detail[].loc`) to its field, show `msg` beside it, keep the user's input |
| 429, 503 | Wait `Retry-After` before any retry and show the wait |
| 5xx | The error card, with retry for a safe read |

The error card shows the title, the detail or the next step, the request ID (copyable, and linked
to logs and trace when runtime configuration provides the URL templates), the time with its zone
and the status; never raw JSON, a stack trace or the `type` URI. One card per failing region,
inside that region's boundary; the starting [error panel](../assets/error-panel.tsx) renders it.

## Collections and cursor pages

A collection is `{ "data": [...], "next_cursor": "..." | null }`. Pass the cursor back verbatim as
`?cursor=`; a `limit` above the maximum is lowered, not rejected; there is no total count, so never
invent "page 3 of 12": show "more" and the loaded count. Filters and sorts are the contract's
allowlist: offer only those, keep them in the URL, and send them as query parameters, because
filtering client-side what the server filters downloads rows nobody sees. When appending a page,
drop rows whose id is already shown. With TanStack Query:
`useInfiniteQuery({ initialPageParam: undefined, getNextPageParam: (last) => last.next_cursor ?? undefined })`.

## Writes

One `Idempotency-Key` per user intent: `newIntentKey()` when the action starts (the form opens, the
button is clicked), `sendIdempotent()` for every send of that unchanged action. An edited payload is
a new intent with a new key, because the contract answers a reused key with a different payload
with `422`. Disable the control while the write is pending; mutations do not retry on their own.
Long-running work answers `202` with a status resource: poll it with backoff, show progress, and
let the user leave the page. A bulk action reports each item's outcome, including unknown. Send
writes with a custom header (`X-Requested-With`, or the project's token header), never as a plain
form post, so cookie-authenticated writes carry the server's CSRF defence; where the API supports
`If-Match`, send it so a stale tab gets a `412` instead of overwriting another operator's change.

## Query keys, freshness and retries

Every input that changes the response — path parameters, filters, sort, cursor, the user or tenant
scope — belongs in the query key; `openapi-react-query` derives it from the request, and a
hand-written `queryOptions` lists each input. TanStack Query treats data as stale at once and
refetches on mount, window focus and reconnect; set `staleTime` and those triggers from what the
view needs, because a console refocused all day refetches each time, and a view kept current by a
stream turns them off and lets the stream update the cache. One source per need: never poll and
stream the same data. The query layer is the one retry owner: three retries with backoff by
default, `Retry-After` honoured on `429` and `503`, non-retryable statuses skipped, the client
wrapper never retrying on its own. Show data age from `dataUpdatedAt` ("updated 12 s ago") and a
stale or disconnected state when a refetch fails. Log a `Deprecation` or `Sunset` header once per
session. The UI never calls `/health/*`.

## Live data

SSE carries one-way live data; a WebSocket only when the browser must send as well as receive.
Native `EventSource` sets no headers, so it fits a cookie session; bearer auth needs the fetch-based
`eventsource` package, which also replays `Last-Event-ID` on reconnect. Never put a token in a
stream URL. One reconnect owner per stream, with capped backoff and jitter; stop on view or session
end and on an authentication failure; show connected, stale and reconnecting states with the last
failure's request ID; after a reconnect gap, refetch the affected queries rather than trusting the
replay. Stream filters travel as query parameters; a filter change opens a new stream and keeps the
visible rows until it delivers. Events land in the query cache so the view has one source of
truth; redraws batch per animation frame with a bounded buffer and flush on a timer while the tab
is hidden; a live view keeps a rolling window and says when older data was dropped. Across tabs,
`BroadcastChannel` and Web Locks let one tab own the connection and the rest listen.

## Sessions

A new corporate SSO flow is OIDC Authorization Code with PKCE through a backend-for-frontend that
keeps tokens server-side and gives the browser a `Secure`, `HttpOnly`, `SameSite` session cookie;
sensitive flows get a `reviewer` pass. When JavaScript must hold a bearer token, keep it in memory,
never in storage or a URL, and retry a request once after a refreshable `401` only when replay is
safe. On logout or an identity change: cancel in-flight requests, close streams, clear or replace
the affected query cache, announce on a `BroadcastChannel` so other tabs follow, and keep query
keys scoped by identity so a late response from the old identity never fills the new one.

## Test doubles

MSW 3 mocks the contract at the network boundary (`setupServer` from `msw/node`; `http` and
`HttpResponse`). Write handlers for the statuses the contract declares, including problem bodies
with a `request_id` and a two-page cursor sequence, and test that a `500` renders its request ID, a
`422` lands on the right fields with the input kept, `next_cursor` loads the second page, a filter
reaches the request's query string, a retried write reuses its `Idempotency-Key`, a `409` with
`Retry-After` keeps the key and waits, an edited payload sends a new key, and API text renders as
text.
