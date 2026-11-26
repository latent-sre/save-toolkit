---
name: obs-analysis
description: >-
  Query and interpret logs, metrics, and traces (SPL, LogQL, Cloud Logging, PromQL, Cloud
  Monitoring, TraceQL, Cloud Trace); design symptom-based alerts, SLIs/SLOs, multi-window
  error-budget burn rates, Splunk saved-search alerts, Moogsoft correlation, and ThousandEyes
  synthetics; and instrument or debug OTel SDKs and Alloy/collector telemetry pipelines.
  Triggers: 'search the logs', 'write a metric query', 'define an SLO',
  'logs are not reaching Loki'. Use
  incident-investigation for active incident decisions and grafana for Grafana dashboard, rule,
  silence, and datasource operations.
argument-hint: "[service, signal, query, SLO/alert, or telemetry pipeline]"
---

# Telemetry & observability — signal queries, alerting/SLOs, and pipelines

Load only the reference needed for the task. Answer standalone signal, SLO, or pipeline questions
directly from supplied evidence without starting unrelated design or investigation workflows.

| Need | Reference |
|---|---|
| Signal population, baselines, request correlation, missing data | [Signal methods](./references/signal-methods.md) |
| Log queries: Splunk SPL, Loki LogQL, GCP Cloud Logging | [SPL](./references/spl.md), [LogQL](./references/logql.md), [Cloud Logging](./references/gcp-logging.md) |
| Metric queries: PromQL, Mimir limits, GCP Cloud Monitoring | [PromQL & Cloud Monitoring](./references/promql.md) |
| Trace queries: Tempo TraceQL, GCP Cloud Trace | [TraceQL](./references/traceql.md), [Cloud Trace](./references/gcp-trace.md) |
| OpenTelemetry span semantics, attributes, SDK instrumentation, sampling, naming | [OTel semantics & SDK](./references/otel.md) |
| Grafana Alloy / collector wiring, Google Telemetry API, WAL/drop debugging, canaries | [Alloy pipeline](./references/alloy.md) |
| SLI/SLO error budgets and multi-window burn-rate alerting | [Burn-rate method](./references/burn-rate.md) |
| Splunk saved-search alerts, cron/window pairing, throttling, actions | [Splunk alerting](./references/splunk-alerting.md) |
| Alert storms, deduplication, and Moogsoft Onprem Situations | [Moogsoft correlation](./references/moogsoft.md) |
| Synthetic checks, DNS/BGP/path evidence, and ThousandEyes | [ThousandEyes synthetics](./references/thousandeyes.md) |

## 1. Signal querying and interpretation

- **Scope and windows:** Bind queries to service/environment/population, backend/tenant/index, and
  absolute UTC windows. Compare deploys across equal windows around the platform's actual
  deploy/traffic-change timestamp. (On Cloud Foundry, durable log history lives in the log backend
  rather than Apps Manager's memory-capped Log Cache; record the interval any buffer actually covers.)
- **Encoding and redaction:** Validate copied identifiers against their documented shape and
  preserve trace IDs verbatim. Never concatenate raw values: use dialect literal escaping, and for
  regex matchers apply literal-regex escaping before query-string encoding. Redact secrets,
  tokens, user/session identifiers, sensitive headers/bodies, and SQL literals; prefer
  access-controlled links plus minimal excerpts.

## 2. Alerting, SLIs/SLOs, and scheduled-work freshness

- **Paging bar:** Draft and test with a draft runbook. Before enabling new paging, confirm an
  owner, an actionable summary, and a working link to a human-approved runbook. For existing
  pages, report live state and documentation gaps separately.
  Keep request-ratio and time-based error budgets in their own units (never convert a
  request-ratio budget into downtime minutes), and separate consumed-budget status from current
  alert firing state. Load `grafana` for Grafana rule, silence, or contact-point implementation.
- **Scheduled-work freshness:** Track `*_last_success_timestamp_seconds` per expected job. Set the
  alert age threshold to `max_freshness_age - (detection + delivery + recovery + scrape/eval/for_lag)`
  (e.g., 26h RPO minus 1h combined allowance → alert at 25h / `90000s`:
  `time() - backup_last_success_timestamp_seconds >= 90000`) and confirm normal completion plus
  jitter fits below it. Detect missing telemetry separately from stale timestamps. For a backup
  required in each region, `expected_backups unless on(backup, region) backup_last_success_timestamp_seconds`
  returns the missing backup/region pairs. Use an expected inventory independent of the reporting
  series, with the same identity labels on both sides. A per-target `absent()` also works when
  scoped to the full identity. In Grafana, one vanished series among siblings
  transitions to Normal (`MissingSeries`), whereas zero series is `No Data`
  (`DatasourceNoData`/`DatasourceError`).
- **Verification:** Validate syntax (`promtool check rules` / `promtool test rules` for
  Prometheus-format rules — agent-runnable in `observability-engineer` only, setting `TMPDIR`/`TMP`
  for `promtool test`'s temporary TSDB; `sre-assistant` routes both to a human), force the
  condition on a safe non-production target/receiver to observe fire, delivery, and resolve, and
  verify the runbook link exists.

## 3. Telemetry pipelines — where a missing signal gets lost

If a backend query finds the signal but a panel does not, check `grafana` (datasource, variables,
time window) before changing the pipeline. Confirmed platform-managed feeds stay with the platform
owner. Otherwise isolate which boundary dropped the canary:

1. **App never emits:** exercise one request locally and check SDK diagnostics or console exporter.
2. **SDK never exports:** check endpoint, protocol, resource attributes, credentials, and export
   drop counters/logs (`otel.sdk.*` self-metrics are Development).
3. **Collector/Alloy rejects or drops:** check receiver health, accepted/refused counts, and
   processor `incoming_items`/`outgoing_items`; validate deployed config before editing.
4. **Exporter/backend rejects or misroutes:** check exporter sent/send-failed/enqueue-failed counts
   and run a time-bounded backend query for the canary's service and trace ID.

Route pipeline-config changes to `observability-engineer` and app instrumentation changes to
`software-engineer`.
