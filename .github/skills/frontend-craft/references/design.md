# Design: an identity for every app

Choose an identity for the app from its audience and work. Honour a caller-supplied brand or
design system; otherwise use the brief below.

## Contents

- [The brief](#the-brief)
- [Catch unchosen defaults](#catch-unchosen-defaults)
- [Archetypes](#archetypes)
- [Colour and density](#colour-and-density)
- [Type](#type)
- [Visible actions and feedback](#visible-actions-and-feedback)
- [Motion](#motion)
- [Words and review](#words-and-review)

## The brief

Record these decisions before styling, using known facts and asking only about consequential
gaps. Keep it short enough to guide implementation and review.

1. **Audience and job:** who uses the app, for which workflows, how often and under what pressure.
2. **Archetype:** the nearest row below, or a named blend.
3. **Palette:** brand and surface hues/chroma, default theme and relationship to status colours.
4. **Type:** faces and their roles, scale and self-hosting; choose a pairing below or a deliberate
   alternative.
5. **Layout and density:** shell, alignment, primary action and sticky regions; add a sketch when
   it clarifies the structure.
6. **Signature and motion budget:** the app's distinguishing element or composition, the state
   changes that animate and their reduced-motion behaviour. A signature may be a strong masthead
   or carefully set table; it need not animate or repeat on every page.

One identity per app; a shared family resemblance is optional. Set the theme's knobs from the
brief and build the shell around the first real workflow.

## Catch unchosen defaults

These are review prompts, not bans. A deliberate owner choice is valid; an accidental default
that conflicts with the brief needs replacing.

- **Type:** an unchosen Inter, Geist, Space Grotesk, Plus Jakarta Sans, Poppins, DM Sans or system
  stack; tracked uppercase eyebrows everywhere; gradient headlines; decorative monospace.
- **Colour:** stock purple/blue gradients, neon on near-black, all-slate surfaces, cream and
  terracotta, pastel washes, or brand and status colours that cannot be distinguished.
- **Layout:** centred hero/two buttons/three cards regardless of the job; identical rounded
  cards, unnecessary bento grids, metric tiles as the only hierarchy, sparkle-icon sidebars.
- **Chrome:** glass, card lifts/glows, scroll entrances, pills, gradient borders or dotted grids
  repeated without purpose; arrows on every link; emoji standing in for a coherent icon set.
- **Words:** “Welcome back”, “Powerful”, “Seamless”, “Supercharge”, generic “Submit” buttons,
  apologetic errors and placeholder content.

## Archetypes

Use these as starting shapes; blend where the workflow changes.

| Archetype | Shape and interaction | Starting density/theme | Motion |
|---|---|---|---|
| Operator console | Queue or system worked all day; toolbar over dense data, details drawer, mono logs/events | Compact (0.85–0.95); dark | State changes and arrivals |
| Workbench | Lists beside editing forms, master-detail, field validation, visible primary actions | Standard (1); light | Dialogs, drawers and action feedback |
| In-app dashboard | Hierarchical overview, charts with units and shared time range, drill-down | Standard; app theme | Values and chart transitions |
| Status or catalog site | Reading measure, strong typography, structure that explains the content | Roomy (1.05–1.15); light | An expressive moment if it serves the brief |
| Guided workflow | Focused steps, progress and a review before commit | Standard; light | Step transitions and completion |

## Colour and density

The [theme](../assets/theme.css) derives colours in OKLCH. Set `--brand-hue`,
`--brand-chroma`, `--surface-hue` and `--surface-chroma`; a separate surface hue allows a
two-tone identity. Brand marks actions and focus. Status has fixed ok, warn, critical, info and
unknown hues with words/icons; categorical chart colours remain distinct. Prioritize the worst
state in status lists when urgency is the task.

Ship both themes. Follow the brief's default, or the OS when it leaves one open, and persist the
user's choice with the [theme boot](./serving.md#security-headers-and-the-csp). Verify actual
combinations, including charts and kit overlays; the theme's contrast tests cover its supplied
tokens, not every possible composition.

The density knob scales spacing, rows and controls together. Use a coherent spacing/type scale,
right-aligned numeric columns with `tabular-nums`, and hierarchy through size and weight. For
consoles, make the current destination, toolbar, data age, selected row and stream state easy to
find; use sticky headers where they help. For reading, keep lines below about 80 characters and
use rhythm, borders and numbering to express structure.

## Type

Self-host fonts through `@fontsource`, variable where available. Give each face a role: UI,
heading/display, or identifiers/logs/code. These are options, not a required catalogue:

| Pairing | Useful character |
|---|---|
| IBM Plex Sans + IBM Plex Mono | Engineered consoles and workbenches |
| Source Sans 3 + Source Code Pro | Quiet, compact data and forms |
| Public Sans + JetBrains Mono | Clear status sites and catalogs |
| Atkinson Hyperlegible Next + Commit Mono | Legibility on shared screens |
| Hanken Grotesk + Martian Mono | Crisp dashboards |
| Instrument Sans + Instrument Serif | Editorial sites |
| Schibsted Grotesk + Fira Code | Status pages and timelines |
| Bricolage Grotesque over Albert Sans | Distinctive display headings |
| Fraunces or Newsreader over Source Sans 3 | Warm editorial catalogs |
| Red Hat Text + Red Hat Display | Open, friendly guided workflows |

A system stack is also valid when deliberately chosen for the audience or operating constraints.

## Visible actions and feedback

Put the primary action where the user looks; one primary per view. Row/card actions appear on
hover and focus and remain available to touch users. Shortcuts and command palettes accelerate
visible paths. Buttons have labels; icon-only controls have accessible names and tooltips.

Use immediate local pressed, pending and completion feedback. Toasts suit outcomes elsewhere;
undo belongs with a reversible result. Use direct manipulation when useful—reordering, resizing,
row selection or inline editing—with keyboard alternatives and stable layouts.

## Motion

Budget motion for state, attention and spatial continuity. Use the theme's fast/base/slow
durations, usually 150–300 ms on opacity and transform.

| Need | Tool |
|---|---|
| Hover, press, focus, toggle | CSS transitions |
| Native dialog/popover entry and exit | `@starting-style` and `transition-behavior: allow-discrete`, or kit behaviour |
| React-managed entry/exit and reordered lists | Motion `AnimatePresence` and `layout` |
| Navigation | React `<ViewTransition>` or the View Transitions API |
| Changing numbers | Short value tween with tabular digits |
| An expressive sequence chosen in the brief | Motion or an approved animated collection |

Avoid motion that obstructs work: gratuitous load count-ups, card lifts everywhere, pulsing glows
and parallax on data. Every animation respects `prefers-reduced-motion` (and
`useReducedMotion` in Motion), preserving information through a fade or instant change.
No page owes an orchestrated entrance.

## Words and review

Use the audience's vocabulary, sentence case and active verbs: “Cancel order” remains “Cancel
order” through confirmation and feedback. Errors explain what happened and the next step; empty
states suggest an action. Use realistic, clearly labelled sample content when real data is
unavailable.

Inspect the rendered app against the brief: hierarchy, legibility, identity, density, every state
and both themes. Replace unchosen defaults and remove decoration that competes with the work.
