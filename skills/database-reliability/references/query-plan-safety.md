# Query-plan safety

Read only when selecting or interpreting a database execution plan. Start with plan-only evidence;
an actual/analyzed plan is an execution and inherits the production-change boundary in `../SKILL.md`.

| Engine | Plan only | Executes the statement |
|---|---|---|
| PostgreSQL | `EXPLAIN <statement>` | `EXPLAIN ANALYZE <statement>` |
| SQL Server | estimated plan / `SET SHOWPLAN_XML ON` | actual plan / `SET STATISTICS XML ON` |
| Oracle | `EXPLAIN PLAN` + `DBMS_XPLAN.DISPLAY` | executing the statement |

## Escaping effects

An explicit transaction followed by rollback may undo ordinary PostgreSQL DML; it does not undo
sequence consumption or external/nontransactional effects. Confirm there are no volatile functions,
triggers, FDW/dblink writes, programs, or other escaping effects before considering execution.

Treat SQL Server `STATISTICS XML` exactly like running the statement, including its permissions,
load, mutation, and session-option cleanup.

## Oracle licensing

`[sourced]` AWR, ADDM, ASH, and AWR-backed `DBMS_XPLAN` functions require Diagnostics Pack
entitlement regardless of access path. `CONTROL_MANAGEMENT_PACK_ACCESS` can disable pack use; it does
not prove entitlement. Confirm the human owner's contract before use. Prefer permitted `EXPLAIN
PLAN`/`DBMS_XPLAN.DISPLAY` or Statspack where appropriate.

Sources: [PostgreSQL plan usage](https://www.postgresql.org/docs/current/using-explain.html),
[SQL Server `SET SHOWPLAN_XML`](https://learn.microsoft.com/en-us/sql/t-sql/statements/set-showplan-xml-transact-sql?view=sql-server-ver17),
[SQL Server `SET STATISTICS XML`](https://learn.microsoft.com/en-us/sql/t-sql/statements/set-statistics-xml-transact-sql?view=sql-server-ver17),
[Oracle 19c `DBMS_XPLAN`](https://docs.oracle.com/en/database/oracle/oracle-database/19/arpls/DBMS_XPLAN.html),
[Oracle 19c Licensing Information](https://docs.oracle.com/en/database/oracle/oracle-database/19/dblic/Licensing-Information.html),
and [Oracle 19c `CONTROL_MANAGEMENT_PACK_ACCESS`](https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/CONTROL_MANAGEMENT_PACK_ACCESS.html).
Verify the exact engine/version and the owner's Oracle contract before treating any command or
feature as available.
