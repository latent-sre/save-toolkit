# HTTP API contract

Preserve the service's established contract. For a new API, choose conventions from its consumers,
framework and operating environment; a particular path prefix, error envelope, pagination shape,
identity protocol or test package is not a universal team requirement.

## Contract changes

Describe changed operations and compatibility consequences. Reuse approval already covering the
work; return consequential unresolved decisions or breaking changes to the caller.
[Versioning](./versioning.md) covers consumer migration. A bounded change updates existing
documentation and checks without silently adopting a service-wide migration.

## Design reminders

| Boundary | What to settle and verify |
|---|---|
| Inputs and results | Typed, validated boundaries; explicit missing/null and invalid-input behavior; avoid leaking internal fields. |
| Errors | Consistent machine-readable errors and meaningful HTTP status codes. RFC 9457 is an option when it fits consumers. Cover validation, router and unexpected failures; redact submitted secrets and exception text. |
| Correlation | Carry the service's request/trace identity through responses, failures and logs; trust supplied IDs only through an established ingress policy. |
| Collections | Bound results and allowlist filters/sorts. Choose pagination for the access pattern; cursor traversal needs deterministic ordering with a unique tie-breaker. |
| Identity | Reuse the application's authentication/session integration, including corporate SSO where established. Internal network access grants no permissions. Enforce object/tenant authorization and fail closed when verification is unavailable. Authentication changes get independent review. |
| Writes | Choose native idempotence, preconditions or replay keys for the effect; follow [API writes](./api-writes.md). Accepted background work needs durable ownership and observable completion under [Background work](./background-work.md). |
| Browser boundary | Apply CSRF and origin/host checks for the actual browser/session model; scope CORS deliberately. Loopback tools reject untrusted hosts. |
| Dependencies and streams | Bound waits, buffers and reconnects; define degraded versus failed responses. Choose polling, SSE or bidirectional transport from the interaction. |

Document the consumer-facing contract. For a service using OpenAPI, follow
[OpenAPI](./openapi.md); schema and client tooling must agree with actual responses.

## Operation and verification

Bind to the intended deployment interface and configured port. Separate process health from
readiness where traffic withdrawal helps; choose probe paths, access and checks with the host.
Health output must not reveal secrets or dependency internals.

For operational actions, bound targets and preserve actor attribution, recovery and the caller's
change authority; use preview/dry run or plan/apply where effects warrant it.
Test through the real handler chain: normal results, invalid inputs, permission denial and intended
access, dependency failure, and applicable retry/concurrency cases. Report contract changes,
compatibility evidence and unavailable checks.
