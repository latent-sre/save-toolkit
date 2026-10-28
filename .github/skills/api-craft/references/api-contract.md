# HTTP API contract

## Contract changes

Keep bounded changes out of unrelated contract migrations. Reuse approval for an incompatible
change or return the decision. When consumers cannot migrate together, agree version overlap,
retirement evidence and recovery before removing the old contract; `Sunset` alone is not retirement
evidence. Compatibility-gate exceptions need the accepted break, reason and owner.

## Contract checks

| Boundary | What to settle and verify |
|---|---|
| Response exposure | Exclude internal fields from consumer responses. |
| Errors | Use the consumer's error contract, including validation, router and unexpected failures; redact submitted secrets and exception text. RFC 9457 is optional. |
| Correlation | Carry the service's request/trace identity through responses, failures and logs; trust supplied IDs only through an established ingress policy. |
| Collections | Bound results and allowlist filters/sorts; cursor traversal needs deterministic ordering with a unique tie-breaker. |
| Identity | Reuse the application's authentication/session integration, including corporate SSO where established. Internal network access grants no permissions. Enforce object/tenant authorization and fail closed when verification is unavailable. Authentication changes get independent review. |
| Webhook receiver | Use the existing/provider-supported verifier before acceptance or effects. Preserve original bytes for raw-body signatures and enforce the provider's signed-timestamp policy where supplied. Freshness does not deduplicate delivery; use authenticated event identity with [Background work](./background-work.md). |
| Persistence | When the HTTP API uses a database, parameterize queries and keep transactions short; no transaction spans an outbound call. |
| Writes | Choose native idempotence, preconditions or replay keys for the effect; follow [API writes](./api-writes.md). Accepted background work needs durable ownership and observable completion under [Background work](./background-work.md). |
| Browser boundary | Apply CSRF and origin/host checks for the actual browser/session model; scope CORS deliberately. Loopback tools reject untrusted hosts. |
| Streams | Bound waits, buffers and reconnects; distinguish degraded from failed responses. |

For document/client checks, use [OpenAPI](./openapi.md).

## Operation and verification

Desktop-only tools bind loopback; deployed services use the configured interface/port. Health
responses must not expose secrets or dependency internals; readiness follows the host's traffic policy.

Operational endpoints bound targets and preserve actor attribution. Test access and failure paths
through the real handler chain, including middleware; cover invalid inputs and dependency failure.

For signed webhooks, test missing/invalid signatures, a changed body with the original signature,
and stale timestamps where supported: rejection creates no accepted work. Authentic redelivery
must preserve one business effect under the provider's event-identity contract.
