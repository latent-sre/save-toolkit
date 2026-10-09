# Grafana command access — Windows and macOS

Use when the SRE agent has terminal tools and no Grafana MCP. This reference grants no write
authority; the host loads the command guard, and a skill cannot install or enforce it. Host setup
and acceptance checks live in the repository README and VS Code acceptance record, not here.

## Contents

- Bundled read helper
- Supported native observations
- Grafana resource reads

## Bundled read helper

The installed `grafana` skill includes [grafana_read.py](../scripts/grafana_read.py), a stdlib-only Python 3.11+
client. Run it as `python -I -S` (or `python3`, `python.exe`) with its **absolute installed path** in
drive-letter form, such as `"C:/Users/<you>/.claude/plugins/cache/.../grafana_read.py"`, never a
workspace copy, or call its installed [PowerShell wrapper](../scripts/grafana_read.ps1). The SRE
guard admits only the helper's own argument grammar. It denies the Git Bash `/c/...` path form, the
`py` launcher, double-quoted arguments (single-quote literals instead), `--flag=value`, pipes,
redirection including `2>&1`, `timeout` and other wrappers, and custom URL, method or credential
flags; rely on the host tool's own timeout. The generated Copilot copy is accepted only while its
bytes match the canonical installed helper. If Python or the helper is missing on the execution
host, report it; never install tools or switch shells to get around a denial.

The helper loads `GRAFANA_URL`, `GRAFANA_ORG_ID` and a token (or Basic credentials) from the
environment or, when the environment names none of them, from the human-written
`~/.config/save-toolkit/grafana.env`. Never read, print or edit that file, never set the variables,
and never ask for credentials. A missing or unusable setup is a gap to report:
`authentication_unavailable`, `invalid_settings_file`, `insecure_settings_file`, or an
`invalid_*configuration` error. Every request carries `X-Grafana-Org-Id`, and the helper checks
`/api/org` first, failing closed on a mismatch. It masks the configured credentials in its JSON and
returns static error codes; masking covers only its own output, and the telemetry it returns stays
private evidence.

Substitute the installed path and discovered UIDs; times are examples, not the incident window.
Every form except a raw `--expr` query works in both shells:

```text
python -I -S "<absolute-installed-path>/grafana_read.py" dashboard --uid dashboard-uid
python -I -S "<absolute-installed-path>/grafana_read.py" query --datasource metrics-uid --kind prometheus --from 1758400000000 --to 1758403600000 --expr 'up'
python -I -S "<absolute-installed-path>/grafana_read.py" query --datasource logs-uid --kind loki --from 1758400000000 --to 1758403600000 --expr '{service="example"} |= "error"'
python -I -S "<absolute-installed-path>/grafana_read.py" search --query 'checkout latency'
python -I -S "<absolute-installed-path>/grafana_read.py" alerts --folder-uid folder-uid
python -I -S "<absolute-installed-path>/grafana_read.py" annotations --from 1758400000000 --to 1758403600000 --dashboard-uid dashboard-uid
python -I -S "<absolute-installed-path>/grafana_read.py" silences
python -I -S "<absolute-installed-path>/grafana_read.py" render --uid dashboard-uid --panel 5 --from 1758400000000 --to 1758403600000 --var host=example
```

On **Windows PowerShell 5.1 or PowerShell 7**, run queries through the installed wrapper, which
takes the expression intact and encodes it before invoking Python. Windows PowerShell 5.1 strips the
quotes in PromQL/LogQL selectors when it passes arguments to a native program; 7.3+ does not, but the
guard cannot tell them apart and requires the wrapper (or `--expr-base64`) on either:

```powershell
& '<absolute-installed-path>/grafana_read.ps1' -Datasource logs-uid -Kind loki -From 1758400000000 -To 1758403600000 -Expr '{service="example"} |= "error"'
```

Use single-quoted literal expressions with observed values, never shell expansion or unresolved
dashboard macros. `--expr-base64` is for an exact encoding from trusted tooling; it carries query
bytes and is not encryption. The guard also rejects general script paths and `powershell -Command`.

| Operation | Reads | Limits | Specific errors |
|---|---|---|---|
| `dashboard --uid` | One stored model (`coverage: configuration_only`) | 2 MiB | `invalid_dashboard_response` |
| `query --datasource --kind --from --to --expr` | One Prometheus or Loki `/api/ds/query` POST after checking the datasource UID and type | 24 h, 1,000 points, 500 Loki lines, 2 MiB, 20 s | `datasource_mismatch`, `query_failed`, `unresolved_or_invalid_expression` |
| `search --query` | Dashboards by title text of letters, digits, spaces and `_.:-` | 100 results | — |
| `alerts [--folder-uid]` | Grafana-managed rule groups with state, health and last error | 100 groups, 20 instances per rule | `query_failed` when the rules API reports an error; `folder_mismatch`: Grafana answers a folder this identity cannot see with every folder |
| `annotations --from --to [--dashboard-uid]` | Annotations in the window | 24 h, 100 items | — |
| `silences` | Grafana Alertmanager silences with their state | 2 MiB | — |
| `render --uid --panel --from --to [--var name=value]` | One Classic panel as a 1200×600 PNG in a private temporary file; prints its path, size, SHA-256 and dimensions | 7 days, five `--var` (repeat a name for multi-value), 8 MiB, 45 s | See the [visual verification](./visual-verification.md) error table |

Every operation can also fail with `invalid_arguments`, `organization_mismatch`, `http_error`,
`redirect_rejected`, `request_failed`, `response_too_large` or `invalid_response`. Redirects, ambient
proxies and TLS bypass are disabled; there are no write, arbitrary proxy or SQL operations.

Reading results:

- Exit 0 means the read succeeded, not that the investigation is complete; exit 2 returns a static
  error code. Query errors under HTTP 200 count as failures.
- Keep `coverage`, `truncated` and `limits` with the evidence. `permission_scoped` means an absent
  result is what this identity saw within the limits, not proof that none exists.
- Resolve variables and macros from the actual dashboard selections first; the helper rejects
  unresolved ones. It does not run Grafana expressions, panel transformations or instant queries:
  name those gaps. Missing points or events cannot rule out failures outside the sampled coverage.
- Without `--var`, `render` uses the dashboard's saved variable defaults. Open and inspect the PNG
  before describing it (`coverage: image_uninspected`), and bind it to a query over the same window.
- Missing authentication or an unsupported datasource is a gap: continue with browser or supplied
  evidence rather than rewriting the helper during an incident.

### Copilot command-preview queries

In the Copilot command preview the hook cannot tell which shell runs, so it denies raw `--expr` on
**every terminal shell**, including Bash on macOS. Use `--expr-base64` with an exact encoding from
trusted tooling, or the wrapper in a confirmed PowerShell terminal. For example, `dXA=` encodes `up`:

```text
python -I -S "<absolute-installed-path>/grafana_read.py" query --datasource metrics-uid --kind prometheus --from 1758400000000 --to 1758403600000 --expr-base64 dXA=
```

Do not invent or alter an encoded query. If neither path is available, report the missing query
path. This adds no terminal grant to the standard Copilot profile and does not authorize an encoder.

## Supported native observations

| Need | Windows PowerShell | macOS Bash |
|---|---|---|
| Time/status | `Get-Date -Format o` | `date -u`, `uptime` |
| OS identity | supplied host context | `uname -s`, `sw_vers -productVersion` |
| Service/process status | `Get-Service -Name Spooler`, `Get-Process -Name python` | supplied telemetry; no general process-script grant |
| DNS/connectivity | `Resolve-DnsName example.com`, `Test-NetConnection example.com -Port 443` | `dig example.com` |
| Disk usage | supplied telemetry | `df -h` |
| Application/change evidence | existing `cf`, `gcloud`, `git`, `gh` read forms | same existing read forms |

Names are examples, not discovered targets. Before `ConvertTo-Json`, project only approved fields,
for example `Get-Process -Name python | Select-Object -Property Name,Id,CPU | ConvertTo-Json`;
`Select-Object -First` alone can serialize environment credentials through `StartInfo`. The
PowerShell guard rejects assignments, interpolation, script blocks, command chains, redirection and
interpreter wrappers. The authenticated GET below is the one explicit environment-variable
exception. Preserve named targets and bounded windows from the ask.

## Grafana resource reads

Use the [bundled helper](#bundled-read-helper) first. This `curl` form is a fallback for reads the
helper lacks: health, organization and permission reads, folders, datasource and plugin inventory,
datasource health, dashboard version history, the served `/apis/` dashboard APIs, and
`/api/frontend/settings` (`rendererAvailable`).

It works only when the human has put `GRAFANA_URL` and `GRAFANA_SA_TOKEN` in the process
environment. Setting either one makes the helper ignore its settings file, so the two setups do not
run together. If the variables are absent, report the read as unavailable; never set them, read the
settings file, or ask for a token to make this form work. Its output is not masked: datasource
inventory can carry connection usernames, so report only the fields the task needs. Never print a
credential value or change the destination. Use these exact shapes, replacing only the resource path:

```bash
curl -q --silent --show-error --fail --max-time 20 --max-redirs 0 --proto =https --header "Authorization: Bearer $GRAFANA_SA_TOKEN" "$GRAFANA_URL/api/health"
```

```powershell
curl.exe -q --silent --show-error --fail --max-time 20 --max-redirs 0 --proto =https --header "Authorization: Bearer $env:GRAFANA_SA_TOKEN" "$env:GRAFANA_URL/api/health"
```

Use `curl.exe` on Windows; in Windows PowerShell 5.1, `curl` is an alias for `Invoke-WebRequest`.
The form is one line, GET only, with no redirects, TLS bypass, file output, upload or extra headers.
Search pages are bounded to 100 items and 100 pages. It never permits datasource proxy URLs, query
POSTs, render URLs or `Invoke-RestMethod`; use the helper's `query` and `render`. A 200 response or
a healthy datasource does not prove panel data or delivery. Outside these grants, prepare the read
for the human rather than widening the allowlist.
