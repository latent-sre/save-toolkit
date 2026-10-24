# WQL dialect for metric investigation

Primary references:

- [WQL reference](https://docs.wavefront.com/query_language_reference.html)
- [aggregation functions](https://docs.wavefront.com/query_language_aggregate_functions.html)
- [`sum()`](https://docs.wavefront.com/ts_sum.html)
- [series matching](https://docs.wavefront.com/query_language_series_matching.html)
- [histogram `merge()`](https://docs.wavefront.com/hs_merge.html)
- [percentiles](https://docs.wavefront.com/ts_percentile.html)
- [delta counters](https://docs.wavefront.com/delta_counters.html)
- [`rate()`](https://docs.wavefront.com/ts_rate.html) and [`cs()`](https://docs.wavefront.com/cs_function.html)
- [missing-data alerts](https://docs.wavefront.com/alerts_missing_data.html)

## Encode copied tag values

For a value verified to contain only ASCII letters, digits, `.`, `_`, and `-`, use quoted exact
matching: `ts(app.http.requests.count, app="order-router.v2")`. Validate the tag key independently;
it is syntax, not a value. This recipe does not cover quotes, backslashes, delimiters, or control
characters: use a target-validated WQL literal encoder for those values, or stop for a sanitized
identifier. Inspect the rendered query after any additional client encoding.

WQL regex patterns use `/.../`; backslashes escape special characters, and `^`/`$` anchors are
unsupported. Do not copy PromQL's `=~` syntax or treat anchoring as escaping.

## Query shapes — guardrails

WQL has no PromQL-style postfix aggregation clause: group with trailing parameters
(`sum(ts(metric), app)`) or the inner `by` form, never `sum(...) by (...)` after the parenthesis.
For a fleet request percentile, merge instance histogram distributions first
(`percentile(95, merge(hs(metric.m, ...)))`); a percentile over per-instance points describes
instances, not requests. Apply `rate()` to each cumulative series before `sum()`; query delta
counters with `cs()`, not cumulative `rate()` semantics. On PCF, inspect counter-reset behaviour
before treating a rate as alert evidence, and use `default()` only where it cannot conceal late or
missing telemetry — a selector matching nothing needs a separate no-data path.

## Missing data

For a sustained gap, `mcount()` can decay to zero and later stop returning a series. Holding the last
known count across a bounded window is a candidate for keeping the condition evaluable:

```text
last(1h, mcount(3m, ts(app.http.requests.count, app="order-router"))) = 0
```

Verify the reporting cadence and alert lifecycle before using this shape. A known series that stops
and a selector that never matched need separate checks; configure the platform's no-data notification
path for vanishing or unmatched series.
