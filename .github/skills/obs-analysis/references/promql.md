# PromQL dialect for metric investigation

Primary references: [querying basics](https://prometheus.io/docs/prometheus/latest/querying/basics/),
[operators](https://prometheus.io/docs/prometheus/latest/querying/operators/),
[functions](https://prometheus.io/docs/prometheus/latest/querying/functions/),
[histogram practices](https://prometheus.io/docs/practices/histograms/),
[Grafana Mimir HTTP API](https://grafana.com/docs/mimir/latest/references/http-api/).

## Encode copied label values

The identifier `order-router.v2` renders as `app="order-router.v2"`. In a double-quoted PromQL
string, encode each backslash as `\\` and each double quote as `\"`; use the documented escapes for
control characters. Validate label names separately as identifiers.

As a regex, `order-router.v2` becomes regex text `order-router\.v2` and the rendered matcher
`app=~"order-router\\.v2"`. PromQL regex label matchers are already fully anchored.

## Around the query: version-gated facts

Confirm deployed versions and flags before adopting these features.

- **Histogram representation matters:** native `histogram_quantile` inputs use neither `_bucket`
  nor `le`; classic aggregation must retain `le`. Check the scraped representation before treating
  a classic query's empty result as no data. Apply `rate()` before aggregation for request quantiles.
- Duration helpers and extended range selectors depend on deployed versions/flags; check their
  availability and extrapolation semantics before using them in shared rules.
- **Sustained `prometheus_remote_storage_*` failures** mean the query may be missing recent samples
  at the receiving end, a finding for the `obs-pipeline` skill, not a query rewrite.
- **After a Mimir ≥3.2 upgrade**, a query whose cost or result shape changed may now be sharded
  (query sharding is on by default), and query-planning self-metrics moved from
  `component="querier"` to `engine="querier"`.

## Mimir per-tenant limits

Mimir rejects over-limit requests with typed `err-mimir-*` IDs; record the ID verbatim, it
distinguishes data absent from a guardrail firing, and the upstream Mimir runbooks page is the
lookup. Write-side IDs
(`err-mimir-max-series-per-user`, `err-mimir-max-series-per-metric`, `err-mimir-max-active-series`,
`err-mimir-tenant-max-ingestion-rate`) are pipeline findings for `obs-pipeline`; query-side IDs
(`err-mimir-max-chunks-per-query` and siblings) mean narrow the query rather than ask for a
mid-incident limit raise. Which limits bind this tenant is unconfirmed until read from the
deployed runtime configuration; never quote upstream defaults as the tenant's limits.

## Cloud Monitoring

- Prefer PromQL for new work: system, Kubernetes, log-based and custom metrics support it. MQL
  authoring support ended; the console cannot create new MQL charts/dashboards/policies, but
  existing assets remain editable without migration and the API permits creation.
- Legacy pre-UTF-8 name mapping converts the first `/` to `:` and other special characters to `_`
  (e.g. `run.googleapis.com/request_count`). Resolve actual names in the console PromQL editor.
- Managed Prometheus and native Cloud Monitoring metrics share a query backend. For Mimir queries
  that fail here, check `…/stackdriver/docs/managed-prometheus/promql-differences`. Non-PromQL API
  queries of Prometheus-ingested metrics use monitored-resource type `prometheus_target`.
- **Grafana path:** discover plugin, endpoint, authentication, scoping project and query context. A
  Prometheus datasource may use Google's data source syncer for OAuth2 service-account token
  refresh; inspect that only when present. Native Cloud Monitoring uses other configured auth
  paths. Service accounts need Monitoring Viewer on the scoping project. Console success proves
  neither Grafana identity/context nor syncer presence.
- **Terminal reads:** the guard allows `gcloud config get-value project` and
  `gcloud run services describe` for context, not broad credential-bearing configuration listings.
  No GA gcloud command reads metric time series; use console PromQL, Grafana or Monitoring API,
  never invent `gcloud monitoring timeseries`. Without authorized access, return the query for the
  human; `grafana` owns its query verification.
