---
name: database-reliability
description: >-
  Diagnose and improve live data-layer reliability: slow queries, lock contention, replication lag,
  connection-pool saturation, production schema migrations, and restore evidence. Use for query-plan
  safety, online DDL, migration recovery, and database-driven incidents. Not for ordinary repository/
  ORM implementation or app-side triage; those belong to backend-craft and pcf-ops. Triggers: 'this
  query is slow', 'plan this migration', 'the connection pool is exhausted'.
---

> **Evidence default — `[unverified]`.** Unless a paragraph carries a narrower label, each
> stack/product-specific command, query, API or CLI behavior, version, licensing statement, and
> runtime claim in this skill and its bundled files is `[unverified]` for the exact target.
> A narrower `[sourced]` or `[verified]` label takes precedence; handoffs never upgrade it.

# Database reliability

Protect correctness and recoverability before speed. Establish the exact engine, version, topology,
data volume, traffic shape, migration tool, and application compatibility window before prescribing
DDL or interpreting a plan. Before recommending runtime, tooling, or infrastructure change, load
`stack-profile`.

> **Production boundary:** read-only inspection is allowed only within the caller's access and data
> handling rules. Migration execution, DML, query cancellation, failover, scaling, or any other live
> effect requires a human-approved packet naming the exact target/action, blast radius, verification,
> recovery path, and human executor. Missing or changed approval means stop and hand off.

## Migration method

- Every migration needs a tested recovery plan, not necessarily a down script. Choose a verified
  lossless reverse migration, forward/compensating fix, or restore/PITR according to which preserves
  writes created after deployment. Never offer a destructive “rollback” that cannot reconstruct the
  current state.
- Prefer additive expand → backfill → dual-read/write as required → switch → contract. Separate the
  application rollback decision from data recovery. Drop or rename only after measured evidence shows
  no supported caller reads or writes the old shape.
- Record the compatibility window, lock mode and acquisition risk, scan/rewrite behavior, runtime on
  production-scale data, replication/log impact, cancellation behavior, tool transaction mode, and
  cleanup for partial failure. Do not call DDL “online” without those facts.
- Never assume DDL transactionality from the migration framework. Verify the exact engine/version and
  whether the operation is permitted in a transaction.

### PostgreSQL constraints and indexes

- Direct `SET NOT NULL` may scan unless a valid constraint already proves no nulls, and it still
  requires a strong table lock. For a hot large table, consider `CHECK (col IS NOT NULL) NOT VALID`,
  backfill, `VALIDATE CONSTRAINT` under its documented lock, then schedule `SET NOT NULL` in a
  controlled lock window. Verify target-version and partition behavior before adopting the sequence.
- `CREATE INDEX CONCURRENTLY` reduces blocking of ordinary writes but cannot run inside a transaction
  block, performs multiple scans/waits, allows only one concurrent build per table, may leave an
  `INVALID` index after failure, and cannot directly build the partitioned parent. Plan monitoring,
  cleanup, retry, and migration-tool behavior.

## Query-plan safety

`EXPLAIN ANALYZE` executes the statement, including `SELECT` functions or foreign access with side
effects. Default to a compile/plan-only form:

| Engine | Plan only | Executes the statement |
|---|---|---|
| PostgreSQL | `EXPLAIN <statement>` | `EXPLAIN ANALYZE <statement>` |
| SQL Server | estimated plan / `SET SHOWPLAN_XML ON` | actual plan / `SET STATISTICS XML ON` |
| Oracle | `EXPLAIN PLAN` + `DBMS_XPLAN.DISPLAY` | executing the statement |

An explicit transaction followed by rollback may undo ordinary PostgreSQL DML; it does not undo
sequence consumption or external/nontransactional effects. Confirm there are no volatile functions,
triggers, FDW/dblink writes, programs, or other escaping effects before considering execution.
Treat SQL Server `STATISTICS XML` exactly like running the statement, including its permissions,
load, mutation, and session-option cleanup.

For Oracle, AWR, ADDM, ASH, and AWR-backed `DBMS_XPLAN` functions require Diagnostics Pack entitlement
regardless of access path. `CONTROL_MANAGEMENT_PACK_ACCESS` can disable pack use; it does not prove
entitlement. Confirm the human owner's contract before use. Prefer permitted `EXPLAIN PLAN`/
`DBMS_XPLAN.DISPLAY` or Statspack where appropriate.

## Diagnosis

1. Freeze the query, parameters, time window, plan type, engine/version, and observed latency/load.
2. Start with plan-only evidence. Check estimates vs actual evidence only in a safe target; inspect
   access path, cardinality, join order, sorts/spills, predicates, and lock waits.
3. Check saturation: pool wait/leaks, active vs idle connections, long transactions/head blockers,
   replication lag, disk/IOPS/temp, and recent migrations/deploys. Keep correlation separate from
   causation.
4. Change one hypothesis at a time. Match indexes to real predicates/order; remove N+1/unbounded
   reads in application code through a `backend-craft` handoff.
5. Re-run the same workload and report before/after numbers, plan change, variance, and remaining gap.

During an active incident, mitigation remains a recommendation until the human release owner acts
from the current approved packet. Preserve evidence labels and hand application-side triage to `sre`
or `pcf-ops` as appropriate.

## Durability and guardrails

- Monitor backup completion and prove restoration. Before claiming RPO/RTO, follow the
  [restore drill](./references/restore-drill.md) against a scratch target and record locate, restore,
  verification, and total duration separately.
- Use least-privilege application credentials. Never expose customer data, credentials, or sensitive
  query parameters in evidence.
- No unbounded `UPDATE`/`DELETE`: establish predicate, expected row count, batch/transaction limit,
  verification, and recovery before execution.

## Output

- **Migration:** forward plan/script, compatibility sequence, engine/version assumptions, lock/risk
  assessment, verification, and selected recovery procedure. Include a reverse script only when it is
  demonstrably lossless for the allowed state.
- **Performance:** exact query/parameter class, plan provenance, before/after measurements, change,
  and unresolved uncertainty.
- **Recovery:** backup identity, objective, measured timings, verification evidence, deviations, and
  pass/pass-with-findings/fail verdict.

Never present a destructive or production-facing command as executed or authorized without the
effect-bound human packet.
