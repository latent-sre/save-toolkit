---
name: obs-dashboards
description: >-
  Design dashboards around the on-call reader's questions: service health, golden signals,
  useful panels, units, comparisons, missing-data presentation, and drill-downs. Triggers:
  'design a dashboard', 'what should we dashboard', 'which panels do we need',
  'make this dashboard easier to read'. Grafana reads, saves, JSON/API details, and alert
  operations belong to grafana; alert/SLO design belongs to obs-alerting. Not for dashboards
  built into an application UI (frontend-craft).
argument-hint: "[service, audience, dashboard question, or design change]"
---

# Dashboard design

A dashboard should answer a named reader's next operational question. For an existing dashboard,
start with the requested design change and preserve the rest; a panel addition does not require a
full dashboard redesign.

**Grafana implementation lives in `grafana`.** Load that skill when the request needs dashboard
search/interpretation, panel JSON, variables, datasource discovery, create/edit/export, folders,
permissions, validation tooling, version history, or rollback. It owns those procedures and their
bundled helper. This skill supplies design decisions and grants no live-write authority.

## Design for a decision

Name each panel's backend per `stack-profile` and flag panels needing a vendor plugin. Use
`obs-metrics`, `obs-logs`, or `obs-traces` for query semantics, and the team's folder, naming,
time, and variable conventions via `grafana`.

For example, "Are order requests failing?" starts with error ratio beside request volume and
request latency, compared with a known-normal window for the same population. Drill from the
affected route to its errors and traces. "Is position sync current?" instead starts with age of
last success against its schedule, then the latest run's outcome and failing-stage logs.

Distinguish no traffic, zero, missing telemetry, and query failure; a blank panel must not look
healthy, and color is not proof an alert exists or fires. Never append `or vector(0)` or map null
to zero on an error ratio or its numerator; put the request-rate (denominator) panel beside every
ratio. Add a telemetry-present stat whose zero is the alarm: on a Prometheus-scrape target use
`count(up{job="<job>"} == 1) or on() vector(0)` mapped red at 0 `[unverified against the team's
Mimir labels]`; on a push (OTLP) target there is no `up` series, so use the backend or pipeline
presence signal for that route instead of inventing one.

## Check and hand off

State which of the normal, degraded, and missing-data states were actually inspected; a design or
screenshot does not prove current health, query correctness, access, or a successful save. Return
the audience/question, panel changes, signal/query requirements, units, comparison windows,
missing-data behavior, and design limits.
