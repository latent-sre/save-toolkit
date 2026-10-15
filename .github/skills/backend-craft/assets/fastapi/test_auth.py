"""Behavior examples for an app choosing the bearer adapter. Adapt these to its auth boundary."""
from __future__ import annotations

import pytest
from auth import Authenticated, Principal, authenticated, configure_bearer_auth
from contract_checks import assert_problem
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from house import house_app


@pytest.mark.parametrize(("headers", "status"), [
    ({}, 401),
    ({"Authorization": "Basic ignored"}, 401),
    ({"Authorization": "Bearer supplied-token"}, 503),
])
def test_unconfigured_bearer_adapter_fails_closed(headers, status):
    app = FastAPI()

    @app.get("/protected", dependencies=[Depends(authenticated)])
    def protected():
        return {"protected": True}

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/protected", headers=headers)
    assert response.status_code == status
    if status == 401:
        assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize(("token", "status"), [(None, 401), ("invalid", 401), ("outage", 503), ("valid", 200)])
def test_bearer_identity_and_verifier_failures(token, status):
    async def verify(value):
        if value == "outage":
            raise ConnectionError("identity provider unreachable")
        return Principal("tester") if value == "valid" else None

    app = house_app("Auth probe", "1.0.0", loopback_only=False)
    configure_bearer_auth(app, verify)

    @app.get("/v1/probe")
    def probe(principal: Authenticated) -> dict[str, str]:
        return {"subject": principal.subject}

    with TestClient(app) as client:
        response = client.get("/v1/probe", headers={"Authorization": f"Bearer {token}"} if token else {})
    if status == 200:
        assert response.json() == {"subject": "tester"}
        assert response.status_code == 200
    else:
        assert_problem(response, status)
        if status == 401:
            assert response.headers["WWW-Authenticate"] == "Bearer"
