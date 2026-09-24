# SQL Server migrations

Read only for SQL Server-specific migration mechanics. The compatibility, recovery, authority, and
output contracts in `../SKILL.md` remain binding. The target edition is `[unverified]` until observed;
do not plan on an online operation merely because the syntax exists.

## Bound every lock wait

DDL waiting at normal priority blocks every later request on the table, so bound every wait:

- Index create on 2022+ and online index rebuild on 2014+: `WITH (ONLINE = ON (WAIT_AT_LOW_PRIORITY
  (MAX_DURATION = <n ≥ 1> MINUTES, ABORT_AFTER_WAIT = SELF)))`. Never use `BLOCKERS`: it kills user
  transactions, which is a query kill needing its own approval.
- Online `ALTER COLUMN` rejects `WAIT_AT_LOW_PRIORITY`. For it, for `ADD` column/constraint, other
  offline DDL, and index builds before 2022, run `SET LOCK_TIMEOUT <ms>` and `SET XACT_ABORT ON` in
  the migration session. Handle lock timeout (error 1222) in the migration tool's error path;
  roll back any still-open migration transaction and confirm cleanup before retrying with backoff.
  Do not infer cleanup from `XACT_ABORT` alone; verify the tool's transaction and error behavior.
  `LOCK_TIMEOUT` still waits at normal priority, so keep it to seconds.

*[sourced: SQL Server `ALTER TABLE`, `CREATE INDEX`, `SET LOCK_TIMEOUT`, `SET XACT_ABORT`, and
[lock-timeout error handling](https://learn.microsoft.com/en-us/sql/relational-databases/sql-server-transaction-locking-and-row-versioning-guide#customize-the-lock-time-out)
references]*

## Columns

The cheap path is a **new** column, not tightening an existing nullable column. `ADD col ... NOT NULL
DEFAULT <constant>` is metadata-only and near-instant on Enterprise edition: the default is written
to a row when the row is next updated or the index rebuilt. It is not online for `varchar(max)`,
`xml`, or CLR types, and falls back to an offline rewrite if the addition pushes a row past 8,060
bytes.

Tightening an existing nullable column to `NOT NULL` still scans. Backfill in bounded batches and
alter in a quiet window, or use `ALTER COLUMN ... WITH (ONLINE = ON)` only after confirming the
edition and roughly twice the free space for the hidden replacement column. *[sourced: SQL Server
`ALTER TABLE` reference; reviewed 2026-08-21]*

## Index and tool behavior

`CREATE INDEX ... WITH (ONLINE = ON)` takes short locks at its boundaries but is Enterprise-only and
waits for every open transaction on the table before it begins; a long-running report can stall the
migration. *[sourced: SQL Server `ALTER TABLE` reference; reviewed 2026-08-21]*

Add the exact edition, row-size and LOB facts, table/index size, open-transaction risk, expected
duration, space, and cancellation behavior to the migration handoff defined in `../SKILL.md`.
Run the change through the repository's migration tooling rather than ad-hoc production SQL.
