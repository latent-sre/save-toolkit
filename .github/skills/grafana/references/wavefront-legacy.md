# Wavefront and Splunk data sources

Read this for Wavefront/Splunk-backed dashboards and their plugin entitlement. For new dashboards,
use [dashboard design](./dashboard-design.md#new-dashboard-conventions).
Discover names, uids, owners, and installed plugins from the target.

## Licence and lifecycle facts

Catalogue guidance is not entitlement evidence. Confirm edition, the installed plugin list
(`GET /api/plugins`), and the administrator's licence record before proposing either plugin.

- Wavefront uses WQL through `grafana-wavefront-datasource`, an Enterprise plugin. Its backend
  continues as Broadcom DX OpenExplore; support against the team's tenant is unconfirmed.
  Wavefront is the live metrics UI for this team's PCF applications today.
- Splunk uses SPL through `grafana-splunk-datasource` and has the same Enterprise-entitlement check.
- ThousandEyes documents an OpenTelemetry integration with Grafana Cloud. The team's deployed
  integration and receiving backend are unconfirmed; discover installed plugins and the actual
  telemetry route before querying. Never invent a plugin type or uid.
