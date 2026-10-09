# Team dashboard conventions

Read when creating or designing a dashboard for this team. These are the team's target naming,
folder, time, and variable decisions for new dashboards; discover real names, uids, owners, and
installed plugins from the target. Existing dashboards may predate these conventions or be
provisioned from files: check how a dashboard is managed before treating its differences as
defects, and change a provisioned dashboard through its source, not the API.

One team owns these per-application dashboards. Confirm the actual owner on the target rather than
inventing one.

- **Folders:** `<Team>/<app>`; nothing lands in General.
- **Names and identity:** `<App> / Health` for the top level and `<App> / <Topic>` for drill-downs.
  Stable uids use `<app>-health` or `<app>-<topic>` and never change after publication.
- **Tags:** team and app on every dashboard; environment is a variable, not a tag. Experiments use a
  `TEST:` prefix plus an owner tag and are removed when finished. Never copy tags while duplicating.
- **Time:** default `now-6h` to `now`; `1m` refresh on health dashboards and no automatic refresh for
  ranges over a day. Leave `timezone` unset so Grafana inherits the organization/viewer behavior.
  When sharing evidence across regions, give an absolute UTC time or a URL carrying the range.
- **Editing:** leave `editable` true; `false` blocks this team's UI workflow.
- **Variables:** `datasource`, `env`, `app`, `instance`, `route` in that order. Multi-value selectors
  use `allValue: ".+"` and `${var:regex}`.
- **Data sources:** use `${datasource}` for panels backed by interchangeable sources of one type.
  Wavefront/WQL and Splunk/SPL panels use separate typed variables resolved to their discovered
  plugin sources; one variable cannot translate between query languages.

`obs-alerting` owns alert intent and threshold design;
[alerting configuration](./grafana-alerting.md) owns Grafana routing/evaluation details.
