"""Calibrate the three independently injected backend problem-response predicates."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from httpx import Response
from probe_testkit import load_oracle, scenario_file

ROOT = Path(__file__).resolve().parents[1]
ORACLES = ("incidents-api", "incident-writes", "pager-webhook")


@pytest.fixture(params=ORACLES)
def oracle(request):
    return load_oracle(ROOT / "evals/oracles" / request.param / "probe_checks.py")


@pytest.fixture
def problem():
    return {"type": "about:blank", "title": "Invalid input", "status": 422, "request_id": "request-1"}


def verdict(oracle, body, media_type="application/problem+json"):
    return oracle.is_problem(Response(422, json=body, headers={"Content-Type": media_type}))


@pytest.mark.parametrize("media_type", [
    "application/problem+json", "Application/Problem+Json; charset=utf-8",
])
@pytest.mark.parametrize("with_extensions", [False, True])
def test_problem_oracle_accepts_valid_contract(oracle, problem, media_type, with_extensions):
    if with_extensions:
        problem.update(detail="Invalid count", instance="/v1/incidents",
                       errors=[{"loc": ["body", "count"], "msg": "Must be an integer"}],
                       project_extension={"code": "invalid-count"})
    passed, reason = verdict(oracle, problem, media_type)
    assert passed, reason


def test_problem_oracle_accepts_integral_json_number(oracle, problem):
    problem["status"] = 422.0  # JSON Schema's integer type permits an integral number.
    passed, reason = verdict(oracle, problem)
    assert passed, reason


@pytest.mark.parametrize("field", ["type", "title", "status", "request_id"])
def test_problem_oracle_rejects_missing_required_field(oracle, problem, field):
    del problem[field]
    passed, reason = verdict(oracle, problem)
    assert not passed, f"accepted missing {field}: {reason}"
    assert field in reason


@pytest.mark.parametrize("field,value", [
    ("type", []), ("type", None), ("title", False), ("title", {}),
    ("status", "422"), ("status", True), ("status", 500),
    ("request_id", None), ("request_id", []), ("request_id", ""),
    ("detail", []), ("instance", {}), ("errors", {}), ("errors", [None]),
    ("errors", [{"loc": [0], "msg": "Invalid"}]),
    ("errors", [{"loc": [], "msg": False}]),
    ("errors", [{"msg": "Missing loc"}]), ("errors", [{"loc": []}]),
])
def test_problem_oracle_rejects_malformed_field(oracle, problem, field, value):
    problem[field] = value
    passed, reason = verdict(oracle, problem)
    assert not passed, f"accepted malformed {field}: {reason}"
    assert field in reason


@pytest.mark.parametrize("media_type", [
    "application/json", "application/problem+json-extra", "",
])
def test_problem_oracle_rejects_wrong_media_type(oracle, problem, media_type):
    passed, reason = verdict(oracle, problem, media_type)
    assert not passed
    assert "content-type" in reason


@pytest.mark.parametrize("body", [[], ["type", "title", "status", "request_id"], "problem", 422])
def test_problem_oracle_rejects_non_object_body(oracle, body):
    passed, reason = verdict(oracle, body)
    assert not passed
    assert "object" in reason


@pytest.mark.parametrize("content", [b"null", b"not-json"])
def test_problem_oracle_rejects_null_or_non_json_body(oracle, content):
    passed, reason = oracle.is_problem(Response(
        422, content=content, headers={"Content-Type": "application/problem+json"},
    ))
    assert not passed
    assert "object" in reason or "JSON" in reason


def test_problem_oracle_accepts_its_shipped_error_handler(oracle):
    name = Path(oracle.__file__).parent.name
    scenario = ROOT / "evals/build-scenarios" / f"build-software-engineer-{name}.yaml"
    source = scenario_file(scenario)["fixture"]["files"]["app/errors.py"]
    namespace = {}
    exec(compile(source, f"{name}/app/errors.py", "exec"), namespace)
    app = FastAPI()
    namespace["install_problem_handlers"](app)

    @app.get("/invalid")
    def invalid():
        raise HTTPException(422, "Invalid input")

    with TestClient(app) as client:
        passed, reason = oracle.is_problem(client.get("/invalid"))
    assert passed, reason
