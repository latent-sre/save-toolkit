# Multi-window error-budget burn rate

Use this method to turn a user-facing SLI into an actionable page or ticket. It does not define the
backend query: carry the reviewed numerator/denominator query and its result into the alert definition.

## Primary method

`[sourced]` Google's SRE Workbook chapter
[Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/) defines burn rate as error-budget
consumption relative to the SLO, recommends multi-window/multi-burn-rate alerting, and in Table 5-8
binds these three starting-point pairs for a 99.9% SLO:

| Long window | Short window | Threshold | Action |
|---|---|---|---|
| 1h | 5m | 14.4x | PAGE (fast burn) |
| 6h | 30m | 6.0x | PAGE (slow burn) |
| 3d | 6h | 1.0x | TICKET (slow leak) |

The pairs are one unit: both windows must meet the pair's one threshold. Do not mix a long window from
one row with a short window from another, apply one row's threshold to another pair, or weaken the
condition from AND to OR. Low-traffic services require separate judgment because a tiny denominator
can turn one failure into an extreme burn.

## Calculation

For an availability SLO expressed as a percentage:

```text
allowed bad fraction = 1 − (SLO / 100)
observed bad fraction = 1 − (SLI / 100)
burn rate             = observed bad fraction / allowed bad fraction
```

The SLI unit still matters:

- Request-based status uses failed requests and total valid requests; its budget is a count of bad
  requests.
- Time-based status uses bad minutes over a time window; its budget is minutes.
- Never translate a request-based budget to downtime minutes by assuming uniform traffic.

## Verdict boundary

- If both windows meet the selected threshold, emit that pair's page/ticket action.
- If only the long window meets it, do not page: the short window has recovered. State explicitly that
  budget may already be spent and calculate budget status separately.
- If only the short window meets it, do not page: treat it as an unconfirmed spike and re-check.
- If neither meets it, state only that the pair is below its alert threshold. That does not prove that
  the service is within budget; alert state and consumed-budget status answer different questions.

## Calculator

The bundled [error_budget.py](../scripts/error_budget.py) is pure stdlib and supports budget-status and
burn-rate modes. These examples exercise its three admitted pair behaviors:

```powershell
py -3 skills/obs-alerting/scripts/error_budget.py --slo 99.9 --sli-long 99.45 --sli-short 99.95
py -3 skills/obs-alerting/scripts/error_budget.py --slo 99.9 --sli-long 99.45 --sli-short 99.8 --long-window 3d --short-window 6h
py -3 skills/obs-alerting/scripts/error_budget.py --slo 99.9 --long-window 3d --short-window 5m
```

The third command is deliberately invalid and must exit 2 with the exact allowed-pair list.

<!-- terminal-canary: q_oaburn_8c71 -->
