# Metric analysis: semantics that change the result

- For fleet request p95, combine the same population's distributions/histograms across instances
  before taking the percentile. Averaging or summing per-instance percentiles is invalid;
  point values or precomputed quantiles cannot recover a request distribution.
- Determine cumulative counter, interval delta, or gauge before applying a rate. Rate each
  cumulative series before aggregation so resets remain visible. Bind failures and eligible
  requests to the same population/window; absent denominators or zero traffic are not healthy zero.
- Distinguish a reported zero, a late point, a previously known series that stopped, and a
  selector that never matched. Display gap-filling can hide collection loss. Record reporting
  interval, lookback and applicable alert no-data policy; missing metadata remains a gap.
- For unusual query functions, confirm official backend documentation and retain its URL,
  retrieval date and evidence label. Backend syntax is in [WQL](./wql.md), [PromQL](./promql.md),
  or [Cloud Monitoring](./gcp-monitoring.md).

Query evidence includes meaning/type, units, population, cadence, grouping and missing-data
interpretation. An alert/SLO recommendation to `observability-engineer` also needs the exact
query, window, threshold, current value and no-data behavior.
