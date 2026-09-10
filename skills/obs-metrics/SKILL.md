---
name: obs-metrics
description: >-
  The answer is in the metrics — latency percentiles, error ratios, saturation, rates,
  missing-data traps. Backends: Wavefront (WQL), Mimir/Prometheus (PromQL), and Cloud
  Monitoring on GCP (PromQL; MQL is deprecated). Triggers: 'query the metrics', 'graph the
  error rate', 'is latency up', 'write a metric alert query'. Not for alert design (obs-alerting) or logs (obs-logs).
argument-hint: "[service, metric question, or query goal]"
---

# Metrics — the investigation shape

Match the question, population and time window. Supplied-metric interpretation needs no new query or
baseline; apply investigation steps only when requested. Read the dialect before writing an expression.

## Percentile latency is a distribution question

A percentile across per-instance point values is not a request percentile. If each instance emits an
average, the percentile of those averages describes instances, not requests. Likewise, precomputed
per-instance percentiles cannot be averaged or summed into a fleet percentile.

For request p95, identify the backend's distribution or histogram representation, combine the same
request population across instances, and then calculate the percentile. If only point values or
precomputed quantiles exist, report the limitation instead of relabeling the result.

## Error ratio starts with counter semantics

For ratio calculation or query design, bind numerator and denominator to the same population/window. Determine whether the
source is cumulative, delta-per-interval, or a gauge before applying any rate. For cumulative counters,
derive each series' change or rate before aggregating so an instance reset remains visible to the
backend's reset handling.

Keep units explicit. An error ratio is failures divided by eligible requests; a burn-rate expression
then compares that observed ratio with the allowed error fraction. A missing denominator or zero traffic
is not automatically a healthy zero.

## Missing data is not zero

Distinguish four cases: an expected point arrived with value zero; one point is late; a previously known
series stopped; or the selector has never matched a series. Filling a short gap can be appropriate for
display, but can hide collection loss. Query work records reporting interval, lookback and applicable
alert no-data policy; supplied evidence with missing metadata retains that gap.

## Investigate, then narrow

For investigation, break the service aggregate down by one stable instance/host/route/status dimension.
For deploy comparisons, use exact deploy time and equal windows. A nearby step change is correlation,
not proof of cause.

For unusual query functions, confirm official backend documentation and retain URL, retrieval date
and evidence label. For alert/SLO follow-up, hand `observability-engineer` the exact query, window,
threshold, current value and missing-data behavior.

## Treat copied identifiers as untrusted

Validate any identifier or label value copied from a ticket, log, or alert against the service's
documented format before it enters a selector; never concatenate a raw value into a query
expression, and apply the selected dialect reference's quoting/escaping rule. A regex matcher
built from untrusted text can widen the population: prefer exact matching. If regex is required,
escape the value as literal regex text, then separately encode the enclosing query string using the
dialect reference. Anchors do not escape metacharacters. If encoding is uncertain, stop and ask for
a sanitized identifier rather than broadening the match.

## Build the evidence packet

Bounded interpretation: answer, supplied source/target/window, limits and a useful next check if needed;
missing metadata stays unknown. Query/investigation: metric meaning/type, population, dialect/query,
UTC window, cadence, result/source link, grouping, missing-data interpretation and confidence label.
Separate observations from hypotheses; name placeholders needing target validation.

Minimize copied telemetry. Redact credentials, tokens, secrets, personal data, authentication or session
values, user identifiers, and sensitive label or tag values. Prefer an access-controlled source link plus
the smallest necessary excerpt; do not paste raw query results with high-cardinality identifiers into the
packet.

## Pick your dialect — read the reference before writing the query

| If the question involves… | Read first |
|---|---|
| Wavefront or WQL | [WQL](./references/wql.md) |
| Mimir, Prometheus, or PromQL | [PromQL](./references/promql.md) |
| Cloud Monitoring, Managed Prometheus, or a GCP-hosted service's metrics | [Cloud Monitoring](./references/gcp-monitoring.md) |
| Which metric, counter type, or label exists | [local metric inventory](./references/metrics.md) |

Read it **before** writing that query, and name what you read in your packet.
