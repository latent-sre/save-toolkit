# Grafana dashboard and folder changes over the HTTP API

The parent's [authority rules](../SKILL.md#access-and-authority) govern every operation.
`stack-profile` owns version and recovery-copy facts; reviews use
[read-only checks](./dashboard-reading.md#read-only-review-and-static-hygiene) without the edit
loop. Grafana 13 deprecates `/api` in favour of `/apis` but still serves both. Scripted dashboards
are disabled by default and removed in Grafana 14; until then Grafana shows a disabled notice, and
the `disableScriptedDashboards` feature toggle set to `false` temporarily restores them.

## Dashboard change loop

1. **Preflight and discover; never invent.** Run [preflight](#preflight-once-per-target-and-after-every-upgrade).
   Prove a create's UID is absent; resolve names, labels, and UIDs from the target.
2. **Read and export before editing** at the stored version ([read and export](#read-and-export)).
   For a create, choose a stable UID and name the human or protected executor who owns removal.
3. **Make only the requested change.** Preserve unknown fields and the stored schema
   ([model and edit rules](#dashboard-model-and-edit-rules)).
4. **Validate** with [pre-write checks](#check-before-writing).
5. **Show the target and full diff, then write once** ([create, import, update](#create-import-update)).
6. **Verify behavior, storage, and history** ([verify, then record](#verify-then-record)).

## Credentials and effective scope

`stack-profile` records any adopted Grafana CLI, MCP server, vendor skill package, or SDK; an
installed or selected tool grants no new commands or write authority until adopted there. The SRE
assistant's admitted read path is the [command-access](./command-access.md) helper. If
`grafana/mcp-grafana` is present, never use its patch-mode `update_dashboard` for a live
Classic/V1 write: it saves with `overwrite: true`, defeating concurrency checks (its V2 writes carry
`resourceVersion`).

Read `$GRAFANA_URL`/`$GRAFANA_SA_TOKEN` at call time; never use `curl -v` (echoes Authorization).
Check `GET /api/access-control/user/permissions` before trusting search or writing:
- Empty search without `dashboards:read` does not establish an empty instance.
- Create grants do not guarantee readback or rollback, and legacy vs app-platform grants can differ.
  Establish folder-scoped rights before creating; never create what the caller cannot verify or roll back.

## Two API families, one stored version

| Family | Path | Use |
|---|---|---|
| App platform | `/apis/dashboard.grafana.app/<version>/namespaces/<ns>/dashboards` (create/list); `…/dashboards/<uid>` (read/update/delete) | version-pinned; stable-version history |
| Legacy | `/api/dashboards/*`, `/api/search`, `/api/folders`, `/api/datasources` | discovery and Classic fallback after checking grants |

Namespace is `default` for org 1, `org-<id>` otherwise. App-platform identity is `metadata.name`
(the dashboard UID), not the server-minted `metadata.uid`.

The read URL selects response shape, not storage: a Grafana 13 target can prefer `v2` and return a
stored Classic dashboard as V2 `elements` or V1 `panels`, and dynamic dashboards
(`dashboardNewLayouts`, GA and on by default in Grafana 13) make a browser save convert Classic
irreversibly to `v2`. Probe immediately before every write:

1. Read at `v0alpha1` (unstructured, no migration); take `status.conversion.storedVersion` (falling
   back to returned `apiVersion`).
2. Extract the segment after the last `/` (e.g., `v0alpha1` from `dashboard.grafana.app/v0alpha1`).
3. Pin every read/write to that version; stop if the probe and pinned read disagree.

## Preflight, once per target and after every upgrade

Run: `GET /api/health` (`enterpriseCommit` is not plugin entitlement),
`GET /api/access-control/user/permissions`, `GET /api/org`, `GET /apis/dashboard.grafana.app/`,
`GET /api/datasources`, `GET /api/frontend/settings`, and `GET /api/search?type=dash-db&limit=100`.
Never print `/api/datasources` or `/api/frontend/settings` raw — they can carry connection users and
decrypted basic-auth credentials; project only needed fields (`uid`, `name`, `type`,
`rendererAvailable`, `buildInfo`).

## Read and export

Save the pinned stored shape into `live.json` as the pre-change export. Stop (must change in owning
source) when legacy `GET /api/dashboards/uid/<uid>` reports `meta.canSave: false` or
`meta.provisioned: true`, or app-platform `grafana.app/managedBy` is set without
`grafana.app/managerAllowsEdits: "true"`. Portable Classic exports keep `uid`, drop numeric `id`,
and strip app-platform `status`, `resourceVersion`, and `generation`.

## Dashboard model and edit rules

These shapes describe Grafana 13.3.0. New-dashboard choices are in
[dashboard design](./dashboard-design.md#new-dashboard-conventions).

| Version | Spec shape | Write behavior |
|---|---|---|
| `v0alpha1` | Classic, unstructured | no migration or validation; admission strips `uid`, `version`, and `id` from spec |
| `v1`, `v1beta1` | Classic | migrates to final V1 `schemaVersion` 42 and validates; `v1beta1` reports `v1` |
| `v2alpha1`, `v2beta1`, `v2` | V2 `elements` and `layout` | validates; no `schemaVersion`; restructures datasource refs and transformations |

- **Storage and conversion:** `preferredVersion` is config, not stored-shape evidence. Legacy
  `POST /api/dashboards/db` and `/import` store `v0alpha1`; UI import stores Classic as `v1` and V2
  as `v2`; app-platform writes store the path version. Never change API versions during a surgical
  edit (V2 → V1 → V2 is lossy: rows, tabs, and layouts flatten). `conversion.failed: false` is not
  fidelity, and legacy `meta.apiVersion` reports the requested version, not storage.
- **Classic / V1 edits:** Preserve published `uid` values (never rename/reuse; legacy max 40 chars).
  `id` is `null` on create; keep `schemaVersion`; `version` is the legacy concurrency token. New
  panels need unused IDs (link/render targets), standard `gridPos`, explicit `unit`, `noValue`,
  and typed panel + target `datasource` references (prefer `${datasource}` or separately typed
  variables such as `${metrics_source}` / `${logs_source}`). On app-platform V1 writes, Grafana
  strips `spec.uid`/`spec.version` and mints `metadata.uid` — diff the stored readback.
- **V2 differences:** Panels are `spec.elements.<name>` positioned by `spec.layout` (`GridLayout`,
  `RowsLayout`, `AutoGridLayout`, `TabsLayout`); variables are `spec.variables[]`; `graphTooltip` →
  `cursorSync`; time/timezone/refresh live under `timeSettings`; conditional rendering is V2-only.
  Do not author V2 internals from memory — read a real V2 dashboard at its stored version.
- **Variables and portability:** Use `${var:regex}` for regex matchers (custom All values like `.+`
  are not escaped and can expand large). Leave `current` unpinned in portable exports.
  `increase(...[$__range])` can deliberately total the selected window; otherwise use
  `$__rate_interval` on rate/irate/increase.

## Check before writing

Run the bundled stdlib-only [dashboard_hygiene.py](../scripts/dashboard_hygiene.py) (`python
"<resolved helper path>" <file>`; see
[dashboard reading and review](./dashboard-reading.md#read-only-review-and-static-hygiene) for
output format and exit codes). It maps V2 onto Classic for static checks without validating the V2
schema itself; `dashboard-linter` v0.5.2+, when installed, adds PromQL/LogQL rules and basic V2
checks (required fields, element references), not full V2 schema validation. On an
edit, check the live model first and block only confirmed defects this diff introduces.

## Create, import, update

- **Create:** App platform `POST …/namespaces/<ns>/dashboards` (collection path, never item path)
  with pinned `apiVersion`, `metadata.name` = chosen UID, `grafana.app/folder`, `grafana.app/message`,
  and no `resourceVersion`/`generation` (`201`). Legacy `POST /api/dashboards/db` with `id: null`,
  `folderUid`, `message`, `overwrite: false` (`200`). `412 version-mismatch` = UID already taken
  (or a stale version), `400` = `id` and `uid` name different dashboards; stop and reconcile, never
  switch to `overwrite: true`. Name the human/protected recovery owner before dispatch.
- **Import:** Use `POST /api/dashboards/import` (`overwrite: false`, `folderUid`, `inputs[]`) to
  bind `__inputs` and `${DS_*}` placeholders; raw `POST /api/dashboards/db` leaves broken literal
  placeholders.
- **Update:** Show `jq -S` diff, then write once with the fresh concurrency token and a save message
  naming the change (cannot be added later). Changing folder (`folderUid` / `grafana.app/folder`)
  changes inherited permissions and requires separate authorization.

| Family | Token | Stale response |
|---|---|---|
| App-platform `PUT` | `metadata.resourceVersion` (strip `status` first) | `409 Conflict` |
| Legacy `POST /api/dashboards/db` | `dashboard.version`, `overwrite: false` | `412 version-mismatch` (UID taken or stale); `400` when `id` and `uid` disagree |

On conflict, fresh-read, re-diff, and reconcile; never bypass with `overwrite: true`. On timeout or
dropped response after dispatch, follow the parent's [UNKNOWN rule](../SKILL.md#return-the-result)
and reconcile via fresh readback plus version history before any redispatch.

## Folder create and update

Requires `folders:create` / `folders:write` / `folders:read` (`max_nested_folder_depth` default 4,
hard cap 7). **Create:** `POST /apis/folder.grafana.app/v1/namespaces/<ns>/folders` with stable
`metadata.name`, optional `grafana.app/folder` parent, `spec.title`, and no `resourceVersion`
(`201`; `409` = exists, stop). **Update:** `GET` then `PUT …/folders/<uid>` with current
`resourceVersion` and existing parent (moving a folder changes inherited permissions and is out of
scope; `409`/`412` = stop and re-diff). Folders have no version history or save message: verify via
fresh UID readback (and parent listing on UNKNOWN). Deletion is outside the dashboard write rule.

## Verify, then record

1. **Read back** into a new file (never over `live.json`); compare UID, folder, spec, and new
   `version`/`generation`. Retain this as the verified operation-written state.
2. **Run each changed query** via `POST /api/ds/query` with real variables and window. For
   Prometheus macros (`$__interval`, `$__rate_interval`, `$__range`), supply the panel's interval
   context or concrete window (at least 4 scrape intervals for `$__rate_interval`) and report what
   was used. Inspect per-query status (HTTP 200 alone is insufficient). For expected-empty panels,
   check source/window coverage or mark positive-data behavior `[unverified]`.
3. **Visual check:** follow [visual verification](./visual-verification.md) via browser or server
   render; if unavailable, label presentation `[unverified]`.
4. **Confirm save message in version history:** App-platform history is served only at an enabled
   stable version such as `v1` (never alpha/beta):
   `GET /apis/dashboard.grafana.app/v1/namespaces/<ns>/dashboards?labelSelector=grafana.app/get-history=true&fieldSelector=metadata.name=<uid>`,
   or the deprecated legacy `GET /api/dashboards/uid/<uid>/versions?limit=20` (requires `dashboards:write`; 403
   does not prove absence of versions).

## Rollback

Never replay `live.json` with its stale token. Compare a fresh live read against the verified
operation-written state first; stop and hand off on any intervening edit (a fresh token alone does
not authorize overwriting another editor's work). Once confirmed, place the saved spec into the
current envelope, drop `status`, and update with the fresh concurrency token (legacy: fresh
`dashboard.version`). Provisioned/tool-managed rollback belongs to its owner. Grafana keeps 20
versions by default.
