---
name: obs-metrics
description: >-
  The answer is in the metrics — latency percentiles, error ratios, saturation, rates,
  missing-data traps. Backends: Wavefront (WQL), Mimir/Prometheus (PromQL), and Cloud
  Monitoring on GCP (PromQL; MQL is deprecated). Triggers: 'query the metrics', 'graph the
  error rate', 'is latency up', 'write a metric alert query'. Not for alert design (obs-alerting) or logs (obs-logs).
  Deciding what a live page means or what to do next belongs to incident-investigation, which
  routes query work here.
argument-hint: "[service, metric question, or query goal]"
---

# Metrics — the investigation shape

Match the question, population and time window. Supplied-metric interpretation needs no new query or
baseline; apply investigation steps only when requested. Read the dialect before writing an expression.

**Grafana pointer:** dashboard/Explore access, panel configuration, datasource selection, and alert
operations live in `grafana`. This skill owns metric meaning, PromQL/WQL, and result interpretation;
using a Grafana-backed query does not move those responsibilities or authorize a write.

## Percentile latency is a distribution question

A percentile across per-instance point values (or precomputed per-instance percentiles) describes
instances, not requests, and cannot be averaged or summed into a fleet percentile. For request p95,
combine the same request population's distribution or histogram across instances first, then take
the percentile; if only point values or precomputed quantiles exist, report that limitation.

## Error ratio starts with counter semantics

Bind numerator and denominator to the same population and window, and determine whether the source
is cumulative, delta-per-interval, or a gauge before applying any rate; for cumulative counters,
derive each series' rate before aggregating so resets stay visible. An error ratio is failures
divided by eligible requests; a missing denominator or zero traffic is not a healthy zero.

## Missing data is not zero

Distinguish four cases: an expected point arrived with value zero; one point is late; a previously known
series stopped; or the selector has never matched a series. Filling a short gap can be appropriate for
display, but can hide collection loss. Query work records reporting interval, lookback and applicable
alert no-data policy; supplied evidence with missing metadata retains that gap.

## Investigate, then narrow

For deploy comparisons, use the exact deploy time and equal windows; a nearby step change is
correlation, not proof of cause. For unusual query functions, confirm official backend documentation
and retain URL, retrieval date and evidence label. For alert/SLO follow-up, hand
`observability-engineer` the exact query, window, threshold, current value and missing-data behavior.

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

Minimize copied telemetry. Redact credentials, tokens, secrets, personal data, authentication or
session values, and user identifiers before any excerpt enters the packet; prefer an
access-controlled source link plus the smallest necessary excerpt. Also redact sensitive label or
tag values; do not paste raw query results with high-cardinality identifiers into the packet.

## Pick your dialect — read the reference before writing the query

| If the question involves… | Read first |
|---|---|
| Wavefront or WQL | [WQL](./references/wql.md) |
| Mimir, Prometheus, or PromQL | [PromQL](./references/promql.md) |
| Cloud Monitoring, Managed Prometheus, or a GCP-hosted service's metrics | [Cloud Monitoring](./references/gcp-monitoring.md) |
| Which metric, counter type, or label exists | [local metric inventory](./references/metrics.md) |

Read it **before** writing that query, and name what you read in your packet.
