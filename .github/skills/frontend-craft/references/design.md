# Design: an identity for every app

Honour a supplied design system; otherwise record the app's identity in a short brief:

1. **Audience and job:** who uses the app, for which workflows, and under what pressure.
2. **Archetype:** the nearest row below, or a named blend.
3. **Palette:** brand and surface hues/chroma (`--brand-hue`, `--brand-chroma`, `--surface-hue`,
   `--surface-chroma`), default theme and status-colour separation.
4. **Type:** UI, display and mono faces (`--font-ui`, `--font-title`, `--font-code`) self-hosted
   via `@fontsource`, or a deliberate system stack.
5. **Layout and density:** shell, `--density`, alignment, primary action and sticky regions.
6. **Signature and motion budget:** distinguishing composition, animated transitions and
   reduced-motion behaviour.

Set [theme.css](../assets/theme.css) knobs from that brief, not a fleet-wide house theme.

## Catch unchosen defaults

Replace accidental defaults that conflict with the brief:

- **Type:** unchosen stock fonts; tracked uppercase eyebrows, gradient headlines or decorative mono.
- **Colour:** stock purple/blue gradients, neon/near-black, all-slate or pastel/terracotta palettes;
  brand colours that collide with status colours.
- **Layout:** automatic hero/three-card or bento layouts; decorative glass, glows, entrances,
  gradients/dots and emoji that substitute for an intentional hierarchy/icon system.
- **Words:** marketing filler, generic "Submit", apologetic errors and placeholders. Keep action names
  consistent through control, confirmation and outcome (for example "Cancel order").

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

Optional pairings: IBM Plex Sans/Mono for a workbench, Public Sans/JetBrains Mono for a catalog,
or Instrument Sans/Serif for editorial content. Choose for the brief; these are not required fonts.

## Actions and motion

Row/card actions must work on hover, focus and touch. Icon-only controls need accessible names
and tooltips; show pending/completed state at the action.

Use theme durations (120–280 ms on opacity/transform): CSS transitions for hover/press/focus;
`@starting-style` + `transition-behavior: allow-discrete` (or kit primitives) for dialogs/popovers;
Motion `AnimatePresence`/`layout` for mounted/reordered lists; `<ViewTransition>` for navigation.
Respect `prefers-reduced-motion` (`useReducedMotion` in Motion).
