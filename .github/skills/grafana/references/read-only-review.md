# Read-only Grafana review

Use this for an existing instance, a post-upgrade check, or testing the obs skills against real
dashboards. Bind the instance, organization, exact patch, selected dashboards, and UTC window.
Repository recovery copies do not change the requested read-only scope.

## Run the review

1. **Discover with reads.** Use the preflight GETs in [http-api](./http-api.md). Inspect effective
   permission actions, including plugin actions; a Viewer role name alone does not describe every
   grant. Keep credentials in memory and do not follow redirects carrying authorization.
2. **Inventory and sample.** Paginate dashboard search with a stated cap. Count what the token can
   see, then select dashboard models by relevant datasource, schema, variables, and layout. Record
   the sample; an inventory is not a query or visual test of every panel.
3. **Identify ownership and stored shape.** Read the legacy metadata and the pinned app-platform
   model. `provisioned: true` or `canSave: false` permits review but excludes an API edit. A recovery
   copy alone does not establish provisioning ownership. Preserve Classic/V1/V2 shapes; a converted
   read is not evidence that storage migrated.
4. **Check offline.** Run the bundled hygiene helper on a local export. Its fixed-UID findings are
   portability checks: on a provisioned target, resolve the UIDs before calling them broken. Its
   `_total` check is a name heuristic, not metric metadata; counts, presence checks, resets, and
   lifetime totals can be intentional. V2 is explicitly unsupported by this helper. Use a
   V2-capable validator on the actual V2 model or record that gap.
5. **Exercise a bounded query sample.** Use the matching signal skill and the real panel query,
   datasource, variables, absolute time window, step, and timeout. A read-only datasource query may
   use `POST /api/ds/query`; inspect its backend/query semantics before dispatch. Do not treat every
   POST as a write or every GET proxy path as safe. For PromQL, record any concrete replacement of
   Grafana macros; for LogQL, retain its own interval rules. HTTP 200 alone is insufficient: inspect
   result status, series/frames, and no-data behavior. Do not copy raw logs or trace payloads when
   counts and an access-controlled link suffice.
6. **Inspect presentation where available.** Follow [visual verification](./visual-verification.md)
   for browser inspection or a server-rendered image. Compare query and image scope, data, units,
   legends, variables, and missing-data presentation. A renderer flag is capability evidence;
   a false flag does not exclude browser inspection. Record the actual path and observations.
7. **Return evidence and proposed repairs.** Keep source findings, live observations, and unchecked
   claims distinct. Do not save, import, restore, create snapshots/test resources, trigger alerts,
   or alter permissions during this review. Write concurrency, rollback, alert firing/resolution,
   and notification delivery need separate evidence; read-only success does not establish them.

Classify each checker result before proposing a repair: confirmed query/model defect, portability
warning, presentation improvement, or unverified heuristic. Resolved fixed datasource UIDs in a
provisioned model are not broken references. Missing descriptions can be useful improvements
without blocking working queries. Report counts by category rather than calling every emitted
"violation" an operational failure. `canSave: true` does not override `provisioned: true` ownership.

## Grafana 13.2 checks

| Check | What to establish |
|---|---|
| Dashboard APIs | Discover served/preferred versions, then read the stored version. A 13.2.2 target served all six versions with preferred `v2` while sampled dashboards remained `v0alpha1`. `[verified: read-only target, 2026-09-19]` |
| History access | A 13.2.2 target returned 403 for legacy history but 200 with entries for the stable app-platform history query in `http-api`. Do not interpret 403 as no history or seek write grants just to finish a review. `[verified: same target/date]` |
| View panel sidebar | Public preview; inspect availability before relying on it. Viewers can explore visualization options without an edit grant. `[sourced: release notes, checked 2026-09-19]` |
| Plugins and saved queries | Record installed plugin versions separately from Grafana's version. Saved queries are GA for Enterprise/Cloud; discover entitlement and grants before recommending them. `[sourced: release notes, checked 2026-09-19]` |

Sources: [13.2 release notes](https://grafana.com/docs/grafana/latest/whatsnew/whats-new-in-v13-2/),
[panel inspection](https://grafana.com/docs/grafana/latest/panels-visualizations/panel-inspector/),
[Prometheus interval variables](https://grafana.com/docs/grafana/latest/datasources/prometheus/template-variables/).
Refresh after a Grafana/plugin upgrade, permission change, or conflicting target observation.
These target observations establish reads only; historical write probes are not 13.2 acceptance.
