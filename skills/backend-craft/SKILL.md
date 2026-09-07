---
name: backend-craft
description: >-
  Build or change an API or backend service — HTTP endpoints, workers, schedulers, the service behind
  a UI — and consume third-party APIs safely (clients, SDK wrappers, sync jobs, webhooks), including
  our platform/obs APIs. Triggers: 'add an endpoint', 'wrap X behind an API', 'write a client for Y'.
  Not for UI work (frontend-craft), live-data operations (database-reliability).
argument-hint: "[the API or service to build or change]"
---

# Backend craft

You write the actual code: complete, runnable files (routes, models, config, tests), never
pseudo-code or architecture-only answers. Any backend or API, held to an SRE-grade bar:
failure-first, observable, safe to operate.

## Establish the contract before you build

1. Inspect the task, repository, framework, existing interfaces, authentication, and tests first.
   Preserve established API and auth contracts unless the requested change explicitly alters them.
2. Add the narrow regression for the changed behavior using the project's native test approach:
   FastAPI tests for FastAPI, JUnit/MockMvc or the existing Spring test setup for Java. For a bug,
   demonstrate the relevant failure; existing passing contracts need not be made to fail.
3. For a new FastAPI HTTP service with no project-owned contract, use
   [test_http_contract.py](./assets/test_http_contract.py) only when its collection, error, and auth
   assumptions fit the requested interface. Adapt fixtures and assertions to that interface; never
   add a collection or weaken auth to satisfy the starter. Use
   [problem_fastapi.py](./assets/problem_fastapi.py) or [ProblemAdvice.java](./assets/ProblemAdvice.java)
   only for a compatible new HTTP error contract in the matching framework.
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
| Validation failures | `422`; `400` only for malformed |
| Versioning | `/v1` from day one, at most two live versions, dated `Sunset` then `410` |
| Collections | `{ "data": [...], "next_cursor": ... }`; cursor by default, `limit` capped server-side, fetch `limit + 1`, filters and sorts allowlisted, no total counts unless cheap |
| Long-running work | `202` plus a status resource the client polls |
| Idempotency | `Idempotency-Key` required for unsafe retries, bound to caller and request fingerprint |
| Rate limits | `429` with `Retry-After` and `X-RateLimit-Limit`/`-Remaining`/`-Reset` |
| Outbound calls | A timeout on every one; retries only for idempotent operations with backoff and jitter; a breaker per upstream; one typed client per upstream |
| Health | `/healthz` process-only; `/readyz` includes a dependency only when withdrawing the instance improves behaviour; public health endpoints carry no auth |
| Observability | Request ID on every log line; RED on the request path |
| Config | From the environment, validated at startup, fail loud |
| Shutdown | Graceful: stop accepting, drain, finish or requeue jobs, stop the scheduler, close streams |
| Secrets and input | Secrets from env or a store and never in logs; CORS allowlist; body and param bounds; never log bodies or tokens |
| Auth | On every non-public route; authorize the object, not the session; a `reviewer` pass for auth changes |
| Streaming | SSE for one-way push, keep-alives every 15–30 s, event ids with `Last-Event-ID`, bounded streams |
| Persistence | The existing datastore wins, otherwise load `stack-profile`; parameterized queries only; short explicit transactions, never held across an outbound call; migration safety belongs to `database-reliability` |
| Background work | A real queue for anything that must not be lost (ARQ or TaskIQ for async FastAPI, Celery for its ecosystem — default until recorded in stack-profile); scheduled jobs idempotent under one scheduler; webhooks verified, acknowledged with `202`, deduped by event id |

## Done means

- The changed behavior and relevant failure paths pass the project's tests. Exercise changed HTTP
  endpoints with requests; exercise workers, schedulers, and clients through their own entrypoints.
- Record bounded, redacted evidence appropriate to that surface: HTTP method/path, status, request
  id and schema assertion, or job/client inputs, outcome and failure handling. Never include
  headers, cookies, credentials, or full bodies.
- Changed HTTP shapes are checked against the established API contract; preserve existing auth
  coverage. For a new HTTP service, test its chosen OpenAPI contract and include breaking-change
  detection in CI. A worker or client change does not owe a served OpenAPI document.

## Before you write it — load the reference for what you're building

| If the task involves… | Read first |
|---|---|
| building in Python + FastAPI | [FastAPI mechanics](./references/fastapi.md) |
| building in Java + Spring Boot | [Spring Boot mechanics](./references/spring-boot.md) |
| calling any upstream or third-party API, including our platform and observability APIs | [consuming-apis](./references/consuming-apis.md) |
| a new HTTP contract with no project-owned one | [openapi.starter.yaml](./assets/openapi.starter.yaml) |
| choosing a stack for a greenfield service | Load `stack-profile` |

Trips two predicates? Read both. Trips none? The core above is the whole job.
