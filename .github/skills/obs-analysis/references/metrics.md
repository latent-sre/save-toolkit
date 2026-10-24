# Local metric inventory — fill in

Metric names, tags, types and target links for `obs-analysis`. Values below are placeholders;
replace them with discovered inventory, never credentials.

## Candidate Wavefront metric names

| Concern | Metric name | Point tags |
|---|---|---|
| request rate | `<app.http.requests.count>` | `app`, `env`, `instance` |
| latency | `<app.http.requests.latency>` | `app`, `env` |
| errors | `<app.http.requests.errors>` | `app`, `env`, `status` |
| memory | `<app.container.memory.usage>` / `<...limit>` | `app`, `instance` |

PCF apps also expose container CPU, memory, disk, and request metrics through **PCF App Metrics** in
Apps Manager: use it for a quick per-instance view, and Wavefront for history and alerting.

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

## Mimir / Prometheus inventory

| Concern | Metric name | Labels | Type |
|---|---|---|---|
| requests | `<http_requests_total>` | `app`, `env`, `instance`, `status` | `<counter>` |
| latency | `<http_request_duration_seconds_bucket>` | `app`, `env`, `instance`, `le` | `<classic histogram counter>` |
| memory | `<process_resident_memory_bytes>` | `app`, `env`, `instance` | `<gauge>` |

Prometheus/Mimir tenant and data-source identity: `<tenant / data source>`.

## Lookup packet

Record the backend and tenant, exact metric name, type, unit, reporting or scrape interval, stable
dimensions, owner, and telemetry-contract link.
