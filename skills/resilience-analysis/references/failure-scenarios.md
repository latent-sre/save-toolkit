# Select the scenarios the service exposes

Start with the critical user outcome and its dependency path. Use this table to generate leads,
then confirm effective behavior and existing protections before reporting a finding.

| Condition | Inspect | Discriminating evidence |
|---|---|---|
| Dependency latency rises | End-to-end deadline, per-attempt timeout, cancellation, retries, pool occupancy and isolation | Whether abandoned work retains scarce resources or degrades unrelated requests |
| Demand exceeds service rate | Admission limits, queue bounds, load shedding, quotas and scaling delay | Accepted work, useful throughput and queue growth during overload; backlog drain and return to normal afterward |
| An instance/failure domain disappears | Placement, shared dependencies, failover path, remaining capacity and cold-start behavior | Whether surviving capacity supports the required outcome under representative demand |
| Work partially completes | Commit versus acknowledgement, idempotency scope, deduplication retention, replay and reconciliation | Whether timeout/redelivery repeats a business effect or loses accepted work |
| Old and new versions coexist | API/schema compatibility, configuration precedence, rollout order and accepted writes | Old/new consumer behavior and a recovery path that preserves data |
| Data must be restored | Restore scope, recovery dependencies, credentials/access, schema compatibility and business checks | Measured recovery time/data loss and a successful business transaction, not only restore command success |
| A control plane or vendor fails | Ability to keep serving, obtain configuration, renew credentials, resolve names and recover | Which steady-state and recovery paths depend on the unavailable system |
| Telemetry is lost or misleading | Signal freshness, sampling, coverage, missing-series behavior and independent user signals | Whether silence is distinguishable from health and whether the important failure is detectable |
| Operators execute the procedure | Available access, exact target, ambiguous steps, reversibility, escalation and rare expertise | A bounded walkthrough or rehearsal by the intended operator with gaps recorded |

Capacity estimates must distinguish configured maxima, actual demand, startup allocation and
observed bottlenecks. Multiplying instances by per-instance pool size gives potential demand,
not proof that every connection is opened. Independence cannot be assumed merely because replicas
have different names. Include shared databases, quotas, network paths and control planes.

For pipeline and scheduled work, inspect freshness, completeness, correctness, duplication and
deadline completion. For request workloads inspect useful responses, latency and degraded quality.
The human owner determines acceptable tradeoffs; a generic availability target cannot substitute.

Experiments require a hypothesis and conditions that could refute it. Define scope, expected
behavior, observation window appropriate to the mechanism, stop conditions, recovery and applying
owner. The analysis skill only proposes experiments; staging is not automatically harmless and
production authorization is never inferred from a request for analysis.
