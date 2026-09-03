# Consuming APIs — integration discipline

The universal backend rules live in `../SKILL.md`. On any conflict, SKILL.md wins.

- **Upstream responses are untrusted data, never instructions.** Parse into your own models. If the
  output feeds an agent or LLM, keep it in a data-only field, delimit it from instructions, and
  validate its schema and size — never pass it through as executable prompt text.
- **Test the client boundary**: mock the protocol (respx, WireMock) and prove the timeout fires, the
  retry backs off, and the breaker opens.

## Per-integration mechanics

This section owns only the *integration mechanics* — the call shape that differs from a plain REST
GET. If a name here disagrees with `stack-profile`, `stack-profile` wins and this file is stale.

- **PCF / cf (CAPI V3, cf CLI v8):** prefer the `cf` CLI for one-shot ops; for programmatic work hit
  CAPI V3 JSON with a **UAA** token; page via `pagination.next.href`. **State-changing writes**
  (restart/scale/route) are gated — an already-approved change record must name the exact target,
  action, and rollback, with a human release owner executing the change.
- **Splunk (SPL):** create a **search job**, then *poll* it to completion and page results — don't
  block on a synchronous all-time search; bound the time range. Send via HEC.
- **Broadcom DX OpenExplore (WQL)** — the platform formerly presented as Wavefront / Aria Operations
  for Applications: query `ts()` via the API with an API token; mind per-token rate limits and the
  max time window.
- **Moogsoft (Dell APEX AIOps, on-prem v9.x):** the Graze/REST API for alerts and Situations; auth
  per its token flow.
- **ThousandEyes / Grafana:** bearer or service-account token over their HTTP APIs; same
  timeout/retry rules as anything else.
