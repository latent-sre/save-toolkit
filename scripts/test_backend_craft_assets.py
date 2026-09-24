"""Exercise the shipped HTTP starters through their public request/fixture contracts."""
from __future__ import annotations

from contextlib import asynccontextmanager
import asyncio
import importlib.util
import logging
from pathlib import Path
import sys
from types import ModuleType
from urllib.parse import urlsplit

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from pydantic import BaseModel
import pytest
from starlette.datastructures import Headers, MutableHeaders
from starlette.middleware.cors import CORSMiddleware
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
    problems = load_asset("problem_fastapi")
    app = FastAPI(responses=problems.problem_responses(400, 422, 500))
    problems.install_problem_handlers(app)

    @app.get("/auth", responses=problems.problem_responses(401))
    def auth():
        raise HTTPException(401, "Sign in", headers={"WWW-Authenticate": "Bearer"})

    @app.get("/limited", responses=problems.problem_responses(429))
    def limited():
        raise HTTPException(429, "Wait", headers={"Retry-After": "30"})

    @app.get("/multi-auth")
    def multi_auth():
        raise HTTPException(401, "Sign in", headers=Headers(raw=[
            (b"www-authenticate", b'Basic realm="test"'),
            (b"www-authenticate", b"Bearer"),
            (b"set-cookie", b"session=; Max-Age=0; Path=/"),
            (b"set-cookie", b"refresh=; Max-Age=0; Path=/"),
        ]))

    @app.get("/old-representation")
    def old_representation(compressed: bool = False):
        headers = {
            "WWW-Authenticate": "Bearer", "Content-Type": "text/plain", "Content-Length": "0",
            "Cache-Control": "no-store", "Vary": "Authorization",
            "ETag": '"old-body"', "Content-Range": "bytes 0-0/1",
            "Content-Digest": "sha-256=:old-body:", "Transfer-Encoding": "chunked",
        }
        if compressed:
            headers["cOnTeNt-EnCoDiNg"] = "gzip"
        raise HTTPException(401, "Sign in", headers=headers)

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


@pytest.mark.parametrize("header,values", [
    ("www-authenticate", ['Basic realm="test"', "Bearer"]),
    ("set-cookie", ["session=; Max-Age=0; Path=/", "refresh=; Max-Age=0; Path=/"]),
])
def test_problem_keeps_repeated_protocol_headers(client, header, values):
    response = client.get("/multi-auth")
    assert response.status_code == response.json()["status"] == 401
    assert response.headers.get_list(header) == values


@pytest.mark.parametrize("body,status", [('{"count":', 400), ('{"count":"wrong"}', 422)])
def test_malformed_json_is_distinct_from_invalid_values(client, body, status):
    response = client.post("/data", content=body, headers={"Content-Type": "application/json"})
    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["status"] == status


@pytest.mark.parametrize("compressed", [False, True])
def test_problem_recomputes_headers_for_the_replaced_representation(client, compressed):
    response = client.get("/old-representation", params={"compressed": compressed})
    assert response.status_code == response.json()["status"] == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Vary"] == "Authorization"
    assert response.headers["content-type"] == "application/problem+json"
    assert int(response.headers["content-length"]) == len(response.content)
    for header in ("content-encoding", "etag", "content-range", "content-digest", "transfer-encoding"):
        assert header not in response.headers


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
    served = client.get("/openapi.json").json()
    documented = served["paths"]["/data"]["post"]["responses"]["422"]["content"]
    assert documented["application/problem+json"]["schema"] == schema["components"]["schemas"]["Problem"]


@pytest.mark.parametrize("method,path,body,status", [
    ("POST", "/data", '{"count":', 400),
    ("POST", "/data", '{"count":"wrong"}', 422),
    ("GET", "/boom", None, 500),
    ("GET", "/auth", None, 401),
    ("GET", "/limited", None, 429),
])
def test_served_openapi_matches_actual_problem_responses(client, method, path, body, status):
    response = client.request(
        method, path, content=body, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == status
    document = client.get("/openapi.json").json()
    responses = document["paths"][path][method.lower()]["responses"]
    content = responses[str(status)]["content"]
    assert set(content) == {response.headers["content-type"]} == {"application/problem+json"}
    schema = content["application/problem+json"]["schema"]
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    validator.validate(response.json())
    assert not validator.is_valid({"detail": "FastAPI's default error shape"})
    assert not validator.is_valid({
        "type": "https://errors.example.internal/validation-failed",
        "title": "Validation failed", "status": 422, "request_id": "request-1",
        "errors": [{"loc": ["body", 0], "msg": "Invalid"}],
    })
    assert set(responses["200"]["content"]) == {"application/json"}
    assert "HTTPValidationError" not in document["components"]["schemas"]


def test_problem_metadata_composes_with_router_and_operation_contracts():
    problems = load_asset("problem_fastapi")
    app = FastAPI(responses=problems.problem_responses(422, 500))
    problems.install_problem_handlers(app)
    router = APIRouter(responses=problems.problem_responses(401, 429))
    rate_limit = problems.problem_responses(429)
    rate_limit[429]["description"] = "Per-user quota exceeded"
    rate_limit[429]["headers"] = {"Retry-After": {"schema": {"type": "integer"}}}

    @router.get("/limited", responses=rate_limit)
    def limited():
        raise HTTPException(429, "Wait", headers={"Retry-After": "30"})

    app.include_router(router)
    with TestClient(app) as client:
        responses = client.get("/openapi.json").json()["paths"]["/limited"]["get"]["responses"]
        response = client.get("/limited")
    assert set(responses) == {"200", "401", "422", "429", "500"}
    assert responses["429"]["description"] == "Per-user quota exceeded"
    assert responses["429"]["headers"] == rate_limit[429]["headers"]
    assert int(response.headers["Retry-After"]) == 30
    assert response.status_code == 429
    assert "headers" not in responses["401"]
    assert "headers" not in problems.problem_responses(429)[429]
    rate_limit[429]["content"]["application/problem+json"]["schema"]["properties"].clear()
    fresh = problems.problem_responses(429)[429]["content"]["application/problem+json"]["schema"]
    assert "status" in fresh["properties"]


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


@pytest.mark.parametrize("field,accepted,rejected", [
    ("limit", [1, 50, 200], [-1, 0, 201]),
    ("cursor", ["a", "x" * 2048], ["", "x" * 2049]),
    ("idempotency_key", ["a", "x" * 255], ["", "x" * 256]),
    ("title", ["a", "x" * 200], ["", "x" * 201]),
])
def test_starter_input_bounds(field, accepted, rejected):
    """Exercise the example's public bounds with an independent schema validator."""
    schema = yaml.safe_load((ASSETS / "openapi.starter.yaml").read_text(encoding="utf-8"))
    collection = schema["paths"]["/v1/incidents"]
    inputs = {param["name"]: param["schema"] for param in collection["get"]["parameters"]}
    inputs["idempotency_key"] = collection["post"]["parameters"][0]["schema"]
    inputs["title"] = schema["components"]["schemas"]["IncidentCreate"]["properties"]["title"]
    Draft202012Validator.check_schema(inputs[field])
    validator = Draft202012Validator(inputs[field])
    for value in accepted:
        assert validator.is_valid(value), f"{field}: documented boundary rejected"
    for value in rejected:
        assert not validator.is_valid(value), f"{field}: out-of-bounds input accepted"


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


@pytest.mark.parametrize("body_id", [None, ""])
def test_problem_schemas_require_nonempty_request_id(body_id):
    problems = load_asset("problem_fastapi")
    schemas = [
        problems.problem_responses(500)[500]["content"]["application/problem+json"]["schema"],
        yaml.safe_load((ASSETS / "openapi.starter.yaml").read_text())["components"]["schemas"]["Problem"],
    ]
    body = {"type": "https://errors.example.internal/error", "title": "Error", "status": 500}
    if body_id is not None:
        body["request_id"] = body_id
    for schema in schemas:
        assert not Draft202012Validator(schema).is_valid(body)
        assert Draft202012Validator(schema).is_valid({**body, "request_id": "request-1"})


@pytest.mark.parametrize("bundled", [True, False])
@pytest.mark.parametrize("path", ["/ok", "/handled", "/boom"])
def test_project_correlation_owner_keeps_state_logs_and_response_together(caplog, bundled, path):
    problems = load_asset("problem_fastapi")
    seen = []

    class ProjectCorrelation:
        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            if scope["type"] != "http":
                await self.app(scope, receive, send)
                return
            scope.setdefault("state", {})["request_id"] = "project-id"
            # With the bundled owner disabled, the project owns context and response headers too.
            token = problems.request_id_var.set("project-id") if not bundled else None

            async def project_send(message):
                if not bundled and message["type"] == "http.response.start":
                    MutableHeaders(scope=message)["X-Request-ID"] = "project-id"
                await send(message)

            try:
                await self.app(scope, receive, project_send)
            finally:
                if token is not None:
                    problems.request_id_var.reset(token)

    app = FastAPI()
    if bundled:
        problems.install_problem_handlers(app)
    else:
        problems.install_problem_handlers(app, install_request_id=False)
    app.add_middleware(ProjectCorrelation)  # outer: selects the ID before bundled binding

    @app.get("/{kind}")
    async def endpoint(kind: str, request: Request):
        seen.append((request.state.request_id, problems.request_id_var.get()))
        record = logging.makeLogRecord({"msg": "request completed"})
        problems.RequestIdLogFilter().filter(record)
        seen.append(record.request_id)
        if kind == "handled":
            raise HTTPException(409, "Conflict")
        if kind == "boom":
            raise RuntimeError("private detail")
        return JSONResponse({"request_id": request.state.request_id}, headers={"X-Request-ID": "stale-id"})

    with caplog.at_level(logging.ERROR), TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(path, headers={"X-Request-ID": "ingress-id"})
    assert seen == [("project-id", "project-id"), "project-id"]
    assert response.json()["request_id"] == response.headers["X-Request-ID"] == "project-id"
    if path == "/boom":
        assert caplog.records[-1].request_id == "project-id"
    assert problems.request_id_var.get() == "-"


@pytest.mark.parametrize("raises", [False, True])
def test_request_id_context_is_restored_in_same_task(raises):
    problems = load_asset("problem_fastapi")

    async def exercise():
        token = problems.request_id_var.set("outer-context")
        try:
            for request_id in ("request-1", "request-2"):
                async def app(scope, receive, send):
                    assert scope["state"]["request_id"] == problems.request_id_var.get() == request_id
                    if raises:
                        raise RuntimeError("probe")
                    await send({"type": "http.response.start", "status": 200, "headers": []})

                messages = []

                async def send(message):
                    messages.append(message)

                scope = {"type": "http", "headers": [(b"x-request-id", request_id.encode())]}
                middleware = problems.RequestIdMiddleware(app)
                if raises:
                    with pytest.raises(RuntimeError, match="probe"):
                        await middleware(scope, None, send)
                else:
                    await middleware(scope, None, send)
                    assert Headers(scope=messages[0])["X-Request-ID"] == request_id
                assert problems.request_id_var.get() == "outer-context"
        finally:
            problems.request_id_var.reset(token)

    asyncio.run(exercise())


@pytest.mark.parametrize("state_id", ["bad id", "x" * 129, None, 123])
def test_invalid_preselected_request_id_uses_valid_ingress_id(state_id):
    problems = load_asset("problem_fastapi")
    app = FastAPI()
    problems.install_problem_handlers(app)

    class IngressState:
        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            scope.setdefault("state", {})["request_id"] = state_id
            await self.app(scope, receive, send)

    app.add_middleware(IngressState)
    with TestClient(app) as client:
        response = client.get("/missing", headers={"X-Request-ID": "ingress-id"})
    assert response.json()["request_id"] == response.headers["X-Request-ID"] == "ingress-id"


@pytest.mark.parametrize("attribute", ["app", "create_app"])
def test_cors_wrapper_loads_and_exposes_only_allowed_unhandled_errors(monkeypatch, attribute):
    problems = load_asset("problem_fastapi")
    contract = load_asset("test_http_contract")
    api = FastAPI()
    problems.install_problem_handlers(api)

    @api.get("/boom")
    async def boom():
        raise RuntimeError("private detail")

    wrapped = CORSMiddleware(api, allow_origins=["https://allowed.example"])
    module = ModuleType("cors_fixture_app")
    module.app = wrapped
    module.create_app = lambda: wrapped
    monkeypatch.setitem(sys.modules, module.__name__, module)
    contract.APP = f"{module.__name__}:{attribute}"
    loaded = contract.app.__wrapped__()
    assert loaded is wrapped
    assert contract.api.__wrapped__(loaded) is api
    with TestClient(loaded, raise_server_exceptions=False) as client:
        for origin in ("https://allowed.example", "https://denied.example"):
            response = client.get("/boom", headers={"Origin": origin})
            assert response.status_code == 500
            contract.assert_problem(response, 500)
            assert "private detail" not in response.text
            if origin == "https://allowed.example":
                assert response.headers["access-control-allow-origin"] == origin
                assert "Origin" in response.headers["vary"]
            else:
                assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize("broken_handler", [False, True])
def test_boom_probe_precedes_fallback_and_restores_routes(broken_handler):
    problems = load_asset("problem_fastapi")
    contract = load_asset("test_http_contract")
    api = FastAPI()
    if not broken_handler:
        problems.install_problem_handlers(api)

    @api.get("/{path:path}")
    async def fallback(path: str):
        return {"fallback": path}

    wrapped = CORSMiddleware(api, allow_origins=["https://allowed.example"])
    routes = list(api.routes)
    with TestClient(wrapped, raise_server_exceptions=False) as client:
        if broken_handler:
            with pytest.raises(AssertionError, match="application/problem\\+json"):
                contract.test_unexpected_error_is_a_problem(api, client, {})
        else:
            contract.test_unexpected_error_is_a_problem(api, client, {})
        assert api.routes == routes
        assert client.get("/__contract_boom").json() == {"fallback": "__contract_boom"}
