# Default design language — designed, not default

Read only for a greenfield or unbranded UI. An existing brand or design system always wins. The
universal rules live in `../SKILL.md`.

Before styling, record a small design plan: audience, workflow density, page/surface/accent/status
tokens, type choices, and one signature element tied to this product. Every visual choice should be
traceable to that plan; if the same plan could describe any dashboard, it is not specific enough.

## App shell and composition

- Use a persistent sidebar when navigation has more than roughly five destinations; reserve top
  tabs or a single column for focused tools. Collapse the rail on narrow screens.
- Daily-use operator surfaces should be dense, calm, and scannable. Put expressive moments in login,
  onboarding, empty, or overview states—not in every table row.
- A mostly empty viewport is a composition defect. Add honest supporting context or constrain the
  canvas; do not invent metrics merely to fill space.

## Visual character

- Build depth with layered surfaces, restrained borders, and selective elevation. If every surface
  glows or lifts, none has hierarchy.
- Use one primary accent confidently. Categorical KPI colors encode distinct meanings and always
  pair color with a label or icon.
- Use theme tokens for every color, ship light/dark/system, and render the correct theme before first
  paint. Self-host fonts required by the chosen design; use tabular numerals for dense data.
- Design loading, error, and empty states as part of each view, not as fallback markup.

## Motion

- Keep transitions short, interruptible, and tied to state change. Prefer opacity/transform and
  respect `prefers-reduced-motion`.
- Choose one orchestrated moment per view. Simultaneous glow, hover lift, stagger, and number
  animation reads as noise rather than craft.
