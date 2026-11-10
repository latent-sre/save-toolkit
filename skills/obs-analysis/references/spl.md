# SPL dialect for log investigation

Index, sourcetype, correlation and extraction placeholders are not discovered values: resolve each
on the target and confirm it on one real event.
Syntax basis: Splunk Enterprise 10.6; target version and extractions still require confirmation.

## SPL comments

Classic SPL uses triple backticks: `` ```comment``` ``. `#` is not a comment; SPL2's `//` and
`/* */` are a different language. Comments cannot precede generating commands (`tstats`,
`makeresults`, `multisearch`, `gentimes`) or appear inside quoted strings.

## Is the source current?

```spl
| tstats count max(_time) AS last_event max(_indextime) AS last_indexed WHERE index=<app_index> sourcetype=<request_completion_sourcetype> earliest=-4h latest=now BY host
| eval since_last_event_s=now()-last_event, since_last_indexed_s=now()-last_indexed
```

This covers only events whose `_time` lies within four hours, excluding older events indexed recently.
Old `last_indexed` or a missing host therefore cannot prove ingestion stopped.
`max(_indextime)` in `tstats` is unconfirmed; if rejected, use `stats` over a raw search.
Check a bounded index-time window with event-time bounds covering plausible delay/backfill/skew:

```spl
index=<app_index> sourcetype=<request_completion_sourcetype> host=<expected_host> earliest=<event_start_epoch> latest=<event_end_epoch> _index_earliest=-1h _index_latest=now
| stats count max(_time) AS last_event max(_indextime) AS last_indexed BY host
| eval since_last_event_s=now()-last_event, since_last_indexed_s=now()-last_indexed
```

Index-time modifiers still intersect event time; record both resolved UTC windows. Unknown event-time
coverage makes absence inconclusive. Splunk's exhaustive **All Time** range needs a separate scope/cost
decision. Recent indexing proves arrival for returned events only; measure per-event delay with
`eval delay_s=_indextime-_time`, comparing timestamps before assigning cause.

## Top offenders

`stats count by error_type, service` omits events without grouping fields. Verify `error_type` on
known errors with `stats count(error_type) AS classified, count`; a low classified ratio in ordinary
traffic may simply mean few errors.

## PCF apps in Splunk

Confirm each of these on one real event. A Splunk Firehose nozzle feed delivers log lines as
sourcetype `cf:logmessage` and HTTP start/stop events as `cf:httpstartstop`; a syslog drain carries
whatever its input sets. Bind org, space and app fields together: app names repeat across spaces.
Gorouter `RTR` lines, one per routed request, are the request-completion population; `APP` lines
are stdout/stderr, not a request count. RTR `response_time` is in seconds, not ms, and
`vcap_request_id` correlates one request.

## Spot a spike vs the baseline (anomaly detection)

Use one completion event per eligible request/attempt, fresh ingestion, and a single three-digit
HTTP status per event; on PCF that is the [Gorouter `RTR` population](#pcf-apps-in-splunk).

For a preceding-hour baseline, align absolute bounds to five minutes and exclude the current
incomplete bucket. `timechart cont=t` preserves empty buckets, unlike `stats ... by _time`.
Missing/invalid status or no traffic leaves the ratio null; an empty search supplies no baseline.

```spl
index=<app_index> sourcetype=<request_completion_sourcetype> earliest=<start_epoch> latest=<end_epoch>
| eval status=if(match(status, "^[1-5][0-9]{2}$"), tonumber(status), null())
| timechart span=5m cont=t partial=f count AS total count(status) AS classified count(eval(status>=500 AND status<600)) AS errors
| eval error_rate=if(total>0 AND classified=total, errors/total, null())
| streamstats window=12 current=f count(error_rate) AS valid_buckets avg(error_rate) AS baseline stdev(error_rate) AS sd
| where valid_buckets=12 AND isnotnull(error_rate) AND errors>=<minimum_errors>
    AND error_rate-baseline>=<minimum_ratio_increase>
    AND ((sd>0 AND error_rate>baseline+3*sd) OR (sd=0 AND error_rate>baseline))
```

Minimum-error and ratio-increase thresholds are owner-supplied numeric policy. Preserve
chronological order without truncation.

For seasonal comparison, cover both weeks and reuse only `timechart`/`error_rate`, then keep `_time`
and `error_rate` and apply `timewrap 1week series=short`. Compare `s0` (latest) with `s1` (previous)
using complete aligned non-null buckets and an owner-set minimum increase. Do not append the
preceding-hour `streamstats`: fields are now period-specific. `eventstats` includes the candidate
in its whole-period baseline.

## Correlate one request across services

Classic SPL escapes quotes, pipes and backslashes with a backslash. Logged hops are not a complete
call graph.

```spl
index=<app_index> (request_id="<validated_and_spl_escaped_id>" OR trace_id="<validated_and_spl_escaped_id>") earliest=<start_epoch> latest=<end_epoch>
| sort 0 _time
| table _time host service status message
```

`sort 0` keeps the full path instead of the
default 10,000-row truncation, at extra cost. Use `index=*` only for one id crossing services that cannot be enumerated, with
a tight window; it covers public indexes, not internal `_*`, and may miss role-restricted data.

## Compare before vs after a deploy

Use equal absolute windows and one completion event per eligible request/attempt. Count the whole
phase population before any optional error-class grouping.

### Overall deploy error rate

````spl
index=<app_index> sourcetype=<request_completion_sourcetype> earliest=<before_start_epoch> latest=<after_end_epoch>
| eval phase=if(_time < <deploy_epoch>, "before", "after")
| eval status=if(match(status, "^[1-5][0-9]{2}$"), tonumber(status), null())
| stats count AS total, count(status) AS classified, count(eval(status>=500 AND status<600)) AS errors by phase
| eval error_rate=if(total>0 AND classified=total, errors/total, null())
````

The overall rate needs no `error_type`. For an optional class breakdown, verify its extraction
and replace only the `stats` line above with these two lines, keeping the final rate calculation:

```spl
| eventstats count AS total, count(status) AS classified by phase
| stats count(eval(status>=500 AND status<600)) AS errors, max(total) AS total, max(classified) AS classified by phase, error_type
```

Acceptance case: one class has 1/100 failures before and 10/100 after: rates must be 0.01 and 0.10.
Counting denominators inside `by phase, error_type` instead yields 1/1 and 10/10 if only failures
carry the class. Successful events without `error_type` still count in `eventstats`.
Missing/invalid status (including `0`, `700`, fractions) makes the rate null; verify one three-digit
status per completion. Missing phase/class rows require traffic, extraction and window checks,
not zero-fill. Without usable error classification, use the overall query above.

## Fast paths at scale — tstats, data models, TERM/PREFIX

- `summariesonly=t` silently omits unsummarized data, including recent incident events when
  acceleration lags. Default `f` includes the unsummarized remainder at additional cost. Record
  the mode; a summary's quiet tail is not a live all-clear.
- Role/user search filters do not constrain accelerated data models. Apply the parent redaction
  rules and explicit dataset-field `WHERE`/`BY` constraints.
- `TERM(10.0.0.5)` keeps minor breakers in one indexed term, but matches only where major
  breakers (spaces, commas) bound it in the raw event: it misses `ip=10.0.0.5`.
  With `tstats`, `PREFIX(kbps=)` extracts values; omitting the delimiter yields `=10`-shaped values.
- Route any index-time extraction recommendation to `observability-engineer`.

## Tips & gotchas (Splunk-specific — where the default bites)

- `timechart ... by <field>` defaults to the top ten series and folds others into `OTHER`.
  Use `limit=0`, or state the limit, when rare codes/hosts matter.
- Field names are case-sensitive.
