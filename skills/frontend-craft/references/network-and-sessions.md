# OpenAPI, requests, sessions, and live data

Read when implementing API-backed views, forms, actions, authentication, or live updates. Inspect
the service schema and existing client first. Preserve the service's authorization, error,
pagination, concurrency, and idempotency contracts; frontend technology choice does not change them.

## Typed integration and forms

Generate a compatible typed client from the service's OpenAPI schema, or maintain and verify the
project's existing typed client. Detect schema/client drift in the project's checks. Type generation
does not validate responses at runtime; validate or narrow untrusted payloads at the boundary where
the contract requires it. Preserve meaningful distinctions such as absent, null, and empty values.

Design forms around the task and use the chosen framework's suitable state and validation tools.
Map server field errors to inputs, retain entered values after recoverable errors, and keep the
server authoritative for validation and permissions. Handle conflicts without silently overwriting
someone else's changes. Do not put secret fields or unsaved drafts into URLs or telemetry.

## State identity and request ownership

Include inputs that change a response in its cache identity: service, environment, filters, time
range, and user/tenant scope where applicable. Use identifiers, never credentials. On logout or
scope change, cancel old requests, close streams, and clear or replace affected caches. Late results
from the old scope must not populate the new one.

Assign one owner for fetching, polling, reconnecting, and retrying each data need. Select freshness
and refetch triggers from the workflow. Bound retries, skip non-retryable errors, respect server
retry delays, and avoid multiplying attempts across client, cache, and transport layers. Cancel
superseded searches and prevent an older response from replacing the latest selection.

Paginate or incrementally fetch large datasets using the server contract. Row virtualization only
reduces rendering work; it does not reduce fetched data. Distinguish a failed refresh with retained
data from a successful current result, and keep unrelated regions usable during partial failure.

## Actions and uncertain outcomes

Show the target and count before destructive or bulk actions and require explicit confirmation.
Prevent duplicate submission while the request is pending. Where supported, create one idempotency
key per user intent and reuse it on retries of that intent. Do not invent an unsupported header or
assume a client-generated key alone prevents duplicate backend effects.

Represent accepted, running, succeeded, failed, and unknown outcomes according to the actual API.
A timeout after dispatch does not prove failure or make retry safe; reconcile through the service's
receipt or status API. Show per-item outcomes for partial bulk results and reconcile affected views
after completion. Optimistic updates need a safe reconciliation/rollback path and must not present
unconfirmed operational actions as completed. Frontend visibility is not backend authorization.

## Authentication and session expiry

Preserve the project's auth contract. For new corporate OIDC flows use Authorization Code with PKCE
and seek the supported review path for sensitive changes. A BFF can keep OAuth tokens on the
backend; its session cookies need Secure, HttpOnly, and SameSite settings suitable for the flow,
plus CSRF protection for state-changing cookie-authenticated requests.

If JavaScript calls the API with bearer tokens, keep access tokens in memory, never localStorage or
URLs. Use the project's auth client for renewal. Retry once after a refreshable auth failure only
when replay is safe or the original request was rejected before effects. Failed renewal returns to
sign-in without a loop; preserve drafts only through an appropriate non-sensitive mechanism.

## Live data and linked views

Choose polling, SSE, or WebSocket transport for the actual update pattern and service support.
Route updates through the same state model as initial loading. Retain stable identifiers, bound
buffers/history, and batch or throttle rendering so a busy stream does not overwhelm the workspace.
Expose freshness, paused/live mode where needed, and disconnected state. Preserve user selection,
scroll position, and investigation time range while data arrives.

On reconnect, replay from a supported cursor or resynchronize after gaps. Keep one reconnect owner
and close subscriptions on view/session end or failed authentication. Native EventSource cannot
set an Authorization header: use the supported cookie flow, or a fetch-based SSE reader that handles
authentication, event framing, reconnect, and last-event IDs. Never put tokens in stream URLs.
For cross-origin sessions, align browser credential behavior with the server's CORS policy.
