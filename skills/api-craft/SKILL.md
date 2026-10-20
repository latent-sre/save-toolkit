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

Use the service's consumer, error/page/version and identity contracts. HTTP clients keep their
native entrypoint.

Load `stack-profile` for framework, runtime and datastore choices. Include persistence and
asynchronous work where they fulfill the API contract.

For new APIs or scoped upgrades, verify the latest compatible stable releases and recommended APIs
against official docs and upstream evidence. Prefer supported native capabilities; explain older
version constraints or prerelease choices and keep dependency selection reproducible.

Parameterize queries and keep transactions short; no transaction spans an outbound call.

## Load for the changed boundary

Use every matching row and no others.

| Boundary | Guidance |
|---|---|
| HTTP API, including a webhook receiver | [API contract](./references/api-contract.md) |
| OpenAPI document, generated client or schema checks | [OpenAPI](./references/openapi.md) |
| FastAPI | [FastAPI](./references/fastapi.md) |
| Go HTTP server; Huma only when selected | [Go](./references/go.md) |
| Retryable or concurrent API write, including remote effects | [API writes](./references/api-writes.md) |
| HTTP client or upstream API integration | [Consuming APIs](./references/consuming-apis.md) |
| Durable work accepted by an API, including asynchronous webhook processing | [Background work](./references/background-work.md) |
