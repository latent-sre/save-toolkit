# Dense data as a working surface

Read for large tables, linked charts, dependency exploration and bulk selection. The
[API reference](./api.md) owns server filters, cursor pages and writes; [live data](./live-data.md)
owns updates during investigation. Choose only the capabilities the user's task needs.

## Tables and selection

Choose columns from the decision being made. Keep identity, status and missing values readable;
long values need an inspectable path. Column visibility, grouping, resizing, pinning and saved
views are choices, not a mandatory grid feature list.

Define whether search and sort cover loaded rows or the full collection. Client-side ordering
of one page must not pretend to order every result. Preserve stable record IDs through sorting,
pagination, refresh and virtualization. Keep the API's counts honest: cursor-only collections
do not acquire an invented total. Show no-data, no-matches, partial-results and failed-refresh
states distinctly, preserving the useful working set.

Selection must distinguish explicit record IDs, visible rows and all matching records. Decide
what changing filters does to it, expose the target scope and count that the backend can actually
establish, and use the shared action confirmation path. A selected row disappearing from the
current page does not silently authorize a different target. For all-matching operations, use
the backend's supported snapshot/query semantics; do not treat a changing filter as a frozen set.

Use semantic tables for ordinary tabular content. A cell-editing grid needs the component
system's focus and keyboard model. Test focus retention with virtualization and nested controls;
the visible selection and the active control must refer to the same record. Keep return context
when opening a detail route or inspector.

## Linked views and dependency exploration

Brushing a chart, selecting an event or choosing a row updates a shared scope, with an explicit
reset. A chart has the core skill's accessible alternative, and focus can reach values otherwise
shown only by hover. Check units, aggregation and time boundaries across views.

Before drawing dependencies, define node identity, edge direction, relationship type and source
time. Distinguish observed, configured, inferred and unknown relationships when the source does;
layout proximity does not establish severity or causality. Start from a bounded neighborhood,
with search, progressive expansion and a stable inspector instead of an unreadable whole graph.
Preserve position when inspecting an edge or service.

A synchronized relationship list or table provides a keyboard/non-drag route through the same
selection and scope. Include cycles, disconnected nodes and missing ownership in representative
data. Layout movement must not prevent reading or selecting a node. Measure interaction cost at
expected size before adding a heavier renderer or expanding the visible graph.

## Completion exercise

Filter and sort a multi-page collection containing duplicate names but distinct IDs. Select a
record, refresh with changed ordering, inspect it and return: identity and declared selection
scope must survive. Exercise a failed bulk action through the API contract. Trace a dependency
and inspect its provenance, then repeat through the synchronized keyboard path. Verify the
result using actual records and requests, not only changed labels or screenshot appearance.
