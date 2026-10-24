# Read and explain a dashboard

Resolve the UID through bounded search; read the model and relevant panel queries/data. Summaries
select panels, not health verdicts. Use [JSON model](./json-model.md) for schemas,
[read-only review](./read-only-review.md) for structural checks and [dashboard design](./dashboard-design.md)
for design changes.

- Bind observations to an absolute window/timezone, variables, datasource UIDs, refresh time, and
  panel time overrides; compare equivalent windows.
- Green colors and titles do not prove health; panel thresholds do not prove an alert rule exists
  or evaluates the same expression.
- The helper's `dashboard --uid <uid> --panel <id>` isolates a Classic panel with its dashboard
  version and variable/time context. This is stored configuration: expand library-panel dependencies
  through available reads and resolve saved selections against the actual view.
- Inspect per-query errors even under HTTP 200. Use signal skills for rate, percentile and
  missing-data logic. The SRE helper permits bounded Prometheus/Loki query POSTs; other backends
  require returning the missing read, never bypassing the restriction.
- Bind [visual verification](./visual-verification.md) to the same query window/variables. A
  screenshot supports a visual observation, not the underlying query, aggregation, or cause.
- With only a model, explain what it measures and mark current health unverified. Return observations
  and panel links preserving time/variables; deployment correlation is not causation.

## Sharing, access, and editor changes

Confirm actual grants; documented Viewer/Editor capabilities do not establish target permissions.

- Prefer a user/team grant on one dashboard or folder over a wider organization role; dashboards
  inherit folder permissions. Prepare exact permission/role changes for the human under
  `production-change-gate` and [access authority](../SKILL.md#access-and-authority); never apply them.
- Prefer an access-controlled live link preserving time range, `var-<name>` values and timezone.
  Screenshots freeze data and may expose more than the recipient can query. Snapshots embed queried
  data outside normal dashboard access: scrub them, set expiry, and treat sharing as data egress.
- Inventory every library-panel consumer before editing: changes propagate to all consumers.
  Annotation writes are outside the Grafana exception; prepare them for the human owner.
- A version-history restore is durable only for unmanaged dashboards. Provisioned or tool-managed
  resources must change through their owner or reconciliation replaces the UI/API edit.
- UI/API saves and restores follow the [API procedure](./http-api.md), including save messages,
  concurrency and rollback checks.
