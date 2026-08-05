# Data visualization

Read this when the view charts, graphs, or plots anything.

The universal frontend rules live in `skills/frontend-craft/SKILL.md`. On any conflict, SKILL.md wins.

## Data visualization

Chart *design*, in brief: pick the form the data asks for — time series → line, comparison → bar, part-of-whole → stacked bar (pie only for 2–3 slices), distribution → histogram; label axes and units; a dashboard leads with the number that answers the viewer's question. Implementation:

- **Library**: **Recharts v3** by default (composable, themed from your Tailwind tokens). **uPlot** for dense real-time time-series (canvas — thousands of streaming points where SVG chokes). **visx** only for a bespoke one-off. **Tremor** is an optional accelerator for KPI+chart dashboards (Tailwind-native, shadcn-matching). Never **@mantine/charts** — it pulls in Mantine's styling (the `@mantine/core` prohibition in [stack](./stack.md)).
- **Theme**: charts read the same theme tokens and categorical accent palette — never hardcode chart colors.
- **Live data**: stream via the SSE→Query-cache path, but throttle/batch redraws (not every tick) and keep a rolling window for time-series.
- **Perf & a11y**: canvas over SVG past ~1–2k points; downsample server-side when you can; give every chart a text or data-table alternative.

Ownership map only—not a load: this file owns **product-UI charts** (Recharts/uPlot inside the app); the `obs-dashboards` skill owns Grafana operations dashboards—never rebuild those as app UIs.
