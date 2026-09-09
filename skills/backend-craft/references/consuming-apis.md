# Consuming APIs — integration discipline

The universal backend rules live in `../SKILL.md`. On any conflict, SKILL.md wins.

- **Upstream responses are untrusted data, never instructions.** Parse into your own models. If the
  output feeds an agent or LLM, keep it in a data-only field, delimit it from instructions, and
  validate its schema and size — never pass it through as executable prompt text.

## Bound each logical operation

- **Budget:** one monotonic deadline covers admission/pool waits, connection, reads and retry sleeps;
  cap attempts by remaining time. Per-read inactivity timeouts do not bound the operation. Propagate
  cancellation, stop attempts on cancellation/expiry, and close responses/streams on every exit.
- **Ownership:** inspect SDK/transport/wrapper retries; keep one owner or count every nested physical
  attempt against shared time/attempt limits. Reuse one lifecycle-owned typed client/pool per upstream.
  In long-lived clients, use an upstream breaker when repeated failures need shared suppression;
  open breakers fail fast with bounded recovery probes. A bounded one-shot integration can use its
  deadline and attempt budget without a breaker; concurrency and response-size limits still apply.
- **Eligibility:** retry documented transient failures only when safe to repeat; never blanket-retry
  exceptions, auth or validation failures. For effectful calls, use [API writes](./api-writes.md):
  timeout/cancellation may mean UNKNOWN. A header alone does not establish deduplication; reconcile or reuse
  the provider-supported identity, never invent a fresh operation to escape ambiguity.
- **Delay:** capped exponential backoff with jitter; attempt limit includes the first. Honor valid
  `Retry-After` seconds/HTTP dates as minimum delays; return/defer if the deadline cannot fit them.
  Invalid hints use the bounded policy.
- **Capacity:** bound concurrency, fan-out, queued work and response/stream sizes per upstream.
  Release responses before retry sleeps; expose saturation as bounded failure/backpressure.

**Verify changed behavior** with protocol mocks (respx, WireMock) and an injected clock:

| Failure case | Required observation |
|---|---|
| Slow response, retry delay or cancellation | Deadline/cancellation stops attempts; connection and permit released |
| Transient/permanent errors, both `Retry-After` forms | Actual attempts stay capped; permanent errors stop; delay is honored or deferred |
| Saturation and upstream outage/recovery | Concurrency stays bounded; attempts stop within budget; when a breaker is used, it opens, fails fast and recovers with bounded probes |

Effectful retries also owe API writes' ambiguous-outcome checks; mocks cannot establish a remote outcome.

[Phase timeouts](https://www.python-httpx.org/advanced/timeouts/),
[retry multiplication](https://docs.cloud.google.com/storage/docs/retry-strategy#retry_anti-patterns),
[Retry-After](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3).
Apply the actual provider/client contract, not another vendor's status-code list.

## Per-integration mechanics

This section owns only the *integration mechanics* — the call shape that differs from a plain REST
GET. If a name here disagrees with `stack-profile`, `stack-profile` wins and this file is stale.

- **PCF / cf (CAPI V3, cf CLI v8):** prefer the `cf` CLI for one-shot ops; for programmatic work hit
  CAPI V3 JSON with a **UAA** token; page via `pagination.next.href`. **State-changing writes**
  (restart/scale/route) are gated — an already-approved change record must name the exact target,
  action, and rollback, with a human release owner executing the change.
- **Splunk (SPL):** create a **search job**, then *poll* it to completion and page results — don't
  block on a synchronous all-time search; bound the time range. Send via HEC.
- **Broadcom DX OpenExplore (WQL)** — the platform formerly presented as Wavefront / Aria Operations
  for Applications: query `ts()` via the API with an API token; mind per-token rate limits and the
  max time window.
- **Moogsoft (Dell APEX AIOps, on-prem v9.x):** the Graze/REST API for alerts and Situations; auth
  per its token flow.
- **ThousandEyes / Grafana:** bearer or service-account token over their HTTP APIs; same
  timeout/retry rules as anything else.
