# Grafana command access — Windows and macOS

For `sre-assistant` with terminal tools, use only the installed read helper for Grafana commands.
If it cannot perform the requested read, ask the caller for a sanitized excerpt from the intended
instance and organization. Record the source and coverage of that evidence.

## Selected gcx migration

The owner selected `gcx` for read-only Grafana investigation access, but the existing guard does not
admit `gcx` yet (protected execution, redirect/destination enforcement, and installed-client
acceptance remain pending). Keep using the bundled read helper below until fixed CLI commands and
their execution boundary are verified and granted. Do not install `gcx`, change contexts, expose
credentials, enable HTTP payload logging, or install vendor skills as an incident workaround.

## Bundled read helper

Run the stdlib-only [grafana_read.py](../scripts/grafana_read.py) as `python -I -S` (or `python3`,
`python.exe`) with its **absolute installed path**, or call its installed
[PowerShell wrapper](../scripts/grafana_read.ps1). Use drive-letter paths on Windows and the generated
`.github` copy in Copilot command preview. The SRE
guard denies Git Bash `/c/...` paths, `py`, double-quoted arguments (single-quote literals instead),
`--flag=value`, pipes, redirection (including `2>&1`), `timeout`, and custom URL/method/credential
flags. If Python 3.14+ or the helper is missing, report the gap; never install tools or switch
shells to bypass a denial.

Credentials load from `GRAFANA_URL`, `GRAFANA_ORG_ID`, and a token (or Basic credentials) in the
environment, or from `~/.config/save-toolkit/grafana.env` when no `GRAFANA_*` env var is set.
Never read, print, or edit that file, set those variables, or ask for credentials. Every request
sends `X-Grafana-Org-Id`, verifies `/api/org` first (failing closed on mismatch), disables
redirects/proxies/TLS bypass, and masks configured credentials in its own JSON output.

```text
python -I -S "<absolute-installed-path>/grafana_read.py" dashboard --uid dashboard-uid
python -I -S "<absolute-installed-path>/grafana_read.py" query --datasource logs-uid --kind loki --from 1758400000000 --to 1758403600000 --expr '{service="example"} |= "error"'
python -I -S "<absolute-installed-path>/grafana_read.py" search --query 'checkout latency'
python -I -S "<absolute-installed-path>/grafana_read.py" render --uid dashboard-uid --panel 5 --from 1758400000000 --to 1758403600000 --var host=example
```

On **Windows PowerShell 5.1/7**, raw `--expr` is denied; use the wrapper or `--expr-base64`:

```powershell
& '<absolute-installed-path>/grafana_read.ps1' -Datasource logs-uid -Kind loki -From 1758400000000 -To 1758403600000 -Expr '{service="example"} |= "error"'
& '<absolute-installed-path>/grafana_read.ps1' -Datasource metrics-uid -Kind prometheus -From 1758400000000 -To 1758403600000 -Expr 'up' -Mode instant -Output summary
```

| Operation | Reads | Limits |
|---|---|---|
| `dashboard --uid [--panel]` | Stored model (Classic or native V2 with Classic `panel_view`), or one panel (`coverage: configuration_only`) | 2 MiB; up to 3 GETs |
| `query --datasource --kind --from --to --expr [--mode range\|instant] [--output full\|summary]` | Prometheus or Loki `/api/ds/query` POST after verifying datasource UID and type | 24 h window; 1,000 points / 500 Loki lines; 2 MiB, 20 s |
| `search [--query] [--page] [--folder-uid] [--tag]` | Dashboards by title and/or folder (requires `--query` or `--folder-uid`) | 100/page, pages 1–100 |
| `alerts [--folder-uid] [--group-next-token]` | Grafana-managed rule groups with evaluation state and health | 100 groups, 20 instances/rule |
| `alerts --uid` | One Grafana-managed rule definition with provenance and pause state (cannot combine with `--folder-uid`) | 2 MiB |
| `annotations --from --to [--dashboard-uid]` | Annotations in window | 24 h, 100 items |
| `silences [--id]` | Built-in Grafana Alertmanager silences, or one exact UUID | 2 MiB |
| `render --uid --panel --from --to [--var k=v] [--width] [--height]` | Panel PNG saved to `~/.cache/save-toolkit/grafana-renders/` (`coverage: image_uninspected`) | 400–2400 × 200–1600 (default 1200×600); 7 d, 5 `--var`, 8 MiB, 45 s |

Reading results:
- Exit 0 means the read succeeded, not that the investigation is complete; exit 2 returns a static error code. Query errors under HTTP 200 count as failures.
- Keep `coverage`, `truncated`, and `limits` with the evidence. `permission_scoped` means absent results reflect this identity's visibility, not proof of absence.
- Pair `alerts --uid` (config only) with `alerts --folder-uid` (evaluation state). `silences` inspects only the built-in Grafana Alertmanager. Open rendered PNGs before describing them.

### Copilot command-preview queries

In Copilot command preview the shell is unknown, so raw `--expr` is denied on every shell. Use
`--expr-base64` with a double-quoted installed path and unquoted literal arguments (no single
quotes, spaces, or shell operators). The PowerShell wrapper is denied here. Example (`dXA=` = `up`):

```text
python -I -S "<absolute-installed-path>/grafana_read.py" query --datasource metrics-uid --kind prometheus --from 1758400000000 --to 1758403600000 --expr-base64 dXA=
```

## Query modes, macros, and summaries

`--mode range` and `--output full` are defaults; `--mode instant` evaluates at `--to` (both
timestamps remain required for range macros). `--output summary` omits raw `results`, reporting
min/max/last/null counts (numeric) or counts/timestamps (logs) capped at 100 series; keep empty,
all-null, zero, and unsupported distinct. Only these built-in macros are accepted (including
`${__name}`):

| Macro | Prometheus | Loki |
|---|---|---|
| `$__range`, `$__range_s`, `$__range_ms` | Backend-expanded from window | Substituted from `--to` minus `--from` |
| `$__interval`, `$__interval_ms` | `--interval-ms` if given, else backend-expanded | Requires `--interval-ms` |
| `$__rate_interval`, `$__rate_interval_ms` | `--rate-interval-ms` if given, else backend-expanded | Rejected |

Backend-expanded macros report `panel_equivalence: not_established`; pass `--interval-ms` /
`--rate-interval-ms` when panel equivalence matters. Dashboard variables and other `$__` macros fail
before authentication.
