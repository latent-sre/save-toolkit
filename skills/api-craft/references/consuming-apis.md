# Consuming APIs

Parse untrusted upstream responses into owned models. For agent/LLM consumers, validate schema and
size and keep responses in data-only fields delimited from instructions.

## Bound each logical operation

- **Destination:** validate redirect and pagination targets against the integration's allowed
  schemes/origins before following them. Bind credentials to their intended origin (scheme, host,
  port); cross-origin links do not authorize forwarding credentials, cookies or signed requests.
  User-chosen URLs also need address/egress controls enforced at connection time, including retries
  and redirects; a hostname check followed by an unchecked DNS lookup is insufficient.
- **Deadline:** one monotonic budget covers admission/pool waits, connection, reads and retry
  sleeps. Per-read inactivity timeouts are insufficient. Stop attempts on cancellation/expiry;
  propagate cancellation and close responses/streams on every exit.
- **Retry owner:** inspect SDK/transport/wrapper retries; use one owner or count all physical
  attempts against shared time/attempt limits. Reuse a lifecycle-owned typed client/pool per
  upstream. Long-lived clients needing shared failure suppression use a breaker: fail fast while
  open, recover with bounded probes. A bounded one-shot call can use deadline/attempt limits alone.
- **Eligibility:** retry documented transient failures only when safe to repeat. Stop permanent
  validation or permission failures. Allow provider-documented token renewal and retry within the
  same attempt/deadline budget; never loop on unchanged credentials. Effectful calls follow [API writes](./api-writes.md):
  timeout/cancellation may mean UNKNOWN. A header alone does not prove deduplication; reconcile or
  reuse provider-supported identity, never create a fresh operation to escape ambiguity.
- **Delay:** capped exponential backoff with jitter; count the first attempt. Valid `Retry-After`
  seconds/HTTP dates are minimum delays; return/defer when they exceed the deadline. Invalid hints
  use the bounded policy. Release responses before sleeping.
- **Capacity:** bound concurrency, fan-out, queued work and response/stream sizes per upstream;
  expose saturation as bounded failure/backpressure.

Verify changed behaviour with protocol mocks (respx, WireMock) and an injected clock: refuse
disallowed redirects/next-page origins and out-of-scope DNS resolutions before sending credentials;
enforce budget/cancellation and release connections; cap transient retries, stop on permanent errors,
and honour or defer both `Retry-After` forms; bound concurrency and verify breaker open/half-open
recovery. Effectful retries also need API writes' ambiguous-outcome checks; mocks cannot establish
remote outcomes. Use the provider's actual contract, not another vendor's status list.
