# LogQL dialect for log investigation

Use this reference only after applying the parent skill's investigation shape. The syntax below is
based on Grafana Loki's current official [LogQL query reference](https://grafana.com/docs/loki/latest/query/)
and [metric-query reference](https://grafana.com/docs/loki/latest/query/metric_queries/), including the
[string-quoting guidance](https://grafana.com/docs/loki/latest/query/log_queries/). Confirm the
deployed Loki version, tenant, labels, parsers, and alert-engine behavior before use.

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
depends on a structured field, then apply a label filter to the parsed value.

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

## Metric queries: rates and complete buckets

`rate` returns log entries per second over a range; `count_over_time` returns the number of entries in
each stream over the range. Aggregate across streams when you need a service total.

*[sourced: Grafana Loki metric-query reference; unverified for target labels and fields]*

```logql
sum by (app) (
  rate({app="checkout", env="prod"} | json | status >= 500 | __error__="" [5m])
)
```

*[sourced: Grafana Loki `count_over_time`, `or`, and `vector` behavior; unverified for target alert
evaluation cadence]*

```logql
sum(count_over_time({app="checkout", env="prod"} | json | status >= 500 | __error__="" [5m]))
or on() vector(0)
```

This is the bucket-first anomaly shape: evaluate fixed five-minute ranges, count the condition inside
each range, and explicitly represent a quiet evaluation as zero before a downstream baseline is built.
Evaluate or record the zero-filled LogQL count every five minutes, then compute trailing average and
standard deviation over that recorded metric in the verified Prometheus-compatible backend. Loki
recording rules remote-write samples to that backend; do not claim that a pure Loki alert or a dependent
Loki recording rule can consume the derived history. *[sourced: Grafana Loki
[recording rules](https://grafana.com/docs/loki/latest/operations/recording-rules/); unverified for the
target ruler, remote-write destination, and evaluation cadence]*

## Compare before and after a deploy

Run the same rate expression over equal-duration windows and use `offset` immediately after the range
selector for the comparison period. A fixed offset is not a deploy marker; record the actual deploy
timestamp and align the windows deliberately.

*[sourced: Grafana Loki `offset` modifier syntax; unverified for target deploy time and labels]*

```logql
sum(rate({app="checkout", env="prod"} | json | status >= 500 | __error__="" [30m]))
```

```logql
sum(rate({app="checkout", env="prod"} | json | status >= 500 | __error__="" [30m] offset 30m))
```

## Follow one request

Keep the stream selector narrow, then filter the parsed request or trace id. Sort and cross-service
presentation are client concerns; attach the exact query and UTC window to the packet.

Correlation ids copied from a ticket or log are untrusted input. Prefer rejecting any value outside the
service's documented identifier grammar, and never concatenate a raw value into LogQL. Double-quoted
strings require special characters to be escaped; a raw backtick-delimited string is safe only after
excluding the backtick delimiter. If arbitrary values are allowed, use a query client that emits a
LogQL literal and inspect the rendered query. Stop if it cannot be represented unambiguously.

*[sourced: Grafana Loki LogQL string-quoting guidance; unverified target id grammar and query client]*

*[sourced: Grafana Loki `json` parser and label-filter syntax; unverified for target correlation field]*

```logql
{env="prod", app=~"checkout|payments"} | json | request_id="<validated_and_logql_escaped_id>"
```

## Inert canary example

This checks reference loading only; it is not a production request id.

*[sourced: Grafana Loki selector, `json`, and label-filter syntax; unverified for target labels]*

```logql
{app="checkout", env="prod"} | json | request_id="<fixture_request_id>"
```

Expected fixture output (inert):

```text
q_ol_loki_8c2d
```
