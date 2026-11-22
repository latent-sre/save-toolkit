# Grafana command access — Windows and macOS

For `sre-assistant` with terminal tools, use only the installed read helper; if it cannot perform the
read, ask the caller for a sanitized excerpt from the target instance/org and record coverage.

## `gcx` and bundled read helper rules

The guard denies `gcx` and arbitrary shells — run stdlib-only [grafana_read.py](../scripts/grafana_read.py)
as `python -I -S` (or `python3`, `python.exe`) with its **absolute installed path** (drive letter on
Windows; `.github` copy in Copilot preview), or the [PowerShell wrapper](../scripts/grafana_read.ps1).
Guard denies `/c/...` paths, `py`, double-quoted args (use single quotes), `--flag=value`, pipes,
redirection, `timeout`, installs, and context/HTTP-log changes.

Auth loads from `GRAFANA_URL`, `GRAFANA_ORG_ID`, and token/Basic env vars or
`~/.config/save-toolkit/grafana.env` (never read/print/edit or ask for creds). Every request sends
`X-Grafana-Org-Id`, checks `/api/org`, blocks redirects/proxies/TLS bypass, and masks configured creds.

```text
python -I -S "<absolute-installed-path>/grafana_read.py" dashboard --uid dashboard-uid
python -I -S "<absolute-installed-path>/grafana_read.py" query --datasource logs-uid --kind loki --from 1758400000000 --to 1758403600000 --expr '{service="example"} |= "error"'
python -I -S "<absolute-installed-path>/grafana_read.py" search --query 'checkout latency'
python -I -S "<absolute-installed-path>/grafana_read.py" render --uid dashboard-uid --panel 5 --from 1758400000000 --to 1758403600000 --var host=example
```

On **Windows PowerShell 5.1/7**, raw `--expr` is denied — use the wrapper or `--expr-base64`:

```powershell
& '<absolute-installed-path>/grafana_read.ps1' -Datasource logs-uid -Kind loki -From 1758400000000 -To 1758403600000 -Expr '{service="example"} |= "error"'
& '<absolute-installed-path>/grafana_read.ps1' -Datasource metrics-uid -Kind prometheus -From 1758400000000 -To 1758403600000 -Expr 'up' -Mode instant -Output summary
```

| Command | Behavior & Limits |
|---|---|
| `dashboard --uid [--panel]` | Stored model (Classic/V2 `panel_view`), `coverage: configuration_only`; 2 MiB, <=3 GETs |
| `query --datasource --kind --from --to --expr [--mode range\|instant] [--output full\|summary]` | Prom/Loki `/api/ds/query` after UID/type check; 24 h, 1k pts / 500 log lines, 2 MiB, 20 s |
| `search [--query] [--page] [--folder-uid] [--tag]` | Search dashboards (`--query` or `--folder-uid` required); 100/page, pages 1–100 |
| `alerts [--folder-uid] [--group-next-token]` / `alerts --uid` | Rule groups+state (100 groups, 20/rule) OR single def+provenance (exclusive, 2 MiB) |
| `annotations --from --to [--dashboard-uid]` / `silences [--id]` | Annotations (24 h, 100) / built-in Alertmanager silences (2 MiB) |
| `render --uid --panel --from --to [--var k=v] [--width] [--height]` | PNG to `~/.cache/save-toolkit/grafana-renders/` (`image_uninspected`); 400–2400x200–1600 (1200x600), 7 d, 5 vars, 8 MiB, 45 s |

Keep `coverage`, `truncated`, and `limits`: exit `0` is transport success (check HTTP-200 query
errors; `permission_scoped` is not proof of absence).

### Copilot command-preview queries

In Copilot preview the shell is unknown: use `--expr-base64` with double-quoted helper path and
unquoted literal args (no PowerShell wrapper or single quotes). Example (`dXA=` = `up`):

```text
python -I -S "<absolute-installed-path>/grafana_read.py" query --datasource metrics-uid --kind prometheus --from 1758400000000 --to 1758403600000 --expr-base64 dXA=
```

## Query modes, macros, and summaries

Defaults: `--mode range`, `--output full` (`--mode instant` evaluates at `--to`; `--output summary`
caps at 100 series and separates empty, null, zero, unsupported). Accepted macros (+ `${__name}`):
`$__range*` (Prom backend / Loki `--to - --from`), `$__interval*` (Loki needs `--interval-ms`),
`$__rate_interval*` (Prom only). Unpinned macros report `panel_equivalence: not_established`.
