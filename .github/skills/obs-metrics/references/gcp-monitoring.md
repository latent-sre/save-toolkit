# Cloud Monitoring for metric investigation — PromQL first

Apply the parent investigation shape first. This reference adds Cloud Monitoring behavior
to [PromQL](./promql.md); confirm the target's metric and access contract.

## The one decision that's already made: query in PromQL

- **MQL is deprecated.** Google Cloud customer support for MQL ended **2025-07-22**, and MQL can
  no longer be used for new charts, dashboards, or alerting policies in the console; existing MQL
  assets keep working. Do not author new MQL; translate on touch.
- **PromQL covers everything.** All Cloud Monitoring metrics — "Google Cloud system metrics,
  Kubernetes metrics, log-based metrics, and custom metrics" — are queryable with PromQL. The
  PromQL dialect itself is the parent skill's [PromQL reference](./promql.md); this file covers
  only what Cloud Monitoring adds.

## What Cloud Monitoring adds around PromQL

- **Metric-name mapping.** Cloud Monitoring names (`run.googleapis.com/request_count`) convert to
  PromQL-compatible equivalents — the first `/` becomes `:`, other special characters become `_`.
  With UTF-8 metric-name support that
  transliteration is now the **legacy-compatibility** path (pre-UTF-8 charts query by converted
  names); still resolve the mapped name in the console's PromQL editor rather than guessing.
- **Managed Service for Prometheus shares the backend.** Metrics ingested by Managed Prometheus
  and native Cloud Monitoring metrics are queryable together "in Cloud Monitoring, Grafana, or any
  other tool that can read the Prometheus API".
- **Compatibility deltas exist** — Cloud Monitoring's PromQL is not byte-for-byte upstream; the
  differences page (`…/stackdriver/docs/managed-prometheus/promql-differences`) is the checklist
  when a working Mimir query misbehaves against Cloud Monitoring.
- **Non-PromQL API queries** of Prometheus-ingested metrics use monitored-resource type
  `prometheus_target`.

## Grafana against Cloud Monitoring — discover the integration

Confirm the target datasource plugin, endpoint, authentication path, scoping project, and query
context before diagnosing Grafana-only no-data. The deployed integration is unconfirmed.
A Prometheus datasource may use Google's **data source syncer** to refresh an OAuth2
service-account token; inspect syncer/token refresh only when that path is observed.
The native Google Cloud Monitoring datasource supports other authentication paths; inspect its
configured authentication and permissions instead. A service account needs **Monitoring Viewer**
on the scoping project. Console success alone does not establish Grafana's identity, project,
query context, or a syncer deployment.

## Terminal reads

`gcloud config get-value project` and `gcloud run services describe` (limits/concurrency context)
are on the guard's allowlist.
Broad configuration listings are excluded because configurations can contain credentials.
**No GA gcloud command reads metric time series** — the GA `gcloud monitoring`
group holds only `dashboards`, `policies`, `snoozes`, and `uptime`; whether the alpha/beta tracks
also lack one is unconfirmed. Time-series reads go through the console PromQL editor, Grafana, or
the Monitoring API. Lanes without the applicable read tools/authority prepare the query for the
human. The invoked `observability-engineer` retains its existing dashboard-query verification path
under `grafana`; this grants no other lane dashboard writes. Do not hunt for a
`gcloud monitoring timeseries` command.

## Gotchas

- Wavefront and Mimir remain first-class while workloads coexist; a service migrating runtimes
  should keep emitting to the incumbent path until cutover is recorded in `stack-profile` —
  double-emit beats a telemetry gap.
