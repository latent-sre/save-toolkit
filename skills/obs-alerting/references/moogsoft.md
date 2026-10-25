# Moogsoft Onprem correlation and noise reduction

The recorded stack is Onprem v9.x; verify installed release/support contract against
[product notices](https://docs.moogsoft.com/v9/en/product-notices.html) before upgrade advice.
The major version does not establish support. Cloud terminology differs from Onprem **Situations**.

Events deduplicate by [`signature`](https://docs.moogsoft.com/v9/en/data-ingestion.html) into alerts;
[Cookbook Recipes and Tempus](https://docs.moogsoft.com/v9/en/clustering-algorithm-guide.html) cluster
alerts by configured attributes and temporal proximity respectively. Situations notify/page.
[Maintenance](https://docs.moogsoft.com/v9/en/schedule-maintenance-downtime.html) still deduplicates
events into `In Maintenance` alerts, excluded from Situations by default but configurable.
Confirm local fields/algorithms/maintenance behavior; correlation is not cause.

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

## Local inventory

Names, IDs, field maps, and links only, never credentials.

| Source | Integration | Event `signature` formula | Fields mapped | Replay evidence / watch-out | Owner |
|---|---|---|---|---|---|
| `<Splunk>` | `<integration name>` | `<source>:<service>:<check>` | `source/service/check → <fields>` | `<incident set / false merge or leaked duplicate>` | `<owner>` |
| `<Wavefront>` | `<integration name>` | `<formula>` | `<fields>` | `<evidence>` | `<owner>` |
| `<ThousandEyes>` | `<integration name>` | `<formula>` | `<fields>` | `<evidence>` | `<owner>` |

Record beside it the Situation notification route by service, the ticket integration and its owner,
and each maintenance window's source, owner, and start/end verification.
