# LogQL dialect for log investigation

Use this reference only after applying the parent skill's investigation shape. The syntax below is
based on Grafana Loki's current official [LogQL query reference](https://grafana.com/docs/loki/latest/query/)
and [metric-query reference](https://grafana.com/docs/loki/latest/query/metric_queries/), including the
[string-quoting guidance](https://grafana.com/docs/loki/latest/query/log_queries/). Confirm the
deployed Loki version, tenant, labels, parsers, and alert-engine behavior before use.

**Verification scope.** Earlier examples parsed against a non-production Loki source on
2026-08-22, using illustrative selectors that matched no streams. Revised queries below are
`[unverified]` until executed against the target; that historical run does not validate their bytes.
It also showed that `or on() vector(0)` turns a selector matching nothing into zero-valued samples.
That fallback cannot distinguish a quiet service from wrong labels, a wrong tenant, or lost ingestion.

## Contents

- Stream selectors and label discipline
- Line filters versus parsers
- Metric queries: rates and complete buckets
- Compare before and after a deploy
- Follow one request
- Errors that are limits, not bugs

## Stream selectors and label discipline

A LogQL query begins with a stream selector. Keep stable, bounded values such as application,
environment, cluster, or namespace as indexed labels; parse request ids and other high-cardinality
values from the log line instead of promoting them to labels.

*[sourced: Grafana Loki label and LogQL selector documentation; unverified for target labels]*

```logql
{app="checkout", env="prod"}
```

Widen one selector at a time. An empty result can mean the selector is wrong, the tenant is wrong, or
the stream is absent; it is not by itself evidence that the application emitted no failures.

## Line filters versus parsers

Use a line filter for literal or regular-expression text. Use `json` or `logfmt` when the decision
depends on a structured field, then apply a label filter to the parsed value; `pattern` also exists
for fixed-shape lines. Newer Loki adds pattern-match line filters `|>` / `!>` and the probabilistic
`approx_topk(k, ...)` (instant queries only, no grouping) — version-gated; confirm the deployed
Loki version before using either in a shared rule *[sourced: LogQL query reference, re-checked
2026-08-24]*.

*[sourced: Grafana Loki LogQL line-filter and parser documentation; unverified for target log shape]*

```logql
{app="checkout", env="prod"} |= "timeout"
```

*[sourced: Grafana Loki `json` parser and label-filter syntax; unverified for target field names]*

```logql
{app="checkout", env="prod"} | json | status >= 500 | __error__=""
```

*[sourced: Grafana Loki `logfmt` parser syntax; unverified for target log shape]*

```logql
{app="checkout", env="prod"} | logfmt | level="error"
```

Parser failures can set the `__error__` label, and metric queries cannot contain pipeline errors. Check
or filter parser errors explicitly before trusting an aggregate. *[sourced: Grafana Loki pipeline-error
documentation; unverified for target error policy]*

**Structured metadata — filter it before you parse anything.** Loki 3.x can carry high-cardinality
values (trace IDs, pod names, user IDs, `detected_level`) as *structured metadata*: attached to the
line, not indexed, not in the line text. It is "extracted automatically for each returned log line
and added to the labels", so it filters with plain label syntax and **no parser stage**:

```logql
{app="checkout", env="prod"} | traceID="3c0e3dcd33e7"
```

That is the right shape for "follow one request" — the docs put trace and transaction IDs here
precisely because they are "often used in queries but high cardinality and expensive to extract at
query time". Two rules follow. First, **order matters**: put the structured-metadata filter before
any `| json` / `| logfmt`; if bloom-filter query acceleration is enabled (experimental, needs
structured metadata, aimed at 75 TB/month+ tenants) only a filter that precedes every parser stage
is accelerated. Second, it needs schema v13+ with the `tsdb` index — whether the team's Loki emits
structured metadata at all, and which keys, is `[unverified]` until read from a real line.
*[sourced: Loki structured-metadata, query-acceleration, and cardinality documentation;
reviewed 2026-08-21]*

**`pattern` is the parser for fixed-shape lines** — "easier and faster to write" than `regexp`
and it "outperforms the regexp parser". Named captures become labels, `<_>` skips a field:

```logql
{app="gateway"} | pattern `<ip> - - <_> "<method> <uri> <_>" <status> <size> <_> "<agent>" <_>`
```

A pattern is invalid with no named capture, or with two captures not separated by whitespace —
so a line whose fields abut needs `regexp` after all. *[sourced: LogQL log-queries reference,
pattern parser; reviewed 2026-08-21]*

## Metric queries: rates and complete buckets

`rate` returns log entries per second over a range; `count_over_time` returns the number of entries in
each stream over the range. Aggregate across streams when you need a service total.

*[sourced: Grafana Loki metric-query reference; unverified for target labels and fields]*

```logql
sum by (app) (
  rate({app="checkout", env="prod"} | json | status >= 500 | __error__="" [5m])
)
```

*[sourced: Grafana Loki `count_over_time`; unverified target fields, population, and cadence]*

```logql
sum(count_over_time({app="checkout", env="prod"} | json | status >= 500 | __error__="" [5m]))
```

Evaluate fixed five-minute ranges. Preserve an absent result as unknown unless independent evidence
proves the selector, source freshness, parsing coverage, and eligible population, and the source's
emission contract says an absent error series means no errors. Only that verified case may become
zero; retain a separate missing-telemetry path. Filtering `__error__` prevents query failure, but
silently discarded records still reduce coverage.

For a recurring baseline, record the count with its coverage state, then calculate history in the
configured Prometheus-compatible destination. Loki recording rules remote-write samples there;
a pure Loki query cannot read that derived metric history. Require a complete valid baseline window
before drawing an anomaly conclusion. *[sourced: Loki
[recording rules](https://grafana.com/docs/loki/latest/operations/recording-rules/); unverified target
ruler, remote-write destination, and missing-data policy]*

## Compare before and after a deploy

Select a verified request-completion stream with exactly one event per eligible request/attempt.
The illustrative `log_type` label below must be replaced with the target's discovered selector;
application debug/lifecycle logs are not a request denominator. Confirm fresh, complete ingestion in
both windows and one three-digit HTTP status per completion. Run this coverage ratio first:

*[sourced: Loki metric queries, JSON parsing, and label filters; revised queries and target semantics unverified]*

```logql
sum(count_over_time({app="checkout", env="prod", log_type="request_completion"} | json | status=~"[1-5][0-9]{2}" | __error__="" [30m]))
/
sum(count_over_time({app="checkout", env="prod", log_type="request_completion"} [30m]))
```

Require a positive denominator and coverage of 1. A missing/invalid status, parse failure, empty
population, or unproven ingestion coverage leaves request quality unknown. Then compare failures
per eligible request:

```logql
sum(count_over_time({app="checkout", env="prod", log_type="request_completion"} | json | status=~"5[0-9]{2}" | __error__="" [30m]))
/
sum(count_over_time({app="checkout", env="prod", log_type="request_completion"} [30m]))
```

An absent numerator becomes zero only under the verified no-errors policy above; do not silently
zero-fill the ratio. Errors/sec may accompany it as a labeled volume measure. Doubling requests and
failures at a constant ratio is not evidence of worse request quality.

Evaluate at the end of the after window. For the equal preceding window, add `offset 30m` immediately
after **every** `[30m]` in both coverage and failure-ratio queries. Align the actual windows with the
recorded deploy timestamp; an offset alone is not a deploy marker. Keep selectors, classification,
and window lengths identical between numerator and denominator and across phases.

## Follow one request

Keep the stream selector narrow, then filter the parsed request or trace id. Sort and cross-service
presentation are client concerns; attach the exact query and UTC window to the packet.

The identifier-trust rules in `../SKILL.md` (validate, never concatenate, stop if unencodable)
apply; the LogQL-specific part is the quoting: double-quoted strings require special characters to
be escaped, and a raw backtick-delimited string is safe only after excluding the backtick delimiter.
If arbitrary values are allowed, use a query client that emits a LogQL literal and inspect the
rendered query.

*[sourced: Grafana Loki LogQL string-quoting guidance; unverified target id grammar and query client]*

*[sourced: Grafana Loki `json` parser and label-filter syntax; unverified for target correlation field]*

```logql
{env="prod", app=~"checkout|payments"} | json | request_id="<validated_and_logql_escaped_id>"
```

## Errors that are limits, not bugs

A rejected query or a gap in recent logs can be a configured guardrail, not absent data. Record
the error text verbatim with the query — it is evidence. *[sourced: grafana/loki@4b3f975
troubleshoot and configuration docs]*

- Query-side — narrow instead of raising limits mid-incident: `maximum number of series (<limit>)
  reached for a single query…` (`max_query_series`, upstream default 500 — tighter selectors,
  shorter range, or aggregate) and `max entries limit per query exceeded` (log queries only).
- Ingest-side — missing recent logs is a pipeline finding for the `obs-pipeline` skill: `Per
  stream rate limit exceeded (limit: <X>/sec)… consider splitting a stream via additional labels`;
  stream-count pressure is governed by `max_global_streams_per_user`, and upstream warns against
  raising it to absorb high-cardinality labels.
- Which limits bind this tenant is `[unverified]` until read from the deployed config; upstream
  defaults are not the tenant's limits.
