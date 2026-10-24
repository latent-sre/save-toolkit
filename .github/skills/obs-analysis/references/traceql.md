# Tempo TraceQL for trace investigation

Primary reference:

- [Construct a TraceQL query](https://grafana.com/docs/tempo/latest/traceql/construct-traceql-queries/)
- [Grafana Tempo query-builder examples](https://grafana.com/docs/grafana/latest/datasources/tempo/query-editor/traceql-search/)

## Scope and spanset rules

Intrinsics use `scope:name`; custom attributes use `scope.name`. Conditions inside one pair of
braces must match the same span; spansets joined with `&&` may match different spans in one trace.

## Beyond the basic shapes — version-gated TraceQL

Version-sensitive features include structural operators (`>` direct child, `>>` descendant,
`<<` ancestor, `~` sibling), TraceQL metrics functions
(`rate`, `count_over_time`, `quantile_over_time`, `compare`, `topk`), `select()`, and `event:` /
`link:` / `instrumentation:` scopes. TraceQL metrics are GA from Tempo 3.0, but **alerting on a
TraceQL metrics query remains experimental**, is limited to a 24-hour query window, and is not a
Grafana Managed Alerts data source. Other operators/scopes remain version- or block-format-gated
(some need vParquet5+). Confirm the deployed Tempo version before using any of them in a shared
query.

## Limits and discard reasons — absence causes

A missing trace can be a limit casualty, not a telemetry gap. `max_bytes_per_trace` (upstream
default 5000000 = 5 MB) is enforced in three places: ingestion refuses (`TRACE_TOO_LARGE: max size
of trace (5000000) exceeded while adding 387 bytes`), compaction partially drops, and **search
silently skips** oversized traces. Ingest discard reasons are observable as a `reason` label:
`rate_limited` (`rate_limit_bytes`), `live_traces_exceeded` (`max_traces_per_user`),
`trace_too_large`, and `invalid_trace_id`/`invalid_span_id`. Record the exact error or discard
reason verbatim; write-side pressure is a pipeline finding for the `obs-pipeline` skill. Which
limits bind this tenant is unknown until read from the deployed overrides.
