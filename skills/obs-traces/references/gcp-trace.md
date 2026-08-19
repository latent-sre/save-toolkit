# Cloud Trace — the GCP trace backend

Use this reference only after applying the product-agnostic investigation shape in the parent
skill. Sources reviewed 2026-08-19 against live official pages on `docs.cloud.google.com` (every
`cloud.google.com/...` docs URL now 301-redirects there).

## Where trace data goes now (this changed recently)

- **Ingest is OTLP via the Telemetry API** — `telemetry.googleapis.com` "implements the
  OpenTelemetry OTLP API" and is the recommended path for new **and existing** users. It is
  all-signal — `/v1/traces`, `/v1/metrics`, `/v1/logs` — not trace-only. The older proprietary
  Cloud Trace API is *not* retired: it is absent from the deprecations page, and the docs prefer
  the Telemetry API over it for its higher ingestion quotas *[sourced:
  docs.cloud.google.com/stackdriver/docs/reference/telemetry/overview;
  docs.cloud.google.com/stackdriver/docs/otlp/overview;
  cloud.google.com/blog "OpenTelemetry now in Google Cloud Observability", 2025-09]*.
- Cloud Trace's internal storage now uses the **OpenTelemetry data model natively** *[sourced:
  cloud.google.com/blog "OpenTelemetry now in Google Cloud Observability", 2025-09]*, and the
  Trace explorer was rebuilt around it (span aggregation views, heatmaps) *[sourced: Cloud Trace
  release notes, 2025-01-24]*.
- **Trace sinks are deprecated as of 2026-02-18** *[sourced: Cloud Trace release notes]* — do not
  design an export around them; Observability Analytics queries traces with SQL (GA) for the
  analytical path.
- Collector wiring: OTLP exporter → collector/Alloy → `endpoint: https://telemetry.googleapis.com`
  with Application Default Credentials; the writing principal needs `roles/telemetry.writer` plus
  the Service Usage Consumer role and a quota project *[sourced:
  docs.cloud.google.com/stackdriver/docs/otlp/overview]*. The Alloy component shapes live in the
  `obs-pipeline` skill's Alloy reference.

## Reading traces during the migration

- **TraceQL does not apply here.** Cloud Trace is queried through the Trace explorer (filters:
  service, latency, status, span attributes) and Observability Analytics SQL — not TraceQL. The
  investigation shape (find exemplar → read the critical path → compare populations) is the parent
  skill's; only the query surface differs. Tempo remains the additive first-class backend; a trace
  id from Cloud Run logs (`trace` field) opens in whichever backend that service exports to —
  check the pipeline route before declaring a trace "missing".
- W3C trace context propagates identically on both runtimes — one request crossing PCF and Cloud
  Run during coexistence still correlates, **if** both sides propagate; a hop with no common id is
  the same telemetry-gap finding as anywhere else.
- Span attributes follow OTel semconv (`service.name`, `deployment.environment.name`); Cloud Run
  adds resource labels (`service_name`, `revision_name`) that link a slow span population to the
  revision that introduced it — the trace-side "what changed".

## Gotchas

- Sampling: default SDK/agent sampling on Cloud Run can be aggressive; an absent trace is
  evidence about sampling config before it is evidence about traffic. Record the sampler and rate
  with any absence claim.
- The Telemetry API's limits are per-project and regionally variable — trace ingestion 2.4 GB/min
  in major regions vs 300 MB/min elsewhere *[sourced: docs.cloud.google.com/trace/docs/quotas]*;
  sustained drops at high volume are a quota hypothesis, checked in the API dashboard.
- Retention and span caps: the `_Trace` bucket retains spans for **30 days**; per-span limits
  include 1,024 attributes and 256 events *[sourced: docs.cloud.google.com/trace/docs/quotas]*.
  A trace absent beyond 30 days is retention, not telemetry loss.
- Cross-project traces require the viewer to hold access on the scoping project; "no data" for one
  responder and data for another is an IAM symptom, not a telemetry one.

## Inert canary example

Never run outside a canary drill; it references a deliberately nonexistent service.

```text
Trace explorer filter: service:"canary-q-otgcp-2c8d" AND status:error
```

Reference-read token: q_otgcp_2c8d
