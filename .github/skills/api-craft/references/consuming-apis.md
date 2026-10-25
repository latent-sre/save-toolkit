# Consuming APIs

Validate untrusted upstream responses into owned models. For agent/LLM consumers, also bound
response size and keep content in data-only fields, separate from instructions.

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
  upstream. Use a breaker only when shared failure suppression is needed; bound recovery probes.
- **Eligibility:** retry documented transient failures only when safe to repeat. Stop permanent
  validation or permission failures. Allow provider-documented token renewal and retry within the
  same attempt/deadline budget; never loop on unchanged credentials. Effectful calls follow [API writes](./api-writes.md):
  timeout/cancellation may mean UNKNOWN. A header alone does not prove deduplication; reconcile or
  reuse provider-supported identity, never create a fresh operation to escape ambiguity.
- **Delay:** count the first attempt in the cap; bound backoff/jitter. Valid `Retry-After`
  seconds/HTTP dates are minimum delays; return/defer when they exceed the deadline. Invalid hints
  use the bounded policy. Release responses before sleeping.
- **Capacity:** bound concurrency, fan-out, queued work and response/stream sizes per upstream;
  expose saturation as bounded failure/backpressure.

With protocol mocks and a controlled clock, verify destination refusal before credential transmission,
cancellation cleanup, shared budgets, both `Retry-After` forms and applicable breaker recovery.
Mocks cannot establish remote outcomes; verify effectful retries under [API writes](./api-writes.md).
