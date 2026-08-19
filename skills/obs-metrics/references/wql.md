# WQL dialect for metric investigation

Use this reference only after applying the parent skill's product-agnostic investigation shape. The
syntax and behavior statements are sourced from current VMware Aria Operations for Applications
documentation; all metric names, tags, counter types, alert policies, and tenant capabilities remain
unverified until checked against the team's target.

**Lifecycle — `[sourced]` (reviewed 2026-08-19).** The platform continues as **Broadcom DX
OpenExplore**: Broadcom TechDocs introduces it as built "using Aria Operations for Applications
(Wavefront) and the DX platform" and maintains Wavefront release notes under
`techdocs.broadcom.com/us/en/ca-enterprise-software/it-operations-management/dx-openexplore/saas/`
(updated February 2026). The 2025-10-31 end-of-availability (support.broadcom.com announcement
25153) retired the VMware *Tanzu Observability* offering, not the engine or WQL. docs.wavefront.com
remains online but its source is **frozen**: at `wavefrontHQ/docs@0492d79` the newest release-notes
entry is 2024-09.x (a 2024-10.x entry sits committed but commented out) and the string "OpenExplore"
appears nowhere in the repository `[sourced: GitHits grep/read of wavefrontHQ/docs@0492d79]`. WQL
syntax below therefore remains valid as of that freeze; any language change after 2024 appears only
in the DX OpenExplore TechDocs. The public proxy repository is likewise closed off:
`wavefrontHQ/wavefront-proxy`'s README declares the repo read-only and reference-only, with Proxy
14.0+ no longer built from the public sources — proxy updates and security fixes come from
Broadcom, not GitHub `[sourced: wavefrontHQ/wavefront-proxy@7b217ea README]`. `stack-profile` stays
the authority on what the team runs today.

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
- Aggregate and group — reject the fabricated aggregation clause
- Percentile latency — combine the request distribution
- Error ratio depends on counter type
- Rates, windows, and saturation
- Missing data
- WQL and PromQL mapping aid
- Investigation handoff
- Inert canary example

## Select series and filter point tags

`ts()` selects time series. Filter sources, source tags, and point tags inside the selector and confirm
the actual tag keys in [local metric inventory](./metrics.md).

*[sourced: WQL reference; unverified for target metric and tags]*

```text
ts(app.http.requests.count, app="checkout" and env="prod")
```

## Aggregate and group — reject the fabricated aggregation clause

WQL has no PromQL-style **postfix** aggregation clause — `sum(...) by (...)` written after the
closing parenthesis is the fabrication to reject. Group an aggregation with trailing parameters,
`sum(ts(app.http.requests.count), app)`, or with the documented inner form
`sum(ts(app.http.requests.count) by (app))` — the two are equivalent, and `without (...)` also
exists. WQL's separate `by (...)` construct additionally controls series matching across operators;
`join()` is an alternative. Do not translate PromQL postfix aggregation syntax into a WQL
aggregation.

*[sourced: WQL `sum()` and series-matching documentation; the trailing-parameter / inner-`by`
equivalence is byte-verified at wavefrontHQ/docs@0492d79
`pages/doc/query_language_aggregate_functions.md:147-151`; unverified for target metric and tag]*

```text
sum(ts(app.http.requests.count), app)
```

Multiple trailing parameters create nested grouping dimensions.

*[sourced: WQL aggregation functions; unverified for target tags]*

```text
sum(ts(app.http.requests.count), app, env)
```

Break a flat aggregate down by adding the pointTag parameter: `, instance` / `, host`.
*[sourced: WQL aggregation grouping parameters; unverified for target tag names]*

## Percentile latency — combine the request distribution

`percentile()` over a `ts()` expression aggregates point values across the selected series at each
timestamp. If those points are per-instance means, the result is a percentile of instance means, not a
request percentile.

*[sourced: WQL time-series percentile documentation; unverified for target metric semantics]*

```text
percentile(95, ts(app.http.requests.latency, app="checkout"), instance)
```

Histogram conversion functions return a value for each input histogram series. To calculate one
app-wide request percentile across instance histogram series, merge the distributions first.

*[sourced: WQL histogram `merge()` and percentile documentation; unverified for target histogram name]*

```text
percentile(95, merge(hs(app.http.requests.latency.m, app="checkout")))
```

If only precomputed per-instance percentile metrics exist, keep them per instance. Averaging or summing
those quantiles does not reconstruct the combined request distribution. *[unverified target telemetry]*

## Error ratio depends on counter type

### Cumulative counters

Apply `rate()` to each cumulative series before `sum()`. Dividing raw cumulative totals describes the
population since process start and is distorted by resets.

*[sourced: WQL `rate()` and aggregation documentation; unverified for target counter types/metrics]*

```text
100 * sum(rate(ts(app.http.requests.errors, app="checkout")))
    / sum(rate(ts(app.http.requests.count, app="checkout")))
```

`rate()` reports positive change and can leave a gap at a counter reset. On PCF, instance restarts are
routine, so inspect the target's reset, reporting, and gap behavior before this becomes alert evidence;
prefer delta counters when the emitted contract supports them. *[sourced: WQL `rate()` and delta-counter
documentation; unverified for target emission and restart pattern]*

### Delta counters

Delta counters report change for an interval and are queried with `cs()`. Do not apply cumulative-counter
`rate()` semantics to them.

*[sourced: WQL delta-counter and `cs()` documentation; unverified for target counter types/metrics]*

```text
100 * sum(cs(app.http.requests.errors, app="checkout"))
    / sum(cs(app.http.requests.count, app="checkout"))
```

When the numerator is absent during clean periods, a narrowly scoped default can render zero. Confirm
that doing so will not conceal late or missing telemetry.

*[sourced: WQL `default()` behavior; unverified for target emission and alert policy]*

```text
100 * default(0, sum(cs(app.http.requests.errors, app="checkout")))
    / sum(cs(app.http.requests.count, app="checkout"))
```

Use `default()` sparingly. Filling a delayed point can prevent a threshold from seeing collection loss,
and a selector that matches no series for the whole window needs a separate no-data path. *[sourced: WQL
`default()` and missing-data documentation; unverified for target lateness and alert lifecycle]*

## Rates, windows, and saturation

*[sourced: WQL function reference; unverified for target metrics and operational suitability]*

```text
rate(ts(app.messages.processed))
deriv(ts(app.queue.depth))
mavg(5m, ts(app.http.requests.latency))
align(1m, mean, ts(app.http.requests.latency))
100 * ts(app.container.memory.usage) / ts(app.container.memory.limit)
```

Keep query units and the source metric type in the evidence packet. A syntactically valid function can
still be semantically wrong for the selected metric.

## Missing data

Test the expected reporting interval separately from an ordinary threshold. For a metric expected once
per minute, a five-minute count should be interpreted against that cadence; a known series that stops
and a selector that has never matched are different conditions.

*[sourced: WQL `mcount()` and missing-data alert guidance, byte-verified at
wavefrontHQ/docs@0492d79 `pages/doc/alerts_missing_data.md:54-77`; unverified for target
interval/metric]*

```text
mcount(5m, ts(app.http.requests.count, app="checkout")) < 5
```

For a sustained gap, `mcount()` can decay to zero and later stop returning a series. Holding the last
known count across a bounded window is one documented candidate for keeping the condition evaluable.

*[sourced: WQL missing-data alert guidance, byte-verified at wavefrontHQ/docs@0492d79
`pages/doc/alerts_missing_data.md:164`; unverified for target interval, lifecycle, and metric]*

```text
last(1h, mcount(3m, ts(app.http.requests.count, app="checkout"))) = 0
```

Treat this as a candidate only after verifying its behavior in the target alert lifecycle. Configure the
platform's no-data notification path for ordinary thresholds whose series vanishes and for selectors
that match nothing at all. Do not describe a no-data state as healthy. *[sourced: WQL alert states and
missing-data guidance; unverified for target notification configuration]*

## WQL and PromQL mapping aid

The following pairs explain intent; they are not byte-for-byte semantic equivalence across all data and
staleness conditions.

- WQL `sum(ts(m), tag)` roughly maps to PromQL `sum by (label) (m)`.
- WQL `rate(ts(counter))` roughly maps to PromQL `rate(counter[5m])`.
- WQL `mavg(5m, ts(m))` is a moving-window operation.

*[sourced: WQL aggregation/rate documentation and Prometheus language docs; unverified target parity]*

## Investigation handoff

Overlay the exact deploy timestamp, then keep both the aggregate and the dimension that isolates an
outlier. Hand the `observability-engineer` agent the query, window, threshold, value, and missing-data behavior.
Ownership map only—not a load: the `obs-alerting` skill owns alert and SLO design.

## Inert canary example

The expression is a reference-loading fixture, not a target metric claim.

*[sourced: WQL `ts()` and trailing grouping syntax; unverified for placeholder metric/tags]*

```text
sum(ts(<fixture.metric>, app="<fixture_app>"), app)
```

Expected fixture output (inert):

```text
q_omwql_7b31
```
