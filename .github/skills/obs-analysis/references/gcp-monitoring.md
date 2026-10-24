# Cloud Monitoring for metric investigation — PromQL first

## Query in PromQL

- **MQL is deprecated.** Google Cloud customer support for MQL ended **2025-07-22**, and MQL can
  no longer be used for new charts, dashboards, or alerting policies in the console; existing MQL
  assets keep working. Do not author new MQL; translate on touch.
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

Grafana queries Managed Prometheus/Cloud Monitoring through the **data source syncer**: Google
Cloud APIs require OAuth2, Grafana's Prometheus data source doesn't do OAuth2 for service
accounts, so the syncer refreshes a service-account token into the data source every ~10 minutes
(tokens live 1 hour). The service account needs **Monitoring Viewer** on the scoping project.
Triage implication: Grafana panels going all-no-data against GCP while the console works =
suspect the syncer/token path before the metrics.

## Terminal reads

`gcloud config get-value project` and `gcloud run services describe` (limits/concurrency context)
are on the guard's allowlist.
Broad configuration listings are excluded because configurations can contain credentials.
**No GA gcloud command reads metric time series.** Use the console PromQL editor, Grafana, or
Monitoring API, not an invented `gcloud monitoring timeseries` command. Prepare the query for the
human when the lane lacks an authorized read path; Grafana query verification follows `grafana`.

## Gotchas

- Wavefront and Mimir remain first-class while workloads coexist; a service migrating runtimes
  should keep emitting to the incumbent path until cutover is recorded in `stack-profile` —
  double-emit beats a telemetry gap.
