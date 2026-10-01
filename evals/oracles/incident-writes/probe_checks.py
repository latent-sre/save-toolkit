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


def start_app():
    """Run the real app under uvicorn on a free loopback port with a fresh SQLite file."""
    db = os.path.join(tempfile.mkdtemp(prefix="writes-probe-"), "probe.db")
    os.environ["DB_PATH"] = db
    sys.path.insert(0, os.getcwd())
    import uvicorn
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
        return conn.execute("SELECT id, title, service FROM incidents ORDER BY created_at").fetchall()


def post(base, body, key):
    headers = {"Idempotency-Key": key} if key else {}
    return httpx.post(base + "/v1/incidents", json=body, headers=headers, timeout=20)


def is_problem(resp):
    ctype = resp.headers.get("content-type", "")
    if not ctype.startswith("application/problem+json"):
        return False, "content-type %r" % ctype
    try:
        body = resp.json()
    except ValueError:
        return False, "body is not JSON"
    if body.get("status") != resp.status_code:
        return False, "problem status %r != %d" % (body.get("status"), resp.status_code)
    return True, "problem+json"


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
    r = httpx.get(base + "/v1/incidents/" + body["id"], timeout=10)
    if r.status_code != 200 or r.json().get("title") != BODY["title"]:
        fail("created incident is not readable by id: %d %s" % (r.status_code, r.text[:200]))
    if len(rows(db)) != 1:
        fail("one create left %d rows" % len(rows(db)))
    ok("keyed create -> 201 %s, readable by id" % body["id"])


def check_replay(base, db):
    key = str(uuid.uuid4())
    first = created(post(base, BODY, key), "first request")
    second = post(base, BODY, key)
    if second.status_code != 201 or second.json().get("id") != first["id"]:
        fail("resend -> %d %s; expected the first result (201, id %s)"
             % (second.status_code, second.text[:200], first["id"]))
    if len(rows(db)) != 1:
        fail("a resend with the same key left %d rows" % len(rows(db)))
    ok("resend replayed %s without a second row" % first["id"])


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


def check_concurrent(base, db):
    key = str(uuid.uuid4())
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
    errors = [r for r in results if isinstance(r, Exception)]
    if errors or len(results) != 2:
        fail("overlapping requests did not both return: %s" % (errors or results))
    if len(rows(db)) != 1:
        fail("two overlapping requests with one key left %d rows" % len(rows(db)))
    ids = {r.json().get("id") for r in results if r.status_code == 201}
    if len(ids) != 1:
        fail("overlapping requests returned %s; at least one 201 and one id expected"
             % [r.status_code for r in results])
    for r in results:
        if r.status_code == 409:
            good, why = is_problem(r)
            if not good:
                fail("the in-progress 409 is not problem+json: " + why)
        elif r.status_code != 201:
            fail("an overlapping request -> %d; expected 201 or an in-progress 409" % r.status_code)
    ok("overlapping requests -> %s, one row" % sorted(r.status_code for r in results))


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
