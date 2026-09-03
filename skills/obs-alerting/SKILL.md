---
name: obs-alerting
description: >-
  Design alerting that pages on symptoms — SLIs/SLOs and multi-window burn rates, Grafana unified
  alerting as code, Splunk saved-search alerts, Moogsoft correlation, and ThousandEyes synthetics.
  Triggers: 'define an SLO', 'this alert is too noisy', 'what should page', 'design a synthetic
  check'. Not for queries (obs-metrics, obs-logs) or dashboards (obs-dashboards).
argument-hint: "[service, SLO, alert, storm, or synthetic check]"
---

# Alert, correlate, page

Page on user-visible symptoms that require action now. Use an SLI and error budget to distinguish a
significant sustained burn from a transient component signal; use correlation and synthetics to rank
where responders should look, never to manufacture a root cause. Every alert links a runbook.

## SLI, SLO, and burn rate

For every SLI, name the user journey and define **good events / valid events**: numerator,
denominator, exclusions, and whether its unit is requests or time. Preserve the exact metric or log
query with backend, target, time range, and result. A formula without a reproducible query is a
proposal, not a verified SLI.

**Burn rate = observed bad-event fraction / the SLO's allowed bad-event fraction.** Keep request- and
time-based budgets in their own units; never translate a request-ratio budget to downtime minutes.
Record consumed-budget status separately from the current alert verdict. The human service owner
uses the budget to balance feature risk and reliability work.

Load the burn-rate method below for its long/short pairs, low-traffic judgment, and guard-safe
calculator. Treat a pair as one unit: both windows must meet its threshold. A one-window spike or
recovered short window is not a page, but neither proves the service is in budget.

Read only the row needed for the task:

| Need | Reference |
|---|---|
| SLI, SLO, budget status, or multi-window burn rate | [burn-rate method](./references/burn-rate.md) |
| Grafana rule groups, contact points, or notification policies | [Grafana 13 alerting](./references/grafana-alerting.md) |
| Splunk saved-search alerts, cron/window pairing, throttling, or webhook/email actions | [Splunk alerting](./references/splunk-alerting.md) |
| Alert storm, event correlation, deduplication, or Moogsoft | [Moogsoft correlation](./references/moogsoft.md) |
| Synthetic test, DNS, BGP, path, or external reachability | [ThousandEyes synthetics](./references/thousandeyes.md) |
| Calculate budget status or a permitted burn-rate pair | [error_budget.py](./scripts/error_budget.py) |

## Scheduled work — alert on staleness, not errors

Burn-rate machinery covers request-driven SLIs; a backup, sync, or scheduled job has no request
stream to burn, so it needs a freshness signal instead. Have every such job emit
`*_last_success_timestamp_seconds` and alert on "hasn't succeeded in N hours." That catches the
silent failures no error rate ever shows, because a job that never ran emits no errors. Set N from
the job's schedule plus a defensible grace period, and design the no-data case deliberately: a
missing timestamp is the same silence as a stale one, never an all-clear. This complements the
burn-rate table above; it does not replace it for request-driven journeys.

## Verify before calling it done

An alert that has never fired is written, not verified. Before handing it off:

- Validate before any reload: rule and config syntax pass their checkers (for Prometheus-format
  sources, `promtool check rules` / `promtool check config`) so a bad file never reaches the
  evaluator.
- **Force the alert's condition and observe it both fire and resolve** — a deliberately failing
  safe target, a controlled non-production rule with an always-true expression routed only to a
  test contact point, or `promtool test rules` to prove the burn-rate arithmetic and the long/short
  window pair. Never force a production receiver. `promtool check` and `promtool test` are
  agent-runnable **in the `observability-engineer` lane only** (`test` creates a disk-backed
  temporary TSDB — run it in a scratch directory); an `sre-assistant` loading this skill routes both to a
  human and preserves the exact output. A rule that has only ever evaluated false is
  unverified; so is one never observed resolving after recovery.
- The notification route delivered to the intended contact point.
- The runbook link in the alert resolves to a runbook that exists — a dead link at 3 a.m. is a
  design defect, not a docs chore.

This evidence is the "test evidence" the handoff below requires; anything unforced or unobserved
stays labeled `[unverified]`.

## Don't

- Don't choose extra nines because they sound reliable; every nine raises operating cost. Match the
  target to user need and what the team can actually defend.
- Don't create an alert without an owner, tested notification route, actionable summary, and runbook.

## Handoff

Hand the reviewed alert definition and target-validation gaps to the `observability-engineer` agent. Include the SLI
formula and exact query evidence, target/window, selected long/short pair, both measured burns, rule
source and UID, labels, notification route, runbook URL, no-data/error behavior, test evidence, and
every remaining `[unverified]` item. If a signal represents current user impact or unknown cause, hand
the time-bounded evidence to the responder with `incident-investigation` (dispatching `sre-assistant`
only for a bounded read); alert design does not investigate the live incident.
Redact sensitive label and tag values from query evidence before it enters the packet; prefer an
access-controlled link plus the smallest necessary excerpt.
