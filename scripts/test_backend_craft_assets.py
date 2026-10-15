"""Exercise reusable FastAPI components and contract checks against an independent service."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import textwrap
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


@pytest.mark.parametrize("files, test_file", [
    (("house.py", "contract_checks.py"), "test_http_core.py"),
    (("house.py", "contract_checks.py", "auth.py"), "test_auth.py"),
])
def test_fastapi_components_run_independently(tmp_path, files, test_file):
    for name in (*files, test_file):
        shutil.copy2(ASSETS / "fastapi" / name, tmp_path / name)
    _passed(_run([sys.executable, "-m", "pytest", "-q", "-o", "addopts=", test_file], tmp_path))


def test_fastapi_contract_checks_run_against_cookie_service_without_examples(tmp_path):
    for name in ("house.py", "contract_checks.py", "test_openapi_document.py", "test_schemathesis.py"):
        shutil.copy2(ASSETS / "fastapi" / name, tmp_path / name)
    # Deliberately no auth.py or bearer fixtures. Only this ordinary setup
    # module changes; the shipped document/schema checks run unmodified against another service.
    (tmp_path / "contract_app.py").write_text(textwrap.dedent('''\
        from contextlib import asynccontextmanager
        from pathlib import Path
        from typing import Annotated

        from fastapi import Depends, HTTPException, Security
        from fastapi.security import APIKeyCookie
        from house import house_app, problems
        from pydantic import BaseModel

        AUTH_SCHEME = "corporateSession"
        AUTH_ERROR_STATUSES = {401, 503}
        TEST_HEADERS = {"Cookie": "corp_session=local-alice"}
        PUBLIC_OPERATIONS = set()
        cookie = APIKeyCookie(name="corp_session", scheme_name=AUTH_SCHEME, auto_error=False)

        def identity(value: Annotated[str | None, Security(cookie)]):
            if value == "outage":
                raise HTTPException(503, "Session verifier unavailable")
            if value != "local-alice":
                raise HTTPException(401, "Sign in")
            return "alice"

        class Note(BaseModel):
            id: int
            text: str

        @asynccontextmanager
        async def lifespan(app):
            app.state.notes = {1: ("alice", Note(id=1, text="Local fixture"))}
            with Path("lifecycle.log").open("a") as log:
                log.write("start\\n")
            try:
                yield
            finally:
                del app.state.notes
                with Path("lifecycle.log").open("a") as log:
                    log.write("stop\\n")

        def make_app():
            app = house_app("Session notes", "1.0.0", loopback_only=False, lifespan=lifespan, openapi_url=None)

            @app.get("/v1/notes/{note_id}", responses=problems(401, 404, 503))
            def get_note(note_id: int, owner: Annotated[str, Depends(identity)]) -> Note:
                note = app.state.notes.get(note_id)  # fails if the check skipped lifespan
                if note is None or note[0] != owner:
                    raise HTTPException(404, "Not found")
                return note[1]

            return app
        '''), encoding="utf-8")
    (tmp_path / "test_notes.py").write_text(textwrap.dedent('''\
        from contract_app import TEST_HEADERS, make_app
        from contract_checks import assert_problem
        from fastapi.testclient import TestClient

        def test_notes_identity_and_problems():
            with TestClient(make_app()) as client:
                assert_problem(client.get("/v1/notes/1"), 401)
                assert_problem(client.get("/v1/notes/1", headers={"Cookie": "corp_session=invalid"}), 401)
                assert_problem(client.get("/v1/notes/1", headers={"Cookie": "corp_session=outage"}), 503)
                assert_problem(client.get("/v1/notes/2", headers=TEST_HEADERS), 404)
                assert client.get("/v1/notes/1", headers=TEST_HEADERS).json() == {
                    "id": 1, "text": "Local fixture",
                }
        '''), encoding="utf-8")
    pytest_cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "addopts="]
    _passed(_run([*pytest_cmd, "test_openapi_document.py"], tmp_path, UPDATE_OPENAPI="1"))
    result = _run([*pytest_cmd, "-p", "schemathesis", "-p", "hypothesispytest"], tmp_path)
    _passed(result)
    assert "skipped" not in result.stdout, result.stdout
    lifecycle = (tmp_path / "lifecycle.log").read_text().splitlines()
    assert lifecycle and lifecycle.count("start") == lifecycle.count("stop")

    document_path = tmp_path / "openapi.json"
    document = json.loads(document_path.read_text(encoding="utf-8"))
    assert document["components"]["securitySchemes"] == {
        "corporateSession": {"type": "apiKey", "in": "cookie", "name": "corp_session"}
    }
    document["info"]["version"] = "drift"
    document_path.write_text(json.dumps(document), encoding="utf-8")
    drift = _run([*pytest_cmd, "test_openapi_document.py::test_document_matches_the_code"], tmp_path)
    assert drift.returncode == 1 and "openapi.json differs" in drift.stdout, drift.stdout


def _cookie_document():
    return {
        "openapi": "3.1.0", "components": {"securitySchemes": {
            "corporateSession": {"type": "apiKey", "in": "cookie", "name": "corp_session"},
        }},
        "security": [{"corporateSession": []}],
        "paths": {"/v1/notes": {"parameters": [], "get": {
            "operationId": "listNotes", "responses": {"401": {"content": {"application/problem+json": {}}}},
        }}},
    }


@pytest.mark.parametrize(("scheme", "headers", "configured"), [
    ("corporateSession", {}, False),
    ("corporateSession", {"": "local-alice"}, False),
    ("corporateSession", {"Cookie": ""}, False),
    ("corporateSession", {"Cookie": " "}, False),
    (None, {}, True),
])
def test_schema_checks_require_configured_identity_for_protected_service(tmp_path, scheme, headers, configured):
    shutil.copy2(ASSETS / "fastapi/test_schemathesis.py", tmp_path / "test_schemathesis.py")
    (tmp_path / "contract_app.py").write_text(textwrap.dedent(f'''\
        from fastapi import FastAPI

        AUTH_SCHEME = {scheme!r}
        TEST_HEADERS = {headers!r}
        PUBLIC_OPERATIONS = {{"status"}}

        def make_app():
            app = FastAPI()

            @app.get("/v1/status")
            def status() -> str:
                return "ready"

            return app
        '''), encoding="utf-8")
    result = _run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-o", "addopts=",
                   "-p", "schemathesis", "-p", "hypothesispytest"], tmp_path)
    if configured:
        _passed(result)
    else:
        assert result.returncode != 0 and "Configure nonempty test identity" in result.stdout, result.stdout


def test_reusable_document_checks_accept_inherited_cookie_security_and_explicit_public_operation():
    checks = load_path(ASSETS / "fastapi/contract_checks.py", "contract_checks")
    document = _cookie_document()
    checks.assert_document_rules(document, auth_scheme="corporateSession", public_operations=set())
    document["paths"]["/v1/notes"]["get"]["security"] = []
    document["paths"]["/v1/notes"]["get"]["responses"] = {"200": {"description": "OK"}}
    checks.assert_document_rules(document, auth_scheme="corporateSession", public_operations={"listNotes"})


@pytest.mark.parametrize("paths", [{}, {"/v1/notes": {"parameters": [], "summary": "Notes"}}])
def test_reusable_document_checks_reject_no_http_operations(paths):
    checks = load_path(ASSETS / "fastapi/contract_checks.py", "contract_checks")
    document = _cookie_document()
    document["paths"] = paths
    with pytest.raises(AssertionError, match="no HTTP operations"):
        checks.assert_document_rules(document, auth_scheme="corporateSession", public_operations=set())


@pytest.mark.parametrize("security", [None, [{"corporateSession": []}], [{"corporateSession": []}, {}], [{}]])
def test_public_document_operation_cannot_retain_security(security):
    checks = load_path(ASSETS / "fastapi/contract_checks.py", "contract_checks")
    document = _cookie_document()
    if security is not None:
        document["paths"]["/v1/notes"]["get"]["security"] = security
    with pytest.raises(AssertionError, match=r"public operation.*security"):
        checks.assert_document_rules(document, auth_scheme="corporateSession", public_operations={"listNotes"})


def test_protected_document_operation_requires_unauthorized_response():
    checks = load_path(ASSETS / "fastapi/contract_checks.py", "contract_checks")
    document = _cookie_document()
    document["paths"]["/v1/notes"]["get"]["responses"] = {"200": {"description": "OK"}}
    with pytest.raises(AssertionError, match="declare authentication failure 401"):
        checks.assert_document_rules(document, auth_scheme="corporateSession", public_operations=set())


def test_configured_verifier_outage_must_be_documented_as_a_problem():
    checks = load_path(ASSETS / "fastapi/contract_checks.py", "contract_checks")
    document = _cookie_document()
    kwargs = {"auth_scheme": "corporateSession", "public_operations": set(), "auth_error_statuses": {401, 503}}
    with pytest.raises(AssertionError, match="declare authentication failure 503"):
        checks.assert_document_rules(document, **kwargs)
    responses = document["paths"]["/v1/notes"]["get"]["responses"]
    responses["503"] = {"content": {"application/json": {}}}
    with pytest.raises(AssertionError, match="503 must be application/problem\\+json"):
        checks.assert_document_rules(document, **kwargs)
    responses["503"]["content"] = {"application/problem+json": {}}
    checks.assert_document_rules(document, **kwargs)
    document["paths"]["/v1/notes"]["get"]["security"] = []
    checks.assert_document_rules(document, **{**kwargs, "auth_scheme": None, "public_operations": {"listNotes"}})


@pytest.mark.parametrize(("protected", "fault"), [(True, ""), (False, ""),
                                                 (True, "requires-identity"), (True, "requires-permission")])
def test_schema_public_operations_run_without_identity(tmp_path, protected, fault):
    for name in ("house.py", "test_schemathesis.py"):
        shutil.copy2(ASSETS / "fastapi" / name, tmp_path / name)
    (tmp_path / "contract_app.py").write_text(textwrap.dedent(f'''\
        from typing import Annotated
        from fastapi import HTTPException, Request, Security
        from fastapi.security import APIKeyCookie
        from house import house_app, problems

        AUTH_SCHEME = {"corporateSession" if protected else None!r}
        TEST_HEADERS = {({"Cookie": "corp_session=local-alice"} if protected else {})!r}
        PUBLIC_OPERATIONS = {{"publicStatus"}}
        cookie = APIKeyCookie(name="corp_session", scheme_name="corporateSession", auto_error=False)

        def make_app():
            app = house_app("Public probe", "1.0.0", loopback_only=False)

            @app.get("/v1/status", operation_id="publicStatus", responses=problems(401, 403))
            def status(request: Request) -> str:
                if request.headers.get("Cookie") or request.headers.get("Authorization"):
                    raise HTTPException(403, "Public probe must run without identity headers")
                if {fault!r}:
                    raise HTTPException(401 if {fault!r} == "requires-identity" else 403, "Sign in")
                return "ready"

            if AUTH_SCHEME is not None:
                @app.get("/v1/notes", responses=problems(401))
                def notes(value: Annotated[str | None, Security(cookie)]) -> str:
                    if value != "local-alice":
                        raise HTTPException(401, "Sign in")
                    return "private"

            return app
        '''), encoding="utf-8")
    result = _run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "addopts=",
                   "-p", "schemathesis", "-p", "hypothesispytest"], tmp_path)
    if fault:
        assert result.returncode == 1 and "public operation requires authentication" in result.stdout, result.stdout
    else:
        _passed(result)
        assert "skipped" not in result.stdout, result.stdout


@pytest.mark.parametrize("mutation", ["missing", "override", "anonymous", "undeclared", "wrong_scheme", "error_type"])
def test_reusable_document_checks_reject_broken_contract(mutation):
    checks = load_path(ASSETS / "fastapi/contract_checks.py", "contract_checks")
    document = _cookie_document()
    operation = document["paths"]["/v1/notes"]["get"]
    if mutation == "missing":
        del document["security"]
    elif mutation == "override":
        operation["security"] = []
    elif mutation == "anonymous":
        operation["security"] = [{"corporateSession": []}, {}]
    elif mutation == "undeclared":
        operation["security"] = [{"corporateSession": [], "undefinedIdentity": []}]
    elif mutation == "wrong_scheme":
        document["components"]["securitySchemes"]["bearer"] = {"type": "http", "scheme": "bearer"}
        operation["security"] = [{"bearer": []}]
    else:
        operation["responses"]["401"]["content"] = {"application/json": {}}
    with pytest.raises(AssertionError):
        checks.assert_document_rules(document, auth_scheme="corporateSession", public_operations=set())


@pytest.mark.parametrize("mutation", ["request_id", "status", "error_type"])
def test_reusable_problem_check_rejects_broken_response(mutation):
    checks = load_path(ASSETS / "fastapi/contract_checks.py", "contract_checks")
    _, _, test_client = house_client()
    with test_client as c:
        response = c.get("/v1/auth")
    checks.assert_problem(response, 401)
    if mutation == "request_id":
        response.headers["x-request-id"] = "different"
    elif mutation == "status":
        response.status_code = 503
    else:
        response.headers["content-type"] = "application/json"
    with pytest.raises(AssertionError):
        checks.assert_problem(response, 401)


# The FastAPI house module, exercised directly.

def load_house():
    module = load_path(ASSETS / "fastapi/house.py", "house")
    del sys.modules["house"]
    return module


class Payload(BaseModel):
    count: int


def house_client(*, trusted_request_id_header: str | None = None, cors: bool = False):
    house = load_house()
    app = house.house_app("Probe", "1.0.0", loopback_only=False,
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
    app = house.house_app("Probe", "1.0.0", loopback_only=True)

    @app.get("/v1/ping")
    def ping() -> dict:
        return {}

    with TestClient(app) as c:
        response = c.get("/v1/ping", headers={"Host": host})
    assert (response.status_code == 200) is allowed, (host, response.status_code)
    if not allowed:
        assert response.status_code == 421 and response.json()["request_id"]
