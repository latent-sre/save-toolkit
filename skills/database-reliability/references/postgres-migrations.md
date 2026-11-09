# PostgreSQL migrations

Apply the [parent migration and authority rules](../SKILL.md). Confirm the deployed major with
`SHOW server_version;` before selecting version-dependent DDL.

## Bound every lock wait

`ADD COLUMN`, `ADD CHECK`/`NOT NULL`, `SET NOT NULL`, and `ALTER … TYPE` take `ACCESS EXCLUSIVE`;
a waiting request can queue reads/writes. `ADD FOREIGN KEY` takes `SHARE ROW EXCLUSIVE` on both
tables, conflicting with writers but not ordinary `SELECT`. `CREATE INDEX CONCURRENTLY` and
`VALIDATE CONSTRAINT` use `SHARE UPDATE EXCLUSIVE`: ordinary reads/writes proceed, some maintenance
and DDL conflict. Have the DBA inspect actual blockers through `pg_stat_activity`/`pg_locks`.
Bound waits with `SET lock_timeout = '<seconds, below the app's request timeout>'` (session or
`SET LOCAL`, never `postgresql.conf`), with backoff on timeout. Concurrent indexing needs the
separate treatment below.

`CREATE INDEX CONCURRENTLY` waits before both scans for transactions that modified the table,
and after the second for older snapshots, including transactions touching only other tables.
A seconds-scale `lock_timeout` cancels those waits, leaving an INVALID index; retries repeat the
failure while the old transaction lives. Have the DBA inspect database-wide `xact_start` and
`backend_xmin` in `pg_stat_activity`. Avoid a short `lock_timeout` for this build: ordinary
reads/writes proceed, but vacuum and other table DDL wait. The DBA monitors and cancels at an
agreed deadline. A unique build that fails in the second scan leaves an INVALID index that still
enforces uniqueness, so writes can fail on it until it is dropped. After failure/cancellation,
inspect catalog and migration records; use
`DROP INDEX CONCURRENTLY` only for the INVALID index created by that attempt, never a pre-existing
valid index, before retrying.

## Constraints and columns

Existing-column `SET NOT NULL` can scan the table; assess exact-target locking before using it on
a hot, large table.

`NOT VALID` skips the initial scan, not enforcement on subsequent inserts and updates. An unrelated
field update still fails if the resulting row retains a legacy NULL. First make every insert supply
the value, then keep to one of two orders:

- **Backfill first:** correct every legacy NULL in bounded batches, then add the `NOT VALID`
  constraint and validate it. No legacy row remains for an update to trip over.
- **Constraint first:** make every update of an old row also correct its NULL, then add the
  `NOT VALID` constraint, backfill, and validate. Test that update path while the backfill is
  incomplete.

Commit the short constraint-add transaction on its own so its stronger lock does not span the
backfill or validation. The constraint syntax depends on the major:

- **18+**: `NOT NULL` is a catalogued, nameable constraint that accepts `NOT VALID` directly.
  `ALTER TABLE t ADD CONSTRAINT t_col_nn NOT NULL col NOT VALID;` enforces inserts and updates.
  After the backfill, `ALTER TABLE t VALIDATE CONSTRAINT t_col_nn;` scans under
  `SHARE UPDATE EXCLUSIVE`, compatible with ordinary writes. No `CHECK` detour or second
  `SET NOT NULL` step is needed.
- **12–17**: use `CHECK (col IS NOT NULL) NOT VALID`; after the backfill, validate it and only then
  run `SET NOT NULL`; the validated check lets these versions skip the second scan.

On PostgreSQL 18+, generated columns are **virtual by default** and computed on read. Adding a virtual
one needs no table rewrite but moves computation to queries; it cannot be indexed (index the
base-column expression instead) and logical replication does not publish it. Adding a `STORED` one
still rewrites the table and its indexes.

## Index and tool behavior

- Prefer `CREATE INDEX CONCURRENTLY` for a hot table and `ADD COLUMN` without a volatile default, but
  verify lock acquisition, runtime, partial-failure cleanup, and the migration tool's transaction mode.
- Add production-scale scan/rewrite, replication/log impact, cancellation and retry identity to the
  parent migration handoff.
