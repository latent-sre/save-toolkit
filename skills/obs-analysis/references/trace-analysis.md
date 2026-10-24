# Trace analysis: sampling and timing limits

Use an actual trace ID and request UTC window for direct lookup; a request/correlation ID needs
mapping through [logs](./log-analysis.md) first. Without an ID, search service/environment,
operation and symptom in a bounded window; record how the representative trace was selected.
One sampled request does not establish prevalence.

- A long span locates elapsed time, not its cause. Do not add nested durations. A visual gap can
  be uninstrumented work, scheduling, propagation loss or clocks, rather than proven idle time.
- In a full investigation, compare slow and known-normal traces from the same route/deployment
  cohort, or name the missing comparison. A wide client span with a narrow server span only
  hypothesizes time outside the handler.
- For asynchronous work, use links, timestamps and message identity; distinguish queue delay
  from consumer processing instead of imposing synchronous nesting.
- Interpret status and protocol outcome under the span kind's [OTel convention](./otel-semantics.md).
  An unset status is not success. Correlate logs by the same trace ID, UTC time and service.
- Absent spans/traces/logs can result from sampling, retention, size limits, propagation, export
  or instrumentation gaps; they do not prove the request or call never happened.

Full-investigation evidence includes entry/window, source links, selection method, affected and
comparison IDs, critical-path table, protocol/status interpretation, missing hops and sampling
limits. A supplied-span explanation needs only the answer, supplied scope, and uncertainty.
