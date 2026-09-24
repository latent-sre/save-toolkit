"""Starter checks for a compatible FastAPI collection and problem-response contract.

Adapt paths and the `auth_headers` fixture to the project; preserve existing passing contracts.
Reproduce the changed behavior before fixing it. Add a project-owned maximum-limit test with
more seeded records than the chosen cap: a sparse collection cannot prove a cap is enforced.

Needs only pytest, fastapi, and httpx, all of which a FastAPI service already has.
"""
from __future__ import annotations

import importlib
import inspect

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

APP = "app.main:create_app"      # zero-argument factory or exported ASGI app, including middleware
LIST_PATH = "/v1/incidents"      # one cursor-paginated collection
UNKNOWN_PATH = "/v1/no-such-route"   # matches no route: the framework's own 404
MISSING_ITEM_PATH = None   # with an item route: a well-formed id that does not exist; malformed is 422

@pytest.fixture(scope="module")
def app():
    module_name, _, attribute = APP.partition(":")
    obj = getattr(importlib.import_module(module_name), attribute)
    try:
        inspect.signature(obj).bind()
    except TypeError:  # an ASGI callable requires scope/receive/send; it is not a factory
        return obj
    return obj()


@pytest.fixture(scope="module")
def api(app):
    """Locate routing beneath standard ASGI wrappers; client still uses the complete stack."""
    inner = app
    seen = set()
    while not isinstance(inner, FastAPI):
        assert inner is not None and id(inner) not in seen, "adapt api fixture to expose the FastAPI router"
        seen.add(id(inner))
        inner = getattr(inner, "app", None)
    return inner


@pytest.fixture(scope="module")
def client(app):
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def auth_headers():
    """Bearer token for the protected collection.

    The OpenAPI starter applies `bearerAuth` to every route except health and readiness, so these
    requests need one. Return {"Authorization": f"Bearer {token}"} with a token the test issues or
    mints for a test principal — never a production credential, and never `security: []` on the
    collection to make the tests pass. Return {} only for a collection that is genuinely
    unauthenticated.
    """
    return {}


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
    assert body.get("request_id"), (
        "house rule: a problem body carries request_id (Gorouter's X-Vcap-Request-Id on PCF, else a "
        "validated ingress id or a generated one) so the caller's error joins the log line"
    )


def test_collection_is_a_cursor_page(client, auth_headers):
    response = client.get(LIST_PATH, headers=auth_headers)
    assert response.status_code == 200, f"{LIST_PATH} must serve the collection; got {response.status_code}"
    body = response.json()
    assert isinstance(body, dict), (
        'house rule: a collection is an envelope, not a bare array - {"data": [...], '
        f'"next_cursor": ...}}; got a {type(body).__name__}'
    )
    assert isinstance(body.get("data"), list), 'house rule: the envelope carries a "data" list'
    assert "next_cursor" in body, 'house rule: the envelope carries "next_cursor", even when null'

    one = client.get(LIST_PATH, params={"limit": 1}, headers=auth_headers)
    assert one.status_code == 200, f"limit=1 must be accepted; got {one.status_code}"
    assert len(one.json()["data"]) <= 1, "house rule: limit is honoured, not ignored"

def test_unknown_path_is_a_problem(client, auth_headers):
    response = client.get(UNKNOWN_PATH, headers=auth_headers)
    assert response.status_code == 404, (
        f"{UNKNOWN_PATH} must be a 404; got {response.status_code} (a SPA fallback swallowing API paths?)"
    )
    assert_problem(response, 404)


def test_missing_item_is_a_problem(api, client, auth_headers):
    items = [r.path for r in api.routes if getattr(r, "path", "").startswith(LIST_PATH + "/{")]
    if MISSING_ITEM_PATH is None:
        assert not items, f"{items} exist: set MISSING_ITEM_PATH to a well-formed id that does not exist"
        pytest.skip("this contract has no item route")
    response = client.get(MISSING_ITEM_PATH, headers=auth_headers)
    assert response.status_code == 404, f"{MISSING_ITEM_PATH} must be a 404; got {response.status_code}"
    assert_problem(response, 404)


def test_invalid_query_is_a_problem(client, auth_headers):
    response = client.get(LIST_PATH, params={"limit": "not-a-number"}, headers=auth_headers)
    assert response.status_code in (400, 422), (
        f"house rule: a bad query value is 400 (malformed) or 422 (validation); got {response.status_code}"
    )
    assert_problem(response, response.status_code)


def test_unexpected_error_is_a_problem(api, client, auth_headers):
    path = "/__contract_boom"
    reached = False

    @api.get(path, include_in_schema=False)
    async def boom():
        nonlocal reached
        reached = True
        raise RuntimeError("contract probe")

    # Register on the real router ahead of mounts/fallbacks, retaining the complete middleware stack.
    probe = api.router.routes.pop()
    api.router.routes.insert(0, probe)
    try:
        response = client.get(path, headers=auth_headers)
        assert reached, "the request did not reach the failing route; adapt the probe's auth/path"
        assert response.status_code == 500, f"an unhandled error must be a 500; got {response.status_code}"
        assert_problem(response, 500)
    finally:
        api.router.routes.remove(probe)
