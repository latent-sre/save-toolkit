# Verify rendered panels

Query data, rendering capability, an image response and an inspected
image are separate evidence; API success is not visual inspection.

## Pick an available path

| Access | Next step |
|---|---|
| Authorized browser session | Open the dashboard, set time/variables, select the panel, and inspect it with its query/data |
| Server renderer available | SRE agent: run the helper's [`render`](./command-access.md#bundled-read-helper), then open the saved PNG. Other agents: request a bounded panel image through Grafana's render route ([HTTP API](./http-api.md)) and open it |
| Only a supplied screenshot | Explain visible features; retain unknown time, variables, query, and freshness unless independently supplied |
| No usable visual path | Continue model/query checks and mark presentation unverified; name the missing access |

Grafana's `rendererAvailable` flag describes server-rendering capability only: false does not rule
out browser screenshots, and true does not prove a render works. The SRE agent must not read
`/api/frontend/settings`, which also carries datasource connection details; ask the owner or use a
render attempt instead.

## SRE browser investigation

The Copilot projection has no shell, so the browser is its only visual path. The Claude Code agent
grants the Playwright MCP column; the generated Copilot agent grants both columns. Tools from another
server or an absent native tool are not available.

| Capability | Playwright MCP | Native VS Code |
|---|---|---|
| Open/navigate | `browser_navigate` | `openBrowserPage`, `navigatePage` |
| Read/capture | `browser_snapshot`, `browser_take_screenshot` | `readPage`, `screenshotPage` |
| Inspect/select | `browser_click`, `browser_hover`, `browser_select_option` | `clickElement`, `hoverElement` |
| Time/variable inputs and scrolling keys | `browser_type`, `browser_press_key` | `typeInPage` |
| Bounded loading wait | `browser_wait_for` | Read the updated page when ready |

Never pass `filename` to the Playwright capture tools: an explicit name can overwrite a repository
file. Read a fresh snapshot after each interaction; a text snapshot shows structure, and graph
interpretation needs image inspection.

1. Reuse the authenticated page; native VS Code needs the human's **Share with Agent** page,
   because agent-opened pages have no sign-in. Navigate only
   to the assigned HTTPS Grafana origin and dashboard; never follow a panel link to a new origin,
   fill authentication fields, or ask for credentials. A login redirect or expired session goes to
   the human.
2. Keep the session to the requested Grafana context. Freeze the window as absolute UTC instants,
   record timezone and variables, and change only unsaved view controls; an Apply button is fine for
   the time picker, a save or mutation dialog is not.
3. Inspect rows, values and query/data through read-only controls. Do not enter dashboard editing
   to reach a missing inspector.
4. Compare those observations with the stored model and query results at matching selections. The
   bundled [read helper](./command-access.md#bundled-read-helper) supports dashboard models, bounded
   Prometheus/Loki queries and single-panel renders. `query` has no path for other datasource types,
   but `render` and the browser still show their panels.
5. Never save dashboards, add annotations, create snapshots,
   change alerts or silences, or invoke deployment controls. Stop at unavailable protections or
   tools; do not replace a denied tool with another execution channel.

Keep passwords, cookies and tokens out of results; never repeat a signed-in display name from a
snapshot. If a page/error exposes credentials, stop that path and report the gap without repeating
them. Never inspect credential files or copy cookies to manufacture access.

## Bind query and image evidence

1. Resolve the instance/org, dashboard UID, stored model, and actual panel identifier. Capture an
   absolute `from`/`to` window, timezone, variable values, and panel time overrides, and use the
   same selections for query and image; `query` covers at most 24 hours, so keep a paired render
   within that. A changed dashboard version or variable invalidates a claim that the two match.
   Start with `dashboard --uid <uid> --panel <id>` (Classic, or V2 by numeric panel ID). Compare its stored version
   with the render receipt's `dashboard_version`; a mismatch requires a fresh model and matching
   evidence. Matching versions alone do not establish matching data or prevent a change during render.
2. Read all relevant targets and transformations. Query the panel's real datasource with its
   supported read contract; retain instant/range mode, step, macro substitutions, and per-query
   status. One target's sample does not verify every series. The SRE agent queries and renders only through the helper's `query` and
   `render`, never arbitrary HTTP or render URLs.
   Use `--mode instant` for an instant panel. Supply the
   observed `--interval-ms` or `--rate-interval-ms` when the comparison depends on it. Compare actual returned
   bounds and counts in `summary`; backend alignment and sampling may differ from the render.
3. Render one panel at a time. The helper's `render` takes integer panel IDs and up to five
   simple `--var` values. Use `--width` and `--height` when labels or legends need more space. Changing
   dimensions can change Grafana's calculated query interval, so re-check the query context when
   comparing images at another size. Use the browser for unsupported view controls.
   A requested 526×202, the size of one stock rendering-limit image, is rejected; other stock
   images are caught because their dimensions differ from the requested size.
4. Open the image; HTTP 200 or a PNG signature is insufficient. Reject login/loading/error
   states, wrong panels, stale windows, or Grafana's stock "rendering limit" image.

A full layout/interaction check needs the browser, including lower rows and variable controls;
single-panel renders do not establish either.

## Record and diagnose

Return the dashboard/panel link, configuration identity, absolute window and variables, query
evidence, image location, actual visual observations, and unchecked scope. Keep images private
because they contain queried data.

A 403
does not prove a missing renderer; timeouts do not justify concurrency increases or TLS bypass.
Server configuration goes to its owner. Helper errors narrow the check:

| Error | Usual cause |
|---|---|
| `http_error` | Permission denied, or the render itself failed (a missing or broken renderer or a Grafana-side render timeout answers HTTP 500); if `dashboard` reads of the same UID succeed, suspect the renderer and report it to the owner |
| `renderer_busy` | HTTP 429 from the remote rendering service; do not retry in a loop |
| `renderer_placeholder` | A stock image, such as the `rendering_limit` PNG Grafana returns under HTTP 200 when its own `concurrent_render_request_limit` is reached, or a PNG whose dimensions differ from the requested render size |
| `panel_not_found` | No non-row panel with that ID; re-read the model |
| `invalid_image` | A login page or other non-PNG answer |
| `redirect_rejected` | Usually a login redirect |
| `request_failed` | Network failure or the helper's 45-second client timeout |

Grafana 13 removed the Image Renderer plugin; the standalone rendering service is the supported
server path, and an Editor token cannot install or configure it. Since Grafana 13.0 render requests
authenticate with JWT by default, which needs a `renderer_token` that is neither empty nor `-` and
matches the renderer's; report a bad one to the owner.
