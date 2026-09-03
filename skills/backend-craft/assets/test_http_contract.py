"""The HTTP contract as a failing test.

Copy this file into the repository's test directory, fill the three constants below, and run it
BEFORE you build: every test must fail first. Then build until it is green, and leave it in the
repository — this is the contract's regression, not a scratch check.

Needs only pytest, fastapi, and httpx, all of which a FastAPI service already has.
"""
from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

APP = "app.main:create_app"      # "module:factory" returning the app, or "module:app"
LIST_PATH = "/v1/incidents"      # one cursor-paginated collection
MISSING_PATH = "/v1/incidents/does-not-exist"   # a 404 on that resource

MAX_SANE_PAGE = 500


@pytest.fixture(scope="module")
def app():
    module_name, _, attribute = APP.partition(":")
    obj = getattr(importlib.import_module(module_name), attribute)
    return obj() if callable(obj) else obj


@pytest.fixture(scope="module")
def client(app):
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def assert_problem(response, status: int) -> None:
    """RFC 9457: one problem+json shape everywhere — media type included."""
    content_type = response.headers.get("content-type", "")
    assert content_type.startswith("application/problem+json"), (
        f"house rule: a {status} must be served as application/problem+json; got {content_type!r}. "
        "A JSON body with the right keys is not enough - the media type is part of the contract."
    )
    body = response.json()
    missing = [key for key in ("type", "title", "status") if key not in body]
    assert not missing, f"house rule: a problem body needs type/title/status; missing {missing}"
    assert body["status"] == status, (
        f"house rule: the problem body's status must match the HTTP status ({body['status']} != {status})"
    )


def test_collection_is_a_cursor_page(client):
    response = client.get(LIST_PATH)
    assert response.status_code == 200, f"{LIST_PATH} must serve the collection; got {response.status_code}"
    body = response.json()
    assert isinstance(body, dict), (
        'house rule: a collection is an envelope, not a bare array - {"data": [...], '
        f'"next_cursor": ...}}; got a {type(body).__name__}'
    )
    assert isinstance(body.get("data"), list), 'house rule: the envelope carries a "data" list'
    assert "next_cursor" in body, 'house rule: the envelope carries "next_cursor", even when null'

    one = client.get(LIST_PATH, params={"limit": 1})
    assert one.status_code == 200, f"limit=1 must be accepted; got {one.status_code}"
    assert len(one.json()["data"]) <= 1, "house rule: limit is honoured, not ignored"

    huge = client.get(LIST_PATH, params={"limit": 100000})
    if huge.status_code < 400:
        assert len(huge.json()["data"]) <= MAX_SANE_PAGE, (
            "house rule: limit is capped server-side - an unbounded page is the outage"
        )


def test_missing_resource_is_a_problem(client):
    response = client.get(MISSING_PATH)
    assert response.status_code == 404, f"{MISSING_PATH} must be a 404; got {response.status_code}"
    assert_problem(response, 404)


def test_invalid_query_is_a_problem(client):
    response = client.get(LIST_PATH, params={"limit": "not-a-number"})
    assert response.status_code in (400, 422), (
        f"house rule: a bad query value is 400 (malformed) or 422 (validation); got {response.status_code}"
    )
    assert_problem(response, response.status_code)


def test_unexpected_error_is_a_problem(app, client):
    path = "/__contract_boom"
    try:
        @app.get(path)
        def boom():
            raise RuntimeError("contract probe")
    except Exception as exc:  # pragma: no cover - an app that refuses a late route
        pytest.skip(f"cannot register a probe route on this app after startup: {exc!r}")

    response = client.get(path)
    assert response.status_code == 500, f"an unhandled error must be a 500; got {response.status_code}"
    assert_problem(response, 500)
