---
name: frontend-craft
description: >-
  Build or change web applications and SRE interfaces in React or Vue, from one page to a
  complete app integrated with its backend. Triggers: 'build a UI for', 'add a page/form/table/console',
  'make this look less generic', 'wire the UI to the API'. Not for backend implementation
  (api-craft) or Grafana dashboard design and operations (grafana).
argument-hint: "[the GUI to build or change]"
---

# Frontend craft

Deliver runnable UI code wired to the real backend contract with complete workflows and verification.
Preserve an existing app's framework, component kit, router, and locked toolchain. Load `stack-profile`
before introducing a new runtime or infrastructure choice.

## Load for the changed boundary

| Boundary | Guidance |
|---|---|
| Framework, kits, design brief, tokens, and API/state integration | [Stack, design, and API integration](./references/stack.md) |
| Production serving, PCF `Staticfile`/nginx, runtime config, and CSP | [Serving and runtime config](./references/serving.md) |

## Design & workflow standards

- **App identity (new apps or large areas):** Write a short design brief first (audience/job,
  archetype — operator console, workbench, in-app dashboard, status/catalog site, or guided workflow —
  OKLCH brand/surface hues with `light-dark()`, self-hosted `@fontsource` or intentional system fonts,
  density, and motion budget honoring `prefers-reduced-motion`). Avoid generic AI tells (unchosen
  purple/slate palettes, decorative glass/glows, unrequested hero/3-card grids, generic "Submit" labels).
- **Complete workflows:** Wire an end-to-end backend path early and cover loading, empty, success,
  error, and stale states. Keep shareable filters, sort, pagination, and active tabs in the URL.
  Choose pagination or virtualization from rendered row counts and measured cost.
- **Recoverable errors:** Isolate panels with error boundaries so failures never drop the page heading.
  Display actionable messages, copyable request IDs, UTC-zoned timestamps, and safe retries — never raw
  JSON, stack traces, or problem `type` URIs.
- **Permissions & safety:** Show signed-in identity/role; disable forbidden actions with reasons and
  hide unreachable areas. Confirm destructive/bulk actions with target, count, and environment (Cancel
  focused); require typing the target name for irreversible or fleet-wide actions. Render API/log text
  as text (sanitize rich HTML with DOMPurify; allow only `http:`, `https:`, `mailto:` links); mask PII
  until revealed and keep it out of URLs/titles/telemetry; format numbers via `Intl` without float loss.
- **Accessibility:** Semantic controls, labelled inputs, visible focus, full keyboard access, 320 px
  reflow, ≥24×24 px targets (44 px touch), AA contrast in light and dark themes, and text/icon paired
  with status color. Right-align numeric table columns with `tabular-nums`.

## Verify before handing off

Run the repository's typecheck, lint, component tests, and production build. Cover affected workflows
in light and dark mode at desktop and 320 px width (checking navigation, reload, focus, console CSP/style
errors, and `axe-core` accessibility via repo browser tests or Playwright MCP without installing new
browser packages). Verify production serving headers/fallback with [Serving](./references/serving.md).
