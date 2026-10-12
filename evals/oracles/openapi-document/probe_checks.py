"""Probe-owned oracle for a FastAPI service's committed OpenAPI document.

Usage: python probe_checks.py <check>. The service builds its app in app.main:create_app().
`document` passes when openapi.json at the repository root equals the app's generated document;
`drift_gate` passes when the service's own test suite fails on a stale openapi.json and passes on
the committed one. Exit 10 is a contract failure; any other non-zero exit means the measurement
itself was unavailable.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

WORKSPACE = Path.cwd()
DOCUMENT = WORKSPACE / "openapi.json"
# Settings the scenario fixtures read; pointed away from the workspace so grading leaves no files.
SCRATCH = tempfile.mkdtemp(prefix="openapi-oracle-")
ENV = {
    "DB_PATH": os.path.join(SCRATCH, "oracle.db"),
    "PAGING_BASE_URL": "http://paging.oracle.invalid",
    "RUNBOOK_BASE_URL": "http://runbooks.oracle.invalid",
    "PAGER_WEBHOOK_SECRET": "oracle-secret",
    "PYTHONDONTWRITEBYTECODE": "1",
}


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(10)


def ok(msg):
    print("OK: " + msg)
    sys.exit(0)


def committed():
    if not DOCUMENT.is_file():
        fail("no openapi.json committed at the repository root")
    try:
        return json.loads(DOCUMENT.read_text(encoding="utf-8"))
    except ValueError as exc:
        fail("openapi.json is not JSON: %s" % exc)


def generated():
    code = ("import json, sys; sys.path.insert(0, '.'); from app.main import create_app; "
            "print(json.dumps(create_app().openapi()))")
    result = subprocess.run([sys.executable, "-c", code], cwd=WORKSPACE, capture_output=True, text=True,
                            timeout=120, env={**os.environ, **ENV})
    if result.returncode != 0:
        fail("the app's document could not be generated: " + result.stderr[-1500:])
    return json.loads(result.stdout)


def check_document():
    if committed() != generated():
        fail("openapi.json differs from the document the code generates")
    ok("openapi.json is committed and equals the app's generated document")


def suite():
    return subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=WORKSPACE,
                          capture_output=True, text=True, timeout=600, env={**os.environ, **ENV})


def check_drift_gate():
    doc = committed()
    original = DOCUMENT.read_bytes()
    paths = doc.get("paths", {})
    if not paths:
        fail("openapi.json declares no paths")
    try:
        stale = dict(doc, paths=dict(list(paths.items())[1:]))
        DOCUMENT.write_text(json.dumps(stale, indent=2) + "\n", encoding="utf-8")
        with_stale = suite()
    finally:
        DOCUMENT.write_bytes(original)
    if with_stale.returncode == 0:
        fail("the test suite passes with a stale openapi.json: nothing checks the document against the code")
    with_committed = suite()
    if with_committed.returncode != 0:
        fail("the test suite fails on the committed openapi.json: " + (with_committed.stdout + with_committed.stderr)[-1500:])
    ok("the suite fails when openapi.json drifts from the code and passes when it matches")


CHECKS = {name[len("check_"):]: fn for name, fn in globals().items() if name.startswith("check_")}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in CHECKS:
        print("usage: probe_checks.py {%s}" % ",".join(sorted(CHECKS)))
        sys.exit(2)
    CHECKS[sys.argv[1]]()
