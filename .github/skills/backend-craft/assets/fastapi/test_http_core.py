"""Common HTTP helper checks: run with house.py and contract_checks.py, without example/auth files."""
from typing import Annotated

from contract_checks import assert_problem
from fastapi import HTTPException, Query
from fastapi.testclient import TestClient
from house import house_app, problems


def test_http_core_without_an_identity_adapter():
    app = house_app("HTTP core", "1.0.0", loopback_only=True)

    @app.get("/health/live")
    def live():
        return {"alive": True}

    @app.post("/v1/probe", responses=problems(409))
    def probe(limit: Annotated[int, Query(ge=1)] = 1):
        raise HTTPException(409, "Conflict")

    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/health/live")
        assert response.json() == {"alive": True} and response.headers.get("X-Request-ID")
        assert_problem(client.post("/v1/probe"), 409)
        body = assert_problem(client.post("/v1/probe?limit=0"), 422)
        first = body["errors"][0]
        assert first["loc"] == ["query", "limit"] and first["msg"]
        assert "input" not in first and "value" not in first
        assert_problem(client.post("/v1/probe", headers={"Origin": "https://other.example"}), 403)
        assert_problem(client.get("/health/live", headers={"Host": "other.example"}), 421)
        document = client.get("/openapi.json").json()
        assert "securitySchemes" not in document["components"]
        assert document["paths"]["/v1/probe"]["post"]["responses"]["409"]["content"] == {
            "application/problem+json": {"schema": {"$ref": "#/components/schemas/Problem"}}
        }
