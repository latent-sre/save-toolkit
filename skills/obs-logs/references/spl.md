# SPL dialect for log investigation

Use this reference only after applying the product-agnostic investigation shape in the parent skill.
Fill in the team's indexes, sourcetypes, correlation-id field, and saved searches in
[local log inventory](./indexes.md) before treating any placeholder as real.

Official syntax basis: Splunk's current documentation for
[comments](https://help.splunk.com/en/splunk-enterprise/search/search-manual/10.2/use-the-search-app/add-comments-to-searches),
[classic SPL quoting and escaping](https://help.splunk.com/en/splunk-enterprise/search/search-manual/10.4/use-the-search-app/anatomy-of-a-search),
[`timechart`](https://help.splunk.com/en/splunk-enterprise/search/spl-search-reference/10.2/search-commands/timechart),
and [`streamstats`](https://help.splunk.com/en/splunk-enterprise/search/spl-search-reference/10.2/search-commands/streamstats).
Every example still requires confirmation against the target Splunk version, permissions, index
inventory, and field extractions.

> ## ⚠️ `#` IS NOT AN SPL COMMENT
> SPL comments are **triple backticks**: `` ```like this``` ``. A `#` is not SPL comment syntax;
> depending on its position, trailing `#` text can alter the command expression or cause a parse error.
> Every example below therefore uses the documented backtick form. Replace placeholders and validate
> the complete query against the target before execution.
>
> Two documented restrictions: a comment **cannot precede a generating command** (`tstats`,
> `makeresults`, `multisearch`, `gentimes`) — the search fails or returns wrong results — and comments
> **cannot appear inside a quoted string**.
> *(There is a community `` `comment()` `` macro, but it is **not** in Splunk's official docs and its
> app-scoped sharing means it can fail to resolve for other users. Don't rely on it.)*
> *SPL2 is different again: `//` and `/* */`.*
> *[sourced: Splunk comment documentation; unverified exact parser outcome for the target version]*
> *[sourced: Splunk, “Add comments to searches”; community-macro behavior remains unverified for the target]*

## Start narrow

*[sourced: Splunk search syntax; unverified for the target index, sourcetype, host, and extracted fields]*

````spl
index=<app_index> host=<...> sourcetype=<...> earliest=-1h latest=now
| where status>=500
```scope the base search by index/sourcetype/host/time ONLY — no keyword filter.
   a keyword like "error" would drop 5xx access-log events whose raw text has no
   "error", false-clearing the very spike you're confirming.```
````

> **Numeric field comparisons (`status>=500`, `error_type=...`) belong in a `| where`/`| search`
> *after* the base search, not in the raw keyword search.** A numeric comparison on a field that isn't
> search-time-extracted silently matches **nothing** — a false "all clear" mid-incident. Confirm
> `status`/`error_type` are extracted (or `rex` them first); see the extraction note under *Tips*.

## Read it over time

*[sourced: Splunk `timechart`; unverified for the target index and `status` extraction]*

````spl
index=<app_index>
| where status>=500     ```status must be an extracted field, else this matches nothing```
| timechart span=1m count     ```5xx per minute — find the exact onset```
````

> Same trap as above: a keyword like `error` in the base search filters before `| where status>=500`
> runs, missing 5xx access-log events with no "error" text and false-clearing the spike. Scope the base
> search; filter the status in `| where`.

*[sourced: Splunk `timechart`; unverified for the target index and `status` extraction]*

````spl
index=<app_index>
| timechart span=1m count by status     ```split by HTTP status to see 5xx vs 4xx```
````

## Top offenders

*[sourced: Splunk `stats` and `sort`; unverified for the target index and field extraction]*

````spl
index=<app_index> error
| stats count by error_type, message
| sort -count
```error_type must be indexed/extracted — if it isn't, `stats by error_type` buckets
   everything into one empty group```
````

`error_type` must be search-time-extracted; if it isn't, `rex` it first (see *Tips* below).

## Spot a spike vs the baseline (anomaly detection)

Bucket FIRST, filter inside the aggregation — `timechart` fills empty buckets, `stats` does not.
A filter-first pipeline emits rows only for buckets that already had errors, so the baseline is
computed over error-containing buckets and the alert under-fires on the exact spike it exists
to catch.

*[sourced: Splunk `timechart` fills null time buckets and `streamstats current=f` excludes the current
result; unverified for the target schema and for whether a three-standard-deviation threshold fits the service]*

````spl
index=<app_index> earliest=-24h
| timechart span=5m count(eval(status>=500)) AS errors
| streamstats window=12 current=f avg(errors) AS baseline stdev(errors) AS sd
| where isnotnull(baseline) AND sd>0 AND errors > baseline + 3*sd
   ```guards: the first rows have no baseline; a flat window gives sd=0 and would flag everything```
````

`window=12` here really is a trailing hour (12 × 5m), because every bucket emits a row.

**Three traps here, and the skill used to fall into all of them.**

**1. The baseline must EXCLUDE the current point.** `streamstats` defaults to `current=true` and
`window=0` (all previous *and current* events), so a naive trailing baseline is **contaminated by the
very spike you are trying to detect** — the bigger the spike, the more it raises its own baseline and
hides itself. Pass `current=f`.

**2. `streamstats` follows RESULT order, not time order.** For a `stats`-based form, put
`sort 0 _time` first (`0` = no result limit; `sort` silently truncates otherwise). That instruction is
not needed for the fixed `timechart` form above, which emits complete ordered buckets.

**3. Compare RATES, not raw counts.** A rise in error *count* during a traffic doubling is not a rise in
error *rate*. Normalize by total volume, or you page on a marketing campaign.

**Normalized (rate, not count) — prefer this:**

*[sourced: Splunk `bin`, `stats`, `eval`, `sort`, and `streamstats` syntax; unverified operational
guidance and target fields]*

````spl
index=<app_index> earliest=-24h
| bin _time span=5m
| stats count(eval(status>=500)) AS errors, count AS total by _time
| eval error_rate = errors / total                ```a ratio survives a traffic spike; a count does not```
| sort 0 _time
| streamstats window=12 current=f avg(error_rate) AS baseline stdev(error_rate) AS sd
| where isnotnull(baseline) AND sd>0 AND error_rate > baseline + 3*sd
````

**Seasonal comparison** — "is this hour worse than the same hour last week?" is usually the question you
actually mean, and a trailing window can't answer it:

*[sourced: Splunk `timewrap` syntax; unverified for target fields and seasonal suitability]*

````spl
index=<app_index> earliest=-8d
| bin _time span=5m
| stats count(eval(status>=500)) AS errors, count AS total by _time
| eval error_rate = errors / total
| timechart span=5m avg(error_rate)
| timewrap 1week                                  ```overlay this week on last week```
````

> `eventstats` (adds an aggregate to **every** row, unlike `stats` which collapses them) is still the
> right tool for "which buckets exceed the *whole period's* mean" — but note it has the same
> contamination problem in reverse: the outlier is inside the mean it is being compared against.
> *Caveat on sourcing: `sort 0 _time`, `current=f`, and the null/`sd>0` guards are statistically
> correct, but they are **our** guidance — Splunk's own outlier example omits `current=f`. Don't cite
> Splunk for the normalization advice either; it documents the mechanisms (`streamstats`, `timewrap`),
> not the choice to normalize.*

## Correlate one request across services

Correlation ids copied from a ticket or log are untrusted input. Prefer rejecting any value outside the
service's documented identifier grammar. Never concatenate the raw value into SPL. If that grammar
permits reserved characters, apply classic SPL's documented escaping for quotes, pipes, and backslashes,
then inspect the final rendered query; API, shell, or dashboard layers can require additional encoding.
Stop if the value cannot be represented unambiguously.

*[sourced: Splunk classic search quoting/escaping; unverified target id grammar and client layers]*

*[sourced: Splunk base-search, Boolean, `sort`, and `table` syntax; unverified for target field names]*

````spl
index=<app_index> (request_id="<validated_and_spl_escaped_id>" OR trace_id="<validated_and_spl_escaped_id>")
```one index; use (index=a OR index=b) to span several — a LIST inside index= is not valid SPL```
| sort 0 _time     ```the full path of one failing request; 0 = don't truncate```
| table _time host service status message
````

Tracing one id is the rare case a broad search is justified — use `index=*` only when the request may
touch services you can't enumerate, and keep the window tight. If logs lack a correlation id, that's a
finding — recommend adding one through the `sde` agent.

## Compare before vs after a deploy

Compare **rates**, not raw counts — if traffic differs between the two phases (and after a deploy it
usually does), a count comparison tells you about traffic, not about the deploy.

*[sourced: Splunk `eval` and `stats` syntax; unverified for target fields and deploy epoch]*

````spl
index=<app_index>
| eval phase=if(_time < <deploy_epoch>, "before", "after")
| stats count(eval(status>=500)) AS errors, count AS total by phase, error_type
| eval error_rate = errors / total
   ```did this error's RATE rise after the deploy — or did traffic just grow?```
````

## Extract fields ad hoc

*[sourced: Splunk `rex` and `stats` syntax; unverified for target log format]*

````spl
index=<app_index> sourcetype=<...> earliest=-1h     ```scope the base search — never start bare```
| rex field=_raw "latency=(?<latency_ms>[\d.]+)"    ```[\d.]+ keeps fractional ms; \d+ truncates them```
| stats p95(latency_ms), max(latency_ms) by uri
````

## Tips & gotchas (Splunk-specific — where the default bites)

- **Never leave the search broadly unscoped without reason.** `index=*` scans every index — slow, costly,
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
- Record every change and symptom in one UTC incident timeline; hand it to the `sre` agent with
  confidence labels.
- Ownership map only—not a load: the `obs-alerting` skill owns Moogsoft correlation. Hand correlated
  evidence to the `sre-steward` agent.

## Inert canary example

This checks reference loading only; it is not a production identifier.

*[sourced: Splunk equality-filter and `table` syntax; unverified for target index/field availability]*

````spl
index=<app_index> request_id="<fixture_request_id>" earliest=-5m
| table _time request_id service status
````

Expected fixture output (inert):

```text
q_ol_spl_3f7a
```
