# Grafana command access — Windows and macOS

Use when the SRE agent has terminal tools and no Grafana MCP. This reference grants no write
authority. The host must load the matching command guard; a skill cannot install or enforce it.

## Contents

- Host prerequisites
- Bundled read helper
- Supported native observations
- Grafana resource reads

## Host prerequisites

- **Claude Code:** the canonical SRE agent grants Bash and PowerShell, with separate PreToolUse
  handlers. Windows still needs Git for Windows for this plugin's POSIX SessionStart hook, plus a
  working Python 3.11+ interpreter. macOS needs that interpreter and a POSIX shell. PowerShell's
  guard accepts a literal subset, not arbitrary scripts or expressions.
- **VS Code/Copilot:** the standard projection remains without terminal access. The generator can
  export a command preview for a neutral, isolated plugin acceptance session. It grants only
  `execute/runInTerminal` and `execute/getTerminalOutput`, with an agent-scoped hook and OS-specific
  launchers. On inspected VS Code 1.138.0, verify `chat.useHooks` and workspace trust; the old
  `chat.useCustomAgentHooks` switch is absent. Export on the execution host to bind the scripts'
  absolute path; re-export after moving the installation. Prove an allowed read and a denied
  harmless command, and prove the built-in Agent is unaffected. Hook launch failures and timeouts
  need not block commands: this is a best-effort check, not a sandbox. Disabled/failed hooks or
  unverified scoping means no production reads under the preview. Copilot CLI/cloud are not covered.
- Resolve executable availability in the actual execution host: a remote/WSL extension host may
  differ from the workstation. Report missing CLI/authentication rather than installing tools or
  substituting another shell to bypass a denial.

## Bundled read helper

The installed `grafana` skill includes [grafana_read.py](../scripts/grafana_read.py), a stdlib-only Python 3.11+
client. Resolve its **absolute installed path**, not a workspace file with the same relative name.
The SRE shell guard permits only this helper's validated argument grammar under `python -I -S`
(also `python3` or `python.exe`) or its installed [PowerShell wrapper](../scripts/grafana_read.ps1),
with no pipes, redirection, custom URL, method or credential flags.
The generated Copilot copy is accepted only while its bytes match the canonical installed helper.
An interpreter outside these forms is not implicitly granted. PATH and installation integrity remain
host responsibilities; this is not general permission to run Python.

The human-controlled launcher supplies `GRAFANA_URL` (trusted HTTPS origin plus optional subpath),
`GRAFANA_ORG_ID` (the expected positive organization ID), and either `GRAFANA_SA_TOKEN` or both
`GRAFANA_USERNAME` and `GRAFANA_PASSWORD`. The helper prefers
the token if both methods are present. Basic authentication works only where the instance supports
it; browser SSO does not populate API credentials. Use existing SSO through the browser when
available; do not extract its cookies. No values belong in prompts, argv, tracked files, or logs.
Credentials may come from the human's secret manager/launcher; this helper does not read arbitrary
credential files or install a credential store. Do not ask the model to configure secret values.

Use a read-only identity scoped to the intended organization, dashboards and datasources. The
helper cannot grant access. It sends `X-Grafana-Org-Id` on every request and verifies `/api/org`
matches before the requested read. A missing or mismatched organization fails closed; the helper
does not switch the user's active organization. Successful results include the verified organization.
It masks the configured authentication values in returned JSON and
returns static errors instead of server error bodies, headers or exception traces. This protects
its result boundary, not all host processes, files or other tools; retain the host's credential
protections and do not claim OS isolation. Private telemetry remains private evidence.

Substitute the actual installed path and discovered UIDs. The dashboard form works in both shells.
The direct query examples below are for **Bash**; do not use raw `--expr` through native PowerShell:

```text
python -I -S "<absolute-installed-path>/grafana_read.py" dashboard --uid dashboard-uid
python -I -S "<absolute-installed-path>/grafana_read.py" query --datasource metrics-uid --kind prometheus --from 1758400000000 --to 1758403600000 --expr 'up'
python -I -S "<absolute-installed-path>/grafana_read.py" query --datasource logs-uid --kind loki --from 1758400000000 --to 1758403600000 --expr '{service="example"} |= "error"'
```

For **Windows PowerShell 5.1 or PowerShell 7**, call the installed wrapper as a script. It accepts
the expression intact and encodes it internally before invoking Python; this avoids native-program
argument handling removing the quotes in PromQL/LogQL selectors. The agent need not encode it:

```powershell
& '<absolute-installed-path>/grafana_read.ps1' -Datasource logs-uid -Kind loki -From 1758400000000 -To 1758403600000 -Expr '{service="example"} |= "error"'
```

Use literal single-quoted expressions and observed values; no shell expansion or unresolved
dashboard macros. Direct Python `--expr-base64` is available for a trusted caller that already has
the UTF-8 encoding. Encoding preserves query bytes; it is not encryption or permission to run code.
The helper decodes and validates the same expression rules. The guard rejects raw Python `--expr`
on PowerShell, general script paths and `powershell -Command` wrappers.

Times above are examples, not the current incident window. `dashboard` reads one UID's stored model.
`query` first verifies the datasource UID/type, then sends only a bounded `/api/ds/query` request
for Prometheus or Loki. Query POST is a read operation here, not a general HTTP-method grant.
There are no deployment, dashboard/alert write, arbitrary proxy or SQL operations. Redirects,
ambient proxies and TLS bypass are disabled. Limits: 24-hour window, 1,000 requested points,
500 Loki lines, 2 MiB response and a 20-second network timeout. Retain the host tool's wall timeout.

Resolve variables and macros from actual dashboard selections before querying; the helper rejects
unresolved variables rather than guessing substitutions. It does not execute Grafana expressions,
apply panel transformations or reproduce instant-query panels: keep those comparison gaps explicit.
Successful API results do not prove complete history, rendered appearance or service health.
The returned limits and coverage field stay with the evidence; missing points/events cannot rule
out failures outside sampled coverage. Query-level errors count as failure even under HTTP 200.

Exit 0 means the selected API operation succeeded, not that the investigation is complete. Exit 2
returns a safe error category. Missing authentication or unsupported data is a gap; continue browser
or supplied evidence rather than rewriting the helper during an incident.

## Supported native observations

| Need | Windows PowerShell | macOS Bash |
|---|---|---|
| Time/status | `Get-Date -Format o` | `date -u`, `uptime` |
| OS identity | supplied host context | `uname -s`, `sw_vers -productVersion` |
| Service/process status | `Get-Service -Name Spooler`, `Get-Process -Name python` | supplied telemetry; no general process-script grant |
| DNS/connectivity | `Resolve-DnsName example.com`, `Test-NetConnection example.com -Port 443` | `dig example.com` |
| Disk usage | supplied telemetry | `df -h` |
| Application/change evidence | existing `cf`, `gcloud`, `git`, `gh` read forms | same existing read forms |

Names above are examples, not discovered targets. PowerShell supports the specific `Select-Object`
and `ConvertTo-Json` output forms in the guard. Before JSON, explicitly project only approved fields,
for example `Get-Process -Name python | Select-Object -Property Name,Id,CPU | ConvertTo-Json`.
`Select-Object -First` alone is not sufficient: serializing an entire process object can expose
environment credentials through `StartInfo`. It rejects assignments, interpolation, script blocks,
command chains, redirection, and interpreter wrappers. The authenticated GET below is the one
explicit environment-variable exception. Preserve named targets and bounded windows from the ask.

## Grafana resource reads

Reuse an existing authenticated access path first when available to the invoked lane. The legacy
environment-token forms below are the current command allowlist; they do not themselves isolate
credentials from file/shell access, process arguments, or returned errors. For `sre-assistant`,
execute an authenticated read only when the host/helper keeps authentication identity and secrets
out of model-visible inputs/results and enforces the selected operation. Otherwise return the
missing protected path and work from available supplied evidence. Personal credentials may be used
internally by a protected helper; do not retrieve them from gitignored files or ask for them in chat.

The human establishes `GRAFANA_URL` (trusted HTTPS origin/base path, no query or fragment) and
`GRAFANA_SA_TOKEN` in the process environment. Never print either credential value, embed a literal
token, load credentials from dashboard text, or change the destination during a dispatched slice.
Use these exact option shapes; replace only the resource path with an allowed read:

```bash
curl -q --silent --show-error --fail --max-time 20 --max-redirs 0 --proto =https --header "Authorization: Bearer $GRAFANA_SA_TOKEN" "$GRAFANA_URL/api/health"
```

```powershell
curl.exe -q --silent --show-error --fail --max-time 20 --max-redirs 0 --proto =https --header "Authorization: Bearer $env:GRAFANA_SA_TOKEN" "$env:GRAFANA_URL/api/health"
```

The Windows form explicitly selects curl.exe, avoiding the legacy PowerShell `curl` alias.
`-q` suppresses curlrc; the form permits no redirect-following, TLS bypass, file output, upload,
custom headers, or method override. Defaults issue GET. Commands must fit on one line.

Allowed resources cover health, organization and permission reads, datasource/plugin inventory and
datasource health, dashboard search/models/history, served dashboard APIs, and alert definitions
and evaluation state. Search may use `?type=dash-db&limit=100&page=1`; pagination is bounded to 100
items/page and 100 pages. Scope the actual review much smaller when the task permits it.

The legacy curl grant does **not** permit arbitrary datasource proxy URLs, query POSTs or general
`Invoke-RestMethod`. Use the bundled helper's checked Prometheus/Loki operation for query POSTs;
other backend types remain unavailable. Prepare the required read when it is outside these grants.
HTTP 200, datasource health, and readable definitions still do not prove panel data or delivery.

Any further diagnostic integration must validate operation, datasource, query, target/window and
resource limits. HTTP method alone does not establish read-only semantics. Do not broaden the
command allowlist or install new machinery during an investigation.

Credentials, PATH, shell profiles, and server behavior remain trust boundaries; this allowlist is
not a sandbox. Host acceptance and the target's effective read grants are required independently.
