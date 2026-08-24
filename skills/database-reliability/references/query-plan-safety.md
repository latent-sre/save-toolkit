# Query-plan safety

Read only when selecting or interpreting a database execution plan. Start with plan-only evidence;
an actual/analyzed plan is execution and inherits the production-change boundary in `../SKILL.md`.

| Engine | Plan only | Executes the statement |
|---|---|---|
| PostgreSQL | `EXPLAIN <statement>` | `EXPLAIN ANALYZE <statement>` |
| SQL Server | estimated plan / `SET SHOWPLAN_XML ON` | actual plan / `SET STATISTICS XML ON` |

On a `SELECT`, the executing form creates load. On `INSERT`, `UPDATE`, `DELETE`, or `MERGE`, it makes
the data change. Default to the plan-only column. Use an executing form only after confirming the
statement and side effects, preferably on a non-production copy or read replica, with DBA sign-off
and the exact approved packet for production.

PostgreSQL documents this diagnostic pattern for ordinary mutating DML:

```sql
BEGIN;
EXPLAIN ANALYZE <the INSERT/UPDATE/DELETE>;
ROLLBACK;
```

That rollback is not a blanket safety net. It does not undo sequence/`nextval` consumption or effects
that escape the transaction, including FDW/dblink writes and `COPY TO PROGRAM`. Confirm volatile
functions, triggers, external writes, and other effects before considering execution. Treat SQL
Server `STATISTICS XML` exactly like running the statement, including permissions, load, mutation,
and session-option cleanup.

Return the plan kind, target/environment, execution and mutation risk, approvals, observations, and
measured before/after result. Keep assumptions `[unverified]`.
