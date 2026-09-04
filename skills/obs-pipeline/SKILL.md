---
name: obs-pipeline
description: >-
  What ships telemetry where — instrument a service with OTel and route metrics, traces, and
  structured logs through Alloy/collectors to Loki, Mimir, and Tempo. Triggers:
  'instrument this service', 'add telemetry', 'logs are not showing up in', 'wire X to Grafana'.
  Not for reading the signals (obs-logs, obs-metrics, obs-traces).
argument-hint: "[service, missing signal, or telemetry route]"
---

# Ship telemetry end to end

Treat the pipeline as one path with four independently failing boundaries:

```text
app → SDK/agent → collector/Alloy → backend
```

| Signal | App emission | Transport and processing | Backend |
|---|---|---|---|
| Structured logs | approved JSON fields plus trace/span correlation | OTLP or file receiver → redact/filter/batch → route | Loki |
| Metrics | OTel instruments with bounded attributes | OTLP receiver → resource/attribute processing → route | Mimir |
| Traces | spans with propagated W3C trace context | OTLP receiver → sampling/batch → route | Tempo |

Splunk and Wavefront/PCF App Metrics are fed by the PCF platform, not by anything this
skill wires: 'logs are not in Splunk' is a `pcf-ops` and `obs-logs` question.

GCP backends are landing with the migration: the documented ingest is OTLP to the Telemetry API
(`telemetry.googleapis.com` — all three signals, though logs ingestion is Pre-GA) through the same
otelcol exporter slot. The [Alloy pipeline](./references/alloy.md) reference shows the
public-preview Google-auth component and required stability flag. Exact target project/config and
route behavior remain `[unverified]` until a canary run proves them.

## Where a missing signal gets lost

1. **The app never emits it.** Tier-0: exercise one known request locally and inspect SDK diagnostics
   or a local console exporter for the expected log, metric, or span before checking the network.
2. **The SDK/agent never exports it.** Tier-0: confirm the process has the intended endpoint,
   protocol, resource attributes, and credentials, then inspect its export error/drop counters.
3. **The collector/Alloy never accepts or keeps it.** Tier-0: check receiver health and accepted,
   refused, processed, and dropped counts for that signal; validate the deployed config before edits.
4. **The exporter/backend rejects, delays, or misroutes it.** Tier-0: check exporter send/failure
   evidence, then issue one time-bounded backend query using the canary's exact service and trace IDs.

A healthy later component does not prove an earlier boundary, and a backend query with no bounded
canary does not identify loss.

Read only the reference needed for the task:

| Need | Reference |
|---|---|
| Instrumentation, RED/USE, propagation, sampling, correlation, or completion criteria | [OTel SDK method](./references/otel-sdk.md) |
| Alloy receivers, processors, exporters, routing, pipeline health, or end-to-end canary | [Alloy pipeline](./references/alloy.md) |

## The cardinality rule (this is what blows up metric stores)
**Bounded** dimensions → metric labels/tags. **Unbounded** identity (user/request/trace IDs, full URLs,
emails, raw SQL) → traces and logs, **never** metric labels. A label with unbounded values creates a new
time series per value.

## Naming — OTel uses DOTS, not underscores
- **The OTel name is the source of truth:** namespaces delimited by **dots**, `snake_case` only *within*
  a multi-word component. **Units live in instrument metadata (UCUM), not the name** (upstream allows a
  unit in the name only to resolve ambiguity) — *"units do not need to be specified in the names since
  they are included during instrument creation."* Base units (seconds, bytes); dimensions in
  attributes, not the name. Pluralization follows the unit: a name whose value carries a real unit
  stays singular, a unitless countable is pluralized (`system.paging.faults`,
  `system.network.packets`), and UpDownCounter names are never pluralized. *[sourced: semconv
  `general/naming`]*
  ```
  ✅  http.server.request.duration     unit: s     <- an OTel instrument name
  ❌  http_request_duration_seconds                <- an EXPORTER's rendering, not an OTel name
  ```
- **This lands natively on our stack.** Wavefront takes dot-delimited names + point tags
  (`app.http.requests.latency`) — the OTel shape, near-unchanged. Keep the bounded-tag discipline;
  this section owns the emitted naming/tag contract.
- *Portability note (the Mimir path):* a Prometheus-style exporter translates **for you, by default**
  (`translation_strategy: UnderscoreEscapingWithSuffixes`) — dots → `_`, a unit suffix appended,
  `_total` on monotonic sums; with Prometheus 3.x UTF-8 names, `NoTranslation` passes the dotted name
  through instead. The exporter dedupes suffixes the name already carries, so pre-baking is not
  applied twice — and it still breaks the OTel naming contract and every non-Prometheus rendering.
  *[sourced: OTel spec `sdk_exporters/prometheus` and the Prometheus-compatibility spec]*

## Build the evidence packet

Return, per boundary walked: the target, absolute UTC window, exact check run, and result, plus
the canary's service and trace IDs, the deployed config revision, and a confidence label per
claim. Separate observed counter values from interpretations. Minimize copied telemetry: redact
credentials, tokens, secrets, personal data, and sensitive attribute values before any payload
excerpt enters the packet; prefer an access-controlled link plus the smallest necessary excerpt.
Hand pipeline-config changes to the `observability-engineer` agent and app-side instrumentation
changes to the `software-engineer` agent; if the missing signal is part of an active unknown-cause incident,
hand the time-bounded evidence to the responder with `incident-investigation` (`sre-assistant` only for a
dispatched read).
