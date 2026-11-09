# Moogsoft Onprem correlation and noise reduction

The recorded stack is Onprem v9.x. Only Onprem 9.2 and later remain in standard support; verify the
installed release and support contract against
[product notices](https://docs.moogsoft.com/v9/en/product-notices.html) before upgrade advice.
Cloud terminology differs from Onprem **Situations**.

Events deduplicate by [`signature`](https://docs.moogsoft.com/v9/en/data-ingestion.html) into alerts;
[Cookbook Recipes and Tempus](https://docs.moogsoft.com/v9/en/clustering-algorithm-guide.html) cluster
alerts by configured attributes and temporal proximity respectively. Situations notify/page.
[Maintenance](https://docs.moogsoft.com/v9/en/schedule-maintenance-downtime.html) still deduplicates
events into `In Maintenance` alerts, excluded from Situations by default but configurable.
Confirm local fields/algorithms/maintenance behavior. Correlation and time order rank hypotheses,
not cause: promote one only with a disprovable mechanism, corroboration from an independent signal
class, and a disconfirmation test; below that bar, call it a leading hypothesis and keep the
alternatives open.

## During an alert storm

Compare event and ingestion time; polling, delivery delay and clock skew can reorder alerts.
The earliest is a hypothesis, not cause. Follow the live Situation while retaining absorbed/
superseded IDs. Return links/IDs, first/last timestamps, scope, source lineage and alternatives to
the incident responder or their dispatched SRE helper.

## Reducing noise

- Tune `signature` construction so repeats collapse without merging unrelated services or leaking
  duplicates; tune Recipes and Tempus against resolved incidents, not a synthetic happy path.
- Enrich events with bounded service, owner, environment, severity, and runbook metadata; use
  approved maintenance windows for expected deploy and patch noise, and verify the configured
  behaviour at window start and end.
- Assess non-actionable pages for tickets/dashboards. Measure page volume, alerts per Situation,
  auto-clustered share, false merges, missed clusters and time to an actionable Situation.

Hand correlation tuning to the `observability-engineer` agent with before and after replay evidence,
false-merge and missed-cluster examples, proposed key or Recipe changes, and rollback criteria.

Record each source's integration, `signature` formula, field map, replay evidence and owner, the
Situation routes, ticket integration and maintenance windows in the team's own inventory: names, IDs
and links only, never credentials.
