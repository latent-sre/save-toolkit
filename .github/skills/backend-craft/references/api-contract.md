# HTTP API contract

Load when exposing or changing an HTTP API, including a webhook receiver.

| Task | Contract and starting point |
|---|---|
| New HTTP service | FastAPI (Python) or Huma on `net/http` (Go), code-first, using the house contract below. Choose the language of neighbouring services unless the request settles it. |
| Existing HTTP service | Keep its framework, generator, authentication, API contract, canonical specification format/location and equivalent checks, including for added routes, until the owner authorizes a migration. House defaults fill only undecided parts. |

## Contract changes

Read [OpenAPI](./openapi.md) before HTTP implementation for document generation and
contract gates. Describe the contract diff, or changed routes, inputs, outputs and compatibility
assumptions when no document exists. Use existing caller approval when it covers the contract;
otherwise present the concrete change for approval. Breaking changes follow
[versioning](./versioning.md). Existing services keep their conventions; missing
service-wide documentation or CI adoption remains separately scoped. Report missing contract evidence.

## House contract for new HTTP services

These shapes are owned by `backend-craft` and consumed by `frontend-craft`.

| Concern | Rule |
|---|---|
| Errors | HTTP errors (`4xx`/`5xx`), including validation, unknown routes/methods, authentication and unhandled failures, use `application/problem+json`: `type`, `title`, `status`, `request_id`, optional `detail`, and input errors as `errors[]` of `{loc, msg}`. Status-only errors use `about:blank` and the status phrase; actionable domain errors get a stable `type` URI. Never echo submitted values or exception text. Redirects and `304` keep their HTTP semantics. |
| Status codes | `400` for unparseable syntax; `422` for well-formed input with invalid values. Declare input constraints in the schema. Stateful rejection, such as an `Idempotency-Key` reused with different intent, can reject schema-valid input: document and test that response rather than inventing a schema constraint. |
| Request ID | Generate per request, or accept only from a header a trusted ingress overwrites; echo as `X-Request-ID`, in problems and request logs. |
| Collections | `{ "data": [...], "next_cursor": "..." \| null }`; opaque cursor with a declared pattern, clamped maximum `limit`, `limit + 1` fetch, deterministic order with a unique tie-breaker, allowlisted filters/sorts. Include a total only when cheap. |
| Document | Emit OpenAPI 3.1, valid as 3.2; use 3.2-only features only when producer and consumers support them. Unique lowerCamel `operationId`, named schemas (`ThingPage`), `/v1` paths and the actual authentication scheme, with explicit unauthenticated exceptions. |
| Authentication | Shared internal web tools use the application's corporate SSO integration; internal network access grants no permissions. Preserve its session/token contract rather than inventing a provider or trusting caller-supplied identity headers. Missing/invalid identity: `401` (`WWW-Authenticate` for bearer); verifier failure: `503`. Authorize each object; unreadable objects answer `404`. Authentication changes get a `reviewer` pass. |
| Writes | Retryable or concurrent writes follow [API writes](./api-writes.md). Long-running work returns `202` with a pollable status resource and follows [background work](./background-work.md). |
| Operational actions | An endpoint changing external state offers dry run and plan-then-apply, bounds targets per call, and logs who acted and why. |
| Dependency failure | An optional enrichment becomes explicitly unavailable; an essential upstream's bad answer is `502`, timeout `504`. Rate limits return `429` with `Retry-After`. |
| Browser and host safety | Refuse cross-site writes (`Sec-Fetch-Site`, else `Origin` against `Host`); loopback services refuse non-loopback `Host`; CORS uses an allowlist. |
| Streaming | One-way push uses Server-Sent Events: IDs with `Last-Event-ID`, keep-alive comments about every 15 s, bounded streams. |

## HTTP operation

For new services, or undecided parts of an existing service:

| Concern | Rule |
|---|---|
| Listening and health | Bind all interfaces on platform `$PORT` (PCF, Cloud Run), otherwise `127.0.0.1`. `/health/live` is process-only; `/health/ready` checks dependencies only when withdrawing the instance helps. Both bypass auth and the API document; no health path ends in `z`. PCF uses `health-check-type: http` on `/health/live` and `readiness-health-check-type: http` on `/health/ready`; Cloud Run uses an HTTP liveness probe on `/health/live`. |
| Request logs | Carry method, route, status, duration and `request_id`; follow the shared redaction rules. |

Public means explicitly unauthenticated, not internet-facing; shared internal tools stay authenticated.

## Acceptance

- New HTTP services meet the document and gate requirements in [OpenAPI](./openapi.md);
  existing services update their canonical specification when present and verify the changed
  behaviour with applicable checks.
- For item/write routes, test both refusal of an authenticated caller without object permission
  and intended owner/shared/admin access.
- Report HTTP method/path, status, request ID and schema assertion. Include **Contract change**
  with added/changed/removed operations (or `none`), compatibility results and missing contract
  evidence; do not call an unrun check clean.
