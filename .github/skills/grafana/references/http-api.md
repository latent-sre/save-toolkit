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
   [JSON model](./json-model.md) covers Classic/V1/V2 shapes, variables and panels.
4. **Validate** with the [pre-write checks](./json-model.md#check-before-writing).
5. **Show the target and full diff, then write once** ([create, import, update](#create-import-update)).
6. **Verify behavior, storage and the durable record** ([verify, then record](#verify-then-record));
   report unavailable evidence, never an inspection that did not happen.

Folder create/update uses the [folder procedure](#folder-create-and-update) under the same
authority, preflight, validation and evidence rules; dashboard history and save-message rules do
not apply.

## Credentials and effective scope

The owner selected `gcx` for the SRE assistant's read-only access migration; `stack-profile`
records that choice. The selected authentication path uses existing Ansible-managed custody and
private runtime delivery, without a persisted CLI login. Host acceptance is pending;
the [command-access reference](./command-access.md) retains the existing admitted helper path.
CLI selection grants no new commands or write authority. No Grafana MCP server, vendor skill
package or Foundation SDK is adopted; adopting one remains a separate `stack-profile` decision.
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
transform can see no panels. Probe again immediately before every write: in Grafana 13 a browser
save can convert a Classic dashboard to V2.

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

**Import** is the only path that binds `__inputs` and `${DS_*}` placeholders to this instance's data
sources (`POST /api/dashboards/import` with `overwrite: false`, `folderUid`, and an `inputs[]`
binding). Raw `POST /api/dashboards/db` stores the literal placeholder and produces a
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
