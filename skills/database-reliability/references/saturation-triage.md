# Saturation triage

Read only for a DB-driven incident involving connection, lock, replication, storage, or recent-change
signals. Diagnose read-only; any pool change, query kill, failover, scaling, or other live mitigation
still requires the exact human-approved incident packet in `../SKILL.md`.

Check the cheapest discriminating evidence first:

- **Connections:** pool occupancy, wait time, timeouts, database-session limits, and leak evidence.
  Separate an undersized pool from leaked or long-held connections before recommending a change.
- **Locks/blocking:** blocked duration, transaction age, and the head blocker. Identifying a blocker
  is diagnosis; killing it is a state-changing action with its own blast radius and recovery plan.
- **Replication lag:** current lag, freshness impact, and failover risk. Hand SLO/burn evidence to
  `observability-engineer` with raw windows, thresholds, and measurements.
- **Disk, IOPS, and temp:** capacity, latency, growth, and runaway sort/spill evidence.
- **Recent migrations and deploys:** correlate times with the symptom and give the evidence to `sre-assistant`
  without upgrading correlation into root cause.

Return current impact, verified signals, competing hypotheses, the next read-only discriminator, and
the named owner. If mitigation is requested, show the exact target, command, blast radius,
verification, recovery, actor, and approval state; never execute it.
