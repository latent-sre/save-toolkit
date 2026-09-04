# PromQL dialect for metric investigation

Use this reference for Prometheus-compatible queries in Mimir or Prometheus after applying the parent
skill's investigation shape. Confirm Mimir's deployed version, tenancy, metric names, labels, scrape
cadence, rule evaluation, and retention.

Primary references: [querying basics](https://prometheus.io/docs/prometheus/latest/querying/basics/),
[operators](https://prometheus.io/docs/prometheus/latest/querying/operators/),
[functions](https://prometheus.io/docs/prometheus/latest/querying/functions/),
[histogram practices](https://prometheus.io/docs/practices/histograms/),
[Grafana Mimir HTTP API](https://grafana.com/docs/mimir/latest/references/http-api/).

`[verified 2026-08-22]` Every query block below parsed and executed against a live Prometheus
behind a non-production Grafana 13.1.4; the example labels are illustrative and return zero series.
Semantics against your metric names, and Mimir's deployed version and tenancy, remain `[unverified]`.

## The shapes alerts and dashboards copy

Apply `rate()` to each source series before aggregating, so counter resets stay visible; never
`sum()` a counter first. An empty selector result can be a stale series, wrong label, wrong tenant,
or absent telemetry; it is not a zero.

```promql
sum by (app) (rate(http_requests_total{env="prod"}[5m]))
```

Error ratio and burn rate: numerator and denominator over the same population and window, divided
by the allowed error fraction. Do not coerce a missing or zero denominator to a healthy value
without an explicit, verified no-traffic policy.

```promql
(
  sum by (app) (rate(http_requests_total{env="prod", status=~"5.."}[5m]))
/
  sum by (app) (rate(http_requests_total{env="prod"}[5m]))
) / (1 - 0.999)
```

Classic-histogram p95: rate each `_bucket`, aggregate keeping `le`, then `histogram_quantile`. Never
average summary quantiles across instances; a summary has already discarded the distribution.

```promql
histogram_quantile(
  0.95,
  sum by (app, le) (
    rate(http_request_duration_seconds_bucket{env="prod"}[5m])
  )
)
```

## Around the query: version-gated facts

*[sourced: prometheus.io practices and configuration reference, the prometheus/prometheus
CHANGELOG, and the Mimir 3.2.0 release notes; reviewed 2026-08-07 to 2026-08-21; unverified for
the deployed Prometheus and Mimir versions]*

- **Recording-rule names are `level:metric:operations`**, aggregating with an explicit
  `without (…)` so labels like `job` survive:

  ```yaml
  - record: job_instance_mode:node_cpu_seconds:avg_rate5m
    expr: avg without (cpu) (rate(node_cpu_seconds_total[5m]))
  ```

  A recording rule that aggregates away the label an alert later needs makes the alert unwritable;
  check consumers before choosing `level`.
- **Native histograms are stable but optional** from v3.8 (the old feature flag is a no-op from
  v3.9; scraping is enabled per job via `scrape_native_histograms`). Whether the deployed chain has
  them on is `[unverified]` per target, and `histogram_quantile` over a native histogram uses no
  `_bucket` series or `le` label, so the classic p95 shape silently matches nothing against a
  native-only metric. Check which representation the target scrapes before declaring no data.
- **Newer PromQL surface is version-gated**: duration arithmetic from v3.4; later duration helpers
  flag-gated through v3.13 and default-on from v3.14; extended range selectors
  (`promql-extended-range-selectors`, which change `rate()` extrapolation) from v3.7 and still
  experimental in v3.14. Keep both out of shared rules until the deployed version and flags are
  confirmed.
- **remote_write `queue_config` defaults**: `capacity` 10000, `max_shards` 50,
  `max_samples_per_send` 2000, `batch_send_deadline` 5s; sustained `prometheus_remote_storage_*`
  failures mean the query may be missing recent samples at the receiving end, a finding for the
  `obs-pipeline` skill, not a query rewrite.
- **Mimir 3.2.0 changed query-path defaults**: remote execution is on by default and every querier
  must be on 3.1 before the upgrade; query sharding is on by default
  (`-query-frontend.parallelize-shardable-queries=false` disables it), so a query whose cost or
  result shape changed after the upgrade may be sharded now; ingester request hedging is off
  (`-querier.minimize-ingester-requests-hedging-delay=3s` restores it), so one slow ingester shows as
  tail latency it previously hid; and query-planning metrics moved from `component="querier"` to
  `engine="querier"`, so a borrowed self-monitoring dashboard on the old label goes empty. The
  deployed Mimir version is `[unverified]`.

## Mimir per-tenant limits

Mimir rejects over-limit requests with typed `err-mimir-*` IDs; record the ID verbatim, it
distinguishes data absent from a guardrail firing, and the upstream Mimir runbooks page is the
lookup *[sourced: grafana/mimir runbooks and configuration reference]*. Write-side IDs
(`err-mimir-max-series-per-user`, `err-mimir-max-series-per-metric`, `err-mimir-max-active-series`,
`err-mimir-tenant-max-ingestion-rate`) are pipeline findings for `obs-pipeline`; query-side IDs
(`err-mimir-max-chunks-per-query` and siblings) mean narrow the query rather than ask for a
mid-incident limit raise. Which limits bind this tenant is `[unverified]` until read from the
deployed runtime configuration; never quote upstream defaults as the tenant's limits.

## Missing data and staleness

Prometheus marks a series stale when it stops being exported or its target disappears, and selectors
stop returning it after the lookback and staleness behaviour. Record the target's scrape and rule
intervals and test its no-data path separately from any threshold *[sourced: Prometheus querying
basics; unverified for the target's configuration]*.
