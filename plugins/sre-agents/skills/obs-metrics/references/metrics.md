# Local metric inventory — fill in

Concrete metric names, point tags, and dashboards for the `obs-metrics` skill. Loaded on demand.

> Names and links only — no API tokens.

Every value is `[unverified]` until checked against the target tenant and telemetry contract.

## Candidate Wavefront metric names

| Concern | Metric name | Point tags |
|---|---|---|
| request rate | `<app.http.requests.count>` | `app`, `env`, `instance` |
| latency | `<app.http.requests.latency>` | `app`, `env` |
| errors | `<app.http.requests.errors>` | `app`, `env`, `status` |
| memory | `<app.container.memory.usage>` / `<...limit>` | `app`, `instance` |

## Source / tag conventions

- App identifier tag: `<app=...>` · environment tag: `<env=prod|nonprod>`
- Instance/host tag: `<instance=...>` (use to find one bad instance)

## Dashboards & alert targets

| Name | Link | What it shows |
|---|---|---|
| `<dashboard>` | `<url>` | `<SLO / golden signals>` |

## Reusable query snippets (fill in real metric names)

Record which COUNTER TYPE your request/error metrics are — it changes the correct query. Read
[WQL counter semantics](./wql.md#error-ratio-depends-on-counter-type) before choosing:

- **delta counters** → `cs()`, no `rate()`
- **cumulative counters** → `ts()` + per-series `rate()` before aggregation

*[sourced: WQL `cs()`, `rate()`, aggregation, histogram merge/percentile, and missing-data syntax;
unverified for every placeholder and target behavior]*

```text
# error % over time — DELTA counters (per-interval; units cancel). default() so "no errors" reads 0, not no-data.
100 * default(0, sum(cs(<app.http.requests.errors>, app="<app>"))) / sum(cs(<app.http.requests.count>, app="<app>"))

# error % over time — CUMULATIVE counters (must rate() first; raw division = ratio since process start)
100 * sum(rate(ts(<app.http.requests.errors>, app="<app>"))) / sum(rate(ts(<app.http.requests.count>, app="<app>")))

# TRUE request p95 — needs a HISTOGRAM. Merge instance distributions before calculating app-wide p95.
percentile(95, merge(hs(<app.http.requests.latency.m>, app="<app>")))

# worst-INSTANCE hunt — percentile across point series is fine when that is the question
percentile(95, ts(<app.http.requests.latency>, app="<app>"), instance)

# missing-data alert candidate — verify target lifecycle before use
last(1h, mcount(3m, ts(<app.http.requests.count>, app="<app>"))) = 0
```

## Mimir / Prometheus inventory

| Concern | Metric name | Labels | Type |
|---|---|---|---|
| requests | `<http_requests_total>` | `app`, `env`, `instance`, `status` | `<counter>` |
| latency | `<http_request_duration_seconds_bucket>` | `app`, `env`, `instance`, `le` | `<classic histogram counter>` |
| memory | `<process_resident_memory_bytes>` | `app`, `env`, `instance` | `<gauge>` |

Prometheus/Mimir tenant and data-source identity: `<tenant / data source>`.

## Reusable PromQL snippets

*[sourced: PromQL selector, `rate()`, aggregation, and histogram-quantile syntax; unverified for every
placeholder and target behavior]*

```promql
sum by (app) (rate(<http_requests_total>{app="<app>", env="prod"}[5m]))

histogram_quantile(
  0.95,
  sum by (app, le) (rate(<http_request_duration_seconds_bucket>{app="<app>", env="prod"}[5m]))
)
```

## Lookup packet

Record the backend and tenant, exact metric name, type, unit, reporting or scrape interval, stable
dimensions, owner, and telemetry-contract link. Unknown values stay `[unverified]`.

## Inert canary example

This output proves only that the inventory reference loaded.

```text
Reference-read token: q_ommet_c2d8
```
