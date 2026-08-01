---
name: obs-dashboards
description: >-
  Grafana 13 dashboards as code — layout for the 3am reader (top-level health → drill-down), panel
  hygiene, variables, provisioning, and data-source licence facts. Triggers: 'build a dashboard',
  'what should we dashboard', 'dashboard as code', 'add a panel for'. Ownership map only—not a load:
  frontend-craft owns product-UI data visualizations and obs-alerting owns alert rules.
argument-hint: "[service, dashboard question, or dashboard change]"
---

> **Evidence default — `[unverified]`.** Unless a paragraph carries a narrower label, each
> stack/product-specific command, query, API or CLI behavior, version, licensing statement, and
> runtime claim in this skill and its bundled files is `[unverified]` for the exact target.
> A narrower `[sourced]` or `[verified]` label takes precedence; handoffs never upgrade it.

# Grafana 13 operations dashboards as code

A dashboard must answer the on-call reader's next question quickly under stress. Start with service
health, preserve a single time context, and make every lower row a deliberate drill-down. This skill
owns Grafana operations dashboards; product-UI charts inside the application remain frontend work.
Alert-rule definitions and notification routing remain alerting work.

**Version evidence — `[sourced]` (reviewed 2026-07-14).** Grafana's
[v13 documentation](https://grafana.com/docs/grafana/latest/whatsnew/whats-new-in-v13-0/) records
Dynamic Dashboards and Git Sync as generally available in Grafana 13; the upstream
[v13.1.0 release](https://github.com/grafana/grafana/releases/tag/v13.1.0) was published 2026-07-01.
Validate the deployed minor version and enabled features before relying on either capability.

## Layout — top to bottom

1. **Health / SLO row.** Show the service's SLI, target, current burn, and budget remaining together.
   The first screen answers whether user impact exists and whether the error budget is being consumed.
2. **Golden-signals row.** Keep traffic, errors, latency (p50/p95/p99), and saturation on one aligned
   time range. Use rates and ratios where volume changes would make raw counts misleading.
3. **Drill-down rows.** Break down the same signals by dependency, route, instance, region, or failure
   class. A drill-down should test a response hypothesis; omit panels that do not change a decision.

## Panel hygiene

- Title each panel as the question it answers, such as "Is checkout p99 latency breaching target?".
- Set units, legends, null handling, and the expected data delay explicitly. A blank panel must not look
  healthy: distinguish no traffic, a failed query, and missing telemetry.
- Tie thresholds to an SLO or a documented operating limit. Avoid decorative red/amber/green bands.
- Use latency percentiles rather than averages and error ratios rather than raw error counts.
- Default to the useful incident window (usually the last 1–6 hours), the agreed timezone, and the same
  range across panels. Provide links that preserve time range and variables.

## Variables

- Use bounded variables such as `app`, `env`, `instance`, and `route` so one reviewed dashboard serves
  multiple services without unbounded queries.
- A data-source variable may switch between sources of the same type, such as production and non-production
  metrics. It cannot make a single panel portable between Wavefront/WQL and Splunk/SPL.
- Set a safe default and constrain multi-select or "All" values. Verify the expanded query's cardinality
  and target scope before review.

## Data sources — licence facts first

These facts are catalogue/licensing guidance, not proof that this installation is entitled. Confirm the
active licence and plugin allowlist with the Grafana administrator before provisioning either plugin.

- **Wavefront / VMware Aria Operations for Applications — `[sourced]` (reviewed 2026-07-14).** The
  [official plugin documentation](https://grafana.com/docs/plugins/grafana-wavefront-datasource/latest/)
  identifies `grafana-wavefront-datasource` as an **Enterprise** plugin. Its current requirements list
  Grafana Cloud Pro or Advanced; self-managed use requires an activated on-prem Grafana Enterprise
  licence. Keep WQL queries in Wavefront-backed panels.
- **Splunk — `[sourced]` (reviewed 2026-07-14).** The
  [official installation page](https://grafana.com/docs/plugins/grafana-splunk-datasource/latest/install/)
  identifies `grafana-splunk-datasource`. It is available with Grafana Cloud Pro or Advanced, or a
  self-managed Grafana Enterprise licence that includes the plugin; Cloud Free and Starter do not
  include it. Keep SPL in Splunk-backed panels.
- **ThousandEyes — `[sourced]` (reviewed 2026-07-14).** No named ThousandEyes Grafana
  data-source plugin was found in the official product documentation or Grafana catalogue, so do not
  invent a plugin type or UID. Cisco's
  [documented Grafana path](https://docs.thousandeyes.com/product-documentation/integration-guides/opentelemetry/observability-platforms/grafana)
  exports ThousandEyes OpenTelemetry signals to Grafana backends such as Prometheus/Mimir, Tempo, or
  Loki. Query metrics stored in Prometheus/Mimir with PromQL, not WQL; otherwise link to the ThousandEyes
  console. This is an inference from the named official integration path, not a claim that no other
  integration exists.

## As code

- Commit the dashboard JSON model with stable dashboard and data-source UIDs. Review query changes,
  target scope, units, thresholds, links, and failure/no-data behavior in a pull request.
- Prefer file provisioning or the approved Grafana 13 Git Sync workflow. Treat the UI as a preview and
  keep the repository as the source of truth; do not create an unreviewed snowflake dashboard.
- The repository's read-only Grafana MCP configuration is an optional inspection aid. It is not required
  to author, review, or provision a dashboard and must never carry credentials in tracked configuration.

Read only the reference needed for the task:

| Need | Reference |
|---|---|
| Dashboard provisioning, JSON models, UIDs, folders, or PR review | [Grafana 13 provisioning](./references/provisioning.md) |
| Existing Wavefront or Splunk dashboard inventory | [legacy data-source inventory](./references/wavefront-legacy.md) |

## Handoff

Hand the reviewed dashboard definition and target-validation gaps to the `sre-steward` agent. Include the
dashboard UID/folder, source path, target Grafana version, data-source UIDs, query and variable changes,
licence checks, screenshots or rendered evidence, and every remaining `[unverified]` item. If the work
uncovers active user impact or an unknown-cause incident, hand the time-bounded signal evidence to the
`sre` agent; do not diagnose it in this skill.
