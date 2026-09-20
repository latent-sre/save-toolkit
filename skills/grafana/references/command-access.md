# Grafana command access — Windows and macOS

Use when the SRE agent has terminal tools and no Grafana MCP. This reference grants no write
authority. The host must load the matching command guard; a skill cannot install or enforce it.

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
and `ConvertTo-Json` output forms in the guard. It rejects assignments, interpolation, script blocks,
command chains, redirection, and interpreter wrappers. The authenticated GET below is the one
explicit environment-variable exception. Preserve named targets and bounded windows from the ask.

## Grafana resource reads

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

This initial command grant does **not** permit arbitrary datasource proxy URLs, `POST /api/ds/query`,
or general `Invoke-RestMethod`. Those can reach backend-specific behavior and need a separate
query contract. Prepare the exact query for the human when the required read is outside this set.
HTTP 200, datasource health, and readable definitions still do not prove panel data or delivery.

Credentials, PATH, shell profiles, and server behavior remain trust boundaries; this allowlist is
not a sandbox. Host acceptance and the target's effective read grants are required independently.
