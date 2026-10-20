# Design: an identity for every app

Choose an identity for the app from its audience and work. Honour a caller-supplied brand or
design system; otherwise record a short brief before styling:

1. **Audience and job:** who uses the app, for which workflows, and under what pressure.
2. **Archetype:** the nearest row below, or a named blend.
3. **Palette:** brand and surface hues/chroma (`--brand-hue`, `--brand-chroma`, `--surface-hue`,
   `--surface-chroma`), default theme and status-colour separation.
4. **Type:** UI, display and mono faces (`--font-ui`, `--font-title`, `--font-code`) self-hosted
   via `@fontsource`, or a deliberate system stack.
5. **Layout and density:** shell, `--density`, alignment, primary action and sticky regions.
6. **Signature and motion budget:** distinguishing composition, animated transitions and
   reduced-motion behaviour.

One identity per app. Set [theme.css](../assets/theme.css) knobs from the brief and build the
shell around the first real workflow.

## Catch unchosen defaults

Replace accidental defaults that conflict with the brief:

- **Type:** unchosen Inter, Geist, Space Grotesk, Plus Jakarta Sans, Poppins, DM Sans or system
  stack; tracked uppercase eyebrows everywhere; gradient headlines; decorative monospace.
- **Colour:** stock purple/blue gradients, neon on near-black, all-slate surfaces, cream/terracotta,
  pastel washes, or brand colours indistinguishable from status colours.
- **Layout & chrome:** centred hero + three cards regardless of the job; bento grids or metric
  tiles as the only hierarchy; glass, card lifts/glows, scroll entrances, gradient borders, dotted
  grids, arrows on every link, or emoji replacing a coherent icon set.
- **Words:** marketing filler ("Welcome back", "Powerful", "Seamless"), generic "Submit" buttons,
  apologetic errors and placeholder content. Use sentence case and active verbs ("Cancel order"
  stays "Cancel order" through confirm and toast).

## Archetypes

| Archetype | Shape and interaction | Starting density/theme | Motion |
|---|---|---|---|
| Operator console | Queue or system worked all day; toolbar over dense data, details drawer, mono logs/events | Compact (0.85–0.95); dark | State changes and arrivals |
| Workbench | Lists beside editing forms, master-detail, field validation, visible primary actions | Standard (1); light | Dialogs, drawers and action feedback |
| In-app dashboard | Hierarchical overview, charts with units and shared time range, drill-down | Standard; app theme | Values and chart transitions |
| Status or catalog site | Reading measure (<80ch), strong typography, structure that explains content | Roomy (1.05–1.15); light | Expressive moment if in brief |
| Guided workflow | Focused steps, progress and review before commit | Standard; light | Step transitions and completion |

## Colour, density and type

Ship both light and dark themes; follow the brief's default (or OS preference) and persist the
user's choice with the [theme boot script](./serving.md#security-headers-and-the-csp). Status uses
fixed ok, warn, critical, info and unknown hues paired with text/icons; categorical chart colours
stay distinct. Prioritize the worst state in status lists. Right-align numeric columns with
`tabular-nums`.

Font pairings (options, variable where available):
**IBM Plex Sans + IBM Plex Mono** (consoles/workbenches) · **Source Sans 3 + Source Code Pro**
(compact data/forms) · **Public Sans + JetBrains Mono** (status/catalogs) · **Atkinson
Hyperlegible Next + Commit Mono** (shared screens) · **Hanken Grotesk + Martian Mono**
(dashboards) · **Instrument Sans + Instrument Serif** or **Fraunces/Newsreader + Source Sans 3**
(editorial) · **Schibsted Grotesk + Fira Code** (timelines) · **Bricolage Grotesque + Albert Sans**
(display) · **Red Hat Text + Red Hat Display** (guided workflows).

## Actions and motion

Put one primary action per view where the user looks. Row/card actions appear on hover and focus
and remain touch-accessible. Icon-only controls require accessible names and tooltips. Provide
immediate pressed, pending and completion feedback.

Use theme durations (120–280 ms on opacity/transform): CSS transitions for hover/press/focus;
`@starting-style` + `transition-behavior: allow-discrete` (or kit primitives) for dialogs/popovers;
Motion `AnimatePresence`/`layout` for mounted/reordered lists; `<ViewTransition>` for navigation.
Respect `prefers-reduced-motion` (`useReducedMotion` in Motion).
