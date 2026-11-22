# Signal methods: population, coverage, and limits

## Logs

- Bind source and UTC window before symptom filters (`error` misses structured failed requests);
  confirm field extraction and run the dialect's freshness check before treating silence as no errors.
- Count error spikes inside complete fixed-width buckets (`timechart`/histograms), excluding the
  incomplete current bucket from its trailing baseline. Compute request ratios against a verified
  completion population and classification coverage, not arbitrary application log counts.
- Map correlation/request IDs in logs to a trace ID before trace lookup; missing shared IDs across
  hops are an instrumentation gap.

## Metrics

- Compute fleet percentiles by merging histograms/distributions across instances (`sum by (..., le)`
  before `histogram_quantile`); never average per-instance precomputed quantiles.
- Bind failures and eligible requests to the same population/window; absent denominators or zero
  traffic are not healthy zero. Distinguish reported zero, late points, stopped series, and
  unmatched selectors (`absent()` vs. display gap-filling).

## Traces

- Look up by exact trace ID + UTC window when known; otherwise search service/environment/operation
  and document how the representative trace was chosen (one trace does not prove prevalence).
- Do not sum nested span durations; gaps can be uninstrumented work, queueing, or clock skew. A
  wide client span beside a narrow server span only hypothesizes time outside the handler.
- Interpret status under [OTel conventions](./otel.md) (`Unset` != success). Absent spans can come
  from sampling, retention, size caps, propagation loss, or export drops.
