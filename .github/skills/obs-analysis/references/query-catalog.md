# Log query starting points

Selectors and field names below are examples/placeholders, not established team targets. Resolve
them on the target; use [SPL](./spl.md) for dialect semantics. A maintained entry
records its purpose, owner and target/query/window/result evidence from a named authorized executor.
Running an example does not make it accepted team policy. Keep sensitive parameters in an
access-controlled saved search rather than this catalog.

Use the invoked lane's permitted query path and output protections. The standard SRE profile has
no Splunk execution path: return the query for an authorized executor. Diagnostic reads do not
permit saved-search edits or other writes.

### Did error rate change across the deploy? Where did one request fail across services?

Use SPL's [deploy comparison](./spl.md#compare-before-vs-after-a-deploy) and
[cross-service correlation](./spl.md#correlate-one-request-across-services).

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
delivery failures lose lines.
