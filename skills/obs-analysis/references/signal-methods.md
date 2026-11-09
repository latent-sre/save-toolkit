# Signal methods: population, coverage and limits

## Logs

- Bind source and window before symptom filters: `error` misses structured failed requests.
  Confirm field extraction before filtering; an absent field can produce an empty result.
  Run the dialect's freshness check before interpreting silence as no failures.
- For error spikes, count inside complete fixed-width buckets. Filtering failures first erases
  quiet buckets and biases the baseline. Exclude the current bucket from its trailing baseline;
  retain first anomalous and last known-normal buckets plus timed deploy/config events.
- Request ratios need a verified completion population and classification coverage, not a
  denominator of arbitrary application logs.
- A request/correlation ID starts in logs. Map it to an actual trace ID before a trace lookup.
  A hop without a common identifier is a telemetry gap; recommend instrumentation to the caller.

## Metrics

- A fleet request percentile needs the same population's distributions merged across instances;
  per-instance percentiles, point values and precomputed quantiles cannot recover it.
- Bind failures and
  eligible requests to the same population/window; absent denominators or zero traffic are not
  healthy zero.
- Distinguish a reported zero, a late point, a previously known series that stopped, and a
  selector that never matched. Display gap-filling can hide collection loss. Record reporting
  interval, lookback and applicable alert no-data policy; missing metadata remains a gap.
- For unusual query functions, confirm official backend documentation and retain its URL,
  retrieval date and evidence label.

Query evidence includes meaning/type, units, population, cadence, grouping and missing-data
interpretation. An alert/SLO recommendation to `observability-engineer` also needs the exact
query, window, threshold, current value and no-data behavior.

## Traces

Use an actual trace ID (mapped from logs as above) and the request's UTC window for direct lookup.
Without an ID, search service/environment, operation and symptom in a bounded window; record how
the representative trace was selected. One sampled request does not establish prevalence.

- A long span locates elapsed time, not its cause. Do not add nested durations. A visual gap can
  be uninstrumented work, scheduling, propagation loss or clocks, rather than proven idle time.
- In a full investigation, compare slow and known-normal traces from the same route/deployment
  cohort, or name the missing comparison. A wide client span with a narrow server span only
  hypothesizes time outside the handler.
- Interpret status and protocol outcome under the span kind's [OTel convention](./otel-semantics.md).
  An unset status is not success.
- Absent spans/traces/logs can result from sampling, retention, size limits, propagation, export
  or instrumentation gaps; they do not prove the request or call never happened.

Full-investigation evidence includes entry/window, source links, selection method, affected and
comparison IDs, critical-path table, protocol/status interpretation, missing hops and sampling
limits. A supplied-span explanation needs only the answer, supplied scope, and uncertainty.
