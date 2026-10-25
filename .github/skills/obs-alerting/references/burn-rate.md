# Multi-window error-budget burn rate

Carry the reviewed good/valid-event query and results into the alert definition; this reference
supplies no backend query. Keep request/time units and consumed-budget status distinct under the
[parent SLI rules](../SKILL.md#sli-slo-and-burn-rate).

## The pairs

[error_budget.py](../scripts/error_budget.py)'s `WINDOW_PAIRS` implements Google SRE Workbook
30-day examples, not team policy. Select actual windows/thresholds/actions from the owner's reviewed
SLO and alert rule; the calculator lists its supported pairs on a mismatch.

Both windows must meet or exceed their pair's threshold: AND, never OR or mixed pairs. Tiny
low-traffic denominators need separate judgment. Measure actual consumed request budget from
eligible events; changing the objective horizon does not rescale these fixed example thresholds.

## Verdict boundary

For the selected example pair:

| Threshold met by | Verdict |
|---|---|
| Both windows | Pair's PAGE or TICKET |
| Long only | No page; short window recovered, but budget may already be spent |
| Short only | No page; unconfirmed spike, re-check |
| Neither | Below the pair's threshold, not proof of remaining budget |

## Calculator

The stdlib calculator runs through a human or an unguarded lane; the read-only guard denies this calculator.
Resolve its installed absolute path and use the project's verified Python. `--window-days` controls
budget status (default 28), not example alert thresholds; use the reviewed rule for a different policy.

```powershell
$budgetScript = '<resolved calculator path>'
$budgetPython = '<verified project Python executable>'
& $budgetPython $budgetScript --slo 99.9 --window-days 28 --bad-events 200 --total-events 1000000
& $budgetPython $budgetScript --slo 99.9 --sli-long 98.5 --sli-short 98.5 --long-window 1h --short-window 5m
```

These fictional inputs consume 20% of request budget in the first case and yield example PAGE at
15× in both windows in the second. The latter does not establish whole-horizon consumed budget.
