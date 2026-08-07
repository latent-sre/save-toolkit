# Alloy pipeline

All target-specific component names, ports, credentials, feature availability, and validation
commands remain `[unverified]` until checked against the deployed Alloy build and the reviewed
config for the exact environment. Syntax below is `[sourced]` to the official Alloy docs
(`grafana.com/docs/alloy/latest/…`), reviewed 2026-08-07 via indirect retrieval of the doc
sources; Alloy releases minors every ~3 weeks, so re-check component arguments against the
deployed version's reference page.

## The configuration model

Config is **attributes** (`key = value`) plus **blocks**; a component is a top-level block
`component.name "label" { … }`. Components take arguments and expose **exports**; downstream
components consume them by reference (`local.file_match.tmplogs.targets`). The language is the
"Alloy configuration syntax" — "River" is the *old* name from Grafana Agent Flow docs; don't use
it in new work. *[sourced: docs/alloy/latest/get-started/configuration-syntax/]*

**The wiring asymmetry that causes most broken pipelines:** `loki.*`/`prometheus.*` components
chain with `forward_to = [<component>.receiver]`, while `otelcol.*` components chain with an
`output { }` block listing downstream `.input` exports. And on the discovery side:
`discovery.relabel` exports `.output` (targets), `prometheus.relabel` exports `.receiver`
(samples) — mixing those two up is the classic wiring error. *[sourced: component reference pages]*

## Pipeline shapes (adapt labels/endpoints to the environment)

**Logs — file/journal → process → Loki** *[sourced: tutorials/logs-and-relabeling-basics; reference/components/loki/*]*

```alloy
local.file_match "applogs" {
    path_targets = [{"__path__" = "/var/log/app/*.log"}]
}

loki.source.file "local_files" {
    targets    = local.file_match.applogs.targets
    forward_to = [loki.process.enrich.receiver]
}

loki.process "enrich" {
  forward_to = [loki.write.default.receiver]
  stage.json   { expressions = { "extracted_env" = "environment" } }
  stage.labels { values = { "env" = "extracted_env" } }
}

loki.write "default" {
    endpoint { url = "http://<loki>:3100/loki/api/v1/push" }
}
```

**Metrics — discovery → scrape → Mimir remote_write** *[sourced: collect/prometheus-metrics; reference/components/prometheus/prometheus.remote_write]*

```alloy
prometheus.scrape "apps" {
  targets    = discovery.relabel.apps.output
  forward_to = [prometheus.remote_write.mimir.receiver]
}

prometheus.remote_write "mimir" {
  endpoint {
    url = "http://<mimir>:9009/api/v1/push"
  }
}
```

**OTLP (traces/metrics/logs) — receive → batch → export** *[sourced: collect/opentelemetry-data; collect/opentelemetry-to-lgtm-stack]*

```alloy
otelcol.receiver.otlp "default" {
  grpc { endpoint = "127.0.0.1:4317" }
  http { endpoint = "127.0.0.1:4318" }
  output {
    traces  = [otelcol.processor.batch.default.input]
  }
}

otelcol.processor.batch "default" {
  output { traces = [otelcol.exporter.otlp.tempo.input] }
}

otelcol.exporter.otlp "tempo" {
  client { endpoint = "<tempo>:4317" }
}
```

The same `otelcol.exporter.otlp` slot pointed at `https://telemetry.googleapis.com` (with
Application Default Credentials) is the documented path into Cloud Trace as GCP workloads land —
see the `obs-traces` skill's Cloud Trace reference; the exporter auth block for it remains
`[unverified]` here.

## Discipline that stays regardless of syntax

- **Receivers**: keep protocol, bind address, authentication, and TLS explicit; never expose a
  receiver beyond its intended network boundary.
- **Processors**: add approved resource attributes, redact forbidden fields, enforce
  memory/cardinality limits, and batch only after signal-specific filtering. No secrets, PII, or
  unbounded identity in labels. Sharing a processor across signals is safe only when its data
  model and drop policy hold for every connected signal. `[unverified]`
- **Exporters**: name the exact destination and failure policy. Structured logs to Loki (and
  Splunk where required), metrics to Mimir plus the current Wavefront path, traces to Tempo.

## Debugging a running Alloy

- HTTP server with a **debugging UI at `/`**, default `127.0.0.1:12345`
  (`--server.http.listen-addr`); endpoints `/metrics`, `/-/ready`, `/-/healthy`, `/-/reload`,
  `/-/support` (support bundle). *[sourced: troubleshoot/debug; reference/http]*
- **Live debugging** (per-component data stream in the UI) is disabled by default "to avoid
  accidentally displaying sensitive telemetry data"; enable deliberately, in non-prod first:

  ```alloy
  livedebugging { enabled = true }
  ```

  *[sourced: reference/config-blocks/livedebugging]*
- Clustering: `clustering { enabled = true }` inside `prometheus.scrape` distributes targets by
  consistent hashing; assumes identical config on every peer, and cluster CLI flags are fixed at
  startup — `/-/reload` does not change membership. *[sourced: get-started/clustering]*

## Backpressure and loss — where data quietly dies

- **`prometheus.remote_write`** buffers in a WAL: defaults `truncate_frequency = "2h"`,
  `min_keepalive_time = "5m"`, `max_keepalive_time = "8h"`. An unreachable endpoint grows disk
  until truncation, and samples older than max keepalive are force-purged — an outage longer than
  ~8h loses the tail silently. *[sourced: reference/components/prometheus/prometheus.remote_write]*
- **`loki.write`** retries with backoff (defaults: 500ms → 5m, 10 retries, retry on 429) and then
  **drops the batch**, logging "final error sending batch, no retries left, dropping data" — that
  log line is the loss evidence to grep for. *[sourced: loki write client source]*
- Watch the component's own accepted/refused/dropped/sent/failed metrics per signal; record the
  actual metric names from the deployed build rather than assuming upstream names. `[unverified]`
- Alert on sustained receive/export failure and queue or memory saturation; the alert must
  distinguish source silence from collector failure and link a recovery procedure.

## Health-check the pipeline itself

1. `[unverified]` Validate or render the exact deployed configuration with the command supported
   by that Alloy version; save the command, exit status, and diagnostic output.
2. `[unverified]` Check `/-/ready` plus internal accepted, refused, dropped, queued, sent, and
   failed telemetry for every configured signal.
3. `[unverified]` Confirm the alert coverage above exists for this deployment.

## End-to-end canary

From a bounded non-production target, emit one unique structured-log marker, one metric sample with
bounded attributes, and one trace with a known trace ID. Query Loki and Splunk for the log where both
routes are required, Mimir for the metric, and Tempo for the trace. Preserve each exact query, target,
time range, and result. Promote a route from `[unverified]` to `[verified]` only when that evidence
demonstrates the same canary crossed every boundary without leaking forbidden fields.

Worked-evidence canary (inert until a target run records it): `canary_id=q_opalloy_6d4c`.
