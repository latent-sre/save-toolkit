---
name: backend-craft
description: >-
  Build complete backend tools and services, or change existing APIs, workers, schedulers,
  webhook receivers, storage and upstream clients. Triggers: 'build a service for X', 'add an
  endpoint', 'write a client for Y', 'build a worker'. Use frontend-craft for UI work and
  database-reliability for live database operations.
argument-hint: "[the tool, service or backend change]"
---

# Backend craft

Build internal tools and services through their real entrypoints. Load `stack-profile` for
authoring and runtime choices; inspect the repository's framework, contracts, tests and deployment
before choosing a path.

## Choose the path

| Task | Contract and starting point |
|---|---|
| New HTTP service | FastAPI (Python) or Huma on `net/http` (Go), code-first, using the house contract below. Choose the language of neighbouring services unless the request settles it. |
| Existing HTTP service | Keep its framework, generator, authentication, API contract, canonical specification format/location and equivalent checks, including for added routes, until the owner authorizes a migration. House defaults fill only undecided parts. |
| Worker, scheduler, client or storage change | Follow its native entrypoint and repository conventions. Load the relevant references below; an HTTP server, OpenAPI document and house HTTP templates are needed only if the task exposes or changes an HTTP API. |

For a new tool, settle only consequential forks the request and repository leave open: callers,
runtime, language, datastore, and external effects. Present unresolved choices together with
defaults; skip a separate brief when those decisions are already clear. Build one working path
through the real integration, then complete the requested scope, configuration and failure handling.

## HTTP changes

1. Read [OpenAPI](./references/openapi.md). A new HTTP service commits `openapi.json` at its
   **service root** (the module or `pyproject.toml` root, possibly below the repository root).
   Code generation, consumers and CI use that same path. Deliver CI configuration for the
   contract gates below, including for a local-only service. Existing services keep their canonical
   specification and checks; missing service-wide documentation or CI adoption is a separately
   scoped task, not a prerequisite for a bounded API change.
2. Describe the contract change before handler implementation: review the canonical document
   diff when one exists; otherwise state the changed routes, inputs, outputs and compatibility
   assumptions. For new services, write route signatures/models and generate the document first.
   Use existing caller approval when it covers the contract; otherwise present the concrete
   change for approval. A breaking change follows [versioning](./references/versioning.md).
3. New services verify document drift, contract rules, Schemathesis responses and `oasdiff`
   against the base document. Existing services run their applicable checks and focused tests for changed
   behaviour; disclose missing document or compatibility evidence.

### House contract for new HTTP services

These shapes are owned here and consumed by `frontend-craft`.

| Concern | Rule |
|---|---|
| Errors | HTTP errors (`4xx`/`5xx`), including validation, unknown routes/methods, authentication and unhandled failures, use `application/problem+json`: `type`, `title`, `status`, `request_id`, optional `detail`, and input errors as `errors[]` of `{loc, msg}`. Status-only errors use `about:blank` and the status phrase; actionable domain errors get a stable `type` URI. Never echo submitted values or exception text. Redirects and `304` keep their HTTP semantics. |
| Status codes | `400` for unparseable syntax; `422` for well-formed input with invalid values. Declare input constraints in the schema. Stateful rejection, such as an `Idempotency-Key` reused with different intent, can reject schema-valid input: document and test that response rather than inventing a schema constraint. |
| Request ID | Generate per request, or accept only from a header a trusted ingress overwrites; echo as `X-Request-ID`, in problems and request logs. |
| Collections | `{ "data": [...], "next_cursor": "..." \| null }`; opaque cursor with a declared pattern, clamped maximum `limit`, `limit + 1` fetch, deterministic order with a unique tie-breaker, allowlisted filters/sorts. Include a total only when cheap. |
| Document | Emit OpenAPI 3.1, valid as 3.2; use 3.2-only features only when producer and consumers support them. Unique lowerCamel `operationId`, named schemas (`ThingPage`), `/v1` paths and the actual authentication scheme, with explicit unauthenticated exceptions. |
| Authentication | Shared internal web tools use the application's corporate SSO integration; internal network access grants no permissions. Preserve its session/token contract rather than inventing a provider or trusting caller-supplied identity headers. Missing/invalid identity: `401` (`WWW-Authenticate` for bearer); verifier failure: `503`. Authorize each object; unreadable objects answer `404`. Authentication changes get a `reviewer` pass. |
| Writes | Retryable or concurrent writes follow [API writes](./references/api-writes.md). Long-running work returns `202` with a pollable status resource and follows [background work](./references/background-work.md). |
| Operational actions | An endpoint changing external state offers dry run and plan-then-apply, bounds targets per call, and logs who acted and why. |
| Dependency failure | An optional enrichment becomes explicitly unavailable; an essential upstream's bad answer is `502`, timeout `504`. Rate limits return `429` with `Retry-After`. |
| Browser and host safety | Refuse cross-site writes (`Sec-Fetch-Site`, else `Origin` against `Host`); loopback services refuse non-loopback `Host`; CORS uses an allowlist. |
| Streaming | One-way push uses Server-Sent Events: IDs with `Last-Event-ID`, keep-alive comments about every 15 s, bounded streams. |

## Runtime and persistence

The runtime targets are PCF, Cloud Run, Linux hosts under systemd, and Windows desktop tools;
`stack-profile` distinguishes current deployments from approved targets.

| Concern | Rule |
|---|---|
| Configuration | Read environment settings once, validate at startup and fail on invalid values. Keep secrets out of code, logs and problem bodies. |
| Listening and health, for HTTP | Bind all interfaces on platform `$PORT` (PCF, Cloud Run), otherwise `127.0.0.1`. `/health/live` is process-only; `/health/ready` checks dependencies only when withdrawing the instance helps. Both bypass auth and the API document; no health path ends in `z`. PCF uses `health-check-type: http` on `/health/live` and `readiness-health-check-type: http` on `/health/ready`; Cloud Run uses an HTTP liveness probe on `/health/live`. |
| Shutdown | Stop intake, drain, close clients and finish or requeue jobs on SIGTERM/Ctrl+C. PCF and Cloud Run send SIGKILL after 10 s; a closed Windows console allows 5 s. |
| Logs | Structured and redacted. HTTP request records carry method, route, status, duration and `request_id`; never log tokens, cookies or bodies. |
| Persistence | Keep the existing datastore; new services connect directly to PostgreSQL or SQL Server. Parameterized queries and short explicit transactions; no transaction across an outbound call. A migration on a populated table goes to `database-reliability`. |

## Load for the changed boundary

Read only matching references and assets; use every matching row.

| Boundary | Guidance and checks |
|---|---|
| HTTP contract, document, generated client or CI | [OpenAPI](./references/openapi.md); [versioning](./references/versioning.md) if breaking |
| FastAPI | [FastAPI](./references/fastapi.md); `python-craft` for language choices |
| Huma | [Go](./references/go.md) |
| Retryable or concurrent write | [API writes](./references/api-writes.md); adapt [write acceptance tests](./assets/test_api_write_contract.py) when the create/replay contract fits |
| Upstream or vendor client | [Consuming APIs](./references/consuming-apis.md) for deadlines, retries, capacity and integration mechanics |
| Durable job, scheduler or webhook | [Background work](./references/background-work.md) |
| Populated-table migration | `database-reliability`; execution stays with the human owner |
| RED metrics or traces | `obs-pipeline` |

### Optional implementation references

Select by capability; equivalent application/framework facilities satisfy the same contract.
Keep applicable acceptance checks, adapting their fixtures to the real resource and identity
integration. Copying an example application, datastore or bearer adapter is not a requirement.
Here, public means explicitly unauthenticated, not internet-facing; shared internal tools stay
authenticated. Workers use their service identity; local CLIs keep their native execution model.

| Need | FastAPI | Go/Huma |
|---|---|---|
| Common HTTP behavior | [house.py](./assets/fastapi/house.py), [tests](./assets/fastapi/test_http_core.py) | [house.go](./assets/go/house.go), [tests](./assets/go/core_test.go) |
| Bearer adapter, only when that is the identity contract | [auth.py](./assets/fastapi/auth.py), [tests](./assets/fastapi/test_auth.py) | [auth.go](./assets/go/auth.go), [tests](./assets/go/auth_test.go) |
| Contract assertions and app-specific test setup | [checks](./assets/fastapi/contract_checks.py), [setup](./assets/fastapi/contract_app.py) | [checks](./assets/go/contract_helpers_test.go), [setup](./assets/go/example_fixture_test.go) |
| Optional sample-resource acceptance | [test_house.py](./assets/fastapi/test_house.py) | [house_test.go](./assets/go/house_test.go) |
| Document and response checks | [document](./assets/fastapi/test_openapi_document.py), [Schemathesis](./assets/fastapi/test_schemathesis.py) | [document](./assets/go/openapi_test.go), [Schemathesis](./assets/go/schemathesis_test.go) |
| CI wiring | [workflow](./assets/ci/api-contract-fastapi.yml) | [workflow](./assets/ci/api-contract-go.yml) |
| Optional composition example: settings, lifecycle and a sample resource | [main.py](./assets/fastapi/main.py) | [main.go](./assets/go/main.go), [things.go](./assets/go/things.go) |

## Acceptance

- The requested tool or change runs through its actual entrypoint, with configuration/startup,
  successful work and relevant failure/shutdown behaviour exercised. Complete the requested scope
  after the first working integration path.
- Applicable tests pass. New HTTP services meet the document and gate requirements above;
  existing services update their canonical specification when present and verify the changed
  behaviour with their applicable checks. For item/write routes, test both refusal of an
  authenticated caller without object permission and intended owner/shared/admin access.
- Report changed behaviour, commands and bounded evidence: HTTP method/path, status, request ID
  and schema assertion, or job/client inputs, outcome and failure handling. State unavailable
  checks. For HTTP changes, include **Contract change** with added/changed/removed operations (or
  `none`), compatibility results and any missing contract evidence; do not call an unrun check clean.
