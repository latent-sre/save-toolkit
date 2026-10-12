"""Exercise backend-craft's FastAPI starter end to end, then the house module's protections
that its example service does not reach."""
from __future__ import annotations

import asyncio
import importlib.util
import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from pydantic import BaseModel
from starlette.datastructures import Headers
from starlette.middleware.cors import CORSMiddleware

from testkit import load_path

ASSETS = Path(__file__).resolve().parents[1] / "skills/backend-craft/assets"


def _run(command: list[str], cwd: Path, **env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=600,
                          env={**os.environ, **env})


def _passed(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, f"{result.args}\n{result.stdout[-4000:]}\n{result.stderr[-4000:]}"


def test_fastapi_starter_suite_passes(tmp_path):
    shutil.copytree(ASSETS / "fastapi", tmp_path, dirs_exist_ok=True)
    pytest_cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "addopts="]
    _passed(_run([*pytest_cmd, "test_openapi_document.py"], tmp_path, UPDATE_OPENAPI="1"))
    document = json.loads((tmp_path / "openapi.json").read_text(encoding="utf-8"))
    schemas = document["components"]["schemas"]
    assert {"Problem", "FieldError", "Thing", "ThingPage"} <= schemas.keys()
    assert "HTTPValidationError" not in schemas
    assert document["components"]["securitySchemes"]["bearer"]["scheme"] == "bearer"

    assert importlib.util.find_spec("schemathesis"), "schemathesis must be installed (requirements-test.txt)"
    result = _run([*pytest_cmd, "-p", "schemathesis", "-p", "hypothesispytest"], tmp_path)
    _passed(result)
    assert " passed" in result.stdout and "skipped" not in result.stdout, result.stdout


# The FastAPI house module, exercised directly.

def load_house():
    module = load_path(ASSETS / "fastapi/house.py", "house")
    del sys.modules["house"]
    return module


async def _no_tokens(token: str) -> None:
    return None


class Payload(BaseModel):
    count: int


def house_client(*, trusted_request_id_header: str | None = None, cors: bool = False):
    house = load_house()
    app = house.house_app("Probe", "1.0.0", verify_token=_no_tokens, loopback_only=False,
                          trusted_request_id_header=trusted_request_id_header)

    @app.get("/v1/auth", responses=house.problems(401))
    def auth():
        raise HTTPException(401, "Sign in", headers={"WWW-Authenticate": "Bearer"})

    @app.get("/v1/limited", responses=house.problems(429))
    def limited():
        raise HTTPException(429, "Wait", headers={"Retry-After": "30"})

    @app.get("/v1/multi-auth")
    def multi_auth():
        raise HTTPException(401, "Sign in", headers=Headers(raw=[
            (b"www-authenticate", b'Basic realm="test"'), (b"www-authenticate", b"Bearer"),
            (b"set-cookie", b"session=; Max-Age=0; Path=/"), (b"set-cookie", b"refresh=; Max-Age=0; Path=/"),
        ]))

    @app.get("/v1/old-representation")
    def old_representation(compressed: bool = False):
        headers = {
            "WWW-Authenticate": "Bearer", "Content-Type": "text/plain", "Content-Length": "0",
            "Cache-Control": "no-store", "Vary": "Authorization", "ETag": '"old-body"',
            "Content-Range": "bytes 0-0/1", "Content-Digest": "sha-256=:old-body:",
            "Transfer-Encoding": "chunked",
        }
        if compressed:
            headers["cOnTeNt-EnCoDiNg"] = "gzip"
        raise HTTPException(401, "Sign in", headers=headers)

    @app.post("/v1/data")
    def data(payload: Payload) -> Payload:
        return payload

    @app.get("/v1/boom")
    def boom():
        raise RuntimeError("private diagnostic must not reach the client")

    @app.get("/v1/locked", responses=house.problems(409))
    def locked():
        raise house.ProblemError(409, "https://errors.example.internal/thing-locked", "Thing is locked",
                                 "Another change is in progress.")

    exported = app
    if cors:
        exported = CORSMiddleware(app, allow_origins=["https://console.example.internal"],
                                  allow_methods=["GET", "POST"], expose_headers=["X-Request-ID", "Retry-After"])
    return house, app, TestClient(exported, raise_server_exceptions=False)


@pytest.fixture
def client():
    _, _, test_client = house_client()
    with test_client as c:
        yield c


@pytest.mark.parametrize(("method", "path", "status", "header", "value"), [
    ("GET", "/v1/auth", 401, "WWW-Authenticate", "Bearer"),
    ("GET", "/v1/limited", 429, "Retry-After", "30"),
    ("POST", "/v1/auth", 405, "Allow", "GET"),
])
def test_problem_keeps_protocol_headers(client, method, path, status, header, value):
    response = client.request(method, path)
    assert response.status_code == response.json()["status"] == status
    assert response.headers.get(header) == value
    assert response.headers["content-type"] == "application/problem+json"


@pytest.mark.parametrize(("header", "values"), [
    ("www-authenticate", ['Basic realm="test"', "Bearer"]),
    ("set-cookie", ["session=; Max-Age=0; Path=/", "refresh=; Max-Age=0; Path=/"]),
])
def test_problem_keeps_repeated_protocol_headers(client, header, values):
    assert client.get("/v1/multi-auth").headers.get_list(header) == values


@pytest.mark.parametrize("compressed", [False, True])
def test_problem_recomputes_headers_for_the_replaced_representation(client, compressed):
    response = client.get("/v1/old-representation", params={"compressed": compressed})
    assert response.status_code == response.json()["status"] == 401
    assert response.headers["Cache-Control"] == "no-store" and response.headers["Vary"] == "Authorization"
    assert response.headers["content-type"] == "application/problem+json"
    assert int(response.headers["content-length"]) == len(response.content)
    for header in ("content-encoding", "etag", "content-range", "content-digest", "transfer-encoding"):
        assert header not in response.headers


@pytest.mark.parametrize(("body", "status"), [('{"count":', 400), ('{"count":"wrong"}', 422)])
def test_malformed_json_is_distinct_from_invalid_values(client, body, status):
    response = client.post("/v1/data", content=body, headers={"Content-Type": "application/json"})
    assert response.status_code == response.json()["status"] == status
    assert response.headers["content-type"] == "application/problem+json"


def test_status_only_and_domain_problem_types(client):
    status_only = client.get("/v1/auth").json()
    assert status_only["type"] == "about:blank" and status_only["title"] == "Unauthorized"
    domain = client.get("/v1/locked").json()
    assert domain["type"] == "https://errors.example.internal/thing-locked"
    assert domain["title"] == "Thing is locked" and domain["status"] == 409


@pytest.mark.parametrize(("method", "path", "body", "status"), [
    ("POST", "/v1/data", '{"count":', 400),
    ("POST", "/v1/data", '{"count":"wrong"}', 422),
    ("GET", "/v1/boom", None, 500),
    ("GET", "/v1/auth", None, 401),
    ("GET", "/v1/limited", None, 429),
    ("GET", "/v1/locked", None, 409),
])
def test_document_declares_the_problem_each_error_sends(client, method, path, body, status):
    response = client.request(method, path, content=body, headers={"Content-Type": "application/json"})
    assert response.status_code == status
    document = client.get("/openapi.json").json()
    responses = document["paths"][path][method.lower()]["responses"]
    content = responses[str(status)]["content"]
    assert set(content) == {response.headers["content-type"]} == {"application/problem+json"}
    validator = Draft202012Validator({**content["application/problem+json"]["schema"],
                                      "components": document["components"]})
    validator.validate(response.json())
    assert not validator.is_valid({"detail": "FastAPI's default error shape"})
    assert set(responses["200"]["content"]) == {"application/json"}
    assert "HTTPValidationError" not in document["components"]["schemas"]


def test_operation_ids_are_lower_camel(client):
    document = client.get("/openapi.json").json()
    assert document["paths"]["/v1/old-representation"]["get"]["operationId"] == "oldRepresentation"


def test_unexpected_error_is_redacted_and_correlated(client):
    response = client.get("/v1/boom")
    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
    assert "private diagnostic" not in response.text


def _unhandled_record(caplog, house, app, path):
    with caplog.at_level(logging.ERROR), TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.get(path)
    records = [record for record in caplog.records if record.name == house.logger.name]
    assert len(records) == 1
    return response, records[0]


def test_unhandled_log_keeps_diagnostics_without_exception_values(caplog):
    house, app, _ = house_client()

    @app.get("/v1/failure")
    def failure():
        try:
            raise ValueError("SYNTHETIC_CAUSE_TOKEN")
        except ValueError as cause:
            error = RuntimeError("SYNTHETIC_EXCEPTION_TOKEN")
            error.add_note("SYNTHETIC_NOTE_TOKEN")
            raise error from cause

    response, record = _unhandled_record(caplog, house, app, "/v1/failure")
    assert response.status_code == 500
    rendered = logging.Formatter("%(request_id)s %(message)s").format(record)
    assert "SYNTHETIC_" not in rendered
    assert "RuntimeError" in rendered and "ValueError" in rendered and "GET /v1/failure" in rendered
    assert "test_backend_craft_assets.py" in rendered
    assert record.request_id == response.headers["X-Request-ID"]
    assert record.exc_info is None


def test_unhandled_log_names_grouped_and_context_exceptions(caplog):
    house, app, _ = house_client()

    @app.get("/v1/grouped")
    def grouped():
        try:
            raise KeyError("SYNTHETIC_CONTEXT_TOKEN")
        except KeyError:  # implicit __context__ is the chain under test; `from` would make it a __cause__
            raise ExceptionGroup("SYNTHETIC_GROUP_TOKEN", [  # noqa: B904
                OSError("SYNTHETIC_MEMBER_TOKEN"), LookupError("SYNTHETIC_MEMBER_TOKEN"),
            ])

    _, record = _unhandled_record(caplog, house, app, "/v1/grouped")
    message = record.getMessage()
    assert "SYNTHETIC_" not in message
    for name in ("ExceptionGroup", "OSError", "LookupError", "KeyError"):
        assert name in message


def test_unhandled_log_collapses_recursion(caplog):
    house, app, _ = house_client()

    def recurse(depth):
        return recurse(depth + 1)

    @app.get("/v1/deep")
    def deep():
        return recurse(0)

    _, record = _unhandled_record(caplog, house, app, "/v1/deep")
    message = record.getMessage()
    assert "RecursionError" in message and "repeated" in message
    assert message.count("'recurse')") == 1
    assert len(message) < 10_000


def test_unhandled_log_keeps_its_request_id_beside_a_project_record_factory(caplog):
    house, app, _ = house_client()
    original = logging.getLogRecordFactory()

    def stamping_factory(*args, **kwargs):
        record = original(*args, **kwargs)
        record.request_id = "factory-context-value"
        return record

    logging.setLogRecordFactory(stamping_factory)
    try:
        response, record = _unhandled_record(caplog, house, app, "/v1/boom")
    finally:
        logging.setLogRecordFactory(original)
    assert record.request_id == response.headers["X-Request-ID"] == response.json()["request_id"]


def test_request_id_defaults_to_generated_without_a_trusted_ingress(client):
    response = client.get("/v1/missing", headers={"X-Request-ID": "client-id", "X-Vcap-Request-Id": "client-vcap"})
    request_id = response.headers["X-Request-ID"]
    assert request_id not in {"client-id", "client-vcap"} and UUID(request_id).version == 4
    assert response.json()["request_id"] == request_id


@pytest.mark.parametrize("trusted_header", ["X-Request-ID", "X-Vcap-Request-Id"])
@pytest.mark.parametrize("trusted_id", ["ingress-id", "bad id", "x" * 129, None])
def test_only_the_configured_ingress_header_can_supply_an_id(trusted_header, trusted_id):
    _, _, test_client = house_client(trusted_request_id_header=trusted_header)
    headers = {name: "client-alternative" for name in ("X-Request-ID", "X-Vcap-Request-Id")}
    if trusted_id is None:
        del headers[trusted_header]
    else:
        headers[trusted_header] = trusted_id
    with test_client as c:
        response = c.get("/v1/missing", headers=headers)
    request_id = response.headers["X-Request-ID"]
    if trusted_id == "ingress-id":
        assert request_id == trusted_id
    else:
        assert request_id != "client-alternative" and UUID(request_id).version == 4
    assert response.json()["request_id"] == request_id


@pytest.mark.parametrize("raises", [False, True])
def test_request_id_context_is_restored_in_same_task(raises):
    house = load_house()

    async def exercise():
        token = house.request_id_var.set("outer-context")
        try:
            for request_id in ("request-1", "request-2"):
                async def app(scope, receive, send):  # awaited within this iteration
                    assert scope["state"]["request_id"] == house.request_id_var.get() == request_id  # noqa: B023
                    if raises:
                        raise RuntimeError("probe")
                    await send({"type": "http.response.start", "status": 200, "headers": []})

                messages = []

                async def send(message):
                    messages.append(message)  # noqa: B023 -- awaited within this iteration

                scope = {"type": "http", "headers": [(b"x-request-id", request_id.encode())]}
                middleware = house.RequestIdMiddleware(app, trusted_request_id_header="X-Request-ID")
                if raises:
                    with pytest.raises(RuntimeError, match="probe"):
                        await middleware(scope, None, send)
                else:
                    await middleware(scope, None, send)
                    assert Headers(scope=messages[0])["X-Request-ID"] == request_id
                assert house.request_id_var.get() == "outer-context"
        finally:
            house.request_id_var.reset(token)

    asyncio.run(exercise())


def test_cors_wrapper_exposes_headers_on_unhandled_errors():
    _, _, test_client = house_client(cors=True)
    with test_client as c:
        for origin, allowed in (("https://console.example.internal", True), ("https://denied.example", False)):
            response = c.get("/v1/boom", headers={"Origin": origin})
            assert response.status_code == 500
            assert response.headers["content-type"] == "application/problem+json"
            assert "private diagnostic" not in response.text
            if allowed:
                assert response.headers["access-control-allow-origin"] == origin
                assert "x-request-id" in response.headers["access-control-expose-headers"].lower()
            else:
                assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize(("headers", "status"), [
    ({"Sec-Fetch-Site": "cross-site"}, 403),
    ({"Sec-Fetch-Site": "same-site"}, 403),
    ({"Origin": "https://attacker.example"}, 403),
    ({"Sec-Fetch-Site": "same-origin"}, 200),
    ({"Sec-Fetch-Site": "none"}, 200),
    ({}, 200),
])
def test_cross_site_write_guard(client, headers, status):
    response = client.post("/v1/data", json={"count": 1}, headers=headers)
    assert response.status_code == status
    if status == 403:
        assert response.headers["content-type"] == "application/problem+json"


@pytest.mark.parametrize(("host", "allowed"), [
    ("127.0.0.1:8000", True), ("localhost:8000", True), ("[::1]:8000", True),
    ("attacker.example:8000", False), ("127.0.0.1.attacker.example", False),
])
def test_loopback_host_guard(host, allowed):
    house = load_house()
    app = house.house_app("Probe", "1.0.0", verify_token=_no_tokens, loopback_only=True)

    @app.get("/v1/ping")
    def ping() -> dict:
        return {}

    with TestClient(app) as c:
        response = c.get("/v1/ping", headers={"Host": host})
    assert (response.status_code == 200) is allowed, (host, response.status_code)
    if not allowed:
        assert response.status_code == 421 and response.json()["request_id"]
