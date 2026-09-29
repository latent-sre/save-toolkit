# Default design language

Read only for a greenfield or unbranded UI with nothing to match — no brand, no design system, no
established visual conventions. Any of those always wins: match it and leave this file unread. The
invariants (theme tokens, no-flash theme, status never by color alone, designed states, composition)
live in `../SKILL.md`; this file owns the *choices* those rules leave open.

Before styling, record the audience, main workflow, density, theme tokens and type choices.
Use those decisions to guide hierarchy and visual character; decoration should serve the workflow.

## App shell and composition

- **Navigation follows the workflow and viewport.** A grouped sidebar suits many destinations;
  tabs or a single column suit focused tasks. Keep destinations labelled and the active one clear;
  use a drawer or another accessible compact layout when space is limited. Destination count alone
  does not dictate the shell.
- **Spacing grid** on a consistent 4/8px scale.
- **Typography**: 4–5 sizes total, hierarchy through size and weight, never color alone. Inter (or
  similar, self-hosted), tight letter-spacing on large headings, `tabular-nums` for data, big
  confident numbers on stat tiles.

## Visual character

- **Dark-first, layered surfaces.** Dark is the designed-for theme; light stays fully supported
  through the same tokens, with a manual light/dark/system toggle, persisted and defaulting to the
  OS setting. A deep page background tinted from the design plan's palette, not a neutral
  near-black; cards a step lighter, raised elements a step lighter again;
  depth from layering plus low-alpha borders and soft shadows, not heavy lines.
- **Accent with purpose**: derive the accent from the design plan and use it for primary actions
  and active states. Gradients or a
  hero treatment are optional when they help communicate the product. Status stays distinct and
  paired with text or an icon.
- **Categorical KPI accents**, when they help distinguish metric groups: draw a small set of hues
  from theme tokens, keep categories distinct from status, and emphasize metrics by importance.
- **Depth cues, spent sparingly**: use borders, elevation, or grouping when they clarify structure;
  decorative cards and hover lifts are optional. Keep focus rings visible.

## Motion

Use motion when it clarifies feedback, continuity, or a state change. A view needs no decorative
animation. Keep transitions brief (150–250 ms), prefer `opacity` and `transform`, and respect
`prefers-reduced-motion`.

## Review the rendered result

Inspect the affected view against its audience and main task: hierarchy, legibility, consistency,
accessibility and useful feedback in each state. Remove decoration that competes with the work;
follow the parent skill's verification and gap-reporting rules when a browser is unavailable.
