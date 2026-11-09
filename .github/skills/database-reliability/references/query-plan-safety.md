# Query-plan safety

Default to plan-only evidence. Classify actual/analyzed execution's effects and load under the
[parent authority rule](../SKILL.md).

| Engine | Plan only | Executes the statement |
|---|---|---|
| PostgreSQL | `EXPLAIN <statement>` | `EXPLAIN ANALYZE <statement>` |
| SQL Server | estimated plan / `SET SHOWPLAN_XML ON` | actual plan / `SET STATISTICS XML ON` |

Check side effects first; prefer an isolated copy, or a read replica for compatible read-only
queries. Mutating execution still incurs row locks, triggers, sequence consumption and WAL even
with rollback.

On an isolated copy, or inside an approved production change, PostgreSQL documents this pattern for
measuring ordinary mutating DML:

```sql
BEGIN;
EXPLAIN ANALYZE <the INSERT/UPDATE/DELETE>;
ROLLBACK;
```

Rollback does not undo `nextval`/sequence consumption, independently committed `dblink` writes or
external effects such as `COPY TO PROGRAM`. FDW behavior is wrapper-specific: `postgres_fdw` aborts
its corresponding remote transaction on local abort. Check volatile functions, triggers and
external transaction boundaries before executing. SQL Server `STATISTICS XML` requires permission
to run the statement plus `SHOWPLAN` on every database it references (a failed check aborts the
statement), the same load/mutation assessment as statement execution, and session-option cleanup.

Return the plan kind, target/environment, execution and mutation risk, approvals, observations, and
measured before/after result. Keep assumptions `[unverified]`.
