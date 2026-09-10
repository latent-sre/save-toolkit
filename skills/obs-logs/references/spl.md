# SPL dialect for log investigation

Use this reference only after applying the product-agnostic investigation shape in the parent skill.
Fill in the team's indexes, sourcetypes, correlation-id field, and saved searches in
[local log inventory](./indexes.md) before treating any placeholder as real.

Official syntax basis: Splunk's current documentation (Splunk Enterprise **10.4**, the latest in the
docs version selector *[sourced: help.splunk.com; reviewed 2026-08-21]*) for
[comments](https://help.splunk.com/en/splunk-enterprise/search/search-manual/10.4/use-the-search-app/add-comments-to-searches),
[classic SPL quoting and escaping](https://help.splunk.com/en/splunk-enterprise/search/search-manual/10.4/use-the-search-app/anatomy-of-a-search),
[`timechart`](https://help.splunk.com/en/splunk-enterprise/search/spl-search-reference/10.4/search-commands/timechart),
and [`streamstats`](https://help.splunk.com/en/splunk-enterprise/search/spl-search-reference/10.4/search-commands/streamstats).
Query syntax is `[sourced]` to Splunk's command references. Every example remains `[unverified]`
for the target version, permissions, inventory, and extractions until executed there.

## SPL comments

Classic SPL comments use triple backticks: `` ```like this``` ``. `#` can alter a query or
cause a parse error. Comments cannot precede a generating command (`tstats`, `makeresults`,
`multisearch`, `gentimes`) or appear inside a quoted string. Do not substitute an app-scoped
comment macro; SPL2's `//` and `/* */` belong to a different language.
## Contents

- Start narrow
- Read it over time
- Top offenders
- Spot a spike vs the baseline (anomaly detection)
- Correlate one request across services
- Compare before vs after a deploy
- Extract fields ad hoc
- Fast paths at scale — tstats, data models, TERM/PREFIX
- Tips & gotchas (Splunk-specific — where the default bites)

## Start narrow

````spl
index=<app_index> host=<...> sourcetype=<...> earliest=-1h latest=now
| where status>=500
```No raw "error" keyword: it would drop 5xx events without that word.```
````

Confirm field extraction before filtering (`status>=500`, `error_type=...`); use `rex` if needed.
A predicate on an absent field can match nothing, so an empty result alone cannot establish health.

## Read it over time

````spl
index=<app_index>
| where status>=500     ```status must be an extracted field, else this matches nothing```
| timechart span=1m count     ```5xx per minute — find the exact onset```
````

````spl
index=<app_index>
| timechart span=1m count by status     ```split by HTTP status to see 5xx vs 4xx```
````

## Top offenders

````spl
index=<app_index> sourcetype=<...> earliest=-1h latest=now
| where isnotnull(error_type)
| stats count by error_type, service
| sort -count
```Grouping omits events without error_type. Prove extraction on known errors with
   | stats count(error_type) AS classified, count
   before interpreting an empty result. A low classification ratio in ordinary traffic
   can simply reflect few errors.```
````

Group by stable fields (`error_type`, `service`, `route`), not raw `message`.

## Spot a spike vs the baseline (anomaly detection)

Use a request-completion sourcetype with one event per eligible request/attempt. Confirm source
freshness, ingestion coverage, and a single three-digit HTTP status per event before interpreting
an anomaly. A ratio needs the complete request population; errors/sec or counts alone measure volume.

**Complete five-minute buckets, preceding-hour baseline:** choose absolute bounds aligned to five
minutes, excluding the current incomplete bucket. `timechart cont=t` retains empty buckets;
`stats ... by _time` would omit them. Missing/invalid status or zero traffic leaves the ratio null,
not healthy zero. An entirely empty search has no usable baseline.

*[sourced: Splunk `timechart`, `eval`, and `streamstats` mechanisms; unverified target fields,
query execution, coverage, and suitability of the thresholds]*

````spl
index=<app_index> sourcetype=<request_completion_sourcetype> earliest=<start_epoch> latest=<end_epoch>
| eval status=if(match(status, "^[1-5][0-9]{2}$"), tonumber(status), null())
| timechart span=5m cont=t partial=f count AS total count(status) AS classified count(eval(status>=500 AND status<600)) AS errors
| eval error_rate=if(total>0 AND classified=total, errors/total, null())
| streamstats window=12 current=f count(error_rate) AS valid_buckets avg(error_rate) AS baseline stdev(error_rate) AS sd
| where valid_buckets=12 AND isnotnull(error_rate) AND errors>=<minimum_errors>
    AND error_rate-baseline>=<minimum_ratio_increase>
    AND ((sd>0 AND error_rate>baseline+3*sd) OR (sd=0 AND error_rate>baseline))
````

The owner supplies numeric minimum-error and minimum-ratio-increase thresholds before use; they
are service policy, not Splunk defaults. A flat baseline (`sd=0`) can still have a real spike. The
explicit branch detects a material increase instead of suppressing every zero-variance case.
`valid_buckets=12` requires twelve valid preceding five-minute buckets; any null bucket breaks that
coverage. `current=f` excludes the candidate point so it cannot raise its own baseline. Keep
`timechart`'s chronological order; a different pipeline must sort time without truncating results.
Source freshness remains an independent check: complete result buckets do not prove complete ingestion.

**Seasonal comparison:** cover both weeks; reuse only the
`timechart`/`error_rate` construction. Keep `_time` and `error_rate` and apply
`timewrap 1week series=short`. Compare `s0` (latest) with `s1` (previous):
require aligned, complete, non-null buckets in both weeks and an owner-set minimum ratio increase. Do not append the preceding-hour
`streamstats` pipeline: `error_rate` has become period-specific fields.
*[sourced: [Splunk timewrap](https://help.splunk.com/en/splunk-enterprise/spl-search-reference/10.4/search-commands/timewrap);
unverified target query execution and period alignment]*
`eventstats` includes the candidate in its whole-period baseline. Thresholds and normalization
remain operational choices, not Splunk guarantees.

## Correlate one request across services

The identifier-trust rules in `../SKILL.md` (validate, never concatenate, stop if unencodable)
apply; the SPL-specific part is the escaping: apply classic SPL's documented escaping for quotes,
pipes, and backslashes, then inspect the final rendered query — API, shell, or dashboard layers can
require additional encoding.

````spl
index=<app_index> (request_id="<validated_and_spl_escaped_id>" OR trace_id="<validated_and_spl_escaped_id>")
```one index; use (index=a OR index=b) to span several — a LIST inside index= is not valid SPL```
| sort 0 _time     ```the full path of one failing request; 0 = don't truncate```
| table _time host service status message
````

Tracing one id is the rare case a broad search is justified — use `index=*` only when the request may
touch services you can't enumerate, and keep the window tight. If logs lack a correlation id, that's a
finding — recommend adding one through the `software-engineer` agent.

## Compare before vs after a deploy

Use equal, absolute windows around the deploy. Select a request-completion sourcetype with exactly
one event per eligible request/attempt; an application index containing debug or lifecycle events
is not a request denominator. Establish that population and coverage before interpreting a rate.
The denominator below is all eligible requests in the phase, independent of error classification:

````spl
index=<app_index> sourcetype=<request_completion_sourcetype> earliest=<before_start_epoch> latest=<after_end_epoch>
| eval phase=if(_time < <deploy_epoch>, "before", "after")
| eval status=if(match(status, "^[1-5][0-9]{2}$"), tonumber(status), null())
| eventstats count AS total, count(status) AS classified by phase
| stats count(eval(status>=500 AND status<600)) AS errors, max(total) AS total, max(classified) AS classified by phase, error_type
| eval error_rate=if(total>0 AND classified=total, errors/total, null())
````

For one error class, 1 failure among 100 eligible requests before and 10 among 100 after must
produce 0.01 and 0.10. Counting the denominator inside `by phase, error_type` instead produces
1/1 and 10/10 when that class exists only on failures, hiding the regression. Missing or invalid HTTP
status (including `0`, `700`, or fractional codes) leaves the rate null. This assumes a single
three-digit HTTP status per completion event; verify that source contract. A missing phase/class
row is not a zero: confirm traffic, extraction,
and window coverage. Successful requests without `error_type` still count in `eventstats` before
the class grouping. Use the catalog's overall-rate query when no error classification is available.

## Extract fields ad hoc

````spl
index=<app_index> sourcetype=<...> earliest=-1h     ```scope the base search — never start bare```
| rex field=_raw "latency=(?<latency_ms>[\d.]+)"    ```[\d.]+ keeps fractional ms; \d+ truncates them```
| stats p95(latency_ms), max(latency_ms) by uri
````

## Fast paths at scale — tstats, data models, TERM/PREFIX

*[sourced: help.splunk.com SPL search reference — `tstats`, `datamodel`, data-model acceleration,
and the CASE/TERM search-primer pages; reviewed 2026-08-07 via indirect retrieval; unverified for
the target's accelerated models and index population]*

When a raw search over the incident window is too slow to iterate, `tstats` reads **indexed
metadata (tsidx files), not raw events** — orders faster, with two strings attached:

````spl
| tstats count FROM datamodel=<model>.<root_dataset> WHERE earliest=-4h BY <dataset>.<field> _time span=5m
````

- **`summariesonly=t` trades completeness for speed, silently.** It returns results only from
  already-summarized data "even when the time range of the search exceeds the summarization range"
  — if acceleration lags the live incident (it usually lags by minutes), the newest events are
  simply absent, a mid-incident false all-clear. Default (`summariesonly=f`) falls back to raw
  data for the unsummarized remainder: complete but slower. Say which mode produced any
  tstats-based claim in the packet.
- Search filters cannot be applied to accelerated data models — constraints go in `WHERE`/`BY`
  against dataset fields.
- **`TERM()`** matches a term containing minor breakers as one indexed term
  (`TERM(www.example.com)`, `TERM(10.0.0.5)`) instead of letting the segmenter split it — the
  cheap way to hunt one IP/host across a big index. **`PREFIX()`** (with tstats) aggregates on a
  raw indexed segment as if it were a field — include the delimiter: `PREFIX(kbps=)` yields the
  values, `PREFIX(kbps)` yields `=10`-shaped junk.
- **Index-time vs search-time**: Splunk's own guidance — "it is better to perform most
  knowledge-building activities, such as field extraction, at search time." Recommending
  index-time extraction to speed one investigation is a config change with indexing-cost blast
  radius; that recommendation goes to the `observability-engineer` agent, not into an incident.

**When a search is slow, prove why before rewriting it:** the Job Inspector shows per-component
execution costs; `scanCount` vs `resultCount` (events read off disk vs events that matched) is the
first diagnostic — a huge scan for a tiny result means the base search is under-scoped or the
filter isn't index-time-selective (that's what `TERM()`/`tstats` fix).

## Tips & gotchas (Splunk-specific — where the default bites)

- **Never leave the search broadly unscoped without reason.** `index=*` scans every public index (internal `_*` indexes are excluded) — slow, costly,
  and may silently miss role-restricted data. Scope to the app index from [local log inventory](./indexes.md);
  the one justified exception is tracing a single correlation id across services you can't enumerate —
  even then, keep the window tight. *[unverified for target permissions and scale]*
- **The time range is implicit and dangerous.** A bare search uses the picker's range (often last 24h);
  in a saved search/API job it's whatever the job sets. Set `earliest`/`latest` explicitly during triage.
  *[sourced: Splunk time-modifier syntax; unverified target UI state]*
- **Fields are case-sensitive and only exist after extraction.** `table status` shows nothing if the
  field was never extracted; `rex` it first. `_time` is in the search TZ, not necessarily the event's.
  *[sourced: Splunk field/search behavior; unverified target extractions]*
- `stats`/`timechart`/`tstats` aggregate; `transaction` groups events but is expensive — prefer
  `stats by <id>` for correlation. *[unverified performance guidance for target data]*
- Record every change and symptom in one UTC incident timeline; hand it to the responder (or the `sre-assistant` slice they dispatched) with
  confidence labels.
- Hand correlated evidence to the `observability-engineer` agent.
