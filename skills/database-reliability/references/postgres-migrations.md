# PostgreSQL migrations

Read only for PostgreSQL-specific migration mechanics. The compatibility, recovery, authority, and
output contracts in `../SKILL.md` remain binding. Confirm the deployed major with
`SHOW server_version;`; it is `[unverified]` until observed.

## Bound every lock wait

Each DDL here first waits for its table lock, and every later query on the table queues behind the
waiting DDL. `ADD COLUMN`, `ADD CONSTRAINT … NOT VALID`, `SET NOT NULL`, and `ALTER … TYPE` take
`ACCESS EXCLUSIVE`; `ADD FOREIGN KEY` takes `SHARE ROW EXCLUSIVE` on both tables. First get the
transactions open on the table (`pg_stat_activity`, through the DBA). Then run the migration session
with `SET lock_timeout = '<seconds, below the app's request timeout>'` (session or `SET LOCAL`, never
`postgresql.conf`) and retry with backoff on timeout. A timed-out or failed `CREATE INDEX
CONCURRENTLY` leaves an INVALID index: `DROP INDEX CONCURRENTLY` it before the retry. *[sourced:
PostgreSQL 18 `ALTER TABLE` and `lock_timeout` references]*

## Constraints and columns

Adding `NOT NULL` to an existing column can scan the table while validating every row. Do not run a
direct `ALTER COLUMN ... SET NOT NULL` against a hot, large table without the exact target facts and
lock assessment. The safe sequence depends on the major:

- **18+**: `NOT NULL` is a catalogued, nameable constraint that accepts `NOT VALID` directly.
  `ALTER TABLE t ADD CONSTRAINT t_col_nn NOT NULL col NOT VALID;` enforces it for new writes, then
  `ALTER TABLE t VALIDATE CONSTRAINT t_col_nn;` scans under `SHARE UPDATE EXCLUSIVE` without blocking
  writes. No `CHECK` detour or second `SET NOT NULL` step is needed. *[sourced: PostgreSQL 18 release
  notes and `ALTER TABLE` reference; GA 2025-09-25; reviewed 2026-08-21]*
- **12–17**: add `CHECK (col IS NOT NULL) NOT VALID`, backfill, validate the constraint, and
  only then run `SET NOT NULL`; the validated check lets these versions skip the second scan.
- **Before 12**: do not assume the validated check avoids the final scan; assess that scan and its
  lock duration on the exact version before scheduling the change. Scan avoidance was introduced in
  [PostgreSQL 12](https://www.postgresql.org/docs/12/release-12.html).

On PostgreSQL 18+, generated columns are **virtual by default** and computed on read. Adding one no
longer rewrites the table, but moves computation to queries; specify `STORED` when that is the intended
behavior. *[sourced: PostgreSQL 18 release notes; reviewed 2026-08-21]*

## Index and tool behavior

- Prefer `CREATE INDEX CONCURRENTLY` for a hot table and `ADD COLUMN` without a volatile default, but
  verify lock acquisition, runtime, partial-failure cleanup, and the migration tool's transaction mode.
- Run migrations through the repository's migration tooling (Flyway, Liquibase, Alembic, or
  `migrate` as applicable), not ad-hoc production SQL.
- Add production-scale scan/rewrite behavior, replication/log impact, cancellation, and retry
  identity to the migration handoff defined in `../SKILL.md`.
