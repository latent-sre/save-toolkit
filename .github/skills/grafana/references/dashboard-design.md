# Dashboard design

Design-only work needs no instance access or change workflow. Preserve unrelated panels; managed
dashboards change through their owning source.

## Answer the reader's question

Use `stack-profile` for backends and plugin requirements, `obs-analysis` for query semantics.
Request-health ratios need traffic context and a matching comparison population/window; scheduled
work needs freshness against its schedule. Neither a `_total` suffix nor panel color establishes
metric type or alert behavior.

Distinguish no traffic, zero, missing telemetry, and query failure. Never fill an error ratio or
its numerator with zero (`or vector(0)` or null-to-zero). Check the denominator and telemetry
coverage when interpreting a ratio. Add a presence panel when it answers the reader's question.
For scrape-based presence, use
`count(up{job="<job>"} == 1) or on() vector(0)` mapped red at zero after confirming the target labels.
OTLP push has no `up` series: use the actual backend or
pipeline presence signal.

## New-dashboard conventions

Discover owners and resource identities; no fixed naming, folder, tag, variable order, time window
or refresh policy is established here. Follow target conventions and keep published UIDs stable. Leave `timezone`
unset on new dashboards to inherit organization/viewer behavior unless the owner requests otherwise.

Match refresh to data arrival. A datasource variable switches only interchangeable sources of one
type; Wavefront/WQL and Splunk/SPL need separate typed
references resolved to installed plugins. Match multi-value and All expansion to the query language;
`.+` is a regex pattern, not a universal All value.

For cross-region evidence, use an absolute UTC range or a link carrying the range. Alert intent
belongs to `obs-alerting`; [alerting configuration](./grafana-alerting.md) covers Grafana routing.

## Return the design

Return the question, panel/query changes, units, comparison and missing-data behavior; name which
normal/degraded/missing states were inspected. Design does not verify queries, health, access or
save success. Implementation uses [dashboard operations](./dashboard-operations.md).
