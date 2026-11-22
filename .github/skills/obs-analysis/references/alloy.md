# Alloy pipeline

## Configuration wiring

`loki.*` and `prometheus.*` components wire through `forward_to = [<component>.receiver]`;
`otelcol.*` components use `output { }` blocks listing downstream `.input` exports.
`discovery.relabel.output` carries scrape targets, whereas `prometheus.relabel.receiver` accepts
metric samples — never interchange them.

## Google Cloud Telemetry API OTLP

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

Use ADC with `roles/telemetry.writer`, Service Usage Consumer, and a quota project. OTLP/HTTP uses
`https://telemetry.googleapis.com` (never the gRPC `host:port` shape). `otelcol.auth.google` is
**public preview** through Alloy v1.22.0 and requires `--stability.level=public-preview`.

## Validating and debugging a running Alloy

- Keep receiver protocol, bind address, auth, and TLS explicit; redact secrets/PII and forbid
  unbounded high-cardinality labels in processors.
- Validate before `/-/reload` with the same `--stability.level` and
  `--feature.community-components.enabled` flags. In Alloy v1.21.3, `alloy validate <config>`
  checks static syntax, component names, required/unknown properties, and `foreach`/`declare`
  blocks without resolving remote imported modules or testing network/auth delivery.
- Without local Alloy, an authorized unguarded lane can validate a self-contained config via
  networkless Docker with a pinned version tag (the SRE guard denies `alloy` and `docker`):

  ```powershell
  $alloyConfig = (Resolve-Path -LiteralPath .\config.alloy -ErrorAction Stop).ProviderPath
  docker run --rm --network none --mount "type=bind,source=$alloyConfig,target=/etc/alloy/config.alloy,readonly" grafana/alloy:<pinned-version> validate --stability.level=public-preview /etc/alloy/config.alloy
  ```

## Backpressure and data loss

- **`prometheus.remote_write`** buffers in a WAL (`truncate_frequency = "2h"`,
  `min_keepalive_time = "5m"`, `max_keepalive_time = "8h"` upstream defaults). **`8h` is not
  guaranteed outage retention:** WAL segment truncation and send lag determine which unsent samples
  survive, and truncation discards the oldest unsent samples.
- **`loki.write`** retries with backoff (`500ms → 5m`, 10 retries, retries on 429) and then **drops
  the batch**, logging `"final error sending batch, no retries left, dropping data"`.
- Check `/-/ready` and accepted/refused/dropped/queued/sent/failed counters per signal, and verify
  changed routes with a bounded non-production canary query at the destination store.
