# Grafana dashboard HTTP API — safe live edits

Read this when the invoked `observability-engineer` talks to a live Grafana. The dashboard write
rule is dashboards and folders only; Grafana's version history plus the save message is the durable
record, because this team keeps no committed dashboard copy. The traps below were measured on a
non-production Grafana 13.1.4 Enterprise instance on 2026-08-21 and are `[verified: QA 13.1.4]` only
there; after an upgrade or on Grafana Cloud they are `[unverified]` until repeated. Grafana 13
deprecates `/api` in favour of `/apis` but still serves both; 13.2 disables scripted dashboards
(410) by default. *[sourced: Grafana API and dashboard docs, 13.2.0 feature registry; reviewed
2026-09-01]*

## Credentials and effective scope

Read `$GRAFANA_URL` and `$GRAFANA_SA_TOKEN` at call time; never print the token, use `curl -v`, or
put it in an evidence packet. Prefer folder-scoped grants; an organization Editor role is not least
privilege. Read `GET /api/access-control/user/permissions` before trusting search or writing, because
of two silent traps:

- A token without `dashboards:read` gets the same empty `/api/search` array as an empty instance.
- A create-only token received read/write/delete on the object after a *legacy* create, but an
  app-platform create granted its creator nothing: every readback and cleanup returned 403. Use the
  legacy create for that grant shape, or obtain folder-scoped read/write/delete first. Never create
  what the caller cannot verify or roll back.

## Two API families, one stored version

| Family | Path | Use |
|---|---|---|
| App platform | `/apis/dashboard.grafana.app/<version>/namespaces/<ns>/dashboards/<uid>` | version-pinned read, create, update, delete; stable-version history |
| Legacy | `/api/dashboards/*`, `/api/search`, `/api/folders`, `/api/datasources` | discovery, Classic fallback, create when its managed-permission grant is needed |

The namespace is `default` for org 1, `org-<id>` otherwise, `stacks-<id>` on Grafana Cloud.
App-platform identity is `metadata.name` (the dashboard uid), not the server-minted `metadata.uid`.

The version in a read URL controls the returned *shape*, not what is stored: QA 13.1.4 served
`v0alpha1`, `v1`, `v1beta1`, `v2alpha1`, `v2beta1`, and `v2` with preferred `v2`, so a Classic
`spec.panels[]` transform against an unpinned read can silently see nothing. Find the stored version
first: read the dashboard at `v0alpha1` (unstructured, no migration) and take
`status.conversion.storedVersion`, falling back to the returned `apiVersion`; then pin every read
and write to that version. If the probe and the pinned read disagree, stop without diffing or
writing. Do not use the legacy `meta.apiVersion` as storage evidence: it reports what the client
asked for.

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
envelope with `metadata.name` set to a stable 8–40 character uid, the folder in the
`grafana.app/folder` annotation, the change reference in `grafana.app/message`, and no version;
success is 201. Legacy: `POST /api/dashboards/db` with `id: null`, `folderUid`, `message`, and
`overwrite: false`; success is 200. A 409 or `name-exists` means the uid is taken: stop and
reconcile, never switch to `overwrite: true`. QA 13.1.4 returned 409 for a taken uid where older
docs say 412.

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

`overwrite: true` silently defeated the legacy token and discarded the concurrent save in QA.
Re-applying byte-identical content created no new version, so the write is idempotent-by-target
only for the same uid and desired bytes, not retry-safe.

A timeout, dropped response, or crash after dispatch is **UNKNOWN**. Before any redispatch, read back
and inspect version history for the save message: desired bytes and the message mean executed;
prior bytes and no message mean not executed; a conflict, permission failure, or incomplete
observation stays UNKNOWN, stops, and names a reconciliation owner.

## Verify, then record

1. Read back into a new file, never over `live.json`; compare uid, folder, spec, and the new
   `version` or `generation`.
2. Run each changed query through `POST /api/ds/query` with real variable values and the
   dashboard's window. `$__rate_interval` is render-time state the query API does not expand:
   substitute a concrete window of at least four scrape intervals and report what verification used.
   Require success plus populated frames; a 200 with zero frames is not a working panel.
3. If `rendererAvailable` is true, inspect a rendered panel; otherwise record query-only
   verification and label the visual check `[unverified]`.
4. Confirm the save message on the new version: app platform lists history with
   `labelSelector=grafana.app/get-history=true&fieldSelector=metadata.name=<uid>`; legacy
   `GET /api/dashboards/uid/<uid>/versions?limit=20` and `/versions/<n>` for a full prior model.

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
