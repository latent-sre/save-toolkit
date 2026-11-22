# OpenTelemetry semantics, naming, and SDK instrumentation

## Span kinds and status vs. protocol outcome

- **Span kinds:** Confirm both span kinds before treating parent/child as a network hop; deferred or
  async work can use links or separate timelines.
- **Span status:** `Unset` is the default, not proof of health; `Ok` means explicit application/operator
  validation; interpret `Error` under the active semantic convention. HTTP 1xx–3xx normally leaves
  status `Unset`; without extra context, server 4xx is `Unset`, whereas client 4xx and either-side
  5xx are `Error`. Always inspect span status alongside `http.response.status_code`.

## Semantic conventions and attribute maturity

HTTP conventions stabilized in v1.23.0 (`url.*`, `client.*`/`server.*` replacing `net.*`); database
core stabilized in v1.33.0 (MariaDB, SQL Server, MySQL, PostgreSQL). Older instrumentation or
`http/dup` and `database/dup` migration modes may emit legacy fields — inspect emitted attributes
before treating an empty stable-name query as zero traffic:

| Legacy field | Current stable field |
|---|---|
| `http.method` | `http.request.method` |
| `http.status_code` | `http.response.status_code` |
| `db.system` | `db.system.name` |
| `db.name` | `db.namespace` |
| `db.operation` | `db.operation.name` |

- **Maturity in semconv v1.45.0:** `service.instance.id`, `server.address`, `http.route`, and
  `db.collection.name` are **Stable**; `messaging.destination.name` is **Development**.
- **URL redaction:** The spec forbids credentials in `url.full`, but default query redaction only
  masks named signing keys (`AWSAccessKeyId`, `Signature`, `sig`, `X-Goog-Signature`, and `X-Amz-*`
  signature/credential/security-token keys) with `REDACTED`; redact all other sensitive query
  parameters before copying.

## OTel metric naming and backend translation

- **Dotted namespaces and UCUM units:** Delimit namespaces with **dots** and use `snake_case` only
  within multi-word components. Put units in **instrument metadata (UCUM)**, not the metric name,
  using base units (`s`, `By`) and putting dimensions in attributes (`http.server.request.duration`
  with unit `s`). Pluralize only discrete count names with annotation units like `{fault}` or
  `{job}` (`system.paging.faults`, `jobs.processed`); metrics with real units or dimensionless `1`
  (`system.cpu.utilization`) and **UpDownCounter** names (`job.active`) are **never pluralized**.
- **Exporter translation:** Do not pre-bake Prometheus suffixes into OTel instrument names. Mimir's
  OTLP endpoint adds no unit/type suffixes by default (`distributor.otel-metric-suffixes-enabled = false`),
  whereas Alloy/Collector Prometheus exporters and Prometheus's OTLP receiver add them (and UTF-8
  translation strategies keep dots). Check the stored metric name in the backend before querying.

## SDK instrumentation and tail sampling

Installs, agent flags, and app code belong to `software-engineer` or the application owner (under
`stack-profile`, Java source remains with the application owner; check Spring Boot build/buildpack
configs for duplicate PCF `-javaagent` injection).

1. **Resource identity:** Emit `service.name`, `service.version`, and `deployment.environment.name`
   (replaces deprecated `deployment.environment`, stable in v1.41.0; values `development`,
   `staging`, `production`, `test`). Unset names fall back to `unknown_service:<executable>`. Keep
   logical `service.name` consistent across PCF and Cloud Run, filtering by environment attribute.
2. **Sampling and tail-sampling limits:** `RECORD_ONLY` sets `IsRecording=true, Sampled=false`
   (received by in-process processors, excluded from normal SDK export); `RECORD_AND_SAMPLE`
   permits export but does not prove backend receipt. For collector tail sampling:
   - Collectors cannot recover spans dropped by an upstream head sampler.
   - Multiple sampling collectors require **trace-ID affinity** (e.g., load-balancing exporter
     before the sampling tier), never round-robin.
   - `num_traces` defaults to `50,000` in memory (evictions increment
     `otelcol_processor_tail_sampling_sampling_trace_dropped_too_early`); `decision_wait` defaults
     to `30s`; `decision_cache` (sampled/non-sampled LRU) defaults to off (`0`). Since contrib
     v0.145.0: `maximum_trace_size_bytes` (`traces_dropped_too_large`); since v0.149.0:
     `sampling_strategy` (`trace-complete` default vs. `span-ingest`).
3. **Correlation and completion:** Emit structured logs with trace/span IDs and verify actual
   exemplar (`metric → trace`) and shared-ID (`trace → log`) links with a bounded canary.
