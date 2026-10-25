# Alloy pipeline

Confirm components, ports, credential paths, features and validation commands against the deployed
Alloy build/configuration. Examples do not establish target compatibility or delivery.

## The configuration model

`loki.*`/`prometheus.*` wire through `forward_to = [<component>.receiver]`; `otelcol.*` uses
`output { }` listing downstream `.input` exports. `discovery.relabel.output` carries targets;
`prometheus.relabel.receiver` accepts samples. Do not interchange them.

## Pipeline shapes

For three-signal OTLP to Google's Telemetry API, the gRPC exporter requires `host:port`, even
though Grafana's Google-auth example omits the port:

```alloy
otelcol.exporter.otlp "default" {
  client {
    endpoint = "telemetry.googleapis.com:443"
    auth     = otelcol.auth.google.gcp.handler
  }
}

otelcol.auth.google "gcp" {
  project = "<project-id>"
}
```

Use Application Default Credentials with the writer's `roles/telemetry.writer`, Service Usage
Consumer role and quota project. An OTLP/HTTP exporter uses the root URL
`https://telemetry.googleapis.com`; do not reuse the gRPC `host:port` shape for it.

`otelcol.auth.google` is **public preview** in Alloy v1.18.1 and requires Alloy to start with
`--stability.level=public-preview` (or a lower stability level). The exact project, permissions,
deployment flag, and canary result remain unconfirmed for the target environment.

## Discipline that stays regardless of syntax

- **Receivers**: keep protocol, bind address, authentication, and TLS explicit; never expose a
  receiver beyond its intended network boundary.
- **Processors**: approved resource attributes, redaction, memory/cardinality bounds, then batching
  after signal-specific filtering. No secrets, PII or unbounded identity in labels. Confirm a shared
  processor's data model/drop policy works for each connected signal.
- **Exporters**: map each configured signal to its actual destination, protocol, and failure policy
  (LGTM, Google Telemetry API, or a verified gateway). Confirm each feed's route and owner;
  PCF-platform-owned Splunk and Wavefront feeds remain platform responsibilities, so hand their
  gaps to that owner rather than wiring replacement exporters.

## Debugging a running Alloy

- Validate before `/-/reload`. In v1.18.1, `alloy validate <config>` checks static shape/registers
  import namespaces without resolving or validating imported contents; success cannot prove remote
  modules work. The SRE guard denies it, as well as `alloy fmt -w`, `alloy run` and `alloy tools`.
  Request a human or an authorized isolated, networkless runner.
- Without local Alloy, an authorized lane can validate the exact self-contained config through
  local Docker. Pin the deployed version, never `latest`, mount only the config read-only and
  disable networking. A PowerShell text pipe can alter encoding/line endings:

  ```powershell
  $alloyConfig = (Resolve-Path -LiteralPath .\config.alloy -ErrorAction Stop).ProviderPath
  docker run --rm --network none --mount "type=bind,source=$alloyConfig,target=/etc/alloy/config.alloy,readonly" grafana/alloy:<pinned-version> validate --stability.level=public-preview /etc/alloy/config.alloy
  ```

  Omit the preview flag only when no configured component needs it. No credentials, Docker socket
  mounts or relaxed isolation to make imports pass; use a controlled runner for trusted imports.
  Keep input unchanged and record hash, image, `alloy --version`, command, exit and diagnostics.
  Static validation checks syntax/components/references/types, not DNS, TCP, TLS, authentication
  or delivery. Only an actual run establishes execution of that image/config.
## Backpressure and loss — where data quietly dies

- **`prometheus.remote_write`** buffers in a WAL. Upstream defaults include
  `truncate_frequency = "2h"`, `min_keepalive_time = "5m"`, `max_keepalive_time = "8h"`; inspect the
  deployed settings. Eight hours is not guaranteed outage retention: segment truncation and send
  lag affect which unsent samples survive, and truncation can discard the oldest unsent samples.
  Check WAL/send progress and loss evidence rather than inferring a safe outage duration from defaults.
- **`loki.write`** retries with backoff (defaults: 500ms → 5m, 10 retries, retry on 429) and then
  **drops the batch**, logging "final error sending batch, no retries left, dropping data" — that
  log line is the loss evidence to grep for.
- Read actual per-signal accepted/refused/dropped/sent/failed metric names from the deployed build.
- Alert on sustained receive/export failure and queue or memory saturation; the alert must
  distinguish source silence from collector failure and link a recovery procedure.

## Health-check the pipeline itself

Retain the exact-config validation receipt above. Check `/-/ready` plus accepted/refused/dropped/
queued/sent/failed telemetry for every configured signal, and confirm the stated alert coverage.

## End-to-end canary

Emit a bounded non-production log marker, metric sample with bounded attributes, or known trace ID
for each changed-route signal. Query the reviewed destination (Loki/Mimir/Tempo or Google
Logs/Metrics/Trace Explorer). Exercise every fan-out branch within scope, not unrelated stores.
Retain query, target/tenant, UTC window, result and receive/export evidence. Only canary passage
without forbidden fields verifies a route; unexercised routes stay `[unverified]`.
