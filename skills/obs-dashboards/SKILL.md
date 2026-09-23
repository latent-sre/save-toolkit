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

1. Name the service or journey, reader, and decision: is it healthy, who is affected, what changed,
   or where should the responder investigate next? Use the few panels needed to answer it.
2. Put service health/SLOs first, golden signals next, then instance, route, and dependency
   drill-downs. Pair user-facing symptoms with supporting telemetry; a resource panel alone does
   not establish user impact.
3. Choose a representation that preserves the signal: latency percentiles or distributions,
   request/error rates with traffic context, and saturation against a meaningful capacity limit.
   Use `obs-metrics`, `obs-logs`, or `obs-traces` for query semantics and interpretation. Name the
   backend that holds each signal (per `stack-profile`: Wavefront for PCF application metrics today,
   Mimir/Loki/Tempo for OpenTelemetry-instrumented and GCP services) and flag any panel that needs
   the Wavefront or Splunk Grafana plugin.
4. Give each panel a question or clear signal name, correct units, understandable series labels,
   and relevant comparison window. Keep linked views on the same population and time range;
   disclose intentional differences rather than making unlike windows look comparable. Apply the
   team's folder, naming, time, and variable conventions: load `grafana` and read its dashboard
   conventions reference.
5. Distinguish no traffic, zero, missing telemetry, and query failure. A blank panel must not look
   healthy. Color or a threshold is a visual cue, not proof that an alert rule exists or fires.
   Never append `or vector(0)` or map null to zero on an error ratio or its numerator; put the
   request-rate (denominator) panel beside every ratio; add a telemetry-present stat such as
   `count(up{job="<job>"} == 1) or on() vector(0)` with 0 mapped to red "no telemetry" — here zero
   is the alarm, not the all-clear `[unverified against the team's Mimir labels; Wavefront needs its
   obs-metrics equivalent]`.
6. Link the next useful evidence, service context, and runbook without embedding sensitive data.
   Match refresh cadence to the decision and source cadence; avoid unnecessary query load.

## Check and hand off

Walk through the reader's question with representative normal, degraded, and missing-data states
when evidence is available. State which states were actually inspected; a design or screenshot does
not prove current health, query correctness, access, or a successful save.

Return the audience/question, proposed panel changes, signal/query requirements, units, comparison
windows, missing-data behavior, and design limits. For Grafana, continue through `grafana` with that
bounded design; do not duplicate its API or write procedure here. A supplied design needs no new
alert/SLO work unless requested; `obs-alerting` owns that decision.
