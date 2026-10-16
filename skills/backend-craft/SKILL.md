---
name: backend-craft
description: >-
  Build or change backend services, APIs, workers, schedulers, webhooks, and upstream clients.
  Covers service design, integration, persistence, and failure behavior. Triggers:
  'add an endpoint', 'build an API or service for', 'wrap X behind an API', 'write a client for Y'.
  Not for UI work (frontend-craft) or live database operations (database-reliability).
argument-hint: "[the API or service to build or change]"
---

# Backend craft

FastAPI is the team's established backend framework; other framework choices remain open.
Choose from the requirements, existing code, consumer contracts and operating constraints.
Load `stack-profile`; preserve the existing datastore, using PostgreSQL or SQL Server for new services.

Preserve supported behavior and identity integrations. Separate deliberate contract changes from
cleanup; resolve consequential unknowns with a recommendation. Workers and clients keep native
entrypoints; an HTTP API is added only when the task needs one.

## Engineering bar

- **Design:** cohesive responsibilities, explicit dependencies, readable control flow; abstraction
  earns its place through actual consumers or a meaningful boundary.
- **Contracts:** explicit inputs, outputs and failure semantics; stable consumer behavior and a
  compatibility path for deliberate changes.
- **Failure:** bounded work, deadlines and retry ownership; cancellation, partial effects and
  recovery handled at the real boundary.
- **Security:** validate untrusted input, enforce identity and object permissions where required,
  and keep secrets and sensitive payloads out of outputs.
- **Data:** parameterized queries, short transactions, concurrency control; no transaction across
  an outbound call.
- **Operation:** validated startup configuration, correlated structured logs, owned clients/pools/tasks,
  and drain or requeue within the deployment's shutdown deadline.

## Load for the changed boundary

Use every matching row and no others.

| Boundary | Guidance |
|---|---|
| HTTP API, including a webhook receiver | [API contract](./references/api-contract.md) |
| OpenAPI document, generated client or schema checks | [OpenAPI](./references/openapi.md) |
| Breaking API change | [Versioning](./references/versioning.md) |
| FastAPI | [FastAPI](./references/fastapi.md) |
| Go HTTP server; Huma only when selected | [Go](./references/go.md) |
| Python implementation | `python-craft` |
| Retryable or concurrent write, including remote effects | [API writes](./references/api-writes.md) |
| Upstream client | [Consuming APIs](./references/consuming-apis.md) |
| Durable job, scheduler or asynchronous webhook work | [Background work](./references/background-work.md) |
| Populated-table migration | `database-reliability`; execution stays with the human owner |
| Metrics or traces | `obs-pipeline` |

## Acceptance

Deliver the complete change through its real entrypoint. Exercise success, material failures,
authorization, concurrency and lifecycle behavior as applicable; run the project's checks.
Report the design choices that matter, observed results and remaining gaps. Distinguish
mocked behavior from verified integration.
