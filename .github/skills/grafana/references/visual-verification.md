# Verify rendered panels

Use this when the question depends on what the reader actually sees, or when checking a dashboard
change. Query data, rendering capability, an image response, and an inspected image are separate
evidence. A successful API read cannot substitute for a visual check.

## Pick an available path

| Access | Next step |
|---|---|
| Authorized browser session | Open the dashboard, set time/variables, select the panel, and inspect it with its query/data |
| Server renderer available | Request a bounded panel image through Grafana, then open the returned image for inspection |
| Only a supplied screenshot | Explain visible features; retain unknown time, variables, query, and freshness unless independently supplied |
| No usable visual path | Continue model/query checks and mark presentation unverified; name the missing access |

`GET /api/frontend/settings` → `rendererAvailable` describes server-rendering capability. False
does not rule out browser screenshots; true does not prove a render works. A browser inventory with
no connected browser also does not prove that server rendering is unavailable. Check the available
path rather than installing infrastructure as part of a read-only task.

## Bind query and image evidence

1. Resolve the instance/org, dashboard UID, stored model, and actual panel identifier. Capture an
   absolute `from`/`to` window, timezone, variable values, and panel time overrides. Use the same
   selections for query and visual checks. A changed dashboard version or variable invalidates a
   claim that the two describe the same configuration.
2. Read all relevant targets and transformations. Query the panel's real datasource using its
   supported read contract; retain instant/range mode, step, macro substitutions, and per-query
   status. An error-free empty frame means no data, not a healthy zero. A selected target sample
   does not verify every series in the panel. The `sre-assistant` command allowlist still excludes
   query POSTs and render URLs; this procedure does not override that lane's tools.
3. Console: use the panel's Share/Export image action where available. Agent: use the instance's
   generated image link or derive the same-origin `/render/d-solo/<uid>/<slug>` route from the
   resolved dashboard path. Preserve a deployment subpath. Carry `orgId`, `panelId`, absolute
   `from`/`to`, `tz`, and URL-encoded `var-<name>` selections; repeat parameters for multi-values.
   Use the actual panel ID/scene key rather than guessing or converting it to another format.
4. Start with one panel at 1200×600, one render at a time, a 45-second client timeout, and an 8 MiB
   response bound. These are test defaults, not Grafana limits; adjust for the requested content
   and resource budget. Authenticate to the trusted Grafana origin through the existing credential
   path; never put tokens in URLs, images, logs, or evidence. Do not follow authenticated redirects
   or call the renderer service directly with the Grafana service-account token.
5. Check HTTP status, content type, and image decoding. HTTP 200 or a PNG signature alone is not
   visual success: inspect the image with an image/browser tool. Check the expected title, axes,
   units, legends, time window, displayed values, clipping, and missing-data/error presentation.
   Reject a login page, loading/error state, wrong panel, or stale window as a successful check.
6. Compare visible values with the matching query results after transformations/reductions. For
   near-real-time data, account for late samples and distinct evaluation times; do not invent exact
   equality. Explain any mismatch before calling the panel correct. A temperature limit or threshold
   drawn on a graph is not a measured temperature, and a graph's color is not an alert verdict.

For a full-dashboard layout check, inspect the layout through a browser or a supported full-page
render, including lower rows and variable controls. A solo panel verifies neither the full layout
nor interactions such as variable selection and drill-down navigation.

## Record and diagnose

Return the dashboard/panel link, configuration identity, absolute window/variables, selected query
evidence, image location, actual visual observations, and unchecked scope. Keep images private
because they contain queried data; use an access-controlled artifact or cropped panel. Do not
create a public Grafana snapshot as a substitute for an image.

On failure, distinguish permission/authentication, missing server renderer, callback connectivity,
timeout/resource pressure, and query/plugin errors using available evidence. A 403 is not proof of
a missing renderer. A timeout does not justify increasing concurrency or disabling TLS checks.
Prepare a deployment diagnosis for the owner if server configuration is involved.

For Grafana 13+, the old Image Renderer plugin no longer works. The standalone rendering service
is the supported server path; an Editor token cannot install/configure that service. Do not
recommend installing the deprecated plugin from its still-visible catalog entry.

[sourced] [Panel sharing and render parameters](https://grafana.com/docs/grafana/latest/dashboards/share-dashboards-panels/),
[renderer setup](https://grafana.com/docs/grafana/latest/setup-grafana/image-rendering/), and
[Grafana 13 plugin removal](https://grafana.com/docs/grafana/latest/whatsnew/whats-new-in-v13-0/#grafana-image-renderer-plugin-support-removed).
Checked 2026-09-20. Recheck after Grafana/renderer upgrades or an API/scene-key mismatch. A successful
render on one target is not acceptance for another target, panel, or dashboard schema.
