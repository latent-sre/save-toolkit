# Cloud Trace — the GCP trace backend

Use this reference only after applying the product-agnostic investigation shape in the parent
skill. Official pages live on `docs.cloud.google.com` (every `cloud.google.com/...` docs URL
301-redirects there).

## Trace ingestion, storage, and export

- **OTLP-to-Telemetry-API endpoints, signal support, and service maturity are owned by
  `obs-pipeline`.** The older proprietary Cloud Trace API is *not*
  retired: it is absent from the deprecations page, and the docs prefer the Telemetry API for its higher ingestion quotas.
- Cloud Trace's internal storage now uses the **OpenTelemetry data model natively**, and the
  Trace explorer was rebuilt around it (span aggregation views, heatmaps).
- **Trace sinks are deprecated as of 2026-02-18** — do not
  design an export around them; Observability Analytics queries traces with SQL (GA) for the
  analytical path.

## Reading traces here

- **TraceQL does not apply here.** Cloud Trace is queried through the Trace explorer (filters:
  service, latency, status, span attributes) and Observability Analytics SQL — not TraceQL. The
  investigation shape is the parent skill's; only the query surface differs.
- **Identify the span source before choosing a backend.** Cloud Run automatically generates
  sampled platform request traces in Cloud Trace. Application spans follow the configured
  SDK/collector route to Tempo, Cloud Trace, or both. For a Cloud Run log's trace ID, look for
  platform spans in Cloud Trace and application spans in each recorded application destination;
  an unknown route stays `[unverified]`. A platform-only waterfall does not prove application
  delivery, nor does it alone establish a propagation or export failure.
- W3C trace context propagates identically on both runtimes — one request crossing PCF and Cloud
  Run during coexistence still correlates, **if** both sides propagate; a hop with no common id is
  the same telemetry-gap finding as anywhere else.
- Inspect emitted attributes such as `service.name` and `deployment.environment.name`; correlate
  slow spans with observed service/revision metadata. Application-exported spans need not carry
  Cloud Run resource labels. Missing revision evidence stays `[unverified]`.

## Gotchas

- Sampling: Cloud Run's platform request-trace rate is not configurable. Application instrumentation
  has its own sampler and parent-context policy; collector sampling can further reduce coverage.
  Record the span source, applicable sampling policy, and export/backend evidence with an absence
  claim. Changing the SDK sampler does not configure the platform rate.
- The Telemetry API's limits are per-project and regionally variable — trace ingestion 2.4 GB/min
  in major regions vs 300 MB/min elsewhere;
  sustained drops at high volume are a quota hypothesis, checked in the API dashboard.
- Retention and span caps: the `_Trace` bucket retains spans for **30 days**; per-span limits
  include 1,024 attributes and 256 events.
  Older traces are not expected to remain queryable; absence cannot establish whether they were
  originally sampled or exported.
- Cross-project viewing requires `roles/cloudtrace.user` on the viewing project and every project
  storing the trace data. Compare backend, trace scope, time window, and filters before treating
  different responders' results as an access hypothesis; viewing-project access alone is insufficient.
