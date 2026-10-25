# Observability stack

Use the [parent profile](../SKILL.md) for runtime, coexistence and authority boundaries; this is the
signal/product inventory, not a platform-selection decision.

## Two stacks, coexisting (churn is an axiom, not an event)

| Signal | Incumbent | Additive, first-class |
|---|---|---|
| Logs | Splunk (SPL) | Loki (LogQL) |
| Metrics | Wavefront / Aria Ops for Applications — now Broadcom DX OpenExplore (WQL); **the live metrics UI for PCF applications today, with PCF App Metrics** | Mimir / Prometheus (PromQL) |
| Traces | — (new capability) | Tempo (TraceQL) |
| Dashboards | Grafana 13.2.x self-managed; the reviewed target reports 13.2.2 | same instance |
| Alerting / correlation | Moogsoft Onprem v9.x (Dell); ThousandEyes synthetics | Grafana unified alerting |
| Pipeline | — | Alloy + OTel collectors |
| Edge / CDN / WAF / RUM | Akamai (Property Manager delivery, App & API Protector, DataStream 2 logs, mPulse RUM); DataStream 2 destination: not yet confirmed by the owner | — |

Grafana recovery copies are saved in the team's repositories. That does not establish Git Sync,
provisioning ownership, backup freshness, or a tested restore; confirm those separately for the
target. A saved copy does not authorize a live write.

DX OpenExplore entitlement remains unrecorded. Cloud Logging/Monitoring/Trace join additively as
GCP workloads land. For PCF, incumbent tools come first; new backends are usable for a service only
after instrumentation, not an assumed replacement.
