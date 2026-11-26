---
name: api-craft
description: >-
  Design, build or change HTTP APIs, webhook receivers, and HTTP clients. Covers consumer
  contracts, integrations, failure behavior, and durable work accepted by an API. Triggers:
  'add an endpoint', 'build an API', 'wrap X behind an API', 'integrate an upstream API'.
  Not for standalone workers, schedulers or persistence changes (software-engineer),
  UI work (frontend-craft), or live database operations (database-reliability).
argument-hint: "[the HTTP API or integration to build or change]"
---

# API craft

Match the service's consumer, error, pagination, version, and identity contracts. Client-only
integrations keep their CLI, worker, or library entrypoint without adding an HTTP server. Follow
the repository's manifests and lockfiles for runtime and datastore choices, and verify latest
compatible stable releases against official docs for new APIs or upgrades.

## HTTP API & OpenAPI contracts

- **Breaking changes & versioning:** Keep bounded edits out of unrelated contract migrations. When
  consumers cannot migrate together, use expand → migrate → contract and verify client retirement
  evidence (`Sunset` alone is insufficient).
- **OpenAPI single source:** Edit handlers/models or the owning spec, never generated copies; regenerate
  committed schemas in CI and fail on drift (`oasdiff` / Schemathesis where used). Check operation ID
  uniqueness (`generate_unique_id_function`), generic page model names, `separate_input_output_schemas`,
  Pydantic v2 nullable-without-default fields, and OpenAPI 3.2 `itemSchema` (FastAPI streaming routes
  emit `itemSchema` inside 3.1.0 docs — verify client generators do not degrade stream events to `unknown`).
- **Response & boundary hygiene:** Exclude internal fields and exception traces from responses; carry
  correlation/trace IDs (trusting inbound IDs only per ingress policy); bound collections and enforce
  deterministic cursor tie-breakers. Desktop-only tools bind loopback and reject untrusted `Host` headers.
- **Identity & DB:** Reuse the service's existing authentication/SSO mechanism, enforce object/tenant authorization on every
  route/replay, fail closed, and send auth changes to independent review. Apply CSRF and deliberate
  CORS checks for browser clients. Keep DB queries parameterized and transactions short — never hold a
  transaction open across an outbound network call.

## Idempotent writes & concurrency

- Choose native idempotence, client-chosen IDs, preconditions (`If-Match`), or scoped `Idempotency-Key`
  replay (scoped by authenticated caller/tenant, operation, normalized payload fingerprint, target, and
  API version). Reject payload conflicts (`422`), bound in-flight `409` waits, never store secrets/cookies
  in replay records, and retain business uniqueness past key expiry.
- **Atomic local commits:** Claim the unique key and commit mutation + receipt together under DB isolation
  (in-process locks and check-then-insert fail across instances). Protect read-modify-write separately
  against stale writers, and test both sides of commit as well as crash/restart recovery.
- **Remote effects:** Cannot share a local DB transaction. Retry only within provider-documented
  idempotency windows; otherwise an interrupted call stays `UNKNOWN` until authoritative readback or
  operator reconciliation.

## Webhooks & durable background work

- **Webhook receivers:** Verify raw-body signatures and signed timestamps before accepting work;
  deduplicate authenticated deliveries by provider event ID in persistent storage (test invalid/tampered
  signatures, stale timestamps, and duplicate redelivery).
- **Accepted background work:** Persist pending work atomically with the state creating the obligation
  and resume it on startup/runtime (never `BackgroundTasks` or in-memory threads). Use transactional
  queues or an outbox (marking sent only after durable broker acceptance).
- **Queue consumers:** Commit event-ID deduplication and local effects together before acking. In Celery,
  `acks_late` alone acknowledges worker-process death; redelivery requires `task_reject_on_worker_lost`
  plus bounded retries and dead-letter states (never reset IDs to recycle poison messages). On shutdown,
  stop intake, drain within deadline, and fence stale lease owners at the write boundary.

## Consuming upstream APIs

- Validate untrusted upstream payloads into owned models (bound response size and isolate untrusted
  content as data for LLM consumers).
- **Origin & redirect binding:** Validate redirect/pagination targets against allowed origins and never
  forward credentials, cookies, or signed headers cross-origin. Enforce connection-time egress checks
  on user-supplied URLs.
- **Deadlines & retries:** Enforce one monotonic budget across pool wait, connect, read, and retry
  sleeps, and one retry owner across SDK/transport layers. Retry only transient failures of repeat-safe
  calls, honor `Retry-After` (seconds or HTTP date) within the remaining budget, release responses before
  sleeping, and bound concurrency/backpressure per upstream.

## Framework & datastore reference

For FastAPI/SQLAlchemy and Go `net/http`/DB implementation traps, read
[FastAPI and Go HTTP services](./references/fastapi.md).
