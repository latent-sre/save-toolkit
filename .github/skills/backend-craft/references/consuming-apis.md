# Consuming APIs

Parse untrusted upstream responses into owned models. For agent/LLM consumers, validate schema and
size and keep responses in data-only fields delimited from instructions.

## Bound each logical operation

- **Deadline:** one monotonic budget covers admission/pool waits, connection, reads and retry
  sleeps. Per-read inactivity timeouts are insufficient. Stop attempts on cancellation/expiry;
  propagate cancellation and close responses/streams on every exit.
- **Retry owner:** inspect SDK/transport/wrapper retries; use one owner or count all physical
  attempts against shared time/attempt limits. Reuse a lifecycle-owned typed client/pool per
  upstream. Long-lived clients needing shared failure suppression use a breaker: fail fast while
  open, recover with bounded probes. A bounded one-shot call can use deadline/attempt limits alone.
- **Eligibility:** retry documented transient failures only when safe to repeat, never arbitrary
  exceptions or auth/validation failures. Effectful calls follow [API writes](./api-writes.md):
  timeout/cancellation may mean UNKNOWN. A header alone does not prove deduplication; reconcile or
  reuse provider-supported identity, never create a fresh operation to escape ambiguity.
- **Delay:** capped exponential backoff with jitter; count the first attempt. Valid `Retry-After`
  seconds/HTTP dates are minimum delays; return/defer when they exceed the deadline. Invalid hints
  use the bounded policy. Release responses before sleeping.
- **Capacity:** bound concurrency, fan-out, queued work and response/stream sizes per upstream;
  expose saturation as bounded failure/backpressure.

Verify changed behaviour with protocol mocks (respx, WireMock) and an injected clock:

| Failure case | Required observation |
|---|---|
| Slow response, retry delay, cancellation | Budget stops attempts; connection/permit released |
| Transient/permanent errors and both `Retry-After` forms | Capped attempts; permanent errors stop; delays honoured or deferred |
| Saturation, outage and recovery | Bounded concurrency/attempts; a configured breaker opens, fails fast and recovers with bounded probes |

Effectful retries also need API writes' ambiguous-outcome checks; mocks cannot establish remote
outcomes. Use the provider's actual contract, not another vendor's status list.

[Phase timeouts](https://www.python-httpx.org/advanced/timeouts/),
[retry multiplication](https://docs.cloud.google.com/storage/docs/retry-strategy#retry_anti-patterns),
[Retry-After](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3).

## Integration mechanics

Read only the matching integration; `stack-profile` owns platform names and choices.

- **PCF (CAPI V3):** call CAPI V3 JSON using a **UAA** client-credentials token from bound/env
  secrets; never run or paste `cf oauth-token` output. Follow `pagination.next.href`. A platform
  write (restart/scale/route) requires an approved change naming exact target, action and rollback,
  executed by the human release owner.
- **Splunk:** create an SPL search job, poll completion, page results; bound the time range
  rather than synchronously searching all time. Send via HEC.
- **Broadcom DX OpenExplore (WQL)**, formerly Wavefront / Aria Operations for Applications: query
  `ts()` using an API token; bound windows and respect per-token rate limits.
- **Moogsoft Onprem (v9.x, Dell):** Graze/REST for alerts and Situations, using its token flow.
  APEX AIOps Incident Management is the renamed cloud product, not on-prem.
- **ThousandEyes:** use the v7 API in `obs-alerting`'s reference. **Grafana:** load `grafana` for
  its HTTP API and service-account tokens.
