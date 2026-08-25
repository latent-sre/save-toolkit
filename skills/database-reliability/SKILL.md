---
name: database-reliability
description: >-
  Diagnose and improve data-layer reliability: slow queries, lock contention, replication lag,
  connection pools, schema migrations, and recovery evidence. Triggers: 'this query is slow',
  'plan this schema migration', 'the connection pool is exhausted'. Ownership map only—not a
  load: the `pcf-ops` skill owns app-side triage, the `obs-alerting` skill owns burn alerts,
  the `backend-craft` skill owns persistence code, and the `language-idiom` skill owns safe refactoring
  and language idiom.
---

# Database reliability

Keep data **correct, durable, and fast**, and make schema change safe in production. Our apps run on
PCF and bind to managed relational services (Postgres / MS SQL; a few apps embed SQLite, which is
not an operated engine — the one rule that matters is in `stack-profile`) — you operate at the
*application + data* layer, not the DB platform internals. Canonical `backend-craft` owns writing
persistence and migration code; this skill owns operating it safely, diagnosing it, and proving recovery.

> **Safety rule (non-negotiable):** read-only inspection is fine; any **state-changing or prod-facing**
> action (running a migration, `UPDATE`/`DELETE`, killing a query, failover, scaling) requires an
> existing human-approved exact change and recovery packet naming the target, commands, blast radius,
> verification, recovery strategy, and actor. If the packet is absent or materially different, stop
> and hand it to the human release owner.

## Core decision rules

### Migration safety

- Prefer backward-compatible, online changes with no long table locks, assessed on production-scale
  data rather than a tiny development table.
- Every migration needs a tested recovery strategy, not necessarily a reverse script. Choose the
  path that preserves writes and data: a demonstrably lossless backout, a roll-forward or
  compensating fix, restore/PITR, or an expand/contract transition. Never offer a destructive
  reversal merely to make a packet look reversible.
- Use **expand → contract** when running code depends on the schema: expand with the compatible
  shape; backfill in bounded batches; dual-write/read while both shapes coexist; switch only after
  verification; contract in a later deploy after proving nothing reads the old shape.
- Never rename or drop a shape in the same deploy while currently running code still uses it.
- Freeze the exact engine, version/edition, topology, table size, traffic pattern, migration-tool
  transaction mode, and compatibility window before choosing DDL. Treat missing target facts as
  `[unverified]`, not as permission to assume an online path.

### Performance, durability, and ownership

- An actual/analyzed plan **executes the statement**. Default to a plan-only form; an executing plan
  inherits the production-change boundary, and wrapping it in a transaction is not a universal
  rollback because effects may escape the transaction.
- Application diagnosis and DBA operations are different lanes. Reading a plan and fixing a query
  are ours; changing DB parameters or executing against production needs DBA sign-off and the exact
  human-approved packet.
- Index for measured query patterns, avoid N+1 access and unbounded result sets, and verify any fix
  with before/after evidence. Hand query/ORM implementation to `software-engineer` with the plan and contract.
- Backups must be monitored **and restored in a drill**. An untested backup does not prove recovery,
  RPO, or RTO. Verify replication and failover rather than assuming them.
- Use scoped database credentials, never an application admin role. No unbounded `UPDATE`/`DELETE`:
  require a predicate and row-count sanity check, plus the tested recovery strategy.
- During a DB-driven incident, preserve `[verified]`, `[sourced]`, and `[unverified]` labels. A human
  release owner may mitigate only from the current incident packet's exact approved command and
  target; the agent diagnoses and hands off.

## Read only the conditional procedure the request needs

| If the request involves… | Read first |
|---|---|
| PostgreSQL column/constraint/index/generated-column migration mechanics or version-dependent DDL | [PostgreSQL migrations](./references/postgres-migrations.md) |
| SQL Server column/index migration mechanics, edition limits, or row-size/space risks | [SQL Server migrations](./references/sql-server-migrations.md) |
| Selecting or interpreting plan-only versus actual/analyzed execution plans | [Query-plan safety](./references/query-plan-safety.md) |
| Pool exhaustion, blocking, replication lag, storage pressure, or recent-change incident triage | [Saturation triage](./references/saturation-triage.md) |
| A restore rehearsal or a claim about backup recoverability, measured RPO, or measured RTO | [Restore drill](./references/restore-drill.md) |

Load every matching row and no others. Do not infer an engine/version, live authority, or recovery
claim from the request. The entrypoint rules remain authoritative after a reference is loaded.

## Output format

- **Migrations:** compatibility sequence, engine/version assumptions, production-scale lock/risk
  assessment, forward change, tested recovery strategy, and owner. Include a reverse script only
  when it is demonstrably lossless; otherwise name the roll-forward, compensating, or restore path.
  Implementation goes to `software-engineer`.
- **Performance:** plan-only versus executing evidence labelled, with measured before/after results.
- **Incidents/recovery:** current evidence, hypothesis labels, human action boundary, and measured
  recovery gaps. Never present a destructive change without the safety check and recovery strategy.

Ownership map only—not a load: the `language-idiom` skill owns call-site/contract analysis and safe refactoring;
the `eng-ladder` skill owns principal altitude; the `pcf-ops` skill owns app-side triage. This skill
contains the database method it requires.
