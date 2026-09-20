# Grafana dashboard HTTP API — safe live edits

Read this when the invoked `observability-engineer` talks to a live Grafana. The dashboard write
rule is dashboards and folders only; Grafana's version history plus the save message records the live
edit. `stack-profile` owns the repository recovery-copy facts; a backup is not automatically a
provisioning source or a tested rollback. For review-only work use [read-only checks](./read-only-review.md).
The 13.2 baseline below separates current read evidence from write procedures. Create, update,
conflict, import, and rollback behavior is `[unverified]` on the current target; historical QA
write results remain in Git history and do not transfer to an upgraded instance. Grafana 13
deprecates `/api` in favour of `/apis` but still serves both; 13.2 disables scripted dashboards
(410) by default. *[sourced: Grafana API and dashboard docs, 13.2.0 feature registry; reviewed
2026-09-01]*

## Credentials and effective scope

Read `$GRAFANA_URL` and `$GRAFANA_SA_TOKEN` at call time; never print the token, use `curl -v`, or
put it in an evidence packet. Prefer folder-scoped grants; an organization Editor role is not least
privilege. Read `GET /api/access-control/user/permissions` before trusting search or writing, because
the current scope is a prerequisite to interpreting either operation:

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

The namespace is `default` for org 1, `org-<id>` otherwise, `stacks-<id>` on Grafana Cloud.
App-platform identity is `metadata.name` (the dashboard uid), not the server-minted `metadata.uid`.

The read URL selects the returned shape, not the stored schema. The 13.2.2 read-only target served
all six versions with preferred `v2`; the sampled stored Classic dashboard returned `elements`
through V2 and `panels` through V1. `[verified: target reads, 2026-09-19]` An unpinned Classic
transform can therefore see no panels. This does not verify a converted write or its fidelity.

1. Read at `v0alpha1` (unstructured, no migration). Take `status.conversion.storedVersion`,
   falling back to the returned `apiVersion`.
2. Extract the segment after the last slash from a group-qualified value such as
   `dashboard.grafana.app/v0alpha1`; use only that segment in the versioned URL.
3. Pin every read/write to that version. If the probe and pinned read disagree, stop before
   diffing or writing. Legacy `meta.apiVersion` reports the requested version, not storage.

## Preflight, once per target and after every upgrade

`GET /api/health` (version and edition; `enterpriseCommit` is not plugin entitlement),
`GET /api/access-control/user/permissions`, `GET /api/org` (hence the namespace),
`GET /apis/dashboard.grafana.app/` (served and preferred versions), `GET /api/datasources` (names,
types, uids), `GET /api/frontend/settings` (renderer availability and feature toggles), and
`GET /api/search?type=dash-db&limit=100` cross-checked against the permissions read. Identifiers come
from these responses, never from another instance or from memory.

## Read and export

Read the stored shape at the pinned version into `live.json` and keep it as rollback content. Read
the legacy DTO `GET /api/dashboards/uid/<uid>` for `meta`: stop when `canSave` is false,
`provisioned` is true, or `grafana.app/managed-by` names another tool, because the owning source
must change and no API write is durable. Legacy `GET /api/dashboards/uid/<uid>/versions` shows who
last saved and how. A portable Classic export keeps the stable uid, drops the numeric id, and strips
app-platform `status`, `resourceVersion`, and `generation`; instance URLs and folder or data-source
uids leave only under a separate authorization.

## Create, import, update

**Create** is a live change with the same evidence duty as an update. App platform: `POST` the
envelope to the collection path, `…/namespaces/<ns>/dashboards`, never to the `<uid>` item path,
with `apiVersion` set to the pinned `dashboard.grafana.app/<version>`, `metadata.name` set to a
stable 8–40 character uid, the folder in the `grafana.app/folder` annotation, the change reference
in `grafana.app/message`, and no `metadata.resourceVersion` or `generation` (those are the server's
concurrency fields, absent on a create); success is 201. Legacy: `POST /api/dashboards/db` with `id: null`, `folderUid`, `message`, and
`overwrite: false`; success is 200. A 409 or `name-exists` means the uid is taken: stop and
reconcile, never switch to `overwrite: true`. Handle both 409 and legacy documented 412 conflict
responses; the current read-only check does not establish the write response code. Before dispatch,
name the human or protected executor who owns recovery if removal is needed: a create has no prior
dashboard version to restore, and this lane has no deletion authority.

**Import** is the only path that binds `__inputs` and `${DS_*}` placeholders to this instance's data
sources (`POST /api/dashboards/import` with `overwrite: false`, `folderUid`, and an `inputs[]`
binding). Raw `POST /api/dashboards/db` stores the literal placeholder and produces a
missing-data-source panel. After import, replace the bound concrete uid with `${datasource}` where
portability is wanted, and save the corrected model.

**Update** shows a stable diff (`jq -S` both specs), then writes once with the family's fresh
concurrency token and a save message, which cannot be added later:

| Family | Token | Stale response | Then |
|---|---|---|---|
| App-platform `PUT` | `metadata.resourceVersion`; strip `status` first | 409 `Conflict` | fresh read, re-diff, retry only after reconciliation |
| Legacy `POST /api/dashboards/db` | `dashboard.version` from the read just made, `overwrite: false` | 409 with the same "already exists" message as a taken uid (older docs: 412) | fresh read, compare versions |

Never use `overwrite: true` to bypass a conflict. Do not assume a byte-identical reapply creates no
new history entry on the current target. The same uid and desired bytes identify the intended
result, not a retry-safe operation: a timeout, dropped response, or crash after
dispatch is **UNKNOWN** and is reconciled by step 6 of the [dashboard operation loop](./dashboard-operations.md) before any
redispatch.

## Folder create and update

The app-platform folder API has a separate lifecycle from dashboards. Before a folder change, read
the target's folder permissions and namespace. A create needs `folders:create` and `folders:write`;
an update needs `folders:write`; both need enough `folders:read` scope to check the target and read
it back. For a nested folder, confirm that nested folders are enabled and that the parent-specific
grant applies. These current API contracts are [sourced: Grafana's
Folder HTTP API](https://grafana.com/docs/grafana/latest/developers/http_api/folder/), reviewed
2026-09-19; their behavior on the target is `[unverified]` until observed.

- **Create:** list or read the proposed uid and inspect the intended parent for a title collision.
  `POST /apis/folder.grafana.app/v1/namespaces/<ns>/folders` takes a chosen stable `metadata.name`,
  optional `grafana.app/folder` parent annotation, and `spec.title`. Do not send
  `metadata.resourceVersion`: it does not exist before creation. `201`
  creates; `409` means the uid exists, so stop and reconcile rather than delete or overwrite. Before
  dispatch, name the human or protected executor who owns recovery if removal is needed; a create has
  no prior folder version to restore, and this lane has no deletion authority.
- **Update:** `GET …/folders/<uid>` first; `PUT …/folders/<uid>` uses that same `metadata.name`,
  current `metadata.resourceVersion`, the existing parent annotation, and `spec.title`. Moving a
  folder can change inherited access, so it needs a separately authorized path. `404` is an absent
  target; `412 version-mismatch` is a concurrent update. Keep the pre-change fields as rollback
  content; a restore reads the current folder and applies those saved fields with its fresh token.
  In either case stop, fresh-read, and re-diff; do not force.
- **Outcome:** folder writes have no dashboard version-history or dashboard save-message record.
  Preserve the successful write receipt, then fresh-read the uid: it must match the intended uid,
  title, parent, and current returned resource version. A post-dispatch UNKNOWN is reconciled by
  fresh uid readback plus the intended-parent listing. The desired uid, title, parent, and a current
  returned resource version establish the observed state, but cannot attribute it to the unanswered
  dispatch; retain UNKNOWN and name a reconciliation owner. Deletion is outside the dashboard write
  rule.

## Verify, then record

1. Read back into a new file, never over `live.json`; compare uid, folder, spec, and the new
   `version` or `generation`.
2. Run each changed query through `POST /api/ds/query` with real variable values and the
   dashboard's window. `$__rate_interval` is render-time state the query API does not expand:
   substitute a concrete window of at least four scrape intervals and report what verification used.
   Require success plus populated frames; a 200 with zero frames is not a working panel.
3. Follow [visual verification](./visual-verification.md): inspect a server-rendered panel or use an
   authorized browser. `rendererAvailable: false` rules out neither browser inspection nor supplied
   screenshot evidence. If no visual path is available, label presentation `[unverified]`.
4. Confirm the save message on the new version. App-platform history is served only at an
   enabled stable version such as `v1`, never at the alpha or beta version a row may be stored
   at (a legacy-created `v0alpha1` row answers a history query at `$APIVER` with nothing): list
   `/apis/dashboard.grafana.app/v1/namespaces/<ns>/dashboards?labelSelector=grafana.app/get-history=true&fieldSelector=metadata.name=<uid>`,
   or fall back to legacy `GET /api/dashboards/uid/<uid>/versions?limit=20` and `/versions/<n>`
   for a full prior model.

   For a read-only review, legacy history can return 403 while stable app-platform history remains
   readable `[verified: 13.2.2 target, 2026-09-19]`. Preserve the endpoint-specific result; it is
   not evidence that the dashboard has no versions. A history read cannot verify a new save.

## Rollback

Your own write makes the export's token stale, so never replay the export. Read the live object
again, put the saved spec into that current envelope, drop `status`, and apply it like any other
update; the legacy path takes `dashboard.version` from the fresh read the same way. Provisioned or
tool-managed rollback belongs to that owner. Grafana keeps 20 versions by default.

## Decisions Grafana forces

| Evidence | Decision |
|---|---|
| 409 or 412 | re-read, re-diff, keep optimistic concurrency; never force |
| 410 on a scripted dashboard (13.2) | migrate; re-enabling the flag is an owner decision |
| 500 naming a namespace | use the namespace Grafana names; do not repeat the path |
| empty search | check `dashboards:read` before calling the instance empty |
| provisioned, plugin, or managed owner | stop and hand the change to that source |
| zero query frames | fix data source, labels, variables, or window before claiming completion |
| a 404 on the app platform | verify uid, version, and served APIs before falling back to legacy |

Deleting dashboards and changing permissions, data sources, alerts, contact points, or platform
configuration are outside the dashboard write rule.
