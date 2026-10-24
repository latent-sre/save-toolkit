# Dashboard design

For design-only work, use this reference directly: no instance access or change workflow is needed.
For an existing dashboard, change only the requested panels or presentation. Follow the owner's
requirements and existing conventions for new dashboards. Confirm provisioning
ownership before an edit; managed dashboards change through their source.

## Answer the reader's question

Name the audience, operational question, backend, and next decision. For order-request health,
show error ratio beside request volume and latency percentiles, compare the same population with
a known-normal window, and drill into the affected route's logs and traces. For scheduled position
sync, show age of last success against its schedule, latest outcome, and failing-stage logs.
Use `stack-profile` for backends and flag vendor-plugin requirements; use `obs-analysis` for query
semantics. Do not infer counter type from a `_total` suffix.

Distinguish no traffic, zero, missing telemetry, and query failure. Never fill an error ratio or
its numerator with zero (`or vector(0)` or null-to-zero). Check the denominator and telemetry
coverage when interpreting a ratio. Add a presence panel when it answers the reader's question.
For scrape-based presence, use
`count(up{job="<job>"} == 1) or on() vector(0)` mapped red at zero after confirming the target labels.
OTLP push has no `up` series: use the actual backend or
pipeline presence signal. Panel color or thresholds do not prove an alert exists or fires.

## New-dashboard conventions

Discover actual owners, folders, names, UIDs, and plugin sources; placeholders are not target facts.
No fixed naming, folder, tag, variable order, time window, or refresh policy is established here.
Use the target's conventions and requested workflow; keep published UIDs stable. Leave `timezone`
unset on new dashboards to inherit organization/viewer behavior unless the owner requests otherwise.

Choose variables and refresh cadence for the actual queries and data arrival. A datasource variable
only switches interchangeable sources of one type; Wavefront/WQL and Splunk/SPL need separate typed
references resolved to installed plugins. Match multi-value and All expansion to the query language;
`.+` is a regex pattern, not a universal All value.

For cross-region evidence, use an absolute UTC range or a link carrying the range. Alert intent
belongs to `obs-alerting`; [alerting configuration](./grafana-alerting.md) covers Grafana routing.

## Return the design

Give the audience/question, panel changes, signal/query requirements, units, comparison windows,
missing-data behavior, and limits. State which normal, degraded, or missing-data states were
actually inspected. A design or screenshot does not verify current health, queries, access, or a
save. Implementation uses [dashboard operations](./dashboard-operations.md).
