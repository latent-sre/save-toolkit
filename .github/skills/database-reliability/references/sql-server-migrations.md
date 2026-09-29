# SQL Server migrations

Read only for SQL Server-specific migration mechanics. The compatibility, recovery, authority, and
output contracts in `../SKILL.md` remain binding. The target edition is `[unverified]` until observed;
do not plan on an online operation merely because the syntax exists.

## Bound every lock wait

Normal-priority DDL can form a blocking chain when its requested lock conflicts with other work.
Assess the operation's lock phases and bound each wait:

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

For a **new** column, SQL Server 2012+ Enterprise can add `NOT NULL DEFAULT <runtime constant>`
without updating existing rows immediately; the default is initially metadata and is materialized
when a row is updated or the table/clustered index is rebuilt. This path excludes `varchar(max)`,
`nvarchar(max)`, `varbinary(max)`, `xml`, `text`, `ntext`, `image`, `hierarchyid`, `geometry`, `geography`,
and CLR user-defined types. It also falls back to an offline operation if the **maximum possible**
row size exceeds 8,060 bytes, even when current rows are short. A per-row default such as `NEWID()`
is not a runtime constant. Check type, default, edition/version, and row-size eligibility before
calling the addition metadata-only; it still needs a schema lock. *[sourced:
[Microsoft's online-add restrictions](https://learn.microsoft.com/en-us/sql/t-sql/statements/alter-table-transact-sql#add-not-null-columns-as-an-online-operation)]*

Tightening an existing nullable column to `NOT NULL` still scans. Backfill in bounded batches and
alter in a quiet window, or use `ALTER COLUMN ... WITH (ONLINE = ON)` only after confirming the
edition and roughly twice the free space for the hidden replacement column. *[sourced: SQL Server
`ALTER TABLE` reference; reviewed 2026-08-21]*

## Index and tool behavior

`CREATE INDEX ... WITH (ONLINE = ON)` needs a supporting edition and short boundary locks.
Conflicting transactions or long-running queries can delay those locks and form a blocking chain;
the required locks vary by index operation and phase. *[sourced:
[online index phases](https://learn.microsoft.com/en-us/sql/relational-databases/indexes/how-online-index-operations-work)]*

Add the exact edition, row-size and LOB facts, table/index size, open-transaction risk, expected
duration, space, and cancellation behavior to the migration handoff defined in `../SKILL.md`.
Run the change through the repository's migration tooling rather than ad-hoc production SQL.
