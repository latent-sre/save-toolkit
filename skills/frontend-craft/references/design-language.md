# Greenfield design language

Read only for greenfield or unbranded UI. Existing brand and design-system decisions win.

Before styling, record audience, primary jobs, workflow density, navigation model, responsive
constraints, page/surface/accent/status tokens, typography, and one visual decision tied to the
product. If the plan fits every dashboard, it is not specific enough.

- Choose navigation from information architecture and viewport needs; no destination-count rule
  universally selects a sidebar, tabs, or top navigation.
- Put density where comparison demands it and space where comprehension/action demands it. Do not
  invent content or metrics to fill a viewport.
- Use semantic tokens and consistent status meaning. Pair color with text/icon/shape and maintain the
  required contrast in every supported theme.
- Use elevation, borders, accents, and motion sparingly to express hierarchy/state. Respect reduced
  motion and avoid effects that delay interaction.
- Design loading, error, empty, partial, and success states with the main composition. Test long copy,
  localization, zoom, narrow/wide layouts, and real data before declaring the system coherent.
