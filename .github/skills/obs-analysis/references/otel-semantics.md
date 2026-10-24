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

Do not treat every parent/child pair as a network hop. Confirm the kinds on both sides, and expect links
or separated timelines for deferred work. A missing counterpart remains an instrumentation/propagation
hypothesis until another signal verifies the call.

## Span status is not the protocol status

`Unset` is the default, not proof of health. `Ok` means explicit success validation by the application
or operator; interpret `Error` under the active semantic convention.

For HTTP, 1xx–3xx normally leave span status unset absent another error. With no extra request context,
server-side 4xx is normally `Unset`; client-side 4xx should be `Error`. A 5xx should be `Error`. Inspect
both span status and `http.response.status_code`, because the same HTTP outcome can be classified
differently by client and server spans.

## Read stable attributes in context

Stable HTTP conventions landed in semconv v1.23.x, database conventions in v1.33.0. Older
instrumentation can retain legacy names within its major version; inspect emitted fields before
rewriting a query or treating an empty stable-name query as no traffic.

| Legacy field that may still be emitted | Current stable field |
|---|---|
| `http.method` | `http.request.method` |
| `http.status_code` | `http.response.status_code` |
| `db.system` | `db.system.name` |
| `db.name` | `db.namespace` |
| `db.operation` | `db.operation.name` |

Existing instrumentation may expose `http` / `http/dup` or `database` / `database/dup` stability opt-in
modes. Record the active convention and emitted fields; this trace-reading skill does not change them.

`url.full` can include userinfo credentials and sensitive query parameters; redact before copying it.

## Sampling makes absence weak evidence

Recording and sampling are separate. `RECORD_ONLY` sets `IsRecording=true` and `Sampled=false`:
the span records data and reaches processors (for example, local latency calculations), while the
SDK normally excludes it from export. `RECORD_AND_SAMPLE` makes a recording span eligible for
export; the sampled flag does not prove exporter success or backend receipt/retention.
