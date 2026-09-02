# Legacy data-source and dashboard conventions

Read this for Wavefront/Splunk-backed dashboards or this team's naming, folder, time, and variable
decisions. It is not an inventory of a Grafana instance: discover names, uids, owners, and installed
plugins from the target, and never store credentials or sensitive queries here.

## Licence and lifecycle facts

Catalogue guidance is not entitlement evidence. Confirm edition, the installed plugin list
(`GET /api/plugins`), and the administrator's licence record before proposing either plugin.

- Wavefront uses WQL through `grafana-wavefront-datasource`, an Enterprise plugin. Its backend
  continues as Broadcom DX OpenExplore; support against the team's tenant is `[unverified]`.
  Wavefront is the live metrics UI for this team's PCF applications today; "legacy" here means the
  data-source plugin and licence lineage, not the team's usage. *[sourced: operator statement
  2026-09-02]*
- Splunk uses SPL through `grafana-splunk-datasource` and has the same Enterprise-entitlement check.
- ThousandEyes has no Grafana data-source plugin. Its OpenTelemetry signals land in an installed
  Prometheus/Mimir, Tempo, or Loki backend and are queried there; never invent a plugin type or uid.

*[sourced: Grafana plugin catalogue and Broadcom lifecycle material, reviewed 2026-07-14 and
re-checked 2026-08-19]*

## Team decisions

One team owns these per-application dashboards. Confirm the actual owner on the target rather than
inventing one. `[sourced: owner, 2026-08-21]`

- **Folders:** `<Team>/<app>`; nothing lands in General.
- **Names and identity:** `<App> / Health` for the top level and `<App> / <Topic>` for drill-downs.
  Stable uids use `<app>-health` or `<app>-<topic>` and never change after publication.
- **Tags:** team and app on every dashboard; environment is a variable, not a tag. Experiments use a
  `TEST:` prefix plus an owner tag and are removed when finished. Never copy tags while duplicating.
- **Time:** default `now-6h` to `now`; `1m` refresh on health dashboards and no automatic refresh for
  ranges over a day. Leave `timezone` unset so Grafana inherits the organization/viewer behavior.
  When sharing evidence across regions, give an absolute UTC time or a URL carrying the range.
  `[sourced: owner, 2026-08-22]`
- **Variables:** `datasource`, `env`, `app`, `instance`, `route` in that order. Multi-value selectors
  use `allValue: ".+"` and `${var:regex}`.
- **Data sources:** use `${datasource}` for panels backed by interchangeable sources of one type.
  Wavefront/WQL and Splunk/SPL panels name their own discovered plugin source; a single variable
  cannot translate between query languages.

Before any create or edit, record in the task evidence: Grafana instance and edition, dashboard and
folder uids, owner, purpose/SLO, installed data-source names/types/uids, entitlement status, and any
linked alert/runbook. Unknown values remain `[unverified]`. Alert thresholds, notification routing,
and evaluation ownership belong to `obs-alerting`.

<!-- terminal-canary: q_odwf_6a2e -->
