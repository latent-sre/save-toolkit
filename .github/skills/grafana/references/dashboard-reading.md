# Read, explain, and review a dashboard

Resolve the UID through bounded search; read the model and relevant panel queries/data. Summaries
select panels, not health verdicts. Use [HTTP API & JSON model](./http-api.md#dashboard-model-and-edit-rules)
for schemas and [dashboard design](./dashboard-design.md) for design changes. Repository copies do
not authorize writes.

## Reading and interpreting panels

- Panel thresholds do not prove an alert rule exists or evaluates the same expression, and panel
  time overrides change the window a panel shows.
- The helper's `dashboard --uid <uid> --panel <id>` isolates a Classic or V2 panel with its dashboard
  version and variable/time context (`coverage: configuration_only`). Library panels and saved
  selections must be resolved against the actual view.
- Inspect per-query errors even under HTTP 200; `obs-analysis` owns rate, percentile and missing-data
  logic. The SRE helper queries only Prometheus and Loki; for another backend, return the missing read.
- Bind [visual verification](./visual-verification.md) to the same query window and variables.

## Sharing, access, and editor changes

Documented Viewer/Editor capabilities do not establish target permissions; confirm actual grants,
and prepare permission or role changes for the human under [access authority](../SKILL.md#access-and-authority).

- Snapshots embed queried data outside normal dashboard access: scrub them, set expiry, and treat
  sharing as data egress. Prefer an access-controlled live link with time range, `var-<name>`
  values and timezone.
- Inventory every library-panel consumer before editing: changes propagate to all consumers.
- A version-history restore is durable only for unmanaged dashboards. Provisioned or tool-managed
  resources must change through their owner or reconciliation replaces the UI/API edit.
- UI/API saves and restores follow the [API procedure](./http-api.md), including save messages,
  concurrency, and rollback checks.

## Read-only review and static hygiene

1. **Discover and sample.** Follow [API preflight](./http-api.md); inspect effective actions,
   including plugin grants, rather than inferring them from a Viewer role. Cap paginated search and
   record the datasource/schema/variable/layout sample.
2. **Check ownership and stored shape.** Read legacy metadata and the pinned app-platform model.
   `provisioned: true` (even with `canSave: true`) or `canSave: false` permits review, not an API
   edit. A recovery copy does not prove ownership; a converted read does not prove stored-schema
   migration.
3. **Run static hygiene offline** where the lane permits local execution. Invoke the installed
   [dashboard_hygiene.py](../scripts/dashboard_hygiene.py) (keep `grafana_read.py` beside it for V2
   mapping):

   ```text
   python "<absolute-installed-path>/dashboard_hygiene.py" dashboard.json --format json
   ```

   Text is the default. JSON carries `ok` (checked, not finding-free), `coverage`, `title`,
   `panel_count`, `findings` (`rule`, `where`, `detail`, `severity`), `query_analysis`, and `errors`.
   Severity is `advisory` (presentation/portability) or `review` (query/missing-target). Exit 0 means
   no review-required findings, 1 requires review, 2 means uncheckable (including `unsupported_v2`).
   Fixed UIDs are portability advice; `_total` is a name heuristic, not type evidence. For V2,
   `dashboard-linter` v0.5.2+ adds only basic checks (required fields, element references); full
   schema validation remains a recorded gap.
4. **Sample queries and presentation.** Exercise a bounded query sample (`POST /api/ds/query` with
   real variables, window, and step) and follow [visual verification](./visual-verification.md) where
   available. Do not save, import, restore, create snapshots/test resources, trigger alerts, or alter
   permissions during a review. Do not seek write grants just to finish a review.
5. **Classify findings** as confirmed defects, advisory improvements, or unverified heuristics before
   repair, and report counts by category. Saved queries are GA for Enterprise; confirm entitlement
   and grants before recommending them.
