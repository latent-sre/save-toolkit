# Grafana dashboard HTTP API — read, export, and controlled update

Use this reference when a dashboard must be read from or written to a live Grafana over HTTP: exporting
a UI-drafted dashboard into the repository, checking a provisioned dashboard for drift, letting CI apply
reviewed JSON, or walking version history. The API never replaces the as-code contract in
[provisioning](./provisioning.md): the repository stays the source of truth, and an API write that did
not start life as reviewed repository bytes is a snowflake with extra steps.

## Primary sources

- `[sourced]` [Dashboard HTTP API](https://grafana.com/docs/grafana-cloud/learn-and-build/developer-resources/api-reference/http-api/dashboard)
- `[sourced]` [Folder/dashboard search API](https://grafana.com/docs/grafana-cloud/learn-and-build/developer-resources/api-reference/http-api/api-legacy/folder_dashboard_search)
- `[sourced]` [Dashboard versions API](https://grafana.com/docs/grafana-cloud/learn-and-build/developer-resources/api-reference/http-api/api-legacy/dashboard_versions)
- `[sourced]` [Dashboard permissions API](https://grafana.com/docs/grafana-cloud/learn-and-build/developer-resources/api-reference/http-api/api-legacy/dashboard_permissions)
- `[sourced]` [Migrate API keys to service accounts](https://grafana.com/docs/grafana-cloud/platform/security-and-account-management/security-and-access/authentication-and-permissions/service-accounts/migrate-api-keys)

Sources reviewed 2026-08-21 through the Context7 documentation mirror (grafana.com is not directly
reachable from the authoring environment); the pages establish generic Grafana behavior. Exact
endpoint behavior on the deployed Grafana 13 minor, its enabled API families, and local access
remain `[unverified]` until exercised against the target.

## Who runs API calls — this is not an agent surface

- A service-account token is a credential next to egress, the same class as `cf env` output: it never
  lands in tracked configuration, an agent transcript, or a handoff packet. Humans and CI hold tokens;
  supply them at call time from a secret store (`$GRAFANA_SA_TOKEN` below).
- `curl` is deliberately absent from the `sre`/`observability-engineer` Bash allowlist, and `gh api`
  is excluded by design. Guarded agents therefore do not call this API themselves — they prepare the
  exact request for a human or CI, and use the repository's read-only Grafana MCP configuration for
  inspection. `[sourced: scripts/readonly-guard.py]`
- Scope service accounts minimally: a **Viewer**-role account for read/export/drift jobs, a separate
  **Editor**-role account — folder-scoped via dashboard/folder permissions — for the one CI job allowed
  to apply reviewed JSON. API keys are deprecated in favor of service accounts; migrate rather than
  minting new keys. `[sourced: migration page above]`

## Two API families

| Family | Shape | Notes |
|---|---|---|
| Classic | `GET /api/dashboards/uid/:uid`, `POST /api/dashboards/db`, `GET /api/search`, `GET /api/dashboards/uid/:uid/versions` | Wraps the Classic/V1 JSON model; the docs now file most of it under "legacy" |
| App platform | `GET/POST/PUT /apis/dashboard.grafana.app/v1/namespaces/:namespace/dashboards/:uid` | Kubernetes-style: `metadata.name` is the UID, folder and commit message travel as `grafana.app/folder` / `grafana.app/message` annotations, the model is `spec` |

The split maps onto the schema note in [provisioning](./provisioning.md): the app-platform family
speaks the V1/V2 Resource shapes, the classic family the `schemaVersion` JSON. Pick the family that
matches the schema recorded in the dashboard's inventory row, and record which one automation uses.
Single-org self-managed instances appear as namespace `default`; the exact namespace mapping for the
deployed instance is `[unverified]` — read it from an existing dashboard's URL or an API listing
before scripting against it.

## Read and export

```bash
# Find dashboards (title match, tag, or folder scope); results honor the caller's permissions
curl -sS -H "Authorization: Bearer $GRAFANA_SA_TOKEN" \
  "$GRAFANA_URL/api/search?query=checkout&type=dash-db&tag=prod"

# Fetch one dashboard by stable UID; returns {dashboard, meta}
curl -sS -H "Authorization: Bearer $GRAFANA_SA_TOKEN" \
  "$GRAFANA_URL/api/dashboards/uid/<uid>" > export.json
```

Before committing an export: keep the stable `uid`, drop the instance-local numeric `id`, leave the
`version` counter out of review discussion (Grafana owns it), and record the schema family in the
provisioning inventory. Validate with `jq empty` — the one JSON check on the guarded allowlist —
and review the diff against the previous repo copy, not against memory of the UI.

## Update — optimistic concurrency, loud failures

`POST /api/dashboards/db` takes `{dashboard, folderUid, message, overwrite}`; documented statuses are
201 created, 400 invalid model, 401/403 auth, and 409 when the UID already exists on create. For
updates, send the `version` you just read and keep `overwrite: false`, so a concurrent edit fails
loudly instead of being silently clobbered; the documented failure shape in this API family is
`412 Precondition Failed` with `"status": "version-mismatch"`. Always set `message` to the PR number
and full commit SHA of the reviewed bytes, so Grafana's version history points back at review.

```bash
# 1. Read the live model and note .dashboard.version
# 2. Apply the reviewed repo copy with that version pinned
curl -sS -X POST -H "Authorization: Bearer $GRAFANA_SA_TOKEN" -H "Content-Type: application/json" \
  -d '{"dashboard": <reviewed model with "version" pinned>, "folderUid": "<folder>",
       "message": "PR #<n> <full-sha>", "overwrite": false}' \
  "$GRAFANA_URL/api/dashboards/db"
```

Two guard rails:

- **File-provisioned dashboards are not API-writable.** A dashboard owned by a file provider is
  updated by changing the repository file and letting the provisioner reload it; expect the API to
  refuse the save. Exact refusal message per minor is `[unverified]` — verify on the target before
  building automation that assumes either behavior.
- **An API write is a Tier 2 live change** under the `observability-engineer` change ladder: show the
  target UID, the exact request, the diff, and the rollback (the previous reviewed revision reapplied
  through the same path) and hand it to the human or approved CI actor. Ad-hoc hand-pushed JSON —
  even correct JSON — bypasses review and is the failure this reference exists to prevent.

## Version history

`GET /api/dashboards/uid/:uid/versions` lists saved versions (who, when, `message`);
`GET /api/dashboards/uid/:uid/versions/:version` returns the full model at that version. Use them to
answer "what changed on this dashboard and when" during triage, and to fetch rollback evidence. For a
provisioned dashboard the durable rollback is still the repository revert per
[provisioning](./provisioning.md); a version restored in Grafana is overwritten by the next
provisioning cycle.

<!-- terminal-canary: q_odapi_4e19 -->
