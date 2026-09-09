# Saturation triage

Read only for a DB-driven incident involving connection, lock, replication, storage, or recent-change
signals. Diagnose read-only; any pool change, query kill, failover, scaling, or other live mitigation
still requires the exact human-approved incident packet in `../SKILL.md`.

Name the engine/version, database, affected app, UTC window, and available access. Start in the
app's pool dashboard: active/idle connections, pending borrowers, wait time and timeouts over the
same window. If unavailable, request that slice from the app owner; missing metrics are unknown.
For DB-side blocking, ask the DBA for a bounded, sanitized session/wait snapshot for that database:
PostgreSQL `pg_stat_activity` with `pg_blocking_pids`, or SQL Server `sys.dm_exec_requests` with
`sys.dm_os_waiting_tasks`. Include transaction age and blocker IDs; omit SQL literals and credentials.
A helper without permitted SQL tools returns this request instead of executing it.

Use the first evidence to choose the next discriminator:

- **Connections:** pool occupancy, wait time, timeouts, database-session limits, and leak evidence.
  Separate an undersized pool from leaked or long-held connections before recommending a change.
- **Locks/blocking:** blocked duration, transaction age, and the head blocker. Identifying a blocker
  is diagnosis; killing it is a state-changing action with its own blast radius and recovery plan.
- **Replication lag:** current lag, freshness impact, and failover risk. Hand SLO/burn evidence to
  `observability-engineer` with raw windows, thresholds, and measurements.
- **Disk, IOPS, and temp:** capacity, latency, growth, and runaway sort/spill evidence.
- **Recent migrations and deploys:** correlate times with the symptom and give the evidence to the
  responder with `incident-investigation` without upgrading correlation into root cause.

Return current impact, verified signals, competing hypotheses, the next read-only discriminator, and
the named owner. If mitigation is requested, reference the safety packet from `../SKILL.md` and
report its approval state and gaps; never execute mitigation.
