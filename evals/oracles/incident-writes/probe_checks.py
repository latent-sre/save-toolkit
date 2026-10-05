"""Probe-owned oracle for idempotent incident writes. Usage: python probe_checks.py <check>."""
import os
import socket
import sqlite3
import sys
import tempfile
import threading
import time
import uuid

import httpx

BODY = {"title": "Checkout 5xx above 2%", "service": "checkout"}
OTHER = {"title": "Search latency above 800 ms", "service": "search"}


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def ok(msg):
    print("OK: " + msg)
    sys.exit(0)


# Server-side overlap control for the concurrency check: the first armed write waits inside the
# write path until a second write arrives there (proving overlap) or 1.5 s pass (a serializing
# implementation keeps the second request out, which is the correct outcome).
GATE = {"armed": False, "inside": 0, "max_inside": 0, "first_in": threading.Event(),
        "lock": threading.Lock(), "instrumented": False}


def instrument_store():
    """Wrap the fixture's store.create_incident before the app imports it."""
    try:
        import app.store as store
    except Exception:
        return
    original = getattr(store, "create_incident", None)
    if not callable(original):
        return

    def held(*args, **kwargs):
        with GATE["lock"]:
            GATE["inside"] += 1
            GATE["max_inside"] = max(GATE["max_inside"], GATE["inside"])
            first = GATE["armed"] and not GATE["first_in"].is_set()
            if GATE["armed"]:
                GATE["first_in"].set()
        try:
            if first:
                deadline = time.monotonic() + 1.5
                while time.monotonic() < deadline and GATE["max_inside"] < 2:
                    time.sleep(0.01)
            return original(*args, **kwargs)
        finally:
            with GATE["lock"]:
                GATE["inside"] -= 1

    store.create_incident = held
    GATE["instrumented"] = True


def start_app():
    """Run the real app under uvicorn on a free loopback port with a fresh SQLite file."""
    db = os.path.join(tempfile.mkdtemp(prefix="writes-probe-"), "probe.db")
    os.environ["DB_PATH"] = db
    sys.path.insert(0, os.getcwd())
    import uvicorn
    instrument_store()
    from app.main import create_app

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    deadline = time.monotonic() + 20
    while not server.started:
        if time.monotonic() > deadline:
            fail("the app did not start under uvicorn within 20 s")
        time.sleep(0.05)
    return "http://127.0.0.1:%d" % port, db


def rows(db):
    with sqlite3.connect(db, timeout=10) as conn:
        return conn.execute("SELECT id, title, service, status FROM incidents ORDER BY created_at").fetchall()


def post(base, body, key):
    headers = {"Idempotency-Key": key} if key else {}
    return httpx.post(base + "/v1/incidents", json=body, headers=headers, timeout=20)


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


def created(resp, what):
    if resp.status_code != 201:
        fail("%s -> %d, expected 201: %s" % (what, resp.status_code, resp.text[:200]))
    body = resp.json()
    if not isinstance(body, dict) or not body.get("id"):
        fail("%s returned no incident id: %s" % (what, resp.text[:200]))
    return body


def check_create(base, db):
    body = created(post(base, BODY, str(uuid.uuid4())), "keyed create")
    if body.get("title") != BODY["title"] or body.get("service") != BODY["service"]:
        fail("create echoed the wrong incident: %s" % body)
    if body.get("status") != "open":
        fail("a new incident must start open; the response says %r" % body.get("status"))
    r = httpx.get(base + "/v1/incidents/" + body["id"], timeout=10)
    if r.status_code != 200 or r.json().get("title") != BODY["title"]:
        fail("created incident is not readable by id: %d %s" % (r.status_code, r.text[:200]))
    stored = rows(db)
    if len(stored) != 1:
        fail("one create left %d rows" % len(stored))
    if stored[0][3] != "open":
        fail("the stored incident starts %r, not open" % stored[0][3])
    ok("keyed create -> 201 %s, open, readable by id" % body["id"])


def check_replay(base, db):
    key = str(uuid.uuid4())
    first = created(post(base, BODY, key), "first request")
    second = post(base, BODY, key)
    if second.status_code != 201 or second.json() != first:
        fail("resend -> %d %s; expected the first result exactly (201, %s)"
             % (second.status_code, second.text[:200], first))
    if len(rows(db)) != 1:
        fail("a resend with the same key left %d rows" % len(rows(db)))
    ok("resend replayed %s exactly, without a second row" % first["id"])


def check_replay_header(base, db):
    key = str(uuid.uuid4())
    first = post(base, BODY, key)
    second = post(base, BODY, key)
    if first.headers.get("Idempotent-Replayed", "false").lower() == "true":
        fail("the first response claims to be a replay")
    if second.headers.get("Idempotent-Replayed", "").lower() != "true":
        fail("the replay lacks Idempotent-Replayed: true (headers: %s)" % sorted(second.headers))
    ok("replay flagged Idempotent-Replayed: true")


def check_conflict(base, db):
    key = str(uuid.uuid4())
    first = created(post(base, BODY, key), "first request")
    clash = post(base, OTHER, key)
    if clash.status_code != 422:
        fail("same key, different payload -> %d %s; expected 422" % (clash.status_code, clash.text[:200]))
    good, why = is_problem(clash)
    if not good:
        fail("the 422 is not problem+json: " + why)
    stored = rows(db)
    if len(stored) != 1 or stored[0][1] != BODY["title"]:
        fail("a refused payload changed the incidents: %s" % stored)
    again = post(base, BODY, key)
    if again.status_code != 201 or again.json().get("id") != first["id"]:
        fail("after the refusal, the original payload no longer replays: %d" % again.status_code)
    ok("reused key with a different payload -> 422 problem; nothing changed")


def check_missing_key(base, db):
    r = post(base, BODY, None)
    if r.status_code != 400:
        fail("write without Idempotency-Key -> %d; expected 400" % r.status_code)
    good, why = is_problem(r)
    if not good:
        fail("the 400 is not problem+json: " + why)
    if rows(db):
        fail("a refused write still created %d row(s)" % len(rows(db)))
    ok("write without a key -> 400 problem; no row")


def race_from_barrier(base, key):
    """Two requests with one key, released together from a client-side barrier."""
    barrier = threading.Barrier(2)
    results = []

    def send():
        barrier.wait()
        try:
            results.append(post(base, BODY, key))
        except Exception as exc:
            results.append(exc)

    threads = [threading.Thread(target=send) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    return results


def check_concurrent(base, db):
    key = str(uuid.uuid4())
    results = []

    def send():
        try:
            results.append(post(base, BODY, key))
        except Exception as exc:
            results.append(exc)

    # Hold the first request inside the store's write path, uncommitted, then send the second.
    GATE["armed"] = True
    first = threading.Thread(target=send)
    first.start()
    while GATE["instrumented"] and not GATE["first_in"].is_set() and first.is_alive():
        time.sleep(0.01)
    if GATE["first_in"].is_set():
        second = threading.Thread(target=send)
        second.start()
        for t in (first, second):
            t.join(30)
        new_rows = len(rows(db))
        how = "second request sent while the first was held inside store.create_incident, uncommitted"
    else:
        # The app writes without store.create_incident, so the gate cannot hold it. Never fall back
        # to sequential requests: race two fresh ones from a barrier, as before the gate existed.
        first.join(30)
        GATE["armed"] = False
        before = len(rows(db))
        results = race_from_barrier(base, str(uuid.uuid4()))
        new_rows = len(rows(db)) - before
        how = ("client-side barrier fallback: the app does not write through store.create_incident,"
               " so overlap is likely but not proven")
    errors = [r for r in results if isinstance(r, Exception)]
    if errors or len(results) != 2:
        fail("overlapping requests did not both return: %s" % (errors or results))
    if new_rows != 1:
        fail("two overlapping requests with one key left %d rows (%s)" % (new_rows, how))
    bodies = [created(r, "an overlapping request") for r in results if r.status_code == 201]
    if not bodies or len({b["id"] for b in bodies}) != 1:
        fail("overlapping requests returned %s; at least one 201 and one id expected"
             % [r.status_code for r in results])
    for r in results:
        if r.status_code == 409:
            good, why = is_problem(r)
            if not good:
                fail("the in-progress 409 is not problem+json: " + why)
        elif r.status_code != 201:
            fail("an overlapping request -> %d; expected 201 or an in-progress 409" % r.status_code)
    ok("overlapping requests -> %s, one row (%s)" % (sorted(r.status_code for r in results), how))


def check_distinct_keys(base, db):
    a = created(post(base, BODY, str(uuid.uuid4())), "first alert")
    b = created(post(base, BODY, str(uuid.uuid4())), "second alert")
    if a["id"] == b["id"] or len(rows(db)) != 2:
        fail("two alerts with different keys were merged: ids %s/%s, %d rows"
             % (a["id"], b["id"], len(rows(db))))
    ok("different keys stay different incidents")


CHECKS = {
    "create": check_create,
    "replay": check_replay,
    "replay_header": check_replay_header,
    "conflict": check_conflict,
    "missing_key": check_missing_key,
    "concurrent": check_concurrent,
    "distinct_keys": check_distinct_keys,
}

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    if name not in CHECKS:
        fail("unknown check %r" % name)
    try:
        base, db = start_app()
    except SystemExit:
        raise
    except Exception as exc:
        fail("could not start the app: %r" % exc)
    CHECKS[name](base, db)
