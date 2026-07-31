# Moogsoft / Dell APEX AIOps correlation and noise reduction

The fleet target is on-prem Moogsoft v9.x. Its operator object is a **Situation**; cloud product terms
can differ. `[sourced]` The official
[v9 clustering guide](https://docs.moogsoft.com/v9/en/clustering-algorithm-guide.html) identifies
Sigalisers as clustering algorithms and documents Cookbook and Tempus. The v9
[data-ingestion guide](https://docs.moogsoft.com/v9/en/data-ingestion.html) names the event `signature`
as the deduplication control, and the
[maintenance-downtime guide](https://docs.moogsoft.com/v9/en/schedule-maintenance-downtime.html)
documents maintenance behavior. Confirm exact fields, screens, and enabled algorithms against the
local v9 installation before changing correlation behavior.

## The pipeline

```text
events  →  deduplicate into ALERTS  →  cluster into SITUATIONS  →  notify / page
```

- **Events** are raw signals from log, metric, synthetic, and other monitoring sources.
- **Deduplication** collapses repeated equivalent events into an alert with count and first/last time.
- **Clustering** groups related alerts into a Situation. Cookbook uses configured Recipes and alert
  attributes; Tempus emphasizes time proximity. Correlation ranks related evidence—it does not prove cause.

## During an alert storm

1. Start with the Situation and its scope, not every raw event.
2. Order alerts by event time and ingestion time. The first alert is a ranked hypothesis, not the cause:
   polling cadence, delivery delay, and clock skew can reorder the list.
3. If the local v9 instance merges or supersedes Situations, follow the currently live Situation and
   record every absorbed/superseded ID; verify the exact behavior against the target version.
4. Record alternate hypotheses, which service/region is affected, and which signals share a source.
5. Hand the ranked evidence to the `sre` agent with Situation link/ID, first/last timestamps, blast
   radius, event-source lineage, and unresolved alternatives.

## The bar for asserting cause

Clustering and time order rank hypotheses. Promote one to cause only with evidence such as:

- **Mechanism:** state how A produces B concretely enough to be disproved.
- **Corroboration:** an independent signal class agrees, not several views of one feed.
- **Disconfirmation:** test what should be true if the hypothesis is false.
- **Controlled response:** an approved mitigation reverses the symptom with matching timing.

Without that bar, call it a leading hypothesis. Preserve the Situation's ranked chronology; after
resolution, hand the ranked timeline to the `sre-steward` agent.

## Reducing noise

- Tune event `signature` construction so repeats collapse without merging unrelated services or
  leaking duplicates.
- Tune Cookbook Recipes and Tempus against resolved incidents, not a synthetic happy path alone.
- Enrich events with bounded service, owner, environment, severity, and runbook metadata.
- Use approved maintenance windows for expected deploy/patch noise. Events continue deduplicating into
  alerts tagged `In Maintenance`; by default those alerts are omitted from Situations, and Situation
  membership is configurable. Verify the configured behavior at window start and end.
- Demote non-actionable pages to tickets or dashboards, then measure page volume and clustering quality.

Hand correlation tuning to the `sre-steward` agent with before/after replay evidence, false-merge and
missed-cluster examples, proposed key/Recipe changes, and rollback criteria.

## Event sources / integrations

Names, IDs, field maps, and links only—no credentials or API keys.

| Source | Integration | Event fields mapped | Owner / notes |
|---|---|---|---|
| `<Splunk>` | `<integration name>` | `source/service/check → <fields>` | `<owner / log alerts>` |
| `<Wavefront>` | `<integration name>` | `<fields>` | `<owner / metric alerts>` |
| `<ThousandEyes>` | `<integration name>` | `<fields>` | `<owner / synthetics>` |

## Dedup signatures

| Source | Event `signature` formula | Replay evidence | Watch-out |
|---|---|---|---|
| `<source>` | `<source>:<service>:<check>` | `<incident/event set>` | `<false merge or leaked duplicate>` |

## Sigaliser tuning

| Recipe / algorithm | Clusters by | Validated incidents | Rollback trigger |
|---|---|---|---|
| `<Cookbook Recipe or Tempus>` | `<service, app, dependency, time>` | `<links>` | `<measured regression>` |

## Enrichment and routing

- Event tags: `<service>`, `<owner/team>`, `<environment>`, `<runbook URL>`.
- Situation notification/page route: `<policy and escalation by service>`.
- Bidirectional incident/ticket integration: `<name and ownership>`.

## Maintenance windows

| Change class | Window source / mechanism | Owner | Start/end verification |
|---|---|---|---|
| `<deploy or patch>` | `<schedule and Situation-membership policy>` | `<team>` | `<evidence>` |

## Health metrics

Track alerts per Situation, percentage auto-clustered, false merges, missed clusters, page volume, and
mean time from first event to actionable Situation. Record current baselines and targets here:
`<reviewed measurement source and target>`.

<!-- terminal-canary: q_oamoog_6f3a -->
