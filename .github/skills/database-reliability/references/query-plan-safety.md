# Query-plan safety

Read only when selecting or interpreting a database execution plan. Start with plan-only evidence;
an actual/analyzed plan is execution: classify its effects and load under `../SKILL.md`'s authority rule.

| Engine | Plan only | Executes the statement |
|---|---|---|
| PostgreSQL | `EXPLAIN <statement>` | `EXPLAIN ANALYZE <statement>` |
| SQL Server | estimated plan / `SET SHOWPLAN_XML ON` | actual plan / `SET STATISTICS XML ON` |

On a `SELECT`, the executing form creates load. On `INSERT`, `UPDATE`, `DELETE`, or `MERGE`, it makes
the data change. Default to the plan-only column. Use an executing form only after confirming the
statement and side effects. Prefer an isolated copy; a read replica suits compatible read-only queries.
Production diagnostics need the existing DBA-authorized read path and load bounds; live changes use
`production-change-gate`.

PostgreSQL documents this diagnostic pattern for ordinary mutating DML:

```sql
BEGIN;
EXPLAIN ANALYZE <the INSERT/UPDATE/DELETE>;
ROLLBACK;
```

That rollback is not a blanket safety net. It does not undo sequence/`nextval` consumption or effects
that escape the transaction, such as independently committed `dblink` writes or external effects
from `COPY TO PROGRAM`. FDW behavior depends on the wrapper: `postgres_fdw` aborts its corresponding
remote transaction when the local transaction aborts *[sourced:
www.postgresql.org/docs/current/postgres-fdw.html#POSTGRES-FDW-TRANSACTION-MANAGEMENT]*.
Confirm volatile functions, triggers, and external transaction boundaries before execution. Treat SQL
Server `STATISTICS XML` exactly like running the statement, including permissions, load, mutation,
and session-option cleanup.

Return the plan kind, target/environment, execution and mutation risk, approvals, observations, and
measured before/after result. Keep assumptions `[unverified]`.
