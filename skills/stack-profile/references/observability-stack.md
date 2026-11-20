# Observability stack

Use the [parent profile](../SKILL.md) for runtime, coexistence and authority boundaries; this is the
signal/product inventory, not a platform-selection decision.

## Two stacks, coexisting (churn is an axiom, not an event)

| Signal | Incumbent | Additive, first-class |
|---|---|---|
| Logs | Splunk (SPL) | Loki (LogQL) |
| Metrics | **PCF App Metrics** (the live metrics UI for PCF applications today) | Mimir / Prometheus (PromQL) |
| Traces | — (new capability) | Tempo (TraceQL) |
| Dashboards | Grafana 13.3.x self-managed | same instance |
| Alerting / correlation | Moogsoft Onprem v9.x (Dell; 9.2 is the supported line, confirm the target's minor); ThousandEyes synthetics | Grafana unified alerting |
| Pipeline | — | Alloy + OTel collectors |
| Edge / CDN / WAF / RUM | Akamai (Property Manager delivery, App & API Protector, DataStream 2 logs, mPulse RUM); DataStream 2 destination: not yet confirmed by the owner | — |

Grafana recovery copies are saved in the team's repositories. That does not establish Git Sync,
provisioning ownership, backup freshness, or a tested restore; confirm those separately for the
target. A saved copy does not authorize a live write.

The owner selected Grafana `gcx` for the SRE assistant's read-only Grafana access migration.
Protected agent execution, exact command admission, redirect/destination enforcement, and
installed-client acceptance remain pending. The bundled Python helper is the existing admitted path
during migration. The choice adds no terminal grant, live-write authority, vendor skill bundle or
Grafana MCP server.

Cloud Logging/Monitoring/Trace join additively as
GCP workloads land. For PCF, incumbent tools come first; new backends are usable for a service only
after instrumentation, not an assumed replacement.
