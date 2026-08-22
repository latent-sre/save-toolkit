# Existing Wavefront and Splunk operations dashboards

Fill this inventory with names, UIDs, owners, and repository links only—never credentials, API tokens, or
unredacted sensitive queries. Replace every placeholder or explicitly record `none`; do not leave an
ambiguous partial inventory.

## Data sources

| Installed name | Signal/query language | Grafana plugin ID | Data-source UID | Owner / entitlement evidence |
|---|---|---|---|---|
| `<Wavefront / Aria Operations for Applications>` | Wavefront/WQL | `grafana-wavefront-datasource` | `<uid>` | `<owner / licence record>` |
| `<Splunk>` | Splunk/SPL | `grafana-splunk-datasource` | `<uid>` | `<owner / licence record>` |

## Dashboard inventory

| Dashboard | Stable UID | Folder | Source path | Owner | Purpose / SLO |
|---|---|---|---|---|---|
| `<service health>` | `<uid>` | `<folder>` | `<repo path>` | `<team>` | `<top-level health → drill-down>` |

## Conventions we standardize on

One team owns every dashboard here; the dashboards are per application `[sourced: owner, 2026-08-21]`.
The agent applies these on every create or edit; a value marked `[unverified]` is a default the owner
has not yet confirmed — confirm it rather than inventing an alternative.

- **Folders.** One Grafana folder for the team, one subfolder per app: `<Team>/<app>`. The repository
  mirrors it (`dashboards/<app>/<uid>.json`) so `foldersFromFilesStructure: true` reproduces the tree;
  no dashboard lands in `General`.
- **Names and uids.** `<App> / Health` is the top-level dashboard; drill-downs are
  `<App> / <Topic>` (`<App> / Dependencies`, `<App> / Routes`). The uid is the lowercase hyphenated
  form, `<app>-health`, `<app>-<topic>`, minted in the repository and never changed after first publish.
- **Tags.** `<team>` and `<app>` on every dashboard; `env` is a variable, not a tag. Experiments carry
  the `TEST:` name prefix plus the author's initials as a tag and are deleted when done; tags are
  never copied when a dashboard is duplicated.
- **Time.** Default window `now-6h` to `now`; timezone `utc` `[unverified — confirm the on-call
  team's convention]`; auto-refresh `1m` on health dashboards, off on anything with a range over a day.
- **Variables, in this order:** `datasource` (type data source, the only way a panel names its
  backend), `env`, `app` (constant on per-app dashboards), `instance`, `route`; all multi-value
  selectors use `allValue: ".+"` and `${var:regex}`.
- **Default `${datasource}` value:** production metrics `<prod Mimir/Prometheus uid>` `[unverified —
  read it from `GET /api/datasources` on the production instance]`. On QA
  (`qa-grafana.agenticsre.dev`, 13.1.4 Enterprise) the two installed sources are
  **`[verified 2026-08-21]`**:

  | Name in Grafana | Type | UID | Backend URL |
  |---|---|---|---|
  | `prometheus-production-read-only` | `prometheus` | `dfr5gp9z5pzb4a` | `https://qa-prometheus.agenticsre.dev` |
  | `loki-production-read-only` | `loki` | `efr5j53fgnta8e` | `https://qa-loki.agenticsre.dev` |

  **Naming hazard, flagged not fixed:** both QA sources are *named* `…-production-read-only` while
  pointing at QA backends. A dashboard whose panels select a data source by name reads as
  production-backed on either instance; only the uid distinguishes them. This is one more reason
  every panel references `${datasource}` and the repository never hard-codes a uid — and a reason to
  rename these before anyone builds the habit.

  No Wavefront or Splunk data-source plugin is installed on QA **`[verified 2026-08-21:
  `GET /api/plugins` lists alertmanager, cloudwatch, azure-monitor, postgres, pyroscope, testdata,
  graphite, influxdb, jaeger, loki, mssql, mysql, opentsdb, parca, prometheus, stackdriver, tempo —
  and neither wavefront nor splunk]`**, so WQL/SPL panels cannot be exercised there; the licence
  facts in the skill body still govern the production instance.

## Alert inventory

This table inventories links from legacy dashboards; alert-rule design, thresholds, and notification
routing are owned by alerting work and must be reviewed there.

| Rule / purpose | Dashboard or panel link | Evaluation owner | Contact route | Runbook URL |
|---|---|---|---|---|
| `<burn-rate / availability>` | `<uid or URL>#<panel>` | `<Grafana or backend>` | `<route>` | `<runbook URL>` |

## Provisioning

| Item | Reviewed value |
|---|---|
| Dashboard-as-code root | `<repo path>` |
| Provider / Git Sync path | `<provider YAML or Git Sync path>` |
| Controlled apply path | `<CI job or operator procedure>` |
| Validation target | `<non-production Grafana URL/name>` |
| Rollback revision/procedure | `<revision and controlled reapply step>` |

<!-- terminal-canary: q_odwf_6a2e -->
