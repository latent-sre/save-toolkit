# Data-dense views

Read for a table, list, tree, or record grid.

- Match the repository's table/list primitives. Add a headless table or virtualization library only
  when sorting/filtering/selection/accessibility or measured row volume warrants it.
- Put durable filter/sort/page/selection state in validated URL state only when refresh, sharing, or
  back/forward must restore it. Keep server and client sorting/pagination semantics aligned.
- Use semantic table markup where the relationship is tabular. Label sortable state, preserve visible
  keyboard focus, announce result-count changes, and provide an accessible alternative to drag-only
  reordering.
- Keep numerics aligned and units explicit. Bound row count and payload; virtualize from measured
  rendering cost rather than a copied threshold.
- Bulk actions name the count and effect, preserve authorization per object, and require an explicit
  recovery/confirmation design for destructive work.
