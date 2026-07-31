# Grafana 13 provisioning

Use this reference when a dashboard must become reproducible and reviewable. It records the source-of-truth
contract; verify paths and feature availability against the target Grafana instance before applying it.

## Primary sources

- `[sourced]` [Provision Grafana](https://grafana.com/docs/grafana/latest/administration/provisioning/)
- `[sourced]` [Dashboard JSON model](https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/view-dashboard-json-model/)
- `[sourced]` [Git Sync provisioned dashboards](https://grafana.com/docs/grafana/latest/as-code/observability-as-code/git-sync/provisioned-dashboards/)
- `[sourced]` [File-path setup](https://grafana.com/docs/grafana/latest/as-code/observability-as-code/provision-resources/file-path-setup/)

Sources reviewed 2026-07-14. They establish the generic Grafana behavior below; local paths, access,
licensing, and enabled features remain `[unverified]` until checked on the target.

## File-provider inventory

Keep the provider YAML under Grafana's `provisioning/dashboards` configuration tree and the dashboard JSON
under the repository-owned directory named by `options.path`. Record the exact local values here:

| Field | Reviewed value |
|---|---|
| Provider file | `<repo path>/provisioning/dashboards/<provider>.yaml` |
| JSON root | `<repo path>/<dashboard-json-root>` |
| Grafana folder / filesystem directory | `<folder>` / `<directory>` |
| Dashboard UID / title | `<stable uid>` / `<title>` |
| Data-source UIDs | `<metrics uid>`, `<logs uid>`, `<traces uid>` |
| Apply/reload owner | `<team or controlled automation>` |

Minimal provider shape (adapt the name and path, then validate it on the target):

```yaml
apiVersion: 1

providers:
  - name: operations-dashboards
    type: file
    disableDeletion: false
    allowUiUpdates: false
    updateIntervalSeconds: 30
    options:
      path: /var/lib/grafana/dashboards
      foldersFromFilesStructure: true
```

Use a stable `uid` in every dashboard JSON model and refer to data sources by stable data-source UIDs,
not installation-specific numeric IDs or display names. With `foldersFromFilesStructure: true`, do not
also set a provider-level folder; the filesystem layout supplies the folder structure.

## Review and apply

1. Export or edit the JSON in the repository. Normalize only with an approved formatter; avoid noisy
   rewrites that hide query changes.
2. In the pull request, review title/purpose, stable `uid`, folder, data-source UIDs, variables, every
   query, units, thresholds, links, no-data/error behavior, and the expected target Grafana 13 minor.
3. Render or preview against a non-production target with representative data. Capture the exact time
   range and variable values; a syntactically valid dashboard can still query the wrong service.
4. Apply through the controlled provisioning path. Confirm Grafana loaded the expected dashboard UID and
   source revision, then exercise its top-level health-to-drill-down path.
5. Preserve the previous source revision for rollback. Rollback means reverting the reviewed JSON/provider
   change and reapplying it through the same controlled path, then verifying the prior UID content loaded.

`allowUiUpdates: false` makes the source contract explicit. Even when UI saves are allowed, Grafana does
not write UI edits back to the provisioning source; a later source update overwrites the database copy.
Do not treat an in-browser edit as durable until it passes the pull request workflow.

## Grafana 13 Git Sync alternative

Grafana 13 documents Git Sync as generally available. Use it only when the target edition and repository
policy permit it. Record the configured repository, branch, path, folder behavior, service identity, and
review protection; never place a token in dashboard JSON or this inventory. File provisioning remains a
valid path and is the default when Git Sync has not been admitted locally.

<!-- terminal-canary: q_odprov_91c4 -->
