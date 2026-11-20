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
For each hostname and five-minute bucket, compare the known status and cache counts with requests.
Report each share only when its field covers every client request in that bucket. An absent bucket
may indicate a delivery gap.

With midgress enabled, emit `isMidgress` and select `0` (client-to-edge), excluding `1` (internal
edge-to-edge). Omit that predicate only for an independently verified client-only stream lacking
the field. Verify flag coverage before filtering. Unknown composition or flag extraction blocks
both rates. A literal `statusCode=0` counts as a known non-5xx request because the connection
ended before a response. For cache, `0` means absent and `1` means present.

```spl
index=<datastream_index> sourcetype=<datastream_sourcetype> earliest=<start_epoch> latest=<end_epoch> isMidgress=0
| bin _time span=5m
| eval status=if(match(statusCode, "^(0|[1-5][0-9]{2})$"), tonumber(statusCode), null()),
       cache=if(match(cacheStatus, "^[01]$"), tonumber(cacheStatus), null())
| stats count AS requests, count(status) AS status_known, count(cache) AS cache_known,
        count(eval(status>=500)) AS errors_5xx, count(eval(cache=0)) AS not_in_cache by _time, reqHost
| eval pct_status_known=round(100*status_known/requests, 2), pct_cache_known=round(100*cache_known/requests, 2),
       pct_5xx=if(status_known=requests, round(100*errors_5xx/requests, 2), null()),
       pct_not_in_cache=if(cache_known=requests, round(100*not_in_cache/requests, 2), null())
```

Acceptance: 100 client responses, all 200 with 80 cache hits, plus 20 internal 503/cache-miss
records must yield 100 requests, 0% 5xx, 20% not-in-cache. Remove the status field from ten
client records: 90 of 100 statuses are known (90% coverage) and the 5xx share is null. Cache
coverage stays at 100% and the cache-absence share stays at 20%. With both fields absent throughout
the bucket, both coverage percentages are zero and both shares are null. Verify extraction on the target.

Add `country` (client origin) or `serverCountry` (serving location) for regional grouping;
`stats count by errorCode` narrows a spike. Inspect `reqHost` shape before filtering (it mirrors
Host). `akamai-edge`'s DataStream caveats still apply: low-latency streams are less complete and
delivery failures lose lines.
