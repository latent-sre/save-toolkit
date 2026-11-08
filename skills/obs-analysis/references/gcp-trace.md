# Cloud Trace — the GCP trace backend

## Reading traces here

- Cloud Trace uses Trace explorer filters and Observability Analytics SQL, not TraceQL; trace sinks
  are deprecated, so do not design analysis around sink export. `obs-pipeline` owns ingestion.
- Cloud Run's sampled platform request spans land in Cloud Trace; application spans follow the
  SDK/collector route to Tempo, Cloud Trace or both. For a log trace ID, check platform spans here
  and application spans in their recorded destinations; unknown routes remain gaps. Platform-only
  waterfalls prove neither application delivery nor propagation/export failure.
- Application spans can carry `service.name` and `deployment.environment.name` without Cloud Run
  resource labels; do not infer a revision when absent.

## Gotchas

- Cloud Run's platform sampling rate is not configurable. Changing the SDK sampler does not alter it.
  Application sampler,
  parent-context policy and collector sampling independently constrain coverage. Bind absence
  claims to span source, applicable sampling and export/backend evidence.
- Telemetry API trace-ingest quotas differ by region: 2.4 GB/min in major regions, 300 MB/min
  elsewhere; the Cloud Trace API has its own quotas.
  Check the API dashboard before attributing sustained high-volume drops to quota.
- `_Trace` retention is 30 days; per-span caps include 1,024 attributes and 256 events. Expired
  traces cannot establish whether original sampling/export succeeded.
- Cross-project reads need `roles/cloudtrace.user` on the viewing project and every storage project.
  Compare backend/scope/window/filters before blaming responder differences on access; viewing-project
  access alone is insufficient.
