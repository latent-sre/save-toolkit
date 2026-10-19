# Tempo TraceQL for trace investigation

Use this reference only after applying the parent skill's product-agnostic investigation shape. Syntax
and language behavior below follow the current Grafana Tempo documentation. The deployed
Tempo/Grafana version, tenant, retention, time range, attributes, and results remain unverified until
checked against the team's target.

Primary reference:

- [Construct a TraceQL query](https://grafana.com/docs/tempo/latest/traceql/construct-traceql-queries/)
- [Grafana Tempo query-builder examples](https://grafana.com/docs/grafana/latest/datasources/tempo/query-editor/traceql-search/)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)

## Contents

- Scope and spanset rules
- Beyond the basic shapes — version-gated TraceQL
- Limits and discard reasons — absence causes
- Record the result boundary

## Scope and spanset rules

Curly braces select spans. An intrinsic uses a colon after its scope, while a custom attribute uses a
dot-qualified scope. Conditions inside one pair of braces must match the same span. By contrast, two
spansets joined with `&&` may match different spans in one trace. A pipeline can then aggregate or filter
the selected spanset.

Keep the query time picker narrow even when the expression names a trace. Confirm the exact tenant and
time range in the evidence packet; a syntactically valid query against the wrong tenant is empty evidence.

## Beyond the basic shapes — version-gated TraceQL

Current Tempo documents more than the `&&` spanset join used above: structural operators (`>`
direct child, `>>` descendant, `<<` ancestor, `~` sibling), TraceQL metrics functions
(`rate`, `count_over_time`, `quantile_over_time`, `compare`, `topk`), `select()`, and `event:` /
`link:` / `instrumentation:` scopes. TraceQL metrics are GA from Tempo 3.0, but **alerting on a
TraceQL metrics query remains experimental**, is limited to a 24-hour query window, and is not a
Grafana Managed Alerts data source. Other operators/scopes remain version- or block-format-gated
(some need vParquet5+). Confirm the deployed Tempo version before using any of them in a shared
query, and label the result with that version.

## Limits and discard reasons — absence causes

A missing trace can be a limit casualty, not a telemetry gap. `max_bytes_per_trace` (upstream
default 5000000 = 5 MB) is enforced in three places: ingestion refuses (`TRACE_TOO_LARGE: max size
of trace (5000000) exceeded while adding 387 bytes`), compaction partially drops, and **search
silently skips** oversized traces. Ingest discard reasons are observable as a `reason` label:
`rate_limited` (`rate_limit_bytes`), `live_traces_exceeded` (`max_traces_per_user`),
`trace_too_large`, and `invalid_trace_id`/`invalid_span_id`. Record the exact error or discard
reason verbatim; write-side pressure is a pipeline finding for the `obs-pipeline` skill. Which
limits bind this tenant is unknown until read from the deployed overrides.

## Record the result boundary

For every query, return the expression, absolute UTC window, tenant/data source, deployed version if
known, result count, selected trace link, and any required attribute assumptions. Label observed target
results `[verified]` only when they were actually run and retained; these examples remain unconfirmed
for the target.
