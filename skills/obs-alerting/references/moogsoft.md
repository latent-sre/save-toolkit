# Moogsoft Onprem correlation and noise reduction

The recorded stack uses Moogsoft Onprem v9.x. Confirm the installed release and applicable support
contract against the vendor's [product notices](https://docs.moogsoft.com/v9/en/product-notices.html)
before recommending an upgrade; the major version alone does not establish support status.
Its operator object is a **Situation**; cloud product terms differ.

The v9 [clustering guide](https://docs.moogsoft.com/v9/en/clustering-algorithm-guide.html)
names the Sigalisers **Cookbook** (configured Recipes over alert attributes) and **Tempus** (time
proximity); the [data-ingestion guide](https://docs.moogsoft.com/v9/en/data-ingestion.html) names the
event **`signature`** as the deduplication control; the
[maintenance guide](https://docs.moogsoft.com/v9/en/schedule-maintenance-downtime.html) says events in
an approved window still deduplicate into alerts tagged `In Maintenance`, which are by default omitted
from Situations, with membership configurable. Confirm fields, screens, and enabled algorithms
against the local installation before changing correlation behaviour.

Events deduplicate into alerts, alerts cluster into Situations, Situations notify or page.
Correlation ranks related evidence; it does not prove cause.

## During an alert storm

Order alerts by event time and ingestion time: the first alert is a ranked hypothesis, not the
cause, because polling cadence, delivery delay, and clock skew can reorder the list. If the local
instance merges or supersedes Situations, follow the live one and record every absorbed or
superseded ID. Hand the ranked evidence to the responder, or the `sre-assistant` slice they
dispatched, with the Situation link and ID, first and last timestamps, blast radius, event-source
lineage, and unresolved alternatives.

## Reducing noise

- Tune `signature` construction so repeats collapse without merging unrelated services or leaking
  duplicates; tune Recipes and Tempus against resolved incidents, not a synthetic happy path.
- Enrich events with bounded service, owner, environment, severity, and runbook metadata; use
  approved maintenance windows for expected deploy and patch noise, and verify the configured
  behaviour at window start and end.
- Demote non-actionable pages to tickets or dashboards, then measure page volume and clustering
  quality: alerts per Situation, share auto-clustered, false merges, missed clusters, and time from
  first event to an actionable Situation.

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
