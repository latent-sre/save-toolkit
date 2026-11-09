---
name: obs-pipeline
description: >-
  What ships telemetry where — instrument a service with OTel and route metrics, traces, and
  structured logs through Alloy/collectors to Loki, Mimir, and Tempo. Triggers:
  'instrument this service', 'add telemetry', 'logs are not reaching Loki',
  'configure the Alloy exporter'. Not for reading signals (obs-analysis)
  or Grafana datasource/dashboard configuration (grafana).
argument-hint: "[service, missing signal, or telemetry route]"
---

# Ship telemetry end to end

If a bounded backend query finds the signal but a panel does not, carry that evidence to `grafana`
for datasource, variable, query-window, and presentation checks before changing the pipeline.

Treat the pipeline as one path with four independently failing boundaries:

```text
app → SDK/agent → collector/Alloy → backend
```

An SDK that exports OTLP straight to Loki, Mimir, or Tempo has no collector boundary; check the
other three.

| Signal | App emission | Transport and processing | Backend |
|---|---|---|---|
| Structured logs | approved JSON fields plus trace/span correlation | OTLP or file receiver → redact/filter/batch → route | Loki |
| Metrics | OTel instruments with bounded attributes | OTLP receiver → resource/attribute processing → route | Mimir |
| Traces | spans with propagated W3C trace context | OTLP receiver → sampling/batch → route | Tempo |

Identify the affected Splunk or Wavefront/PCF App Metrics feed and its owner before changing it.
Confirmed PCF-platform-owned feeds stay with that owner: hand their gaps to it rather than wiring
replacement exporters, and use `pcf-ops` and `obs-analysis` for platform-side and query evidence.
The backend name alone does not establish the ingestion route.

For Google Cloud ingest (OTLP to the Telemetry API), use [Alloy pipeline](./references/alloy.md).

## Where a missing signal gets lost

1. **The app never emits it.** Exercise one known request locally and inspect SDK diagnostics
   or a local console exporter for the expected log, metric, or span before checking the network.
2. **The SDK/agent never exports it.** Confirm the process has the intended endpoint,
   protocol, resource attributes, and credentials, then inspect its export error/drop counters;
   `otel.sdk.*` self-metrics are still Development, so where they are absent use SDK diagnostic logs.
3. **The collector/Alloy never accepts or keeps it.** Check receiver health, receiver accepted and
   refused counts, and processor `incoming_items`/`outgoing_items` for that signal; validate the
   deployed config before edits.
4. **The exporter/backend rejects, delays, or misroutes it.** Check exporter sent, send-failed, and
   enqueue-failed counts, then issue one time-bounded backend query using the canary's exact service
   and trace IDs.

A healthy later component does not prove an earlier boundary, and a backend query with no bounded
canary does not identify loss.

Read only the reference needed for the task:

| Need | Reference |
|---|---|
| Instrumentation, RED/USE, propagation, sampling, correlation, or completion criteria | [OTel SDK method](./references/otel-sdk.md) |
| Alloy receivers, processors, exporters, routing, pipeline health, or end-to-end canary | [Alloy pipeline](./references/alloy.md) |

**Cardinality:** bounded dimensions become metric labels/tags; unbounded identity (user/request/trace
IDs, full URLs, emails, raw SQL) goes to traces and logs, **never** metric labels, because each value
creates a new time series.

## OTel naming — dotted namespaces and instrument metadata
- **The OTel name is the source of truth:** namespaces delimited by **dots**, `snake_case` only *within*
  a multi-word component. **Units live in instrument metadata (UCUM), not the name** (upstream allows a
  unit in the name only to resolve ambiguity). Base units (seconds, bytes); dimensions in
  attributes, not the name. Pluralization follows the unit: a name whose value carries a real unit,
  or the dimensionless unit `1` (`system.cpu.utilization`), stays singular; a count of discrete
  things with an annotation unit such as `{fault}` is pluralized (`system.paging.faults`,
  `system.network.packets`); UpDownCounter names are never pluralized.
- Wavefront takes dot-delimited names + point tags
  (`app.http.request.duration`) — the OTel shape, near-unchanged. Resource attributes become point
  tags only when the proxy sets `otlpResourceAttrsOnMetricsIncluded=true`, and a metric over the
  point-tag limit is dropped. Keep the bounded-tag discipline; this section owns the emitted
  naming/tag contract.
- A Prometheus-style exporter translates dotted names for you by default; do not pre-bake exporter
  suffixes into the OTel name. The stored name depends on the route: Mimir's OTLP endpoint adds no
  unit or type suffixes by default (`distributor.otel-metric-suffixes-enabled = false`), while the
  Alloy/Collector Prometheus exporters and Prometheus's OTLP receiver add them, and UTF-8
  translation strategies keep the dots. Check the stored name in the backend before querying.

## Build the evidence packet

Return per boundary checked: target, UTC window, exact check/result, canary service ID (trace ID for
traces), config revision and claim confidence. Name missing proof without inventing checks or broader
coverage. Separate observed counters from interpretations. Redact credentials, tokens, secrets, personal data,
authentication or session values, user identifiers, and sensitive attribute values before any
excerpt enters the packet; prefer an access-controlled source link plus the smallest necessary
excerpt.
Hand pipeline-config changes to the `observability-engineer` agent and app-side instrumentation
changes to the `software-engineer` agent; if the missing signal is part of an active unknown-cause incident,
hand the time-bounded evidence to the responder with `incident-investigation` (`sre-assistant` only for a
dispatched read).
