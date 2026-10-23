# Alloy pipeline

Target-specific components, ports, credentials, feature availability, and validation commands
remain unconfirmed until checked against the deployed Alloy build and exact environment config.
Examples follow the official Alloy documentation; check component arguments against that
build's reference before use.

## Contents

- The configuration model
- Pipeline shapes
- Discipline that stays regardless of syntax
- Debugging a running Alloy
- Backpressure and loss — where data quietly dies
- Health-check the pipeline itself
- End-to-end canary

## The configuration model

Config is **attributes** (`key = value`) plus **blocks**; a component is a top-level block
`component.name "label" { … }`. Components take arguments and expose **exports**; downstream
components consume them by reference (`local.file_match.tmplogs.targets`). The language is the
"Alloy configuration syntax" — "River" is the *old* name from Grafana Agent Flow docs; don't use
it in new work.

**Component wiring:** `loki.*`/`prometheus.*` components
chain with `forward_to = [<component>.receiver]`, while `otelcol.*` components chain with an
`output { }` block listing downstream `.input` exports. And on the discovery side:
`discovery.relabel` exports `.output` (targets), `prometheus.relabel` exports `.receiver`
(samples) — mixing those two up is the classic wiring error.

## Pipeline shapes

Build each route from the wiring rules above (file/journal or discovery inputs, signal-specific
processing, one exporter per destination); adapt labels and endpoints to the environment.

To send a three-signal OTLP pipeline to Google's Telemetry API, replace the generic
`otelcol.exporter.otlp` exporter block with this block. The current Grafana Google-auth
example omits the port, while the OTLP exporter contract requires `host:port`; this example follows
that contract and uses the gRPC TLS port:

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
- **Processors**: add approved resource attributes, redact forbidden fields, enforce
  memory/cardinality limits, and batch only after signal-specific filtering. No secrets, PII, or
  unbounded identity in labels. Sharing a processor across signals is safe only when its data
  model and drop policy hold for every connected signal; this rule is not yet confirmed.
- **Exporters**: map each configured signal to its actual destination, protocol, and failure policy
  (LGTM, Google Telemetry API, or a verified gateway). Existing PCF-owned Splunk and Wavefront feeds
  remain platform responsibilities; verify or hand off gaps without wiring new exporters for them.

## Debugging a running Alloy

- **`alloy validate <config>`** is a documented CLI command (alongside `run`, `fmt`, `convert`) —
  validate before any `/-/reload`. It is not allowed by the read-only guard: validation resolves
  `import.http` and `import.git`, so an untrusted config can initiate outbound requests (including
  a URL assembled from environment-backed expressions). Ask a human or use an isolated,
  networkless runner; `alloy fmt -w`, `alloy run`, and `alloy tools` also stay denied. This CLI
  behavior is as described in Alloy v1.18.1.
- **Docker is the local fallback when the Alloy binary is unavailable.** Assemble the exact
  self-contained config being reviewed, replace `<pinned-version>` with the deployed Alloy version
  (never `latest` for retained evidence), and validate it without network access. With a local Docker
  daemon, mount only that file read-only; a PowerShell text pipeline can change its encoding and line endings:

  ```powershell
  $alloyConfig = (Resolve-Path -LiteralPath .\config.alloy -ErrorAction Stop).ProviderPath
  docker run --rm --network none --mount "type=bind,source=$alloyConfig,target=/etc/alloy/config.alloy,readonly" grafana/alloy:<pinned-version> validate --stability.level=public-preview /etc/alloy/config.alloy
  ```

  Omit `--stability.level=public-preview` only when the exact config has no public-preview
  components. Do not pass credentials, mount the Docker socket, or relax network isolation merely
  to make an imported config pass; route trusted imports to a controlled runner instead. Keep the
  input file unchanged during validation. Record its hash, image reference, `alloy --version`, command,
  exit status, and diagnostics. This is static
  validation: it checks syntax, component availability, references, and types, but does not prove
  DNS, TCP, TLS, authentication, or telemetry delivery. Execution of the exact image and config
  is unconfirmed until run.
## Backpressure and loss — where data quietly dies

- **`prometheus.remote_write`** buffers in a WAL: defaults `truncate_frequency = "2h"`,
  `min_keepalive_time = "5m"`, `max_keepalive_time = "8h"`. An unreachable endpoint grows disk
  until truncation, and samples older than max keepalive are force-purged — an outage longer than
  ~8h loses the tail silently.
- **`loki.write`** retries with backoff (defaults: 500ms → 5m, 10 retries, retry on 429) and then
  **drops the batch**, logging "final error sending batch, no retries left, dropping data" — that
  log line is the loss evidence to grep for.
- Watch the component's own accepted/refused/dropped/sent/failed metrics per signal; record the
  actual metric names from the deployed build rather than assuming upstream names.
- Alert on sustained receive/export failure and queue or memory saturation; the alert must
  distinguish source silence from collector failure and link a recovery procedure.

## Health-check the pipeline itself

1. Validate or render the exact deployed configuration with the command supported
   by that Alloy version; save the command, exit status, and diagnostic output.
2. Check `/-/ready` plus internal accepted, refused, dropped, queued, sent, and
   failed telemetry for every configured signal.
3. Confirm the alert coverage above exists for this deployment.

## End-to-end canary

For each signal on the changed route, emit a bounded non-production canary: a unique log marker,
a metric sample with bounded attributes, or a known trace ID. Query the reviewed destination:
Loki/Mimir/Tempo for LGTM, or Logs/Metrics/Trace Explorer for Google ingestion. Check every
configured branch of a fan-out; do not require signals or stores outside the changed path.
Preserve query, target/tenant, UTC window, result, and corresponding receive/export evidence.
Call a route `[verified]` only when the canary crossed its boundaries without forbidden fields;
unexercised routes stay `[unverified]`.
