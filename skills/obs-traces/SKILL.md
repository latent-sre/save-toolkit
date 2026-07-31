---
name: obs-traces
description: >-
  Follow one request across services — when logs say 'slow' and metrics say 'sometimes',
  the trace says where. Read waterfalls, find the span that ate latency, and correlate
  trace ids with logs. Backend: Tempo (TraceQL). Triggers: 'trace this request',
  'where did the latency go', 'follow this correlation id'. Ownership map only—not a
  load: obs-pipeline owns trace instrumentation.
---

> **Evidence default — `[unverified]`.** Unless a paragraph carries a narrower label, each
> stack/product-specific command, query, API or CLI behavior, version, licensing statement, and
> runtime claim in this skill and its bundled files is `[unverified]` for the exact target.
> A narrower `[sourced]` or `[verified]` label takes precedence; handoffs never upgrade it.

# Traces — the investigation shape

Use a trace when the question is about one request's path, ordering, or latency allocation. Logs are
better for event detail and metrics are better for population trends; a trace connects one sampled
request across instrumented boundaries. Keep backend syntax out of the investigation packet until you
have selected and read the matching reference.

## Know what the waterfall represents

A trace is a causal graph rendered as a timeline. Its spans describe operations; parent/child links
describe nesting, and attributes or events add context. A long span tells you where elapsed time was
observed, not automatically why the operation was slow.

Read left to right from the root. Mark the user-visible interval, then follow the branch that determines
when the root can finish. That branch is the critical path. Do not add nested durations: a parent's
duration already includes synchronous children. Parallel branches overlap, and a visual gap may be
uninstrumented work, scheduling, propagation loss, or clock behavior—not proven idle time.

## Enter through one of two doors

If you have a real trace id, preserve it exactly, constrain the originating request's UTC window, and
look it up directly. A generic request or correlation id is not automatically a trace id: first use the
logs to map it to a trace id. Treat identifiers copied from tickets or logs as untrusted data; validate a
candidate trace id against the backend's documented shape and place it only in a quoted value position.

If you have no id, start from the service, environment, operation, and latency or error symptom over a
bounded window. Select a representative trace from the affected population. Record how it was selected;
one trace is an example, not proof of prevalence.

## Find the span that controls latency

For each span on the critical path, record its service, operation, kind, start/end, duration, status,
and relevant peer or dependency. Compare a slow trace with a known-normal trace from the same route and
deployment cohort. A wide client span with a much narrower downstream server span can point toward time
before/after the remote handler, but the gap remains a hypothesis until another signal explains it.

For asynchronous work, do not force producer and consumer spans into a synchronous nesting model. Use
links, timestamps, and message identity where present, and separate queue delay from consumer processing.

## Read status and protocol outcome together

Span status is an instrumentation judgment, while an HTTP or database response code is a protocol
outcome. They can legitimately differ. Inspect both and apply the semantic convention for the span kind;
do not equate an unset span status with success or require every non-success protocol result to be an
instrumentation error.

## Correlate without overclaiming

Use the same trace id to retrieve nearby structured logs, then align them by UTC timestamp and service.
Keep the original log and trace evidence links. A missing trace, span, or log event can result from
sampling, retention, propagation, export, or instrumentation gaps, so absence is telemetry evidence—not
proof that the request or call never happened.

## Build the evidence packet

Return the entry point, exact UTC window, trace/artifact link, selection method, affected and comparison
trace ids, critical-path span table, status/protocol interpretation, missing hops, sampling caveat, and
confidence label. Separate observations from hypotheses. Ownership map only—not a load: the `obs-pipeline` skill owns changes to instrumentation, propagation, collection, and export.

Minimize copied telemetry. Redact credentials, tokens, secrets, personal data, authentication or session
values, user identifiers, sensitive headers, request bodies, and database query literals. Prefer an
access-controlled source link plus the smallest necessary excerpt; do not paste raw payloads into the
packet.

## Pick the reference — read it before writing the query

| If the question involves… | Read first |
|---|---|
| Tempo or TraceQL | [TraceQL](./references/traceql.md) |
| Span kinds, status, attributes, propagation, or sampling | [OpenTelemetry semantics](./references/otel-semantics.md) |

Read it **before** writing that query or interpreting those fields, and name what you read in your packet.
