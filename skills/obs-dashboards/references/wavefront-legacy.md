# Existing Wavefront and Splunk operations dashboards

Fill this inventory with names, UIDs, owners, and repository links only—never credentials, API tokens, or
unredacted sensitive queries. Replace every placeholder or explicitly record `none`; do not leave an
ambiguous partial inventory.

## Licence and plugin evidence

Catalogue guidance, not proof of entitlement — confirm the licence and the installed plugin list
(`GET /api/plugins`) with the Grafana administrator before provisioning either.

- **Wavefront** — `grafana-wavefront-datasource` is an **Enterprise** plugin (Cloud Pro/Advanced, or
  a self-managed Enterprise licence). Its backend continues as **Broadcom DX OpenExplore**; the
  2025-10-31 end-of-availability retired the VMware Tanzu Observability offering, not the engine
  (see `stack-profile`). Whether the plugin is supported against a DX OpenExplore tenant is
  `[unverified]`.
- **Splunk** — `grafana-splunk-datasource`, same entitlement rule. Cloud Free and Starter exclude it.
- **ThousandEyes** — no Grafana data-source plugin exists; do not invent a plugin type or uid. Its
  OpenTelemetry signals land in Prometheus/Mimir, Tempo, or Loki and are queried there.

`[sourced, reviewed 2026-07-14; lifecycle re-checked 2026-08-19]`

## Data sources

| Installed name | Signal/query language | Grafana plugin ID | Data-source UID | Owner / entitlement evidence |
|---|---|---|---|---|
| `<Wavefront / Aria Operations for Applications>` | Wavefront/WQL | `grafana-wavefront-datasource` | `<uid>` | `<owner / licence record>` |
| `<Splunk>` | Splunk/SPL | `grafana-splunk-datasource` | `<uid>` | `<owner / licence record>` |

## Dashboard inventory

| Dashboard | Stable UID | Folder | Owner | Purpose / SLO |
|---|---|---|---|---|
| `<service health>` | `<uid>` | `<folder>` | `<team>` | `<top-level health → drill-down>` |

## Conventions we standardize on

One team owns every dashboard here; the dashboards are per application `[sourced: owner, 2026-08-21]`.
The agent applies these on every create or edit; a value marked `[unverified]` is a default the owner
has not yet confirmed — confirm it rather than inventing an alternative.

- **Folders.** One Grafana folder for the team, one subfolder per app: `<Team>/<app>`. The repository
    no dashboard lands in `General`.
- **Names and uids.** `<App> / Health` is the top-level dashboard; drill-downs are
  `<App> / <Topic>` (`<App> / Dependencies`, `<App> / Routes`). The uid is the lowercase hyphenated
  form, `<app>-health`, `<app>-<topic>`, minted in the repository and never changed after first publish.
- **Tags.** `<team>` and `<app>` on every dashboard; `env` is a variable, not a tag. Experiments carry
  the `TEST:` name prefix plus the author's initials as a tag and are deleted when done; tags are
  never copied when a dashboard is duplicated.
- **Time.** Default window `now-6h` to `now`; auto-refresh `1m` on health dashboards, off on anything
  with a range over a day. **Timezone is deliberately not pinned** `[sourced: owner, 2026-08-22]` —
  leave `timezone` unset so each dashboard inherits the org default and each viewer sees their own
  local time. The trade-off to know rather than re-litigate: two people comparing the same spike from
  different regions are reading different clocks, so quote an absolute UTC time (or paste the URL,
  which carries the range) when handing evidence to someone else.
- **Variables, in this order:** `datasource` (type data source, the only way a panel names its
  backend), `env`, `app` (constant on per-app dashboards), `instance`, `route`; all multi-value
  selectors use `allValue: ".+"` and `${var:regex}`.
- **Data sources.** Panels never name a data source directly — they reference `${datasource}`, and
  the variable's default carries the environment. Fill this in per instance from
  `GET /api/datasources` on that instance; do not copy a uid between environments, and do not assume
  a source's *name* tells you which backend it points at.

  | Environment | Grafana URL | Metrics source name / uid | Logs source name / uid |
  |---|---|---|---|
  | Production | `<url>` | `<name>` / `<uid>` | `<name>` / `<uid>` |
  | Non-production | `<url>` | `<name>` / `<uid>` | `<name>` / `<uid>` |

  All four uids are `[unverified]` — read them from the target rather than from this table until
  someone fills it in. Wavefront- and Splunk-backed panels name their own data source and are not
  switched by this variable; whether those Enterprise plugins are licensed on a given instance is a
  per-instance check (`GET /api/plugins`), not something this file can assert.

## Alert inventory

This table inventories links from legacy dashboards; alert-rule design, thresholds, and notification
routing are owned by alerting work and must be reviewed there.

| Rule / purpose | Dashboard or panel link | Evaluation owner | Contact route | Runbook URL |
|---|---|---|---|---|
| `<burn-rate / availability>` | `<uid or URL>#<panel>` | `<Grafana or backend>` | `<route>` | `<runbook URL>` |


<!-- terminal-canary: q_odwf_6a2e -->
