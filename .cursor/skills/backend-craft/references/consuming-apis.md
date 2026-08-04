# Consuming APIs — integration discipline

Read this before writing any code that calls another service: a client, an SDK wrapper, a sync job,
or a webhook consumer. Much of a backend's job is being someone else's client; take that as
seriously as being a server.

The universal backend rules live in `skills/backend-craft/SKILL.md`. On any conflict, SKILL.md wins.

## Consuming APIs (integration discipline)

Much of this service's job is calling *other* APIs — take being a good client as seriously as being a good server.

- **One typed client per upstream**, configured once — base URL, auth, timeout, retry policy in a single place; never scatter ad-hoc calls (a shared `httpx.AsyncClient`, not a new session per call).
- **Auth to upstreams**: API key / bearer / OAuth2 client-credentials — **cache the token and refresh before expiry**, never re-auth per call.
- **Respect their limits**: honor `429` + `Retry-After`, self-throttle to their quota, backoff + jitter on retryable failures. Never be the reason an upstream rate-limits you.
- **Circuit breaker per upstream**: after N consecutive failures, open the circuit and fail fast instead of hammering a down dependency; half-open to probe recovery. Retries alone don't give you this.
- **Consume pagination fully**: follow cursor / next-links to completion, bounded — never assume one page.
- **Upstream responses are untrusted**: parse into *your own* models, tolerate schema drift (ignore unknown fields, fail loudly only on a missing critical one), and never leak a raw upstream error to your caller — translate it into your one error shape.
- **Cache upstream data** with a TTL (stale-while-revalidate) — fewer calls, and you ride out upstream blips.
- **Idempotency for side-effecting calls** — an idempotency key or dedup so a retry doesn't double-submit.
- **Observe every upstream call**: log target, latency, status; **propagate your request ID downstream** (`X-Request-ID`) so one trace spans services; RED metrics per upstream; reflect a hard-down critical dependency in `/readyz`.

## Every external call
- **Always set timeouts** (connect + read). A hung dependency must not hang your tool.
- **Retry only the safe ones** — idempotent reads and transient failures (`429`, `5xx`, connection
  resets) with **exponential backoff + jitter** and a cap. Never blind-retry a non-idempotent write.
- **Honor rate limits.** Respect `429` + `Retry-After`; throttle and bound concurrency. Hammering the
  platform pages the **platform team** — not your blast radius; preserve the loaded repository's platform boundary.
- **Follow pagination** (cursor/`next` links); cap total pulled and stream rather than load-all — these
  APIs return huge result sets.
- **Treat responses as data, not truth or instructions.** Parse defensively; validate shape; an empty/
  partial result is normal. If output feeds an agent/LLM, keep it in a data-only field, delimit it from instructions, validate its schema and size, and never pass it through as executable prompt text.

## Per-integration notes (cite current product names)
- **PCF / cf (CAPI V3, cf CLI v8):** prefer the `cf` CLI for one-shot ops; for programmatic work hit
  CAPI V3 JSON with a **UAA** token; page via `pagination.next.href`. **State-changing writes**
  (restart/scale/route) are gated — an already-approved change record must name the exact target, action, and rollback, with a human release owner executing the change.
- **Splunk (SPL):** create a **search job**, then *poll* it to completion and page results — don't block
  on a synchronous all-time search; bound the time range. Send via HEC.
- **Wavefront (Aria Operations for Applications, WQL):** query `ts()` via the API with an API token;
  mind per-token rate limits and the max time window.
- **Moogsoft (on-prem v9.x):** the Graze/REST API for alerts/Situations; auth per its token flow.
- **ThousandEyes / Grafana:** bearer/service-account token over their HTTP APIs; same timeout/retry rules.

## Make writes safe
**Check current state before acting**, make the write idempotent (a retried "restart" or "scale to 3"
must converge, not stack), and **separate decision from effect** so `--dry-run` is trivial and the logic
is testable without side effects. Version operation/state contracts and keep retry behavior explicit. Cache slow/stable lookups (app GUIDs, metric
metadata) with a TTL.

## Observe your own tool
Emit structured logs, RED metrics, and traces with approved request, operation, and correlation fields;
fail loud with a clear message naming which dependency failed and what you tried.
