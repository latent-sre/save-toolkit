# SQL Server migrations

Apply the [parent migration and authority rules](../SKILL.md). Confirm edition/version before
planning online DDL; supported syntax alone does not establish eligibility.

## Bound every lock wait

Conflicting normal-priority DDL can form a blocking chain. Bound each lock phase:

- Index create on 2022+ and online index rebuild on 2014+: `WITH (ONLINE = ON (WAIT_AT_LOW_PRIORITY
  (MAX_DURATION = <n ≥ 1> MINUTES, ABORT_AFTER_WAIT = SELF)))`. Never use `BLOCKERS`: it kills user
  transactions, which is a query kill needing its own approval.
- Online `ALTER COLUMN` rejects `WAIT_AT_LOW_PRIORITY`. For it, `ADD` column/constraint, other
  offline DDL and pre-2022 index builds, use session `SET LOCK_TIMEOUT <ms>` and `SET XACT_ABORT ON`.
  On error 1222, the migration tool must roll back any open transaction and confirm cleanup before
  backoff/retry. `XACT_ABORT` alone does not prove cleanup. `LOCK_TIMEOUT` waits at normal priority:
  keep it to seconds and verify the tool's transaction/error behavior.

## Columns

For a **new** column, SQL Server 2012+ Enterprise can add `NOT NULL DEFAULT <runtime constant>`
without updating existing rows immediately; the default is initially metadata and is materialized
when a row is updated or the table/clustered index is rebuilt. This path excludes `varchar(max)`,
`nvarchar(max)`, `varbinary(max)`, `xml`, `text`, `ntext`, `image`, `hierarchyid`, `geometry`, `geography`,
and CLR user-defined types. It also falls back to an offline operation if the **maximum possible**
row size exceeds 8,060 bytes, even when current rows are short. A per-row default such as `NEWID()`
is not a runtime constant. Check type, default, edition/version, and row-size eligibility before
calling the addition metadata-only; it still needs a schema lock.

Tightening an existing nullable column to `NOT NULL` still scans. Backfill in bounded batches and
alter in a quiet window, or use `ALTER COLUMN ... WITH (ONLINE = ON)` only after confirming the
edition and roughly twice the free space for the hidden replacement column.

## Index and tool behavior

`CREATE INDEX ... WITH (ONLINE = ON)` needs a supporting edition and short boundary locks, varying by
operation/phase. Conflicting transactions or long queries can delay them and form a blocking chain.
Include edition, row-size/LOB facts, table/index size, transaction risk, duration, space and cancellation
in the parent handoff. Use repository migration tooling, not ad-hoc production SQL.
