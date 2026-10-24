# Log analysis: population and coverage

- Bind source and window before symptom filters: `error` misses structured failed requests.
  Confirm field extraction before filtering; an absent field can produce an empty result.
  Run the dialect's freshness check before interpreting silence as no failures.
- For error spikes, count inside complete fixed-width buckets. Filtering failures first erases
  quiet buckets and biases the baseline. Exclude the current bucket from its trailing baseline;
  retain first anomalous and last known-normal buckets plus timed deploy/config events.
- Group stable service, route, status, error type or host; show counts and traffic share.
  Traffic growth alone is not a worse error rate. Request ratios need a verified completion
  population and classification coverage, not a denominator of arbitrary application logs.
- A request/correlation ID starts in logs. Map it to an actual trace ID before a trace lookup.
  A hop without a common identifier is a telemetry gap; recommend instrumentation to the caller.
- Keep field-extraction assumptions and comparison boundaries with query evidence. Complete
  time buckets do not prove complete ingestion; no events may mean missing telemetry.
