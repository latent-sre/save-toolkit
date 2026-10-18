# WQL dialect for metric investigation

Apply the parent investigation shape first. Query syntax follows the primary references
below; all example names, tags, types, policies, and target behavior remain unconfirmed until
checked against the deployed tenant.

**Lifecycle.** Wavefront continues as Broadcom DX OpenExplore; the end-of-availability retired
the VMware *Tanzu Observability* offering, not the engine or WQL. `docs.wavefront.com` is still
online but frozen at 2024-09 — treat it as authoritative for the WQL syntax below and for nothing
newer, because a language change after that date appears only in the DX OpenExplore TechDocs. The
public proxy repository is read-only and reference-only: Proxy 14.0+ is not built from public
sources, so proxy updates and security fixes come from Broadcom rather than GitHub.
`stack-profile` stays the authority on what the team runs today.

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

## Contents

- Select series and filter point tags
- Query shapes — guardrails
- Missing data

## Select series and filter point tags

### Encode copied tag values

For a value verified to contain only ASCII letters, digits, `.`, `_`, and `-`, use quoted exact
matching: `ts(app.http.requests.count, app="checkout.v2")`. Validate the tag key independently;
it is syntax, not a value. This recipe does not cover quotes, backslashes, delimiters, or control
characters: use a target-validated WQL literal encoder for those values, or stop for a sanitized
identifier. Inspect the rendered query after any additional client encoding.

WQL regex patterns use `/.../`; backslashes escape special characters, and `^`/`$` anchors are
unsupported. Do not copy PromQL's `=~` syntax or treat anchoring as escaping. Prefer exact matching
for copied identifiers rather than constructing a regex from their contents. The target version
and an arbitrary-value encoder are unconfirmed.

## Query shapes — guardrails

WQL has no PromQL-style postfix aggregation clause: group with trailing parameters
(`sum(ts(metric), app)`) or the inner `by` form, never `sum(...) by (...)` after the parenthesis.
For a fleet request percentile, merge instance histogram distributions first
(`percentile(95, merge(hs(metric.m, ...)))`); a percentile over per-instance points describes
instances, not requests. Apply `rate()` to each cumulative series before `sum()`; query delta
counters with `cs()`, not cumulative `rate()` semantics. On PCF, inspect counter-reset behaviour
before treating a rate as alert evidence, and use `default()` only where it cannot conceal late or
missing telemetry — a selector matching nothing needs a separate no-data path. These shapes are
unconfirmed for the target metric.

## Missing data

Test the expected reporting interval separately from an ordinary threshold. For a metric expected once
per minute, a five-minute count should be interpreted against that cadence; a known series that stops
and a selector that has never matched are different conditions.

This is unconfirmed for the target interval and metric.

```text
mcount(5m, ts(app.http.requests.count, app="checkout")) < 5
```

For a sustained gap, `mcount()` can decay to zero and later stop returning a series. Holding the last
known count across a bounded window is one documented candidate for keeping the condition evaluable.

This is unconfirmed for the target interval, lifecycle, and metric.

```text
last(1h, mcount(3m, ts(app.http.requests.count, app="checkout"))) = 0
```

Treat this as a candidate only after verifying its behavior in the target alert lifecycle. Configure the
platform's no-data notification path for ordinary thresholds whose series vanishes and for selectors
that match nothing at all. Do not describe a no-data state as healthy.


