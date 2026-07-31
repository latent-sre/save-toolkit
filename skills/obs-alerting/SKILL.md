---
name: obs-alerting
description: >-
  Design alerting that pages on symptoms — SLIs/SLOs and multi-window burn rates, Grafana unified
  alerting as code, Moogsoft correlation, and ThousandEyes synthetics. Triggers: 'define an SLO',
  'this alert is too noisy', 'what should page', 'design a synthetic check'. Every alert links a
  runbook. Ownership map only—not a load: obs-metrics/obs-logs own queries and obs-dashboards owns
  dashboards.
argument-hint: "[service, SLO, alert, storm, or synthetic check]"
---

> **Evidence default — `[unverified]`.** Unless a paragraph carries a narrower label, each
> stack/product-specific command, query, API or CLI behavior, version, licensing statement, and
> runtime claim in this skill and its bundled files is `[unverified]` for the exact target.
> A narrower `[sourced]` or `[verified]` label takes precedence; handoffs never upgrade it.

# Alert, correlate, page

Page on user-visible symptoms that require action now. Use an SLI and error budget to distinguish a
significant sustained burn from a transient component signal; use correlation and synthetics to rank
where responders should look, never to manufacture a root cause. Every alert links a runbook.

## SLI — the measurement

An SLI is a ratio of **good events / valid events** from the user's perspective:

```text
availability SLI = successful requests / valid requests
latency SLI      = requests faster than <threshold> / valid requests
```

For every SLI, define the numerator and denominator explicitly: which outcomes are good, which events
are valid, which health checks or client errors are excluded, and which user journey the ratio
represents. Query it in the team's current metric or log backend and preserve the exact query as
evidence with its time range, target, and result. A formula without a reproducible query is a proposal,
not a verified SLI.

## SLO — the target over a window

- Pick one target for each critical user journey over a stated rolling window, commonly 28 days.
- **Error budget = 1 − SLO**, and its unit follows the SLI. A request-based SLI has a budget measured
  in bad requests; a time-based probe/uptime SLI has a budget measured in bad minutes.
- For example, a 99.9% request SLO over 9.3 million valid requests permits about 9,300 bad requests;
  a 99.9% time-based SLO over 28 days permits about 40.3 bad minutes. These are different SLIs and
  are not interchangeable even though the percentage target is the same.
- Never convert a request-ratio budget into downtime minutes: that assumes uniform traffic and hides
  the difference between peak-hour and overnight impact.
- Treat the budget as a decision input. Record the budget-status calculation separately from an alert
  verdict; a recovered short window does not restore budget already consumed. The human service owner
  uses the remaining budget and error-budget policy to balance feature risk and reliability work.

Use [error_budget.py](./scripts/error_budget.py) for local, pure-stdlib calculations. It refuses mixed
time/request units, validates numeric inputs, and emits a severity only when a legal long/short pair is
selected and both measurements are present.

## Burn-rate alerts

Burn rate is the observed bad-event ratio divided by the SLO's allowed bad-event ratio. Bind each
threshold to its window pair; the threshold is not a free label:

| Action | Long window | Short window | Threshold |
|---|---|---|---|
| Page — fast burn | 1h | 5m | 14.4x |
| Page — slow burn | 6h | 30m | 6.0x |
| Ticket — slow leak | 3d | 6h | 1.0x |

Require BOTH the long and short windows to meet that pair's threshold. The long window provides
significance; the short window proves the burn is still active and lets the notification resolve
quickly after recovery. A one-window spike or a recovered short window is not a page, but neither is
an all-clear about budget status.

Read only the row needed for the task:

| Need | Reference |
|---|---|
| SLI, SLO, budget status, or multi-window burn rate | [burn-rate method](./references/burn-rate.md) |
| Grafana rule groups, contact points, or notification policies | [Grafana 13 alerting](./references/grafana-alerting.md) |
| Alert storm, event correlation, deduplication, or Moogsoft | [Moogsoft correlation](./references/moogsoft.md) |
| Synthetic test, DNS, BGP, path, or external reachability | [ThousandEyes synthetics](./references/thousandeyes.md) |
| Calculate budget status or a permitted burn-rate pair | [error_budget.py](./scripts/error_budget.py) |

## Don't

- Don't choose extra nines because they sound reliable; every nine raises operating cost. Match the
  target to user need and what the team can actually defend.
- Don't page on every cause candidate such as CPU or one failed instance. Page on the symptom and give
  the responder those signals as ranked diagnostic evidence.
- Don't call a non-alert branch healthy, in budget, or an all-clear. Alert state answers whether the
  paired burn condition is firing now; budget status answers what has already been consumed.
- Don't create an alert without an owner, tested notification route, actionable summary, and runbook.

## Handoff

Hand the reviewed alert definition and target-validation gaps to the `sre-steward` agent. Include the SLI
formula and exact query evidence, target/window, selected long/short pair, both measured burns, rule
source and UID, labels, notification route, runbook URL, no-data/error behavior, test evidence, and
every remaining `[unverified]` item. If a signal represents current user impact or unknown cause, hand
the time-bounded evidence to the `sre` agent; alert design does not investigate the live incident.
