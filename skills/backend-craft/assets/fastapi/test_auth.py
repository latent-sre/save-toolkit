"""Behavior examples for an app choosing the bearer adapter. Adapt these to its auth boundary."""
from __future__ import annotations

import pytest
from auth import authenticated
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient


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
