---
name: backend-craft
description: >-
  Build or change backend HTTP services (FastAPI or Huma), workers, schedulers, webhooks, and
  upstream clients. Owns the house API contract and service operating surface. Triggers:
  'add an endpoint', 'build an API or service for', 'wrap X behind an API', 'write a client for Y'.
  Not for UI work (frontend-craft) or live database operations (database-reliability).
argument-hint: "[the API or service to build or change]"
---

# Backend craft

Build internal tools and services through their real entrypoints. Load `stack-profile` for
authoring and runtime choices; inspect the repository's framework, contracts, tests and deployment.
Keep existing conventions unless the owner authorizes a migration. Workers and clients use their
native entrypoints; add an HTTP server or OpenAPI document only when the task exposes an HTTP API.

For a new tool, settle only consequential forks the request and repository leave open: callers,
runtime, language, datastore, and external effects. Present unresolved choices together with
defaults; skip a separate brief when those decisions are already clear. Build one working path
through the real integration, then complete the requested scope, configuration and failure handling.

## Load for the changed boundary

Read only matching references; use every matching row. A service can cross several boundaries.

| Boundary | Guidance and checks |
|---|---|
| Expose or change an HTTP API, including a webhook receiver | [API contract](./references/api-contract.md) and [OpenAPI](./references/openapi.md) |
| API document, generated client or contract CI | [OpenAPI](./references/openapi.md) |
| Breaking API change | [Versioning](./references/versioning.md) |
| FastAPI HTTP implementation | [FastAPI](./references/fastapi.md) |
| Huma HTTP implementation | [Go](./references/go.md) |
| Python implementation | `python-craft` |
| Retryable or concurrent API write, including a job's remote effects | [API writes](./references/api-writes.md) |
| Upstream or vendor client | [Consuming APIs](./references/consuming-apis.md) |
| Durable job, scheduler or asynchronous webhook work | [Background work](./references/background-work.md) |
| Populated-table migration | `database-reliability`; execution stays with the human owner |
| RED metrics or traces | `obs-pipeline` |

## Shared runtime and persistence

The runtime targets are PCF, Cloud Run, Linux hosts under systemd, and Windows desktop tools;
`stack-profile` distinguishes current deployments from approved targets. Workers use their service
identity; local CLIs keep their native execution model.

| Concern | Rule |
|---|---|
| Configuration | Read environment settings once, validate at startup and fail on invalid values. Keep secrets out of code, logs and outputs. |
| Resource ownership | Give clients, pools and background tasks a lifecycle owner that closes or drains them on shutdown. |
| Shutdown | Stop intake, drain, close clients and finish or requeue jobs on SIGTERM/Ctrl+C. PCF and Cloud Run send SIGKILL after 10 s; a closed Windows console allows 5 s. |
| Logs | Structured and redacted; never log tokens, cookies or bodies. |
| Persistence | Keep the existing datastore; new services connect directly to PostgreSQL or SQL Server. Parameterized queries and short explicit transactions; no transaction across an outbound call. A migration on a populated table goes to `database-reliability`. |

## Acceptance

- Exercise the actual entrypoint: configuration/startup, successful work and relevant
  failure/shutdown behaviour. Complete the requested scope after the first working integration.
- Applicable tests and the selected references' checks pass.
- Report changed behaviour, commands and bounded evidence: inputs, outcome and failure handling.
  State unavailable checks; do not call an unrun check clean.
