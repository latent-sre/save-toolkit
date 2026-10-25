# Saturation triage

Diagnose through the [parent's read-only authority](../SKILL.md). Pool changes, query kills, failover
and scaling require `production-change-gate` and the human/protected executor; incident envelopes
cover only their named actions.

Bind engine/version, database, app, UTC window and access. Start with same-window pool active/idle
connections, pending borrowers, wait time and timeouts; request missing metrics from the app owner; absence stays unknown.
For blocking, request a bounded sanitized DBA snapshot: PostgreSQL `pg_stat_activity` plus
`pg_blocking_pids`, or SQL Server `sys.dm_exec_requests` plus `sys.dm_os_waiting_tasks`. Include
transaction age and blocker IDs, omit SQL literals/credentials. Without permitted SQL tools,
return the request rather than executing it.

Choose the next discriminator from the evidence:

| Signal | Distinguish/check |
|---|---|
| Connections | Pool occupancy/waits/timeouts, DB session limits and leak evidence; undersizing versus leaked or long-held connections |
| Blocking | Blocked duration, transaction age and head blocker; identification never authorizes killing it, which needs its own blast radius/recovery plan |
| Replication lag | Current lag, freshness impact and failover risk; send SLO/burn windows, thresholds and measurements to `observability-engineer` |
| Disk/IOPS/temp | Capacity, latency, growth and runaway sorts/spills |
| Recent migrations/deploys | Compare symptom timing and return evidence to `incident-investigation`; correlation does not establish cause |

Return impact, verified signals, competing hypotheses, next read-only discriminator and owner.
Timed-out requests may have committed: mark effect state unknown and have its owner reconcile before
retry/replay. Requested mitigation returns the applicable gate's approval state and gaps, never execution.
