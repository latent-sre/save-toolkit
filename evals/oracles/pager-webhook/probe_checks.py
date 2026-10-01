"""Probe-owned oracle for the pager webhook. Usage: python probe_checks.py <check>."""
import atexit
import hashlib
import hmac
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx

SECRET = "probe-webhook-secret"
# The runbook lookup must outlast the vendor's 3 s window; CI shortens it to keep the suite fast.
RUNBOOK_DELAY = float(os.environ.get("PROBE_RUNBOOK_DELAY", "8"))
ACK_WINDOW_S = 3.0
_PROCS = []


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def ok(msg):
    print("OK: " + msg)
    sys.exit(0)


@atexit.register
def _stop_apps():
    for proc in _PROCS:
        if proc.poll() is None:
            proc.kill()


class _Runbooks(BaseHTTPRequestHandler):
    def do_GET(self):
        time.sleep(RUNBOOK_DELAY)
        service = self.path.partition("service=")[2] or "unknown"
        body = json.dumps({"url": "https://runbooks.example.invalid/" + service}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def start():
    """A runbook stub, then the app as a uvicorn subprocess on a fresh SQLite file."""
    runbooks = ThreadingHTTPServer(("127.0.0.1", 0), _Runbooks)
    threading.Thread(target=runbooks.serve_forever, daemon=True).start()
    db = os.path.join(tempfile.mkdtemp(prefix="webhook-probe-"), "probe.db")
    port = free_port()
    env = dict(os.environ, DB_PATH=db, PAGER_WEBHOOK_SECRET=SECRET, PYTHONDONTWRITEBYTECODE="1",
               RUNBOOK_BASE_URL="http://127.0.0.1:%d" % runbooks.server_address[1])
    code = ("import uvicorn; from app.main import create_app; "
            "uvicorn.run(create_app(), host='127.0.0.1', port=%d, log_level='warning')" % port)
    proc = subprocess.Popen([sys.executable, "-c", code], cwd=os.getcwd(), env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    _PROCS.append(proc)
    base = "http://127.0.0.1:%d" % port
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            fail("the app exited at startup: %s" % (proc.stderr.read() or "")[-400:])
        try:
            httpx.get(base + "/healthz", timeout=1)
            return proc, base, db
        except httpx.HTTPError:
            time.sleep(0.2)
    fail("the app did not answer /healthz within 30 s")


def new_event(summary=None):
    event_id = "evt-" + uuid.uuid4().hex
    return {"event_id": event_id, "service": "checkout",
            "summary": summary or "Checkout 5xx above 2%% (%s)" % event_id[-6:]}


def deliver(base, event, signature="valid"):
    body = json.dumps(event).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if signature == "valid":
        headers["X-Pager-Signature"] = "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    elif signature == "forged":
        headers["X-Pager-Signature"] = "sha256=" + hmac.new(b"wrong-secret", body, hashlib.sha256).hexdigest()
    started = time.monotonic()
    response = httpx.post(base + "/v1/webhooks/pager", content=body, headers=headers, timeout=30)
    return response, time.monotonic() - started


def incidents(db, title=None):
    with sqlite3.connect(db, timeout=10) as conn:
        rows = conn.execute("SELECT title, service, runbook_url FROM incidents").fetchall()
    return [r for r in rows if title is None or r[0] == title]


def stored_anywhere(db, needle):
    with sqlite3.connect(db, timeout=10) as conn:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
        for table in tables:
            for row in conn.execute('SELECT * FROM "%s"' % table.replace('"', '""')):
                if any(needle in str(cell) for cell in row):
                    return table
    return None


def wait_for_incident(db, title, seconds=RUNBOOK_DELAY + 20):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        found = incidents(db, title)
        if found:
            return found
        time.sleep(0.25)
    return []


def is_problem(resp):
    ctype = resp.headers.get("content-type", "")
    if not ctype.startswith("application/problem+json"):
        return False, "content-type %r" % ctype
    try:
        status = resp.json().get("status")
    except ValueError:
        return False, "body is not JSON"
    return (status == resp.status_code), "problem status %r" % status


def check_signature(proc, base, db):
    for mode in ("forged", "missing"):
        event = new_event()
        resp, _ = deliver(base, event, signature=mode)
        if resp.status_code not in (401, 403):
            fail("%s signature -> %d; expected 401 or 403" % (mode, resp.status_code))
        good, why = is_problem(resp)
        if not good:
            fail("%s-signature refusal is not problem+json: %s" % (mode, why))
        time.sleep(1.0)
        where = stored_anywhere(db, event["event_id"])
        if where or incidents(db, event["summary"]):
            fail("a %s-signature event was stored (table %s)" % (mode, where))
    ok("forged and missing signatures -> refused as problem+json; nothing stored")


def check_fast_ack(proc, base, db):
    resp, elapsed = deliver(base, new_event())
    if not 200 <= resp.status_code < 300 or elapsed >= ACK_WINDOW_S:
        fail("valid event -> %d after %.1fs; the vendor needs a 2xx within %.0fs while the runbook "
             "lookup takes %.0fs" % (resp.status_code, elapsed, ACK_WINDOW_S, RUNBOOK_DELAY))
    ok("valid event acknowledged %d in %.2fs" % (resp.status_code, elapsed))


def check_accepted(proc, base, db):
    resp, _ = deliver(base, new_event())
    if resp.status_code != 202:
        fail("valid event -> %d; a new asynchronous receiver answers 202 Accepted" % resp.status_code)
    ok("valid event -> 202 Accepted")


def check_completes(proc, base, db):
    # An incident may be created first and enriched later; poll until the link arrives.
    event = new_event()
    resp, _ = deliver(base, event)
    if not 200 <= resp.status_code < 300:
        fail("valid event -> %d" % resp.status_code)
    expected = "https://runbooks.example.invalid/checkout"
    deadline = time.monotonic() + RUNBOOK_DELAY + 20
    found = []
    while time.monotonic() < deadline:
        found = incidents(db, event["summary"])
        if found and found[0][2] == expected:
            break
        time.sleep(0.25)
    if not found:
        fail("no incident titled %r appeared within %.0fs" % (event["summary"], RUNBOOK_DELAY + 20))
    title, service, url = found[0]
    if service != "checkout" or url != expected:
        fail("within %.0fs the incident carries service %r and runbook link %r"
             % (RUNBOOK_DELAY + 20, service, url))
    ok("incident created with its runbook link")


def check_redelivery(proc, base, db):
    event = new_event()
    for attempt in range(3):
        resp, _ = deliver(base, event)
        if not 200 <= resp.status_code < 300:
            fail("delivery %d of one event -> %d; a redelivery is acknowledged too"
                 % (attempt + 1, resp.status_code))
        time.sleep(1.0)
    if not wait_for_incident(db, event["summary"]):
        fail("no incident appeared for the redelivered event")
    time.sleep(RUNBOOK_DELAY + 3)
    count = len(incidents(db, event["summary"]))
    if count != 1:
        fail("three deliveries of one event made %d incidents" % count)
    ok("three deliveries of one event -> one incident")


def check_durable(proc, base, db):
    event = new_event()
    resp, elapsed = deliver(base, event)
    proc.kill()
    proc.wait(10)
    if not 200 <= resp.status_code < 300:
        fail("valid event -> %d" % resp.status_code)
    where = stored_anywhere(db, event["event_id"])
    if where is None:
        fail("the app acknowledged the event (%d in %.1fs) but had not stored it when killed"
             % (resp.status_code, elapsed))
    ok("event stored in %r before the acknowledgement" % where)


CHECKS = {
    "signature": check_signature,
    "fast_ack": check_fast_ack,
    "accepted": check_accepted,
    "completes": check_completes,
    "redelivery": check_redelivery,
    "durable": check_durable,
}

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    if name not in CHECKS:
        fail("unknown check %r" % name)
    CHECKS[name](*start())
