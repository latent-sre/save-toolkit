---
name: frontend-craft
description: >-
  Build or change a web GUI for the team's applications and SRE tooling — operator consoles,
  workbenches and admin panels, in-app dashboards, status and catalog sites, form-driven workflows —
  in React (Vue allowed) on Vite and TypeScript, from one page to a full app, wired to the team's
  FastAPI and Go OpenAPI services and served on localhost and PCF. Owns the caller interview and
  design brief, the component-kit choice (shadcn/ui, Radix, Base UI, HeroUI, Mantine, Material UI,
  daisyUI, the animated collections and Motion — mixable), the browser side of the API contract,
  error and action surfaces, runtime configuration, accessibility and motion. Triggers: 'build a UI
  for', 'add a page/form/table/console', 'make this look less generic', 'wire the UI to the API'.
  Not for the service behind the UI (backend-craft) or Grafana dashboards (obs-dashboards to
  design, grafana to operate).
argument-hint: "[the GUI to build or change]"
---

# Frontend craft

Build GUIs for the team's applications: complete, runnable code — components, styles,
configuration, tests and wiring — that an SRE can read during an incident and a user wants to
click. The repository's existing framework, kit, libraries and conventions win over every default
here; the owner decisions apply wherever the repository has not already chosen. Before any code,
two things: ask the caller the forks below, and write the design brief. A page that looks like
every AI-generated page is not finished, and neither is a page that was never rendered.

## Ask before you build

One round, each fork with your recommended default, so the caller can answer "defaults except…".
Ask for a new app or a new area; inside an existing app, read the answers from the repository and
confirm only what it does not settle. Record the answers in the packet.

| Fork | Ask | Recommend when the caller says "whatever's best" |
|---|---|---|
| Audience and job | Who uses it, doing what, how often, under what pressure? | Nothing: this answer shapes everything, so get it |
| Archetype | A console worked all day, a workbench of forms and tables, an overview dashboard, a site people read, a guided workflow? | The archetype nearest the job, named in the brief ([design](./references/design.md)) |
| Kit | A kit the team already uses or wants here? Any they dislike? | shadcn/ui on Base UI with Tailwind v4 and Motion, plus a second kit only for what it does better ([stack](./references/stack.md)) |
| Look | A brand, palette or existing app to match? A mood word? | A new identity from the brief: a chosen hue and tint, a chosen type pairing, one signature element |
| Density and input | Dense or roomy? Mouse-first, keyboard-first, touch? | Visible, clickable actions with full keyboard parity; density from the archetype |
| Motion | How much, and where? | Purposeful: state changes animate, arrivals settle, one orchestrated moment; nothing on every card |
| Live data | Does anything change without a click? | Polling through the query cache; the API's SSE stream when it offers one |
| Serving | Localhost only, or PCF too? Which host, where does the API live? | The Vite dev server proxying the API; on PCF the staticfile buildpack with the API on a context-path route of the same host ([serving](./references/serving.md)) |

## Owner decisions

| Area | Decision |
|---|---|
| Framework | React first: a new app is React 19 on Vite with TypeScript `strict`. Vue is allowed when the caller or the neighbouring apps say Vue; an existing app keeps its framework. |
| Kits | Any kit on the approved list — shadcn/ui (on Base UI, Radix or React Aria), Radix UI, Base UI, HeroUI, Mantine, Material UI, daisyUI, the animated collections (Magic UI, Animate UI, Aceternity UI, React Bits) and Motion — and nothing is banned. Kits may be mixed: one base kit owns the reset, the tokens and the provider; others join for the components they do better, under the mixing rules in the stack reference. No single product line. |
| Look | No house theme. Every app gets its own identity from the design brief on the parametric tokens; the generic AI look is a defect, not a default. |
| Interaction | Visual and clickable first: the action sits where the eye is, with keyboard and screen-reader parity. Keyboard-first density is a choice for consoles whose users ask for it, not the register. |
| Motion | Welcome and budgeted: animation explains state and rewards action; reduced motion is a first-class variant of every animation. |
| API | The UI consumes the team's FastAPI and Go services through their OpenAPI documents: a generated typed client, RFC 9457 problems carrying a request ID, cursor pages, an `Idempotency-Key` on writes. |
| Serving | Localhost through the Vite dev server with the API proxied; PCF through the staticfile buildpack, or the nginx buildpack when it needs more, with runtime configuration and a CSP. |

## What every GUI does

1. **Looks chosen.** Load the [design reference](./references/design.md), write the brief, set
   the knobs in the theme, pick the type pairing, name the one signature element, and read the
   result against the list of tells. Tokens everywhere, density by decision, light and dark both
   complete.
2. **Is direct.** The action a user wants is visible where they are looking: one primary action
   per view, row actions shown on hover and on focus, buttons with a label (an icon alone needs a
   tooltip and an accessible name), immediate feedback — pressed, pending, done — and undo for
   anything reversible. Shortcuts and a command palette are accelerators, never the only path.
3. **Consumes the contract.** Types generated from the service's OpenAPI document; every failed
   response read with the problem helper; cursors passed back verbatim; writes sent with the
   idempotent-write helper under one key per user intent, the in-flight `409` waited out under that
   key. Never a call to `/health/*`.
4. **Shows errors an operator can act on.** Loading, error and empty states are designed before
   the happy path. Every route and every independent panel sits in an error boundary that renders
   the error card in place: title, next step, the request ID copyable and linked to logs and trace
   when runtime configuration provides the templates, the time with its zone, and a retry only when
   the request is safe to repeat. Every async path ends in a rendered state; a handler never
   re-throws to the page. Boundary catches and unhandled rejections reach the repository's browser
   error reporting with the request ID and the release, without sensitive values. Status never by
   colour alone.
5. **Makes writes safe.** Friction matches blast radius: a reversible action runs at once and
   offers undo; a destructive or bulk action confirms with the exact target, count and environment
   shown and Cancel focused; an irreversible or fleet-wide one also has the user type the target's
   name. Disable the control while the write is pending; report per-item outcomes, including
   unknown. The server is the validation truth: field errors land beside their fields with the
   user's input intact. An action the user may see but not run is disabled with the reason; an area
   they can never use is hidden; the shell shows who is signed in and with what role; the server
   stays the authority.
6. **Builds once, configures at startup.** Environment values load from same-origin
   `config.json` through the runtime-config helper before first render; `import.meta.env` and
   `VITE_*` hold only values identical everywhere, never secrets, because the bundle ships to every
   browser. Every environment shows its name in the shell and in every destructive confirm,
   production most distinctly. The HTML ships with a Content-Security-Policy that forbids framing
   and with `nosniff`; the serving contract is the proof.
7. **Keeps state where it belongs.** Server state in the query cache, with its age visible; UI
   state local; non-sensitive search, filters, page, sort and tabs in the URL when they should
   survive a refresh or be shared; no global store until two distant components genuinely share.
   Tables choose pagination or virtualization from rendered rows, interaction and measured cost;
   virtualization never stands in for a filter the server should apply.
8. **Treats content as data.** API, log and user text render as text, never through
   `dangerouslySetInnerHTML` or `innerHTML`; rich text passes the repository's sanitizer (DOMPurify
   if none); a data-driven `href` or `src` allows only `http:`, `https:` and `mailto:`. Timestamps
   show the zone (UTC unless the repository sets another) with relative time only beside them;
   numbers format through `Intl`; server decimals such as prices never touch floating point.
   Account and client identifiers and personal data are masked until the user reveals them —
   consoles are screen-shared on bridges — and never enter URLs, page titles or telemetry.
9. **Is accessible by construction.** Semantic HTML, labelled inputs, keyboard access, visible
   focus; focus moves to the main heading on navigation and stays put on same-view updates;
   saving, completion and error status reach assistive technology without stealing focus; layouts
   reflow at 320 CSS px; targets are at least 24 by 24 px; motion honours `prefers-reduced-motion`;
   AA contrast in both themes (the theme's test proves it at every hue); every chart has a text or
   table alternative. Widget behaviour — focus traps, ARIA state, arrow keys — comes from a kit's
   primitives, never hand-rolled; simple controls stay native `<button>`, `<a>` and `<input>`.
10. **Moves with purpose.** Motion for state changes, arrivals, attention and spatial continuity:
    CSS for hovers, fades and enter/exit; Motion for orchestration and layout; view transitions for
    navigation; an animated collection for the brief's one orchestrated moment. 150 to 300 ms on
    opacity and transform, no choreography on page load, and a reduced-motion variant of every
    animation.
11. **Adds dependencies deliberately.** A maintained, typed library whose licence fits (the stack
    reference records each kit's) is ordinary work inside an authorized change; name every addition
    and its licence in the packet. Ask the caller before a second framework, a second test runner,
    or a global store.

## Done means

Typecheck and lint clean. Component tests for changed behaviour, with MSW at the network boundary
and the contract cases covered: a `500` renders its request ID, a `422` lands on its fields,
`next_cursor` loads the next page, a retried write reuses its key. The starting files' own tests
green inside the app. The serving contract run against the built app whenever the build or serving
changed. For a bug, the failing regression first.

Then render it. With Playwright or the available browser tool, screenshot every changed view in
light and dark, at a desktop width and at 320 px, and look at the screenshots: hierarchy,
legibility, each state, the list of tells. Run axe on the loaded page. Walk the changed
interactions by keyboard. Put the brief and the screenshot paths in the packet. Without a browser,
component and accessibility tests stand in and the missing render is a named gap; never add
Playwright or download browsers without the caller's approval. The production build ships the
page's stylesheet; a page in browser defaults is not done. A UI never rendered is written, not
verified.

## Starting code

Read each file and write its contents into the app with the editor tools, adapting names to the
app; the skill's folder sits outside the workspace, so a shell copy from it is refused or prompts.

| File | Where it goes | What it settles |
|---|---|---|
| [theme.css](./assets/theme.css) | `src/styles/theme.css`, imported before any kit stylesheet | The parametric tokens, light and dark, the Tailwind and shadcn bridges |
| [problem.ts](./assets/problem.ts) and [its test](./assets/problem.test.ts) | Beside the API client | House problems, FastAPI's native shapes and gateway HTML all read as one `Problem` |
| [idempotent-write.ts](./assets/idempotent-write.ts) and [its test](./assets/idempotent-write.test.ts) | Beside the API client | One key per intent; an in-flight `409` waited out under the same key |
| [runtime-config.ts](./assets/runtime-config.ts) and [its test](./assets/runtime-config.test.ts) | The app's bootstrap | `config.json` validated before first render, every missing field named |
| [error-panel.tsx](./assets/error-panel.tsx), [its stylesheet](./assets/error-panel.css) and [its test](./assets/error-panel.test.tsx) | Shared components | The per-panel boundary and the error card, drawn from the tokens |
| [vite.config.ts](./assets/vite.config.ts) | The app root | React Compiler, Tailwind, the API proxy, Vitest |
| [Staticfile](./assets/pcf/Staticfile), [spa.conf](./assets/pcf/nginx/conf/includes/spa.conf), [manifest.yml](./assets/pcf/manifest.yml) and [profile.sh](./assets/pcf/profile.sh) | The PCF deploy directory | Headers, caching, the SPA fallback, runtime configuration written at container start |
| [serving-contract.mjs](./assets/serving-contract.mjs) | Beside the build configuration | The acceptance test for serving, run locally and against each environment |

## Before you write it — load the reference for what you're building

| If the work involves… | Read first |
|---|---|
| any new page, view or app, or a visual change larger than a component | [Design](./references/design.md) |
| a new app; choosing, adding or mixing kits; the toolchain; data, routing, forms, tables, charts or motion libraries | [Stack](./references/stack.md) |
| API requests, caching, pages, writes, error display, live data, test doubles | [API](./references/api.md) |
| the build, runtime configuration, local development against the API, serving on PCF, the CSP | [Serving](./references/serving.md) |
| a Vue app | [Vue](./references/vue.md) |

Load every matching row. Before recommending a hosting, runtime or platform change, also load
`stack-profile`.
