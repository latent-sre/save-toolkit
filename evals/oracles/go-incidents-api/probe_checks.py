"""Probe-owned oracle for the Go incidents service. Usage: python probe_checks.py <check>.

It builds the candidate's main package, starts the binary with PORT set, and drives it over HTTP,
so it grades the running service whatever framework the candidate chose. Exit 10 is a contract
failure; any other non-zero exit means the measurement itself was unavailable.
"""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

FIXTURE_COUNT = 501
MAX_SANE_PAGE = 500
TOKEN = "oracle-token"
WORKSPACE = Path.cwd()


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(10)


def ok(msg):
    print("OK: " + msg)
    sys.exit(0)


def go():
    found = shutil.which("go")
    if not found:
        print("UNAVAILABLE: go is not installed")
        sys.exit(1)
    return found


def main_package():
    listed = subprocess.run([go(), "list", "-f", "{{.Name}} {{.ImportPath}}", "./..."], cwd=WORKSPACE,
                            capture_output=True, text=True, timeout=300)
    if listed.returncode != 0:
        fail("go list failed: " + (listed.stderr or listed.stdout)[-1500:])
    mains = [line.split()[1] for line in listed.stdout.splitlines() if line.startswith("main ")]
    if len(mains) != 1:
        fail("expected exactly one main package, found %r" % mains)
    return mains[0]


SLOTS = 8


def binary_slot():
    """A stable path for the built service, held by a lock for this process's life.

    Windows Firewall asks about each new executable path that listens beyond loopback, and a
    candidate on PORT listens on all interfaces; reusing a few fixed paths asks once per slot
    instead of once per check. On Windows the slots live under LOCALAPPDATA, because the probe gives
    each trial its own TEMP and a per-trial path would ask again every trial."""
    base = os.environ.get("LOCALAPPDATA") if os.name == "nt" else None
    root = Path(base or tempfile.gettempdir()) / "save-toolkit-go-oracle"
    root.mkdir(parents=True, exist_ok=True)
    for n in range(SLOTS):
        lock = open(root / ("slot-%d.lock" % n), "a+b")
        try:
            if os.name == "nt":
                import msvcrt
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            lock.close()
            continue
        return lock, str(root / ("svc-%d%s" % (n, ".exe" if os.name == "nt" else "")))
    print("UNAVAILABLE: every oracle binary slot is busy")
    sys.exit(1)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Service:
    """The candidate's binary, built and listening on a loopback port."""

    def __enter__(self):
        self.dir = tempfile.mkdtemp(prefix="go-oracle-")
        self.slot, binary = binary_slot()
        built = subprocess.run([go(), "build", "-o", binary, main_package()], cwd=WORKSPACE,
                               capture_output=True, text=True, timeout=600)
        if built.returncode != 0:
            self.slot.close()
            shutil.rmtree(self.dir, ignore_errors=True)
            fail("go build failed: " + (built.stderr or built.stdout)[-1500:])
        self.port = free_port()
        env = {**os.environ, "PORT": str(self.port), "ONCALL_TEST_TOKEN": TOKEN}
        self.log = open(os.path.join(self.dir, "service.log"), "w+")
        self.proc = subprocess.Popen([binary], cwd=WORKSPACE, env=env, stdout=self.log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                self.log.seek(0)
                output = self.log.read()[-1500:]
                self.__exit__()
                fail("the service exited with %s before listening: %s" % (self.proc.returncode, output))
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.5):
                    return self
            except OSError:
                time.sleep(0.2)
        # __exit__ never runs after a failed __enter__: stop the candidate here, so a service that
        # ignores PORT does not outlive this check and hold ports or the binary slot.
        self.__exit__()
        fail("the service did not listen on PORT=%d within 30 s" % self.port)

    def __exit__(self, *exc):
        if self.proc.poll() is None:
            self.proc.kill()
        self.proc.wait(timeout=10)
        self.log.close()
        self.slot.close()
        shutil.rmtree(self.dir, ignore_errors=True)

    def request(self, method, path, token=TOKEN):
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path), method=method)
        if token:
            req.add_header("Authorization", "Bearer " + token)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, dict(resp.headers.items()), resp.read()
        except urllib.error.HTTPError as err:
            return err.code, dict(err.headers.items()), err.read()


def header(headers, name):
    return next((v for k, v in headers.items() if k.lower() == name.lower()), "")


def body_json(raw, what):
    try:
        return json.loads(raw)
    except ValueError:
        fail("%s is not JSON: %r" % (what, raw[:200]))


def assert_problem(status, headers, raw, expected, what):
    if status != expected:
        fail("%s answered %d, want %d: %r" % (what, status, expected, raw[:300]))
    ctype = header(headers, "Content-Type").partition(";")[0].strip().lower()
    if ctype != "application/problem+json":
        fail("%s Content-Type %r, want application/problem+json" % (what, ctype))
    body = body_json(raw, what)
    for key in ("type", "title", "request_id"):
        if not isinstance(body.get(key), str) or not body[key]:
            fail("%s problem lacks a nonempty %s: %r" % (what, key, body))
    if body.get("status") != expected:
        fail("%s problem status %r != %d" % (what, body.get("status"), expected))
    if body["request_id"] != header(headers, "X-Request-ID"):
        fail("%s request_id %r differs from X-Request-ID %r" % (what, body["request_id"], header(headers, "X-Request-ID")))
    return body


def page(svc, path):
    status, headers, raw = svc.request("GET", path)
    if status != 200:
        fail("GET %s answered %d: %r" % (path, status, raw[:300]))
    body = body_json(raw, "GET " + path)
    if not isinstance(body, dict) or not isinstance(body.get("data"), list):
        fail("GET %s: a collection is an object with a data array" % path)
    if "next_cursor" not in body:
        fail("GET %s: next_cursor missing; it is present and null on the last page" % path)
    cursor = body["next_cursor"]
    if cursor is not None and (not isinstance(cursor, str) or not cursor):
        fail("GET %s: next_cursor must be null or a nonempty string" % path)
    return body


def walk(svc, query):
    ids, path = [], "/v1/incidents?" + query
    for _ in range(FIXTURE_COUNT + 2):
        body = page(svc, path)
        if len(body["data"]) > MAX_SANE_PAGE:
            fail("a page of %d rows: an oversized limit must be lowered to a cap" % len(body["data"]))
        ids += [row.get("id") for row in body["data"]]
        if body["next_cursor"] is None:
            return ids, body
        path = "/v1/incidents?%s&cursor=%s" % (query, urllib.request.quote(body["next_cursor"], safe=""))
    fail("pagination never ended")


def check_auth():
    with Service() as svc:
        for path in ("/v1/incidents", "/v1/incidents/inc-0001"):
            for token, what in ((None, "no token"), ("wrong-token", "a wrong token")):
                status, headers, raw = svc.request("GET", path, token=token)
                assert_problem(status, headers, raw, 401, "GET %s with %s" % (path, what))
                if not header(headers, "WWW-Authenticate"):
                    fail("a 401 names its scheme in WWW-Authenticate")
    ok("both routes answer 401 problem+json with WWW-Authenticate without a valid bearer token")


def check_pagination():
    with Service() as svc:
        default = page(svc, "/v1/incidents")
        if len(default["data"]) >= FIXTURE_COUNT:
            fail("the default page returned all %d incidents" % len(default["data"]))
        ids, _ = walk(svc, "limit=1000")
    if len(ids) != FIXTURE_COUNT or len(set(ids)) != FIXTURE_COUNT:
        fail("the walk returned %d ids, %d unique; want %d" % (len(ids), len(set(ids)), FIXTURE_COUNT))
    ok("cursor pages walk %d unique incidents; the oversized limit is lowered" % FIXTURE_COUNT)


def check_filter():
    expected_closed = sum(1 for n in range(1, FIXTURE_COUNT + 1) if n % 3 == 0)
    with Service() as svc:
        ids, _ = walk(svc, "status=closed&limit=200")
        status, headers, raw = svc.request("GET", "/v1/incidents?status=bogus")
        body = assert_problem(status, headers, raw, 422, "GET /v1/incidents?status=bogus")
    if len(set(ids)) != expected_closed or any(int(i.rsplit("-", 1)[1]) % 3 for i in ids):
        fail("?status=closed returned %d ids, want exactly the %d closed ones" % (len(set(ids)), expected_closed))
    if not isinstance(body.get("errors"), list) or not body["errors"]:
        fail("a 422 locates the invalid input in errors[]: %r" % body)
    ok("?status= filters, and an invalid value is a 422 problem+json with errors[]")


def check_problem_json():
    with Service() as svc:
        status, headers, raw = svc.request("GET", "/v1/incidents/inc-9999")
        assert_problem(status, headers, raw, 404, "GET /v1/incidents/inc-9999")
        status, _, raw = svc.request("GET", "/v1/incidents/inc-0003")
        if status != 200 or body_json(raw, "GET /v1/incidents/inc-0003").get("id") != "inc-0003":
            fail("GET /v1/incidents/inc-0003 answered %d: %r" % (status, raw[:300]))
    ok("a missing incident is a 404 problem+json whose request_id matches X-Request-ID")


def check_router_problems():
    with Service() as svc:
        status, headers, raw = svc.request("GET", "/v1/no-such-route")
        assert_problem(status, headers, raw, 404, "GET /v1/no-such-route")
        status, headers, raw = svc.request("DELETE", "/v1/incidents")
        assert_problem(status, headers, raw, 405, "DELETE /v1/incidents")
        if "GET" not in header(headers, "Allow"):
            fail("a 405 names the allowed methods in Allow")
    ok("the router's own 404 and 405 answer problem+json")


def check_no_leak():
    with Service() as svc:
        _, _, listed = svc.request("GET", "/v1/incidents?limit=200")
        _, _, one = svc.request("GET", "/v1/incidents/inc-0001")
    for raw in (listed, one):
        if b"internal_note" in raw or b"triage scratch" in raw:
            fail("the store's internal_note crossed the API boundary")
    ok("internal_note never crosses the API boundary")


def committed_document():
    path = WORKSPACE / "openapi.json"
    if not path.is_file():
        fail("no openapi.json committed at the repository root")
    return path, body_json(path.read_bytes(), "openapi.json")


def check_document():
    _, doc = committed_document()
    if not str(doc.get("openapi", "")).startswith("3.1"):
        fail("openapi.json declares %r; emit 3.1, valid as 3.2" % doc.get("openapi"))
    paths = doc.get("paths", {})
    ids = []
    for path in ("/v1/incidents", "/v1/incidents/{id}"):
        op = (paths.get(path) or {}).get("get")
        if op is None:
            fail("openapi.json has no GET %s (the item parameter is named {id})" % path)
        op_id = op.get("operationId", "")
        if not re.fullmatch(r"[a-z][A-Za-z0-9]*", op_id):
            fail("GET %s operationId %r is not a lowerCamel name" % (path, op_id))
        ids.append(op_id)
        if not op.get("security") and not doc.get("security"):
            fail("GET %s declares no security" % path)
        for code, response in op.get("responses", {}).items():
            if code.isdigit() and int(code) >= 400 and list(response.get("content", {})) != ["application/problem+json"]:
                fail("GET %s response %s is not application/problem+json" % (path, code))
    if len(set(ids)) != len(ids):
        fail("operationIds repeat: %r" % ids)
    ok("openapi.json is committed: 3.1, lowerCamel operationIds, security, problem+json errors")


def go_test():
    return subprocess.run([go(), "test", "-count=1", "./..."], cwd=WORKSPACE, capture_output=True,
                          text=True, timeout=600, env={**os.environ, "ONCALL_TEST_TOKEN": TOKEN})


def check_drift_gate():
    path, doc = committed_document()
    original = path.read_bytes()
    try:
        corrupted = dict(doc, paths={k: v for k, v in doc.get("paths", {}).items() if k != "/v1/incidents"})
        path.write_text(json.dumps(corrupted, indent=2) + "\n", encoding="utf-8")
        stale = go_test()
    finally:
        path.write_bytes(original)
    if stale.returncode == 0:
        fail("go test passes with a stale openapi.json: nothing checks the document against the code")
    fresh = go_test()
    if fresh.returncode != 0:
        fail("go test fails on the committed openapi.json: " + (fresh.stdout + fresh.stderr)[-1500:])
    ok("go test fails when openapi.json drifts from the code and passes when it matches")


def check_server_timeouts():
    sources = [p for p in WORKSPACE.rglob("*.go") if not p.name.endswith("_test.go")]
    if not any("ReadHeaderTimeout" in p.read_text(encoding="utf-8", errors="replace") for p in sources):
        fail("no http.Server sets ReadHeaderTimeout: the zero server has no timeouts")
    ok("the server sets ReadHeaderTimeout")


CHECKS = {name[len("check_"):]: fn for name, fn in globals().items() if name.startswith("check_")}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in CHECKS:
        print("usage: probe_checks.py {%s}" % ",".join(sorted(CHECKS)))
        sys.exit(2)
    CHECKS[sys.argv[1]]()
