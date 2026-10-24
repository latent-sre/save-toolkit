# Cloud Monitoring for metric investigation — PromQL first

## Query in PromQL

- Prefer PromQL for new work. MQL authoring support ended; the console cannot create new MQL
  charts/dashboards/policies, but existing assets remain editable and the API permits creation.
  Editing an MQL asset does not require migration.
- Cloud Monitoring system, Kubernetes, log-based and custom metrics support PromQL; use the
  [PromQL reference](./promql.md) for the dialect.

## What Cloud Monitoring adds around PromQL

- Legacy pre-UTF-8 name mapping converts the first `/` to `:` and other special characters to `_`
  (e.g. `run.googleapis.com/request_count`). Resolve actual names in the console PromQL editor.
- Managed Prometheus and native Cloud Monitoring metrics share a query backend.
- For Mimir queries that fail here, check Cloud Monitoring's compatibility differences at
  `…/stackdriver/docs/managed-prometheus/promql-differences`.
- **Non-PromQL API queries** of Prometheus-ingested metrics use monitored-resource type
  `prometheus_target`.

## Grafana authentication path

Discover plugin, endpoint, authentication, scoping project and query context. A Prometheus datasource
may use Google's data source syncer for OAuth2 service-account token refresh; inspect that only when
present. Native Cloud Monitoring uses other configured auth paths. Service accounts need Monitoring
Viewer on the scoping project. Console success proves neither Grafana identity/context nor syncer
presence.

## Terminal reads

The guard allows `gcloud config get-value project` and `gcloud run services describe` for context,
not broad credential-bearing configuration listings. No GA gcloud command reads metric time series;
use console PromQL, Grafana or Monitoring API, never invent `gcloud monitoring timeseries`.
Without authorized access, return the query for the human; `grafana` owns its query verification.

## Gotchas

- Preserve coexisting Wavefront/Mimir feeds until an agreed cutover with continuity/ownership
  evidence. Dual emission is a choice, not an automatic requirement.
