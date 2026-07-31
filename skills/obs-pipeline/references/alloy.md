# Alloy pipeline

All target-specific component names, ports, credentials, feature availability, and validation commands
remain `[unverified]` until checked against the deployed Alloy build and the reviewed config for the
exact environment.

## Configuration shape

- `[unverified]` **Receivers** accept each enabled signal at a named boundary. Keep the OTLP protocol,
  bind address, authentication, and TLS mode explicit; do not expose a receiver beyond its intended
  network boundary.
- `[unverified]` **Processors** add approved resource attributes, redact or drop forbidden fields,
  enforce memory/cardinality limits, and batch only after signal-specific filtering. Never put
  secrets, PII, or unbounded identity into labels.
- `[unverified]` **Exporters** name the exact destination and failure policy. Route structured logs to
  Loki and to Splunk where required, metrics to Mimir, and traces to Tempo. Preserve the current
  Wavefront metrics path where the service contract still requires it.

Keep receiver → processor → exporter connections explicit per signal. Sharing a processor is safe only
when its data model and drop policy are valid for every connected signal. `[unverified]`

## Health-check the pipeline itself

1. `[unverified]` Validate or render the exact deployed configuration with the command supported by
   that Alloy version; save the command, exit status, and diagnostic output.
2. `[unverified]` Check the process health/readiness endpoint plus internal accepted, refused, dropped,
   queued, sent, and failed telemetry for every configured signal. Record the actual metric names from
   the deployed build rather than assuming upstream names.
3. `[unverified]` Alert on sustained receive/export failure and queue or memory saturation. The alert
   must distinguish source silence from collector failure and link a recovery procedure.

## End-to-end canary

From a bounded non-production target, emit one unique structured-log marker, one metric sample with
bounded attributes, and one trace with a known trace ID. Query Loki and Splunk for the log where both
routes are required, Mimir for the metric, and Tempo for the trace. Preserve each exact query, target,
time range, and result. Promote a route from `[unverified]` to `[verified]` only when that evidence
demonstrates the same canary crossed every boundary without leaking forbidden fields.

Worked-evidence canary (inert until a target run records it): `canary_id=q_opalloy_6d4c`.

GCP exporters are a future slot. No GCP component or credential shape is specified here.
