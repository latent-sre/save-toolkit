# Cloud Monitoring for metric investigation — PromQL first

## Query in PromQL

- **MQL is no longer recommended.** Customer support for writing MQL has ended, and the console
  cannot create new MQL charts, dashboards, or alerting policies. Existing assets still work and
  can be edited; the Monitoring API still supports creating them. Prefer PromQL for new work;
  touching an existing MQL asset does not require migrating it.
- Cloud Monitoring system, Kubernetes, log-based and custom metrics support PromQL; use the
  [PromQL reference](./promql.md) for the dialect.

## What Cloud Monitoring adds around PromQL

- **Metric-name mapping.** Cloud Monitoring names (`run.googleapis.com/request_count`) convert to
  PromQL-compatible equivalents — the first `/` becomes `:`, other special characters become `_`.
  This is the legacy path for pre-UTF-8 charts; resolve the name in the console's PromQL editor.
- Managed Prometheus and native Cloud Monitoring metrics share a query backend.
- For Mimir queries that fail here, check Cloud Monitoring's compatibility differences at
  `…/stackdriver/docs/managed-prometheus/promql-differences`.
- **Non-PromQL API queries** of Prometheus-ingested metrics use monitored-resource type
  `prometheus_target`.

## Grafana authentication path

Discover the target datasource plugin, endpoint, authentication path, scoping project and query
context before diagnosing Grafana-only no-data. A Prometheus datasource may use Google's
**data source syncer** to refresh an OAuth2 service-account token; inspect syncer/token refresh
only when that path is observed. The native Cloud Monitoring datasource supports other paths:
inspect its configured authentication and permissions. Service accounts need **Monitoring Viewer**
on the scoping project. Console success does not establish Grafana's identity, project, query
context, or a syncer deployment; the deployed integration remains unconfirmed.

## Terminal reads

`gcloud config get-value project` and `gcloud run services describe` (limits/concurrency context)
are on the guard's allowlist.
Broad configuration listings are excluded because configurations can contain credentials.
**No GA gcloud command reads metric time series.** Use the console PromQL editor, Grafana, or
Monitoring API, not an invented `gcloud monitoring timeseries` command. Prepare the query for the
human when the lane lacks an authorized read path; Grafana query verification follows `grafana`.

## Gotchas

- Wavefront and Mimir remain in use while workloads coexist. Preserve existing emission paths
  unless the task includes an agreed cutover; verify telemetry continuity and ownership before
  removing a feed. Dual emission is a migration choice, not an automatic requirement.
