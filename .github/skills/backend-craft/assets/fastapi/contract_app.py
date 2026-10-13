"""Replaceable test setup: this version composes the optional Things/bearer example.

    Supply the real app, seeded resources and test identity here. Keep fixture credentials local
    to tests; this module does not select the production corporate SSO provider or protocol.
"""
from __future__ import annotations

from auth import Principal
from main import Settings, Thing, ThingStore, create_app

TEST_HEADERS = {"Authorization": "Bearer test-token"}
AUTH_SCHEME = "bearer"  # the actual key in components.securitySchemes; session cookies also work
PUBLIC_OPERATIONS: set[str] = set()  # deliberately unauthenticated operation IDs


async def _verify(token: str) -> Principal | None:
    return Principal("tester", frozenset({"team:sre"})) if token == "test-token" else None


def make_app():
    return create_app(
        # Schemathesis's in-process host is accepted; test_http_core covers the loopback Host guard.
        Settings(host="0.0.0.0", port=8000, trusted_request_id_header=None),
        _verify,
        ThingStore([Thing(id=f"thing-{i:04d}", name=f"Thing {i}", team="sre") for i in range(1, 30)]),
    )
