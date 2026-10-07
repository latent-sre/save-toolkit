"""No-model regressions for the pager-webhook oracle: a house-rule reference passes, mutants fail."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "evals/build-scenarios/build-software-engineer-pager-webhook.yaml"
ORACLE = ROOT / "evals/oracles/pager-webhook/probe_checks.py"
CHECKS = ["signature", "fast_ack", "accepted", "completes", "redelivery", "durable"]

REFERENCE = '''
"""opsapi application factory."""
from __future__ import annotations

import hashlib
import hmac
import json
import threading
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app import store
from app.config import get_settings
from app.db import connect, init_schema
from app.errors import install_problem_handlers
from app.runbooks import runbook_url

INBOX = INBOX_SQL
INSERT_INCIDENT = ("INSERT INTO incidents (id, title, service, status, runbook_url, created_at)"
                   " VALUES (?, ?, ?, INCIDENT_STATUS, ?, ?)")


def _incident_args(event: dict, url: str) -> tuple:
    return (f"inc-{uuid.uuid4().hex[:12]}", event["summary"], event["service"], url,
            datetime.now(timezone.utc).isoformat())


def _enrich_later(event: dict) -> None:
    url = runbook_url(event["service"])
    with connect() as conn:
        conn.execute("UPDATE incidents SET runbook_url = ? WHERE title = ?", (url, event["summary"]))
        conn.commit()


def _process_one(event: dict) -> None:
    url = runbook_url(event["service"])
    with connect() as conn:
        conn.execute(INSERT_INCIDENT, _incident_args(event, url))
        conn.commit()


def _worker(stop: threading.Event) -> None:
    while not stop.is_set():
        with connect() as conn:
            row = conn.execute("SELECT rowid AS rid, event_id, service, summary FROM pager_events"
                               " WHERE status = 'pending' ORDER BY rowid LIMIT 1").fetchone()
        if row is None:
            stop.wait(0.2)
            continue
        url = runbook_url(row["service"])
        with connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            current = conn.execute("SELECT status FROM pager_events WHERE rowid = ?", (row["rid"],)).fetchone()
            if current["status"] == "pending":
                conn.execute(INSERT_INCIDENT, _incident_args(dict(row), url))
                conn.execute("UPDATE pager_events SET status = 'done' WHERE rowid = ?", (row["rid"],))
            conn.commit()


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_schema()
        with connect() as conn:
            conn.execute(INBOX)
        stop = threading.Event()
        if WORKER_ENABLED:
            threading.Thread(target=_worker, args=(stop,), daemon=True).start()
        yield
        stop.set()

    app = FastAPI(title="opsapi", lifespan=lifespan)
    install_problem_handlers(app)

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    @app.post("/v1/webhooks/pager")
    async def pager(request: Request):
        raw = await request.body()
        expected = "sha256=" + hmac.new(get_settings().pager_webhook_secret.encode(), raw,
                                        hashlib.sha256).hexdigest()
        if SIGNATURE_REJECTS:
            raise HTTPException(401, "invalid or missing X-Pager-Signature")
        event = json.loads(raw)
        ACCEPT
        return JSONResponse({"accepted": event["event_id"]}, status_code=ACK_STATUS)

    return app
'''
HOUSE = {
    "INBOX_SQL": ('"CREATE TABLE IF NOT EXISTS pager_events (event_id TEXT PRIMARY KEY, service TEXT,'
                  ' summary TEXT, status TEXT NOT NULL DEFAULT \'pending\')"'),
    "WORKER_ENABLED": "True",
    "SIGNATURE_REJECTS": 'not hmac.compare_digest(request.headers.get("x-pager-signature", ""), expected)',
    "ACCEPT": ('with connect() as conn:\n'
               '            conn.execute("INSERT OR IGNORE INTO pager_events (event_id, service, summary)"\n'
               '                         " VALUES (?, ?, ?)", (event["event_id"], event["service"], event["summary"]))\n'
               '            conn.commit()'),
    "ACK_STATUS": "202",
    "INCIDENT_STATUS": "'open'",
}
_INBOX = ('"CREATE TABLE IF NOT EXISTS pager_events ({cols}, service TEXT, summary TEXT{pk},'
          ' status TEXT NOT NULL DEFAULT \'pending\')"')
# name: (check that must fail, overrides, expected failure text)
MUTANTS = {
    "no_signature_check": ("signature", {"SIGNATURE_REJECTS": "False"}, "signature ->"),
    "signature_checked_after_processing": (
        "signature",
        {"SIGNATURE_REJECTS": ('(threading.Thread(target=_process_one, args=(json.loads(raw),), daemon=True).start()'
                               ' or True) and not hmac.compare_digest(request.headers.get("x-pager-signature", ""),'
                               ' expected)')},
        "was stored or processed"),
    "inline_processing": ("fast_ack", {"ACCEPT": "_process_one(event)", "WORKER_ENABLED": "False"},
                          "needs a 2xx within"),
    "status_200": ("accepted", {"ACK_STATUS": "200"}, "answers 202 Accepted"),
    "no_worker": ("completes", {"WORKER_ENABLED": "False"}, "no incident titled"),
    "incident_closed": ("completes", {"INCIDENT_STATUS": "'closed'"}, "must start open"),
    "no_dedupe": ("redelivery",
                  {"INBOX_SQL": _INBOX.format(cols="n INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT", pk=""),
                   "ACCEPT": HOUSE["ACCEPT"].replace("INSERT OR IGNORE", "INSERT")},
                  "incidents; expected 2"),
    "dedupe_by_summary": ("redelivery",
                          {"INBOX_SQL": _INBOX.format(cols="event_id TEXT", pk=" PRIMARY KEY")},
                          "incidents; expected 2"),
    "in_memory_task": ("durable",
                       {"ACCEPT": "threading.Thread(target=_process_one, args=(event,), daemon=True).start()",
                        "WORKER_ENABLED": "False"},
                       "had not stored it"),
    "audit_row_only": ("durable",
                       {"ACCEPT": ('with connect() as conn:\n'
                                   '            conn.execute("CREATE TABLE IF NOT EXISTS webhook_audit (event_id TEXT)")\n'
                                   '            conn.execute("INSERT INTO webhook_audit VALUES (?)", (event["event_id"],))\n'
                                   '            conn.commit()\n'
                                   '        threading.Thread(target=_process_one, args=(event,), daemon=True).start()'),
                        "WORKER_ENABLED": "False"},
                       "never became a complete incident"),
    # Incident now, runbook link in memory: a restart loses the link.
    "link_in_memory": ("durable",
                       {"ACCEPT": ('with connect() as conn:\n'
                                   '            conn.execute("INSERT OR IGNORE INTO pager_events'
                                   ' (event_id, service, summary, status) VALUES (?, ?, ?, \'done\')",\n'
                                   '                         (event["event_id"], event["service"], event["summary"]))\n'
                                   '            conn.execute(INSERT_INCIDENT, _incident_args(event, None))\n'
                                   '            conn.commit()\n'
                                   '        threading.Thread(target=_enrich_later, args=(event,), daemon=True).start()')},
                       "never became a complete incident"),
    # Processing starts 5 s after a forged request, beyond a short fixed wait.
    "signature_checked_after_delayed_processing": (
        "signature",
        {"SIGNATURE_REJECTS": ('(threading.Timer(5, _process_one, args=(json.loads(raw),)).start() or True)'
                               ' and not hmac.compare_digest(request.headers.get("x-pager-signature", ""),'
                               ' expected)')},
        "was stored or processed"),
}


def materialize(tmp_path: Path, overrides: dict[str, str]) -> Path:
    spec = yaml.safe_load(SCENARIO.read_text(encoding="utf-8"))
    for rel, text in spec["fixture"]["files"].items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    code = REFERENCE
    for marker, value in {**HOUSE, **overrides}.items():
        code = code.replace(marker, value)
    (tmp_path / "app/main.py").write_text(code, encoding="utf-8")
    (tmp_path / "probe_checks.py").write_text(ORACLE.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def run(workspace: Path, check: str) -> subprocess.CompletedProcess:
    # A 4 s runbook lookup still outlasts the vendor's 3 s window, so the timing checks discriminate.
    # Shorter allowances keep CI fast and still discriminate: the delayed-processing mutant finishes
    # at about 9 s, inside the 4 + 10 s signature wait, and the reference recovers at once.
    env = dict(os.environ, PROBE_RUNBOOK_DELAY="4", PROBE_PROCESSING_ALLOWANCE="10",
               PROBE_RECOVERY_ALLOWANCE="15", PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, "-B", "probe_checks.py", check], cwd=workspace, env=env,
                          capture_output=True, text=True, timeout=180)


@pytest.mark.parametrize("check", CHECKS)
def test_house_reference_passes(tmp_path, check):
    result = run(materialize(tmp_path, {}), check)
    assert result.returncode == 0, result.stdout + result.stderr


ENRICH_LATER = {
    "ACCEPT": ('with connect() as conn:\n'
               '            conn.execute(INSERT_INCIDENT, _incident_args(event, None))\n'
               '            conn.commit()\n'
               '        threading.Thread(target=_enrich_later, args=(event,), daemon=True).start()'),
    "WORKER_ENABLED": "False",
}


def test_enrich_later_design_completes(tmp_path):
    """Creating the incident first and attaching the runbook link afterwards is a valid design."""
    result = run(materialize(tmp_path, ENRICH_LATER), "completes")
    assert result.returncode == 0, result.stdout + result.stderr


def test_fixture_suite_passes_unchanged(tmp_path):
    spec = yaml.safe_load(SCENARIO.read_text(encoding="utf-8"))
    for rel, text in spec["fixture"]["files"].items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    result = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                            cwd=tmp_path, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("scenario_name,permits_review", [
    ("pager-webhook", True), ("cli-with-tests", False),
])
def test_review_dispatch_policy_matches_security_scope(tmp_path, scenario_name, permits_review):
    from probe import checking as probe_checking  # noqa: PLC0415 -- only this test needs the runner
    from probe import tracing as probe_tracing  # noqa: PLC0415

    scenario = SCENARIO.with_name(f"build-software-engineer-{scenario_name}.yaml")
    spec = yaml.safe_load(scenario.read_text(encoding="utf-8"))
    events = [
        {"type": "assistant", "message": {"content": [{
            "type": "tool_use", "id": "review-1", "name": "Task", "input": {
                "subagent_type": "save-toolkit:reviewer",
                "prompt": "Review only the new HMAC authentication boundary and its tests.",
            },
        }]}},
        {"type": "user", "message": {"content": [{
            "type": "tool_result", "tool_use_id": "review-1", "content": "Scoped review complete.",
        }]}},
    ]
    trace_path = tmp_path / "review.jsonl"
    trace_path.write_text("\n".join(json.dumps(event) for event in events), encoding="utf-8")
    trace = probe_tracing.parse_trace(trace_path)
    assert trace.dispatches == ["save-toolkit:reviewer"]
    ctx = SimpleNamespace(trace=trace)
    checks = [check for check in spec["checks"] if check["check"] == "no_task_dispatch"]
    results = [probe_checking.CHECKS[check["check"]](ctx, check) for check in checks]
    assert all(passed for passed, _ in results) is permits_review, results
    if not permits_review:
        assert any(check["target"] == "reviewer" for check in checks)


def test_webhook_scenario_preserves_scope_and_commit_guards():
    checks = yaml.safe_load(SCENARIO.read_text(encoding="utf-8"))["checks"]
    kinds = {check["check"] for check in checks}
    assert {"changes_within", "no_new_commits", "no_agents_dir"} <= kinds
    scope = next(check for check in checks if check["check"] == "changes_within")
    assert scope["allowed"] == ["app", "tests", "README.md", "pyproject.toml"]
