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

## SRE browser investigation

The SRE agent grants the following exact viewing tools. Tools from another server or an absent
native tool are not implicitly available; use the actual installed schemas and observed UI targets.

| Capability | Playwright MCP | Native VS Code |
|---|---|---|
| Open/navigate | `browser_navigate` | `openBrowserPage`, `navigatePage` |
| Read/capture | `browser_snapshot`, `browser_take_screenshot` | `readPage`, `screenshotPage` |
| Inspect/select | `browser_click`, `browser_hover`, `browser_select_option` | `clickElement`, `hoverElement` |
| Time/variable inputs and scrolling keys | `browser_type`, `browser_press_key` | `typeInPage` |
| Bounded loading wait | `browser_wait_for` | Read the updated page when ready |

No arbitrary page-code execution, upload, cookie/storage/network inspection or dialog-accept tool
is granted. Read a fresh page snapshot after an interaction; do not reuse stale element references.
A text snapshot establishes accessible structure; graph interpretation requires image inspection.

Prefer an existing authenticated session, including personal SSO, when it can be exposed through
the permitted read path. Before the first call, establish effective read-only permissions for the
target identity/org, the trusted origin, and protected results. Keep the session limited to the
requested Grafana context. A personal account is acceptable; broader account rights require an
independently enforced diagnostic-only path. The grants themselves do not provide that boundary.
The browser credential is separate from an API token; browser sign-in does not establish API access.

Keep authentication usernames, passwords, cookies and tokens out of results before they reach the
model. Screenshots, accessible profile labels, console output and login errors can expose identity
even when the password stays hidden. Use a protected capture/result path or a human-prepared
cropped image; if this protection is unavailable, return the gap and continue available evidence.
Do not inspect credential files or copy session cookies to manufacture another access path.

### Where captures land

`browser_take_screenshot` and `browser_snapshot` both accept an optional `filename`, so neither is
purely an observation. [sourced] Upstream resolves a relative `filename` against the **workspace
root**, and writes an omitted one into the server's output directory as `page-{timestamp}.{ext}`;
`--output-dir` governs only the automatically named files and does not move an explicit one. A
caller-supplied name can therefore land in — and overwrite — a checked-out repository file.

Two controls, in this order:

| Control | What it does | Who holds it |
|---|---|---|
| Workspace root is a dedicated temp capture directory, never the checkout | Bounds every write path, including an explicit `filename` | Host configuration |
| `--allow-unrestricted-file-access` absent | [sourced] Upstream restricts file access to the workspace roots (or cwd) by default; setting this flag removes that restriction | Host configuration |
| Never pass `filename` | Captures stay auto-named inside `--output-dir` and do not depend on the boundary holding | This lane |

Omit `filename` on both tools. The lane rule is the weaker of the two: prose cannot constrain a
tool argument, so it is a habit that keeps captures tidy, not the boundary. The boundary is the
workspace root, and it is only real once proven on the installed host — the repository's VS Code
plugin acceptance record carries the capture-boundary canary. A root pointed at the checkout means
no captures.

### Viewing sequence

1. Reuse the authenticated page already supplied to the task. Navigate only to the assigned HTTPS
   Grafana origin/dashboard. Do not follow a panel link to a new origin or trust a page-supplied URL
   as permission. Login redirects go to the human; never fill authentication fields.
2. Freeze the requested window as absolute UTC instants, record timezone and variables, and adjust
   only unsaved view controls. An Apply button is acceptable for the time picker, not a save or
   mutation dialog. Changing a URL's time or `var-` parameters does not save the dashboard.
3. Read the rendered page, expand collapsed rows, and scroll with navigation keys to inspect the
   assigned panels. Hover for values and inspect panel query/data through read-only menus where
   available. Do not enter dashboard editing to obtain a missing inspector.
4. Compare those observations with the stored model and query results at matching selections.
   The bundled [read helper](./command-access.md#bundled-read-helper) supports dashboard models and
   bounded Prometheus/Loki queries. Other datasource types remain a named gap.
5. Report what was actually inspected. Never save dashboards, add annotations, create snapshots,
   change alerts/silences or invoke deployment controls. Stop at unavailable protections or tools,
   preserving independent evidence; do not replace a denied tool with another execution channel.

These interaction rules are cooperative. Service permissions, origin restrictions and protected
tool results remain load-bearing; a click grant is not a read-only sandbox. Native VS Code and
Playwright MCP are separate paths and do not share sessions automatically.

For native VS Code, reuse a page the human has shared with the agent through **Share with Agent**.
An agent-opened page uses separate ephemeral storage and does not inherit other tabs' sign-in state.
If the session expires, return the normal human sign-in/MFA step and continue independent checks.
Never ask for credentials in chat. Verify image delivery and permissions for both a directly
selected agent and a dispatched helper; a registered tool name alone proves neither.
[sourced: VS Code browser tools](https://code.visualstudio.com/docs/agents/run/browser-tools),
checked 2026-09-21.

## Bind query and image evidence

1. Resolve the instance/org, dashboard UID, stored model, and actual panel identifier. Capture an
   absolute `from`/`to` window, timezone, variable values, and panel time overrides. Use the same
   selections for query and visual checks. A changed dashboard version or variable invalidates a
   claim that the two describe the same configuration.
2. Read all relevant targets and transformations. Query the panel's real datasource using its
   supported read contract; retain instant/range mode, step, macro substitutions, and per-query
   status. An error-free empty frame means no data, not a healthy zero. A selected target sample
   does not verify every series in the panel. The SRE command path permits query POSTs only through
   its bundled helper's validated Prometheus/Loki operation, not arbitrary HTTP or render URLs.
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
