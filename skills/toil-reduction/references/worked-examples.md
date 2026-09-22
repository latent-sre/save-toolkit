# Worked examples

Numbers below are fictional inputs, not thresholds or promises of benefit.

## Positive time saving with ongoing costs

A representative month has 24 interventions at 15 minutes each: 360 minutes, or 6 hours.
The proposal needs 40 hours to build and validate, then 2 hours/month of residual handling plus
2 hours/month of maintenance. Net saving is 6 - 2 - 2 = 2 hours/month. Time-only break-even is
40 / 2 = 20 months, assuming comparable demand and no omitted costs. Record uncertainty and
alternative simpler changes before recommending the investment.

If one-time effort varies from 30 to 50 hours and net savings from 1 to 3 hours/month, the bounds
are 10 to 50 months; the inputs and dependence between estimates matter more than a single precise
date. Treat any claimed reduction in mistakes or customer impact as a separate benefit to verify.

## Automation that increases total work

The same 6-hour baseline is replaced by 3 hours/month of residual handling and 4 hours/month of
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
