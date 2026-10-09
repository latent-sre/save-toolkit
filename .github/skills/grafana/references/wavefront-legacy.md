# Wavefront and Splunk data sources

Read this for Wavefront/Splunk-backed dashboards and their plugin entitlement. The team's naming,
folder, time, and variable decisions are in [dashboard conventions](./dashboard-conventions.md).
Discover names, uids, owners, and installed plugins from the target.

## Licence and lifecycle facts

Catalogue guidance is not entitlement evidence. Confirm edition, the installed plugin list
(`GET /api/plugins`), and the administrator's licence record before proposing either plugin.

- Wavefront uses WQL through `grafana-wavefront-datasource`, an Enterprise plugin. Its backend
  continues as Broadcom DX OpenExplore; support against the team's tenant is unconfirmed.
  Wavefront is the live metrics UI for this team's PCF applications today.
- Splunk uses SPL through `grafana-splunk-datasource` and has the same Enterprise-entitlement check.
- ThousandEyes has no Grafana data-source plugin; never invent a plugin type or uid. That its
  OpenTelemetry signals land in an installed Prometheus/Mimir, Tempo, or Loki backend is
  unconfirmed; discover the backend before querying it.
