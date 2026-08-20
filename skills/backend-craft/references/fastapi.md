# FastAPI and Pydantic mechanics

Read only when the verified target uses FastAPI/Pydantic. Match the repository's layout and pinned
versions; this file does not make FastAPI a greenfield default.

## Application boundary

- Keep HTTP translation thin and business/domain code framework-independent where practical. Own
  clients, pools, and other resources through the application's lifespan; schema changes use the
  repository's migration tool, never startup `create_all` against real data.
- Validate settings at startup with the repository's configuration mechanism. Do not assume PCF,
  `VCAP_SERVICES`, SQLAlchemy, or `pydantic-settings` unless the checkout proves them.
- Separate authentication (`401` and the protocol's challenge) from authorization (`403`) and
  resource-level access checks.

## Response schemas

Declare an explicit public output schema for every JSON endpoint that returns a body, using a typed
return annotation or `response_model=`. Use `response_model=None` only for an intentional stream,
file, redirect, or custom response, and test that internal fields are absent.

Pydantic `from_attributes=True` lets a model read object attributes; it is not the disclosure
boundary and does not prove lazy attributes are loaded or safe. Separate input/update/output models
where their contracts differ. Apply partial updates from explicitly supplied fields rather than
turning omitted values into destructive defaults.

## Transactions and async

- Let database constraints enforce uniqueness and translate expected integrity failures into typed
  domain errors. A select-then-insert precheck is not concurrency control.
- Keep transaction ownership explicit and roll back failed sessions before reuse.
- In async routes, do not call blocking drivers or CPU-heavy work on the event loop. Match the
  repository's sync/async stack rather than converting only one layer.

## Tests

Exercise application lifespan. FastAPI/Starlette `TestClient` must be used as a context manager when
startup/shutdown matters. HTTPX `ASGITransport` does not emit ASGI lifespan events; async tests need
an ASGI lifespan manager or the application's lifespan context.

Test real routing, validation, exception mapping, response filtering, dependency overrides, startup/
shutdown failure, and the selected database's semantics. In-memory SQLite is not evidence for
PostgreSQL-specific constraints, locking, or SQL.
