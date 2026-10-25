# LogQL dialect for log investigation

Syntax references: [LogQL](https://grafana.com/docs/loki/latest/query/),
[metric queries](https://grafana.com/docs/loki/latest/query/metric_queries/), and
[string quoting](https://grafana.com/docs/loki/latest/query/log_queries/).

## Stream selectors and label discipline

Keep bounded app/environment/cluster/namespace values as indexed labels; request ids belong in
parsed fields or structured metadata. To check a candidate stream:

```logql
absent_over_time({app="settlement-api", env="prod"}[10m])
```

It returns 1 for no matching lines, nothing when lines exist. Wrong selector/tenant, silent source
and lost ingestion remain alternatives; find the last line before assigning a pipeline fault.
`or on() vector(0)` hides this distinction by turning no matches into zero-valued samples.

## Line filters versus parsers

- Parser failures set `__error__`; metric queries cannot contain pipeline errors. Filtering them
  avoids query failure but discards records, so separately check parsing coverage.
- `|>` / `!>` pattern-match filters and probabilistic `approx_topk(k, ...)` are version-gated;
  `approx_topk` supports instant queries only, without grouping.
- A `pattern` needs a named capture and whitespace between captures; abutting fields need `regexp`.

Loki 3.x structured metadata attaches high-cardinality fields to lines without indexing or including
them in the text. It needs schema v13+ and the `tsdb` index. Confirm actual emitted keys; filter them
without a parser:

```logql
{app="checkout", env="prod"} | traceID="3c0e3dcd33e7"
```

Put that filter before every `json`/`logfmt` stage. Experimental bloom-filter acceleration requires
structured metadata and only accelerates filters preceding parsers; confirm availability on the tenant.

## Metric queries: rates and complete buckets

`rate` counts lines/second; `count_over_time` counts lines per stream. Aggregate streams for service
totals; retain coverage state for the selected range. An absent error series may become
zero only after independent proof of selector, freshness, parsing and eligible population, plus an
emission contract that absence means no errors. Retain a separate missing-telemetry path.

For recurring baselines, Loki recording rules remote-write samples to a Prometheus-compatible
destination; a pure Loki query cannot read that derived history. Confirm ruler, destination and
missing-data policy, and require a complete valid baseline window.

## Compare before and after a deploy

Use one completion event per eligible request/attempt; debug/lifecycle lines are not a denominator.
Replace illustrative `log_type` with the discovered selector. Require fresh, complete ingestion in
both windows and a single three-digit HTTP status per completion. First check status coverage:

```logql
sum(count_over_time({app="checkout", env="prod", log_type="request_completion"} | json | status=~"[1-5][0-9]{2}" | __error__="" [30m]))
/
sum(count_over_time({app="checkout", env="prod", log_type="request_completion"} [30m]))
```

Require positive denominator and coverage 1. Missing/invalid status or parse failures leave request
quality unknown. Then calculate failures per eligible request:

```logql
sum(count_over_time({app="checkout", env="prod", log_type="request_completion"} | json | status=~"5[0-9]{2}" | __error__="" [30m]))
/
sum(count_over_time({app="checkout", env="prod", log_type="request_completion"} [30m]))
```

Do not silently zero-fill an absent numerator; apply the verified no-errors policy above. Errors/sec
is volume, not request quality: doubling requests and failures at a constant ratio is not regression.
Evaluate at the after-window end. For the preceding window, add `offset 30m` immediately after
**every** `[30m]` in both queries. Align windows with the actual deploy; preserve selector,
classification and duration across numerator, denominator and phases.

## Follow one request

For line text, prefilter before parsing, then match the parsed ID exactly:

```logql
{env="prod", app=~"checkout|payments"} |= "<validated_and_logql_escaped_id>" | json | request_id="<validated_and_logql_escaped_id>"
```

For structured metadata, use its parser-free shape above. Double-quoted literals require escaping;
raw backtick strings require excluding the backtick delimiter. For arbitrary values, use a client
that emits a LogQL literal and inspect the rendered query. Sorting/cross-service presentation is
client-side.

## Errors that are limits, not bugs

| Error or pressure | Relevant limit and response |
|---|---|
| `maximum number of series (<limit>) reached for a single query` | `max_query_series`, upstream default 500; tighten selectors/range or aggregate |
| `max entries limit per query exceeded` | Log-query limit, not evidence of absent logs |
| `Per stream rate limit exceeded (limit: <X>/sec)` | Ingest-side; route to `obs-pipeline` |
| Stream-count pressure | `max_global_streams_per_user`; do not raise it to absorb high-cardinality labels |

Read deployed configuration: upstream defaults do not establish this tenant's limits.
