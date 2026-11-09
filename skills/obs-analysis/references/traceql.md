# Tempo TraceQL for trace investigation

## Scope and spanset rules

Intrinsics use `scope:name` (short forms such as `duration` also work); custom attributes use `scope.name`. Conditions inside one pair of
braces must match the same span; spansets joined with `&&` may match different spans in one trace.

## Beyond the basic shapes — version-gated TraceQL

Structural operators, metrics functions,
`select()` and event/link/instrumentation scopes depend on the deployed version and block format.
Check those capabilities before using them in shared queries.

Metrics query windows are configurable (`query_frontend.metrics.max_duration` and tenant
`max_metrics_duration`), not an immutable 24-hour ceiling. Grafana documents direct TraceQL alerting
behind the experimental `tempoAlerting` feature flag; do not assume production support or enable it
through an analysis task. Alert design stays with `obs-alerting`.

## Limits and discard reasons — absence causes

A missing trace can be a limit casualty, not a telemetry gap. `max_bytes_per_trace` (upstream
default 5000000 = 5 MB) drops oversized traces without telling the client: since Tempo 3.0 it accepts the
spans and discards the trace downstream (before 3.0 it refused them at ingest with `TRACE_TOO_LARGE`),
compaction partially drops, and **search silently skips** oversized traces. Discard reasons are
observable as the `reason` label on `tempo_discarded_spans_total`:
`rate_limited` (`rate_limit_bytes`), `live_traces_exceeded` (`max_traces_per_user`),
`trace_too_large`, and `invalid_trace_id`/`invalid_span_id`. Record the exact error or discard
reason verbatim; write-side pressure is a pipeline finding for the `obs-pipeline` skill. Which
limits bind this tenant is unknown until read from the deployed overrides.
