# Grafana dashboard and folder changes over the HTTP API

The parent's [authority rules](../SKILL.md#access-and-authority) govern every operation.
`stack-profile` owns version and recovery-copy facts: a backup proves neither provisioning ownership
nor tested rollback. Reviews use [read-only checks](./read-only-review.md) without the edit loop or
test resources. Target create/update/import, conflict and recovery behavior remains unconfirmed
until observed. Grafana 13 deprecates `/api`, including the legacy dashboard writes, in favour of
`/apis` but still serves both. Scripted dashboards are disabled by default and removed in Grafana
14: migrate them; re-enabling is an owner decision. Their 410 comes from the frontend, so API
clients never receive it.

## Dashboard change loop

1. **Preflight and discover; never invent.** Run the [preflight](#preflight-once-per-target-and-after-every-upgrade).
   Prove a create's uid is absent and stop on collisions. Resolve names, labels and UIDs from the target.
2. **Read and export before editing** at the stored version ([read and export](#read-and-export)).
   A create has no prior model or token: choose its stable uid, name the human or protected
   executor who owns recovery if removal is needed, and author only the requested model.
3. **Make only the requested change.** Preserve unknown fields and the stored schema;
   the [model and edit rules](#dashboard-model-and-edit-rules) cover Classic/V1/V2 shapes,
   variables and panels.
4. **Validate** with the [pre-write checks](#check-before-writing).
5. **Show the target and full diff, then write once** ([create, import, update](#create-import-update)).
6. **Verify behavior, storage and the durable record** ([verify, then record](#verify-then-record));
   report unavailable evidence, never an inspection that did not happen.

Folder create/update uses the [folder procedure](#folder-create-and-update) under the same
authority, preflight, validation and evidence rules; dashboard history and save-message rules do
not apply.

## Credentials and effective scope

`stack-profile` records any adopted Grafana CLI, MCP server, vendor skill package or SDK; an
installed or selected tool grants no new commands or write authority until it is adopted there.
The SRE assistant's admitted read path is the [command-access](./command-access.md) helper.
If `grafana/mcp-grafana` is present, never
use its patch-mode `update_dashboard` for a live write: for Classic/v1 dashboards it saves with
`overwrite: true`, defeating the concurrency rule (its V2 writes carry `resourceVersion`). For
renderer/browser capability use [visual verification](./visual-verification.md).

Read `$GRAFANA_URL`/`$GRAFANA_SA_TOKEN` at call time; never use `curl -v`, which echoes the
Authorization header. Read `GET /api/access-control/user/permissions` before trusting search or
writing:

- Empty search without `dashboards:read` does not establish an empty instance.
- Do not assume a create grant also permits readback or rollback, or that the two API families
  grant the creator identical access. Establish the required folder-scoped rights before an
  authorized create. Never create what the caller cannot verify or roll back; a review needs no
  create or write grant.

## Two API families, one stored version

| Family | Path | Use |
|---|---|---|
| App platform | `/apis/dashboard.grafana.app/<version>/namespaces/<ns>/dashboards` for create and list; `…/dashboards/<uid>` for read, update, delete | version-pinned; stable-version history |
| Legacy | `/api/dashboards/*`, `/api/search`, `/api/folders`, `/api/datasources` | discovery and Classic fallback after checking the target's grants |

The namespace is `default` for org 1, `org-<id>` otherwise.
App-platform identity is `metadata.name` (the dashboard uid), not the server-minted `metadata.uid`.
On an app-platform 404, verify uid, version, and served APIs before falling back to legacy.

The read URL selects response shape, not storage. One observed 13.2.2 target served six versions,
preferred `v2`, and returned stored Classic as V2 `elements` or V1 `panels`, so an unpinned Classic
transform can see no panels. Never assume v1: probe again immediately before every write. In
Grafana 13, dynamic dashboards (`dashboardNewLayouts`, GA and on by default) make a browser save
of a Classic dashboard convert it irreversibly to `v2`; a Classic browser save stores `v1` only
where that feature is off.

1. Read at `v0alpha1` (unstructured, no migration). Take `status.conversion.storedVersion`,
   falling back to the returned `apiVersion`.
2. Extract the segment after the last slash from a group-qualified value such as
   `dashboard.grafana.app/v0alpha1`; use only that segment in the versioned URL.
3. Pin every read/write to that version. If the probe and pinned read disagree, stop before
   diffing or writing.

## Preflight, once per target and after every upgrade

`GET /api/health` (version and edition; `enterpriseCommit` is not plugin entitlement),
`GET /api/access-control/user/permissions`, `GET /api/org` (hence the namespace),
`GET /apis/dashboard.grafana.app/` (served and preferred versions), `GET /api/datasources` (names,
types, uids), `GET /api/frontend/settings` (renderer availability and feature toggles), and
`GET /api/search?type=dash-db&limit=100` cross-checked against the permissions read. Identifiers come
from these responses, never from another instance or from memory. Never print `/api/datasources` or
`/api/frontend/settings` raw: datasource entries carry connection users and databases, and frontend
settings carries decrypted basic-auth credentials for direct-access datasources. Project the named
fields (uid, name, type; `rendererAvailable`, `buildInfo`) before output.

## Read and export

Read the stored shape at the pinned version into `live.json` and keep it as the pre-change export.
Stop, because the owning source must change and no API write is durable, when the legacy DTO
`GET /api/dashboards/uid/<uid>` reports `meta.canSave: false` or `meta.provisioned: true`, or when
the app-platform object's `grafana.app/managedBy` annotation names a manager (`grafana.app/managerId`
identifies it) without `grafana.app/managerAllowsEdits: "true"`. A portable Classic export
keeps the stable uid, drops the numeric id, and strips app-platform `status`, `resourceVersion`,
and `generation`; instance URLs and folder or data-source uids leave only under a separate
authorization.

## Dashboard model and edit rules

These shapes describe Grafana 13.3.0 source/docs. New-dashboard choices are in
[dashboard design](./dashboard-design.md#new-dashboard-conventions).

### Six served versions, three shapes

| Version | Spec shape | Write behavior |
|---|---|---|
| `v0alpha1` | Classic, unstructured | no migration or validation; admission strips `uid`, `version` and `id` from the spec |
| `v1`, `v1beta1` | Classic | migrates to final V1 `schemaVersion` 42 and validates; `v1beta1` reports `v1` |
| `v2alpha1`, `v2beta1`, `v2` | V2 `elements` and `layout` | validates; no `schemaVersion`; later versions restructure data-source references and transformations |

`preferredVersion` is configuration, not stability or stored-shape evidence.

### Storage and conversion rules

A row keeps the version of its write. Legacy `POST /api/dashboards/db` and
`POST /api/dashboards/import` store `v0alpha1`. The UI import page stores Classic JSON as `v1` and
a V2 resource as `v2`. An app-platform write stores the version named in its path.

1. **Never change API versions during a surgical edit.** A converted body written at another
   version rewrites the row's stored schema, and V2 → V1 → V2 is lossy: rows, tabs, and layout kinds
   flatten into Classic panels and cannot be reconstructed.
2. **`conversion.failed: false` is not fidelity.** A conversion error can still answer 200. Compare
   source and converted structures; Grafana also emits conversion-loss metrics.
3. **Legacy `meta.apiVersion` is not storage evidence.** It reports the requested version. On a
   failed conversion the legacy GET reports `storedVersion` and returns the unconverted source body.

### Classic / V1 edits

- Preserve published `uid` values, including existing IDs shorter than eight characters; never
  reuse or rename them during an edit. The legacy validator limits length to 40 and permits letters,
  digits, hyphens and underscores; validate new IDs against the selected API's name rules.
  `id` is `null` on create and dropped from portable exports; `schemaVersion` stays at the exported value;
  `version` is the legacy concurrency token.
- A new panel needs an unused ID: panel IDs are link and render targets, and duplicates can retarget consumers.
- On app-platform V1 writes, Grafana strips `spec.uid` and `spec.version`, injects defaults, and mints a distinct
  `metadata.uid`. Diff the stored readback, not the local body.
- Keep both panel and query-target `datasource` references typed and bound to the intended source.

### V2 differences

Panels are `spec.elements.<name>` resources positioned by `spec.layout` (`GridLayout`,
`RowsLayout`, `AutoGridLayout`, `TabsLayout`); variables are typed `spec.variables[]`;
`graphTooltip` becomes `cursorSync`; time, timezone, and refresh live under `timeSettings`;
conditional rendering is V2-only and applies to auto-grid items, rows and tabs. Do not author V2
element or query internals from memory: read a real V2 dashboard at its stored version, or use an
adopted typed SDK, and preserve that shape.

### Variables and portability

- A data-source variable cannot translate query languages: mixed-backend dashboards need separately
  typed variables (for example `${metrics_source}` and `${logs_source}`) in corresponding panels and
  targets. Set each variable's plugin type and resolve it to a discovered source; scope selection
  when several sources share that type. For portable exports, leave `current` unpinned and verify
  selected sources after import; do not assume a saved concrete uid resolves to the intended source
  on another instance.
- Regex matchers use `${var:regex}`; a custom All value such as `.+` is not escaped, works only
  where the query language takes a regex, and the generated expansion can grow large.
- `increase(...[$__range])` can deliberately total the selected dashboard window; preserve
  fixed-horizon intent when justified by scrape cadence.

## Check before writing

`dashboard_hygiene.py` is bundled, stdlib-only, and offline; it accepts a bare Classic/V1 or V2
model, an app-platform wrapper, or a legacy GET body. Resolve the installed
[hygiene helper](../scripts/dashboard_hygiene.py) to its absolute path and run
`python "<resolved helper path>" <file>`. It
checks a V2 candidate by mapping its elements and grid, row, tab and auto-grid layouts onto the
Classic panel shape; it never validates the V2 schema itself. Check the actual V2 candidate, never a converted
V1 substitute, and use `dashboard-linter` v0.5.2+ for V2 schema validation; if the candidate cannot
be checked, report the gap and stop before writing. `dashboard-linter lint --strict`, when installed,
validates more of the real Grafana, PromQL, and LogQL contract; scoped exclusions need a reason.
PromQL heuristics require a datasource reference typed `prometheus`; untyped references remain
unchecked for query semantics. Treat fixed-UID and counter-name findings as review prompts as
explained in [read-only review](./read-only-review.md). On an edit, check the live model first and
block only confirmed defects this diff introduces; report pre-existing findings without expanding
scope. Presentation and portability advice does not block a write. A clean result never proves
target permissions, query data, rendering, concurrency, or the durable save record; the
[change loop](#dashboard-change-loop) covers those.

## Create, import, update

**Create** is a live change with the same evidence duty as an update. App platform: `POST` the
envelope to the collection path, `…/namespaces/<ns>/dashboards`, never to the `<uid>` item path,
with `apiVersion` set to the pinned `dashboard.grafana.app/<version>`, `metadata.name` set to a
stable uid accepted by the selected API, the folder in the `grafana.app/folder` annotation, the change reference
in `grafana.app/message`, and no `metadata.resourceVersion` or `generation` (those are the server's
concurrency fields, absent on a create); success is 201. Legacy: `POST /api/dashboards/db` with `id: null`, `folderUid`, `message`, and
`overwrite: false`; success is 200. A 409 means the uid is taken: stop and
reconcile, never switch to `overwrite: true`. Before dispatch, name the human or protected executor
who owns recovery if removal is needed: a create has no prior dashboard version to restore, and
this lane has no deletion authority.

**Import** is the only path that binds `__inputs` and `${DS_*}` placeholders, which a
cross-instance export writes alongside `__requires`, to this instance's data
sources (`POST /api/dashboards/import` with `overwrite: false`, `folderUid`, and an `inputs[]`
binding; the import UI also resolves them). Raw `POST /api/dashboards/db` stores the literal placeholder and produces a
missing-data-source panel. Verify the imported datasource bindings against the actual target;
correct an unresolved binding through the scoped update procedure.

**Update** shows a stable diff (`jq -S` both specs), then writes once with the family's fresh
concurrency token and a save message naming the change, which cannot be added later. Changing a
dashboard's folder (`folderUid` or `grafana.app/folder`) changes its inherited permissions like a
folder move: flag it in the diff and treat it as that separately authorized change.

| Family | Token | Stale response |
|---|---|---|
| App-platform `PUT` | `metadata.resourceVersion`; strip `status` first | 409 `Conflict` |
| Legacy `POST /api/dashboards/db` | `dashboard.version` from the read just made, `overwrite: false` | 409 with the same "already exists" message as a taken uid, or 412 `version-mismatch`; handle both |

On a conflict, fresh-read, re-diff and reconcile before any retry; never bypass it with
`overwrite: true`. The same uid and byte-identical model do not make redispatch safe or
history-free. A timeout, dropped response or caller crash after dispatch is UNKNOWN under the
parent's [result rule](../SKILL.md#return-the-result): before any redispatch, reconcile fresh
readback plus version history. Matching history attributes execution; desired bytes alone establish
current state; prior bytes with no matching history cannot prove non-execution while a request could
still land.

## Folder create and update

Read folder permissions and namespace: create needs `folders:create`, update
needs `folders:write`, and target checks and readback need `folders:read`. A nested folder needs
the parent-specific grant and is limited by `max_nested_folder_depth` (default 4, hard cap 7).
Dashboard lifecycle evidence does not verify folders.

- **Create:** list or read the proposed uid and inspect the intended parent for a title collision.
  `POST /apis/folder.grafana.app/v1/namespaces/<ns>/folders` takes a chosen stable `metadata.name`,
  optional `grafana.app/folder` parent annotation, and `spec.title`, with no
  `metadata.resourceVersion`. `201` creates; `409` means the uid exists, so stop and reconcile
  rather than delete or overwrite. Name the recovery owner before dispatch, as for a dashboard create.
- **Update:** `GET …/folders/<uid>` first; `PUT …/folders/<uid>` uses that same `metadata.name`,
  current `metadata.resourceVersion`, the existing parent annotation, and `spec.title`. Moving a
  folder can change inherited access, so it needs a separately authorized path. `404` is an absent
  target; `409` or `412 version-mismatch` is a concurrent update: stop, fresh-read, and re-diff; do
  not force. Keep the pre-change fields as rollback content and restore them under
  [rollback](#rollback), comparing title and parent too.
- **Outcome:** folder writes have no version history or save message. Preserve the write receipt,
  then fresh-read the uid: it must match the intended uid, title, parent, and current returned
  resource version. A post-dispatch UNKNOWN is reconciled by fresh uid readback plus the
  intended-parent listing; matching state cannot be attributed to the unanswered dispatch, so
  retain UNKNOWN and name a reconciliation owner. Deletion is outside the dashboard write rule.

## Verify, then record

1. Read back into a new file, never over `live.json`; compare uid, folder, spec, and the new
   `version` or `generation`. Keep it as the verified operation-written state.
2. Run each changed query through `POST /api/ds/query` with real variable values and the
   dashboard's window. The Prometheus backend expands `$__interval`, `$__rate_interval` and
   `$__range` server-side from the request's `intervalMs`, range and the datasource scrape
   interval, so the value can differ from the panel's: send the panel's interval context or
   substitute its concrete window (for `$__rate_interval`, at least four scrape intervals), and
   report what verification used.
   Inspect per-query success and expected results; HTTP 200 alone proves neither. For an expected
   empty result, such as an error-only log panel during a quiet window, check source/window coverage
   and the panel's empty-state presentation. Use a known populated window when available; otherwise
   report positive-data behavior `[unverified]`. Do not widen filters just to obtain frames, or
   mistake missing telemetry for an expected empty result.
3. Follow [visual verification](./visual-verification.md) through an authorized browser or a server
   render. For a server render, use the instance's generated image link or derive the same-origin
   `GET /render/d-solo/<uid>/<slug>` route, preserving a deployment subpath. Carry `orgId`, `tz`, the
   `var-<name>` selections and absolute window; use the actual panel ID or scene key. Start from one panel at
   1200×600 with `scale=1`, a 45-second client timeout and an 8 MiB bound, one render at a time.
   Authenticate through the existing credential path, never in the URL, follow no redirects, and
   never call the renderer service directly with the service-account token. Grafana answers its own
   render-concurrency limit with a stock PNG under HTTP 200, so check the dimensions; a missing
   renderer answers HTTP 500. With no visual path, label presentation `[unverified]`.
4. Confirm the save message on the new version. App-platform history is served only at an
   enabled stable version such as `v1`, never at the alpha or beta version a row may be stored
   at (a legacy-created `v0alpha1` row answers a history query at `$APIVER` with nothing): list
   `/apis/dashboard.grafana.app/v1/namespaces/<ns>/dashboards?labelSelector=grafana.app/get-history=true&fieldSelector=metadata.name=<uid>`,
   or fall back to legacy `GET /api/dashboards/uid/<uid>/versions?limit=20` and `/versions/<n>`
   for a full prior model.

   Legacy history requires `dashboards:write`; a read-only identity gets 403.
   Preserve endpoint-specific results; neither 403 nor a history read proves absence of versions or
   verification of a new save.

## Rollback

Your own write makes the export's token stale, so never replay the export. Keep the verified
operation-written state separately from the pre-change export. Before restoring, compare a fresh
live read with that operation-written state: spec, folder, and other editable fields must match; a
changed concurrency token also requires reconciliation. Stop on intervening edits or missing
comparison evidence; a fresh token alone does not authorize replacing another editor's changes.
Hand off the drift and proposed scoped inverse for review under the existing authority. Only after the
comparison passes, put the saved spec into the current envelope, drop `status`, and apply it like
any other update with the fresh concurrency token; the legacy path takes `dashboard.version` from
that fresh read. Re-diff the complete restore, preserve scope, and stop on conflict. Provisioned or
tool-managed rollback belongs to that owner. Grafana keeps 20 versions by default.

## Handoff

Dashboards: instance, folder, uid, schema written, diff, resulting version/generation, execution
outcome, save message, query evidence, visual-check status, data-source/entitlement checks, and
final evidence line. Folders: instance, uid, title, parent, current resource version, write
receipt, diff, recovery owner, and execution outcome. For UNKNOWN, add the readback with version
history (dashboard) or the intended-parent listing (folder), and the reconciliation owner. Redact
rendered evidence; prefer an access-controlled link or cropped panel over a full-screen image.
