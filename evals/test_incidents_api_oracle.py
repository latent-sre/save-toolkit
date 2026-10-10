"""No-model pagination regressions against the shipped fixture and in-process HTTP apps."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from probe_testkit import load_oracle, scenario_file

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "evals/build-scenarios/build-software-engineer-incidents-api.yaml"
ORACLE = ROOT / "evals/oracles/incidents-api/probe_checks.py"


@pytest.fixture
def rows():
    scenario = scenario_file(SCENARIO)
    namespace = {"__name__": "fixture_store"}
    source = scenario["fixture"]["files"]["app/store.py"]
    exec(compile(source, "fixture_store.py", "exec"), namespace)
    return namespace["INCIDENTS"]


@pytest.fixture
def oracle():
    return load_oracle(ORACLE)


def make_app(rows, cap=None, oversized_response=None, mutate=None):
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
        body = {"data": page, "next_cursor": str(end) if end < len(rows) else None}
        return mutate(body, limit, cursor) if mutate else body

    return app


def problem(status):
    return {"type": "about:blank", "title": "Invalid limit", "status": status, "request_id": "request-1"}


def exit_code(check, app):
    """The code one of the oracle's checks exits with against `app`."""
    with TestClient(app) as client, pytest.raises(SystemExit) as result:
        check(client)
    return result.value.code


def assert_verdict(oracle, app, expected):
    assert exit_code(oracle.check_pagination, app) == expected


def test_fixture_exceeds_the_accepted_maximum_page(rows):
    assert len(rows) > 500, "an uncapped response must exceed the oracle's accepted maximum"


def test_uncapped_endpoint_fails(oracle, rows):
    app = make_app(rows)
    with TestClient(app) as client:
        assert len(client.get("/v1/incidents", params={"limit": 100000}).json()["data"]) == len(rows)
    assert_verdict(oracle, app, 10)


@pytest.mark.parametrize("cap", [5, 40, 200, 500])
def test_capped_endpoint_passes(oracle, rows, cap):
    assert_verdict(oracle, make_app(rows, cap=cap), 0)


@pytest.mark.parametrize("request_kind", ["default", "limited", "walk", "oversized", "last"])
def test_malformed_pagination_cursor_fails(oracle, rows, request_kind, capsys):
    def mutate(body, limit, cursor):
        if ((request_kind == "default" and limit == 50)
                or (request_kind == "limited" and limit == 1)
                or (request_kind == "walk" and limit == 40)
                or (request_kind == "oversized" and limit == 100000)) and body["next_cursor"] is not None:
            body["next_cursor"] = int(body["next_cursor"])
        if request_kind == "last" and body["next_cursor"] is None:
            body["next_cursor"] = ""
        return body

    assert_verdict(oracle, make_app(rows, cap=200, mutate=mutate), 10)
    assert "next_cursor" in capsys.readouterr().out


@pytest.mark.parametrize("defect", ["empty", "ignored"])
def test_populated_limit_one_is_honoured(oracle, rows, defect, capsys):
    def mutate(body, limit, cursor):
        if limit == 1:
            body["data"] = [] if defect == "empty" else rows[:2]
        return body

    assert_verdict(oracle, make_app(rows, cap=200, mutate=mutate), 10)
    assert "limit=1" in capsys.readouterr().out


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
    assert_verdict(oracle, make_app(rows, oversized_response=response), 10)


@pytest.mark.parametrize("status", [400, 422, 201, 401, 404, 429, 500, 503])
def test_an_oversized_limit_answered_as_a_problem_fails(oracle, rows, status):
    """House rule (AIP-158): a limit above the maximum is lowered to it, not rejected, so even a
    well-formed problem fails, whether it claims limit validation (400, 422) or an unrelated status."""
    response = (status, problem(status), "application/problem+json")
    assert_verdict(oracle, make_app(rows, oversized_response=response), 10)


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
    assert_verdict(oracle, make_app(rows, oversized_response=response), 10)


def detail_app(status, body, media_type="application/json"):
    """A detail endpoint that answers the hung-vendor case one fixed way."""
    app = FastAPI()

    @app.get("/v1/incidents/{incident_id}")
    def detail(incident_id: str):
        return JSONResponse(body, status_code=status, media_type=media_type)

    return app


PUBLIC = {"id": "inc-0001", "title": "Incident 1", "status": "closed", "service": "search"}


@pytest.mark.parametrize("status,body,media_type,expected", [
    (200, {**PUBLIC, "owner": None}, "application/json", 0),
    (200, {**PUBLIC, "owner": "unavailable"}, "application/json", 0),
    (504, {**problem(504), "title": "Gateway Timeout"}, "application/problem+json", 0),
    (200, {**PUBLIC, "owner": None, "internal_note": "triage scratch"}, "application/json", 10),
    (200, {"owner": None}, "application/json", 10),
    (200, dict(PUBLIC), "application/json", 10),
    (500, {**problem(500), "title": "Internal Server Error"}, "application/problem+json", 10),
])
def test_timeout_accepts_only_a_fast_explicit_answer(oracle, status, body, media_type, expected):
    assert exit_code(oracle.check_timeout, detail_app(status, body, media_type)) == expected
