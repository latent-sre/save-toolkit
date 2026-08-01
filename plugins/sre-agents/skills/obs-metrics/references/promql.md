# PromQL dialect for metric investigation

Use this reference for Prometheus-compatible queries in Mimir or Prometheus after applying the parent
skill's investigation shape. Syntax is sourced from current Prometheus documentation; confirm Mimir's
deployed version, tenancy, metric names, labels, scrape cadence, rule evaluation, and retention.

Primary references:

- [querying basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [operators](https://prometheus.io/docs/prometheus/latest/querying/operators/)
- [functions](https://prometheus.io/docs/prometheus/latest/querying/functions/)
- [histogram practices](https://prometheus.io/docs/practices/histograms/)
- [Grafana Mimir HTTP API](https://grafana.com/docs/mimir/latest/references/http-api/)

## Selectors and label matchers

Use a metric selector with the narrowest stable labels that answer the question. PromQL supports exact,
negative, regular-expression, and negative-regular-expression matchers: `=`, `!=`, `=~`, and `!~`.

*[sourced: Prometheus querying basics; unverified for target metric and labels]*

```promql
http_requests_total{app="checkout", env="prod", method=~"GET|POST"}
```

An empty selector result can reflect a stale series, wrong label, wrong tenant, or absent telemetry; it
is not automatically a zero.

## Counters — rate before aggregation

For counters, **`rate()` before `sum()`, never `sum()` before `rate()`**. Apply `rate()` to each source
series so counter resets remain detectable, then aggregate the rates. `increase()` is the range-window
increase derived from the counter's rate behavior.

*[sourced: Prometheus `rate()`/`increase()` documentation; unverified for target metric/window]*

```promql
sum(rate(http_requests_total{job="checkout"}[5m]))
```

*[sourced: Prometheus `rate()` and aggregation operators; unverified for target labels/window]*

```promql
sum by (app) (rate(http_requests_total{env="prod"}[5m]))
```

*[sourced: Prometheus `increase()` and aggregation operators; unverified for target labels/window]*

```promql
sum by (app) (increase(http_requests_total{env="prod"}[1h]))
```

Use these only for counters. Applying counter functions to gauges can return syntactically valid but
meaningless results.

## Aggregate with real `by` and `without`

PromQL aggregation operators support `by` to retain named labels and `without` to remove named labels.

*[sourced: Prometheus aggregation operators; unverified for target labels]*

```promql
sum without (instance) (rate(http_requests_total{env="prod"}[5m]))
```

```promql
sum by (app, status) (rate(http_requests_total{env="prod"}[5m]))
```

## Error ratio and burn-rate shape

The numerator and denominator must describe the same request population and window. The illustrative
expression below divides observed error ratio by an allowed error fraction of `1 - 0.999`.

*[sourced: PromQL selector, `rate()`, aggregation, and arithmetic syntax; unverified metric, labels,
window, SLO target, and target no-traffic behavior]*

```promql
(
  sum by (app) (rate(http_requests_total{env="prod", status=~"5.."}[5m]))
/
  sum by (app) (rate(http_requests_total{env="prod"}[5m]))
) / (1 - 0.999)
```

Do not coerce a missing or zero denominator to a healthy value without an explicit, verified no-traffic
policy. Ownership map only—not a load: the `obs-alerting` skill owns the later multi-window threshold
design.

## Histogram p95

For a classic histogram, rate each `_bucket` counter, aggregate while retaining `le`, and then apply
`histogram_quantile`. This calculates a percentile from the combined bucket distribution.

*[sourced: Prometheus `histogram_quantile()` documentation and histogram practices; unverified target
histogram name, labels, bucket design, and window]*

```promql
histogram_quantile(
  0.95,
  sum by (app, le) (
    rate(http_request_duration_seconds_bucket{env="prod"}[5m])
  )
)
```

Do not average summary quantiles across instances; summaries have already discarded the distribution
needed to reconstruct an aggregate percentile. *[sourced: Prometheus histogram and summary practices]*

## Missing data and staleness

Prometheus marks series stale when they stop being exported or a target disappears; selectors then stop
returning the series after the applicable lookback/staleness behavior. Record the target's scrape and
rule intervals and test its no-data path separately from a threshold. *[sourced: Prometheus querying
basics; unverified for target configuration]*

## Inert canary example

The expression is a reference-loading fixture, not a target metric claim.

*[sourced: PromQL selector and `rate()` syntax; unverified placeholder metric/labels]*

```promql
sum by (app) (rate(fixture_requests_total{app="<fixture_app>"}[5m]))
```

Expected fixture output (inert):

```text
q_ompr_4e9a
```
