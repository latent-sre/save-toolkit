# Wavefront and Splunk data sources

Read this for Wavefront/Splunk-backed dashboards and their plugin entitlement. The team's naming,
folder, time, and variable decisions are in [dashboard conventions](./dashboard-conventions.md). It
is not an inventory of a Grafana instance: discover names, uids, owners, and installed plugins from
the target, and never store credentials or sensitive queries here.

## Licence and lifecycle facts

Catalogue guidance is not entitlement evidence. Confirm edition, the installed plugin list
(`GET /api/plugins`), and the administrator's licence record before proposing either plugin.

- Wavefront uses WQL through `grafana-wavefront-datasource`, an Enterprise plugin. Its backend
  continues as Broadcom DX OpenExplore; support against the team's tenant is `[unverified]`.
  Wavefront is the live metrics UI for this team's PCF applications today; "legacy" here means the
  data-source plugin and licence lineage, not the team's usage. *[sourced: operator statement
  2026-09-02]*
- Splunk uses SPL through `grafana-splunk-datasource` and has the same Enterprise-entitlement check.
- ThousandEyes has no Grafana data-source plugin. Its OpenTelemetry signals land in an installed
  Prometheus/Mimir, Tempo, or Loki backend and are queried there; never invent a plugin type or uid.

*[sourced: Grafana plugin catalogue and Broadcom lifecycle material, reviewed 2026-07-14 and
re-checked 2026-08-19]*
