# WQL dialect for metric investigation

## Encode copied tag values

For a value verified to contain only ASCII letters, digits, `.`, `_`, and `-`, use quoted exact
matching: `ts(app.http.requests.count, app="order-router.v2")`. Validate the tag key independently;
it is syntax, not a value. This recipe does not cover quotes, backslashes, delimiters, or control
characters: those need a target-validated WQL literal encoder.

WQL regex patterns use `/.../`; backslashes escape special characters, and `^`/`$` anchors are
unsupported. Do not copy PromQL's `=~` syntax.

## Query shapes — guardrails

WQL has no PromQL-style postfix aggregation clause: group with trailing parameters
(`sum(ts(metric), app)`) or the inner `by` form, never `sum(...) by (...)` after the parenthesis.
For a fleet request percentile, merge instance histogram distributions first
(`percentile(95, merge(hs(metric.m, ...)))`). Apply `rate()` to each cumulative series before `sum()`; query delta
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
