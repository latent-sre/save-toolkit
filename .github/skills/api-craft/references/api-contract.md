# HTTP API contract

Preserve established contracts. For new APIs, choose paths, errors, pagination and identity from
consumers, the framework and operating environment; no single convention is a team-wide requirement.

## Contract changes

Describe changed operations and compatibility consequences. [Versioning](./versioning.md) covers
consumer migration; keep bounded changes out of unrelated contract migrations.

## Contract checks

| Boundary | What to settle and verify |
|---|---|
| Inputs and results | Typed, validated boundaries; explicit missing/null and invalid-input behavior; avoid leaking internal fields. |
| Errors | Consistent machine-readable errors and meaningful HTTP status codes. RFC 9457 is an option when it fits consumers. Cover validation, router and unexpected failures; redact submitted secrets and exception text. |
| Correlation | Carry the service's request/trace identity through responses, failures and logs; trust supplied IDs only through an established ingress policy. |
| Collections | Bound results and allowlist filters/sorts. Choose pagination for the access pattern; cursor traversal needs deterministic ordering with a unique tie-breaker. |
| Identity | Reuse the application's authentication/session integration, including corporate SSO where established. Internal network access grants no permissions. Enforce object/tenant authorization and fail closed when verification is unavailable. Authentication changes get independent review. |
| Webhook receiver | Use the existing/provider-supported verifier before acceptance or effects. Preserve original bytes for raw-body signatures and enforce the provider's signed-timestamp policy where supplied. Freshness does not deduplicate delivery; use authenticated event identity with [Background work](./background-work.md). |
| Writes | Choose native idempotence, preconditions or replay keys for the effect; follow [API writes](./api-writes.md). Accepted background work needs durable ownership and observable completion under [Background work](./background-work.md). |
| Browser boundary | Apply CSRF and origin/host checks for the actual browser/session model; scope CORS deliberately. Loopback tools reject untrusted hosts. |
| Dependencies and streams | Bound waits, buffers and reconnects; define degraded versus failed responses. Choose polling, SSE or bidirectional transport from the interaction. |

Document the consumer-facing contract. For a service using OpenAPI, follow
[OpenAPI](./openapi.md); schema and client tooling must agree with actual responses.

## Operation and verification

Bind to the deployment interface and configured port; desktop-only tools bind loopback. Separate
process health from readiness where traffic withdrawal helps; choose probe paths, access and
checks with the host. Health output must not reveal secrets or dependency internals.

For operational endpoints, bound targets and preserve actor attribution.
Test the real handler chain for success, invalid inputs, denied and intended access, dependency
failure and applicable retry/concurrency cases.

For signed webhooks, test missing/invalid signatures, a changed body with the original signature,
and stale timestamps where supported: rejection creates no accepted work. Authentic redelivery
must preserve one business effect under the provider's event-identity contract.
