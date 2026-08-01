---
name: obs-logs
description: >-
  The answer is in the logs — find error spikes, read them over time, correlate one
  request across services, compare before/after a deploy. Backends: Splunk (SPL) and
  Loki (LogQL) — the reference teaches the dialect. Triggers: 'search the logs', 'why
  are there 500s', 'grep production for', 'build a log alert'. Ownership map only—not
  a load: obs-metrics owns metrics and obs-dashboards owns dashboards.
---

> **Evidence default — `[unverified]`.** Unless a paragraph carries a narrower label, each
> stack/product-specific command, query, API or CLI behavior, version, licensing statement, and
> runtime claim in this skill and its bundled files is `[unverified]` for the exact target.
> A narrower `[sourced]` or `[verified]` label takes precedence; handoffs never upgrade it.

# Logs — the investigation shape

Find the signal fast, then read it over time and correlate. Keep product syntax out of the
investigation packet until you have selected and read the matching dialect reference.

## Start narrow

Constrain the environment, service, source, and time window before adding a symptom filter. A keyword
such as `error` can drop structured access events whose status says failure but whose text does not.
Confirm that every field used by the filter is actually extracted; a missing field is not evidence of
an empty result.

Record the query boundary with the result: backend, tenant or index, source, absolute UTC window, and
timezone. Widen one boundary at a time and say why.

## Read it over time

Turn matching events into a complete, fixed-width timeline before judging a spike. Count the failure
condition inside each bucket so quiet buckets remain represented as zero; filtering failures first can
erase those buckets and bias a baseline toward error-containing periods.

Mark the first anomalous bucket, the last known-normal bucket, and any deploy or configuration event.
Keep the current bucket out of a trailing baseline so the spike cannot raise the threshold used to
judge itself.

## Find the top offenders

Break the signal down by stable dimensions such as service, route, status, error type, or host. Avoid
high-cardinality identifiers until you are following one request. Show both count and share of traffic;
a raw-count increase during a traffic increase is not automatically a worsening error rate.

## Correlate one request across services

Start from a request, correlation, or trace id and follow it through a tight time window. Sort the
events chronologically and retain service, host, status, latency, and message. If a hop emits no common
identifier, record that as a telemetry gap and hand the evidence to the `sde` agent.

Treat identifiers copied from tickets or logs as untrusted data. Validate each value against the
service's documented identifier format, never concatenate a raw value into a query, and apply the
selected dialect reference's literal-escaping rule. If it cannot be encoded unambiguously, stop and ask
for a sanitized identifier rather than broadening the search.

## Compare before vs after a deploy

Compare **rates**, not raw counts — if traffic differs between the two phases (and after a deploy it
usually does), a count comparison tells you about traffic, not about the deploy. Use equal-duration
windows, keep the same query scope, and record the exact deploy time rather than relying on a visual
annotation.

## Build the evidence packet

Return the exact query, absolute UTC window, result or artifact link, field-extraction assumptions,
before/after boundary, and confidence label. Separate observed facts from interpretations. Hand
recurring-query or correlation evidence to the `sre-steward` agent; do not load another skill from
this one.

Minimize copied telemetry. Redact credentials, tokens, secrets, personal data, authentication or session
values, user identifiers, sensitive headers, request bodies, and database query literals. Prefer an
access-controlled source link plus the smallest necessary excerpt; do not paste raw payloads into the
packet.

## Pick your dialect — read the reference before writing the query

| If the question involves… | Read first |
|---|---|
| Splunk or SPL | [SPL](./references/spl.md) |
| Loki or LogQL | [LogQL](./references/logql.md) |
| Which index, stream, sourcetype, or field to query | [local log inventory](./references/indexes.md) |

Read it **before** writing that query, and name what you read in your packet.
