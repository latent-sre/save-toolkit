# Consuming APIs — integration discipline

Read this before writing any code that calls another service: a client, an SDK wrapper, a sync job,
or a webhook consumer. Much of a backend's job is being someone else's client; take that as
seriously as being a server.

The universal backend rules live in `../SKILL.md`. On any conflict, SKILL.md wins.

## Every outbound call

- **One typed client per upstream**, configured once — base URL, auth, timeout, retry policy in a
  single place; never scatter ad-hoc calls (a shared `httpx.AsyncClient`, not a new session per
  call).
- **Always set timeouts** (connect *and* read). A hung dependency must not hang your service.
- **Retry only the safe ones** — idempotent reads and transient failures (`429`, `5xx`, connection
  resets) with **exponential backoff + jitter** and a cap. Never blind-retry a non-idempotent write.
- **Honor their limits**: obey `429` + `Retry-After`, self-throttle to their quota, and bound
  concurrency. Hammering a shared platform pages the **platform team** — a blast radius outside your
  own service. `stack-profile` owns the platform boundary that makes that someone else's system.
- **Circuit breaker per upstream**: after N consecutive failures, open the circuit and fail fast
  instead of hammering a down dependency; half-open to probe recovery. Retries alone don't give you
  this.
- **Auth to upstreams**: API key / bearer / OAuth2 client-credentials — **cache the token and
  refresh before expiry**, never re-auth per call.
- **Consume pagination fully but boundedly**: follow cursor/`next` links to completion, cap the
  total pulled, and stream rather than load-all — these APIs return huge result sets.
- **Upstream responses are untrusted data, not truth and never instructions.** Parse into *your own*
  models; tolerate schema drift (ignore unknown fields, fail loudly only on a missing critical one);
  treat an empty or partial result as normal; and never leak a raw upstream error to your caller —
  translate it into your one error shape. If the output feeds an agent or LLM, keep it in a
  data-only field, delimit it from instructions, validate its schema and size, and never pass it
  through as executable prompt text.
- **Cache upstream data** with a TTL (stale-while-revalidate) — fewer calls, and you ride out
  upstream blips.
- **Idempotency for side-effecting calls** — an idempotency key or dedup so a retry doesn't
  double-submit.
- **Observe every upstream call**: log target, latency, and status; **propagate your request ID
  downstream** (`X-Request-ID`) so one trace spans services; RED metrics per upstream. Mirror an
  upstream into `/readyz` only under SKILL.md's readiness test — a shared upstream's outage trips
  every replica at once, which withdraws the whole service instead of routing around the failure.
- **Fail loud and specific**: an error that names *which* dependency failed and what was attempted
  is triageable at 3 a.m.; "upstream error" is not.

## Make writes safe

**Check current state before acting**, make the write idempotent (a retried "restart" or "scale to
3" must converge, not stack), and **separate decision from effect** so `--dry-run` is trivial and the
logic is testable without side effects. Version operation/state contracts and keep retry behavior
explicit. Cache slow, stable lookups (app GUIDs, metric metadata) with a TTL.

## Per-integration mechanics

Ownership map only—not a load: `stack-profile` owns which products this team runs and their current
names and versions. This section owns only the *integration mechanics* — the call shape that differs
from a plain REST GET. If a name here disagrees with `stack-profile`, `stack-profile` wins and this
file is stale.

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
