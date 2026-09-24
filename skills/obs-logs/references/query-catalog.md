# Team query catalog — cataloged starting queries

The searches this team runs often enough to write down once. Each entry answers a stated question,
so a responder can pick by *what they need to know* rather than by remembering SPL. Read
[SPL](./spl.md) for the dialect and [local log inventory](./indexes.md) for index, sourcetype, and
field values; this file holds the assembled searches that combine them.

> **Names, locators, and query text only** — no credentials, tokens, session or user identifiers,
> customer data, or raw payloads. A query that only works with a secret pasted into it does not
> belong here; reference the access-controlled saved search instead.

**Every entry is a starting point, not a trusted result.** A row stays `[unverified]` until a named
human validates it against the live target and records the date; only then may a recommendation
call it verified. Nothing here is proof about production, and an entry's presence never upgrades a
guess into evidence.

## Who runs a catalog entry

Use a registered, permitted diagnostic API, browser session, or reviewed team helper when the
invoked lane actually has that access and its credential/result protections. A Splunk CLI is not a
prerequisite. The standard SRE profile currently has no Splunk query execution path; return the
exact query and expected result to the caller and continue other useful, authorized evidence.
Do not claim to have run a catalog entry or widen tool permissions because it appears here.

The "reads as" and "healthy looks like" fields remain required for both executed and proposed
queries: they let the human and caller assess what the result establishes. Bind the source,
service, absolute window, filters, limits and completeness; a diagnostic search job is not
permission to persist results, modify saved searches, or run a query with other write effects.

## Entry shape

Use the question as the entry heading, followed by the metadata fields below and the query block.

| Field | Meaning |
|---|---|
| **Question** | What a responder wants to know, in plain English. This is the lookup key. |
| **Applies to** | Service, environment, or signal the query is valid for. |
| **Reads as** | What the columns mean, so pasted output can be interpreted. |
| **Healthy looks like** | The result shape when nothing is wrong — the comparison that makes an unhealthy result legible. |
| **Owner** | Named human or team role accountable for the entry. |
| **Verified** | `[verified] <date> by <role>`, or `[unverified]` with what is untested. |
| **Query** | The final code block, with `<placeholders>` for every inventory value. |

## Contribute an entry

Copy this template into this catalog, fill every field, and open a PR. No new skill is needed;
review checks the entry shape, target assumptions, and safety rules.

````markdown
### <the question, phrased as a responder would ask it>

- **Applies to:** <service / environment / signal>
- **Reads as:** <what the output columns mean>
- **Healthy looks like:** <the result when nothing is wrong>
- **Owner:** <role>
- **Verified:** [unverified]

```spl
<the query, with <placeholders> for inventory values>
```
````

## Splunk (SPL)

### Which errors started at the same time as the impact?

- **Applies to:** any service emitting structured errors to Splunk
- **Reads as:** one row per error class per minute containing classified events, most recent first; quiet buckets are absent
- **Healthy looks like:** returned counts match a known-normal comparison; absent buckets or classes do not establish health
- **Owner:** `<service on-call>`
- **Verified:** [unverified: target index, sourcetype, and `error_type` extraction]

```spl
index=<app_index> sourcetype=<error_sourcetype> earliest=<start_epoch> latest=<end_epoch>
| bin _time span=1m
| stats count by _time, error_type
| sort 0 - _time
```

This is an onset shortlist, not a complete baseline. Confirm `error_type` extraction and ingestion
coverage; use [SPL's complete-bucket method](./spl.md#spot-a-spike-vs-the-baseline-anomaly-detection)
when the question requires quiet periods and a trailing baseline.

### Did error rate change across the deploy?

- **Applies to:** a known deploy timestamp and a request-completion sourcetype with exactly one event per eligible request/attempt; mixed application logs are not the denominator
- **Reads as:** failures divided by total requests for equal windows either side of the change — a rate, never a raw count, so a traffic shift cannot read as a regression
- **Healthy looks like:** `error_rate` after within normal variation of before, whatever happened to `total`
- **Owner:** `<service on-call>`
- **Verified:** [unverified: target index, status field, and deploy-epoch substitution]

```spl
index=<app_index> sourcetype=<request_completion_sourcetype> earliest=<before_start_epoch> latest=<after_end_epoch>
| eval phase=if(_time < <deploy_epoch>, "before", "after")
| eval status=if(match(status, "^[1-5][0-9]{2}$"), tonumber(status), null())
| stats count(eval(status>=500 AND status<600)) AS errors, count AS total, count(status) AS classified by phase
| eval error_rate=if(total>0 AND classified=total, errors/total, null())
```

Set the start and end equally far from the deploy epoch. Confirm population and coverage in both
windows and one three-digit HTTP status per completion event. Missing or invalid status, including
`0`, `700`, or fractional codes, leaves the rate null; no traffic or a missing phase is not healthy
zero. `spl.md` owns the per-error-class variant and its phase-wide denominator.

### Where did one request fail across services?

- **Applies to:** services that emit the shared correlation-id field
- **Reads as:** the ordered path of one request, one row per service hop
- **Healthy looks like:** every expected hop present, terminating in a success status
- **Owner:** `<service on-call>`
- **Verified:** [unverified: correlation-id field name per `indexes.md`]

```spl
index=<app_index> <correlation_field>="<validated_and_spl_escaped_id>" earliest=<start_epoch> latest=<end_epoch>
| table _time, service, status, latency_ms
| sort 0 _time
```

Keep the request window tight. [Splunk `sort`](https://help.splunk.com/en/splunk-enterprise/spl-search-reference/10.4/search-commands/sort)
defaults to 10,000 results; `sort 0` preserves the path but can cost more. Missing hops remain
telemetry gaps until independently explained.

### Which callers are driving the current load?

- **Applies to:** request-driven services with an access log in Splunk
- **Reads as:** request counts by caller over the window, largest first
- **Healthy looks like:** the usual caller mix; no single new caller dominating
- **Owner:** `<service on-call>`
- **Verified:** [unverified: request-completion sourcetype and caller field name per `indexes.md`]

```spl
index=<app_index> sourcetype=<request_completion_sourcetype> earliest=-30m latest=now
| stats count AS requests by <caller_field>
| sort - requests
| head 20
```

`stats by` drops events without the caller field; compare `count(<caller_field>)` with `count` over
the same search before reading the mix.

### Is the Akamai edge failing or missing cache for one hostname or region?

- **Applies to:** Akamai DataStream 2 JSON logs, only once `stack-profile`'s edge row records that they land in Splunk; another destination needs the same fields in its own dialect
- **Reads as:** per 5-minute bucket and hostname: requests, 5xx share, and not-in-cache share (`cacheStatus=0`); `statusCode=0` (client left before a response) is in `requests` but not in `errors_5xx`; quiet buckets are absent
- **Healthy looks like:** shares near a known-normal window for the same hostname; a missing bucket can be a delivery gap, not zero traffic
- **Owner:** `<edge on-call>`
- **Verified:** [unverified: destination, index, sourcetype, JSON field extraction]

```spl
index=<datastream_index> sourcetype=<datastream_sourcetype> earliest=<start_epoch> latest=<end_epoch>
| bin _time span=5m
| stats count AS requests, count(eval(statusCode>=500 AND statusCode<600)) AS errors_5xx, count(eval(cacheStatus=0)) AS not_in_cache by _time, reqHost
| eval pct_5xx=round(100*errors_5xx/requests, 2), pct_not_in_cache=round(100*not_in_cache/requests, 2)
```

For a regional report, add `country` (where the request originated) or `serverCountry` (where it
was served) to the `by` clause; break a spike down with `stats count by errorCode` over the same
scope. Check the `reqHost` value shape in one raw event before filtering on it (it mirrors the Host
header). The `akamai-edge` skill's DataStream caveats apply: low-latency streams deliver less
complete data, and delivery failures lose lines.

## Loki (LogQL)

No entries yet. Add them under this heading using the same shape; `logql.md` owns the dialect and
`indexes.md` owns the stream selectors.

## Metrics (PromQL and WQL)

No entries yet. Metric searches belong to `obs-metrics`; add a pointer here only when a metric query
is the natural companion to a log query above, and keep the query itself in the owning skill.
