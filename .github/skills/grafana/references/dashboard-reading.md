# Dashboard design, reading, review, and visual verification

Resolve the UID via bounded search, read the stored model and panel queries, and confirm live query
and visual evidence separately. Repository exports never authorize live writes, and summaries
select panels rather than proving service health. See [HTTP API](./http-api.md#dashboard-model-and-edit-rules)
for JSON schema details and [HTTP API change loop](./http-api.md#dashboard-change-loop) for writes.

## Reading and interpreting panels

- Fix **absolute time window**, **timezone**, and **template variables** before interpreting any
  panel (panel time overrides narrow or shift the dashboard window).
- Panel colors, thresholds, or titles (`"healthy"`) prove neither that an alert rule exists nor that
  users are healthy; from a stored model without live query data, mark health **unverified/unknown**.
- `grafana_read.py dashboard --uid <uid> --panel <id>` isolates a Classic or V2 panel (`coverage: configuration_only`); resolve library panels and saved views against the live dashboard. Inspect per-query errors even under HTTP 200 (`obs-analysis` owns rate, percentile, and missing-data logic; the SRE helper queries only Prometheus and Loki).

## Dashboard design

Design-only requests need no live access or change workflow (`observability-engineer` implements;
`stack-profile` owns stack choices, `obs-analysis` owns query/SLO semantics).

- Distinguish no traffic, zero, missing telemetry, and query failure; never fill an error ratio or
  numerator with `or vector(0)` or null-to-zero. For scrape presence, use
  `count(up{job="<job>"} == 1) or on() vector(0)` after confirming labels (native OTLP push has no
  `up`; Collector/Alloy Prometheus scrape forwarded over OTLP does).
- Preserve unrelated panels and published UIDs; leave Classic/V1 `timezone` unset (V2
  `timeSettings.timezone` defaults to `"browser"`, pick with the owner). Datasource variables switch
  only interchangeable same-type sources; Splunk (`grafana-splunk-datasource`) is Enterprise-only and
  needs confirmed edition, installed plugins (`GET /api/plugins`), and license entitlement. Load
  [alerting](./alerting.md) when design reaches Grafana routing/provisioning.

## Sharing, access, and editor changes

- **Roles & inheritance:** **Viewer** views dashboards/folders; **Editor** creates/edits within
  permitted folders; **Admin** manages org settings, datasources, and permissions. Confirm actual
  grants rather than inferring them from roles; dashboard permissions inherit from their **folder**
  (and moving folders alters inherited permissions).
- **Snapshots & library panels:** **Snapshots** embed queried data outside dashboard permissions
  (data-egress risk: scrub and set expiry, or share an access-controlled live link with window,
  `var-<name>`, and timezone). Inventory all consumers before editing a shared **library panel**.
- **Provisioned ownership:** Version-history restores endure only on unmanaged dashboards;
  **provisioned** or tool-managed dashboards (`provisioned: true`, even when `canSave: true`, or
  `canSave: false`) revert on reconciliation and must change in their **owning source**.

## Read-only review and static hygiene

1. **Discover & inspect ownership:** Run [HTTP API preflight](./http-api.md#preflight-api-families-and-stored-version)
   and check `meta.provisioned` / `meta.canSave` (or `grafana.app/managedBy`). Reviews stay
   read-only (`Apply repairs now: NO`); never create snapshots, restore, or request write grants.
2. **Offline hygiene:** Run stdlib-only [dashboard_hygiene.py](../scripts/dashboard_hygiene.py)
   (`python "<absolute-installed-path>/dashboard_hygiene.py" dashboard.json --format json`, with
   `grafana_read.py` beside it for V2 mapping; exit `0` = no review-required findings, `1` = review
   required, `2` = uncheckable/`unsupported_v2`). Resolved **fixed datasource UIDs** are an advisory
   **portability warning**, not a broken datasource; `_total` is a heuristic, not type evidence.
3. **Sample queries & visuals:** Exercise bounded `POST /api/ds/query` checks with real variables
   and classify defects, portability/advisory notes, and unverified heuristics by count.

## Visual verification

Query results, `rendererAvailable`, HTTP 200 PNG bytes, and **inspected images** are separate claims:
API or PNG success without viewing the rendered image leaves visuals **`UNVERIFIED`**.

| Access | Next step |
|---|---|
| Authorized browser session | `rendererAvailable=false` never blocks browser screenshots (`BROWSER_AVAILABLE`). Open URL on assigned HTTPS origin, freeze UTC window/variables, use only unsaved view controls (no `filename` arg in Playwright, never enter creds, never follow cross-origin links, never click save/silence/delete). |
| Server renderer available | **Grafana 13 removed the legacy renderer plugin** — use only the **standalone rendering service** (`STANDALONE_SERVICE`) with `renderer_token` JWT. SRE agent uses helper [`render`](./command-access.md#gcx-and-bundled-read-helper-rules); other agents use same-origin `GET /render/d-solo/<uid>/<slug>` (carry `orgId`, `tz`, `var-<name>`, absolute window, `scale=1`, `1200x600`, 45 s timeout, 8 MiB max, header auth). Wait/check dims: hit of `concurrent_render_request_limit` returns a **stock HTTP 200 placeholder PNG** (e.g., `526x202`) — reject dimension mismatches, login pages, or mismatched query/image windows or environments (`env=staging` image != `env=production` queries -> matched evidence `NO`). |
| Unusable / screenshot-only | Explain visible cues marking unverified window/vars/freshness; mark presentation `[unverified]`. |
