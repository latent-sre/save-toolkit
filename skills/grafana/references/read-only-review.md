# Read-only Grafana review

Bind the instance/org, exact patch, selected dashboards and UTC window. Repository copies do not
authorize writes.

## Run the review

1. **Discover with reads.** Follow [API preflight](./http-api.md); inspect effective actions, including
   plugin grants, rather than inferring them from a Viewer role. Use existing credentials; no redirects.
2. **Inventory and sample.** Cap paginated search and record the datasource/schema/variable/layout
   sample. Visible inventory is not complete query or visual coverage.
3. **Identify ownership and stored shape.** Read legacy metadata and the pinned app-platform model.
   `provisioned: true` or `canSave: false` permits review, not an API edit. A recovery copy does not
   prove ownership; a converted read does not prove stored-schema migration.
4. **Check offline.** Run the bundled hygiene helper on a local export when the lane permits it.
   For `sre-assistant`, use the installed [workflow](./investigation-workflows.md#agent-collection-and-follow-up)
   analysis on an eligible named capture; otherwise report it not run. Direct standalone execution
   stays denied. Fixed UIDs are portability advice; `_total` is a name heuristic, not type evidence
   (presence, counts, resets and lifetime totals may be intentional). For V2, use a V2-capable validator
   on the actual model or record the gap.
5. **Exercise a bounded query sample.** Use the matching signal skill and the real panel query,
   datasource, variables, absolute time window, step, and timeout. A read-only datasource query may
   use `POST /api/ds/query`; inspect its backend/query semantics before dispatch. Do not treat every
   POST as a write or every GET proxy path as safe. For PromQL, record any concrete replacement of
   Grafana macros; for LogQL, retain its own interval rules. HTTP 200 alone is insufficient: inspect
   result status, series/frames, and no-data behavior. Prefer counts and protected links to payloads.
6. **Inspect presentation where available.** Follow [visual verification](./visual-verification.md)
   at matching query/image scope. A renderer flag is capability evidence, not inspection;
   false does not exclude browser access.
7. **Return evidence and proposed repairs.** Keep source findings, live observations, and unchecked
   claims distinct. Do not save, import, restore, create snapshots/test resources, trigger alerts,
   or alter permissions during this review. Write concurrency, rollback, alert firing/resolution,
   and notification delivery need separate evidence; read-only success does not establish them.

Classify findings as confirmed defects, advisory improvements or unverified heuristics before repair;
query/missing-target findings are not automatic rewrites. Report counts by category.
`canSave: true` does not override `provisioned: true` ownership.

For guarded named-capture analysis, use the managed workflow in the project environment:

```text
python -I "<absolute-installed-path>/grafana_workflow.py" analyze --source-id capture-one --analysis hygiene --agent-json
```

Replace `capture-one` with the eligible capture ID; unavailable/unsupported input is a gap, not clean.

For unguarded automation on a local export, invoke the installed checker with `--format json`.
Keep its bundled Python helpers beside it when installing or relocating the skill.

```text
python "<absolute-installed-path>/dashboard_hygiene.py" dashboard.json --format json
```

Text is the default. JSON carries `ok` (checked, not finding-free), `coverage`, `title`, `panel_count`,
`findings` (`rule`, `where`, `detail`, `severity`), `query_analysis` and `errors`. Severity is `advisory`
for presentation/portability or `review` for query/missing-target checks. Exit 0 means no review-required
findings (advisories allowed), 1 requires review, 2 means uncheckable. `--quiet` retains all JSON findings.

Query analysis distinguishes bounded PromQL parsing, text heuristics for unresolved templates or
missing parsers, and `not_checked` for exceeded limits. Inspect gaps even with no findings. The report
establishes static hygiene only, not schema/query/render validation or health; V2 remains unsupported.

## Grafana 13.2 checks

| Check | What to establish |
|---|---|
| Dashboard APIs | Discover served/preferred versions, then read the stored version. A 13.2.2 target served all six versions with preferred `v2` while sampled dashboards remained `v0alpha1`. |
| History access | A 13.2.2 target returned 403 for legacy history but 200 with entries for the stable app-platform history query in `http-api`. Do not interpret 403 as no history or seek write grants just to finish a review. |
| View panel sidebar | Public preview; inspect availability before relying on it. Viewers can explore visualization options without an edit grant. |
| Plugins and saved queries | Record installed plugin versions separately from Grafana's version. Saved queries are GA for Enterprise/Cloud; discover entitlement and grants before recommending them. |
