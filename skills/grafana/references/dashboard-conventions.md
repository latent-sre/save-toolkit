# Team dashboard conventions

Read on every dashboard create, and when designing a dashboard for this team. These are the team's
naming, folder, time, and variable decisions; discover real names, uids, owners, and installed
plugins from the target, and never store credentials or sensitive queries here.

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
  Wavefront/WQL and Splunk/SPL panels use separate typed variables resolved to their discovered
  plugin sources; one variable cannot translate between query languages.

Before any create or edit, record in the task evidence: Grafana instance and edition, dashboard and
folder uids, owner, purpose/SLO, installed data-source names/types/uids, entitlement status, and any
linked alert/runbook. Unknown values remain `[unverified]`. `obs-alerting` owns alert intent and
threshold design; [alerting configuration](./grafana-alerting.md) owns Grafana routing/evaluation details.
