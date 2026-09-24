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
| `route` | `<auto / props.conf / rex>` | route template with ids removed, for latency and error breakdowns |

## PCF apps in Splunk

All rows are `[unverified]` placeholders until read from one real event. If the Splunk Firehose
nozzle feeds Splunk, log lines arrive as sourcetype `cf:logmessage` and HTTP start/stop events as
`cf:httpstartstop` *[sourced: Splunk Firehose nozzle docs]*; a syslog drain carries whatever its
input sets.

| What | Value | Note |
|---|---|---|
| Org / space / app fields | `<org_field>` / `<space_field>` / `<app_field>` | bind all three; app names repeat across spaces |
| Request completion (rate denominator) | `index=<pcf_index> sourcetype=<sourcetype> <rtr_selector>` | Gorouter `RTR` lines, emitted per routed request |
| App output | `<app_selector>` | `APP` lines: stdout/stderr, not a request count |
| Status / response time | `<status_field>` / `<response_time_field>` | RTR `response_time` is in seconds, not ms |
| Request id | `<request_id_field>` | RTR `vcap_request_id`, for one-request correlation |

*[sourced: docs.cloudfoundry.org streaming-logs — RTR and APP log types, `response_time` in
seconds, `vcap_request_id`]*

## Saved searches & dashboards

| Name | Link | Purpose |
|---|---|---|
| `<saved search>` | `<url>` | `<error-rate alert, etc.>` |

## Loki streams by app

All rows are `[unverified]` placeholders until checked against the target tenant.

| App / service | Tenant | Stable selector | Parser |
|---|---|---|---|
| `<app>` | `<tenant>` | `{app="<app>", env="<env>"}` | `<json|logfmt|regexp>` |
