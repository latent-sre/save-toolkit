---
name: frontend-craft
description: >-
  Build or change a web GUI for the team's applications and SRE tooling — operator consoles,
  workbenches and admin panels, in-app dashboards, status and catalog sites, form-driven
  workflows — in React (Vue allowed) on Vite and TypeScript, from one page to a full app, wired
  to the team's FastAPI and Go OpenAPI services and served on localhost and PCF. Owns the caller
  interview and design brief, the component-kit choice, the browser side of the API contract,
  error and action surfaces, runtime configuration, accessibility and motion. Triggers: 'build
  a UI for', 'add a page/form/table/console', 'make this look less generic', 'wire the UI to
  the API'. Not for the service behind the UI (backend-craft) or Grafana dashboards
  (obs-dashboards to design, grafana to operate).
argument-hint: "[the GUI to build or change]"
---

# Frontend craft

Deliver a distinctive, complete application with runnable code, real backend integration and
verified user workflows. The backend may be new or existing. Use the caller's requirements and
repository facts first; defaults fill decisions they leave open.

In an existing app, keep its framework, kit, router, libraries and conventions: read settled
choices from the repository and confirm only what it leaves open. A feature change never
migrates a framework, router or kit as a side effect. Write the brief for a new app or a new
area, and for a visual change larger than one component; a bounded change follows the app's
established identity.

## Shape the app and select the relevant guidance

Write a short [design brief](./references/design.md) from the known audience, job, workflows and
visual direction before styling. Ask one round with recommended defaults only for consequential
unsettled choices; carry forward answers already supplied. Choose an app identity, density and
motion budget that fit the work, with visible actions and keyboard and screen-reader parity.

Resolve these capabilities before scaffolding:

| Decision | Guidance to load |
|---|---|
| Framework and kit | [Stack](./references/stack.md): React, Vite and strict TypeScript by default; [Vue](./references/vue.md) when the caller or neighbouring apps choose it. Approved kits are mixable; one base owns the global styling and providers. |
| Backend contract; read-only or actions | [API](./references/api.md): typed client, errors, caching and sessions. Add cursor handling for paged endpoints and write safeguards for actions the app actually offers. |
| Live data | The API reference's live-data section when updates arrive without a click; choose polling or streaming for each need. |
| Localhost or PCF | [Serving](./references/serving.md): local API proxy and build checks; runtime configuration and PCF files when those capabilities are needed. |

Load `stack-profile` before recommending runtime, tooling or infrastructure choices. Use
[starting code](#starting-code) selectively: equivalent app or library facilities satisfy the
contract. A read-only app needs no write helper; an unpaged API needs no cursor machinery; a
localhost-only app needs no PCF deployment scaffold.

## Build the complete workflows

Get one working end-to-end path through the running backend early, then complete every required
workflow and its loading, empty, success, error and stale states. Generate the client from the
backend's actual OpenAPI contract. If the backend also needs work, coordinate it through
`backend-craft`. Mocks and labelled sample data support development and tests; any integration
they replace remains an explicit gap.

- **Recoverable failures.** Route and independent-panel error boundaries contain failures where
  they occur. Every async path ends in a rendered state. Show an actionable error, a copyable
  request ID, time and zone, and safe retry; report boundary catches and unhandled rejections to
  the app's browser error reporting with request ID and release, without sensitive values.
- **State ownership.** Server state lives in the query cache with visible data age; UI state stays
  local. Put shareable, non-sensitive filters, sort, page and tabs in the URL. Add a global store
  only for state shared by distant components. Choose pagination or virtualization from rendered
  rows, interaction and measured cost; preserve server filtering.
- **Permissions and actions.** For authenticated apps, show the signed-in identity and role.
  Disable visible but forbidden actions with a reason; hide areas the user can never use. The
  server enforces authorization. Reversible actions offer undo; destructive or bulk actions
  confirm the exact target, count and environment with Cancel focused; irreversible or fleet-wide
  actions also require the target's name. Preserve input on validation failure and show per-item
  outcomes, including unknown.
- **Content safety.** Render API, log and user text as text. Rich HTML uses the repository's
  sanitizer, or DOMPurify; data-driven links and sources allow only `http:`, `https:` and
  `mailto:`. Mask account/client identifiers and personal data until revealed; keep them out of
  URLs, page titles and telemetry. Show timestamp zones (UTC unless the repository chooses
  another), with relative time beside them; format numbers through `Intl` and preserve server
  decimals without floating-point conversion.
- **Accessibility.** Use semantic controls and labelled inputs, visible focus and full keyboard
  access. Kit primitives own focus traps, ARIA state and arrow-key behaviour. Navigation moves
  focus to the main heading; same-view updates preserve it. Announce save, completion and error
  status without stealing focus. Reflow at 320 CSS px; targets are at least 24 by 24 px, 44 for
  touch. Provide AA contrast in both themes, reduced-motion variants and chart text/table
  alternatives. Status always has a word or icon as well as colour.

## Verify before handing off

Run typecheck, lint, component tests for implemented behaviour and a production build. Adapt the
selected helpers' assertions to the app's existing runner: the dependency-free `.test.ts` assets
use `node:test` and must not be blindly copied into Vitest's collection. Do not add a second test
runner. Cover applicable API cases from the [API reference](./references/api.md), including auth
and failure paths; read-only or unpaged apps do not acquire write or cursor tests.

Exercise every required workflow against the running backend. Run the serving contract for a
served production build with the relevant optional checks enabled. Use the host's Playwright
MCP server (through the caller when this lane lacks its tools) to inspect every view and its
states in light and dark, at desktop width and 320 px. Check hierarchy, legibility and the
design brief; run axe, walk the interactions by
keyboard and inspect the served build's console for CSP violations and missing styles. Fix what
the rendered result reveals.

Return the brief, workflows delivered, dependency additions and licences, commands/results,
screenshot paths and remaining gaps. Without the Playwright MCP server, use component/accessibility
checks and name the missing render; without the backend, name the unverified integration. Neither
proves the missing behaviour. Do not add Playwright packages or download browsers for this MCP
verification.

## Starting code

Read and adapt only files the selected capabilities need, using editor tools to bring content
from the installed skill into the app. Reuse equivalent facilities already present; keep their
behaviour covered by the app's runner.

| Capability | Assets and destination |
|---|---|
| App identity | [theme.css](./assets/theme.css) → `src/styles/theme.css`, imported before kit styles; set its palette, type and density from the brief |
| API errors | [problem.ts](./assets/problem.ts), [test](./assets/problem.test.ts) → beside the client |
| API writes | [idempotent-write.ts](./assets/idempotent-write.ts), [test](./assets/idempotent-write.test.ts) → beside the client; imports `problem.ts` |
| Runtime configuration | [runtime-config.ts](./assets/runtime-config.ts), [test](./assets/runtime-config.test.ts) → bootstrap |
| React error surfaces | [error-panel.tsx](./assets/error-panel.tsx), [stylesheet](./assets/error-panel.css), [test](./assets/error-panel.test.tsx) → shared components; port the card and boundary for Vue |
| PCF serving | [Staticfile](./assets/pcf/Staticfile), [spa.conf](./assets/pcf/nginx/conf/includes/spa.conf), [manifest.yml](./assets/pcf/manifest.yml), [profile.sh](./assets/pcf/profile.sh) → deploy directory, with `profile.sh` saved as `.profile` |
| Served-build checks | [serving-contract.mjs](./assets/serving-contract.mjs) → build configuration; enable API/runtime-config checks only when applicable |
