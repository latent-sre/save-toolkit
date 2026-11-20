# Verify rendered panels

Query data, rendering capability, an image response, and an inspected image are separate evidence;
API success is not visual inspection.

## Pick an available path

| Access | Next step |
|---|---|
| Authorized browser session | Open dashboard, set UTC window/variables, select panel, inspect with its query/data |
| Server renderer available | SRE agent: helper [`render`](./command-access.md#bundled-read-helper), then open saved PNG. Other agents: same-origin `GET /render/d-solo/<uid>/<slug>` (carry `orgId`, `tz`, `var-<name>`, absolute window, `scale=1`, 1200×600, 45 s timeout, 8 MiB bound, one at a time, no redirects, auth in header not URL) and open it |
| Only a supplied screenshot | Explain visible features; mark unknown time, variables, query, and freshness |
| No usable visual path | Continue model/query checks, mark presentation `[unverified]`, name missing access |

Grafana's `rendererAvailable` flag describes server-rendering only (false does not rule out browser
screenshots; true does not prove a render works). The SRE agent must not read
`/api/frontend/settings`; ask the owner or attempt a render instead.

## SRE browser investigation

Use the browser tools the lane grants. Never pass `filename` to Playwright capture tools (can overwrite a repo file). Read a fresh snapshot
after each interaction; graphs require image inspection, not text snapshots alone.

1. Reuse the authenticated page (native VS Code requires the human's **Share with Agent** page).
   Stay on the assigned HTTPS Grafana origin and dashboard; never follow panel links to another
   origin, enter credentials, or ask for them — hand expired sessions/login redirects to the human.
2. Freeze absolute UTC times, record timezone and variables, and touch only unsaved view controls
   (time-picker Apply is fine; edit/save/silence/annotation/snapshot/delete dialogs are forbidden).
3. Keep passwords, cookies, tokens, and signed-in display names out of results. If a page exposes
   credentials, stop that path and report the gap without repeating them.

## Bind query and image evidence

- Match the exact dashboard UID, stored `dashboard_version`, panel ID, absolute UTC window (≤24 h
  for paired helper queries), timezone, and variable values between model, query, and render.
- Open every PNG before describing it: HTTP 200 or a PNG signature is insufficient. Reject login,
  loading, error, wrong-panel, or stale-window images.
- Single-panel renders do not verify full layout, lower rows, or variable controls; use the browser
  for those. Keep rendered images private (they contain queried data).

## Grafana 13 renderer traps

- **Stock HTTP 200 placeholder (`renderer_placeholder`):** Grafana returns a stock "rendering limit"
  PNG (e.g., 526×202) under HTTP 200 when `concurrent_render_request_limit` is hit; verify returned
  dimensions match requested size.
- **Missing/broken renderer (`http_error` 500 / `renderer_busy` 429):** If `dashboard` reads succeed
  on the same UID, suspect the renderer and report to its owner (do not retry 429 in a loop).
- **Standalone renderer + JWT:** Grafana 13 removed the Image Renderer plugin; the standalone
  rendering service is required and authenticates with JWT by default (needs a valid non-empty
  `renderer_token` matching the renderer). Never call the renderer service directly with a
  service-account token.
