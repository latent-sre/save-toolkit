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

## Interview when evidence is thin

Two entry modes; the evidence decides, not the caller's patience:

- **Evidence mode (default):** records or a supplied assessment packet exist. Assess from them
  and label gaps; ask nothing.
- **Interview mode:** a human invokes this directly with a thin description (no frequency,
  effort or ownership evidence) and an answer would change the recommendation. Ask **one
  batched round** from the generalized bank below — every aspect that could change the
  decision, none that could not — then assess from the answers. A dispatched agent never
  interviews: it returns its missing evidence to its caller **with the relevant bank
  questions attached**, so the caller can put them to the human without loading this skill.
  A human who selected an agent directly is in interview mode, not dispatched mode.

The bank is deliberately task-neutral; phrase each question for the work at hand, accept
ranges and "unknown", and never make an answer a precondition. An aspect already settled at
gist level by the supplied description is not re-asked; a sub-detail is asked only when it
could change the decision. An unanswered aspect becomes an `[unverified]` gap with the
smallest useful measurement, and the assessment proceeds once the round is answered or the
caller re-invokes — not in the same reply as the questions.

| Aspect | Ask, generalized |
|---|---|
| Task and trigger | What exactly is done, what triggers it, for which service/environment, and what counts as done? |
| Frequency and pattern | How often over the last full cycle? Growing, shrinking, seasonal or spiky — and what drives the volume (users, services, releases, data)? |
| Effort and interruption | Hands-on time per occurrence? Elapsed time, waiting and approvals? When does it land (work hours, on-call, nights) and what does the context switch cost? |
| People and skill | Who bears it today, who else touches it (handoffs, approvers), and what skill or judgment does it need? Who would maintain an alternative? |
| Variability and judgment | How identical is each run? Where do exceptions, decisions or escalation happen, and what makes an occurrence hard? |
| Risk and reversibility | What goes wrong when it's done badly, late or not at all? Blast radius, detection, and how is a mistake undone? What access or compliance constraints apply? |
| Quality and rework | How often does it fail, repeat or bounce back? What verification follows, and what is the user or downstream impact of the work itself? |
| Why it recurs | Why does this work exist at all — defect, process, growth, missing tooling or documentation? What has already been tried? |
| Boundaries and appetite | What must stay manual, what may requesters do themselves, and what outcome would make this worth changing now? Who owns that decision? |

Do not infer toil from the interview alone: a task that is rare, judgment-heavy or deliberately
practised may be accepted work, and the interview's job is to surface that, not to manufacture
an automation case.

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

A repeated restart may expose a service defect; use `root-cause` for that diagnosis and
`resilience-analysis` for its failure path rather than immediately automating the restart.

## Compare options

Consider eliminating the task, correcting its cause, simplifying the workflow or default,
providing bounded self-service, automating, or explicitly accepting the work. Follow the evidence;
there is no mandatory automation quota or universal toil percentage. Company policy and human-owned
reliability requirements outrank an example threshold from another organization.

Explicit acceptance is a decision, not an omission: name its owner, the residual effort the team
accepts per window, and the revisit trigger (a date, a volume or effort change, or a related
incident) that reopens the comparison.

Measure or label as estimates: effort per occurrence including interruptions, rework and
approvals; one-time effort including testing, migration and training; residual handling and
maintenance across every affected team. For comparable time windows, show units and assumptions:

```text
baseline effort = occurrences per window * effort per occurrence
net effort saved per window = baseline - residual handling - ongoing maintenance
break-even windows = one-time effort / positive net effort saved per window
```

Count each cost once; include work transferred to developers or another operations team. If net
savings are zero or negative, there is no positive time-saving break-even. A risk-reduction benefit
may still justify the work, but needs its own evidence and human tradeoff. Use ranges when demand or
maintenance is uncertain; do not claim a payback date from weak estimates. One-time and maintenance
estimates from the person proposing the work are systematically optimistic: prefer observed build
and maintenance effort from a comparable existing automation, or state the optimism margin applied
and who accepted it. Break-even also assumes
the workflow and its demand survive unchanged: when the payback approaches the workflow's expected
useful life, or adoption ramps slowly, compare cumulative effort over that horizon instead of
quoting a break-even month. Read
[worked cost comparison](references/worked-examples.md) for maintenance and payback sensitivity.

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
Classification: <toil | accepted work | enduring-value work — by this test: manual and recurring with little enduring value is toil (growth with volume is supporting evidence, not a requirement); judgment, deliberate practice or rare recovery is accepted work; work that creates lasting capability is enduring-value work>
Recommendation: <bounded change, mechanism and alternatives>
Owner: <implementation owner; acceptance owner and revisit trigger when accepting>
Verification: <before/after comparison under comparable demand, and what remains unmeasured>
Uncertainty: <material unknowns and what evidence would settle them>
```

Write no durable operational records through this method; requested accepted knowledge goes to
`scribe` through the caller.

Primary method: [Google SRE: Eliminating Toil](https://sre.google/workbook/eliminating-toil/), for
measurement, option selection and maintenance economics; its organization-specific targets are not
fleet policy.
