# PromQL and Cloud Monitoring

## Label escaping

Render `order-router.v2` literally as `app="order-router.v2"` (escaping `\` → `\\`, `"` → `\"`).
As a regex, escape metacharacters first (`order-router\.v2`), then escape for the double-quoted
string: `app=~"order-router\\.v2"` (PromQL regex matchers are already full-string anchored).

## Version-gated features and Mimir limits

- **Histograms:** native histograms for `histogram_quantile` use neither `_bucket` nor `le` — confirm
  scraped representation before treating an empty classic `_bucket` query as zero traffic.
- **Remote-write / Mimir upgrades:** sustained `prometheus_remote_storage_*` errors indicate
  pipeline loss ([Alloy pipeline](./alloy.md)). After Mimir ≥ 3.2, query sharding is enabled by default
  and querier metrics moved from `component="querier"` to `engine="querier"`.
- **Mimir per-tenant limits (`err-mimir-*`):** write-side errors (`err-mimir-max-series-per-user`,
  `err-mimir-max-series-per-metric`, `err-mimir-max-active-series`,
  `err-mimir-tenant-max-ingestion-rate`) are ingestion/pipeline findings ([Alloy pipeline](./alloy.md));
  query-side errors (`err-mimir-max-chunks-per-query` and siblings) require narrowing the query.
  Read deployed runtime overrides rather than quoting upstream defaults.

## Cloud Monitoring

- Prefer PromQL for new charts/policies (`MQL` authoring ended, though existing MQL assets remain
  editable and API-creatable). Legacy pre-UTF-8 metric names map the first `/` to `:` and special
  characters to `_` (`run.googleapis.com/request_count` excludes 429s rejected at max instances).
- Managed Prometheus and Cloud Monitoring share a query backend; non-PromQL API queries over
  Prometheus metrics use monitored resource `prometheus_target`.
- **Grafana path:** discover the plugin, endpoint, authentication path (including any OAuth2
  data-source syncer only if present), scoping project (`Monitoring Viewer`), and query context first.
- **Terminal reads:** use Console PromQL, Grafana, or the Monitoring API (`gcloud config get-value project`
  and `gcloud run services describe` are guard-allowed for context; no GA `gcloud` command reads
  time series).
