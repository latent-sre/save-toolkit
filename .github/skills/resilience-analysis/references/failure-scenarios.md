# Select the scenarios the service exposes

Use applicable rows as leads, not findings.

| Condition | Evidence that distinguishes failure from effective protection |
|---|---|
| Slow dependency | Effective deadlines, retries and cancellation release scarce resources; unrelated requests retain capacity |
| Overload | Exercise admission/overflow, queue bounds, quotas and scaling delay; measure useful throughput, queue growth and subsequent drain |
| Lost instance/failure domain | Surviving capacity meets the outcome under demand, including cold starts and shared failover dependencies |
| Partial completion | Commit/acknowledgement, idempotency scope, deduplication retention and reconciliation prevent redelivery from duplicating effects or losing accepted work |
| Mixed versions | Old/new consumers, effective configuration and rollout order preserve compatibility and accepted writes through recovery |
| Restore | Access, dependencies and schema permit recovery within required time/data-loss bounds; a business transaction succeeds, not just the restore command |
| Control-plane/vendor loss | Serving and recovery paths still obtain required configuration, credentials and name resolution |
| Missing/misleading telemetry | Freshness, sampling and coverage checks distinguish silence from health against independent user signals |
| Operator procedure | The intended operator rehearses with actual access and targets; ambiguous steps, rare expertise, reversal and escalation gaps remain explicit |

Configured pool maxima multiplied by instance count are potential demand, not opened connections.
Distinguish startup allocation, actual demand and observed bottlenecks. Replica names do not prove
independence: inspect shared databases, quotas, network paths and control planes.

For pipeline and scheduled work, inspect freshness, completeness, correctness, duplication and
deadline completion. For request workloads inspect useful responses, latency and degraded quality.
