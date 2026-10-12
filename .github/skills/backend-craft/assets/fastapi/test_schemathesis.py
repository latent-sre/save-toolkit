"""Schemathesis drives the app in-process from its own OpenAPI document: every operation, with
valid and invalid inputs, must answer as the document says, never with a 500. The test token
lives here, in the test verifier; the service never accepts a static token. Needs schemathesis in
the dev dependencies."""
from __future__ import annotations

import schemathesis
from house import Principal
from hypothesis import settings
from main import Settings, Thing, ThingStore, create_app

TOKEN = "test-token"


async def verify(token: str) -> Principal | None:
    return Principal("tester", frozenset({"team:sre"})) if token == TOKEN else None


app = create_app(
    # Bound beyond loopback so Schemathesis's test host is accepted; test_house covers the Host guard.
    Settings(host="0.0.0.0", port=8000, trusted_request_id_header=None),
    verify,
    ThingStore([Thing(id=f"thing-{i:04d}", name=f"Thing {i}", team="sre") for i in range(1, 30)]),
)
schema = schemathesis.openapi.from_asgi("/openapi.json", app)


@schema.parametrize()
@settings(max_examples=25, deadline=None)
def test_api_matches_its_document(case):
    case.call_and_validate(headers={"Authorization": f"Bearer {TOKEN}"})
