# Our Splunk indexes & saved searches — fill in

Concrete values for the `obs-logs` skill. The agent loads this on demand.

> Names and access-controlled links only — no credentials, tokens, user/session values, or raw payloads.

## Indexes / sourcetypes by app

| App / service | `index` | `sourcetype` | `host` pattern |
|---|---|---|---|
| `<app>` | `<index>` | `<sourcetype>` | `<host-*>` |

## Correlation fields (so we can trace one request across services)

- Request/correlation id field: `<field_name>` (e.g. `request_id`, `trace_id`, `x_request_id`)
- User/session id field: `<field_name>`
- If a service doesn't emit one, that's a finding → ask `software-engineer` to add it.

## Field extractions we rely on

| Field | How it's extracted | Example |
|---|---|---|
| `status` | `<auto / props.conf / rex>` | HTTP status |
| `latency_ms` | `<rex pattern>` | per-request latency |
| `error_type` | `<auto / props.conf / rex>` | failure class — the SPL top-offender searches depend on it |
| `service` | `<auto / props.conf / rex>` | emitting service, for breakdowns and correlation |

## Saved searches & dashboards

| Name | Link | Purpose |
|---|---|---|
| `<saved search>` | `<url>` | `<error-rate alert, etc.>` |

## Loki streams by app

All rows are `[unverified]` placeholders until checked against the target tenant.

| App / service | Tenant | Stable selector | Parser |
|---|---|---|---|
| `<app>` | `<tenant>` | `{app="<app>", env="<env>"}` | `<json|logfmt|regexp>` |
