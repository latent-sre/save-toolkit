# Persistence

Read this when the service owns a database or any persisted state.

The universal backend rules live in `skills/backend-craft/SKILL.md`. On any conflict, SKILL.md wins.

## Persistence

- **Postgres by default** for anything with real data — async driver + a bounded connection pool (asyncpg + SQLAlchemy 2.0 async for FastAPI, pgx for Go, Postgres.js/Drizzle for Node). **SQLite** only for embedded, single-file, single-node cases.
- **Migrations** versioned and reversible, expand → migrate → contract (Alembic for Python). Never edit a shipped migration — add a new one.
- **Explicit, short transaction boundaries** wherever an invariant spans more than one write — and never hold a transaction open across an outbound API call.
- Size the pool to the DB's real connection limit; kill N+1 (fetch related rows in one query, not per row). Parameterized queries only — never string-built SQL.

Ownership map only—not a load: this file owns **writing** the data layer (drivers, pools, migrations, transactions); the `database-reliability` skill owns **operating** it—slow queries, lock contention, replication lag, and pool exhaustion during an incident.
