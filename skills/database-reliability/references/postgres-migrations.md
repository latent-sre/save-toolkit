# PostgreSQL migrations

Read only for PostgreSQL-specific migration mechanics. The compatibility, recovery, authority, and
output contracts in `../SKILL.md` remain binding. Confirm the deployed major with
`SHOW server_version;`; it is `[unverified]` until observed.

## Bound every lock wait

Blocking depends on the requested lock. `ADD COLUMN`, `ADD CHECK`/`NOT NULL`, `SET NOT NULL`, and
`ALTER … TYPE` take `ACCESS EXCLUSIVE`; a waiting request can queue later reads and writes.
`ADD FOREIGN KEY` takes `SHARE ROW EXCLUSIVE` on both tables, conflicting with writers but not
ordinary `SELECT`. `CREATE INDEX CONCURRENTLY` and `VALIDATE CONSTRAINT` use `SHARE UPDATE EXCLUSIVE`,
which permits ordinary reads and writes but conflicts with some maintenance and DDL. Inspect the
actual blockers (`pg_stat_activity`, `pg_locks`, through the DBA), not merely all open transactions.
Run the migration session with `SET lock_timeout = '<seconds, below the app's request timeout>'`
(session or `SET LOCAL`, never
`postgresql.conf`) and retry with backoff on timeout. A timed-out or failed `CREATE INDEX
CONCURRENTLY` may leave an INVALID index. Inspect the catalog and migration record first; use
`DROP INDEX CONCURRENTLY` only for the invalid index created by that failed attempt, before retrying.
Do not drop a pre-existing valid index merely because creation failed. *[sourced:
PostgreSQL 18 [lock modes](https://www.postgresql.org/docs/18/explicit-locking.html),
[`lock_timeout`](https://www.postgresql.org/docs/18/runtime-config-client.html#GUC-LOCK-TIMEOUT), and
[concurrent index creation](https://www.postgresql.org/docs/18/sql-createindex.html#SQL-CREATEINDEX-CONCURRENTLY) references]*

## Constraints and columns

Adding `NOT NULL` to an existing column can scan the table while validating every row. Do not run a
direct `ALTER COLUMN ... SET NOT NULL` against a hot, large table without the exact target facts and
lock assessment.

`NOT VALID` skips the initial scan, not enforcement on subsequent inserts and updates. An unrelated
field update still fails if the resulting row retains a legacy NULL. Before adding the constraint,
make all active writers compatible, including updates of old rows: backfill first or correct the NULL
in the same update. Test that path while a backfill is incomplete. Commit the short constraint-add
transaction before backfill/validation so its stronger lock does not span those phases.
The constraint syntax depends on the major:

- **18+**: `NOT NULL` is a catalogued, nameable constraint that accepts `NOT VALID` directly.
  `ALTER TABLE t ADD CONSTRAINT t_col_nn NOT NULL col NOT VALID;` enforces inserts and updates.
  Correct remaining NULLs in bounded batches, then `ALTER TABLE t VALIDATE CONSTRAINT t_col_nn;`
  scans under `SHARE UPDATE EXCLUSIVE`, compatible with ordinary writes. No `CHECK` detour or second
  `SET NOT NULL` step is needed. *[sourced: PostgreSQL 18
  [ALTER TABLE](https://www.postgresql.org/docs/18/sql-altertable.html)]*
- **12–17**: add `CHECK (col IS NOT NULL) NOT VALID`, backfill, validate the constraint, and
  only then run `SET NOT NULL`; the validated check lets these versions skip the second scan
  ([PostgreSQL 17 ALTER TABLE](https://www.postgresql.org/docs/17/sql-altertable.html)).
- **Before 12**: do not assume the validated check avoids the final scan; assess that scan and its
  lock duration on the exact version before scheduling the change. Scan avoidance was introduced in
  [PostgreSQL 12](https://www.postgresql.org/docs/12/release-12.html).

On PostgreSQL 18+, generated columns are **virtual by default** and computed on read. Adding one no
longer rewrites the table, but moves computation to queries; specify `STORED` when that is the intended
behavior. *[sourced: PostgreSQL 18 [generated columns](https://www.postgresql.org/docs/18/ddl-generated-columns.html)
and [release notes](https://www.postgresql.org/docs/18/release-18.html); reviewed 2026-09-30]*

## Index and tool behavior

- Prefer `CREATE INDEX CONCURRENTLY` for a hot table and `ADD COLUMN` without a volatile default, but
  verify lock acquisition, runtime, partial-failure cleanup, and the migration tool's transaction mode.
- Run migrations through the repository's migration tooling (Flyway, Liquibase, Alembic, or
  `migrate` as applicable), not ad-hoc production SQL.
- Add production-scale scan/rewrite behavior, replication/log impact, cancellation, and retry
  identity to the migration handoff defined in `../SKILL.md`.
