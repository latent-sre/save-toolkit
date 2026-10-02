# Cloud Trace — the GCP trace backend

Use this reference only after applying the product-agnostic investigation shape in the parent
skill. Sources reviewed 2026-08-19 against live official pages on `docs.cloud.google.com` (every
`cloud.google.com/...` docs URL now 301-redirects there).

## Trace ingestion, storage, and export

- **OTLP-to-Telemetry-API endpoints, signal support, and service maturity are owned by
  `obs-pipeline`.** The older proprietary Cloud Trace API is *not*
  retired: it is absent from the deprecations page, and the docs prefer the Telemetry API for its higher ingestion quotas
  *[sourced: docs.cloud.google.com/stackdriver/docs/reference/telemetry/overview;
  cloud.google.com/blog "OpenTelemetry now in Google Cloud Observability", 2025-09]*.
- Cloud Trace's internal storage now uses the **OpenTelemetry data model natively** *[sourced:
  cloud.google.com/blog "OpenTelemetry now in Google Cloud Observability", 2025-09]*, and the
  Trace explorer was rebuilt around it (span aggregation views, heatmaps) *[sourced: Cloud Trace
  release notes, 2025-01-24]*.
- **Trace sinks are deprecated as of 2026-02-18** *[sourced: Cloud Trace release notes]* — do not
  design an export around them; Observability Analytics queries traces with SQL (GA) for the
  analytical path.

## Reading traces during the migration

- **TraceQL does not apply here.** Cloud Trace is queried through the Trace explorer (filters:
  service, latency, status, span attributes) and Observability Analytics SQL — not TraceQL. The
  investigation shape (find exemplar → read the critical path → compare populations) is the parent
  skill's; only the query surface differs. Tempo remains the additive first-class backend.
- **Identify the span source before choosing a backend.** Cloud Run automatically generates
  sampled platform request traces in Cloud Trace. Application spans follow the configured
  SDK/collector route to Tempo, Cloud Trace, or both. For a Cloud Run log's trace ID, look for
  platform spans in Cloud Trace and application spans in each recorded application destination;
  an unknown route stays `[unverified]`. A platform-only waterfall does not prove application
  delivery, nor does it alone establish a propagation or export failure.
  *[sourced: [Cloud Run tracing](https://docs.cloud.google.com/run/docs/trace) and
  [application instrumentation](https://docs.cloud.google.com/trace/docs/setup), checked 2026-10-02]*
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
  *[sourced: [Cloud Run sampling](https://docs.cloud.google.com/run/docs/trace#trace_sampling_rate) and
  [component sampling decisions](https://docs.cloud.google.com/trace/docs/setup), checked 2026-10-02]*
- The Telemetry API's limits are per-project and regionally variable — trace ingestion 2.4 GB/min
  in major regions vs 300 MB/min elsewhere *[sourced: docs.cloud.google.com/trace/docs/quotas]*;
  sustained drops at high volume are a quota hypothesis, checked in the API dashboard.
- Retention and span caps: the `_Trace` bucket retains spans for **30 days**; per-span limits
  include 1,024 attributes and 256 events *[sourced: docs.cloud.google.com/trace/docs/quotas]*.
  Older traces are not expected to remain queryable; absence cannot establish whether they were
  originally sampled or exported.
- Cross-project viewing requires `roles/cloudtrace.user` on the viewing project and every project
  storing the trace data. Compare backend, trace scope, time window, and filters before treating
  different responders' results as an access hypothesis; viewing-project access alone is insufficient.
  *[sourced: [Cloud Trace IAM](https://docs.cloud.google.com/trace/docs/iam); reviewed 2026-09-09]*
