# Data-dense views (tables & lists)

Read this when the view shows a table, list, or grid of records.

The universal frontend rules live in `../SKILL.md`. On any conflict, SKILL.md wins.

- **TanStack Table** (headless) for anything tabular — you own the markup and Tailwind styling; sort/filter/paginate through the URL state (the `URL is state` invariant in `SKILL.md`).
- Density where data lives: compact rows, `tabular-nums`, right-aligned numerics, sticky header, a row-action menu. **Virtualize** (TanStack Virtual) once a list can exceed a few hundred rows.
- Bulk selection with an "N selected" action bar when the workflow needs it; destructive bulk actions confirm.
