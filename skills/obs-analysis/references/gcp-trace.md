# Cloud Trace — the GCP trace backend

## Trace ingestion, storage, and export

- `obs-pipeline` owns OTLP/Telemetry API ingestion. The older proprietary Cloud Trace API is not
  retired; the Telemetry API is preferred for higher ingestion quotas.
- **Trace sinks are deprecated as of 2026-02-18** — do not
  design an export around them; Observability Analytics queries traces with SQL (GA) for the
  analytical path.

## Reading traces here

- Cloud Trace uses Trace explorer filters and Observability Analytics SQL, not TraceQL.
- **Identify the span source before choosing a backend.** Cloud Run automatically generates
  sampled platform request traces in Cloud Trace. Application spans follow the configured
  SDK/collector route to Tempo, Cloud Trace, or both. For a Cloud Run log's trace ID, look for
  platform spans in Cloud Trace and application spans in each recorded application destination;
  do not assume an unknown route. A platform-only waterfall does not prove application
  delivery, nor does it alone establish a propagation or export failure.
- Application spans can carry `service.name` and `deployment.environment.name` without Cloud Run
  resource labels; do not infer a revision when absent.

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
