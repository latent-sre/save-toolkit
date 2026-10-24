# PromQL dialect for metric investigation

Primary references: [querying basics](https://prometheus.io/docs/prometheus/latest/querying/basics/),
[operators](https://prometheus.io/docs/prometheus/latest/querying/operators/),
[functions](https://prometheus.io/docs/prometheus/latest/querying/functions/),
[histogram practices](https://prometheus.io/docs/practices/histograms/),
[Grafana Mimir HTTP API](https://grafana.com/docs/mimir/latest/references/http-api/).

## Encode copied label values

Prefer an exact matcher: the identifier `order-router.v2` renders as `app="order-router.v2"`.
In a double-quoted PromQL string, encode each backslash as `\\` and each double quote as `\"`;
use the documented escapes for control characters. Then apply any additional client JSON or shell
encoding, and inspect the final PromQL expression. Validate label names separately as identifiers.

If a regex is necessary, first escape its metacharacters so the supplied value is literal, then
encode that regex as a PromQL string. `order-router.v2` becomes regex text `order-router\.v2` and the
rendered matcher `app=~"order-router\\.v2"`. PromQL regex label matchers are already fully anchored;
adding `^` and `$` does not make an unescaped dot literal. Use a tested encoder for arbitrary values
or stop for a sanitized identifier; never concatenate raw input.

## Around the query: version-gated facts

Confirm deployed versions and flags before adopting these features.

- Recording rules use `level:metric:operations`; choose explicit `without (…)` dimensions to
  preserve labels alert consumers need, such as `job`.
- **Native histograms are stable but optional** from v3.8 (the old feature flag is a no-op from
  v3.9; scraping is enabled per job via `scrape_native_histograms`). Whether the deployed chain has
  them enabled must be checked: `histogram_quantile` over a native histogram uses no
  `_bucket` series or `le` label, so the classic p95 shape silently matches nothing against a
  native-only metric. Check which representation the target scrapes before declaring no data.
- **Newer PromQL surface is version-gated**: duration arithmetic from v3.4; later duration helpers
  flag-gated through v3.13 and default-on from v3.14; extended range selectors
  (`promql-extended-range-selectors`, which change `rate()` extrapolation) from v3.7 and still
  experimental in v3.14. Keep both out of shared rules until the deployed version and flags are
  confirmed.
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
