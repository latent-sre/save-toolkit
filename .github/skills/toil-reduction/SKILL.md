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

Reduce recurring operational burden without transferring hidden work or failure risk to another
team. This is analysis and design under the caller's authority, not permission to automate live
actions. Load `stack-profile` for ownership before recommending implementation.

## Find the recurring mechanism

Trace **trigger -> manual steps -> judgment/access needed -> result -> reason it recurs** using a
representative window of tickets, pages, runbooks, change records or supplied observations. Name
the people and teams bearing the work, the service/environment, evidence dates and coverage gaps.
Do not infer frequency from one incident or duplicate records of the same intervention.

One occurrence is one distinct intervention: records of the same intervention in different
systems (a ticket, a page and a runbook entry for one restart) count once. The window must cover
the task's natural cycle — a monthly batch, a release cadence, a seasonal peak — or state why it
cannot and label the baseline partial. Report total human effort over the window, not only
effort per occurrence.

Distinguish repeated maintenance of the same state from engineering that creates lasting value.
Necessary judgment, a rare recovery exercise or a one-off task is not automatically toil. A repeated
restart may expose a service defect; use `root-cause` for that diagnosis and `resilience-analysis`
for its failure path rather than immediately automating the restart.

## Compare options

Consider eliminating the task, correcting its cause, simplifying the workflow or default,
providing bounded self-service, automating, or explicitly accepting the work. Follow the evidence;
there is no mandatory automation quota or universal toil percentage. Company policy and human-owned
reliability requirements outrank an example threshold from another organization.

Explicit acceptance is a decision, not an omission: name its owner, the residual effort the team
accepts per window, and the revisit trigger (a date, a volume or effort change, or a related
incident) that reopens the comparison.

Measure or clearly label estimates for:

- Frequency and human effort per occurrence, including interruptions, rework and approvals.
- One-time design, implementation, testing, migration and training effort.
- Residual handling, review, failures, maintenance and support across all affected teams.
- User impact, error reduction, recoverability, access requirements and maintenance ownership.

For comparable time windows, show units and assumptions:

```text
baseline effort = occurrences per window * effort per occurrence
net effort saved per window = baseline - residual handling - ongoing maintenance
break-even windows = one-time effort / positive net effort saved per window
```

Count each cost once; include work transferred to developers or another operations team. If net
savings are zero or negative, there is no positive time-saving break-even. A risk-reduction benefit
may still justify the work, but needs its own evidence and human tradeoff. Use ranges when demand or
maintenance is uncertain; do not claim a payback date from weak estimates. Break-even also assumes
the workflow and its demand survive unchanged: when the payback approaches the workflow's expected
useful life, or adoption ramps slowly, compare cumulative effort over that horizon instead of
quoting a break-even month. Read
[worked examples](references/worked-examples.md) when evaluating economics or recurring restarts.

## Design and verify the improvement

Recommend a bounded change with its mechanism, owner, alternatives, expected benefit and acceptance
criteria. When automation is the recommendation, also specify:

- Inputs and target binding: what triggers it, and the exact service/environment it may act on.
- Idempotency and partial/unknown outcomes: what a re-run, a half-completed run and an
  unconfirmed result do.
- Retry limits, observability and recovery: when it stops, what it logs or alerts, and how a
  human reverses or completes its work.
- A maintainable manual fallback for when it is unavailable or wrong.

These are implementation requirements, not permission to execute; `production-change-gate` retains live
authority and `software-engineer` or the application owner implements the accepted work.

Compare before/after effort, errors, residual interventions and relevant user outcomes under
comparable demand. A faster script or fewer tickets alone does not establish reduced total work or
improved reliability. Retain unfavorable outcomes and changes in volume; absence of a follow-up
measurement leaves the benefit unverified.

Return the assessment in this shape; combine fields in prose only when the caller asks for a
short answer, and mark a field unknown rather than filling it from assumption. Precede this shape
with your caller's return header when one applies: `Owner` below is the implementation or
acceptance owner, never the human decision owner named in that header. When the caller requires a
closed schema or JSON only, carry these meanings in its permitted fields and do not append the shape:

```text
Baseline: <occurrences and total effort per window; window, sources and coverage limits>
Options: <elimination, cause correction, simplification, self-service, automation, acceptance — each kept or rejected, with why>
Calculation: <baseline, residual and maintenance effort, net saving and break-even or why none exists; ranges and assumptions>
Recommendation: <bounded change, mechanism and alternatives>
Owner: <implementation owner; acceptance owner and revisit trigger when accepting>
Verification: <before/after comparison under comparable demand, and what remains unmeasured>
Uncertainty: <material unknowns and what evidence would settle them>
```

Use `[verified]` for directly observed bounded facts,
`[sourced]` for supplied records and `[unverified]` for assumptions or unavailable results; preserve
`[UNTRUSTED]` taint. Write no durable operational records through this method; requested accepted
knowledge goes to `scribe` through the caller.

Primary method: [Google SRE: Eliminating Toil](https://sre.google/workbook/eliminating-toil/), checked
2026-09-21 for measurement, option selection and maintenance economics. Recheck when adapting the
method or resolving disputed guidance. Organization-specific targets in that source are not fleet
policy. The examples here are fictional and the method's native effectiveness remains unverified
until evaluated on the accepted candidate.
