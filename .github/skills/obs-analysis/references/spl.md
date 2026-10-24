# SPL dialect for log investigation

## Contents

- [Comments](#spl-comments), [scope](#start-narrow), [freshness](#is-the-source-current)
- [Time buckets](#read-it-over-time), [top offenders](#top-offenders)
- [Spike baseline](#spot-a-spike-vs-the-baseline-anomaly-detection)
- [Correlation](#correlate-one-request-across-services), [deploy comparison](#compare-before-vs-after-a-deploy)
- [Scale](#fast-paths-at-scale--tstats-data-models-termprefix), [defaults](#tips--gotchas-splunk-specific--where-the-default-bites)

Resolve index, sourcetype, correlation and extraction placeholders through [local inventory](./indexes.md).
Syntax basis: Splunk Enterprise 10.4 references for
[comments](https://help.splunk.com/en/splunk-enterprise/search/search-manual/10.4/use-the-search-app/add-comments-to-searches),
[quoting](https://help.splunk.com/en/splunk-enterprise/search/search-manual/10.4/use-the-search-app/anatomy-of-a-search),
[`timechart`](https://help.splunk.com/en/splunk-enterprise/search/spl-search-reference/10.4/search-commands/timechart),
and [`streamstats`](https://help.splunk.com/en/splunk-enterprise/search/spl-search-reference/10.4/search-commands/streamstats).
Target version and extractions still require confirmation.

## SPL comments

Classic SPL uses triple backticks: `` ```comment``` ``. `#` is not a comment; SPL2's `//` and
`/* */` are a different language. Comments cannot precede generating commands (`tstats`,
`makeresults`, `multisearch`, `gentimes`) or appear inside quoted strings. Do not substitute an
app-scoped comment macro.

## Start narrow

Filtering `status>=500` requires a verified extraction; use `rex` when needed. Adding a raw
`"error"` keyword drops 5xx events without that word. Fields are case-sensitive; an absent field
can make a predicate return nothing.

## Is the source current?

```spl
| tstats count max(_time) AS last_event max(_indextime) AS last_indexed WHERE index=<app_index> sourcetype=<request_completion_sourcetype> earliest=-4h latest=now BY host
| eval since_last_event_s=now()-last_event, since_last_indexed_s=now()-last_indexed
```

This covers only events whose `_time` lies within four hours. At 12:00, an event timestamped 05:50
but indexed at 11:59 is excluded: old `last_indexed` or a missing host cannot prove ingestion stopped.
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

## Read it over time

```spl
index=<app_index> sourcetype=<request_completion_sourcetype> earliest=<start_epoch> latest=<end_epoch>
| timechart span=1m count AS total count(status) AS classified count(eval(status>=500 AND status<600)) AS errors
```

`classified<total` exposes incomplete status extraction. For every status class rather than the
default top ten series:

```spl
index=<app_index> sourcetype=<request_completion_sourcetype> earliest=<start_epoch> latest=<end_epoch>
| eval status_class=if(match(status, "^[1-5][0-9]{2}$"), substr(status, 1, 1)."xx", "invalid")
| timechart span=1m limit=0 count by status_class
```

## Top offenders

`stats count by error_type, service` omits events without grouping fields. Verify `error_type` on
known errors with `stats count(error_type) AS classified, count`; a low classified ratio in ordinary
traffic may simply mean few errors. Group by stable error/service/route fields, not raw messages.

## Spot a spike vs the baseline (anomaly detection)

Use one completion event per eligible request/attempt, fresh ingestion, and a single three-digit
HTTP status per event. PCF Gorouter `RTR` is normally that source; `APP` stdout is not a request
count. Resolve the selector from [inventory](./indexes.md).

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

Minimum-error and ratio-increase thresholds are owner-supplied numeric policy. The `sd=0` branch
keeps flat-baseline spikes detectable. Twelve valid preceding buckets are required; a null breaks
coverage. `current=f` excludes the candidate from its baseline. Preserve chronological order
without truncation. Complete buckets do not independently prove complete ingestion.

For seasonal comparison, cover both weeks and reuse only `timechart`/`error_rate`, then keep `_time`
and `error_rate` and apply `timewrap 1week series=short`. Compare `s0` (latest) with `s1` (previous)
using complete aligned non-null buckets and an owner-set minimum increase. Do not append the
preceding-hour `streamstats`: fields are now period-specific. `eventstats` includes the candidate
in its whole-period baseline.

## Correlate one request across services

Apply classic SPL escaping for quotes, pipes and backslashes, then inspect the rendered query;
API/shell/dashboard encoding may add another layer.

```spl
index=<app_index> (request_id="<validated_and_spl_escaped_id>" OR trace_id="<validated_and_spl_escaped_id>") earliest=<start_epoch> latest=<end_epoch>
| sort 0 _time
| table _time host service status message
```

Use `(index=a OR index=b)`, not a list inside `index=`. `sort 0` keeps the full path instead of the
default truncation. Use `index=*` only for one id crossing services that cannot be enumerated, with
a tight window; it covers public indexes, not internal `_*`, and may miss role-restricted data.

## Compare before vs after a deploy

Use equal absolute windows and one completion event per eligible request/attempt. The denominator
must count all requests in a phase before grouping by error classification:

```spl
index=<app_index> sourcetype=<request_completion_sourcetype> earliest=<before_start_epoch> latest=<after_end_epoch>
| eval phase=if(_time < <deploy_epoch>, "before", "after")
| eval status=if(match(status, "^[1-5][0-9]{2}$"), tonumber(status), null())
| eventstats count AS total, count(status) AS classified by phase
| stats count(eval(status>=500 AND status<600)) AS errors, max(total) AS total, max(classified) AS classified by phase, error_type
| eval error_rate=if(total>0 AND classified=total, errors/total, null())
```

Acceptance case: one class has 1/100 failures before and 10/100 after: rates must be 0.01 and 0.10.
Counting denominators inside `by phase, error_type` instead yields 1/1 and 10/10 if only failures
carry the class. Successful events without `error_type` still count in `eventstats`.
Missing/invalid status (including `0`, `700`, fractions) makes the rate null; verify one three-digit
status per completion. Missing phase/class rows require traffic, extraction and window checks,
not zero-fill.

## Fast paths at scale — tstats, data models, TERM/PREFIX

`tstats` reads indexed metadata (tsidx), not raw events:

```spl
| tstats count FROM datamodel=<model>.<root_dataset> WHERE earliest=-4h BY <dataset>.<field> _time span=5m
```

- `summariesonly=t` silently omits unsummarized data, including recent incident events when
  acceleration lags. Default `f` includes the unsummarized remainder at additional cost. Record
  the mode; a summary's quiet tail is not a live all-clear.
- Role/user search filters do not constrain accelerated data models. Apply the parent redaction
  rules and explicit dataset-field `WHERE`/`BY` constraints.
- `TERM(www.example.com)` or `TERM(10.0.0.5)` keeps minor breakers in one indexed term.
  With `tstats`, `PREFIX(kbps=)` extracts values; omitting the delimiter yields `=10`-shaped values.
- Prefer search-time extraction. Index-time extraction changes indexing cost and configuration;
  route that recommendation to `observability-engineer`.
- Use Job Inspector's component costs and `scanCount` versus `resultCount` before rewriting a slow
  search: a large scan/tiny result suggests under-scoping or a non-index-selective filter.

## Tips & gotchas (Splunk-specific — where the default bites)

- Explicit `earliest`/`latest` avoids inherited picker or saved-job ranges. `_time` displays in
  search timezone, not necessarily the event's.
- `timechart`/`chart ... by <field>` defaults to the top ten series and folds others into `OTHER`.
  Use `limit=0`, or state the limit, when rare codes/hosts matter.
- `transaction` groups events at substantial cost; prefer `stats by <id>` for correlation when
  suitable, without claiming target performance until measured.
