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

For a bounded check or explanation, answer from the supplied rule and evidence; name its limits.
Design and verification steps below apply only to the artifact or readiness work requested.

## SLI, SLO, and burn rate

When defining an SLI, name the journey, **good events / valid events**, exclusions, and request/time
unit. Retain the exact query, backend, target, time range and result. Without reproducible query
evidence, the SLI is proposed, not verified.

**Burn rate = observed bad-event fraction / the SLO's allowed bad-event fraction.** Keep request- and
time-based budgets in their own units; never translate a request-ratio budget to downtime minutes.
For budget work, separate consumed-budget status from the current alert verdict. The human service owner
uses the budget to balance feature risk and reliability work.

For burn-rate work, load the method below for its pairs, low-traffic judgment, and guard-safe
calculator. Both windows must meet the pair's threshold. A one-window spike or
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

For a backup, sync, or scheduled-job alert, use freshness rather than a request burn pair. Design
`*_last_success_timestamp_seconds` and an age threshold from the schedule plus a defensible grace
period. Define no-data behavior: a missing timestamp is silence, never an all-clear. A job that never
runs emits no errors. Freshness complements request-driven SLIs; it does not replace them.

## Verify before calling it done

To claim an alert implementation verified, supply actual evidence for these checks. A design or
review may be handed off with the missing proof explicitly `[unverified]`:

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

## The bar for asserting cause

Correlation, time order, and a path difference rank hypotheses; they do not prove cause. Promote
one only with a mechanism stated concretely enough to be disproved, corroboration from an
independent signal class, a disconfirmation test of what should be true if the hypothesis is false,
and, for a network path, the blast radius: which agents, sites, or users are affected and which are
healthy. Below that bar, call it a leading hypothesis and keep the alternatives open.

## Don't

- Don't choose extra nines because they sound reliable; every nine raises operating cost. Match the
  target to user need and what the team can actually defend.
- Don't call an alert ready without an owner, tested notification route, actionable summary, and runbook.

## Handoff

Bounded question: answer, supplied scope/evidence, relevant gap or next step.
Design/change to `observability-engineer`: proposed definition, target/window, query evidence,
rule source/UID, labels, owner, notification route, runbook, no-data/error behavior, actual tests
and `[unverified]` gaps.

- SLI: journey, good/valid events, units. Burn only: selected pair and both measured burns.
- Freshness only: success signal, schedule, threshold and grace period.
- Correlation tuning only: replay, false-merge/missed-cluster examples, rollback criteria.

For current user impact or an unexplained live failure, hand time-bounded evidence to the responder
with `incident-investigation` (`sre-assistant` only for a dispatched bounded read). Alert design does
not investigate the live incident.
Redact sensitive label and tag values from query evidence before it enters the packet; prefer an
access-controlled link plus the smallest necessary excerpt.
