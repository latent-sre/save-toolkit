# Cloud Logging dialect for log investigation

## Filters, populations, and correlation

- Logging filters select entries (use Logs Explorer, Observability Analytics SQL, or log-based
  metrics to aggregate; log-based metrics are not retroactive).
- Map/struct keys (`jsonPayload.requestId`) and `labels` keys are case-sensitive; proto field names
  and string comparisons are case-insensitive; regex is case-sensitive; Boolean operators `AND`, `OR`,
  `NOT` must be uppercase.
- Cloud Run's request population is `log_id("run.googleapis.com/requests")` (`httpRequest.status`,
  `httpRequest.latency`; use `logName="projects/<project>/logs/run.googleapis.com%2Frequests"` or in
  PowerShell `logName=projects/<project>/logs/run.googleapis.com%2Frequests` without parentheses).
  `SEARCH("world")` is token-boundary text search only.
- Request logs store `trace` as `projects/<project>/traces/<trace-id>` or bare `<trace-id>` (32 hex
  chars for W3C). For [Cloud Trace](./gcp-trace.md), strip any `projects/<project>/traces/` prefix.

## Terminal reads (`gcloud logging read`)

```bash
gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name="<service>" AND resource.labels.location="<region>" AND severity>=ERROR' --project=<project_id> --freshness=1h --limit=50 --format='table(timestamp,severity,resource.labels.revision_name,httpRequest.status,httpRequest.latency)'
```

- Always bind `--project`, `resource.labels.location`, and `--limit`. Use `--freshness` with DESC
  order OR absolute UTC timestamp bounds (never both).
- **Bash guard:** quoted filters allow `>=` comparisons. **PowerShell guard:** forbids `>`, `<`, and
  parentheses even in quotes — use `--format=json`, `--freshness`, and
  `NOT severity=DEFAULT AND NOT severity=DEBUG AND NOT severity=INFO AND NOT severity=NOTICE AND NOT severity=WARNING`
  (run OR'd predicates separately).

## Observability Analytics, sinks, quotas, and retention

- **Observability Analytics (SQL):** verify the bucket was upgraded before trusting SQL counts;
  pre-upgrade entries require backfill (automatic backfill paused; manual backfill via Cloud
  Customer Care).
- **Sinks & defaults:** `_Default` sink exclusions can drop matching logs; Data Access audit logs
  are off by default except for BigQuery.
- **Quotas & retention:** `entries.list` is capped at **60 calls/minute per project** and is **not
  increasable**. `_Required` retention is **400 days** (fixed); project `_Default` and custom buckets
  default to **30 days**.
