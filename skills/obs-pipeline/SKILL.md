---
name: obs-pipeline
description: >-
  What ships telemetry where — instrument a service with OTel and route metrics, traces, and
  structured logs through Alloy/collectors to Loki, Mimir, Tempo, Splunk, and Wavefront. Triggers:
  'instrument this service', 'add telemetry', 'logs are not showing up in', 'wire X to Grafana'.
  Ownership map only—not a load: obs-logs, obs-metrics, and obs-traces own reading the signals.
argument-hint: "[service, missing signal, or telemetry route]"
---

> **Evidence default — `[unverified]`.** Unless a paragraph carries a narrower label, each
> stack/product-specific command, query, API or CLI behavior, version, licensing statement, and
> runtime claim in this skill and its bundled files is `[unverified]` for the exact target.
> A narrower `[sourced]` or `[verified]` label takes precedence; handoffs never upgrade it.

# Ship telemetry end to end

Treat the pipeline as one path with four independently failing boundaries:

```text
app → SDK/agent → collector/Alloy → backend
```

| Signal | App emission | Transport and processing | Backend |
|---|---|---|---|
| Structured logs | approved JSON fields plus trace/span correlation | OTLP or file receiver → redact/filter/batch → route | Loki; Splunk where required |
| Metrics | OTel instruments with bounded attributes | OTLP receiver → resource/attribute processing → route | Mimir and the current Wavefront path |
| Traces | spans with propagated W3C trace context | OTLP receiver → sampling/batch → route | Tempo |

GCP exporters are the future backend slot; this skill ships no GCP exporter configuration.

## Where a missing signal gets lost

1. **The app never emits it.** Tier-0: exercise one known request locally and inspect SDK diagnostics
   or a local console exporter for the expected log, metric, or span before checking the network.
2. **The SDK/agent never exports it.** Tier-0: confirm the process has the intended endpoint,
   protocol, resource attributes, and credentials, then inspect its export error/drop counters.
3. **The collector/Alloy never accepts or keeps it.** Tier-0: check receiver health and accepted,
   refused, processed, and dropped counts for that signal; validate the deployed config before edits.
4. **The exporter/backend rejects, delays, or misroutes it.** Tier-0: check exporter send/failure
   evidence, then issue one time-bounded backend query using the canary's exact service and trace IDs.

At each boundary, record the target, time range, exact check, and result. A healthy later component
does not prove an earlier boundary, and a backend query with no bounded canary does not identify loss.

| Need | Reference |
|---|---|
| Instrumentation, RED/USE, propagation, sampling, correlation, or completion criteria | [OTel SDK method](./references/otel-sdk.md) |
| Alloy receivers, processors, exporters, routing, pipeline health, or end-to-end canary | [Alloy pipeline](./references/alloy.md) |

## The cardinality rule (this is what blows up metric stores)
**Bounded** dimensions → metric labels/tags. **Unbounded** identity (user/request/trace IDs, full URLs,
emails, raw SQL) → traces and logs, **never** metric labels. A label with unbounded values creates a new
time series per value and melts the metrics backend.

## Naming — OTel uses DOTS, not underscores
- **The OTel name is the source of truth:** namespaces delimited by **dots**, `snake_case` only *within*
  a multi-word component. **Units live in instrument metadata (UCUM), never in the name** — *"units do
  not need to be specified in the names since they are included during instrument creation."* Base units
  (seconds, bytes); counters not pluralized; dimensions in attributes, not the name.
  ```
  ✅  http.server.request.duration     unit: s     <- an OTel instrument name
  ❌  http_request_duration_seconds                <- an EXPORTER's rendering, not an OTel name
  ```
- **This lands natively on our stack.** Wavefront takes dot-delimited names + point tags
  (`app.http.requests.latency`) — the OTel shape, near-unchanged. Keep the bounded-tag discipline.
  Wavefront receives dot-delimited names plus bounded point tags; this section owns the emitted naming/tag contract.
- *Portability note (off-stack):* an underscore-style exporter translates **for you** — dots → `_`, a
  unit suffix appended, `_total` on monotonic sums. Never pre-bake that shape into the instrument name
  or it gets applied twice. Authoring the underscore form and calling it OTel is the common error.
- In **Wavefront** the same metrics arrive as dot-delimited names (`app.http.requests.latency`) + point
  tags — keep the identical bounded-tag discipline. Wavefront receives dot-delimited names plus bounded point tags; this section owns the emitted naming/tag contract.
