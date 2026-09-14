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

PCF apps also expose container CPU, memory, disk, and request metrics through **PCF App Metrics** in
Apps Manager: use it for a quick per-instance view, and Wavefront for history and alerting.
[unverified — confirm the metric names your foundation exports]

## Source / tag conventions

- App identifier tag: `<app=...>` · environment tag: `<env=prod|nonprod>`
- Instance/host tag: `<instance=...>` (use to find one bad instance)

## Dashboards & alert targets

| Name | Link | What it shows |
|---|---|---|
| `<dashboard>` | `<url>` | `<SLO / golden signals>` |

## Telemetry contract

Record request/error counter type: delta-per-interval or cumulative. Record whether latency is a
histogram/distribution, a per-instance point value, or a precomputed percentile; these require
different calculations. Also record clean-period emission, reporting interval, and missing-data policy.
Use [WQL](./wql.md) for the corresponding query forms, including the conditions on zero-fill;
keep this file for discovered names, types, tags, and target links.

## Mimir / Prometheus inventory

| Concern | Metric name | Labels | Type |
|---|---|---|---|
| requests | `<http_requests_total>` | `app`, `env`, `instance`, `status` | `<counter>` |
| latency | `<http_request_duration_seconds_bucket>` | `app`, `env`, `instance`, `le` | `<classic histogram counter>` |
| memory | `<process_resident_memory_bytes>` | `app`, `env`, `instance` | `<gauge>` |

Prometheus/Mimir tenant and data-source identity: `<tenant / data source>`.

Use the [PromQL reference](./promql.md) for counter, error-ratio, and histogram query forms.

## Lookup packet

Record the backend and tenant, exact metric name, type, unit, reporting or scrape interval, stable
dimensions, owner, and telemetry-contract link. Unknown values stay `[unverified]`.
