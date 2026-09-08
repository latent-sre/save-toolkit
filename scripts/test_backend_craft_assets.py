"""Exercise the shipped HTTP starters through their public request/fixture contracts."""
from __future__ import annotations

from contextlib import asynccontextmanager
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
import pytest
import yaml


ASSETS = Path(__file__).resolve().parents[1] / "skills/backend-craft/assets"


def load_asset(name):
    spec = importlib.util.spec_from_file_location(name, ASSETS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Payload(BaseModel):
    count: int


@pytest.fixture
def client():
    app = FastAPI()
    load_asset("problem_fastapi").install_problem_handlers(app)

    @app.get("/auth")
    def auth():
        raise HTTPException(401, "Sign in", headers={"WWW-Authenticate": "Bearer"})

    @app.get("/limited")
    def limited():
        raise HTTPException(429, "Wait", headers={"Retry-After": "30"})

    @app.get("/old-representation")
    def old_representation():
        raise HTTPException(401, "Sign in", headers={
            "WWW-Authenticate": "Bearer", "Content-Type": "text/plain", "Content-Length": "0",
        })

    @app.post("/data")
    def data(payload: Payload):
        return payload

    @app.get("/boom")
    def boom():
        raise RuntimeError("private diagnostic must not reach the client")

    with TestClient(app, raise_server_exceptions=False) as http:
        yield http


@pytest.mark.parametrize("method,path,status,header,value", [
    ("GET", "/auth", 401, "WWW-Authenticate", "Bearer"),
    ("GET", "/limited", 429, "Retry-After", "30"),
    ("POST", "/auth", 405, "Allow", "GET"),
])
def test_problem_keeps_protocol_headers(client, method, path, status, header, value):
    response = client.request(method, path)
    assert response.status_code == status
    assert response.headers.get(header) == value
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["status"] == status
    assert "headers" not in response.json()


@pytest.mark.parametrize("body,status", [('{"count":', 400), ('{"count":"wrong"}', 422)])
def test_malformed_json_is_distinct_from_invalid_values(client, body, status):
    response = client.post("/data", content=body, headers={"Content-Type": "application/json"})
    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["status"] == status


def test_problem_recomputes_headers_for_the_replaced_representation(client):
    response = client.get("/old-representation")
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.headers["content-type"] == "application/problem+json"
    assert int(response.headers["content-length"]) == len(response.content)


def test_validation_response_matches_consumer_fields(client):
    response = client.post("/data", json={"count": "wrong"})
    error = response.json()["errors"][0]
    assert error["loc"] == ["body", "count"]
    assert isinstance(error["msg"], str) and error["msg"]
    schema = yaml.safe_load((ASSETS / "openapi.starter.yaml").read_text(encoding="utf-8"))
    item = schema["components"]["schemas"]["Problem"]["properties"]["errors"]["items"]
    assert set(item["required"]) == {"loc", "msg"}
    assert item["properties"]["loc"] == {"type": "array", "items": {"type": "string"}}
    assert item["properties"]["msg"]["type"] == "string"


def test_unexpected_error_is_redacted_and_correlated(client):
    response = client.get("/boom", headers={"X-Request-ID": "test-request"})
    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["request_id"] == "test-request"
    assert "private diagnostic" not in response.text


def test_starter_urls_and_page_shape_match_the_house_contract():
    schema = yaml.safe_load((ASSETS / "openapi.starter.yaml").read_text(encoding="utf-8"))
    base = urlsplit(schema["servers"][0]["url"]).path.rstrip("/")
    assert {base + path for path in schema["paths"]} == {"/healthz", "/readyz", "/v1/incidents"}
    page = schema["components"]["schemas"]["IncidentPage"]
    assert set(page["required"]) == {"data", "next_cursor"}


@pytest.mark.parametrize("attribute", ["app", "create_app"])
def test_starter_accepts_instance_and_factory_and_runs_lifespan(monkeypatch, attribute):
    events = []

    @asynccontextmanager
    async def lifespan(app):
        events.append("started")
        yield
        events.append("stopped")

    app = FastAPI(lifespan=lifespan)

    @app.get("/state")
    def state():
        return events

    module = ModuleType("craft_fixture_app")
    module.app = app
    module.create_app = lambda: app
    monkeypatch.setitem(sys.modules, module.__name__, module)
    contract = load_asset("test_http_contract")
    contract.APP = f"{module.__name__}:{attribute}"
    loaded = contract.app.__wrapped__()
    assert loaded is app
    fixture = contract.client.__wrapped__(loaded)
    try:
        http = next(fixture)
        assert http.get("/state").json() == ["started"]
    finally:
        fixture.close()
    assert events == ["started", "stopped"]
