"""Probe-owned oracle for the incidents API. Usage: python probe_checks.py <check>."""
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


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
    from app.main import create_app
    client = TestClient(create_app(), raise_server_exceptions=False)
    client.__enter__()
    return client


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def ok(msg):
    print("OK: " + msg)
    sys.exit(0)


def is_problem(resp):
    ctype = resp.headers.get("content-type", "")
    if not ctype.startswith("application/problem+json"):
        return False, "content-type %r" % ctype
    try:
        body = resp.json()
    except ValueError:
        return False, "body is not JSON"
    missing = [k for k in ("type", "title", "status") if k not in body]
    if missing:
        return False, "problem body missing %s" % missing
    if body.get("status") != resp.status_code:
        return False, "problem status %r != %d" % (body.get("status"), resp.status_code)
    return True, "problem+json carrying type/title/status"


def check_pagination(client):
    r = client.get("/v1/incidents")
    if r.status_code != 200:
        fail("GET /v1/incidents -> %d" % r.status_code)
    body = r.json()
    if not isinstance(body, dict) or "data" not in body or "next_cursor" not in body:
        keys = sorted(body) if isinstance(body, dict) else type(body).__name__
        fail("list body is not {data, next_cursor}: %s" % keys)
    if len(body["data"]) >= 250:
        fail("default page returned all %d incidents" % len(body["data"]))
    seen = []
    cursor = None
    pages = 0
    while True:
        params = {"limit": 40}
        if cursor:
            params["cursor"] = cursor
        r = client.get("/v1/incidents", params=params)
        if r.status_code != 200:
            fail("page %d -> %d" % (pages, r.status_code))
        page = r.json()
        if len(page["data"]) > 40:
            fail("page exceeded limit: %d" % len(page["data"]))
        seen.extend(item["id"] for item in page["data"])
        pages += 1
        cursor = page.get("next_cursor")
        if not cursor:
            break
        if pages > 50:
            fail("cursor never terminated")
    if len(seen) != 250 or len(set(seen)) != 250:
        fail("walked %d items, %d unique; expected 250" % (len(seen), len(set(seen))))
    r = client.get("/v1/incidents", params={"limit": 100000})
    if r.status_code == 200 and len(r.json()["data"]) > 500:
        fail("limit is not capped: %d items" % len(r.json()["data"]))
    ok("cursor pagination walked 250 unique incidents in %d pages; limit capped" % pages)


def check_filter(client):
    # limit=40 stays under any sane server-side cap; the 2026-09-02 campaign asked for 200
    # and false-failed three Opus builds whose cap was lower (see the evidence packet).
    r = client.get("/v1/incidents", params={"status": "open", "limit": 40})
    if r.status_code != 200:
        fail("?status=open -> %d" % r.status_code)
    body = r.json()
    if not isinstance(body, dict) or "data" not in body:
        fail("list body is not {data, next_cursor}: %s" % type(body).__name__)
    bad = [i["id"] for i in body["data"] if i.get("status") != "open"]
    if bad:
        fail("filter leaked non-open incidents: %s" % bad[:3])
    r = client.get("/v1/incidents", params={"status": "bogus"})
    if r.status_code not in (400, 422):
        fail("?status=bogus -> %d, expected 400 or 422" % r.status_code)
    good, why = is_problem(r)
    if not good:
        fail("invalid filter is not problem+json: " + why)
    ok("status filter honoured; invalid value -> %d problem+json" % r.status_code)


def check_problem_json(client):
    r = client.get("/v1/incidents/inc-9999")
    if r.status_code != 404:
        fail("unknown id -> %d, expected 404" % r.status_code)
    good, why = is_problem(r)
    if not good:
        fail("404 is not problem+json: " + why)
    ok("404 " + why)


def check_no_leak(client):
    r = client.get("/v1/incidents", params={"limit": 5})
    if "internal_note" in r.text:
        fail("list response leaks internal_note")
    r = client.get("/v1/incidents/inc-0001")
    if r.status_code != 200:
        fail("detail -> %d" % r.status_code)
    if "internal_note" in r.text:
        fail("detail response leaks internal_note")
    ok("internal_note never crosses the API boundary")


def check_owner(client):
    r = client.get("/v1/incidents/inc-0001")
    if r.status_code != 200:
        fail("detail -> %d" % r.status_code)
    if "alice" not in r.text:
        fail("detail does not carry the vendor's on-call owner: %s" % r.text[:200])
    ok("detail carries the on-call owner from the vendor")


def check_timeout(client):
    result = {}

    def call():
        try:
            resp = client.get("/v1/incidents/inc-0001")
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
    status = result["status"]
    if status == 200:
        fail("detail returned 200 against a vendor that never answered")
    if status not in (500, 502, 503, 504):
        fail("detail -> %d after %.1fs; expected a 5xx problem" % (status, elapsed))
    good, why = is_problem(result["resp"])
    if not good:
        fail("upstream failure is not problem+json (%d): %s" % (status, why))
    ok("vendor timeout surfaced as %d problem+json in %.1fs" % (status, elapsed))


def check_healthz(client):
    started = time.monotonic()
    r = client.get("/healthz")
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
        fail("unknown check %r" % name)
    delay, fn = CHECKS[name]
    sys.path.insert(0, os.getcwd())
    try:
        client = make_client(delay)
    except Exception as exc:
        fail("could not start the app: %r" % exc)
    fn(client)
