# Drill card — <run ID>

One screen per drill, filled at close and kept at the head of the retro, so drills stay comparable
across months without rereading retros. Numbers come from the frozen run conditions and
`drill_report.py`, not from memory.

| Field | Value |
|---|---|
| Date | <YYYY-MM-DD> |
| Scenario | <name, and whether bundled or authored for this run> |
| Fleet revision | <commit, clean or dirty> |
| CLI / model | <CLI version> / <requested → resolved model> |
| Runtime | <disposable credential-free runtime attested? egress boundary> |
| Lanes | <dispatched n of planned m; attempts beyond first> |
| Wall clock / spend | <minutes> / <USD from `drill_report.py`> |
| Verdict | <one sentence: did authority hold, and what the drill found> |
| Fleet findings | <count, by proposed owner — e.g. 2 agent-engineer, 1 software-engineer> |
| Coordinator findings | <count> |
| Retro | <link to the dated retro in the repository's review location> |

A field you cannot fill is itself a finding about the run conditions you froze.

Reference-read token: q_idcard_5d19
