# Team query catalog — cataloged starting queries

## Contents

- [Execution](#who-runs-a-catalog-entry), [entry fields](#entry-shape)
- [Error onset](#which-errors-started-at-the-same-time-as-the-impact), [deploy comparison](#did-error-rate-change-across-the-deploy)
- [Request path](#where-did-one-request-fail-across-services), [caller load](#which-callers-are-driving-the-current-load)
- [Akamai](#is-the-akamai-edge-failing-or-missing-cache-for-one-hostname-or-region)

Use [SPL](./spl.md) for dialect rules and [inventory](./indexes.md) for actual selectors/fields.
Entries remain unverified until a named human validates them on the target and records the date;
catalog presence is not production evidence. Store only names, locators and query text, never
credentials, session/user identifiers, customer data or raw payloads. Link an access-controlled
saved search if its sensitive parameters cannot be represented here.

## Who runs a catalog entry

Use only the invoked lane's permitted diagnostic API, browser or reviewed helper with its
credential/output protections. The standard SRE profile has no Splunk query execution path: return
the query and expected interpretation, then continue other authorized work. A CLI is not required.
A diagnostic search grants no permission to persist results, edit saved searches or perform writes.

## Entry shape

Keep question, Applies to, Reads as, Healthy looks like, Owner, Verified, and the query or its
canonical reference. These interpretation fields apply to proposed queries too. Inventory values
stay placeholders until resolved; parent scope/window/coverage and evidence rules apply.

## Splunk (SPL)

### Which errors started at the same time as the impact?

| Field | Value |
|---|---|
| Applies to | Structured service errors |
| Reads as | Error-class counts per populated minute, newest first; quiet buckets absent |
| Healthy looks like | Counts match known-normal comparison; missing buckets/classes are not health |
| Owner | `<service on-call>` |
| Verified | Unverified: index, sourcetype, `error_type` extraction |

```spl
index=<app_index> sourcetype=<error_sourcetype> earliest=<start_epoch> latest=<end_epoch>
| bin _time span=1m
| stats count by _time, error_type
| sort 0 - _time
```

An onset shortlist, not a complete baseline. Check extraction/ingestion; use
[complete buckets](./spl.md#spot-a-spike-vs-the-baseline-anomaly-detection) for quiet periods and trailing baselines.

### Did error rate change across the deploy?

| Field | Value |
|---|---|
| Applies to | Known deploy time; one completion event per eligible request/attempt |
| Reads as | Failure/request ratio in equal windows, not raw counts |
| Healthy looks like | After ratio within normal before variation despite traffic changes |
| Owner | `<service on-call>` |
| Verified | Unverified: population, status extraction and deploy epoch |

Use [SPL's deploy comparison](./spl.md#compare-before-vs-after-a-deploy) with this population.
Missing/invalid status leaves the ratio null; no traffic or a missing phase is not healthy zero.

### Where did one request fail across services?

| Field | Value |
|---|---|
| Applies to | Services with a shared correlation field |
| Reads as | Ordered request path, one row per logged service hop |
| Healthy looks like | Every expected hop present, ending in success |
| Owner | `<service on-call>` |
| Verified | Unverified: correlation field per inventory |

```spl
index=<app_index> <correlation_field>="<validated_and_spl_escaped_id>" earliest=<start_epoch> latest=<end_epoch>
| table _time, service, status, latency_ms
| sort 0 _time
```

[`sort`](https://help.splunk.com/en/splunk-enterprise/spl-search-reference/10.4/search-commands/sort)
defaults to 10,000 rows; `sort 0` preserves the path at extra cost. Keep the window tight;
missing hops remain telemetry gaps until explained independently.

### Which callers are driving the current load?

| Field | Value |
|---|---|
| Applies to | Request-completion access logs |
| Reads as | Largest caller request counts |
| Healthy looks like | Usual caller mix; no new dominant caller |
| Owner | `<service on-call>` |
| Verified | Unverified: completion population and caller field |

```spl
index=<app_index> sourcetype=<request_completion_sourcetype> earliest=-30m latest=now
| stats count AS requests by <caller_field>
| sort - requests
| head 20
```

`stats by` drops missing caller fields; compare `count(<caller_field>)` against `count` first.

### Is the Akamai edge failing or missing cache for one hostname or region?

| Field | Value |
|---|---|
| Applies to | DataStream 2 JSON client-request logs, only when `stack-profile` records Splunk as destination |
| Reads as | Five-minute hostname buckets: requests, 5xx share, not-in-cache share (`cacheStatus=0`); quiet buckets absent |
| Healthy looks like | Same-host shares near normal; missing buckets may be delivery gaps |
| Owner | `<edge on-call>` |
| Verified | Unverified: destination, selectors, client population and field extraction |

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
