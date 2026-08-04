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

- Variables: `<app>`, `<env>`, `<instance>`, `<route>`; record any bounded local additions.
- Timezone and default window: `<timezone>` / `<last 1–6h>`.
- Service identity labels and naming: `<documented convention>`.
- SLO-linked thresholds and units: `<source of truth>`.
- Cross-links that preserve time range and variables: `<dashboard/runbook/log links>`.

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
