---
name: backend-craft
description: >-
  Build or change the team's backend services — FastAPI or Huma (Go) HTTP APIs, workers, schedulers,
  webhook receivers, and clients for platform and vendor APIs. Owns the house API contract (RFC 9457
  problems, cursor pages, Idempotency-Key writes, /v1) and its OpenAPI gates (committed document,
  drift tests, Schemathesis, oasdiff), plus the service's operating surface. Triggers: 'add an
  endpoint', 'build an API or service for', 'wrap X behind an API', 'write a client for Y'. Not for
  UI work (frontend-craft) or live database operations (database-reliability).
argument-hint: "[the API or service to build or change]"
---

# Backend craft

Build the team's backend services: complete, runnable code — handlers, models, configuration,
tests and the committed OpenAPI document — that the team's UIs and automation generate clients
from, and that an SRE can operate during an incident. Load `stack-profile` first to tell code the
team authors from services it only supports. The repository's framework, contract and conventions
win over every default here; the owner decisions apply wherever the repository has not chosen.

## Owner decisions

| Area | Decision |
|---|---|
| Frameworks | A new HTTP service is FastAPI (Python) or Huma on `net/http` (Go), code-first: the framework generates the OpenAPI document from typed handlers. An existing service keeps its framework, generator and contract. |
| Contract gates | Every HTTP service, new or existing, commits its generated `openapi.json` at the repository root; a service without one gains it, with its document tests, in the first change to its API, because the UI's generated client and oasdiff read only that file. Its tests fail when the code and the document differ, when an operation breaks a house rule, and when Schemathesis finds a response the document does not allow; CI fails a breaking change with `oasdiff`. |
| OpenAPI version | Emit 3.1, valid as 3.2. A 3.2-only feature waits until the tools that write and read the document support it. |
| Shared shapes | Owned here and consumed by `frontend-craft`: RFC 9457 problems with `request_id` and `errors[]`, cursor pages, `Idempotency-Key` writes. |
| Versioning | Every API path starts with `/v1`; a breaking change follows [versioning](./references/versioning.md). |
| Actions | Services perform operational actions (restart, scale, silence, purge). An endpoint that changes something outside the service offers a dry run, bounds how many targets one call touches, and logs who acted and why. |
| Runtimes | PCF, Linux hosts under systemd, and Windows desktops as localhost tools; Cloud Run as the candidate GCP landing runtime, which `stack-profile` records as decision-pending. |
| Data | PostgreSQL and SQL Server, connected directly. |

## Before you build

1. **Read the repository**: framework, committed or served OpenAPI document, authentication,
   tests, how it runs and where it deploys. Preserve the existing contract unless the request
   changes it; an existing service keeps its own established error shape.
2. **Settle the forks of a new service** from the request and the repository. Ask the caller, in
   one round with your default for each, only what neither settles:

   | Fork | Default |
   |---|---|
   | Python or Go | The language of the services it sits beside |
   | Who calls it | The team's UI, shipped with it, and scripts |
   | Where it runs | Decides listening, health and shutdown below |
   | Datastore | The one its neighbours use |
   | Does it change anything outside itself | Then the Actions decision applies |

3. **Install the house contract first.** Read each starter file for the language and write it into
   the service with your editor tools, adapting its resource and keeping every assertion. They are
   templates to read: a shell `cp` from the plugin directory is refused.
   - FastAPI: [house.py](./assets/fastapi/house.py), [test_house.py](./assets/fastapi/test_house.py),
     [test_openapi_document.py](./assets/fastapi/test_openapi_document.py),
     [test_schemathesis.py](./assets/fastapi/test_schemathesis.py), with
     [main.py](./assets/fastapi/main.py) as the example service.
   - Go: [house.go](./assets/go/house.go), [house_test.go](./assets/go/house_test.go),
     [openapi_test.go](./assets/go/openapi_test.go),
     [schemathesis_test.go](./assets/go/schemathesis_test.go), with [main.go](./assets/go/main.go)
     and [things.go](./assets/go/things.go) as the example service.
   - CI: [api-contract-fastapi.yml](./assets/ci/api-contract-fastapi.yml) or
     [api-contract-go.yml](./assets/ci/api-contract-go.yml).

   In an existing service, keep its own error and auth code and adapt the contract tests to what
   it already does. Add the document tests and the generated `openapi.json` even when the service
   has neither yet — committing the document changes no behaviour, and without it a contract change
   is invisible — with its existing operations listed as predating the house rules, which then
   govern only what you add.
4. **Change the contract before the code.** Write the route signatures and models, regenerate the
   document (`UPDATE_OPENAPI=1 python -m pytest test_openapi_document.py`, or
   `go test -run TestOpenAPIDocument -update`), and read its diff: that diff is the API change.
   A breaking change stops for the caller's approval before you implement it.
5. **Implement, then run every test**: the contract tests, the document tests and Schemathesis.

## House contract

The starters implement and test the errors, status codes, request ID, collections, document,
authentication, and browser and host safety rows; the other rows are yours to build and test.

| Decision | Rule |
|---|---|
| Errors | Every non-2xx answer — validation, unknown routes and methods, authentication, unhandled errors — is `application/problem+json` with `type`, `title`, `status`, `request_id`, optional `detail`, and for invalid input `errors[]` of `{loc, msg}`. A status-only error is `type: "about:blank"` with the status phrase; a domain error the client acts on gets its own stable `type` URI. Never echo the submitted value or exception text. |
| Status codes | `422` for well-formed input with invalid values; `400` only for unparseable syntax. A value the document allows never gets a 422: declare the real constraint (pattern, enum, bounds) so the document and the service agree. |
| Request ID | Generated per request, or read from a header only a trusted ingress overwrites; echoed as `X-Request-ID`, in every problem and on every log line. |
| Collections | `{ "data": [...], "next_cursor": "..." \| null }` with an opaque cursor declared by its pattern; a `limit` above the maximum is lowered, not rejected; fetch `limit + 1` to know whether more exist; a deterministic order with a unique tie-breaker; allowlisted filters and sorts; no total count unless it is cheap. |
| Document | Each `operationId` a unique lowerCamel name; named schemas (`ThingPage`, never `Page_Thing_`); every operation under `/v1` with bearer security unless deliberately public. |
| Authentication | Every operation authenticated unless listed public; `401` with `WWW-Authenticate` for a missing or bad token; `503`, not `401`, when the verifier itself fails. Authorize the object in the handler: an object the caller may not read answers `404`. Authentication changes get a `reviewer` pass. |
| Writes | Before a retryable or concurrent write, read [API writes](./references/api-writes.md); it owns `Idempotency-Key`. |
| Long-running work | `202` with a status resource the client polls; durable jobs, schedulers and webhook receivers follow [background work](./references/background-work.md). |
| Rate limits | `429` with `Retry-After`, always. |
| Outbound calls | One deadline per logical operation; retry only documented transient failures of idempotent calls; one typed client per upstream ([consuming APIs](./references/consuming-apis.md)). |
| Dependency failure | Fail fast, never hang or drop data: an upstream that only enriches marks its field unavailable; an essential one answers `502` for a bad answer or `504` for a timeout. |
| Browser and host safety | Refuse cross-site writes (`Sec-Fetch-Site`, else `Origin` against `Host`); a service bound to loopback refuses a non-loopback `Host`; CORS only from an allowlist. |
| Streaming | Server-Sent Events for one-way push: event IDs with `Last-Event-ID`, a keep-alive comment about every 15 s, bounded streams. |
| Persistence | The existing datastore wins; parameterized queries only; short explicit transactions, never held across an outbound call; a migration on a table holding data goes to `database-reliability`. |

## Operating surface

| Concern | Rule |
|---|---|
| Configuration | From the environment, read once and validated at startup; an invalid value stops the process. |
| Listening | `$PORT` on all interfaces when the platform sets it (PCF, Cloud Run); otherwise `127.0.0.1`. A desktop or host tool never listens beyond loopback by default. |
| Health | `/health/live` is process-only; `/health/ready` includes a dependency only when withdrawing the instance helps. Both stay outside the document and authentication, and no health path ends in `z`. PCF: `health-check-type: http` on `/health/live` and `readiness-health-check-type: http` on `/health/ready`; Cloud Run: an HTTP liveness probe on `/health/live`. |
| Shutdown | On SIGTERM or Ctrl+C: stop accepting, drain, close clients, and finish or requeue jobs. PCF and Cloud Run send SIGKILL 10 s after SIGTERM; a closed Windows console allows 5 s. |
| Logs | Structured; one line per request with method, route, status, duration and `request_id`; never secrets, tokens, cookies or bodies. |
| Secrets | From the environment or a secret store; never in code, logs or problem bodies. |

## Done means

- Every test passes, including the document tests and Schemathesis, and `openapi.json` exists at
  the repository root and matches the code.
- Your report has a **Contract change** heading: operations added, changed or removed, and whether
  oasdiff calls any of it breaking, or `none`.
- Changed endpoints were exercised through the running app, and workers, schedulers and clients
  through their own entrypoints. Record bounded, redacted evidence: method and path, status,
  request ID and the schema assertion, or job inputs, outcome and failure handling. Never record
  credentials, cookies or full bodies.
- For an item or write route, a test shows an authenticated caller without permission for the
  object is refused and the intended owner, shared or administrative access succeeds.

## Read before you build

| If the task involves… | Read first |
|---|---|
| any HTTP contract change, the committed document, client generation, CI gates or OpenAPI 3.2 | [OpenAPI](./references/openapi.md) |
| a change oasdiff calls breaking | [Versioning](./references/versioning.md) |
| Python and FastAPI | [FastAPI](./references/fastapi.md); load `python-craft` for language choices |
| Go and Huma | [Go](./references/go.md) |
| a retryable or concurrent write | [API writes](./references/api-writes.md), with [write acceptance tests](./assets/test_api_write_contract.py) |
| calling any upstream or third-party API, including our platform and observability APIs | [Consuming APIs](./references/consuming-apis.md) |
| durable jobs, schedulers or webhook receivers | [Background work](./references/background-work.md) |
| a schema migration on a table that holds data | Load `database-reliability`; running the migration stays with the human owner |
| RED metrics or traces | Load `obs-pipeline` |

Trips two rows? Read both. Trips none? The sections above are the whole job.
