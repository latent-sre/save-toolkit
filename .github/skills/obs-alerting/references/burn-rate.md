# Multi-window error-budget burn rate

Turn a user-facing SLI into an actionable page or ticket. This method does not define the backend
query: carry the reviewed numerator/denominator query and its result into the alert definition.

## The pairs

The allowed long/short window pairs, thresholds, and actions are owned by the calculator's
`WINDOW_PAIRS` in [error_budget.py](../scripts/error_budget.py);
run the calculator to see them applied, or pass it a mismatched pair to list the allowed ones.
This file does not mirror the values, so the two cannot drift.

A pair is one unit: both windows must meet or exceed the pair's threshold (AND, never OR).
No pair lends its window or threshold to another. Low-traffic services need separate judgment: a
tiny denominator turns one failure into an extreme burn. For another objective horizon, measure
actual consumed budget from eligible requests rather than rescaling the fixed thresholds by time.

## Verdict boundary

- Both windows at or above the threshold: emit that pair's page or ticket.
- Only the long window at or above: do not page; the short window has recovered. Say that budget may
  already be spent and calculate budget status separately.
- Only the short window at or above: do not page; treat it as an unconfirmed spike and re-check.
- Neither meets the threshold: say only that the pair is below its threshold. That does not prove
  the service is within budget; alert state and consumed-budget status answer different questions.

## Calculator

[error_budget.py](../scripts/error_budget.py) is pure stdlib with budget-status and burn-rate modes.
A human or an unguarded lane runs it and pastes the output; the read-only guard denies script
execution by design. Resolve the linked calculator to its absolute path in this installed skill;
substitute that path below and use the project's verified Python interpreter. Set `--window-days`
to the objective horizon for budget status; its
default is 28 days and it **does not rescale the fixed alert thresholds above**. For a different
threshold policy, use the reviewed alert rule rather than this calculator's verdict. These fictional
inputs demonstrate request-budget status and a valid paired burn:

```powershell
$budgetScript = '<resolved calculator path>'
$budgetPython = '<verified project Python executable>'
& $budgetPython $budgetScript --slo 99.9 --window-days 28 --bad-events 200 --total-events 1000000
& $budgetPython $budgetScript --slo 99.9 --sli-long 98.5 --sli-short 98.5 --long-window 1h --short-window 5m
```

The first result consumes 20% of the request budget. The second pages because both windows burn at
15×; it does not establish the consumed budget over the objective horizon.
