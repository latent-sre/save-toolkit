# Design: two registers

Read before writing any page or view, whether or not the request mentions a look, and before
any visual change larger than a component. An existing brand, design system or established look
wins: match it and build within it. Browser defaults are not a look — an app that renders in
them is unbranded, and gets the register and the brief below. The accessibility, token and
status rules live in `../SKILL.md`; this file owns the choices those rules leave open.

## Pick the register from the audience

| Register | Who and what | The look |
|---|---|---|
| **Operator console** | People working a queue, an incident or a system during the trading day: tools, dashboards-as-app-features, admin panels | Dense, keyboard-first, dark-first with a full light theme; information density is the feature; motion only to explain a state change |
| **Site** | Anyone arriving to understand, browse or be convinced: a service catalog, a status overview, an internal product's front door | Generous space, one memorable moment, typography that carries personality; expressive motion is welcome in that one moment |

Most tools are consoles. A page that both audiences use (a status overview with a drill-down)
is a site at the top and a console once the user is working.

## Write the design brief first

Ten lines, in the review packet, before any styling: audience and their job; register; palette
as four to six named colours with the status set beside them; one or two type families and their
roles; a layout concept in one sentence and an ASCII sketch, with alignment; the one element that
is allowed to be bold; the motion budget. Then read the brief against the generic defaults below.
Anything that matches one is a default, not a choice: change it and say why.

## The console register

Start an unstyled app from [the console theme](../assets/console-theme.css): read it, write it
into the app's styles with the editor tools (never a shell copy from the skill's folder), import
it once at the entry point, and build every view from its tokens —
`--surface-*`, `--text*`, `--accent`, the `--status-*` set, the type scale and `--row-height`.
Its base layer already makes semantic HTML look like a console (the `nav > ul` app bar with the
current page marked by `aria-current="page"`, a page gutter on `main`, `[data-panel]` surfaces
with a `header` row, tables, buttons, inputs, focus, `[data-status]` pills, `[role="alert"]`
cards); the view's own CSS adds the layout and the one memorable element. Change the palette when the product has its own, and keep the token names.

A console page has a shape, not just a style:

- **A toolbar row** above the data: the title, the live or data-age indicator, filters and
  primary actions on one line, sticky while the content scrolls.
- **Dense tables** with sticky headers, right-aligned numbers, status as a pill with text, row
  hover, and the selected or focused row visible.
- **Log and event views** in the mono face: timestamp, level as a coloured pill with its word,
  message; level filters as a segmented control; the stream state (live, paused with a waiting
  count, reconnecting, dropped) as a pill in the toolbar; keyboard hints shown as `<kbd>`.
- **Panels** on the panel surface with a heading row (`<section data-panel>` with a `<header>`
  holding the heading and the panel's actions), never a bare heading on the page canvas.

- **Density is designed, not accidental.** A 4/8 px spacing scale with tight row heights, a
  type scale of four or five sizes, `tabular-nums` on every column of numbers, and monospace only
  where it carries meaning: log lines, identifiers, code. Hierarchy through weight and size,
  never colour alone.
- **Dark-first, light-complete.** A deep page surface tinted from the palette rather than a
  neutral near-black; cards one step lighter, raised elements one more; depth from layering and
  low-alpha borders, not heavy lines or shadows. Light theme through the same tokens, with a
  light/dark/system toggle that persists and defaults to the OS.
- **Status is a vocabulary.** One colour per state, paired with text or an icon everywhere it
  appears, with distinct tokens for ok, warning, critical, unknown and in-progress; categorical
  accents for metric groups stay distinct from status. Lists of things with a state put the
  worst first — outage, degraded, unknown, then ok — in both registers.
- **Keyboard-first.** A command palette for navigation and actions, single-key shortcuts for the
  main workflow, focus that moves with the task and is always visible, and dense tables that can
  be navigated row by row.
- **Motion explains.** Transitions of 150–250 ms on `opacity` and `transform` when something
  opens, expands, sorts, confirms or arrives; no decorative entrance animation on page load.

## The site register

- **Open with the most characteristic thing** in the product's world — a live number, a
  headline, a working demo — in the form that fits it. A big number with a small label and a
  gradient accent is the default hero; use it only when it is genuinely the best option.
- **Typography carries the page.** One family, or two that are clearly different; a deliberate
  scale; running text set to a measure in `ch` (under 80 characters); the type treatment is part
  of the design, not a neutral container.
- **Spend boldness once.** One memorable element; everything around it quiet. Animated
  components from a collection belong in that one orchestrated moment, not on every card.
- **Structure is information.** Borders, numbering, dividers and labels encode something about
  the content; a numbered sequence means the content is a sequence.

## Generic defaults to recognise and replace

A warm cream page with a high-contrast serif and a terracotta accent. A near-black page with one
acid-green or vermilion accent. Hairline rules, zero radius and newspaper columns. The card kit:
everything in identical rounded cards with one radius and one soft grey shadow, gradient washes
as decoration. Template chrome: an all-caps tracked eyebrow above every heading, meta strings
joined with middle dots, a `→` appended to every link, tinted near-black standing in for black,
monospace as a decorative label style. Fade-and-slide-up on every section and a hover lift on
every card. Each is fine when the brief asks for it; none is a choice when it appears by default.

## Words are design

Name things as the user understands them, in sentence case, active voice; a button says what
happens ("Close incident"), and the same word follows the action through its toast. Errors say
what happened and what to do, never apologise, never vague. An empty state invites the next
action. No lorem, no filler, no placeholder names.

## Review the rendered result

Render the view and look at it: hierarchy, legibility, consistency, each state, and whether the
one bold element is the only bold element. Remove one thing. When no browser is available,
follow the parent skill's verification and gap-reporting rules.
