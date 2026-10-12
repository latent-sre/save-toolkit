"""House contract tests: they drive the real app, so a change that breaks the error, request-ID,
page or authentication contract fails here. Adapt the import, the seed and the requests to the
service's resource; keep every assertion."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from house import Principal
from main import MAX_PAGE_SIZE, Settings, Thing, ThingStore, create_app, load_settings

TOKEN = "test-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
LOOPBACK = Settings(host="127.0.0.1", port=8000, trusted_request_id_header=None)


async def verify(token: str) -> Principal | None:
    return Principal("tester", frozenset({"team:sre"})) if token == TOKEN else None


def seeded(n: int) -> ThingStore:
    things = [Thing(id=f"thing-{i:04d}", name=f"Thing {i}", team="sre") for i in range(1, n + 1)]
    return ThingStore([*things, Thing(id="thing-other", name="Other", team="payments")])


def client_for(store: ThingStore, settings: Settings = LOOPBACK, verify_token=verify) -> TestClient:
    app = create_app(settings, verify_token, store)
    return TestClient(app, base_url="http://127.0.0.1:8000", raise_server_exceptions=False)


@pytest.fixture
def client():
    with client_for(seeded(3)) as c:  # the with block runs the lifespan
        yield c


def assert_problem(response, status: int) -> dict:
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert {"type", "title", "status", "request_id"} <= body.keys(), body
    assert body["status"] == status
    assert body["request_id"] and body["request_id"] == response.headers["x-request-id"]
    return body


@pytest.mark.parametrize(
    ("method", "path", "headers", "status"),
    [
        ("GET", "/v1/things", {}, 401),
        ("GET", "/v1/things", {"Authorization": "Bearer wrong"}, 401),
        ("GET", "/v1/things/missing", AUTH, 404),
        ("GET", "/v1/no-such-route", AUTH, 404),
        ("GET", "/v1/things?limit=0", AUTH, 422),
        ("GET", "/v1/things?cursor=%21%21", AUTH, 422),
        ("GET", "/v1/things?cursor=", AUTH, 422),
        ("DELETE", "/v1/things", AUTH, 405),
    ],
)
def test_errors_are_problems(client, method, path, headers, status):
    response = client.request(method, path, headers=headers)
    assert_problem(response, status)
    if status == 405:
        assert "GET" in response.headers["allow"]


def test_unauthorized_names_the_scheme(client):
    assert client.get("/v1/things").headers["www-authenticate"] == "Bearer"


def test_verifier_outage_is_not_an_auth_failure():
    async def down(token: str) -> Principal | None:
        raise ConnectionError("identity provider unreachable")

    with client_for(seeded(1), verify_token=down) as c:
        assert_problem(c.get("/v1/things", headers=AUTH), 503)


def test_validation_errors_locate_the_input(client):
    body = assert_problem(client.get("/v1/things?limit=0", headers=AUTH), 422)
    assert body["errors"], body
    first = body["errors"][0]
    assert first["loc"] == ["query", "limit"] and first["msg"]
    assert "input" not in first and "value" not in first  # the submitted value is never echoed


def test_every_response_carries_a_request_id(client):
    for path in ("/health/live", "/v1/things", "/v1/nope"):
        assert client.get(path).headers.get("x-request-id")
    # A client-sent ID is not trusted unless the ingress header is configured.
    assert client.get("/health/live", headers={"X-Request-ID": "spoofed"}).headers["x-request-id"] != "spoofed"


def test_cursor_pages_walk_the_collection_once():
    with client_for(seeded(501)) as c:
        seen: list[str] = []
        url = "/v1/things?limit=1000"  # above the maximum: lowered, not rejected
        for _ in range(10):
            response = c.get(url, headers=AUTH)
            assert response.status_code == 200, response.text
            body = response.json()
            assert isinstance(body["data"], list) and len(body["data"]) <= MAX_PAGE_SIZE
            seen += [item["id"] for item in body["data"]]
            assert "next_cursor" in body, "next_cursor must be present, and null on the last page"
            if body["next_cursor"] is None:
                break
            url = f"/v1/things?limit=1000&cursor={body['next_cursor']}"
        else:
            pytest.fail("pagination did not end")
    assert len(seen) == len(set(seen)) == 501
    assert "thing-other" not in seen, "listed a thing outside the caller's teams"


def test_empty_page_is_an_empty_array():
    with client_for(ThingStore()) as c:
        assert c.get("/v1/things", headers=AUTH).json() == {"data": [], "next_cursor": None}


def test_object_authorization(client):
    assert client.get("/v1/things/thing-0001", headers=AUTH).status_code == 200
    assert_problem(client.get("/v1/things/thing-other", headers=AUTH), 404)


def test_loopback_service_refuses_foreign_hosts(client):
    response = client.get("/v1/things", headers={**AUTH, "Host": "attacker.example:8000"})
    assert_problem(response, 421)


def test_cross_site_writes_are_refused(client):
    response = client.post("/v1/things", headers={**AUTH, "Sec-Fetch-Site": "cross-site"})
    assert_problem(response, 403)


def test_settings_come_from_the_environment():
    assert load_settings({}).host == "127.0.0.1"
    assert load_settings({"PORT": "8081"}).port == 8081
    with pytest.raises(ValueError):
        load_settings({"PORT": "eighty"})
