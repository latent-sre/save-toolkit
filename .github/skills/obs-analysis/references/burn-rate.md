# Error budgets and multi-window burn-rate alerting

## Error-budget arithmetic

Keep time-based and request-based SLIs in their own units and never mix them:

- **Time-based (`bad_minutes`):** `budget_minutes = (1 - SLO / 100) * window_minutes` (for a 28-day
  window, `40,320 * (1 - SLO / 100)` minutes; for 30 days, `43,200 * (1 - SLO / 100)` minutes).
- **Request-based (`bad_events`, `total_events`):** `budget_requests = (1 - SLO / 100) * total_events`,
  `remaining = budget_requests - bad_events`. Preserve exact fractional request budgets (e.g.,
  `99.9%` over `600` requests → `budget = 0.6 failed requests`) and report
  `additional whole failures permitted (fixed denominator) = max(0, floor(remaining))` (`[ok]` when
  `remaining > 0`, `[EXHAUSTED]` when `remaining == 0`, `[OVER BUDGET]` when `remaining < 0`).

## Google SRE Workbook 30-day multi-window burn-rate pairs

Select actual windows and thresholds from the service's reviewed SLO rule; the standard 30-day
reference pairs are:

| Long window | Short window | Burn rate (`B`) | 30d budget consumed | Error-ratio threshold (`B * (1 - SLO/100)`) | Action |
|---|---|---|---|---|---|
| `1h` | `5m` | `14.4` | 2% | `0.0144` at 99.9% SLO | `PAGE (fast burn)` |
| `6h` | `30m` | `6.0` | 5% | `0.0060` at 99.9% SLO | `PAGE (slow burn)` |
| `24h` (`1d`) | `2h` | `3.0` | 10% | `0.0030` at 99.9% SLO | `TICKET` (or slow page) |
| `3d` | `6h` | `1.0` | 10% | `0.0010` at 99.9% SLO | `TICKET (slow leak)` |

## Verdict boundary

A burn-rate rule requires **both** the long and short windows to meet or exceed their pair's
threshold (`and`, never `or` or mixed pairs):

| Threshold met by | Verdict |
|---|---|
| Both windows (`long >= B*(1-SLO)` and `short >= B*(1-SLO)`) | Pair's `PAGE` or `TICKET` |
| Long only | No page; short window recovered, though budget may already be spent |
| Short only | No page; unconfirmed brief spike, re-check |
| Neither | Below pair threshold (not proof of remaining period budget) |
| Unreachable (`B * (100 - SLO) > 100`) | Pair can never fire at this SLO; pick a reachable pair |
