# Grafana dashboard and folder changes over the HTTP API

[Access authority](../SKILL.md#access-and-authority) governs all operations; reviews follow
[read-only review](./dashboard-reading.md#read-only-review-and-static-hygiene). Grafana 13 deprecates
`/api` in favour of `/apis` while serving both.

## Dashboard change loop

1. **Preflight & discover** ([preflight](#preflight-api-families-and-stored-version)); prove UID absence before create.
2. **Read & export** at the pinned stored version (`live.json`); stop if `meta.provisioned: true`,
   `meta.canSave: false`, or `grafana.app/managedBy` lacks `grafana.app/managerAllowsEdits: "true"`.
   Keep `uid`, drop numeric `id`, and strip app-platform `status`/`resourceVersion`/`generation`.
3. **Edit only the requested diff**, keeping unknown fields and stored version ([model rules](#dashboard-model-and-edit-rules)).
4. **Validate offline** via [dashboard_hygiene.py](../scripts/dashboard_hygiene.py) (`dashboard-linter`
   adds basic V2/query checks, not full V2 schema); check live baseline first and block only newly
   introduced defects.
5. **Show full `jq -S` diff & write once**; never retry conflicts with `overwrite: true`.
6. **Verify readback, queries, visuals, and version history**.

## Credentials and effective scope

Installed Grafana CLIs, SDKs, or MCP servers grant no authority unless `stack-profile` records them
(`sre-assistant` uses [command-access](./command-access.md)). Never use `grafana/mcp-grafana`
patch-mode `update_dashboard` on Classic/V1 (sends `overwrite: true`). Auth uses
`$GRAFANA_URL`/`$GRAFANA_SA_TOKEN` at call time; never log tokens. Check
`GET /api/access-control/user/permissions` and confirm folder-scoped read, write, and rollback
grants before creating (empty search without `dashboards:read` != empty instance).

## Preflight, API families, and stored version

- **App platform:** `/apis/dashboard.grafana.app/<ver>/namespaces/<ns>/dashboards` (create/list) and
  `.../dashboards/<uid>` (`<ns>` = `default` for org 1 or `org-<id>`; `metadata.name` = dashboard UID,
  distinct from minted `metadata.uid`). **Legacy:** `/api/dashboards/db`, `/api/dashboards/uid/<uid>`,
  `/api/dashboards/import`, `/api/folders`.
- **Stored-version trap (why V2 read shows empty panels):** Read URLs choose response conversion shape,
  not storage. Reading a Classic dashboard (`v0alpha1`/`v1`) via `v2` expects `elements`/`layout`
  instead of `panels` and can return empty panels (and browser saves under `dashboardNewLayouts`
  irreversibly convert Classic to `v2`).
- **Probe before every write:** Read unstructured at **`v0alpha1`**
  (`GET /apis/dashboard.grafana.app/v0alpha1/namespaces/<ns>/dashboards/<uid>`), inspect
  **`status.conversion.storedVersion`** (fallback `apiVersion`), and pin every read/write to that
  version. Never convert versions mid-edit (V2 -> V1 -> V2 flattens layout).
- **Preflight (once per target/upgrade):** `GET /api/health` (`enterpriseCommit` != plugin license),
  `/api/access-control/user/permissions`, `/api/org`, `/apis/dashboard.grafana.app/`,
  `/api/datasources`, `/api/frontend/settings`, `/api/search?type=dash-db&limit=100`. Never dump raw
  `/api/datasources` or `/api/frontend/settings` (contain secrets); project only needed keys.

## Dashboard model and edit rules

| Version | Spec shape & write behavior |
|---|---|
| `v0alpha1` | Classic unstructured (legacy `POST /api/dashboards/db` & `/import` store this; app-platform strips `uid`/`version`/`id`) |
| `v1`, `v1beta1` | Classic `schemaVersion` 42 (`v1beta1` reports `v1`; app-platform strips `spec.uid`/`version`, mints `metadata.uid`) |
| `v2alpha1`, `v2beta1`, `v2` | V2 `elements`, `layout`, `variables[]`, `cursorSync`, `timeSettings`; read live V2 instead of guessing |

**Classic panel shape:** Keep published `uid` (<=40 chars); set `id: null` on create; new panels need
unique numeric `id`, `"gridPos"`, explicit `"unit"` (e.g., `"s"`), `"noValue"`, thresholds, typed
variable datasource (`{"type": "prometheus", "uid": "${datasource}"}` or `${metrics_source}`), and
`$__rate_interval` rate queries (e.g., `histogram_quantile(0.99, sum by (le) (rate(<metric>_bucket{...}[$__rate_interval])))`).
Use `${var:regex}` for regex filters; keep `current` unpinned in portable exports. New-dashboard rules:
[dashboard design](./dashboard-reading.md#dashboard-design).

## Create, import, update, and folders

- **App-platform create:** `POST /apis/dashboard.grafana.app/<ver>/namespaces/<ns>/dashboards`
  (collection path) with **`metadata.name`** = UID, `grafana.app/folder`, `grafana.app/message`, and
  **omit** **`resourceVersion`** and **`generation`** (`201`).
- **Legacy create / import:** `POST /api/dashboards/db` (`dashboard.id: null`, `uid`, `folderUid`,
  `message`, **`overwrite: false`**, HTTP **`200`**). Use `POST /api/dashboards/import` (`inputs[]`)
  for `__inputs`/`${DS_*}`.
- **Update & concurrency:** App-platform `PUT` carries fresh `metadata.resourceVersion` (strip `status`;
  `409` on conflict); legacy `POST /api/dashboards/db` carries fresh `dashboard.version` +
  `overwrite: false` (`412 version-mismatch` = UID taken or stale; `400` = `id`/`uid` mismatch). On
  conflict, **fresh-read, re-diff, and reconcile** — never `overwrite: true`. Save messages must be
  supplied at write time and **cannot be added afterwards**. Folder changes alter permissions and need
  separate approval. On post-dispatch timeout/drop: `Write outcome: UNKNOWN`, `Replay safety: idempotent-by-target`,
  `Redispatch: BLOCKED_PENDING_RECONCILIATION`, reconcile via `READBACK_PLUS_VERSION_HISTORY`.
- **Folders (`folders:*`; depth default 4, cap 7):** Create via `POST /apis/folder.grafana.app/v1/namespaces/<ns>/folders`
  (`metadata.name`, `spec.title`, optional `grafana.app/folder`, omit `resourceVersion`, `201`);
  update via `GET` + `PUT .../folders/<uid>` with `resourceVersion` (no version history).

## Verify, history, and rollback

1. **Read back** into a fresh file (never over `live.json`), checking UID, folder, spec, and version/generation.
2. **Execute changed queries (`POST /api/ds/query`):** Check per-query statuses even under HTTP 200. For
   `$__rate_interval`/`$__interval`, pin panel cadence or substitute a concrete window (`>= 4x` scrape
   interval) matching the panel.
3. **Visual check & dimensions:** Follow [visual verification](./dashboard-reading.md#visual-verification);
   verify PNG dimensions match requested size (`1200x600`) to catch Grafana 13 stock placeholder images (`526x202`).
4. **Version history (including alpha-stored dashboards):** Query **only at stable `v1`**, never
   alpha/beta: `GET /apis/dashboard.grafana.app/v1/namespaces/<ns>/dashboards?labelSelector=grafana.app/get-history=true&fieldSelector=metadata.name=<uid>`
   (legacy `GET /api/dashboards/uid/<uid>/versions?limit=20`).
5. **Rollback:** Confirm fresh read matches operation-written state before overwriting with `live.json`
   spec + fresh concurrency token (Grafana keeps 20 versions by default).
