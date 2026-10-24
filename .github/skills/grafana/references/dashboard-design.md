# Dashboard design and team conventions

For design-only work, use this reference directly: no instance access or change workflow is needed.
For an existing dashboard, change only the requested panels or presentation. Apply the conventions
below to new dashboards; older differences are not automatically defects. Confirm provisioning
ownership before an edit; managed dashboards change through their source.

## Answer the reader's question

Name the audience, operational question, backend, and next decision. For order-request health,
show error ratio beside request volume and latency percentiles, compare the same population with
a known-normal window, and drill into the affected route's logs and traces. For scheduled position
sync, show age of last success against its schedule, latest outcome, and failing-stage logs.
Use `stack-profile` for backends and flag vendor-plugin requirements; use `obs-metrics`, `obs-logs`,
or `obs-traces` for query semantics. Do not infer counter type from a `_total` suffix.

Distinguish no traffic, zero, missing telemetry, and query failure. Never fill an error ratio or
its numerator with zero (`or vector(0)` or null-to-zero); put request rate beside every ratio.
Add a telemetry-present stat whose zero is the alarm. For scrape-based presence, use
`count(up{job="<job>"} == 1) or on() vector(0)` mapped red at zero after confirming the target labels.
OTLP push has no `up` series: use the actual backend or
pipeline presence signal. Panel color or thresholds do not prove an alert exists or fires.

## New-dashboard conventions

Discover actual owners, names, UIDs, and plugin sources; placeholders are not target facts.

| Choice | Team convention |
|---|---|
| Folder | `<Team>/<app>`, never General |
| Name and UID | `<App> / Health` or `<App> / <Topic>`; stable `<app>-health` or `<app>-<topic>` UID, unchanged after publication |
| Tags | Team and app; environment is a variable. Experiments use `TEST:` and an owner tag, with cleanup through the authorized owner. Do not copy tags when duplicating |
| Time | `now-6h` to `now`; health refresh `1m`, no automatic refresh over a day; leave `timezone` unset to inherit organization/viewer behavior |
| Editing | `editable: true` for the team's UI workflow |
| Variables | `datasource`, `env`, `app`, `instance`, `route` in that order; multi-value uses `allValue: ".+"` and `${var:regex}` |
| Sources | `${datasource}` only for interchangeable sources of one type; Wavefront/WQL and Splunk/SPL need separate typed variables resolved to their plugins |

For cross-region evidence, use an absolute UTC range or a link carrying the range. Alert intent
belongs to `obs-alerting`; [alerting configuration](./grafana-alerting.md) covers Grafana routing.

## Return the design

Give the audience/question, panel changes, signal/query requirements, units, comparison windows,
missing-data behavior, and limits. State which normal, degraded, or missing-data states were
actually inspected. A design or screenshot does not verify current health, queries, access, or a
save. Implementation uses [dashboard operations](./dashboard-operations.md).
