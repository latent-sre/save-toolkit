# Observability stack

Read when the request involves an observability backend, signal, query language, vendor lifecycle,
GCP observability choice, or an edge, CDN, WAF, or RUM product. The parent `SKILL.md` owns the
current-runtime truth, additive-stack rule, stay-in-lane boundary, decision status, and evidence
labels; this inventory settles none of those rules by itself.

## Two stacks, coexisting (churn is an axiom, not an event)

| Signal | Incumbent | Additive, first-class |
|---|---|---|
| Logs | Splunk (SPL) | Loki (LogQL) |
| Metrics | Wavefront / Aria Ops for Applications — now Broadcom DX OpenExplore (WQL); **the live metrics UI for PCF applications today, with PCF App Metrics** | Mimir / Prometheus (PromQL) |
| Traces | — (new capability) | Tempo (TraceQL) |
| Dashboards | Grafana 13.1.x self-managed; **13.2 upgrade planned** `[sourced: owner, 2026-08-21]` | same instance |
| Alerting / correlation | Moogsoft (Dell APEX AIOps, on-prem v9.x); ThousandEyes synthetics | Grafana unified alerting |
| Pipeline | — | Alloy + OTel collectors |
| Edge / CDN / WAF / RUM | Akamai (Property Manager delivery, App & API Protector, DataStream 2 logs, mPulse RUM) | — |

Both incumbent columns stay first-class — Splunk, Wavefront, Grafana, Alloy, and Prometheus all
deepen in place; none is being retired by team decision. The team's entitlement basis for DX
OpenExplore under Broadcom is `[unverified]`; the stack owner records it here when known. As GCP
workloads land, Cloud Logging / Cloud Monitoring / Cloud Trace join as additional backends via
reference files in the obs skills — additive, same as everything else in the right column. For PCF applications the incumbent column is
what the responder opens first; the additive column is not a replacement until a service is
instrumented into it. *[sourced: operator statement 2026-09-02]*
