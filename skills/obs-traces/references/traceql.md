# Tempo TraceQL for trace investigation

Use this reference only after applying the parent skill's product-agnostic investigation shape. Syntax
and language behavior below are sourced from the current Grafana Tempo documentation, retrieved
2026-07-14. The deployed Tempo/Grafana version, tenant, retention, time range, attributes, and results
remain unverified until checked against the team's target.

Primary reference:

- [Construct a TraceQL query](https://grafana.com/docs/tempo/latest/traceql/construct-traceql-queries/)
- [Grafana Tempo query-builder examples](https://grafana.com/docs/grafana/latest/datasources/tempo/query-editor/traceql-search/)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)

## Contents

- Scope and spanset rules
- Start from a trace id
- Start from a latency symptom
- Find a service span with an HTTP 5xx outcome
- Find a service trace that also contains a database span
- Find traces with repeated error-status spans for one service
- Beyond these shapes — version-gated TraceQL
- Limits and discard reasons — absence causes
- Record the result boundary

## Scope and spanset rules

Curly braces select spans. An intrinsic uses a colon after its scope, while a custom attribute uses a
dot-qualified scope. Conditions inside one pair of braces must match the same span. By contrast, two
spansets joined with `&&` may match different spans in one trace. A pipeline can then aggregate or filter
the selected spanset.

*[sourced: Grafana Tempo, “Construct a TraceQL query”; unverified for deployed version and data]*

Keep the query time picker narrow even when the expression names a trace. Confirm the exact tenant and
time range in the evidence packet; a syntactically valid query against the wrong tenant is empty evidence.

## Start from a trace id

Use the trace-level intrinsic for an exact trace id. The value below is the W3C example fixture, not a
production identifier.

*[sourced: Grafana Tempo intrinsic fields/string literals and W3C Trace Context trace-id example;
unverified against target]*

```traceql
{ trace:id = "4bf92f3577b34da6a3ce929d0e0e4736" }
```

Do not splice arbitrary ticket or log text into an expression. Validate the copied id as the expected
hex value and keep it inside the quoted value position.

## Start from a latency symptom

The trace-level duration intrinsic is the trace's maximum span end minus minimum span start. It avoids
reconstructing total trace duration from individual spans.

*[sourced: Grafana Tempo trace-level intrinsics and duration literals; unverified threshold/window]*

```traceql
{ trace:duration > 2s }
```

This finds examples above a threshold; it does not calculate prevalence. Retain the search window and
selection method, then compare a representative slow trace with a normal trace from the same operation.

## Find a service span with an HTTP 5xx outcome

Resource attributes identify the emitting service, while span attributes describe the operation. The
HTTP attribute below follows the current stable OpenTelemetry HTTP convention; confirm what the deployed
instrumentation actually emits before treating an empty result as meaningful. Current Tempo
documentation still includes examples using legacy `span.http.status_code`; that is a query example
for telemetry emitting the old convention, not the current OpenTelemetry contract.

*[sourced: Grafana Tempo query-builder example/attribute scopes and current OTel HTTP semantic
conventions; unverified for target attributes]*

```traceql
{ resource.service.name = "checkout" && span.http.response.status_code >= 500 }
```

Both conditions are inside one pair of braces, so they must be true on the same span.

## Find a service trace that also contains a database span

Use separate spansets when the service span and database span may be different spans. `!= nil` tests that
the current stable database-system attribute is present.

*[sourced: Grafana Tempo logical spanset operators/nil and current OTel database semantic conventions;
unverified for target attributes]*

```traceql
{ resource.service.name = "checkout" } && { span.db.system.name != nil }
```

This proves only that both matching spansets occur in the same returned trace. It does not by itself
prove that the selected service called that database span; inspect parent/child or link structure.

## Find traces with repeated error-status spans for one service

The status intrinsic is an enum. `count()` counts the spans in the selected spanset for each trace, so
the following retains traces containing more than one matching error-status span.

*[sourced: Grafana Tempo status intrinsic, pipeline, and `count()` examples; unverified for target data]*

```traceql
{ resource.service.name = "orders" && span:status = error } | count() > 1
```

Span error status and protocol response status are different evidence. Read
[OpenTelemetry semantics](./otel-semantics.md) before interpreting either.

## Beyond these shapes — version-gated TraceQL

Current Tempo documents more than the `&&` spanset join used above: structural operators (`>`
direct child, `>>` descendant, `<<` ancestor, `~` sibling), TraceQL metrics functions
(`rate`, `count_over_time`, `quantile_over_time`, `compare`, `topk`), `select()`, and `event:` /
`link:` / `instrumentation:` scopes. TraceQL metrics are GA from Tempo 3.0, but **alerting on a
TraceQL metrics query remains experimental**, is limited to a 24-hour query window, and is not a
Grafana Managed Alerts data source. Other operators/scopes remain version- or block-format-gated
(some need vParquet5+). Confirm the deployed Tempo version before using any of them in a shared
query, and label the result with that version. *[sourced: Tempo 3.0 release notes; Tempo metrics-query
limitations; TraceQL construct-query documentation; re-checked 2026-08-24]*

## Limits and discard reasons — absence causes

A missing trace can be a limit casualty, not a telemetry gap. `max_bytes_per_trace` (upstream
default 5000000 = 5 MB) is enforced in three places: ingestion refuses (`TRACE_TOO_LARGE: max size
of trace (5000000) exceeded while adding 387 bytes`), compaction partially drops, and **search
silently skips** oversized traces. Ingest discard reasons are observable as a `reason` label:
`rate_limited` (`rate_limit_bytes`), `live_traces_exceeded` (`max_traces_per_user`),
`trace_too_large`, and `invalid_trace_id`/`invalid_span_id`. Record the exact error or discard
reason verbatim; write-side pressure is a pipeline finding for the `obs-pipeline` skill. Which
limits bind this tenant is `[unverified]` until read from the deployed overrides. *[sourced:
grafana/tempo@494bf22 manage-trace-ingestion and configuration docs]*

## Record the result boundary

For every query, return the expression, absolute UTC window, tenant/data source, deployed version if
known, result count, selected trace link, and any required attribute assumptions. Label observed target
results `[verified]` only when they were actually run and retained; these examples remain `[unverified]`
for the target.
