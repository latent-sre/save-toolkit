---
name: backend-craft
description: >-
  Builds or changes an API or backend service — HTTP endpoints, workers, schedulers, the service
  behind a UI — and consumes third-party APIs safely (clients, SDK wrappers, sync jobs, webhooks),
  including our platform/obs APIs. Triggers: 'add an endpoint', 'wrap X behind an API', 'write a client for Y'.
  Not for UI work (frontend-craft), live-data operations (database-reliability).
argument-hint: "[the API or service to build or change]"
---

# Backend craft

Load `stack-profile` to distinguish code the team authors from services it
only supports. For authoring work, deliver complete, runnable files (routes, models, config, tests):
failure-first, observable and safe to operate.

## Establish the contract before you build

1. Inspect the task, repository, framework, existing interfaces, authentication, and tests first.
   Preserve established API and auth contracts unless the requested change explicitly alters them.
2. Add the narrow regression for the changed behavior using the project's native test approach.
   For a bug, demonstrate the relevant failure; existing passing contracts need not be made to fail.
3. For a new FastAPI HTTP service with no project-owned contract, use
   [test_http_contract.py](./assets/test_http_contract.py) only when its collection, error, and auth
   assumptions fit the requested interface. Adapt fixtures and assertions to that interface; never
   add a collection or weaken auth to satisfy the starter. Use
   [problem_fastapi.py](./assets/problem_fastapi.py) only for a compatible new FastAPI error contract.
4. Build and verify the scoped change. Workers, schedulers, and client-only tasks use their own
   execution and failure contracts; they do not require HTTP endpoints, collections, or scaffolds.

## House contract

Apply each rule to the surface being built. HTTP shapes below are defaults for new interfaces
without a project-owned contract; they do not mandate redesigning an existing service. Use the
operability and failure rules that fit a worker, scheduler, or client without adding an HTTP layer.

| Decision | Rule |
|---|---|
| API contract | For an HTTP interface, keep its OpenAPI contract current; use [openapi.starter.yaml](./assets/openapi.starter.yaml) only for a compatible new interface with no project-owned contract |
| Errors | Top-level RFC 9457 `application/problem+json` with `errors[]` and `request_id` extensions — one shape everywhere |
| Validation failures | `422` for a well-formed request with invalid values; `400` only for malformed syntax or an unparseable body |
| Versioning | `/v1` from day one, at most two live versions; announce retirement with `Deprecation` (RFC 9745) and a later `Sunset` (RFC 8594) header plus a `deprecation` link, then `410` |
| Collections | `{ "data": [...], "next_cursor": ... }`, opaque cursor, `null` on the last page; a `limit` above the maximum is lowered, not rejected; fetch `limit + 1`; allowlisted filters and sorts; no total counts unless cheap |
| Long-running work | `202` plus a status resource the client polls |
| API writes | Before retryable or concurrent writes, read [API writes](./references/api-writes.md); adapt [write acceptance tests](./assets/test_api_write_contract.py) to compatible Python contracts |
| Rate limits | `429` with `Retry-After`, always. Optional quota headers use the IETF `RateLimit-Policy`/`RateLimit` draft fields as the starter shows; `X-RateLimit-*` (`-Reset` in seconds) only for clients that already parse them |
| Outbound calls | One deadline per logical operation, not just per call; retry only documented transient failures of idempotent operations, with capped backoff, jitter and `Retry-After`; one typed client per upstream |
| Dependency failure | Fail fast; never hang or drop data silently. An upstream that only enriches: return the resource with that field marked unavailable. An essential one: `502` (bad answer) or `504` (timeout) problem. Document which |
| Health | `/health/live` is process-only; `/health/ready` includes a dependency only when withdrawing the instance helps; no auth; no health path ends in `z` (Cloud Run reserves some). PCF manifest: `health-check-type: http`, `health-check-http-endpoint: /health/live`, `readiness-health-check-type: http`, `readiness-health-check-http-endpoint: /health/ready`; a routeless worker uses `process`. Cloud Run: HTTP liveness probe on `/health/live`. Never point liveness at a dependency |
| Observability | A request ID on every log line and problem body, echoed as `X-Request-ID`: generated, or read from a header only a trusted ingress overwrites (on PCF, Gorouter's `X-Vcap-Request-Id`, when nothing bypasses Gorouter). RED on the request path |
| Config | From the environment, validated at startup, fail loud |
| Shutdown | Graceful: stop accepting, drain, stop the scheduler, close streams, and finish or requeue jobs within the platform grace period (PCF and Cloud Run: 10 s from SIGTERM to SIGKILL by default) |
| Secrets and input | Secrets from env or a store; CORS allowlist; body and param bounds; never log secrets, bodies or tokens |
| Auth | On every non-public route; authorize the object, not the session; a `reviewer` pass for auth changes |
| Streaming | SSE for one-way push, a keep-alive comment about every 15 s, event ids with `Last-Event-ID`, bounded streams |
| Persistence | The existing datastore wins, otherwise load `stack-profile`; parameterized queries only; short explicit transactions, never held across an outbound call; migration safety belongs to `database-reliability` |
| Background work | Before durable jobs, schedulers, or webhooks, read [background work](./references/background-work.md). Answer `202`, or the provider's required code, while work is pending, even if a record exists; persist everything still owed, enrichment included, as pending work resumed on startup: an in-memory task dies with its process, and a sender given a 2xx won't redeliver |

## Done means

- Exercise changed HTTP endpoints with requests, and workers, schedulers, and clients through their
  own entrypoints. Record bounded, redacted evidence for that surface: HTTP method/path, status,
  request id and schema assertion, or job/client inputs, outcome and failure handling. Keep only allowlisted
  protocol headers such as `Retry-After`; never credentials, cookies or full bodies.
- Changed HTTP shapes are checked against the established API contract; preserve existing auth
  coverage. For an item or write route, test that an authenticated principal without permission
  for the object is refused, and that intended owner, shared, or administrative access succeeds.
  For a new HTTP service, test its chosen OpenAPI contract and include breaking-change detection in
  CI. A worker or client change owes no served OpenAPI document.

## Before you write it — load the reference for what you're building

| If the task involves… | Read first |
|---|---|
| writing, refactoring, or modernizing Python | Load `python-craft` for language and library choices |
| building in Python + FastAPI | [FastAPI mechanics](./references/fastapi.md) |
| calling any upstream or third-party API, including our platform and observability APIs | [consuming-apis](./references/consuming-apis.md) |
| writing or changing a schema migration on a table that holds data | Load `database-reliability` for the expand → contract design rules; running the migration stays with the human owner |
| emitting RED metrics or traces | Load `obs-pipeline` |
| request-id log correlation | `RequestIdMiddleware` in [problem_fastapi.py](./assets/problem_fastapi.py); `obs-logs` for the Gorouter `vcap_request_id` join |

Trips two predicates? Read both. Trips none? The core above is the whole job.
