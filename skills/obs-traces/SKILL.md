---
name: obs-traces
description: >-
  Follow one request across services — when logs say 'slow' and metrics say 'sometimes',
  the trace says where. Read waterfalls, find the span that ate latency, and correlate
  trace ids with logs. Backends: Tempo (TraceQL) and Cloud Trace on GCP. Triggers: 'trace this
  request', 'where did the latency go', 'open this trace id'. A request or correlation id with no
  trace id starts in obs-logs. Not for trace instrumentation (obs-pipeline).
argument-hint: "[trace id, service, or latency question]"
---

# Traces — the investigation shape

Traces connect one sampled request across instrumented boundaries; logs give event detail, metrics
population trends. A bounded interpretation needs the answer, supplied scope/evidence and uncertainty.
Retrieval, comparison and full-path work below are for requested investigation, not prerequisites for
explaining a supplied span.

**Grafana pointer:** Grafana navigation, datasource selection, panel configuration, dashboard
interpretation, and alert operations live in `grafana`. This skill retains TraceQL, waterfall
analysis, and trace/log correlation; return configuration follow-up to the caller.

## Know what the waterfall represents

A long span shows where elapsed time was observed, not why the operation was slow. Do not add
nested durations: a parent already includes its synchronous children. A visual gap may be
uninstrumented work, scheduling, propagation loss, or clock behavior — not proven idle time.

## Enter through one of two doors

When retrieval is requested, use a real trace id and the request's UTC window for direct lookup.
A request/correlation id needs mapping through logs first (load `obs-logs` to map it to a trace id);
it is not automatically a trace id.
Preserve trace ids exactly. Treat copied identifiers as untrusted: validate the backend's documented
shape and place them only in quoted values.

For an investigation without an id, start from service, environment, operation, and symptom over a
bounded window. Select a representative trace from the affected population. Record how it was selected;
one trace is an example, not proof of prevalence.

## Find the span that controls latency

Compare slow against known-normal traces from the same route and deployment cohort (name a missing
comparison). A wide client span with a narrower server span only hypothesizes time outside the
remote handler. For asynchronous work, use links, timestamps, and message identity rather than a
synchronous nesting model, and separate queue delay from consumer processing.

## Read status and protocol outcome together

Inspect span status and the protocol outcome together under the span kind's convention
([OpenTelemetry semantics](./references/otel-semantics.md) owns the rules); an unset span status
is not success.

## Correlate without overclaiming

When correlating logs is in scope, use the same trace id and align by UTC time and service; keep
source links. A missing trace, span, or log event can result from
sampling, retention, backend size limits, propagation, export, or instrumentation gaps, so
absence is telemetry evidence—not proof that the request or call never happened.

## Build the evidence packet

Bounded interpretation: answer, supplied scope/source, uncertainty and useful clarification; no
comparison or critical-path table required. Full investigation:
retain entry/UTC window, source links, selection method, affected/comparison ids, critical-path table,
status/protocol interpretation, missing hops and sampling limits. Preserve missing evidence and
confidence labels; separate observations from hypotheses. The `obs-pipeline` skill owns changes to
instrumentation, propagation, collection, and export; do not load `obs-pipeline` for a reading task.

Minimize copied telemetry. Redact credentials, tokens, secrets, personal data, authentication or
session values, and user identifiers before any excerpt enters the packet; prefer an
access-controlled source link plus the smallest necessary excerpt. Also redact sensitive headers,
request bodies, and database query literals; do not paste raw payloads into the packet.

## Pick the reference — read it before writing the query

| If the question involves… | Read first |
|---|---|
| Tempo or TraceQL | [TraceQL](./references/traceql.md) |
| Cloud Trace, the Telemetry API, or a GCP-hosted service's traces | [Cloud Trace](./references/gcp-trace.md) |
| Span kinds, status, attributes, propagation, or sampling | [OpenTelemetry semantics](./references/otel-semantics.md) |

Read it **before** writing that query or interpreting those fields, and name what you read in your packet.
