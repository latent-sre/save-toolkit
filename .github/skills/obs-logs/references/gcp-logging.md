# Cloud Logging dialect for log investigation

Apply the parent investigation shape first. Syntax follows the official references below;
validate filters against the target project and client.

Official syntax basis: the
[Logging query language](https://docs.cloud.google.com/logging/docs/view/logging-query-language)
and [`gcloud logging read`](https://docs.cloud.google.com/sdk/gcloud/reference/logging/read).

## Contents

- Start narrow
- Read it over time
- Correlate one request
- gcloud read from the terminal
- Observability Analytics (SQL over logs)
- Tips & gotchas

## Start narrow

The Logging query language is a **filter** language: it selects entries and does not aggregate
them, so time-series and top-N questions route through the Logs Explorer histogram, log-based
metrics, or Observability Analytics SQL — pick the surface before writing the "query".

```text
resource.type = "cloud_run_revision"
resource.labels.service_name = "<service>"
severity >= "ERROR"
timestamp >= "2026-08-07T00:00:00Z" timestamp <= "2026-08-07T00:30:00Z"
```

- Preserve the exact case and spelling of map/struct keys: `jsonPayload.requestId` and
  `jsonPayload.requestid` address different fields; `labels` keys follow the same rule.
  Regular protocol-buffer field names and ordinary string comparisons are case-insensitive;
  regular expressions are case-sensitive, and `AND`/`OR`/`NOT` must be capitalized.
- Operators: `=`, `!=`, `:` (substring/has), `=~` / `!~` (regex), and range comparisons.
- Prefer `log_id("run.googleapis.com/stderr")`. The full-field form is
  `logName="projects/<project>/logs/run.googleapis.com%2Fstderr"`: encode the log ID's slash
  in `logName`, but not in `log_id()`.
- **Request completion on Cloud Run is the request log**, `log_id("run.googleapis.com/requests")`:
  written automatically for each request to a service, with `httpRequest.status` and
  `httpRequest.latency` (a duration such as `3.5s`). It is a rate's denominator;
  `severity >= "ERROR"` mixes request entries with the app's own stderr lines. Under PowerShell,
  where the guard refuses parentheses, select it as
  `logName=projects/<project>/logs/run.googleapis.com%2Frequests`.
- `SEARCH("text")` matches on **token boundaries** (`SEARCH("world")` matches `world`, not
  `worlds`) and cannot match non-text fields — it is not a substring grep.
- A structured payload field lives at `jsonPayload.<field>`; plain text at `textPayload`. A filter
  on a field the entry doesn't carry silently matches nothing — the same false-all-clear trap as
  an unextracted Splunk field. Confirm the payload shape with one unfiltered read first.

## Read it over time

The filter alone cannot bucket: use the Logs Explorer histogram for a quick visual, Observability
Analytics SQL for exportable aggregation, or a log-based metric for the recurring version.
`GROUP BY` returns only populated buckets, so for a complete timeline generate the bounded bucket
series and left-join counts; turn missing counts into zero only after confirming source freshness
and ingestion coverage. Log-based metrics are **not retroactive** — useless for the incident you
are in now, right for the next one.

## Correlate one request

Cloud Run request logs carry `trace` (`projects/<project>/traces/<trace-id>`); filter on it to
follow one request across services. App lines (`run.googleapis.com/stdout`, `/stderr`) carry it
only when the app writes `logging.googleapis.com/trace` or uses a Cloud Logging client library, so
request-log rows alone do not mean the app logged nothing.
To pivot to the trace backend (`obs-traces`), strip the `projects/<project>/traces/` prefix; the
remainder is the trace id (32 hex characters for a W3C trace id). Validate any
identifier copied from a ticket against its documented format before it enters a filter, and
prefer `=` on an exact field over a global `SEARCH()`. Escape quotes and backslashes per the
query language's quoted-string rules before a value enters a filter literal; a value that cannot
be encoded unambiguously is a stop-and-ask, not a broader match.

## gcloud read from the terminal

```bash
gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name="<service>" AND resource.labels.location="<region>" AND severity>=ERROR' --project=<project_id> --freshness=1h --limit=50 --format='table(timestamp,severity,resource.labels.revision_name,httpRequest.status,httpRequest.latency)'
```

- The `table(...)` projection keeps the excerpt small. Use `--format=json` only for one targeted
  entry, when the caller asks for JSON, or under PowerShell, whose guard denies the projection's
  parentheses; keep `--limit` small with JSON.
- Bind the project explicitly and the Cloud Run region through `resource.labels.location`; a
  same-named service in another region is a different population. For a specific log bucket/view,
  also select the discovered `--location`, `--bucket`, and `--view` scope supported by the client;
  bucket location is distinct from the Cloud Run resource location.
- For a named event, replace freshness with explicit absolute UTC timestamp bounds in the filter.
- `--freshness` (default `1d`) supplies the time bound and "works only with DESC ordering and
  filters without a timestamp" — so use it INSTEAD of
  `timestamp >=` comparisons, not alongside them.
- **Fleet-specific**: the read-only guard treats the two shells differently. Through the Bash
  tool it permits comparison operators (`severity>=ERROR`, timestamp and numeric bounds) **inside a
  quoted filter argument** and denies an unquoted `>=` as a shell redirect. Through the PowerShell
  tool it refuses `>`, `<` and parentheses anywhere, even inside quotes, so the example above and
  `severity=(ERROR OR CRITICAL OR ALERT OR EMERGENCY)` are denied there. For PowerShell,
  write the floor as exclusions — `NOT severity=DEFAULT AND NOT severity=DEBUG AND NOT
  severity=INFO AND NOT severity=NOTICE AND NOT severity=WARNING` — and run any OR'd condition
  such as `httpRequest.status=429` as a separate read: Google requires parentheses whenever AND
  and OR are mixed. There, pass values bare when they are only letters, digits and inner hyphens
  (legal unquoted); embedded double quotes may not survive PowerShell's native argument passing,
  which is untested. Bound time with `--freshness` in either shell.
- `--limit` defaults to **unlimited** — always set it.

## Observability Analytics (SQL over logs)

Log Analytics was renamed **Observability Analytics** (June 2026): BigQuery-backed SQL over logs
and traces, where "top offenders" and "before vs after, as rates" can be answered with explicit
gap filling. Log buckets must be upgraded for it — upgrade state per bucket is unknown, so
check before promising a SQL answer.

## Tips & gotchas

- **Record the boundary**: project(s), log bucket/view, filter, absolute UTC window, and which
  surface ran it (Explorer / gcloud / Analytics) — a filter without its project and bucket is not
  reproducible evidence.
- Severity floor via `severity=(ERROR OR CRITICAL OR ALERT OR EMERGENCY)`, via
  `severity >= "ERROR"`, and via the exclusion chain above are equivalent, including ALERT and
  EMERGENCY: LogSeverity has nine values, five below ERROR. Only
  the exclusion chain passes the guard under PowerShell.
- The `_Default` sink does not capture everything (Data Access audit logs are opt-in); absence of
  an entry proves nothing until the sink/exclusion config is checked — exclusions are silent.
- Quota: `entries.list` is rate-limited to **60 calls/min per project** and the limit cannot be
  raised; a greedy unlimited read mid-incident
  can starve the humans' consoles. Set `--limit`, narrow first.
- Retention: the `_Required` bucket keeps its logs **400 days, not configurable**; `_Default` and
  user-created buckets default to **30 days**, configurable per bucket. "No entries" past the
  bucket's retention is ageing, not absence at write time.
