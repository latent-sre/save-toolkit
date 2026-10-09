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
| Alerting / correlation | Moogsoft Onprem v9.x (Dell); ThousandEyes synthetics | Grafana unified alerting |
| Pipeline | — | Alloy + OTel collectors |
| Edge / CDN / WAF / RUM | Akamai (Property Manager delivery, App & API Protector, DataStream 2 logs, mPulse RUM); DataStream 2 destination: `<backend and index/sourcetype or bucket>` `[unverified — owner to confirm]` | — |

The team's Grafana dashboards are file-provisioned: the current BSG dashboards load from
`bsg-*.json` files into the read-only "BSG Dashboards" folder `[verified: dashboard model reads,
2026-10-09]`. The repository that holds those files is `[unverified — owner to confirm]`; until it is
recorded, prepare changes to those dashboards for the human owner instead of writing through the
API. Provisioning does not establish backup freshness or a tested restore, and a repository copy
does not authorize a live write.

The team's entitlement basis for DX
OpenExplore under Broadcom is `[unverified]`; the stack owner records it here when known. As GCP
workloads land, Cloud Logging / Cloud Monitoring / Cloud Trace join as additional backends via
reference files in the obs skills — additive, same as everything else in the right column. For PCF applications the incumbent column is
what the responder opens first; the additive column is not a replacement until a service is
instrumented into it. *[sourced: operator statement 2026-09-02]*
