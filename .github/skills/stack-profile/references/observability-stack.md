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
| Dashboards | Grafana 13.2.x self-managed `[sourced: owner, 2026-09-19]`; reviewed target reports 13.2.2 `[verified: /api/health, 2026-09-19]` | same instance |
| Alerting / correlation | Moogsoft (Dell APEX AIOps, on-prem v9.x); ThousandEyes synthetics | Grafana unified alerting |
| Pipeline | — | Alloy + OTel collectors |
| Edge / CDN / WAF / RUM | Akamai (Property Manager delivery, App & API Protector, DataStream 2 logs, mPulse RUM); DataStream 2 destination: `<backend and index/sourcetype or bucket>` `[unverified — owner to confirm]` | — |

Grafana recovery copies are saved in the team's repositories `[sourced: owner, 2026-09-19]`.
That does not establish Git Sync, provisioning ownership, backup freshness, or a tested restore;
confirm those separately for the target. A saved copy does not authorize a live write.

Both incumbent columns stay first-class — Splunk, Wavefront, Grafana, Alloy, and Prometheus all
deepen in place; none is being retired by team decision. The team's entitlement basis for DX
OpenExplore under Broadcom is `[unverified]`; the stack owner records it here when known. As GCP
workloads land, Cloud Logging / Cloud Monitoring / Cloud Trace join as additional backends via
reference files in the obs skills — additive, same as everything else in the right column. For PCF applications the incumbent column is
what the responder opens first; the additive column is not a replacement until a service is
instrumented into it. *[sourced: operator statement 2026-09-02]*
