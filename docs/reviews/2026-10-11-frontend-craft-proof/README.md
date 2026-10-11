# Rendered proof of the rewritten frontend-craft (2026-10-11)

The owner approved a rendered proof of the skill's own defaults before accepting the rewrite
([decision](../../decisions/2026-10-11-frontend-craft-generalized.md)). This packet holds the
screenshots and what the build established. The app was scaffolded and built in the session's
scratchpad by following the skill as written, not from any prior app; it is not committed, and
every number below is from that build on 2026-10-11.

## The brief the build followed

- **Audience and job:** SREs watching and controlling service rollouts across PCF foundations
  during the trading day.
- **Archetype:** operator console; density 0.92; dark default with the light theme complete.
- **Palette:** brand hue 196 (teal, chroma 0.14) on surfaces tinted toward hue 232 (chroma
  0.022): a two-tone identity, not the theme's shipped values.
- **Type:** Public Sans Variable for the UI, JetBrains Mono Variable for identifiers and times,
  both self-hosted through `@fontsource-variable`.
- **Layout:** a top bar with the environment badge; a toolbar row (title, live pill, foundation
  segmented control, status filter, the one primary action); a dense worst-first table beside a
  details panel.
- **Signature and motion:** the rollout's step timeline, drawn in with a staggered Motion
  sequence when a rollout is selected; row actions on hover and focus; an undo bar for pause and
  resume; the error-rate sparkline. Reduced motion collapses every animation.

## What was built, with what

| Piece | Version used |
|---|---|
| Vite / @vitejs/plugin-react / oxc-transform-react (React Compiler on) | 8.3.4 / 6.1.2 / 0.152.0 |
| React | 19.3.0 |
| TypeScript | 6.0.3 (pinned to 6.x per the stack reference) |
| Tailwind CSS | 4.3.3 |
| shadcn/ui CLI 4.21.4 on `@base-ui/react` | 1.9.0, preset `vega` |
| Motion | 14.1.0 |
| Vitest | 5.0.3 |

Starting files written in from the skill unchanged: `theme.css` (with the brief's knobs set in
the entry stylesheet), `problem.ts`, `idempotent-write.ts`, `runtime-config.ts`,
`error-panel.tsx` with its stylesheet and test, `vite.config.ts`. Runtime configuration loads
from `public/config.json` before first render, and the shell shows the environment badge from it.

## Results

| Check | Result |
|---|---|
| `tsc -b` | clean [verified] |
| `vitest run` (the error panel's test from the skill, plus four page tests: worst-first order with status as text, the typed-confirmation rollback with Cancel focused, pause with undo, an axe pass in jsdom) | 8 of 8 passed [verified] |
| `vite build` | 63 kB of CSS, one 600 kB JS chunk (Motion, Base UI, Lucide and the kit are all in the one proof bundle; a real app lazy-loads) [verified] |
| axe through Playwright on the built app, dark desktop, light desktop and with the rollback dialog open | 0 violations in each [verified] |
| Layout at 320 CSS px | single column; the table scrolls in its own container; no page overflow after two fixes to the proof page [verified] |
| Font in use | Public Sans Variable in every screenshot; the CSS bundle contains no Inter [verified] |

Screenshots: [dark desktop](dark-desktop.png), [light desktop](light-desktop.png),
[rollback dialog](dark-desktop-rollback-dialog.png), [dark at 320 px](dark-mobile-320.png).

## What the proof found in the skill, and what changed

- The shadcn CLI's `init` installs `@fontsource-variable/inter` and sets Inter as the font
  by default, and stops unless Tailwind is already imported. The stack reference now carries the
  post-init steps that remove that look and bridge the theme's tokens.
- `react({ compiler: true })` needs the optional `oxc-transform-react` package; TypeScript 6
  rejects `baseUrl`, so the `@` alias is `paths` alone with a matching Vite alias. The starting
  `vite.config.ts` and the stack reference now say so.
- The theme's Tailwind bridge originally mapped `--font-sans` to a token of the same name, which
  Tailwind would emit as a self-reference; the knobs are now `--font-ui`, `--font-code`,
  `--font-title`, `--elevation-*` and `--easing-*`.
- The error card rendered unstyled (the first dark-desktop build showed it as stacked plain
  text); it now ships `error-panel.css`, drawn from the tokens.
- The faint ink token failed AA at small sizes in both themes (axe: seven nodes at 3.8 to 4.3
  against 4.5); it is now AA on every surface, and the repository test sweeps it with the rest.
- The error card's time formatter combined `dateStyle` with `timeZoneName`, which
  `Intl.DateTimeFormat` rejects; it now uses explicit components so the zone shows.
- The boundary's retry re-rendered the children before the caller could clear the cause; it now
  calls `onReset` first.

## Not verified

- Nothing was deployed: the PCF deploy files were reproduced against the staticfile buildpack's
  own nginx template on a local nginx 1.24, where the serving contract passed with every file-like
  path answering 404 and client routes serving the app, but not on a foundation.
- The proof app was not run against a real FastAPI or Go service; its data is static and the API
  helpers are exercised by their own node tests and the error card, not by live requests.
- One build on one host; no clean-room agent trial has yet used the rewritten skill end to end.
