"""Schema-driven behavior checks; supply the real app and test identity in contract_app.py.
Schemathesis drives the app in-process from its own OpenAPI document: every operation, with
valid and invalid inputs, must answer as the document says, never with a 500. Needs schemathesis in
the dev dependencies."""
from __future__ import annotations

import schemathesis
from contract_app import AUTH_SCHEME, TEST_HEADERS, make_app
from hypothesis import settings

if AUTH_SCHEME is not None:
    assert TEST_HEADERS and all(
        isinstance(name, str) and name.strip() and isinstance(value, str) and value.strip()
        for name, value in TEST_HEADERS.items()
    ), "Configure nonempty test identity header names and values for AUTH_SCHEME"

app = make_app()
schema = schemathesis.openapi.from_dict(app.openapi())
schema.app = app  # schema checks do not require an exposed or unauthenticated document endpoint
# The test supplies identity, so Schemathesis does not generate security parameters; the service
# ignores query parameters it does not declare, so an extra one is not invalid input.
schema.config.generation.update(allow_extra_parameters=False, with_security_parameters=False)


@schema.parametrize()
@settings(max_examples=25, deadline=None)
def test_api_matches_its_document(case):
    case.call_and_validate(headers=TEST_HEADERS)
