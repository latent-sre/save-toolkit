# Tempo TraceQL for trace investigation

## Scope, spansets, and version-gated features

- Intrinsics use `scope:name` (or shorthand like `duration`); custom attributes use `scope.name`.
  Conditions inside one `{ ... }` block match the same span; spansets joined with `&&` match
  different spans within the same trace.
- Structural operators, metrics functions, `select()`, and event/link/instrumentation scopes depend
  on deployed Tempo version and block format. Metrics query max lookback is configured via
  `query_frontend.metrics.max_duration` and tenant `max_metrics_duration`. Direct TraceQL alerting
  (`tempoAlerting`) is experimental and off by default.

## Limits and discard reasons

A missing trace may be dropped by limits rather than absent upstream: `max_bytes_per_trace` (upstream
default `5000000` / 5 MB) in Tempo 3.0+ accepts spans and drops oversized traces downstream during
compaction/search (pre-3.0 rejected at ingest with `TRACE_TOO_LARGE`). Observe drops verbatim via
the `reason` label on `tempo_discarded_spans_total` (`rate_limited`, `live_traces_exceeded`,
`trace_too_large`, `trace_too_large_to_compact`, `invalid_trace_id`, `invalid_span_id`,
`unknown_error`) — write-side drops are pipeline findings ([Alloy pipeline](./alloy.md)); check
deployed tenant overrides rather than upstream defaults.
