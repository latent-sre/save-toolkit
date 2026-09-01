---
name: backend-craft
description: >-
  Build or change an API or backend service — HTTP endpoints, workers, schedulers, the service behind
  a UI — and consume third-party APIs safely (clients, SDK wrappers, sync jobs, webhooks), including
  our platform/obs APIs. Triggers: 'add an endpoint', 'wrap X behind an API', 'write a client for Y'.
  Ownership map only—not a load: frontend-craft owns UI work, database-reliability owns live-data
  operations, and language-idiom owns the per-language rules.
argument-hint: "[the API or service to build or change]"
---

# Backend craft

**You write the actual code.** Complete, runnable files — routes, models, config, tests — never pseudo-code, never architecture-only answers. Make the decision, state it in one line, build it. Exception — a material fork (the answer changes what gets built: data model, auth, API surface) that can't be inferred is worth one batched question round with recommended defaults *before* building; a wrong build costs a full rebuild-and-review cycle, a question costs seconds. If the *requested* approach has a materially better alternative, recommend it in one line with the trade-off — then build what was chosen; never silently substitute your own preference.

This skill is general-purpose — any backend or API, not just ops tooling — held to an SRE-grade bar: failure-first, observable, safe to operate. The examples lean ops/home-lab; the rules are domain-neutral.

## Contract first

- The API contract (OpenAPI or equivalent) is written/generated before the frontend consumes anything; it is the single source of truth for shapes — and it is **living**: if your implementation diverges, update the contract in the same change. A stale contract is worse than none; parallel builders trust it.
- Starter contract: [openapi.starter.yaml](./assets/openapi.starter.yaml) — problem+json with
  `request_id`, cursor pagination, bearer auth, idempotency key, and a `429` carrying `Retry-After`.
- **One RFC 9457 error shape everywhere** — a client should never parse two error formats.
  Use top-level problem details, never a nested error envelope. The worked shape is in the
  **Errors — RFC 9457 problem+json** section below.
- **Serialize through explicit response models** — never return ORM objects or internal dicts directly. A response model is an allowlist: anything not declared in it (password hash, internal flag) *cannot* leak.
- `/v1` in the path from day one; breaking changes mean a new version, not a mutation. Breaking = removing or renaming a field, changing a type, or changing auth; adding fields or optional params is not. Run at most **two live versions**: announce the sunset (`Sunset` header with a date), then `410 Gone` after it — an undated deprecation never completes.
- Every list endpoint paginates from the start — cursor-based by default (offset is fine for small, bounded admin lists); retrofitting pagination is a breaking change.
- Compatibility review starts from this rule: a breaking change to a shipped contract is a principal-altitude change:
  expand → migrate → contract, with the compatibility and rollback path explicit.
  Ownership map only—not a load: the `eng-ladder` skill owns the altitude vocabulary.

### Resource modeling & HTTP semantics

- Model **nouns as resources**, with plural collections (`/incidents`,
  `/incidents/{id}/events`). Reserve verb-y paths for genuine actions that are not CRUD
  (`POST /deploys/{id}:cancel`).
- Use methods for their **semantics**: `GET` (safe, cacheable), `POST` (create/non-idempotent),
  `PUT`/`DELETE` (idempotent), and `PATCH` (partial). Never use `GET` for side effects.
- **Status codes that mean something:** `200/201/202/204`; `400` (malformed) vs `422` (valid shape, bad value) vs `409` (conflict); `401` (who are you) vs `403` (not allowed);
  `404`; `429` (rate limited, with `Retry-After`); and `503` (dependency down).
  Never `200` with an error in the body.
- **Long-running operations** return `202` + a status resource the client polls; do not block the
  request thread while a deploy, backfill, or other operation runs.

## Errors — RFC 9457 problem+json

Return one consistent `application/problem+json` shape with top-level `type` (a stable URI),
`title`, `status`, `detail`, and `instance`, plus defined extension fields such as `errors[]`
for field validation and `request_id` for log correlation. Stable types and codes are contract
surface. *[sourced: RFC 9457]*

```json
{
  "type": "https://errors.example.internal/upstream-timeout",
  "title": "Upstream timeout",
  "status": 504,
  "detail": "Grafana did not respond within 5s.",
  "instance": "/v1/incidents",
  "request_id": "req_8f3a2c"
}
```

Use that same top-level shape for validation errors, 404s, and 500s; represent each validation issue
as an `errors[]` entry.

## Collections

- **Cursor pagination** is the default: accept opaque `cursor` + capped `limit`, and return
  `next_cursor`. Offset paging drifts and scans on large or changing sets.
- **Filter and sort through allowlisted fields only.** Parameterize values; align the cursor with a
  stable indexed order; keep transaction and lock budgets bounded; never interpolate client input.
- Keep list responses envelope-consistent: `{ "data": [...], "next_cursor": ... }`.

## Resiliency (the core focus)

- **Timeouts on every outbound call** — HTTP, DB, queue — no exceptions. An unset timeout is an unbounded outage.
- **Retries with backoff + jitter, only on idempotent operations**; a retry storm is self-inflicted DDoS.
- **Fail fast on persistent dependency failure** and define degradation per dependency: what still works when the DB / upstream API / cache is down, decided deliberately.
- **Idempotency**: mutating endpoints are safe to retry — naturally idempotent or via idempotency keys.
- **Validate at the boundary** (Pydantic / zod / validator): reject bad input early with a clear error. Your own frontend is still an untrusted caller.
- Guard shared mutable state and concurrent access; make every write safe under retry (transaction boundaries live in [persistence](./references/persistence.md)).

These are the system-wide principles. The client-side mechanics for *calling other services* — retry policy, breakers, token refresh — live in [consuming APIs](./references/consuming-apis.md); don't restate them ad hoc.

## Operability

- Structured logs with a request ID on every entry — one request must be traceable end to end.
- `/healthz` answers only whether the process is alive; never make it depend on an external system.
  `/readyz` answers whether this instance should receive new traffic. Do not mirror every shared
  dependency into readiness: include one only when its loss makes this instance unable to serve and
  withdrawing the instance improves behavior rather than removing every replica at once.
- RED metrics (rate, errors, duration) on the request path.
- Config from environment, validated at startup — fail fast and loud on bad config, never limp.
- Graceful shutdown: stop accepting, drain in-flight requests, finish or re-queue the running job, stop the scheduler, close live streams — then exit.

## Security

- Secrets from env or a secret store — never in code, images, or logs.
- Explicit CORS allowlist — never `*` with credentials.
- **Rate-limit per principal and route** (token bucket) on anything exposed: return `429` + `Retry-After` and publish the budget in `X-RateLimit-Limit`/`-Remaining`/`-Reset` so well-behaved clients self-throttle instead of retrying blind.
- Require `Idempotency-Key` for unsafe retries of non-idempotent writes; bind the stored result to the caller and request fingerprint.
- Never log secrets, tokens, or full request/response bodies.
- **Bound what you accept**: request-body size caps, server-side request timeouts, and bounded query params (max page size, max array length). Inbound requests can do unbounded damage exactly like unbounded outbound calls — input *validation* itself lives under Resiliency.

## Testing & quality gate

- Unit-test pure logic; exercise changed boundaries and material failure paths. The matching
  conditional reference owns its test matrix; load only the references the task trips.
- Before "done": the service starts clean, tests pass, and the primary endpoints were exercised with **real requests** (curl/httpie). Record only a bounded, redacted evidence excerpt: method/path, status, request ID, and schema assertion. Strip Authorization headers, cookies, credentials, PII, and full bodies; keep full evidence in an access-controlled local artifact referenced by path and content hash. An API that was never called is written, not verified.

## Before you write it — load the reference for what you're building

Everything above applies to every backend task. The rules below apply only when the task involves the
thing named. Read the file **before** writing that code, not after — and name what you read in your
review packet.

| If the task involves… | Read first |
|---|---|
| endpoint/resource/status/list design or a published API change | [API surface design](./references/api-design.md) |
| choosing a stack for a greenfield service | Load `stack-profile` first, then [stack](./references/stack.md) |
| building in Python + FastAPI (the greenfield default) | [FastAPI mechanics](./references/fastapi.md) |
| building in Java + Spring Boot (the JVM default) | [Spring Boot mechanics](./references/spring-boot.md) |
| calling any upstream or third-party API | [consuming-apis](./references/consuming-apis.md) |
| a queue, a scheduled job, or an inbound webhook | [background-work](./references/background-work.md) |
| streaming to clients (SSE or WebSocket) | [live-data](./references/live-data.md) |
| a database or any persisted state | If datastore or driver is not already selected, load `stack-profile` first; then [persistence](./references/persistence.md) |
| authenticating or authorizing a caller | [auth](./references/auth.md) |

Trips two predicates? Read both. Trips none? The core above is the whole job.
