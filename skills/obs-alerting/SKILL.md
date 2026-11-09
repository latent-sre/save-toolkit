---
name: obs-alerting
description: >-
  Design alerting that pages on symptoms — SLIs/SLOs and multi-window burn rates,
  Splunk saved-search alerts, Moogsoft correlation, and ThousandEyes synthetics.
  Triggers: 'define an SLO', 'this alert is too noisy', 'what should page', 'design a synthetic
  check'. Not for signal queries or interpretation (obs-analysis) or dashboards (grafana).
argument-hint: "[service, SLO, alert, storm, or synthetic check]"
---

# Alert, correlate, page

Page on user-visible symptoms that require action now. Use an SLI and error budget to distinguish a
significant sustained burn from a transient component signal; use correlation and synthetics to rank
where responders should look, never to manufacture a root cause. Every paging alert has an owner, an actionable summary, and a runbook link.

For a bounded check or explanation, answer from the supplied rule and evidence; name its limits.
Design and verification steps below apply only to the artifact or readiness work requested.
Redact sensitive label and tag values from query evidence; prefer an access-controlled link plus
the smallest necessary excerpt.
**Grafana implementation lives in `grafana`;** load it for any Grafana rule, silence, routing, or
missing-notification work. This skill owns alert intent, SLOs, burn rates, and verification
criteria; it does not grant live access.

## SLI, SLO, and burn rate

When defining an SLI, name the journey, **good events / valid events**, exclusions, and request/time
unit; for an SLO, name its objective horizon. Retain query, backend, target, time range and result.
Without reproducible query evidence, the SLI is proposed, not verified.

**Burn rate = observed bad-event fraction / the SLO's allowed bad-event fraction.** Keep request- and
time-based budgets in their own units; never translate a request-ratio budget to downtime minutes,
and separate consumed-budget status from the current alert verdict. For burn-rate work, load the
method below: both windows must meet the pair's threshold — a one-window spike is not a page, and
neither outcome proves the service is in budget.

Read only the row needed for the task:

| Need | Reference |
|---|---|
| SLI, SLO, budget status, or multi-window burn rate | [burn-rate method](./references/burn-rate.md) |
| Splunk saved-search alerts, cron/window pairing, throttling, or webhook/email actions | [Splunk alerting](./references/splunk-alerting.md) |
| Alert storm, event correlation, deduplication, or Moogsoft | [Moogsoft correlation](./references/moogsoft.md) |
| Synthetic test, DNS, BGP, path, or external reachability | [ThousandEyes synthetics](./references/thousandeyes.md) |
| Calculate budget status or a supported example burn-rate pair | [error_budget.py](./scripts/error_budget.py) |

## Scheduled work — alert on staleness, not errors

For a backup, sync, or scheduled-job alert, use freshness rather than a request burn pair. Design
`*_last_success_timestamp_seconds` and an age threshold of at least two full schedule intervals.
Define no-data behavior: a missing timestamp is silence, never an all-clear. In Prometheus,
`time() - x > t` returns nothing once the series vanishes, so the alert resolves; pair it with an
`absent()` rule. In Grafana, a vanished series goes to Normal (missing series), and the
`DatasourceNoData`/`DatasourceError` alerts may not match the notification policies and silences
written for the rule. A job that never runs emits no errors. Freshness complements request-driven
SLIs; it does not replace them.

Trace shared dependencies of the job, signal store, evaluator and notification path. If the signal
store fails, an age query cannot evaluate: specify query-error notification or an independent
detection path, and test it separately from missing data through the contact point. Name evaluator
and receiver outages that the same failed component cannot report.

## Verify before calling it done

To claim an alert implementation verified, supply actual evidence for these checks. A design or
review may be handed off with the missing proof explicitly `[unverified]`:

- Validate before any reload: rule and config syntax pass their checkers (for Prometheus-format
  sources, `promtool check rules` / `promtool check config`; these do not check Grafana-managed
  rules) so a bad file never reaches the evaluator.
- **Force the alert's condition and observe it fire, resolve, and deliver to the intended contact
  point** — a deliberately failing safe target, or a controlled non-production rule with an
  always-true expression routed only to a test contact point. Never force a production receiver.
  `promtool test rules` proves the burn-rate arithmetic and the long/short window pair on
  synthetic series only; live fire/resolve and delivery still need their own checks. `promtool
  check` and `promtool test` are agent-runnable **in the `observability-engineer` lane only**
  (`test` creates a disk-backed temporary TSDB in the OS temp directory whatever the working
  directory; set `TMPDIR` on POSIX or `TMP` on Windows to relocate it); an `sre-assistant` loading
  this skill routes both to a human and preserves the exact output. A rule that has only ever
  evaluated false is unverified; so is one never observed resolving after recovery.
- A paging alert's runbook link resolves to a runbook that exists — a dead link at 3 a.m. is a
  design defect, not a docs chore.
