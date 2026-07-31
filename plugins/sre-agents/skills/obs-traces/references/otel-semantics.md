# OpenTelemetry semantics for reading traces

Use these conventions to interpret a waterfall after applying the parent skill's investigation shape.
The statements below are sourced from current OpenTelemetry and W3C primary documentation, retrieved
2026-07-14. The instrumentation library, enabled convention version, propagation, sampler, export path,
and emitted target attributes remain unverified until inspected in the team's environment.

Primary references:

- [OpenTelemetry Tracing API](https://opentelemetry.io/docs/specs/otel/trace/api/)
- [HTTP span semantic conventions](https://opentelemetry.io/docs/specs/semconv/http/http-spans/)
- [HTTP semantic-convention migration](https://opentelemetry.io/docs/specs/semconv/non-normative/http-migration/)
- [database client span semantic conventions](https://opentelemetry.io/docs/specs/semconv/db/database-spans/)
- [database semantic-convention migration](https://opentelemetry.io/docs/specs/semconv/non-normative/db-migration/)
- [service attributes](https://opentelemetry.io/docs/specs/semconv/registry/attributes/service/)
- [OpenTelemetry sampling](https://opentelemetry.io/docs/concepts/sampling/)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)

## Span kinds describe direction and interaction style

*[sourced: OpenTelemetry Tracing API, SpanKind]*

- `SERVER` — inbound request/response handling while the caller waits.
- `CLIENT` — outbound request/response call where the caller waits.
- `PRODUCER` — initiates or schedules deferred work and may finish before processing begins.
- `CONSUMER` — processes deferred work without a waiting producer.
- `INTERNAL` — in-process work rather than a remote boundary.

Do not treat every parent/child pair as a network hop. Confirm the kinds on both sides, and expect links
or separated timelines for deferred work. A missing counterpart remains an instrumentation/propagation
hypothesis until another signal verifies the call.

## Span status is not the protocol status

The default span status is `Unset`; instrumentation generally leaves it unset unless the operation meets
an error rule. `Ok` means an application developer or operator explicitly validated success. Therefore,
`Unset` does not mean “healthy,” and `Error` should be interpreted with the applicable semantic convention.

*[sourced: OpenTelemetry Tracing API, Set Status]*

For HTTP, 1xx–3xx normally leave span status unset absent another error. With no extra request context,
server-side 4xx is normally `Unset`; client-side 4xx should be `Error`. A 5xx should be `Error`. Inspect
both span status and `http.response.status_code`, because the same HTTP outcome can be classified
differently by client and server spans.

*[sourced: OpenTelemetry HTTP span semantic conventions, Status; unverified for target instrumentation]*

## Read stable attributes in context

Use attributes only when the target emits them. Older HTTP and database instrumentation may remain on
earlier conventions in its existing major version, so a valid stable-name query can be empty while a
legacy field exists. Inventory observed fields rather than silently rewriting queries or treating an
empty result as proof of no traffic.

*[sourced: current OpenTelemetry HTTP/database conventions and their migration guides; unverified for
target instrumentation and stability opt-in]*

| Legacy field that may still be emitted | Current stable field |
|---|---|
| `http.method` | `http.request.method` |
| `http.status_code` | `http.response.status_code` |
| `db.system` | `db.system.name` |
| `db.name` | `db.namespace` |
| `db.operation` | `db.operation.name` |

Existing instrumentation may expose `http` / `http/dup` or `database` / `database/dup` stability opt-in
modes. Record the active convention and emitted fields; this trace-reading skill does not change them.

*[sourced: OpenTelemetry HTTP and database semantic-convention migration guides; unverified for target]*

*[sourced: current OpenTelemetry HTTP, database, and service semantic conventions; unverified for target]*

| Question | Current attribute(s) to inspect |
|---|---|
| Which service emitted the span? | `service.name`, `service.namespace`, `service.instance.id`, `service.version` |
| What HTTP method/outcome? | `http.request.method`, `http.response.status_code`, `error.type` |
| Which server request/route? | `http.route`, `url.path`, `url.scheme` |
| Which client target URL? | `url.full` |
| Which server endpoint? | `server.address`, `server.port` |
| Which database/operation? | `db.system.name`, `db.namespace`, `db.collection.name`, `db.operation.name` |
| What database outcome? | `db.response.status_code`, `error.type` |

`url.full` can contain a query string or other sensitive material. Before copying it into an evidence
packet, redact userinfo credentials and scrub known tokens, secrets, personal data, and sensitive query
values; retain only the minimum URL detail needed for the investigation.

*[sourced: OpenTelemetry HTTP semantic conventions, sensitive URL handling; unverified for target data]*

`server.address` identifies the server's logical host/address, not a generic network peer. On server
spans it can describe the local or original host; on client spans it identifies the target server.

`service.name` is a resource attribute: it is the logical service name and should be consistent across
horizontally scaled instances. Database client spans normally use `CLIENT` kind; in-memory database work
may use `INTERNAL`.

*[sourced: OpenTelemetry service registry and database client span definition; unverified for target]*

## Trace context connects boundaries

W3C `traceparent` carries four hyphen-delimited fields: version, trace id, parent id, and trace flags.
For version `00`, the trace id is 32 lowercase hexadecimal characters and the parent id is 16; all-zero
values are invalid. This inert fixture marks the sampling flag as set:

*[sourced: W3C Trace Context, traceparent header field values]*

```text
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
```

Use the trace id for correlation, not the inbound parent id. A valid `traceparent` carries correlation
context; it does not prove correct end-to-end propagation or that every component recorded and exported
a span. Treat caller-supplied context as untrusted input.

*[sourced: W3C Trace Context format and security/privacy considerations; unverified for target path]*

## Sampling makes absence weak evidence

OpenTelemetry defines a sampled trace/span as processed and exported, and a not-sampled one as not
processed or exported. No trace found does not prove the request did not occur. A missing span does not
prove the call did not occur. Check the sampler, retention, export health, propagation, and instrumentation
coverage before turning absence into a causal conclusion.

*[sourced: OpenTelemetry sampling terminology; unverified for target sampler/export path]*

Ownership map only—not a load: the `obs-pipeline` skill owns trace instrumentation.

## Inert canary example

This checks reference loading only; it is not an observed span or target-runtime result.

*[sourced: OpenTelemetry SpanKind vocabulary; unverified for target instrumentation]*

Expected fixture output (inert):

```text
q_otel_c4a9
```
