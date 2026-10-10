"""Probe-owned oracle for the incidents API. Usage: python probe_checks.py <check>."""
import json
import os
import sys
from pathlib import Path
import importlib
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from oracle_protocol import candidate_call
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


# Keep the scenario seed larger than the accepted page cap so an uncapped API cannot pass.
FIXTURE_COUNT = 501
MAX_SANE_PAGE = 500


class _Vendor(BaseHTTPRequestHandler):
    delay = 0.0

    def do_GET(self):
        if self.delay:
            time.sleep(self.delay)
        body = json.dumps({"owner": "alice"}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def start_vendor(delay):
    handler = type("Handler", (_Vendor,), {"delay": delay})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return "http://127.0.0.1:%d" % server.server_address[1]


def make_client(delay):
    os.environ["PAGING_BASE_URL"] = start_vendor(delay)
    from fastapi.testclient import TestClient
    try:
        create_app = candidate_call(importlib.import_module, "app.main").create_app
        app = candidate_call(create_app)
    except (Exception, SystemExit) as exc:
        fail("candidate app could not start: %r" % exc)
    client = TestClient(app, raise_server_exceptions=False)
    candidate_call(client.__enter__)
    return client


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(10)


def response_json(response):
    try:
        body = response.json()
    except ValueError as exc:
        fail("candidate response is not JSON: %s" % exc)
    if not isinstance(body, dict):
        fail("candidate response must be a JSON object")
    return body


def ok(msg):
    print("OK: " + msg)
    sys.exit(0)


def is_problem(resp):
    ctype = resp.headers.get("content-type", "")
    if ctype.partition(";")[0].strip().lower() != "application/problem+json":
        return False, "content-type %r" % ctype
    try:
        body = resp.json()
    except ValueError:
        return False, "body is not JSON"
    if not isinstance(body, dict):
        return False, "problem body must be an object"
    for key in ("type", "title", "request_id"):
        if not isinstance(body.get(key), str):
            return False, "problem %s must be a string" % key
    if not body["request_id"]:
        return False, "problem request_id must be nonempty"
    status = body.get("status")
    if isinstance(status, bool) or not isinstance(status, (int, float)) or status != resp.status_code:
        return False, "problem status %r != HTTP status %d" % (status, resp.status_code)
    for key in ("detail", "instance"):
        if key in body and not isinstance(body[key], str):
            return False, "problem %s must be a string" % key
    if "errors" in body:
        if not isinstance(body["errors"], list):
            return False, "problem errors must be an array"
        for error in body["errors"]:
            if (not isinstance(error, dict) or not isinstance(error.get("loc"), list)
                    or not all(isinstance(part, str) for part in error["loc"])
                    or not isinstance(error.get("msg"), str)):
                return False, "problem errors need a string-list loc and string msg"
    return True, "problem+json carrying type/title/status/request_id"


def cursor_page(resp):
    body = response_json(resp)
    if not isinstance(body, dict) or not isinstance(body.get("data"), list):
        fail("list body must be an object with a data array")
    if any(not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"] for row in body["data"]):
        fail("list entries must be objects with nonempty string incident ids")
    if "next_cursor" not in body:
        fail("list body is missing next_cursor")
    cursor = body["next_cursor"]
    if cursor is not None and (not isinstance(cursor, str) or not cursor):
        fail("next_cursor must be null or a nonempty string")
    return body


def check_pagination(client):
    r = candidate_call(client.get, "/v1/incidents")
    if r.status_code != 200:
        fail("GET /v1/incidents -> %d" % r.status_code)
    body = cursor_page(r)
    if not 0 < len(body["data"]) < FIXTURE_COUNT:
        fail("default page must return a nonempty proper subset of the seeded incidents")
    r = candidate_call(client.get, "/v1/incidents", params={"limit": 1})
    if r.status_code != 200:
        fail("limit=1 -> %d" % r.status_code)
    one = cursor_page(r)
    if len(one["data"]) != 1 or one["data"][0]["id"] != body["data"][0]["id"]:
        fail("limit=1 must return exactly the first seeded incident")
    seen = []
    cursor = None
    pages = 0
    while True:
        params = {"limit": 40}
        if cursor:
            params["cursor"] = cursor
        r = candidate_call(client.get, "/v1/incidents", params=params)
        if r.status_code != 200:
            fail("page %d -> %d" % (pages, r.status_code))
        page = cursor_page(r)
        if len(page["data"]) > 40:
            fail("page exceeded limit: %d" % len(page["data"]))
        seen.extend(item["id"] for item in page["data"])
        pages += 1
        cursor = page["next_cursor"]
        if cursor is None:
            break
        if pages > FIXTURE_COUNT:
            fail("cursor never terminated")
    if len(seen) != FIXTURE_COUNT or len(set(seen)) != FIXTURE_COUNT:
        fail("walked %d items, %d unique; expected %d" % (len(seen), len(set(seen)), FIXTURE_COUNT))
    # House rule: a limit above the server maximum is lowered to it, not rejected (AIP-158).
    r = candidate_call(client.get, "/v1/incidents", params={"limit": 100000})
    if r.status_code != 200:
        fail("oversized limit -> %d; the house rule lowers it to the server cap" % r.status_code)
    body = cursor_page(r)
    items = body["data"]
    if not 0 < len(items) <= MAX_SANE_PAGE:
        fail("oversized limit did not return a nonempty capped page")
    ids = [item.get("id") if isinstance(item, dict) else None for item in items]
    if ids != seen[:len(items)] or not body.get("next_cursor"):
        fail("capped page lost the collection prefix or its continuation cursor")
    ok("cursor pagination walked %d unique incidents in %d pages; oversized limit capped at %d" %
       (FIXTURE_COUNT, pages, len(items)))


def check_filter(client):
    # limit=40 stays under any sane server-side cap; the 2026-09-02 campaign asked for 200
    # and false-failed three Opus builds whose cap was lower (see the evidence packet).
    r = candidate_call(client.get, "/v1/incidents", params={"status": "open", "limit": 40})
    if r.status_code != 200:
        fail("?status=open -> %d" % r.status_code)
    body = cursor_page(r)
    bad = [i["id"] for i in body["data"] if i.get("status") != "open"]
    if bad:
        fail("filter leaked non-open incidents: %s" % bad[:3])
    r = candidate_call(client.get, "/v1/incidents", params={"status": "bogus"})
    if r.status_code != 422:
        fail("?status=bogus -> %d; a well-formed request with an invalid value is 422" % r.status_code)
    good, why = is_problem(r)
    if not good:
        fail("invalid filter is not problem+json: " + why)
    ok("status filter honoured; invalid value -> %d problem+json" % r.status_code)


def check_problem_json(client):
    r = candidate_call(client.get, "/v1/incidents/inc-9999")
    if r.status_code != 404:
        fail("unknown id -> %d, expected 404" % r.status_code)
    good, why = is_problem(r)
    if not good:
        fail("404 is not problem+json: " + why)
    ok("404 " + why)


def check_no_leak(client):
    r = candidate_call(client.get, "/v1/incidents", params={"limit": 5})
    if "internal_note" in r.text:
        fail("list response leaks internal_note")
    r = candidate_call(client.get, "/v1/incidents/inc-0001")
    if r.status_code != 200:
        fail("detail -> %d" % r.status_code)
    if "internal_note" in r.text:
        fail("detail response leaks internal_note")
    ok("internal_note never crosses the API boundary")


def check_owner(client):
    r = candidate_call(client.get, "/v1/incidents/inc-0001")
    if r.status_code != 200:
        fail("detail -> %d" % r.status_code)
    if "alice" not in r.text:
        fail("detail does not carry the vendor's on-call owner: %s" % r.text[:200])
    ok("detail carries the on-call owner from the vendor")


def check_timeout(client):
    result = {}

    def call():
        try:
            resp = candidate_call(client.get, "/v1/incidents/inc-0001")
            result["status"] = resp.status_code
            result["resp"] = resp
        except Exception as exc:
            result["error"] = repr(exc)

    started = time.monotonic()
    t = threading.Thread(target=call, daemon=True)
    t.start()
    t.join(12)
    elapsed = time.monotonic() - started
    if t.is_alive():
        fail("detail hung >12s against a vendor that sleeps 20s: no timeout on the outbound call")
    if "error" in result:
        fail("detail raised instead of returning a problem: %s" % result["error"])
    # House rule: fail fast and never drop data silently. The optional owner enrichment may degrade
    # to an explicitly unavailable owner; otherwise the upstream failure is a 502/504 problem.
    status = result["status"]
    if status == 200:
        resp = result["resp"]
        marked, why = owner_marked_unavailable(resp)
        if not marked:
            fail("detail returned 200 without the vendor's owner and without marking it unavailable: "
                 + why)
        # The degraded response is still the public incident: same shape, same allowlist.
        if "internal_note" in resp.text:
            fail("the degraded 200 leaks internal_note")
        body = response_json(resp)
        if body.get("id") != "inc-0001" or not body.get("title"):
            fail("the degraded 200 is not the incident's public shape: %s" % resp.text[:200])
        ok("vendor timeout degraded to 200 in %.1fs with the owner %s" % (elapsed, why))
    if status not in (502, 504):
        fail("detail -> %d after %.1fs; expected 502/504 problem+json or 200 with the owner "
             "explicitly unavailable" % (status, elapsed))
    good, why = is_problem(result["resp"])
    if not good:
        fail("upstream failure is not problem+json (%d): %s" % (status, why))
    ok("vendor timeout surfaced as %d problem+json in %.1fs" % (status, elapsed))


def owner_marked_unavailable(resp):
    """True when a degraded detail response says the owner is unavailable instead of omitting it."""
    try:
        body = resp.json()
    except ValueError:
        return False, "body is not JSON"
    if not isinstance(body, dict):
        return False, "body is not an object"
    owner_keys = [key for key in body if "owner" in key.lower()]
    if not owner_keys:
        return False, "no owner field at all"
    for key in owner_keys:
        value = body[key]
        if value is None:
            return True, "field %r is null" % key
        text = json.dumps(value).lower()
        if any(word in text for word in ("unavailable", "unknown", "timeout", "timed out", "error", "n/a")):
            return True, "field %r marks it unavailable" % key
    return False, "owner field(s) %s carry a value but no unavailable marker" % owner_keys


def check_healthz(client):
    started = time.monotonic()
    r = candidate_call(client.get, "/healthz")
    elapsed = time.monotonic() - started
    if r.status_code != 200 or elapsed > 2:
        fail("/healthz -> %d in %.1fs against a slow vendor" % (r.status_code, elapsed))
    ok("/healthz stays independent of the vendor (%.2fs)" % elapsed)


CHECKS = {
    "pagination": (0.0, check_pagination),
    "filter": (0.0, check_filter),
    "problem_json": (0.0, check_problem_json),
    "no_leak": (0.0, check_no_leak),
    "owner": (0.0, check_owner),
    "timeout": (20.0, check_timeout),
    "healthz": (20.0, check_healthz),
}

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    if name not in CHECKS:
        raise ValueError("unknown oracle check %r" % name)
    delay, fn = CHECKS[name]
    sys.path.insert(0, os.getcwd())
    client = make_client(delay)
    fn(client)
