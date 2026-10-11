# Design: an identity for every app

Read before any new page, view or app, and before any visual change larger than a component,
whether or not the request mentions a look. An existing brand, design system or established look
wins: match it and build within it. Browser defaults are not a look, and neither is the look an AI
reaches for when nobody chose; that one is listed below so you can recognise it and replace it.
The accessibility and content rules live in the parent file; this file owns the choices those
rules leave open.

## Why the generic look happens

Every unchosen detail falls to a default, and the defaults are the same for every tool that has
one: the font nobody picked, the indigo nobody picked, the card grid nobody picked. The page is not
ugly; it is anonymous, and a user who has seen it on ten other sites trusts it less. The cure is
not a house style, which would be one more default, but a decision for each detail that carries
identity. The brief forces those decisions; the tells catch the ones that slipped.

## The tells: recognise and replace

Each is fine when the brief asked for it. None is a choice when it appears by default.

- **Type.** Inter, Geist, Space Grotesk, Plus Jakarta Sans, Poppins, DM Sans or the system stack
  as the whole identity; an all-caps tracked eyebrow above every heading; gradient-filled headline
  text; monospace as decoration.
- **Colour.** Indigo-to-violet or purple-to-blue gradients; one neon accent on near-black; slate
  everything; a warm cream page with terracotta; pastel washes behind sections; brand and status
  in the same hue.
- **Layout.** A hero with a centred headline, two buttons and three feature cards; everything in
  identical rounded cards with one radius and one soft shadow; a bento grid for content that is not
  a grid; metric tiles with a big number and a tiny caption as the only idea; centred text
  everywhere; a sidebar with the product name beside a sparkle icon.
- **Chrome.** Glassmorphism; a hover lift and a glow on every card; fade-and-slide-up on every
  section as it scrolls into view; an arrow appended to every link; meta strings joined with middle
  dots; emoji as icons; pill badges on everything; gradient borders; a dotted-grid background.
- **Words.** "Welcome back", "Powerful", "Seamless", "Supercharge", "Your dashboard"; apologetic
  errors; lorem ipsum; placeholder names such as Acme and John Doe; every button saying "Submit".

## The brief: six decisions, written before any styling

Ten to fifteen lines in the packet. Read each line against the tells; anything that matches one
is a default, not a choice.

1. **Audience and job.** Who, doing what, how often, under what pressure. A support desk working
   a queue during the open is a different page from a manager glancing at a status board.
2. **Archetype.** The nearest row of the table below, or two rows blended with the split named.
3. **Palette.** The brand hue and its chroma; whether surfaces take the same hue or a second one;
   whether the app defaults to dark or light. The status set is fixed by the theme. Pick the hue
   from the subject — markets, risk, settlement, infrastructure each suggest a temperature — not
   from habit, and two apps on the same team share a hue only when they are one product.
4. **Type.** One pairing with a role for each face, from the table below or a deliberate
   alternative, self-hosted through `@fontsource`. A display face is allowed for the one signature
   element. Name the scale: the theme's seven steps, or a tighter or looser one.
5. **Layout and density.** One sentence and an ASCII sketch with alignment; the shell (top bar,
   sidebar, tabs or a single column); the density knob; where the primary action lives; what is
   sticky.
6. **The signature and the motion budget.** One element that carries the identity — a live
   number, a timeline, a map, a wall of sparklines, a strong masthead, a hand-set table — and the
   motion budget: which state changes animate, the one orchestrated moment if any, and what the
   reduced-motion variant does.

Then set the knobs in the theme to match, and build the shell before the first feature.

## Archetypes

Pick the nearest; blend when a page serves two jobs, and say where it switches.

| Archetype | Who and what | Shape | Density and theme | Motion budget |
|---|---|---|---|---|
| **Operator console** | People working a queue, an incident or a system through the day: order flow, rollouts, log tails | A top bar or grouped sidebar; a toolbar row above dense data; a details panel or drawer; log and event views in mono | Compact (0.85 to 0.95); dark by default with a complete light theme | State changes and arrivals only; no page-load choreography |
| **Workbench** | Admins and support staff creating and editing records: accounts, limits, configurations | Lists beside forms; a master-detail split; clear primary actions; validation beside fields | Standard (1); light by default | Dialogs, drawers and confirmations; micro-feedback on every action |
| **Dashboard in the app** | Leads and operators checking state at a glance, then drilling in | Overview tiles with real hierarchy; charts with units and one shared time range; drill-down links | Standard; follows the app's theme | Charts settle on load; values tick; nothing bounces |
| **Status or catalog site** | Anyone arriving to understand: a platform status page, a service catalog, an internal product's front door | A measure for reading; typography that carries the page; one memorable element; structure that encodes meaning | Roomy (1.05 to 1.15); light by default | One expressive moment; everything else quiet |
| **Guided workflow** | A person completing a bounded task: onboarding a client, raising a change, running a checklist | One column; numbered steps with progress; one thing per screen; a review step before commit | Standard; light by default | Step transitions and completion |

A page that serves two audiences, such as a status overview with drill-down, is a site at the top
and a console once the user is working.

## Colour

The theme derives every colour from a brand hue and a surface hue in OKLCH, so each app is a new
palette rather than a new theme file. Set `--brand-hue`, `--brand-chroma`, `--surface-hue` and
`--surface-chroma` from the brief; a second surface hue gives a two-tone identity (warm surfaces
under a cool brand) that no default produces. Surfaces layer by lightness in the dark theme and by
shadow in the light one; lines are low-alpha so they sit on any surface. The brand colour is for
action and focus — buttons, links, the active item, the ring — and never for status.

Status is a vocabulary: ok, warn, critical, info and unknown, one fixed hue each, always paired
with a word or an icon, with categorical chart colours kept distinct from it. Lists of things with
a state put the worst first. Both themes ship complete: the default follows the OS, the user's
choice persists through the boot script in the serving reference, and the repository's test
proves AA contrast at every brand hue in both themes.

## Type

Self-host every face through its `@fontsource` package, variable where one exists; a fetch from a
public font service leaves the app's origin and the CSP. One family carries the UI; a second,
clearly different, carries headings or data when the brief wants contrast; one mono face for
identifiers, logs and code, with `tabular-nums` on every column of numbers. Pairings with
character, none of them the default anywhere:

| Pairing | Character | Fits |
|---|---|---|
| IBM Plex Sans + IBM Plex Mono | Engineered, even, serious | Consoles and workbenches read all day |
| Source Sans 3 + Source Code Pro | Quiet, humanist, compact | Dense data and forms |
| Public Sans + JetBrains Mono | Civic, clear, a little stern | Status sites and catalogs |
| Atkinson Hyperlegible Next + Commit Mono | Built for legibility first | Consoles read on shared screens and bridges |
| Hanken Grotesk + Martian Mono | Crisp and contemporary | Dashboards |
| Instrument Sans + Instrument Serif | Editorial contrast between body and display | Sites and front doors |
| Schibsted Grotesk + Fira Code | News desk, confident | Status pages and timelines |
| Bricolage Grotesque for display over Albert Sans | Strong, idiosyncratic headings | The signature element on a site |
| Fraunces or Newsreader for display over Source Sans 3 | Warm editorial serif | A catalog or an announcement page |
| Red Hat Text + Red Hat Display | Friendly, open, rounded | Guided workflows |

A system-stack face in the shipped app is either a recorded choice with a reason (a kiosk, a
locked-down browser) or a defect.

## Density and layout

The density knob scales spacing, row height and control height together. A 4 px grid, a type
scale of seven steps, `tabular-nums` on numbers, and hierarchy through weight and size rather than
colour. A console page has a shape: a shell with the current destination marked; a toolbar row
holding the title, the live or data-age indicator, filters and primary actions, sticky while the
content scrolls; dense tables with sticky headers, right-aligned numbers, status as a pill with
text and the selected row visible; panels with a heading row, never a bare heading on the page
canvas; logs in mono with level filters as a segmented control and the stream state as a pill. A
site page has a measure: running text under 80 characters, generous vertical rhythm, borders and
numbering that encode something about the content.

## Visual and clickable

The team's users look, then click. Design for that:

- Every row, card and tile that can be acted on shows its actions on hover and on focus, and the
  most common action is one click; a context menu holds the rest. Nothing requires remembering a
  shortcut, though shortcuts and a command palette speed up the people who learn them.
- Buttons look like buttons: a filled primary, an outlined or quiet secondary, a destructive
  variant that is red only when it is dangerous. Every button has a label; an icon-only control
  has a tooltip and an accessible name. One primary action per view.
- Feedback is immediate and local: a pressed state, a pending spinner inside the control itself, a
  success state that lasts long enough to see, and a toast only for outcomes that happen somewhere
  else, with undo in the toast for reversible actions.
- Direct manipulation where it is natural: drag to reorder a list, resize a panel, select rows
  with a checkbox column and a shift-click range, edit a cell in place.
- Targets at least 24 by 24 CSS px, 44 for touch; hover states that never move content; cursors
  that say what will happen.

## Motion

Motion is welcome. It explains what changed, where something came from and where it went, and it
makes a click feel acknowledged. The theme carries three durations — fast for feedback, base for
state changes, slow for arrivals and the signature moment — on opacity and transform only, and two
curves.

| Animate | How |
|---|---|
| Hover, press, focus, toggle | CSS transitions on the fast duration |
| Enter and exit of dialogs, menus, toasts and drawers | `@starting-style` with `transition-behavior: allow-discrete` for native `<dialog>` and `popover`, or the kit's own; Motion's `AnimatePresence` for React-managed lists |
| Lists that reorder, filter or load more | Motion `layout` animations, so rows slide instead of jumping |
| Navigation between views | React's `<ViewTransition>`, or the View Transitions API directly |
| A number that changes | A short tween on the value with `tabular-nums`; never a count-up on page load |
| The signature moment | One orchestrated sequence from Motion or from a collection (Magic UI, Animate UI, Aceternity UI, React Bits), once, where the brief put it |

Never: an entrance animation on every section as it scrolls into view, a hover lift on every card,
a pulsing glow, parallax on data. Every animation has a reduced-motion variant that keeps the
information — a fade in place of a slide, an instant swap in place of a tween — through
`prefers-reduced-motion` in CSS and `useReducedMotion` in Motion.

## Words are design

Name things as the user does, in sentence case and active voice; a button says what happens
("Cancel order") and the same word follows the action into its toast. Errors say what happened and
what to do, never apologise, never go vague. An empty state names the next action. No lorem, no
filler, no placeholder names: the team's real vocabulary is orders, accounts, markets, exchanges,
services and instances.

## Review the rendered result

Look at the screenshots in both themes and at 320 px. Check hierarchy, legibility, consistency,
each state, and whether the one bold element is the only bold element. Read the page against the
tells. Remove one thing. When no browser is available, the packet names the missing render as a
gap.
