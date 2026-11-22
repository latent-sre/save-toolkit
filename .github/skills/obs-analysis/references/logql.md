# LogQL dialect for log investigation

## Stream selectors and absence

Check a candidate stream with `absent_over_time({app="settlement-api", env="prod"}[10m])` (returns
`1` only when no lines match). Wrong selector/tenant, silent source, and lost ingestion remain
open alternatives. Do not mask absence with `or on() vector(0)` in diagnostic or ratio queries.

## Parsers vs. structured metadata

- Pipeline parse errors set `__error__`, which metric queries reject; filtering `__error__=""`
  drops unparsed lines, so verify parsing coverage separately.
- `approx_topk(k, ...)` is experimental, tenant-flagged (`shard_aggregations`), and instant-only.
- **Structured metadata** (schema v13+ with `tsdb`) indexes neither keys nor text; place filters
  before any `json`/`logfmt` stage: `{app="checkout", env="prod"} | traceID="3c0e3dcd33e7"`.

## Compare before vs. after a deploy

Count one completion event per eligible request across complete, fresh buckets (`log_type` is an
example selector — resolve on target). First verify classification coverage equals `1`:

```logql
sum(count_over_time({app="checkout", env="prod", log_type="request_completion"} | json | status=~"[1-5][0-9]{2}" | __error__="" [30m]))
/
sum(count_over_time({app="checkout", env="prod", log_type="request_completion"} [30m]))
```

With positive denominator and coverage `1`, swap the numerator regex to `5[0-9]{2}` for the
failure ratio. Evaluate at the after-window end; for the before-window, add `offset 30m`
immediately after **every** `[30m]` in both numerator and denominator. Loki recording rules
remote-write samples to Prometheus/Mimir; pure LogQL cannot query that derived series.

## Follow one request and limit errors

- Prefilter line text before parsing, then exact-match (`{env="prod", app=~"checkout|payments"} |= "<id>" | json | request_id="<id>"`).
- **Limits (read deployed overrides, not upstream defaults):** `max_query_series` (upstream default
  500) and `max entries limit per query exceeded` require narrowing selectors/range; `Per stream rate
  limit exceeded` and `max_global_streams_per_user` pressure are ingest/pipeline issues
  ([Alloy pipeline](./alloy.md)).
