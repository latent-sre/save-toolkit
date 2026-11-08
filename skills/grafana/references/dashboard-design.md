# Dashboard design

Design-only work needs no instance access or change workflow. Preserve unrelated panels; managed
dashboards change through their owning source.

## Answer the reader's question

Use `stack-profile` for backends and plugin requirements, `obs-analysis` for query semantics.
Request-health ratios need traffic context and a matching comparison population/window; scheduled
work needs freshness against its schedule.

Distinguish no traffic, zero, missing telemetry, and query failure. Never fill an error ratio or
its numerator with zero (`or vector(0)` or null-to-zero). Check the denominator and telemetry
coverage when interpreting a ratio. Add a presence panel when it answers the reader's question.
For scrape-based presence, use
`count(up{job="<job>"} == 1) or on() vector(0)` mapped red at zero after confirming the target labels.
Native OTLP push has no `up` series; targets scraped by a Collector or Alloy Prometheus receiver and
forwarded over OTLP do carry it. Without `up`, use the actual backend or pipeline presence signal.

## New-dashboard conventions

Discover owners and resource identities; no fixed naming, folder, tag, variable order, time window
or refresh policy is established here. Follow target conventions and keep published UIDs stable.
On a new Classic/V1 dashboard leave `timezone` unset to inherit organization/viewer behavior; a V2
dashboard's `timeSettings.timezone` defaults to `"browser"`, so choose it with the owner.

A datasource variable switches only interchangeable sources of one type. Wavefront (WQL,
`grafana-wavefront-datasource`) and Splunk (SPL, `grafana-splunk-datasource`) need separate typed
references resolved to installed plugins; both are Enterprise plugins, and catalogue listing is not
entitlement, so confirm the edition, installed plugins (`GET /api/plugins`), and the administrator's
licence record before proposing either. Tanzu Observability (Wavefront) service has ended; its
backend continues as Broadcom DX OpenExplore. ThousandEyes documents an OpenTelemetry integration
with Grafana Cloud; discover the installed plugins and actual telemetry route before querying, and
never invent a plugin type or uid.

Alert intent belongs to `obs-alerting`; [alerting configuration](./grafana-alerting.md) covers
Grafana routing.

## Return the design

Return the question, panel/query changes, units, comparison and missing-data behavior; name which
normal/degraded/missing states were inspected. Design does not verify queries, health, access or
save success. Implementation uses the [HTTP API change loop](./http-api.md#dashboard-change-loop).
