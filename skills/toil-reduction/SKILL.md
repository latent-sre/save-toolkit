---
name: toil-reduction
description: >-
  Analyze recurring operational work and design measurable elimination, simplification, self-service
  or automation improvements. Triggers: 'reduce these repeated manual interventions', 'which toil
  should we automate', 'is this automation worth maintaining'. Uses frequency, effort, interruption,
  rework and maintenance evidence. Implementation belongs to software-engineer or the application
  owner; active incidents use incident-investigation.
argument-hint: "[recurring task or workflow, baseline window, effort and outcome evidence]"
---

# Toil reduction

Reduce recurring operational burden without shifting hidden maintenance or failure risk onto
another team. Analysis stays under caller authority (`production-change-gate` owns live execution;
`software-engineer`/application team implements; durable docs go to `scribe`; `stack-profile` owns
stack/ownership facts).

## Entry mode: evidence vs. interview

- **Evidence mode (default):** Records or an assessment packet are supplied — assess from them and
  label gaps; ask nothing.
- **Interview mode:** Only when a human invokes this directly with thin inputs (no frequency,
  effort, or ownership) and answers change the recommendation, ask **one batched round** from the
  bank below — only unsettled decision-changing aspects, accepting ranges/`"unknown"` — then wait
  before assessing. Dispatched agents never interview directly: return missing evidence to the caller
  with relevant bank questions attached.

| Aspect | Question bank |
|---|---|
| Task & trigger | Action done, trigger, service/env, and completion definition |
| Frequency & pattern | Count per full cycle (trend/seasonality) and volume driver |
| Effort & interruption | Hands-on minutes, elapsed/wait time, and on-call/off-hours impact |
| People & skill | Current bearers, approvers/handoffs, judgment required, future maintainer |
| Variability & exceptions | Run uniformity vs exceptions, decisions, and escalations |
| Risk & reversibility | Impact of mistake/delay, detection, rollback, and access/compliance bounds |
| Quality & rework | Failure/bounce-back rate, verification, and user/downstream impact |
| Why it recurs | Underlying driver (defect, process, growth, missing tooling/docs) and prior attempts |
| Boundaries & appetite | What stays manual, safe self-service, and who owns the tradeoff |

## Find the mechanism and count distinct work

Trace **trigger -> manual steps -> judgment/access -> result -> reason it recurs** across a
representative natural-cycle window (monthly/release/seasonal; otherwise mark baseline partial).
Name teams, service/env, dates, and coverage gaps.

- **One occurrence = one distinct intervention:** Duplicate records for the same event (ticket +
  page + runbook row for one restart) count **once**; report total human effort per window.
- **Unknown baseline:** Never invent numbers from vague claims ("happens often"); keep baseline and
  break-even `unknown` (`null`), reject unsubstantiated payback claims, and return a qualitative
  opportunity with a measurement plan (`measure_baseline_first`).
- Repeated restarts masking a defect route to `root-cause` and `resilience-analysis` rather than
  symptom automation; measured restart toil bounds avoidable restart time.

## Compare options and economics

Weigh **elimination, cause correction, simplification, bounded self-service, automation, and explicit
acceptance** (acceptance names owner, accepted residual effort/window, and revisit trigger). Human
reliability policy outranks external toil percentages. Count handling, interruptions, rework,
approvals, build/test/migration/training cost, and residual + ongoing maintenance across **all**
teams (transferred dev maintenance reduces savings):

```text
baseline effort = occurrences per window * effort per occurrence
net effort saved per window = baseline - residual handling - ongoing maintenance
break-even windows = one-time effort / positive net effort saved per window
```

- If `net effort saved <= 0` (zero/negative), there is **no positive time-saving break-even**
  (`null`); favor simplification/acceptance unless an independently evidenced safety benefit
  justifies a human tradeoff.
- Label unmeasured projections `estimated` (never `measured`/approved); adjust for proposer optimism
  vs comparable automations, use ranges for uncertainty, and compare cumulative horizon effort when
  payback approaches expected workflow lifetime.

## Design, verify, and return

Automation designs specify trigger, exact target, idempotency, partial/`unknown` outcome handling,
retry bounds, logging/alerts, human reversal, and manual fallback; verify before/after effort,
errors, residual interventions, and user outcomes under comparable demand.

Return these fields (when the caller requires JSON/closed schema, map meanings into allowed fields
without appending this block; `Owner` is implementation/acceptance owner, distinct from caller header):

```text
Baseline: <distinct interventions & total effort per window; sources & coverage gaps>
Options: <elimination, cause fix, simplification, self-service, automation, acceptance — verdict & why>
Calculation: <baseline, residual, maintenance, net saving, break-even (or none), assumptions/ranges>
Classification: <toil | accepted work | enduring-value work | overhead — manual/recurring/low-value = toil; judgment/deliberate/rare = accepted; lasting capability = enduring-value; admin = overhead>
Recommendation: <bounded change, mechanism, alternatives>
Owner: <implementation owner; acceptance owner & revisit trigger when accepting>
Verification: <before/after comparison under comparable demand; unmeasured items>
Uncertainty: <material unknowns and what settles them>
```
