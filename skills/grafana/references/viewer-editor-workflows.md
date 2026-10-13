# Viewer and Editor workflows

Read this when helping someone consume or author dashboards without widening their organization role.
Confirm the deployed Grafana edition and permission model; documentation describes capabilities, not
the grants on this instance.

## Permission boundary

- Prefer a user/team grant on the one dashboard or folder over an organization-wide role increase.
  Dashboards inherit folder permissions.
- Permission and role changes use `production-change-gate` under the parent skill's
  [Access and authority](../SKILL.md#access-and-authority). Prepare the exact requested grant; the
  agent does not apply it.

## Sharing and evidence

- Prefer an access-controlled live link preserving the time range, `var-<name>` values, and timezone
  over a screenshot, which freezes data and can expose more than the recipient may query.
- A Grafana snapshot embeds queried data outside the dashboard's normal access path: scrub it, set
  an expiry, and treat sharing it as data egress.

## Editor changes

- Library panels propagate an edit to every consumer; inventory those consumers before changing one.
- Annotation writes are not part of the Grafana write exception: prepare them for the human owner.
- A restore from version history is durable only for an unmanaged dashboard. Provisioned or
  tool-managed resources must be changed through their owner or the next reconciliation will
  replace the UI/API edit.
- Every UI or API save is a real change. Use a meaningful save message; prefer the API path in
  [http-api](./http-api.md) when the work needs a reviewable diff, concurrency protection, query
  evidence, and a rollback.
