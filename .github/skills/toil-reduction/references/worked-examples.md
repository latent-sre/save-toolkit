# Worked examples

Numbers below are fictional inputs, not thresholds or promises of benefit.

## Automation that increases total work

A 6-hour monthly baseline is replaced by 3 hours/month of residual handling and 4 hours/month of
maintenance elsewhere. Net saving is -1 hour/month: no positive time-saving break-even, regardless
of build cost. Explain the transfer of work and consider simplification or accepting the current
process. If a demonstrated safety benefit is the purpose, present that tradeoff explicitly rather
than relabeling negative savings as efficiency.

## Recurring restart

Tickets repeatedly say a restart restores progress. This establishes a repeated intervention if
the records are distinct and comparable; it does not establish the cause. Inspect whether a leak,
poison message, stalled dependency or resource limit explains the evidence. A durable defect repair
may remove the task. Automatic restarts require justification against duplicate processing, lost
work and masking of the underlying failure; proposed automation is not an approved mitigation.

## Unknown baseline

An operator says a task happens often but has no frequency or effort record. Return a qualitative
opportunity and the smallest useful measurement window, not an invented ROI. Design the measurement
so collecting it does not become a larger burden than the task being assessed.

## Interview excerpt (thin direct request)

Request: "I keep doing some manual cleanup work and it's getting annoying. Should we just
automate it?" No records are supplied, so the reply is one batched round, not an assessment:

> Before I can judge that: What exactly is cleaned up, what triggers it, and what counts as
> done? Roughly how often over the last month, and is that growing? How long does one run take
> including getting interrupted? Who does it today, and where does it need judgment rather
> than identical steps? What goes wrong if it's late or done badly, and can that be undone?
> Why does the cleanup exist — a defect, a missing scheduled job, growth? What must stay
> manual? Rough ranges are fine; "unknown" just becomes a small measurement.

An assessment follows only from the answers; an unanswered aspect stays `[unverified]`.

## The positive case in the return shape

```text
Baseline: 24 distinct interventions in a representative month, 15 minutes each including
rework — 6 human-hours/month [sourced: ticket export]; no other record systems overlap it.
Options: eliminate (fix the cause — no defect identified), simplify (batch the steps —
kept as fallback), self-service (rejected: requesters lack access), automate (kept),
accept (rejected at current volume).
Calculation: baseline 6 h/month; residual handling 2 + maintenance 2; net saving
2 h/month [unverified: proposer estimate, no comparable automation observed — the
operations lead accepted it unadjusted; if maintenance reaches 3 h/month the net
saving halves and break-even doubles]; build 40 h; time-only break-even 20 months.
Classification: toil — manual and recurring, little enduring value, volume follows ticket count.
Recommendation: automate the bounded procedure below, or simplify if the 20-month horizon
exceeds the workflow's expected life.
Owner: application team implements; operations lead accepts the residual 4 h/month.
Verification: repeat the same export after one comparable month; benefit stays estimated
until residual and maintenance match the prediction.
Uncertainty: maintenance estimate is the proposer's, accepted unadjusted above; the
workflow's expected useful life is unstated, so the horizon comparison remains open.
```

The calculation assumes comparable demand and no omitted costs. If one-time effort varies from
30 to 50 hours and net savings from 1 to 3 hours/month, the bounds are 10 to 50 months; the inputs
and dependence between estimates matter more than a single precise date. Treat any claimed
reduction in mistakes or customer impact as a separate benefit to verify.
