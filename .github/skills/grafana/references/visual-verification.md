# Verify rendered panels

Use this when the question depends on what the reader actually sees, or when checking a dashboard
change. Query data, rendering capability, an image response, and an inspected image are separate
evidence. A successful API read cannot substitute for a visual check.

## Contents

- [Available paths](#pick-an-available-path)
- [Browser investigation](#sre-browser-investigation)
- [Query and image evidence](#bind-query-and-image-evidence)
- [Record and diagnose](#record-and-diagnose)

## Pick an available path

| Access | Next step |
|---|---|
| Authorized browser session | Open the dashboard, set time/variables, select the panel, and inspect it with its query/data |
| Server renderer available | SRE agent: run the helper's [`render`](./command-access.md#bundled-read-helper), then open the saved PNG. Other agents: request a bounded panel image through Grafana's render route ([HTTP API](./http-api.md)) and open it |
| Only a supplied screenshot | Explain visible features; retain unknown time, variables, query, and freshness unless independently supplied |
| No usable visual path | Continue model/query checks and mark presentation unverified; name the missing access |

`GET /api/frontend/settings` → `rendererAvailable` describes server-rendering capability; the SRE
agent reaches it only through the [curl fallback](./command-access.md#grafana-resource-reads).
False does not rule out browser screenshots; true does not prove a render works. Check the available
path rather than installing infrastructure as part of a read-only task.

## SRE browser investigation

The Copilot projection has no shell, so the browser is its only visual path. The Claude Code agent
grants the Playwright MCP column and the generated Copilot agent the native VS Code column; tools
from another server or an absent native tool are not available.

| Capability | Playwright MCP | Native VS Code |
|---|---|---|
| Open/navigate | `browser_navigate` | `openBrowserPage`, `navigatePage` |
| Read/capture | `browser_snapshot`, `browser_take_screenshot` | `readPage`, `screenshotPage` |
| Inspect/select | `browser_click`, `browser_hover`, `browser_select_option` | `clickElement`, `hoverElement` |
| Time/variable inputs and scrolling keys | `browser_type`, `browser_press_key` | `typeInPage` |
| Bounded loading wait | `browser_wait_for` | Read the updated page when ready |

No page-code execution, upload, cookie/storage/network inspection or dialog-accept tool is granted.
Never pass `filename` to the Playwright capture tools: an explicit name can overwrite a repository
file. Read a fresh snapshot after each interaction; a text snapshot shows structure, and graph
interpretation needs image inspection.

1. Reuse the authenticated page supplied to the task; in native VS Code, that is a page the human
   shared through **Share with Agent**, because an agent-opened page has no sign-in. Navigate only
   to the assigned HTTPS Grafana origin and dashboard; never follow a panel link to a new origin,
   fill authentication fields, or ask for credentials. A login redirect or expired session goes to
   the human.
2. Keep the session to the requested Grafana context. Freeze the window as absolute UTC instants,
   record timezone and variables, and change only unsaved view controls; an Apply button is fine for
   the time picker, a save or mutation dialog is not.
3. Expand collapsed rows, scroll with navigation keys, hover for values, and inspect panel query and
   data through read-only menus. Do not enter dashboard editing to reach a missing inspector.
4. Compare those observations with the stored model and query results at matching selections. The
   bundled [read helper](./command-access.md#bundled-read-helper) supports dashboard models, bounded
   Prometheus/Loki queries and single-panel renders; other datasource types remain a named gap.
5. Report what was actually inspected. Never save dashboards, add annotations, create snapshots,
   change alerts or silences, or invoke deployment controls. Stop at unavailable protections or
   tools; do not replace a denied tool with another execution channel.

Keep usernames, passwords, cookies and tokens out of results. Screenshots, profile labels, console
output and login errors can expose identity even when the password stays hidden: use a protected
capture path or a human-prepared cropped image, or return the gap. Never inspect credential files or
copy session cookies to manufacture another access path.

## Bind query and image evidence

1. Resolve the instance/org, dashboard UID, stored model, and actual panel identifier. Capture an
   absolute `from`/`to` window, timezone, variable values, and panel time overrides, and use the
   same selections for query and image; `query` covers at most 24 hours, so keep a paired render
   within that. A changed dashboard version or variable invalidates a claim that the two match.
2. Read all relevant targets and transformations. Query the panel's real datasource with its
   supported read contract; retain instant/range mode, step, macro substitutions, and per-query
   status. An error-free empty frame means no data, not a healthy zero, and one target's sample does
   not verify every series. The SRE agent queries and renders only through the helper's `query` and
   `render`, never arbitrary HTTP or render URLs.
3. Render one panel at a time. The helper's `render` takes Classic integer panel IDs and up to five
   simple `--var` values at a fixed size and timeout; use the browser for anything else.
4. Open the image. HTTP 200 or a PNG signature alone is not visual success. Check the expected
   title, axes, units, legends, time window, displayed values, clipping, and missing-data or error
   presentation. Reject a login page, loading or error state, wrong panel, stale window, or Grafana's
   stock "rendering limit" or "renderer not installed" image.
5. Compare visible values with the matching query results after transformations and reductions,
   allowing for late samples and distinct evaluation times; explain any mismatch before calling the
   panel correct. A threshold drawn on a graph is not a measurement, and a color is not an alert
   verdict.

A full-dashboard layout check needs the browser, including lower rows and variable controls; the
helper renders single panels only, and a solo panel verifies neither layout nor interactions such as
variable selection and drill-down navigation.

## Record and diagnose

Return the dashboard/panel link, configuration identity, absolute window and variables, query
evidence, image location, actual visual observations, and unchecked scope. Keep images private
because they contain queried data; never create a public Grafana snapshot instead.

On failure, distinguish permission or authentication, a missing renderer, callback connectivity,
timeout or resource pressure, and query or plugin errors. A 403 is not proof of a missing renderer,
and a timeout does not justify raising concurrency or disabling TLS checks. Prepare a deployment
diagnosis for the owner when server configuration is involved. The helper's `render` errors narrow
this down:

| Error | Usual cause |
|---|---|
| `http_error` | Permission denied, or the render itself failed (a missing or broken renderer answers HTTP 500); read `rendererAvailable` through the [curl fallback](./command-access.md#grafana-resource-reads) or the browser to tell them apart |
| `renderer_busy` | HTTP 429 from the renderer; do not retry in a loop |
| `renderer_placeholder` | Grafana's own render limit or an unavailable renderer, served as a stock image |
| `panel_not_found` | No non-row Classic panel with that ID; re-read the model |
| `invalid_image` | A login page or other non-PNG answer |
| `redirect_rejected` | Usually a login redirect |
| `request_failed` | Network failure or the 45-second timeout |

Grafana 13 removed the Image Renderer plugin; the standalone rendering service is the supported
server path, and an Editor token cannot install or configure it. Never recommend installing the
deprecated plugin.

[sourced] [Panel sharing and render parameters](https://grafana.com/docs/grafana/latest/dashboards/share-dashboards-panels/),
[renderer setup](https://grafana.com/docs/grafana/latest/setup-grafana/image-rendering/),
[Grafana 13 plugin removal](https://grafana.com/docs/grafana/latest/whatsnew/whats-new-in-v13-0/#grafana-image-renderer-plugin-support-removed),
[Playwright MCP tools](https://github.com/microsoft/playwright-mcp#tools) and
[VS Code browser tools](https://code.visualstudio.com/docs/agents/run/browser-tools).
