# Observability stack

Read when the request involves an observability backend, signal, query language, vendor lifecycle,
GCP observability choice, or an edge, CDN, WAF, or RUM product. The parent `SKILL.md` owns the
current-runtime truth, additive-stack rule, stay-in-lane boundary, decision status, and evidence
labels; this inventory settles none of those rules by itself.

## Two stacks, coexisting (churn is an axiom, not an event)

| Signal | Incumbent | Additive, first-class |
|---|---|---|
| Logs | Splunk (SPL) | Loki (LogQL) |
| Metrics | Wavefront / Aria Ops for Applications — now Broadcom DX OpenExplore (WQL) | Mimir / Prometheus (PromQL) |
| Traces | — (new capability) | Tempo (TraceQL) |
| Dashboards | Grafana 13.1.x self-managed; **13.2 upgrade planned** `[sourced: owner, 2026-08-21]` | same instance |
| Alerting / correlation | Moogsoft (Dell APEX AIOps, on-prem v9.x); ThousandEyes synthetics | Grafana unified alerting |
| Pipeline | — | Alloy + OTel collectors |
| Edge / CDN / WAF / RUM | Akamai (Property Manager delivery, App & API Protector, DataStream 2 logs, mPulse RUM) | — |

Both incumbent columns stay first-class — Splunk, Wavefront, Grafana, Alloy, and Prometheus all
deepen in place; none is being retired by team decision. **Vendor lifecycle — `[sourced]`
(reviewed 2026-08-19):** the Wavefront platform continues as **Broadcom DX OpenExplore** — Broadcom
TechDocs introduces it as "a high-performance observability and analytics platform built using
Aria Operations for Applications (Wavefront) and the DX platform", with actively maintained
Wavefront release notes (February 2026) and a TAS integration, under
`techdocs.broadcom.com/us/en/ca-enterprise-software/it-operations-management/dx-openexplore/saas/`.
The 2025-10-31 end-of-availability (support.broadcom.com announcement 25153) retired the VMware
*Tanzu Observability* offering, not the platform. The team's tenant answers as DX OpenExplore —
observed 2026-08-19, UI version 250.1 with residual VMware branding `[sourced: operator
observation]`; the number fits DX OpenExplore's scheme (its release notes cite "version 235.8" in
March 2025). Still `[unverified]`: the team's entitlement/contract basis under Broadcom — the
stack owner records it here when known. As GCP workloads land, Cloud Logging / Cloud Monitoring /
Cloud Trace join as additional backends via reference files in the obs skills — additive, same as
everything else in the right column.
