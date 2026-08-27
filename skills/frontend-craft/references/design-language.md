# Default design language — designed, not default

Read only for a greenfield or unbranded UI with nothing to match — no brand, no design system, no
established visual conventions. Any of those always wins: match it and leave this file unread. The
invariants (theme tokens, no-flash theme, status never by color alone, designed states, composition)
live in `../SKILL.md`; this file owns the *choices* those rules leave open.

Before styling, record a small design plan: audience, workflow density, page/surface/accent/status
tokens, type choices, and one signature element tied to this product. Every visual choice should be
traceable to that plan; if the same plan could describe any dashboard, it is not specific enough.

The bar: organized and uncluttered is the floor, not the ceiling. Aim to sit at home next to Linear
or Vercel's dashboard with the color courage turned up — never mistakable for an unstyled admin
template.

## App shell and composition

- **Default to a sidebar rail.** Any app with more than ~5 destinations gets a persistent left
  sidebar rail, not top tabs (tabs don't scale past a handful): icon + label nav grouped by area,
  the active item marked with an accent bar or tint, a brand mark at the top and the user/account
  with theme toggle pinned at the bottom. The rail collapses to icons-only on narrow viewports and
  to a drawer on mobile. Top tabs or a single-column layout are reserved for genuinely small apps
  (≤5 views) or a focused single-purpose tool.
- **Spacing grid** on a consistent 4/8px scale: generous whitespace at decision points, higher
  density where data lives.
- **Typography**: 4–5 sizes total; hierarchy through size and weight, never color alone. A quality
  UI font (Inter or similar, self-hosted — no CDN dependency), tight letter-spacing on large
  headings, `tabular-nums` for data, big confident numbers on stat tiles.
- Daily-use operator surfaces are dense, calm, and scannable. Put expressive moments in login,
  onboarding, empty, or overview states — not in every table row.

## Visual character

- **Dark-first, layered surfaces.** Dark is the designed-for theme; light stays fully supported
  through the same tokens, and the app ships a manual light/dark/system toggle, persisted and
  defaulting to the OS setting. A deep page background, cards a distinct step lighter, raised
  elements a step lighter again. Depth comes from this layering plus low-alpha borders and soft
  shadows — not heavy lines.
- **Color with courage.** One vivid accent used confidently: gradient touches on primary actions
  and active states, and one hero moment per view — a gradient heading, a glowing stat. Status
  colors saturated enough to glow against dark surfaces (each still paired with its dot and text).
- **Categorical accents on KPI grids.** When a view shows a row of distinct metrics or stat cards,
  give each its own accent hue (e.g. purple / teal / amber / cyan) rather than repeating one color —
  the color *codes* the category, with the icon and number tinted to match. Elevate one card above
  the rest (an accent border-glow on the most important metric) so the grid has a focal point. Keep
  the accent set to ~4–5 hues drawn from the theme tokens; this is categorical coding, not a rainbow.
- **Depth cues, spent sparingly.** Rounded-xl cards, soft elevation shadows, hover lift (small
  translate + shadow), accent-colored focus rings. If every surface is elevated, nothing is.
- Icons anchor navigation, actions, and stats.

## Motion

Choose one orchestrated moment per view. Hover lifts, pressed states, animated number changes on
live stats, staggered list entrances (30–50 ms steps), and smooth expand/collapse are the
vocabulary; simultaneous glow, lift, stagger, and number animation reads as noise rather than craft.
Transitions 150–250 ms, ease-out, animating `opacity` and `transform` only; if an animation makes the
user wait, cut it; respect `prefers-reduced-motion`.

## Self-critique as you build

Screenshot what you made and look at it: would a stranger read it as a templated default?
Generated UIs cluster around a few stock looks (cream page + serif display + terracotta accent;
near-black + one acid accent; hairline-rule broadsheet) and stock component tells (uniform
rounded-2xl, purple-to-indigo gradients as the default aesthetic, a shadow on every surface) — a
look you fell into is not a decision you made; change one real thing. Spend your boldness in one
place: one deliberate risk you can justify, everything around it quiet. Bespoke work sources its
distinctive choices from the subject's own world — its materials, instruments, vernacular — never a
house style carried from the last project.
