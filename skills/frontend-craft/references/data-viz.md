# Data visualization

Read this when the view charts, graphs, or plots anything.

The universal frontend rules live in `../SKILL.md`. On any conflict, SKILL.md wins.

Chart *design*, in brief: pick the form the data asks for — time series → line, comparison → bar, part-of-whole → stacked bar (pie only for 2–3 slices), distribution → histogram; label axes and units; a dashboard leads with the number that answers the viewer's question. Implementation:

- **Library**: match an existing repository first. In the React greenfield stack, use **Recharts
  v3** by default, **visx** only for a bespoke one-off, and optionally **Tremor** for a
  KPI-and-chart dashboard. Those are React choices, not Vue defaults. A Vue target keeps its
  established Vue chart layer. **uPlot** is the framework-neutral choice for dense real-time time
  series where thousands of points make SVG too expensive. Never **@mantine/charts** — it pulls in
  Mantine's styling (the `@mantine/core` prohibition in [stack](./stack.md)).
- **Theme**: charts read the same theme tokens and categorical accent palette — never hardcode chart colors.
- **Live data**: stream via the SSE→Query-cache path, but throttle/batch redraws (not every tick) and keep a rolling window for time-series.
- **Perf & a11y**: canvas over SVG past ~1–2k points; downsample server-side when you can; give every chart a text or data-table alternative.

This file owns **product-UI charts** (Recharts/uPlot inside the app); the `obs-dashboards` skill owns Grafana operations dashboards—never rebuild those as app UIs.
