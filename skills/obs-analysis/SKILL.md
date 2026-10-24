---
name: obs-analysis
description: >-
  Query and interpret logs, metrics, and traces: signal meaning, request correlation, and bounded
  comparisons. Triggers: 'search the logs', 'write a metric query', 'trace this request',
  'explain this telemetry'. Live incident decisions use incident-investigation; alert/SLO design
  uses obs-alerting, Grafana operations use grafana, and instrumentation/export uses obs-pipeline.
argument-hint: "[service, signal, query, or evidence]"
---

# Signal analysis

Read the applicable signal method for queries or interpretation; read backend references when
writing queries or interpreting backend-specific fields. Load only what the question needs.
Supplied-evidence explanations need no new retrieval, baseline, or full investigation.

| Need | References |
|---|---|
| Logs / correlation IDs | [Method](./references/log-analysis.md); [SPL](./references/spl.md), [LogQL](./references/logql.md), [Cloud Logging](./references/gcp-logging.md) |
| Metrics | [Method](./references/metric-analysis.md); [WQL](./references/wql.md), [PromQL](./references/promql.md), [Cloud Monitoring](./references/gcp-monitoring.md) |
| Traces | [Method](./references/trace-analysis.md); [TraceQL](./references/traceql.md), [Cloud Trace](./references/gcp-trace.md); [OTel](./references/otel-semantics.md) for status, attributes, propagation or sampling |
| Target fields/selectors | [Log inventory](./references/indexes.md), [metric inventory](./references/metrics.md) |
| Recurring log queries | [Catalog](./references/query-catalog.md) |

PCF history uses Splunk; Apps Manager retains only recent minutes. `stack-profile` owns backend
choices. `grafana` owns navigation/configuration; a query does not start a change workflow.
Proposed saved searches/alerts/dashboards go to the caller for `observability-engineer`, app
instrumentation gaps for `software-engineer`. This skill grants no write or incident ownership.

Bind queries to service/environment/population, backend/tenant/index, source and absolute UTC
window/timezone. Widen one boundary at a time with a reason. Deploy comparisons use equal windows
around the platform's actual deploy/traffic-change time, not a dashboard annotation.

Validate copied identifiers against their documented shape; preserve trace IDs exactly. Never
concatenate raw values: use the dialect's literal encoding and prefer exact match. Regex values
need literal-regex escaping, then query-string encoding; anchors do not escape metacharacters.
Uncertain encoding requires a sanitized identifier, not a wider search.

Return the answer and evidence limits; query work also retains exact query, scope/window,
source/result, references used and method-specific assumptions. Preserve incoming evidence labels.
Keep unknowns and hypotheses
distinct from observations. Prefer access-controlled links and minimal excerpts; redact secrets,
personal/user/session identifiers, sensitive headers/bodies, SQL literals and label/tag/attribute
values. Never paste raw payloads.
