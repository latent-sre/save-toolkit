# Moogsoft Onprem correlation and noise reduction

Onprem v9.x only stays in standard support on **9.2+** (Cloud terminology differs from Onprem
**Situations**). [Maintenance windows](https://docs.moogsoft.com/v9/en/schedule-maintenance-downtime.html)
still ingest events into alerts labelled `In Maintenance` (excluded from Situations by default,
configurable). Correlation ranks hypotheses rather than proving cause.

## During an alert storm

- Compare event time vs. ingestion time (polling, delivery delay, and clock skew reorder alerts).
- Follow the live Situation while preserving absorbed/superseded alert IDs, first/last timestamps,
  scope, source lineage, and uneliminated alternatives.

## Reducing noise

- Tune [`signature`](https://docs.moogsoft.com/v9/en/data-ingestion.html) construction so repeats
  collapse without merging unrelated services or leaking duplicates; tune
  [Recipes and Tempus](https://docs.moogsoft.com/v9/en/clustering-algorithm-guide.html) against
  resolved incidents with before/after replay evidence, false-merge and missed-cluster examples,
  and rollback criteria before handing changes to `observability-engineer`.
- Maintain an inventory of each source's integration, `signature` formula, field map, Situation
  routes, ticket links, and approved maintenance windows (names, IDs, and links only).
