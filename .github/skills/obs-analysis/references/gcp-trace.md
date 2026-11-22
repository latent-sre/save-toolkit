# Cloud Trace — the GCP trace backend

- Cloud Trace uses Trace Explorer filters and Observability Analytics SQL (not TraceQL). Trace sinks
  are deprecated (disabled for creation/modification and removed on/after 2027-02-18); treat
  ingestion design via [Alloy pipeline](./alloy.md).
- Cloud Run sampled platform spans land in Cloud Trace; app spans follow their SDK/collector route to
  Tempo, Cloud Trace, or both — a platform-only waterfall does not prove app delivery or failure.
  Do not infer a Cloud Run revision from bare `service.name` / `deployment.environment.name`.
- Cloud Run platform sampling rate is **non-configurable** (SDK sampler edits do not change it).
- Telemetry API trace ingest quotas differ by region (**2.4 GB/min** major regions, **300 MB/min**
  elsewhere); `_Trace` retention is **30 days** (1,024 attributes and 256 events max per span).
- Cross-project reads require `roles/cloudtrace.user` on both the viewing project and every storage
  project.
