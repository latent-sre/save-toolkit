# Consume the API

Read before any request, cache, page, write, error display or test double. The services this
team builds follow `backend-craft`'s house contract; this file is the browser side of that
contract. A repository's own client and contract win over every default here. Start from
[the problem helper](../assets/problem.ts) and [its test](../assets/problem.test.ts): read them,
write them beside the API client with the editor tools (never a shell copy from the skill's
folder), and adapt the names to the app. They encode the error shape
below and run with `node --test`, no packages.

## The typed client

Generate types from the service's OpenAPI document with `openapi-typescript`, and call the API
through `openapi-fetch`: `client.GET("/v1/incidents", { params })` returns `data` typed as the
2xx body and `error` typed as the declared problem body, so a changed contract fails the
typecheck at every call site instead of at runtime. React wraps the client with
`openapi-react-query` (`useQuery`, `useInfiniteQuery`, `useMutation`, `queryOptions`); Vue has
no official wrapper, so wrap client calls in `queryOptions` for `@tanstack/vue-query`, or use
`orval` or `kubb` when generated composables are wanted. Commit the generated types and
regenerate on every contract change; in CI, regenerate and fail on a diff
(`openapi-typescript --check`), then run `tsc --noEmit`. The error body is typed only where the
contract declares `application/problem+json` on that status, so keep it declared.
([openapi-typescript](https://openapi-ts.dev/introduction))

## Problem responses

Every error is an [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457.html) problem:
`type` (a stable URI — the contract; compare it, never the title), `title` (display text),
`status`, `detail` (what to do), `instance`, plus the house extensions `request_id` (required;
also sent as the `X-Request-ID` header, which a cross-origin client reads only when the server
exposes it) and `errors[]` of `{ loc: string[], msg: string }` for field-level validation
failures. Ignore members you do not recognise. A gateway can answer with HTML or an empty body
instead of a problem; the helper synthesises a problem from the status and headers so the UI
still has something to show.

| Status | The UI does |
|---|---|
| 401 | Hand to the auth client (sessions reference); never loop |
| 403 | Say the action is not permitted; no retry, no hidden control |
| 404 | The designed missing or empty state, not an error card |
| 409 | With `Retry-After`, an idempotent write still in flight: keep waiting. Without it, a conflict: show the current state |
| 410 | The version is retired; the app needs an upgrade, say so |
| 422 | Map each `errors[].loc` to its field and show `msg` beside it; keep the user's input |
| 429, 503 | Wait `Retry-After` before any retry; show the wait |
| 5xx | The error card below, with retry for a safe read |

## The error card

One card per failing panel, inside the panel's error boundary. It shows the `title`, the
`detail` or the next step, the request ID (copyable — it is the key to the log line), the time
with its zone, and the status; a retry only when the request is safe to repeat. Never raw JSON,
a stack trace, or the `type` URI. An operator reads this card during an incident: every word is
there to tell them what happened and what to do.

## Collections and cursor pages

A collection is `{ "data": [...], "next_cursor": "..." | null }`. Pass the cursor back verbatim
as `?cursor=`; a `limit` above the maximum is lowered, not rejected; there is no total count, so
never invent "page 3 of 12" — show "more" and the loaded count. Filters and sorts are allowlisted
by the contract: offer only those, keep them in the URL, and send them to the server as query
parameters — filtering client-side what the contract filters downloads data nobody sees. When
appending a page, drop rows whose id is already shown; a row can move while you page. With TanStack Query:
`useInfiniteQuery({ initialPageParam: undefined, getNextPageParam: (last) => last.next_cursor ?? undefined })`.
([infinite queries](https://tanstack.com/query/latest/docs/framework/react/guides/infinite-queries))

## Writes

Send one `Idempotency-Key` per user intent: mint a UUID when the user starts the action, reuse
it on every retry of that action, and mint a new one for a new intent. A payload the user edits —
fixing a field after a `422` — is a new intent with a new key, because the contract answers a key
reused with a different payload with `422`. The contract answers `409` with `Retry-After` while
the first request with that key is still in flight — keep waiting and poll, never re-send with a
fresh key; a `409` without `Retry-After` is a conflict to show, not to wait out. Start
from [the idempotent-write helper](../assets/idempotent-write.ts) and
[its test](../assets/idempotent-write.test.ts), written in with the editor tools like the
problem helper: `newIntentKey()` when the action starts,
`sendIdempotent()` for every send, which waits out the `409` with the same key. Disable the
control while the write is pending. Mutations do not retry by default; keep it that way unless
replay is proven safe. Long-running work answers `202` with a status resource: poll it with
backoff, show progress, and let the user leave the page. A bulk action reports each item's
outcome, including unknown.

## Retries, rate limits and freshness

Queries retry three times with backoff by default; honour `Retry-After` on `429` and `503`, skip
non-retryable statuses, and keep one retry owner — the query layer — so the client wrapper never
retries on its own. Show data age from the query's `dataUpdatedAt` ("updated 12 s ago") and a
stale or disconnected state when refetching fails. Log a `Deprecation` or `Sunset` header once
per session so the migration is visible. The UI never calls `/health/*`; those belong to the
platform.

## Test doubles

MSW 3 mocks the contract at the network boundary (`import { http, HttpResponse } from "msw/http"`;
Node 22 or later, ESM only). Write handlers for the statuses the contract declares, including
problem bodies with a `request_id` and a two-page cursor sequence, and test that a `500`
renders its request ID, a `422` lands on the right fields, `next_cursor` loads the second page,
a filter reaches the request's query string, a retried write reuses its `Idempotency-Key`, a
`409` with `Retry-After` keeps the key and waits, and an edited payload sends a new key.
