# Grafana command access — Windows and macOS

For an SRE agent with terminal tools; no write authority is granted.

## Bundled read helper

The installed `grafana` skill includes [grafana_read.py](../scripts/grafana_read.py), a stdlib-only Python 3.12+
client. Run it as `python -I -S` (or `python3`, `python.exe`) with its **absolute installed path** in
drive-letter form, such as `"C:/Users/<you>/.claude/plugins/cache/.../grafana_read.py"` (on
Copilot, the generated `.github` copy), never another file, or call its installed
[PowerShell wrapper](../scripts/grafana_read.ps1). The SRE guard admits only the helper's own
argument grammar. It denies the Git Bash `/c/...` path form, the `py` launcher, double-quoted
arguments (single-quote literals instead), `--flag=value`, pipes, redirection including `2>&1`,
`timeout` and other wrappers, and custom URL, method or credential flags; rely on the host tool's
own timeout. If Python or the helper is missing on the execution host, report it; never install
tools or switch shells to get around a denial.

For multi-panel investigation use the [agent workflow](./investigation-workflows.md#agent-collection-and-follow-up)
with `--agent-json`. Its grant admits fixed commands/capture IDs, not arbitrary paths or editor
launches. It uses managed dependencies under `python -I`; the read helper requires `python -I -S`.
Windows PowerShell native arguments with embedded double quotes are denied because the shell can
change them; do not switch shells to bypass a denial.

The helper loads `GRAFANA_URL`, `GRAFANA_ORG_ID` and a token (or Basic credentials) from the
environment or, when the environment names none of them, from the human-written
`~/.config/save-toolkit/grafana.env`. Never read, print or edit that file, never set the variables,
and never ask for credentials. A missing or unusable setup is a gap to report:
`authentication_unavailable`, `invalid_authentication`, `invalid_settings_file`,
`insecure_settings_file`, an `invalid_*configuration` error, or the wrapper's `helper_launch_failed`. `render` also fails as `capture_directory_unavailable`, or as
`image_path_masked` when a Basic-auth username or password appears in the capture path; use a
service-account token. Every request carries `X-Grafana-Org-Id`, and the helper checks
`/api/org` first, failing closed on a mismatch. It masks the configured credentials in its JSON and
returns static errors. Masking covers its own output only; returned telemetry remains private.

Substitute the installed path and discovered UIDs; times are examples, not the incident window.
Every form except a raw `--expr` query works in both shells:

```text
python -I -S "<absolute-installed-path>/grafana_read.py" dashboard --uid dashboard-uid
python -I -S "<absolute-installed-path>/grafana_read.py" dashboard --uid dashboard-uid --panel 5
python -I -S "<absolute-installed-path>/grafana_read.py" query --datasource metrics-uid --kind prometheus --from 1758400000000 --to 1758403600000 --expr 'up'
python -I -S "<absolute-installed-path>/grafana_read.py" query --datasource logs-uid --kind loki --from 1758400000000 --to 1758403600000 --expr '{service="example"} |= "error"'
python -I -S "<absolute-installed-path>/grafana_read.py" search --query 'checkout latency'
python -I -S "<absolute-installed-path>/grafana_read.py" search --query orders --folder-uid trading --tag production --page 2
python -I -S "<absolute-installed-path>/grafana_read.py" alerts --folder-uid folder-uid
python -I -S "<absolute-installed-path>/grafana_read.py" alerts --uid rule-uid
python -I -S "<absolute-installed-path>/grafana_read.py" annotations --from 1758400000000 --to 1758403600000 --dashboard-uid dashboard-uid
python -I -S "<absolute-installed-path>/grafana_read.py" silences
python -I -S "<absolute-installed-path>/grafana_read.py" silences --id 11111111-2222-3333-4444-555555555555
python -I -S "<absolute-installed-path>/grafana_read.py" render --uid dashboard-uid --panel 5 --from 1758400000000 --to 1758403600000 --var host=example
python -I -S "<absolute-installed-path>/grafana_read.py" render --uid dashboard-uid --panel 5 --from 1758400000000 --to 1758403600000 --width 1600 --height 900
```

On **Windows PowerShell 5.1 or PowerShell 7**, run queries through the installed wrapper, which
takes the expression intact and encodes it before invoking Python; the guard denies a raw `--expr`
on PowerShell and accepts the wrapper or `--expr-base64`:

```powershell
& '<absolute-installed-path>/grafana_read.ps1' -Datasource logs-uid -Kind loki -From 1758400000000 -To 1758403600000 -Expr '{service="example"} |= "error"'
& '<absolute-installed-path>/grafana_read.ps1' -Datasource metrics-uid -Kind prometheus -From 1758400000000 -To 1758403600000 -Expr 'up' -Mode instant -Output summary
```

Use single-quoted literal expressions with observed values, never shell expansion. The built-in
macros below resolve from explicit inputs; all other unresolved variables are rejected.
`--expr-base64` is for an exact encoding from trusted tooling; it carries query
bytes and is not encryption. The guard also rejects general script paths and `powershell -Command`.

| Operation | Reads | Limits | Specific errors |
|---|---|---|---|
| `dashboard --uid [--panel]` | One stored model, or one Classic panel with dashboard context (`coverage: configuration_only`) | 2 MiB source response | `invalid_dashboard_response`, `unsupported_dashboard_model`, `invalid_panel_tree`, `panel_not_found`, `ambiguous_panel_id` |
| `query --datasource --kind --from --to --expr [--mode range\|instant] [--output full\|summary]` | One Prometheus or Loki `/api/ds/query` POST after checking the datasource UID and type | 24 h input window; requests 1,000 points and 500 Loki lines; enforced 2 MiB response cap and 20 s timeout | `datasource_mismatch`, `query_failed`, `unresolved_or_invalid_expression` |
| `search --query [--page] [--folder-uid] [--tag]` | Dashboards by title text, optionally scoped to one folder and tag; query/tag accept letters, digits, spaces and `_.:-` | 100 results per call, pages 1–100 | `invalid_search_response`, `folder_mismatch` if a scoped response contains another folder |
| `alerts [--folder-uid]` | Grafana-managed rule groups with state, health and last error | 100 groups, 20 instances per rule | `query_failed` when the rules API reports an error; `folder_mismatch`: Grafana answers a folder this identity cannot see with every folder |
| `alerts --uid` | One Grafana-managed rule definition, including returned provenance and pause settings | 2 MiB; cannot combine with `--folder-uid` | `alert_rule_mismatch`, `organization_mismatch` |
| `annotations --from --to [--dashboard-uid]` | Annotations in the window | 24 h, 100 items | — |
| `silences [--id]` | Built-in Grafana Alertmanager silences, or one exact silence by UUID | 2 MiB | `silence_mismatch` for a mismatched ID |
| `render --uid --panel --from --to [--var name=value] [--width] [--height]` | One Classic panel as an owner-only PNG in `~/.cache/save-toolkit/grafana-renders/` (renders older than a day are deleted); prints its path, size, SHA-256 and verified dimensions | Default 1200×600; width 400–2400, height 200–1600; 7 days, five `--var` (repeat a name for multi-value), 8 MiB, 45 s | See the [visual verification](./visual-verification.md) error table |

Every operation can also fail with `invalid_arguments`, `organization_mismatch`, `http_error`,
`redirect_rejected`, `request_failed`, `response_too_large` or `invalid_response`. Redirects, ambient
proxies and TLS bypass are disabled; there are no write, arbitrary proxy or SQL operations.

Reading results:

- Exit 0 means the read succeeded, not that the investigation is complete; exit 2 returns a static
  error code. Query errors under HTTP 200 count as failures.
- Keep `coverage`, `truncated` and `limits` with the evidence. `permission_scoped` means an absent
  result is what this identity saw within the limits, not proof that none exists.
- Search fetches one page per invocation. Keep the query, folder and tag fixed when following
  `next_page`; a full page means more results may exist, not that they do. Stop at the task's cap
  and retain `truncated` even when page 100 has no permitted next page. Search is not a stable
  snapshot: concurrent dashboard changes can cause duplicates or omissions across pages.
- Selected panels retain stored targets, transformations, field configuration and dashboard context,
  not necessarily the viewer's current selections. References/macros remain unresolved; no query or
  transformation runs.
- `alerts --uid` reads configuration, not evaluation health or notification delivery. Pair it with
  the folder's state read. `silences --id` verifies only the built-in Grafana Alertmanager's object;
  it does not inspect an external Alertmanager or prove an alert is suppressed.
- Resolve variables from actual selections; only the built-ins below expand. Grafana expressions
  and transformations do not run; missing points cannot rule out failures beyond sampled coverage.
- Without `--var`, `render` uses the dashboard's saved variable defaults. Open and inspect the PNG
  before describing it (`coverage: image_uninspected`), and bind it to a query over the same window.
- Missing authentication or an unsupported datasource is a gap: continue with browser or supplied
  evidence rather than rewriting the helper during an incident.

### Copilot command-preview queries

In the Copilot command preview the hook cannot tell which shell runs, so it denies raw `--expr` on
**every terminal shell**, including Bash on macOS. Use `--expr-base64` with an exact encoding from
trusted tooling. The command-preview grant requires a double-quoted installed script path and
unquoted arguments containing only letters, digits and safe literal punctuation. It rejects
single-quoted values, spaces in argument values, shell operators and expansion syntax because
their interpretation depends on the terminal shell. The PowerShell wrapper belongs to the
confirmed PowerShell tool grant and is denied by this preview. For example, `dXA=` encodes `up`:

```text
python -I -S "<absolute-installed-path>/grafana_read.py" query --datasource metrics-uid --kind prometheus --from 1758400000000 --to 1758403600000 --expr-base64 dXA=
```

Do not invent or alter an encoded query. If neither path is available, report the missing query
path. This adds no terminal grant to the standard Copilot profile and does not authorize an encoder.

## Query modes, macros and result summaries

`--mode range` and `--output full` remain the defaults. `--mode instant` evaluates at `--to`;
both absolute timestamps remain required because the window supplies range macros. Prometheus
and Loki metric instant queries are supported; a backend may reject an instant log-stream query.
The PowerShell equivalents are `-Mode`, `-Output`, `-IntervalMs` and `-RateIntervalMs`.

The helper expands only these built-ins, including their exact `${__name}` forms:

| Macro | Required source |
|---|---|
| `$__range`, `$__range_s`, `$__range_ms` | Difference between `--to` and `--from`; duration, seconds and milliseconds respectively |
| `$__interval`, `$__interval_ms` | Explicit `--interval-ms` from the panel's query context; also used for the request's `intervalMs` |
| `$__rate_interval` | Explicit `--rate-interval-ms` from the Prometheus panel's query context |

The rate interval depends on scrape cadence and the query's minimum step; it cannot be inferred
from the time window alone. Do not guess it. The regular interval must be at least the larger of
1,000 ms and the window divided by 1,000, rounded up; this preserves the helper's request-density
bound. Both explicit intervals are capped at 86,400,000 ms, and the rate interval is at least
1,000 ms. Rate intervals are Prometheus-only. Other variables, macro format modifiers and
unresolved interval macros fail before authentication. The result records original/resolved
expressions and substitutions; inspect them before claiming equivalence with the panel.

Queries include a `summary`; `--output summary` omits raw `results`, retaining provenance, settings
and expressions. Numeric summaries report finite minima/maxima, last returned/finite values and null
counts, without Grafana reductions or metric interpretation. Logs report counts/timestamps, not lines.
Detailed series cap at 100 with explicit truncation. Empty, all-null, zero and unsupported remain
distinct; complete means parsed, not healthy. Encoded frames and numeric tables with row-label series
identities are unsupported: retain full output for a capable reader rather than interpreting
placeholders or merging different series.

Compare actual timestamp bounds/counts with requested `from`/`to` and `limits`. `maxDataPoints` is a
hint: alignment may return extra/out-of-window points, reported without clipping. The 2 MiB cap is
enforced. Retain `coverage: not_established` until results/gaps are assessed; compact output proves
neither complete history nor notification delivery.

## Grafana resource reads

Use the [bundled helper](#bundled-read-helper) first. This `curl` form is a fallback for reads the
helper lacks: health, your token's permissions, folders, plugin inventory, datasource health, and a
single `/apis/` dashboard object. The guard denies every other path, including
`/api/frontend/settings` and `/api/datasources`, whose unmasked output can carry datasource
connection users or decrypted credentials.

It works only when the human has put `GRAFANA_URL` and `GRAFANA_SA_TOKEN` in the process
environment. Setting either one makes the helper ignore its settings file, so the two setups do not
run together; the helper then also needs `GRAFANA_ORG_ID` in the environment. If the variables are
absent, report the read as unavailable; never set them, read the settings file, or ask for a token
to make this form work. Never print a credential value or change the destination. Use these exact
shapes, replacing only the resource path:

```bash
curl -q --silent --show-error --fail --max-time 20 --max-redirs 0 --proto =https --header "Authorization: Bearer $GRAFANA_SA_TOKEN" "$GRAFANA_URL/api/health"
```

```powershell
curl.exe -q --silent --show-error --fail --max-time 20 --max-redirs 0 --proto =https --header "Authorization: Bearer $env:GRAFANA_SA_TOKEN" "$env:GRAFANA_URL/api/health"
```

Use `curl.exe` on Windows; in Windows PowerShell 5.1, `curl` is an alias for `Invoke-WebRequest`.
The form is one line, GET only, with no redirects, TLS bypass, file output, upload or extra headers.
Folder pages are bounded to 100 items and 100 pages. It never permits datasource proxy URLs, query
POSTs, render URLs or `Invoke-RestMethod`; use the helper's `query` and `render`. A 200 response or
a healthy datasource does not prove panel data or delivery. Outside these grants, prepare the read
for the human rather than widening the allowlist.
