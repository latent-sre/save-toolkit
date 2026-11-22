# SPL dialect for log investigation

Resolve index, sourcetype, correlation, and extraction field names on the target first (syntax
basis: Splunk Enterprise 10.6). Comments use triple backticks (`` ```comment``` ``, never `#` or
before generating commands like `tstats`). Field names are case-sensitive; `timechart ... by <field>`
defaults to top 10 + `OTHER` (set `limit=0` when rare values matter).

## Source freshness

```spl
| tstats count max(_time) AS last_event max(_indextime) AS last_indexed WHERE index=<app_index> sourcetype=<request_completion_sourcetype> earliest=-4h latest=now BY host
| eval since_last_event_s=now()-last_event, since_last_indexed_s=now()-last_indexed
```

`tstats` above covers only `_time` in the last 4h (`max(_indextime)` in `tstats` varies by support;
fall back to raw `stats`). For delayed/backfilled events check a bounded index-time and event-time
window (`_index_earliest=-1h _index_latest=now earliest=<event_start_epoch> latest=<event_end_epoch>`),
and measure lag via `eval delay_s=_indextime-_time`.

## PCF apps in Splunk

Confirm on a real event: Firehose nozzles emit `cf:logmessage` and `cf:httpstartstop`. Bind org,
space, and app fields together (app names repeat across spaces). Gorouter `RTR` lines (one per
routed request; `response_time` in seconds, correlated via `vcap_request_id`) are the request
population; `APP` lines are stdout/stderr.

## Baseline spike detection (`timechart` + `streamstats`)

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

Use `timechart cont=t partial=f` to keep empty buckets and exclude the incomplete current bucket;
for week-over-week checks keep only `_time` and `error_rate` and apply `timewrap 1week series=short`
(do not reuse `eventstats`, which leaks the current bucket into its own baseline).

## Request correlation and deploy comparison

- **Correlate one request (escape quotes, pipes, backslashes with `\`):**
  ```spl
  index=<app_index> (request_id="<id>" OR trace_id="<id>") earliest=<start_epoch> latest=<end_epoch>
  | sort 0 _time | table _time host service status message
  ```
### Overall deploy error rate

Compare equal absolute windows around the deploy with one completion event per eligible request:

```spl
index=<app_index> sourcetype=<request_completion_sourcetype> earliest=<before_start_epoch> latest=<after_end_epoch>
| eval phase=if(_time < <deploy_epoch>, "before", "after")
| eval status=if(match(status, "^[1-5][0-9]{2}$"), tonumber(status), null())
| stats count AS total, count(status) AS classified, count(eval(status>=500 AND status<600)) AS errors by phase
| eval error_rate=if(total>0 AND classified=total, errors/total, null())
```
  For a per-`error_type` breakdown while keeping the **full phase denominator**, replace only the
  `stats` line with:
  ```spl
  | eventstats count AS total, count(status) AS classified by phase
  | stats count(eval(status>=500 AND status<600)) AS errors, max(total) AS total, max(classified) AS classified by phase, error_type
  ```

## Fast paths (`tstats`, data models, `TERM`/`PREFIX`)

- `summariesonly=t` omits unsummarized recent events when acceleration lags; record the mode.
  Explicitly constrain `WHERE`/`BY` clauses (role filters do not constrain accelerated models).
- `TERM(10.0.0.5)` matches minor-breaker tokens bounded by major breakers (spaces/commas; misses
  `ip=10.0.0.5`). `PREFIX(kbps=)` extracts `tstats` values cleanly.
