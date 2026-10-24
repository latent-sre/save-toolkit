# Cloud Logging dialect for log investigation

Syntax references: [Logging query language](https://docs.cloud.google.com/logging/docs/view/logging-query-language)
and [`gcloud logging read`](https://docs.cloud.google.com/sdk/gcloud/reference/logging/read).

## Start narrow

Logging filters select entries; they do not aggregate. Choose Logs Explorer's histogram,
Observability Analytics SQL, or a log-based metric for time-series/top-N work.

- Map/struct keys are case-sensitive: `jsonPayload.requestId` differs from `requestid`; so do
  `labels` keys. Protocol-buffer field names and ordinary string comparisons are case-insensitive;
  regex is case-sensitive and `AND`/`OR`/`NOT` must be capitalized.
- `log_id("run.googleapis.com/stderr")` uses the unencoded id; the full field requires
  `logName="projects/<project>/logs/run.googleapis.com%2Fstderr"`.
- Cloud Run's completion population is `log_id("run.googleapis.com/requests")`, with
  `httpRequest.status` and duration-valued `httpRequest.latency` (such as `3.5s`). A severity-only
  filter also admits app stderr and is not a request denominator. Under PowerShell, use
  `logName=projects/<project>/logs/run.googleapis.com%2Frequests` to avoid forbidden parentheses.
- `SEARCH("world")` matches token boundaries, not `worlds`, and cannot match non-text fields.
- Inspect one entry's payload shape before filtering: `jsonPayload.<field>` and `textPayload`
  differ, and a predicate on an absent field silently matches nothing.

## Read it over time

Analytics `GROUP BY` omits empty buckets. Generate the bounded bucket series and left-join counts;
zero-fill only after checking freshness and ingestion coverage. Log-based metrics are not
retroactive: they cannot reconstruct an earlier incident.

## Correlate one request

Cloud Run request logs carry `trace="projects/<project>/traces/<trace-id>"`. App stdout/stderr
carries it only through `logging.googleapis.com/trace` or a Cloud Logging client library; request
rows alone cannot establish missing app logging. For [Cloud Trace](./gcp-trace.md), strip the
`projects/<project>/traces/` prefix; a W3C trace id is 32 hex characters. Prefer exact-field `=` to
global `SEARCH()`, escaping quotes and backslashes using Logging's quoted-string rules.

## gcloud read from the terminal

```bash
gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name="<service>" AND resource.labels.location="<region>" AND severity>=ERROR' --project=<project_id> --freshness=1h --limit=50 --format='table(timestamp,severity,resource.labels.revision_name,httpRequest.status,httpRequest.latency)'
```

- Bind `--project` and Cloud Run's `resource.labels.location`. Bucket `--location` is separate;
  for a particular bucket/view, select discovered `--location`, `--bucket`, and `--view` supported
  by the client. Same-named services in different regions are different populations.
- `--freshness` defaults to `1d`, works only with DESC ordering and no timestamp filter. For a
  named event replace it with absolute UTC timestamp bounds; do not combine the two.
- `--limit` defaults to unlimited: always set it. Use `--format=json` only for one targeted entry,
  an explicit JSON request, or PowerShell's projection restriction; keep JSON limits small.
- **Fleet Bash guard:** comparisons such as `severity>=ERROR` and timestamp/numeric bounds are
  permitted inside a quoted filter argument; unquoted `>=` is denied as shell redirection.
- **Fleet PowerShell guard:** `>`, `<` and parentheses are denied even inside quotes, including
  `table(...)` and `severity=(ERROR OR CRITICAL OR ALERT OR EMERGENCY)`. Use JSON and this floor:
  `NOT severity=DEFAULT AND NOT severity=DEBUG AND NOT severity=INFO AND NOT severity=NOTICE AND NOT severity=WARNING`.
  It retains ERROR, CRITICAL, ALERT and EMERGENCY, equivalent to `severity >= "ERROR"`. Run OR'd
  conditions such as `httpRequest.status=429` separately: mixed AND/OR requires parentheses.
  Pass simple letters/digits/inner-hyphen values bare; embedded double-quote passage is untested.
  Use `--freshness` for bounded PowerShell reads because comparison timestamp filters are denied.

## Observability Analytics (SQL over logs)

Observability Analytics (formerly Log Analytics) provides BigQuery-backed SQL over logs and traces.
Check that the selected log bucket is upgraded before promising SQL aggregation or gap filling.

## Tips & gotchas

- `_Default` sink excludes some logs; Data Access audit logs are opt-in. Check sink/exclusions
  before interpreting absence.
- `entries.list` has a non-increasable quota of 60 calls/min per project; unbounded reads can
  starve console users.
- `_Required` retention is 400 days, not configurable. `_Default` and user-created buckets default
  to 30 days, configurable per bucket. Past-retention absence does not establish absence at write time.
