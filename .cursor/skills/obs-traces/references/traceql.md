# Tempo TraceQL for trace investigation

Use this reference only after applying the parent skill's product-agnostic investigation shape. Syntax
and language behavior below are sourced from the current Grafana Tempo documentation, retrieved
2026-07-14. The deployed Tempo/Grafana version, tenant, retention, time range, attributes, and results
remain unverified until checked against the team's target.

Primary reference:

- [Construct a TraceQL query](https://grafana.com/docs/tempo/latest/traceql/construct-traceql-queries/)
- [Grafana Tempo query-builder examples](https://grafana.com/docs/grafana/latest/datasources/tempo/query-editor/traceql-search/)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)

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
instrumentation actually emits before treating an empty result as meaningful.

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

## Record the result boundary

For every query, return the expression, absolute UTC window, tenant/data source, deployed version if
known, result count, selected trace link, and any required attribute assumptions. Label observed target
results `[verified]` only when they were actually run and retained; these examples remain `[unverified]`
for the target.

Ownership map only—not a load: the `obs-pipeline` skill owns trace instrumentation.

## Inert canary example

This checks reference loading only; it is not a production trace or a claim that the target was queried.

*[sourced: Grafana Tempo trace-id filtering syntax; unverified for target availability]*

Expected fixture output (inert):

```text
q_otql_7b3e
```
