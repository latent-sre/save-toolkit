# Log query starting points

Selectors and field names below are examples/placeholders, not established team targets. Resolve
through [inventory](./indexes.md); use [SPL](./spl.md) for dialect semantics. A maintained entry
records its purpose, owner and target/query/window/result evidence from a named authorized executor.
Running an example does not make it accepted team policy. Keep sensitive parameters in an
access-controlled saved search rather than this catalog.

Use the invoked lane's permitted query path and output protections. The standard SRE profile has
no Splunk execution path: return the query for an authorized executor. Diagnostic reads do not
permit saved-search edits or other writes.

### Which errors started at the same time as the impact?

```spl
index=<app_index> sourcetype=<error_sourcetype> earliest=<start_epoch> latest=<end_epoch>
| bin _time span=1m
| stats count by _time, error_type
| sort 0 - _time
```

An onset shortlist, not a complete baseline. Check extraction/ingestion; use
[complete buckets](./spl.md#spot-a-spike-vs-the-baseline-anomaly-detection) for quiet periods and trailing baselines.

### Did error rate change across the deploy?

Use [SPL's deploy comparison](./spl.md#overall-deploy-error-rate) on one completion event per
eligible request/attempt, with equal windows around the known deploy time.
Its overall rate needs no `error_type`; the optional class breakdown keeps the phase denominator.
Missing/invalid status leaves the ratio null; no traffic or a missing phase is not healthy zero.

### Where did one request fail across services?

Resolve the shared correlation field on each service; logged hops are not a complete call graph.

```spl
index=<app_index> <correlation_field>="<validated_and_spl_escaped_id>" earliest=<start_epoch> latest=<end_epoch>
| table _time, service, status, latency_ms
| sort 0 _time
```

[`sort`](https://help.splunk.com/en/splunk-enterprise/spl-search-reference/10.4/search-commands/sort)
defaults to 10,000 rows; `sort 0` preserves the path at extra cost. Keep the window tight;
missing hops remain telemetry gaps until explained independently.

### Which callers are driving the current load?

Use request-completion events and a discovered caller field; compare the top counts with the
usual caller mix rather than treating a large caller as a fault.

```spl
index=<app_index> sourcetype=<request_completion_sourcetype> earliest=-30m latest=now
| stats count AS requests by <caller_field>
| sort - requests
| head 20
```

`stats by` drops missing caller fields; compare `count(<caller_field>)` against `count` first.

### Is the Akamai edge failing or missing cache for one hostname or region?

Use DataStream 2 JSON client-request logs only when `stack-profile` records Splunk as the destination.
The query measures five-minute hostname shares; `cacheStatus=0` means not in cache. Missing buckets
may be delivery gaps, not healthy zero.

With midgress enabled, emit `isMidgress` and select `0` (client-to-edge), excluding `1` (internal
edge-to-edge). Omit that predicate only for an independently verified client-only stream lacking
the field. Missing is not `0`: unknown composition/extraction blocks rates. `statusCode=0` means
the client left before a response; include it in requests, not 5xx.

```spl
index=<datastream_index> sourcetype=<datastream_sourcetype> earliest=<start_epoch> latest=<end_epoch> isMidgress=0
| bin _time span=5m
| stats count AS requests, count(eval(statusCode>=500 AND statusCode<600)) AS errors_5xx, count(eval(cacheStatus=0)) AS not_in_cache by _time, reqHost
| eval pct_5xx=round(100*errors_5xx/requests, 2), pct_not_in_cache=round(100*not_in_cache/requests, 2)
```

Acceptance: 100 client responses, all 200 with 80 cache hits, plus 20 internal 503/cache-miss
records must yield 100 requests, 0% 5xx, 20% not-in-cache. Verify this and missing/unknown-flag
refusal before use; it does not prove live extraction.

Add `country` (client origin) or `serverCountry` (serving location) for regional grouping;
`stats count by errorCode` narrows a spike. Inspect `reqHost` shape before filtering (it mirrors
Host). `akamai-edge`'s DataStream caveats still apply: low-latency streams are less complete and
delivery failures lose lines. Other destinations need equivalent fields in their own dialect.

Metric queries use the metric-analysis path in `obs-analysis`, not this log catalog.
