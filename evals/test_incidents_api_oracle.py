"""No-model pagination regressions against the shipped fixture and in-process HTTP apps."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "evals/build-scenarios/build-software-engineer-incidents-api.yaml"
ORACLE = ROOT / "evals/oracles/incidents-api/probe_checks.py"


@pytest.fixture
def rows():
    scenario = yaml.safe_load(SCENARIO.read_text(encoding="utf-8"))
    namespace = {"__name__": "fixture_store"}
    source = scenario["fixture"]["files"]["app/store.py"]
    exec(compile(source, "fixture_store.py", "exec"), namespace)
    return namespace["INCIDENTS"]


@pytest.fixture
def oracle():
    spec = importlib.util.spec_from_file_location("incidents_api_oracle", ORACLE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_app(rows, cap=None, oversized_response=None):
    """A working cursor endpoint; vary only how it handles an oversized limit."""
    app = FastAPI()

    @app.get("/v1/incidents")
    def incidents(limit: int = 50, cursor: int = 0):
        if limit > 500 and oversized_response is not None:
            status, body, media_type = oversized_response
            return JSONResponse(body, status_code=status, media_type=media_type)
        size = min(limit, cap) if cap is not None else limit
        page = rows[cursor:cursor + size]
        end = cursor + len(page)
        return {"data": page, "next_cursor": str(end) if end < len(rows) else None}

    return app


def problem(status):
    return {"type": "about:blank", "title": "Invalid limit", "status": status}


def assert_verdict(oracle, app, expected):
    with TestClient(app) as client, pytest.raises(SystemExit) as result:
        oracle.check_pagination(client)
    assert result.value.code == expected


def test_fixture_exceeds_the_accepted_maximum_page(rows):
    assert len(rows) > 500, "an uncapped response must exceed the oracle's accepted maximum"


def test_uncapped_endpoint_fails(oracle, rows):
    app = make_app(rows)
    with TestClient(app) as client:
        assert len(client.get("/v1/incidents", params={"limit": 100000}).json()["data"]) == len(rows)
    assert_verdict(oracle, app, 1)


@pytest.mark.parametrize("cap", [5, 40, 200, 500])
def test_capped_endpoint_passes(oracle, rows, cap):
    assert_verdict(oracle, make_app(rows, cap=cap), 0)


@pytest.mark.parametrize("defect", ["empty", "not_a_list", "wrong_prefix", "missing_cursor"])
def test_oversized_success_must_be_a_real_page(oracle, rows, defect):
    body = {"data": rows[:5], "next_cursor": "5"}
    if defect == "empty":
        body["data"] = []
    elif defect == "not_a_list":
        body["data"] = "wrong"
    elif defect == "wrong_prefix":
        body["data"] = rows[5:10]
    else:
        body["next_cursor"] = None
    response = (200, body, "application/json")
    assert_verdict(oracle, make_app(rows, oversized_response=response), 1)


@pytest.mark.parametrize("status", [400, 422])
def test_rejecting_an_oversized_limit_fails_even_as_a_problem(oracle, rows, status):
    """House rule (AIP-158): a limit above the maximum is lowered to it, not rejected."""
    response = (status, problem(status), "application/problem+json")
    assert_verdict(oracle, make_app(rows, oversized_response=response), 1)


@pytest.mark.parametrize("status", [201, 401, 404, 429, 500, 503])
def test_unrelated_status_cannot_pass_as_limit_validation(oracle, rows, status):
    response = (status, problem(status), "application/problem+json")
    assert_verdict(oracle, make_app(rows, oversized_response=response), 1)


@pytest.mark.parametrize("status", [400, 422])
@pytest.mark.parametrize("defect", ["media_type", "missing_status", "wrong_status"])
def test_invalid_problem_response_fails(oracle, rows, status, defect):
    body = problem(status)
    media_type = "application/problem+json"
    if defect == "media_type":
        media_type = "application/json"
    elif defect == "missing_status":
        del body["status"]
    else:
        body["status"] = 500
    response = (status, body, media_type)
    assert_verdict(oracle, make_app(rows, oversized_response=response), 1)


def detail_app(status, body, media_type="application/json"):
    """A detail endpoint that answers the hung-vendor case one fixed way."""
    app = FastAPI()

    @app.get("/v1/incidents/{incident_id}")
    def detail(incident_id: str):
        return JSONResponse(body, status_code=status, media_type=media_type)

    return app


PUBLIC = {"id": "inc-0001", "title": "Incident 1", "status": "closed", "service": "search"}


def timeout_verdict(oracle, app):
    with TestClient(app) as client, pytest.raises(SystemExit) as result:
        oracle.check_timeout(client)
    return result.value.code


@pytest.mark.parametrize("status,body,media_type,expected", [
    (200, {**PUBLIC, "owner": None}, "application/json", 0),
    (200, {**PUBLIC, "owner": "unavailable"}, "application/json", 0),
    (504, {"type": "about:blank", "title": "Gateway Timeout", "status": 504}, "application/problem+json", 0),
    (200, {**PUBLIC, "owner": None, "internal_note": "triage scratch"}, "application/json", 1),
    (200, {"owner": None}, "application/json", 1),
    (200, dict(PUBLIC), "application/json", 1),
    (500, {"type": "about:blank", "title": "Internal Server Error", "status": 500}, "application/problem+json", 1),
])
def test_timeout_accepts_only_a_fast_explicit_answer(oracle, status, body, media_type, expected):
    assert timeout_verdict(oracle, detail_app(status, body, media_type)) == expected
