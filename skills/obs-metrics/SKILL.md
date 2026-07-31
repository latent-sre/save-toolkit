---
name: obs-metrics
description: >-
  The answer is in the metrics — latency percentiles, error ratios, saturation, rates,
  missing-data traps. Backends: Wavefront (WQL) and Mimir/Prometheus (PromQL). Triggers:
  'query the metrics', 'graph the error rate', 'is latency up', 'write a metric alert query'.
  Ownership map only—not a load: obs-alerting owns alert design and obs-logs owns logs.
---

> **Evidence default — `[unverified]`.** Unless a paragraph carries a narrower label, each
> stack/product-specific command, query, API or CLI behavior, version, licensing statement, and
> runtime claim in this skill and its bundled files is `[unverified]` for the exact target.
> A narrower `[sourced]` or `[verified]` label takes precedence; handoffs never upgrade it.

# Metrics — the investigation shape

Start with the operational question, the population it concerns, and the time window. Do not choose a
backend expression until you have selected and read the matching dialect reference.

## Percentile latency is a distribution question

A percentile across per-instance point values is not a request percentile. If each instance emits an
average, the percentile of those averages describes instances, not requests. Likewise, precomputed
per-instance percentiles cannot be averaged or summed into a fleet percentile.

For request p95, identify the backend's distribution or histogram representation, combine the same
request population across instances, and then calculate the percentile. If only point values or
precomputed quantiles exist, report the limitation instead of relabeling the result.

## Error ratio starts with counter semantics

Define numerator and denominator over the same population and evaluation window. Determine whether the
source is cumulative, delta-per-interval, or a gauge before applying any rate. For cumulative counters,
derive each series' change or rate before aggregating so an instance reset remains visible to the
backend's reset handling.

Keep units explicit. An error ratio is failures divided by eligible requests; a burn-rate expression
then compares that observed ratio with the allowed error fraction. A missing denominator or zero traffic
is not automatically a healthy zero.

## Missing data is not zero

Distinguish four cases: an expected point arrived with value zero; one point is late; a previously known
series stopped; or the selector has never matched a series. Filling a short gap can be appropriate for
display, but it can also hide collection loss. Record the reporting interval, lookback behavior, and
alert no-data policy with the query.

## Investigate, then narrow

Begin with the service aggregate and break it down by one stable dimension such as instance, host,
route, or status. Overlay the exact deploy time and compare equal windows. A step change near a deploy
is correlation evidence, not by itself proof that the deploy caused the change.

Confirm unusual functions against the current official backend documentation and retain the URL,
retrieval date, and evidence label. Hand the `sre-steward` agent the exact query, evaluation window,
threshold, current value, and missing-data behavior so it can author the alert/SLO follow-up.

## Build the evidence packet

Return the metric meaning and type, exact selector/query, absolute UTC window, step/evaluation cadence,
result or artifact link, grouping dimensions, missing-data interpretation, and confidence label.
Separate observed values from hypotheses and note every placeholder that still needs target validation.

## Pick your dialect — read the reference before writing the query

| If the question involves… | Read first |
|---|---|
| Wavefront or WQL | [WQL](./references/wql.md) |
| Mimir, Prometheus, or PromQL | [PromQL](./references/promql.md) |
| Which metric, counter type, or label exists | [local metric inventory](./references/metrics.md) |

Read it **before** writing that query, and name what you read in your packet.
