# OpenTelemetry semantics for reading traces

Primary references:

- [OpenTelemetry Tracing API](https://opentelemetry.io/docs/specs/otel/trace/api/)
- [HTTP span semantic conventions](https://opentelemetry.io/docs/specs/semconv/http/http-spans/)
- [HTTP semantic-convention migration](https://opentelemetry.io/docs/specs/semconv/non-normative/http-migration/)
- [database client span semantic conventions](https://opentelemetry.io/docs/specs/semconv/db/database-spans/)
- [database semantic-convention migration](https://opentelemetry.io/docs/specs/semconv/non-normative/db-migration/)
- [service attributes](https://opentelemetry.io/docs/specs/semconv/registry/attributes/service/)
- [OpenTelemetry sampling](https://opentelemetry.io/docs/concepts/sampling/)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)

## Span kinds

Confirm both span kinds before treating parent/child as a network hop. Deferred work can use links
or separate timelines; a missing counterpart needs another signal to establish the call.

## Span status is not the protocol status

`Unset` is the default, not proof of health. `Ok` means explicit success validation by the application
or operator; interpret `Error` under the active semantic convention.

HTTP 1xx–3xx normally leaves status unset absent another error. Without extra request context,
server 4xx is normally `Unset`; client 4xx and either-side 5xx should be `Error`. Inspect status alongside
`http.response.status_code`; client/server classification differs.

## Read stable attributes in context

HTTP conventions stabilized in v1.23.x, database in v1.33.0. Older instrumentation may retain
legacy fields within its major version; inspect emitted fields before rewriting queries or
interpreting an empty stable-name query as no traffic.

| Legacy field that may still be emitted | Current stable field |
|---|---|
| `http.method` | `http.request.method` |
| `http.status_code` | `http.response.status_code` |
| `db.system` | `db.system.name` |
| `db.name` | `db.namespace` |
| `db.operation` | `db.operation.name` |

Existing instrumentation may expose `http` / `http/dup` or `database` / `database/dup` stability opt-in
modes. Record the active convention and emitted fields; this trace-reading skill does not change them.

In semconv v1.44.0, `service.instance.id`, `server.address`, `http.route`, and
`db.collection.name` are Stable; `messaging.destination.name` is Development. A valid name does
not imply stable maturity. `url.full` can include userinfo credentials and sensitive query
parameters; redact before copying it.

## Sampling makes absence weak evidence

`RECORD_ONLY` sets `IsRecording=true`, `Sampled=false`: processors receive recorded data but normal
SDK export excludes it. `RECORD_AND_SAMPLE` permits export; the flag proves neither exporter
success nor backend receipt/retention.
